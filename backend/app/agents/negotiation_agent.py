"""
Negotiation RAG + Agentic Reasoning

Design:
    Current procurement context
            |
            v
    Agent chooses evidence tools
            |
            +--> hybrid RAG over negotiation_history
            |       - product family / procurement title
            |       - category
            |       - vendor/brand (bonus, not filter)
            |       - quote similarity
            |       - department
            |       - commercial-term similarity
            |       - historical outcome / success
            |
            +--> vendor risk
            +--> contract terms
            +--> deterministic benchmark
            +--> deterministic confidence
            |
            v
       LLM compares retrieved evidence
            |
            v
       evidence-grounded strategy
"""

import json
import logging
import math
import os
import re
import statistics
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq

from ..services.groq_key_manager import get_next_groq_key
from ..supabase_client import supabase, supabase_service
from ..models.negotiation import NegotiationEmail

logger = logging.getLogger(__name__)


_LAST_STRATEGY_TRACE: Dict[str, Any] = {}
_LAST_EMAIL_TRACE: Dict[str, Any] = {}


def get_last_strategy_trace() -> Dict[str, Any]:
    return dict(_LAST_STRATEGY_TRACE)


def get_last_email_trace() -> Dict[str, Any]:
    return dict(_LAST_EMAIL_TRACE)


def _store_strategy_trace(**kwargs: Any) -> None:
    _LAST_STRATEGY_TRACE.clear()
    _LAST_STRATEGY_TRACE.update(kwargs)


def _store_email_trace(**kwargs: Any) -> None:
    _LAST_EMAIL_TRACE.clear()
    _LAST_EMAIL_TRACE.update(kwargs)


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: Any) -> str:
    value = _text(value).lower()
    value = re.sub(r"[^a-z0-9\s]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _tokens(value: Any) -> set[str]:
    return {
        x.lower()
        for x in TOKEN_RE.findall(_text(value))
        if len(x) > 2
    }


def _token_similarity(a: Any, b: Any) -> float:
    """
    Dependency-free semantic-ish similarity.

    This is lexical similarity, not an embedding model. It is deliberately
    used as one component of hybrid RAG because the supplied `embedding`
    column is currently empty. If pgvector embeddings are populated later,
    this component can be replaced by vector similarity without changing the
    agent workflow.
    """
    left = _tokens(a)
    right = _tokens(b)

    if not left or not right:
        return 0.0

    intersection = len(left & right)
    union = len(left | right)

    return intersection / union if union else 0.0


def _text_match(a: Any, b: Any) -> float:
    left = _norm(a)
    right = _norm(b)

    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if left in right or right in left:
        return 0.8
    return _token_similarity(left, right)


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _norm(value) in {"true", "1", "yes", "y"}


def _is_success(row: Dict[str, Any]) -> bool:
    return _norm(
        row.get("outcome") or row.get("negotiation_status")
    ) in {
        "success",
        "successful",
        "won",
        "completed successfully",
    }


def _discount_received(row: Dict[str, Any]) -> Optional[float]:
    direct = _safe_float(row.get("discount_received"))
    if direct is not None and direct >= 0:
        return direct

    initial = _safe_float(row.get("initial_quote_value"))
    final = _safe_float(row.get("final_negotiated_value"))

    if (
        initial is not None
        and final is not None
        and initial > 0
        and 0 <= final <= initial
    ):
        return round((initial - final) / initial * 100.0, 4)

    return None


def _quote_similarity(
    current_quote: Optional[float],
    historical_quote: Optional[float],
) -> float:
    if (
        current_quote is None
        or historical_quote is None
        or current_quote <= 0
        or historical_quote <= 0
    ):
        return 0.0

    # Ratio-based similarity is more useful than absolute difference when
    # different vendors have different price scales.
    ratio = min(current_quote, historical_quote) / max(
        current_quote,
        historical_quote,
    )

    return max(0.0, min(1.0, ratio))


def _range_from_values(values: List[float]) -> Optional[str]:
    if not values:
        return None

    values = sorted(values)

    low = math.floor(min(values))
    high = math.ceil(max(values))

    if low == high:
        return f"{low:.0f}%"

    return f"{low:.0f}% - {high:.0f}%"


def _parse_json(value: Any) -> Dict[str, Any]:
    """
    Robustly parse JSON returned by the LLM.

    Handles:
    - normal JSON
    - markdown ```json blocks
    - JSON embedded in surrounding text
    - literal newlines inside JSON string values
    """

    if isinstance(value, dict):
        return value

    if not value:
        return {}

    text = str(value).strip()

    # Remove markdown code fences.
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\s*```$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    # First try normal JSON parsing.
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Find the outermost JSON object.
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end <= start:
        return {}

    candidate = text[start:end + 1]

    # The model sometimes places actual newline characters inside
    # JSON string values. Convert those newlines to escaped newlines
    # while preserving JSON structure.
    repaired = []
    inside_string = False
    escaped = False

    for char in candidate:
        if char == '"' and not escaped:
            inside_string = not inside_string

        if char == "\n" and inside_string:
            repaired.append("\\n")
        elif char == "\r" and inside_string:
            continue
        elif char == "\t" and inside_string:
            repaired.append("\\t")
        else:
            repaired.append(char)

        if char == "\\" and not escaped:
            escaped = True
        else:
            escaped = False

    repaired_text = "".join(repaired)

    try:
        parsed = json.loads(repaired_text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _normalize_confidence(value: Any) -> float:
    score = _safe_float(value)
    if score is None:
        return 0.0

    if 0 <= score <= 1:
        score *= 100

    return round(max(0.0, min(100.0, score)), 2)


# ---------------------------------------------------------------------------
# RAG retrieval
# ---------------------------------------------------------------------------

def _rag_weights() -> Dict[str, float]:
    """
    Weights are configurable through environment variables.
    They are generic retrieval signals, not strategy-specific rules.
    """
    return {
        "product": float(os.getenv("RAG_PRODUCT_WEIGHT", "0.28")),
        "category": float(os.getenv("RAG_CATEGORY_WEIGHT", "0.16")),
        "quote": float(os.getenv("RAG_QUOTE_WEIGHT", "0.16")),
        "vendor": float(os.getenv("RAG_VENDOR_WEIGHT", "0.12")),
        "department": float(os.getenv("RAG_DEPARTMENT_WEIGHT", "0.06")),
        "commercial": float(os.getenv("RAG_COMMERCIAL_WEIGHT", "0.08")),
        "outcome": float(os.getenv("RAG_OUTCOME_WEIGHT", "0.07")),
        "success": float(os.getenv("RAG_SUCCESS_WEIGHT", "0.07")),
    }


def _similarity_breakdown(
    current: Dict[str, Any],
    row: Dict[str, Any],
) -> Dict[str, float]:
    """Score historical evidence against the current procurement.

    Product family/category are the cross-brand anchors. Vendor is only a
    bonus. When procurement-only mode supplies multiple current quotes, the
    best matching candidate quote/vendor is used for that signal.
    """
    weights = _rag_weights()

    product_score = _text_match(
        current.get("product_family"),
        row.get("_historical_product_family"),
    )
    category_score = _text_match(
        current.get("product_category"),
        row.get("product_category"),
    )

    candidates = current.get("candidate_quotes") or []
    if not isinstance(candidates, list):
        candidates = []

    if candidates:
        vendor_scores = [
            _text_match(candidate.get("vendor_name"), row.get("vendor_name"))
            for candidate in candidates
            if candidate.get("vendor_name")
        ]
        quote_scores = [
            _quote_similarity(
                _safe_float(candidate.get("quote_value")),
                _safe_float(row.get("initial_quote_value")),
            )
            for candidate in candidates
            if candidate.get("quote_value") is not None
        ]
    else:
        vendor_scores = [
            _text_match(current.get("vendor_name"), row.get("vendor_name"))
        ] if current.get("vendor_name") else []
        quote_scores = [
            _quote_similarity(
                _safe_float(current.get("quote_value")),
                _safe_float(row.get("initial_quote_value")),
            )
        ] if current.get("quote_value") is not None else []

    vendor_score = max(vendor_scores, default=0.0)
    quote_score = max(quote_scores, default=0.0)

    department_score = _text_match(
        current.get("department"),
        row.get("_historical_department"),
    )

    current_commercial = " ".join(
        [
            _text(current.get("payment_terms")),
            _text(current.get("support_level")),
            _text(current.get("support_details")),
            _text(current.get("warranty")),
            _text(current.get("delivery_days")),
            _text(current.get("compliance")),
        ]
    )

    candidate_commercial_scores = []
    for candidate in candidates:
        candidate_text = " ".join(
            [
                _text(candidate.get("payment_terms")),
                _text(candidate.get("support_level")),
                _text(candidate.get("warranty_years")),
                _text(candidate.get("delivery_days")),
                _text(candidate.get("compliance_score")),
            ]
        )
        if candidate_text:
            candidate_commercial_scores.append(
                _token_similarity(candidate_text, " ".join(
                    [
                        _text(row.get("payment_terms")),
                        _text(row.get("support_level")),
                        _text(row.get("warranty_years")),
                        _text(row.get("delivery_days")),
                        _text(row.get("compliance_score")),
                    ]
                ))
            )

    if candidate_commercial_scores:
        commercial_score = max(candidate_commercial_scores)
    else:
        commercial_history = " ".join(
            [
                _text(row.get("payment_terms")),
                _text(row.get("support_level")),
                _text(row.get("warranty_years")),
                _text(row.get("delivery_days")),
                _text(row.get("compliance_score")),
            ]
        )
        commercial_score = _token_similarity(current_commercial, commercial_history)

    outcome_score = 1.0 if _is_success(row) else 0.0
    success = _safe_float(row.get("success_score"))
    success_score = max(0.0, min(100.0, success)) / 100.0 if success is not None else 0.0

    weighted = (
        product_score * weights["product"]
        + category_score * weights["category"]
        + quote_score * weights["quote"]
        + vendor_score * weights["vendor"]
        + department_score * weights["department"]
        + commercial_score * weights["commercial"]
        + outcome_score * weights["outcome"]
        + success_score * weights["success"]
    )
    total_weight = sum(weights.values()) or 1.0
    final_score = weighted / total_weight

    return {
        "product_similarity": round(product_score, 4),
        "category_similarity": round(category_score, 4),
        "quote_similarity": round(quote_score, 4),
        "vendor_similarity": round(vendor_score, 4),
        "department_similarity": round(department_score, 4),
        "commercial_similarity": round(commercial_score, 4),
        "outcome_score": round(outcome_score, 4),
        "success_score": round(success_score, 4),
        "relevance": round(final_score, 4),
    }


def _strategy_summary(
    records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for row in records:
        strategy = _text(row.get("strategy_used"))
        if strategy:
            groups[strategy].append(row)

    summaries = []

    for strategy, cases in groups.items():
        discounts = [
            d
            for d in (_discount_received(row) for row in cases)
            if d is not None
        ]

        successful = [
            row
            for row in cases
            if _is_success(row)
        ]

        scores = [
            s
            for s in (
                _safe_float(row.get("success_score"))
                for row in cases
            )
            if s is not None
        ]

        relevance = [
            r
            for r in (
                _safe_float(
                    row.get("_rag", {}).get("relevance")
                )
                for row in cases
            )
            if r is not None
        ]

        summaries.append(
            {
                "strategy": strategy,
                "cases": len(cases),
                "successful_cases": len(successful),
                "success_rate": round(
                    len(successful) / len(cases) * 100,
                    2,
                ),
                "average_success_score": round(
                    statistics.mean(scores),
                    2,
                ) if scores else None,
                "median_discount_received": round(
                    statistics.median(discounts),
                    2,
                ) if discounts else None,
                "discount_range": _range_from_values(
                    discounts
                ),
                "average_relevance": round(
                    statistics.mean(relevance) * 100,
                    2,
                ) if relevance else None,
            }
        )

    summaries.sort(
        key=lambda x: (
            x["success_rate"],
            x["average_success_score"] or 0,
            x["average_relevance"] or 0,
            x["cases"],
        ),
        reverse=True,
    )

    return summaries


def _calculate_confidence(
    records: List[Dict[str, Any]],
    chosen_strategy: Optional[str],
    benchmark: Dict[str, Any],
) -> Dict[str, Any]:
    if not records:
        return {
            "score": 15.0,
            "reason": "No historical evidence was retrieved.",
            "components": {},
        }

    relevance_values = [
        _safe_float(
            row.get("_rag", {}).get("relevance")
        )
        for row in records
    ]
    relevance_values = [
        x for x in relevance_values if x is not None
    ]

    average_relevance = (
        statistics.mean(relevance_values)
        if relevance_values else 0.0
    )

    successful = sum(
        1 for row in records if _is_success(row)
    )

    success_rate = successful / len(records)

    evidence_quantity = min(
        len(records) / 6.0,
        1.0,
    )

    benchmark_available = (
        benchmark.get("status") == "success"
    )

    strategy_support = 0.0

    if chosen_strategy:
        matching = [
            row
            for row in records
            if _norm(row.get("strategy_used"))
            == _norm(chosen_strategy)
        ]

        if matching:
            strategy_support = min(
                len(matching) / 3.0,
                1.0,
            )

    score = (
        0.30 * average_relevance
        + 0.20 * success_rate
        + 0.20 * evidence_quantity
        + 0.15 * (1.0 if benchmark_available else 0.0)
        + 0.15 * strategy_support
    ) * 100

    if len(records) < 2:
        score = min(score, 50.0)

    if not benchmark_available:
        score = min(score, 55.0)

    return {
        "score": round(score, 2),
        "reason": (
            "Confidence is derived from retrieval relevance, "
            "historical outcomes, evidence quantity, benchmark "
            "availability, and support for the selected strategy."
        ),
        "components": {
            "average_relevance": round(
                average_relevance * 100,
                2,
            ),
            "historical_success_rate": round(
                success_rate * 100,
                2,
            ),
            "evidence_count": len(records),
            "benchmark_available": benchmark_available,
            "selected_strategy_support": round(
                strategy_support * 100,
                2,
            ),
        },
    }



# ---------------------------------------------------------------------------
# Public RAG retrieval
# ---------------------------------------------------------------------------

async def retrieve_rag_evidence(
    context: Dict[str, Any],
    limit: int = 12,
    client: Any = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve hybrid RAG evidence from negotiation_history.

    Vendor is a relevance bonus, never a hard filter.
    Product family/procurement title is the primary cross-brand signal.
    Current procurement/baseline/accepted workflow records are excluded.
    """
    active_client = client or (supabase_service or supabase)

    limit = max(5, min(int(limit or 12), 20))

    response = (
        active_client
        .table("negotiation_history")
        .select("*")
        .limit(500)
        .execute()
    )

    rows = getattr(response, "data", None) or []

    current_procurement_id = _text(
        context.get("procurement_id")
    )

    rows = [
        row
        for row in rows
        if not _bool(row.get("is_baseline"))
        and _norm(row.get("outcome"))
        not in {"accepted"}
        and (
            not current_procurement_id
            or _text(row.get("procurement_id"))
            != current_procurement_id
        )
    ]

    if not rows:
        return []

    procurement_ids = list(
        {
            _text(row.get("procurement_id"))
            for row in rows
            if row.get("procurement_id")
        }
    )

    procurement_map: Dict[str, Dict[str, Any]] = {}

    if procurement_ids:
        procurement_response = (
            active_client
            .table("procurements")
            .select(
                "id,title,description,category,department"
            )
            .in_("id", procurement_ids)
            .execute()
        )

        for procurement in (
            getattr(
                procurement_response,
                "data",
                None,
            )
            or []
        ):
            procurement_map[
                _text(procurement.get("id"))
            ] = procurement

    for row in rows:
        procurement = procurement_map.get(
            _text(row.get("procurement_id")),
            {},
        )

        row["_historical_product_family"] = (
            procurement.get("title")
            or procurement.get("description")
            or ""
        )

        row["_historical_department"] = (
            procurement.get("department")
            or ""
        )

    scored: List[Dict[str, Any]] = []

    for row in rows:
        rag = _similarity_breakdown(
            context,
            row,
        )

        # Category is a domain boundary. Product-family similarity handles
        # cross-brand generalization inside that domain.
        current_category = _norm(
            context.get("product_category")
        )
        historical_category = _norm(
            row.get("product_category")
        )

        if (
            current_category
            and historical_category
            and current_category != historical_category
        ):
            continue

        row["_rag"] = rag
        scored.append(row)

    # If the category is missing or historical category data is incomplete,
    # broaden rather than silently return nothing.
    if not scored:
        for row in rows:
            row["_rag"] = _similarity_breakdown(
                context,
                row,
            )
        scored = rows

    scored.sort(
        key=lambda row: (
            row.get("_rag", {}).get("relevance", 0.0)
        ),
        reverse=True,
    )

    return scored[:limit]


# ---------------------------------------------------------------------------
# Agent tools
# ---------------------------------------------------------------------------

def _make_tools(
    context: Dict[str, Any],
    retrieved: List[Dict[str, Any]],
    state: Dict[str, Any],
    trace: List[Dict[str, Any]],
):
    client = supabase_service or supabase

    def log_tool(
        name: str,
        arguments: Dict[str, Any],
        result: Any,
    ) -> None:
        trace.append(
            {
                "tool": name,
                "arguments": arguments,
                "result_summary": (
                    {
                        "records": len(result)
                    }
                    if isinstance(result, list)
                    else result
                ),
            }
        )

    @tool
    async def retrieve_historical_negotiations(
        search_scope: str = "best relevant historical evidence",
        limit: int = 12,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant historical negotiations.

        Same vendor is a bonus, not a filter. Other brands in the same
        product family remain valid RAG evidence.
        """
        del search_scope

        try:
            selected = await retrieve_rag_evidence(
                context,
                limit=limit,
                client=client,
            )

            summaries = _strategy_summary(selected)

            retrieved.clear()
            retrieved.extend(selected)

            state["retrieval_complete"] = True
            state["strategy_summary"] = summaries

            result = {
                "records": [
                    {
                        "id": row.get("id"),
                        "vendor_name": row.get("vendor_name"),
                        "product_category": row.get("product_category"),
                        "historical_product": row.get(
                            "_historical_product_family"
                        ),
                        "strategy_used": row.get("strategy_used"),
                        "outcome": row.get("outcome"),
                        "discount_received": _discount_received(row),
                        "success_score": row.get("success_score"),
                        "relevance": round(
                            row["_rag"]["relevance"] * 100,
                            2,
                        ),
                        "match_components": row["_rag"],
                        "notes": row.get("notes"),
                        "successful_tactics": row.get(
                            "successful_tactics"
                        ),
                    }
                    for row in selected
                ],
                "strategy_summary": summaries,
            }

            log_tool(
                "retrieve_historical_negotiations",
                {"limit": limit},
                result,
            )

            return result

        except Exception as exc:
            result = {
                "records": [],
                "strategy_summary": [],
                "error": str(exc),
            }

            log_tool(
                "retrieve_historical_negotiations",
                {"limit": limit},
                result,
            )

            return result

    @tool
    async def get_vendor_risk() -> Dict[str, Any]:
        """Retrieve risk for the selected vendor or all current candidates."""
        vendor_ids = []
        if context.get("vendor_id"):
            vendor_ids.append(_text(context.get("vendor_id")))
        for candidate in context.get("candidate_quotes") or []:
            vid = _text(candidate.get("vendor_id"))
            if vid and vid not in vendor_ids:
                vendor_ids.append(vid)

        results = []
        for vid in vendor_ids:
            response = (
                client.table("vendor_risk_analysis").select("*")
                .eq("vendor_id", vid).order("created_at", desc=True).limit(1).execute()
            )
            rows = getattr(response, "data", None) or []
            if rows:
                results.append(rows[0])

        state["risk_checked"] = True
        result = {"available": bool(results), "records": results}
        log_tool("get_vendor_risk", {"vendor_ids": vendor_ids}, result)
        return result

    @tool
    async def get_contract_terms() -> Dict[str, Any]:
        """Retrieve contract terms for the selected vendor or all candidates."""
        vendor_ids = []
        if context.get("vendor_id"):
            vendor_ids.append(_text(context.get("vendor_id")))
        for candidate in context.get("candidate_quotes") or []:
            vid = _text(candidate.get("vendor_id"))
            if vid and vid not in vendor_ids:
                vendor_ids.append(vid)

        results = []
        for vid in vendor_ids:
            response = (
                client.table("contracts").select("*")
                .eq("vendor_id", vid).order("created_at", desc=True).limit(1).execute()
            )
            rows = getattr(response, "data", None) or []
            if rows:
                results.append(rows[0])

        state["contract_checked"] = True
        result = {"available": bool(results), "records": results}
        log_tool("get_contract_terms", {"vendor_ids": vendor_ids}, result)
        return result

    @tool
    async def calculate_discount_benchmark(
        strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculate discount evidence from the records already retrieved.

        The LLM cannot provide discount numbers to this tool.
        """
        records = retrieved

        if strategy:
            matching = [
                row
                for row in records
                if _norm(row.get("strategy_used"))
                == _norm(strategy)
            ]

            if matching:
                records = matching

        successful = [
            row
            for row in records
            if _is_success(row)
            and _discount_received(row) is not None
        ]

        values = [
            _discount_received(row)
            for row in successful
        ]

        values = [
            value for value in values
            if value is not None
        ]

        if not values:
            benchmark = {
                "status": "insufficient_data",
                "strategy": strategy,
                "sample_size": 0,
                "discount_range": None,
                "median_discount": None,
                "observed_discounts": [],
            }
        else:
            benchmark = {
                "status": "success",
                "strategy": strategy,
                "sample_size": len(values),
                "discount_range": _range_from_values(
                    values
                ),
                "median_discount": round(
                    statistics.median(values),
                    2,
                ),
                "observed_discounts": [
                    round(value, 2)
                    for value in sorted(values)
                ],
            }

        state["benchmark"] = benchmark

        log_tool(
            "calculate_discount_benchmark",
            {"strategy": strategy},
            benchmark,
        )

        return benchmark

    @tool
    async def calculate_confidence(
        selected_strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculate confidence deterministically from retrieved evidence."""
        benchmark = state.get(
            "benchmark",
            {
                "status": "insufficient_data"
            },
        )

        result = _calculate_confidence(
            retrieved,
            selected_strategy,
            benchmark,
        )

        state["confidence"] = result

        log_tool(
            "calculate_confidence",
            {
                "selected_strategy": selected_strategy
            },
            result,
        )

        return result

    return [
        retrieve_historical_negotiations,
        get_vendor_risk,
        get_contract_terms,
        calculate_discount_benchmark,
        calculate_confidence,
    ]


# ---------------------------------------------------------------------------
# Agent prompt
# ---------------------------------------------------------------------------

def _system_prompt(context: Dict[str, Any], evidence: List[Dict[str, Any]], summaries: List[Dict[str, Any]]) -> str:
    """Build a deliberately compact, evidence-grounded reasoning prompt.

    Important: do not dump raw procurement/quote/history objects into the LLM.
    The backend already performed RAG. The model's job is to compare the
    compact evidence and explain the recommendation.
    """
    compact_context = {
        "procurement": context.get("procurement_title") or context.get("title"),
        "category": context.get("product_category"),
        "department": context.get("department"),
        "vendor": context.get("vendor_name"),
        "quote_value": context.get("quote_value"),
        "candidate_quotes": [
            {
                "vendor": q.get("vendor_name"),
                "quote": q.get("quote_value"),
                "payment": q.get("payment_terms"),
                "delivery_days": q.get("delivery_days"),
                "warranty_years": q.get("warranty_years"),
            }
            for q in (context.get("candidate_quotes") or [])[:6]
        ],
    }

    compact_evidence = []
    for row in evidence[:6]:
        compact_evidence.append({
            "vendor": row.get("vendor_name"),
            "product": row.get("_historical_product_family"),
            "strategy": row.get("strategy_used"),
            "outcome": row.get("outcome"),
            "discount_received": _discount_received(row),
            "success_score": row.get("success_score"),
            "relevance": round(row.get("_rag", {}).get("relevance", 0) * 100, 1),
            "successful_tactics": row.get("successful_tactics"),
            "notes": _text(row.get("notes"))[:180],
        })

    compact_summaries = [
        {
            "strategy": s.get("strategy"),
            "cases": s.get("cases"),
            "cases": s.get("cases"),
            "successful_cases": s.get("successful_cases"),
            "success_rate": s.get("success_rate"),
            "avg_success_score": s.get("average_success_score"),
            "median_discount_received": s.get("median_discount_received"),
            "discount_range": s.get("discount_range"),
            "avg_relevance": s.get("average_relevance"),
        }
        for s in summaries[:6]
    ]

    return f"""
You are the procurement negotiation reasoning agent.

The backend has already performed hybrid RAG. Use ONLY the evidence below.

CURRENT PROCUREMENT:
{json.dumps(compact_context, default=str, separators=(",", ":"))}

RETRIEVED HISTORICAL EVIDENCE:
{json.dumps(compact_evidence, default=str, separators=(",", ":"))}

STRATEGY SUMMARIES:
{json.dumps(compact_summaries, default=str, separators=(",", ":"))}

REASONING RULES:
- Compare the retrieved strategies using the NUMBERS in STRATEGY SUMMARIES.
- For every strategy you mention, keep these facts separate: cases, successful cases, success rate, average success score, median discount, and relevance.
- NEVER say a strategy has a higher success rate unless its numeric success_rate is actually higher.
- NEVER write a sentence that contains both "higher success rate" and "lower success rate" for the same comparison.
- More cases, higher success score, higher relevance, and higher discount are separate signals; do not treat any one of them as the success rate.
- Same-vendor evidence is a bonus, not a requirement.
- Same product family across different brands is valid evidence.
- Do not invent historical facts, discounts, vendors, or strategies.
- Do not choose a strategy merely because it achieved the highest discount.
- Explain the selected strategy using a balanced comparison of evidence strength, sample size, success rate, success score, product relevance, vendor relevance, and achieved discount.
- If the sample size is small, explicitly say that the evidence is limited.
- The discount is grounded by the backend, so do not invent a percentage.
- If you cannot establish the comparison from the supplied numbers, say that the evidence is inconclusive rather than guessing.

Return ONLY valid JSON:
{{
  "recommended_strategy": "",
  "reasoning": "",
  "risks": []
}}
""".strip()

def _fallback_strategy(reason: str) -> Dict[str, Any]:
    # No invented percentage is used in the fallback.
    return {
        "recommended_strategy": (
            "Review the available procurement evidence before "
            "committing to a negotiation position."
        ),
        "expected_discount_range": "Evidence unavailable",
        "confidence_score": 15.0,
        "reasoning": (
            "The negotiation agent could not obtain sufficient evidence "
            f"to make a reliable recommendation. {reason}"
        ),
        "risks": [
            "Insufficient historical evidence",
            "Human procurement review required",
        ],
        "_historical_records": [],
    }


def _validate_strategy(
    parsed: Dict[str, Any],
) -> Dict[str, Any]:
    risks = parsed.get("risks", [])

    if not isinstance(risks, list):
        risks = [str(risks)]

    return {
        "recommended_strategy": _text(
            parsed.get("recommended_strategy")
        ),
        "expected_discount_range": _text(
            parsed.get("expected_discount_range")
        ),
        "confidence_score": round(_normalize_confidence(parsed.get("confidence_score"))),
        "reasoning": _text(
            parsed.get("reasoning")
        ),
        "risks": [
            _text(x)
            for x in risks
            if _text(x)
        ],
    }



def _build_grounded_reasoning(
    selected_strategy: str,
    summaries: List[Dict[str, Any]],
    benchmark: Dict[str, Any],
    records: List[Dict[str, Any]],
) -> str:
    """Create the factual evidence explanation from backend-calculated metrics.

    The LLM chooses/interprets the strategy, but this section deliberately
    avoids letting the LLM rewrite numerical evidence inconsistently.
    """
    selected = next(
        (
            s for s in summaries
            if _norm(s.get("strategy")) == _norm(selected_strategy)
        ),
        None,
    )

    if not selected:
        return (
            f"{selected_strategy} was selected by the reasoning model, "
            "but the retrieved strategy summary was unavailable."
        )

    parts = [
        f"{selected_strategy} is supported by "
        f"{selected.get('cases', 0)} retrieved historical case(s), "
        f"of which {selected.get('successful_cases', 0)} were successful "
        f"({selected.get('success_rate', 0)}% success rate)."
    ]

    score = selected.get("average_success_score")
    relevance = selected.get("average_relevance")
    median_discount = selected.get("median_discount_received")

    if score is not None:
        parts.append(
            f"Its average historical success score is {score}."
        )
    if relevance is not None:
        parts.append(
            f"Its average RAG relevance to the current procurement is "
            f"{relevance}%."
        )
    if median_discount is not None:
        parts.append(
            f"The median observed discount for this strategy in the "
            f"retrieved cases is {median_discount}%."
        )

    # Compare against the strongest alternatives using actual numbers.
    alternatives = [
        s for s in summaries
        if _norm(s.get("strategy")) != _norm(selected_strategy)
    ][:3]

    if alternatives:
        comparisons = []
        for alt in alternatives:
            comparisons.append(
                f"{alt.get('strategy')}: "
                f"{alt.get('cases', 0)} case(s), "
                f"{alt.get('successful_cases', 0)} successful, "
                f"{alt.get('success_rate', 0)}% success rate, "
                f"average success score "
                f"{alt.get('average_success_score') if alt.get('average_success_score') is not None else 'N/A'}, "
                f"average relevance "
                f"{alt.get('average_relevance') if alt.get('average_relevance') is not None else 'N/A'}%"
            )

        parts.append(
            "For comparison, the strongest retrieved alternatives were: "
            + "; ".join(comparisons) + "."
        )

    if selected.get("cases", 0) <= 2:
        parts.append(
            "The recommendation should be treated as moderately supported "
            "because the number of directly retrieved historical cases is small."
        )
    else:
        parts.append(
            "The recommendation is supported by multiple retrieved historical cases."
        )

    if benchmark.get("status") == "success":
        parts.append(
            f"The evidence-based discount benchmark is "
            f"{benchmark.get('discount_range')} based on successful retrieved cases."
        )
    else:
        parts.append("There is insufficient successful discount evidence for a benchmark.")

    return " ".join(parts)


def _strategy_supported(
    strategy: str,
    records: List[Dict[str, Any]],
) -> bool:
    if not strategy:
        return False

    normalized = _norm(strategy)

    return any(
        normalized == _norm(
            row.get("strategy_used")
        )
        for row in records
        if row.get("strategy_used")
    )


async def _run_agent(
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Run the real RAG -> LLM reasoning path.

    RAG is performed by the backend first so the LLM receives a small,
    controlled evidence set. No tool-binding loop is used here because the
    Groq 6K TPM limit makes a multi-tool conversation unnecessarily large.
    There is intentionally NO strategy fallback: if the model fails, the
    exception is propagated so the API exposes the real failure.
    """
    key = get_next_groq_key()
    if not key:
        raise RuntimeError("No Groq API key is configured.")

    # 1. Real hybrid RAG retrieval.
    retrieved = await retrieve_rag_evidence(
        context,
        limit=8,
        client=supabase_service or supabase,
    )

    if not retrieved:
        raise RuntimeError(
            "No relevant historical negotiation evidence was retrieved."
        )

    # 2. Aggregate the retrieved evidence before sending it to the model.
    summaries = _strategy_summary(retrieved)

    # 3. Keep the prompt deliberately compact.
    prompt = _system_prompt(context, retrieved, summaries)

    model_name = os.getenv(
        "NEGOTIATION_MODEL",
        "llama-3.1-8b-instant",
    )

    llm = ChatGroq(
        api_key=key,
        model=model_name,
        temperature=0,
        max_tokens=500,
        timeout=30,
        max_retries=2,
    )

    # 4. One actual reasoning call. No fallback and no tool-call loop.
    response = await llm.ainvoke(prompt)
    final_text = _text(response.content)

    parsed = _parse_json(final_text)
    if not parsed:
        raise ValueError(
            f"Negotiation model returned invalid JSON: {final_text[:500]}"
        )

    result = _validate_strategy(parsed)

    if not result["recommended_strategy"]:
        raise ValueError("Negotiation model returned no recommended strategy.")

    # 5. Ground the numeric fields deterministically.
    chosen_strategy = result["recommended_strategy"]

    benchmark = _benchmark_for_strategy(
        retrieved,
        chosen_strategy,
    )

    # If the model names a strategy that was not actually retrieved,
    # do not silently replace it. Surface the mismatch as an error.
    if not _strategy_supported(chosen_strategy, retrieved):
        raise ValueError(
            f"Model recommended unsupported strategy '{chosen_strategy}'. "
            "The strategy must be supported by retrieved historical evidence."
        )

    if benchmark["status"] != "success":
        benchmark = _benchmark_for_strategy(retrieved, None)

    if benchmark["status"] == "success":
        result["expected_discount_range"] = benchmark["discount_range"]
    else:
        result["expected_discount_range"] = "Evidence unavailable"

    confidence = _calculate_confidence(
        retrieved,
        result["recommended_strategy"],
        benchmark,
    )
    result["confidence_score"] = round(confidence["score"])

    # Keep the model responsible for choosing the strategy, but generate the
    # numerical explanation from backend evidence so contradictions cannot
    # appear between success rate, sample size, score, relevance, and discount.
    result["reasoning"] = _build_grounded_reasoning(
        selected_strategy=result["recommended_strategy"],
        summaries=summaries,
        benchmark=benchmark,
        records=retrieved,
    )

    if not result["risks"]:
        result["risks"] = [
            "Commercial terms require human review before action."
        ]

    return {
        "result": result,
        "records": retrieved,
        "trace": {
            "fallback": False,
            "steps": 1,
            "tool_calls": [],
            "raw_response": final_text,
            "strategy_summary": summaries,
            "benchmark": benchmark,
            "confidence": confidence,
            "model": model_name,
            "retrieval_count": len(retrieved),
        },
    }

def _benchmark_for_strategy(
    records: List[Dict[str, Any]],
    strategy: Optional[str],
) -> Dict[str, Any]:
    selected = records

    if strategy:
        matching = [
            row
            for row in records
            if _norm(row.get("strategy_used"))
            == _norm(strategy)
        ]

        if matching:
            selected = matching

    successful_values = [
        _discount_received(row)
        for row in selected
        if _is_success(row)
    ]

    successful_values = [
        value
        for value in successful_values
        if value is not None
    ]

    if not successful_values:
        return {
            "status": "insufficient_data",
            "strategy": strategy,
            "sample_size": 0,
            "discount_range": None,
            "median_discount": None,
            "observed_discounts": [],
        }

    return {
        "status": "success",
        "strategy": strategy,
        "sample_size": len(successful_values),
        "discount_range": _range_from_values(
            successful_values
        ),
        "median_discount": round(
            statistics.median(successful_values),
            2,
        ),
        "observed_discounts": [
            round(x, 2)
            for x in sorted(successful_values)
        ],
    }


# ---------------------------------------------------------------------------
# Public strategy function
# ---------------------------------------------------------------------------

async def generate_negotiation_strategy(
    current_negotiation: Dict[str, Any],
    historical: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Run the real procurement RAG + LLM reasoning workflow.

    `historical` remains accepted for backward compatibility, but authoritative
    evidence is always retrieved by the current RAG pipeline.
    """
    context = dict(current_negotiation or {})

    if "current_procurement_context" in context:
        context = dict(context["current_procurement_context"])

    if historical:
        context["legacy_historical_count"] = len(historical)

    try:
        outcome = await _run_agent(context)
        result = outcome["result"]

        _store_strategy_trace(
            prompt=_system_prompt(
                context,
                outcome["records"],
                outcome["trace"].get("strategy_summary", []),
            ),
            raw_llm_response=outcome["trace"].get("raw_response", ""),
            parsed_json=_parse_json(
                outcome["trace"].get("raw_response", "")
            ) or {},
            final_returned_object=result,
            used_fallback=False,
            fallback_reason="",
            agent_steps=outcome["trace"].get("steps", 1),
            tool_calls=[],
            strategy_summary=outcome["trace"].get("strategy_summary", []),
            benchmark=outcome["trace"].get("benchmark", {}),
            confidence=outcome["trace"].get("confidence", {}),
            retrieval_count=outcome["trace"].get("retrieval_count", 0),
            model=outcome["trace"].get("model", ""),
        )

        result["_historical_records"] = outcome["records"]
        return result

    except Exception as exc:
        _store_strategy_trace(
            prompt="",
            raw_llm_response="",
            parsed_json={},
            final_returned_object={},
            used_fallback=False,
            fallback_reason="",
            agent_steps=0,
            tool_calls=[],
            error=str(exc),
        )
        # Do NOT hide the failure behind a fake recommendation.
        raise


# ---------------------------------------------------------------------------
# Email generation
# ---------------------------------------------------------------------------

def _email_prompt(
    vendor_name: str,
    strategy: str,
    discount: str,
) -> str:
    """Generate a professional, friendly vendor-facing negotiation email."""

    strategy_key = _norm(strategy)

    if "bulk" in strategy_key or "volume" in strategy_key:
        strategy_guidance = (
            "Naturally explore whether the volume of the requirement could "
            "enable better pricing or other commercial benefits."
        )
    elif "competitive" in strategy_key or "bidding" in strategy_key:
        strategy_guidance = (
            "Naturally explore whether there is flexibility in the current "
            "commercial proposal and whether a more competitive offer is possible."
        )
    elif "long" in strategy_key or "multi" in strategy_key:
        strategy_guidance = (
            "Naturally explore whether the potential longer-term relationship "
            "could enable more favorable commercial terms."
        )
    elif "bundle" in strategy_key:
        strategy_guidance = (
            "Naturally explore whether the overall package or combination "
            "of requirements could provide better value."
        )
    elif "consolid" in strategy_key:
        strategy_guidance = (
            "Naturally explore whether the broader scope of the requirement "
            "could enable more favorable commercial terms."
        )
    else:
        strategy_guidance = (
            "Naturally explore whether there is flexibility to improve "
            "the current commercial terms."
        )

    return f"""
You are an experienced procurement professional writing a vendor
negotiation email.

Vendor:
{vendor_name or "the vendor"}

Internal negotiation approach:
{strategy}

Internal discount guidance:
{discount}

Use the internal approach only to guide the wording. NEVER reveal the
strategy name, discount guidance, RAG evidence, AI reasoning, confidence,
risk scores, benchmarks, or historical negotiation data.

Negotiation direction:
{strategy_guidance}

EMAIL REQUIREMENTS:
- Professional, warm, concise and collaborative.
- Thank the vendor for the quotation.
- Refer to "our current requirement" unless a specific requirement name
  is provided.
- Make ONE clear and polite request to explore better commercial terms.
- Invite the vendor to suggest suitable pricing or commercial alternatives.
- Emphasize a mutually beneficial discussion.
- Address the vendor naturally using the actual vendor name.
- If the vendor is a company, use "Hi <Company Name> Team,".
- If it is a person's name, use "Hi <Name>,".
- Sign as "Procurement Team".
- Keep the email around 100-150 words.

DO NOT:
- Use "Dear Vendor".
- Mention or demand a specific discount percentage.
- Say "Our proposed approach is {strategy}".
- Say "Our strategy is {strategy}".
- Mention competitors unless explicitly provided as vendor-safe information.
- Invent quantities, prices, deadlines, commitments, quotations or facts.
- Use commanding or threatening language.
- Use placeholders such as [Vendor Name], [Project Name], [Your Name], etc.
- Repeat the same negotiation request multiple times.
- Use unnecessary generic filler.

Preferred tone:
"We would appreciate it if you could..."
"We were wondering if there may be an opportunity to..."
"Could you please let us know if..."
"We would be happy to explore..."
"We would welcome the opportunity to discuss..."

FINAL CHECK:
Before returning the email, ensure that:
1. The actual vendor name is used.
2. There are no placeholders.
3. The internal strategy and discount are not exposed.
4. There is one clear negotiation request.
5. The email sounds naturally written by a procurement professional.
6. The email ends with "Procurement Team".

Return ONLY valid JSON:
{{
    "subject": "...",
    "body": "..."
}}
""".strip()


def _fallback_email(
    vendor_name: str,
    strategy: str,
    discount: str,
) -> Dict[str, str]:
    """
    Emergency fallback only.

    This is not the normal path. It never exposes internal strategy,
    discount benchmarks, RAG evidence, or AI reasoning.
    """
    vendor = (vendor_name or "").strip()

    if not vendor:
        greeting = "Hi there,"
    elif any(ch in vendor for ch in [" ", "."]) and len(vendor.split()) <= 4:
        greeting = f"Hi {vendor},"
    else:
        greeting = f"Hi {vendor} Team,"

    strategy_key = _norm(strategy)

    if "bulk" in strategy_key or "volume" in strategy_key:
        request = (
            "As we review the requirement, we were wondering if there may "
            "be an opportunity to explore more favorable pricing based on "
            "the volume we are considering. If there are any volume-based "
            "pricing options or other commercial benefits available, we "
            "would be happy to consider them."
        )
    elif "competitive" in strategy_key or "bidding" in strategy_key:
        request = (
            "As we review the proposal internally, we were wondering if "
            "there may be any flexibility in the current commercial terms. "
            "We would appreciate the opportunity to explore whether there "
            "are alternative options that could make the proposal more "
            "competitive."
        )
    elif "long" in strategy_key or "multi" in strategy_key:
        request = (
            "As we consider our requirements going forward, we would be "
            "happy to explore whether the potential longer-term business "
            "could provide an opportunity for more favorable commercial "
            "terms."
        )
    else:
        request = (
            "As we review the proposal internally, we were wondering if "
            "there may be any flexibility in the current commercial terms "
            "that we could explore together."
        )

    return {
        "subject": "Exploring Commercial Options for Our Requirement",
        "body": (
            f"{greeting}\n\n"
            "I hope you're doing well.\n\n"
            "Thank you for sharing the quotation and for your support "
            "with our current requirement.\n\n"
            f"{request}\n\n"
            "If there are any alternative pricing or commercial options "
            "you feel would be suitable, we would be glad to consider "
            "them as part of our evaluation.\n\n"
            "We value the opportunity to work with your team and would "
            "welcome the chance to discuss this further.\n\n"
            "Looking forward to hearing your thoughts.\n\n"
            "Best regards,\n"
            "Procurement Team"
        ),
    }

async def generate_negotiation_email(
    vendor_name: str,
    recommended_strategy: str,
    expected_discount: str,
    procurement_id: Optional[str] = None,
    quote_id: Optional[str] = None,
    vendor_id: Optional[str] = None,
) -> NegotiationEmail:
    """Generate the actual vendor-facing negotiation email with the LLM.

    Internal strategy labels, RAG evidence, confidence, and discount
    benchmarks are supplied only as internal guidance and must never be
    exposed in the vendor-facing email.

    IMPORTANT:
    There is intentionally no silent fallback here. If Groq fails, returns
    invalid JSON, or produces an unsafe email, the real error is raised so
    the API/UI can surface the problem instead of showing a misleading
    hard-coded email.
    """
    del procurement_id, quote_id, vendor_id

    key = get_next_groq_key()
    if not key:
        raise RuntimeError("No Groq API key is configured.")

    prompt = _email_prompt(
        vendor_name=vendor_name,
        strategy=recommended_strategy,
        discount=expected_discount,
    )

    model_name = os.getenv(
        "NEGOTIATION_EMAIL_MODEL",
        os.getenv("NEGOTIATION_MODEL", "llama-3.1-8b-instant"),
    )

    llm = ChatGroq(
        api_key=key,
        model=model_name,
        temperature=0,
        max_tokens=500,
        timeout=30,
        max_retries=2,
    )

    content = ""

    try:
        response = await llm.ainvoke(prompt)
        content = response.content

        if isinstance(content, list):
            content = "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            )

        content = _text(content)

        if not content:
            raise ValueError("Email model returned an empty response.")

        parsed = _parse_json(content)

        if not parsed:
            raise ValueError(
                "Email model returned invalid JSON. "
                f"Raw response: {content[:1000]}"
            )

        subject = _text(parsed.get("subject"))
        body = _text(parsed.get("body"))

        if not subject:
            raise ValueError("Email model returned an empty subject.")

        if not body:
            raise ValueError("Email model returned an empty body.")

        if len(subject) < 10:
            raise ValueError(
                f"Email subject is too short: {subject!r}"
            )

        if len(body) < 80:
            raise ValueError(
                "Email body is too short to be a proper negotiation email."
            )

        combined = _norm(f"{subject} {body}")

        # Never allow internal procurement terminology to reach the vendor.
        forbidden_patterns = [
            "evidence-supported",
            "evidence supported",
            "target range",
            "expected discount",
            "recommended strategy",
            "our strategy is",
            "our proposed approach",
            "rag",
            "confidence score",
            "success score",
            "historical evidence",
            "internal strategy",
            "ai strategy",
            "benchmark",
        ]

        leaked = [
            term
            for term in forbidden_patterns
            if _norm(term) in combined
        ]

        if leaked:
            raise ValueError(
                "Generated email contains internal procurement terminology: "
                + ", ".join(leaked)
            )

        # Prevent obvious placeholder leakage.
        placeholders = [
            "[vendor name]",
            "[company name]",
            "[project name]",
            "[your name]",
            "[requirement name]",
        ]

        found_placeholders = [
            placeholder
            for placeholder in placeholders
            if _norm(placeholder) in combined
        ]

        if found_placeholders:
            raise ValueError(
                "Generated email contains placeholders: "
                + ", ".join(found_placeholders)
            )

        # Prevent the exact generic greeting that caused the fallback problem.
        if combined.startswith("dear vendor"):
            raise ValueError(
                "Generated email contains the generic 'Dear Vendor' greeting."
            )

        result = NegotiationEmail(
            subject=subject,
            body=body,
        )

        _store_email_trace(
            prompt=prompt,
            raw_llm_response=content,
            parsed_json=parsed,
            final_returned_object={
                "subject": subject,
                "body": body,
            },
            used_fallback=False,
            fallback_reason="",
            model=model_name,
        )

        logger.info(
            "Negotiation email generated successfully using model=%s",
            model_name,
        )

        return result

    except Exception as exc:
        logger.exception("Negotiation email LLM generation failed")

        _store_email_trace(
            prompt=prompt,
            raw_llm_response=content,
            parsed_json={},
            final_returned_object={},
            used_fallback=False,
            fallback_reason="email_generation_failed",
            model=model_name,
            error=str(exc),
        )

        # DO NOT return _fallback_email().
        # Surface the real failure so the actual issue can be diagnosed.
        raise RuntimeError(
            f"Negotiation email LLM generation failed: {str(exc)}"
        ) from exc

