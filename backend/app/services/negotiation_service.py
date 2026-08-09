"""Negotiation service for procurement RAG/agent workflows."""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..agents import negotiation_agent as negotiation_agent_module
from ..agents.negotiation_agent import (
    generate_negotiation_email,
    generate_negotiation_strategy,
    retrieve_rag_evidence,
)
from ..models.negotiation import (
    NegotiationEmail,
    NegotiationHistoryRecord,
    NegotiationStrategy,
    NegotiationStrategyResult,
)
from ..supabase_client import supabase, supabase_service
from .audit_service import log_agent_execution


logger = logging.getLogger(__name__)


def _text(value: Any) -> str:
    return str(value or "").strip()


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


def _norm(value: Any) -> str:
    text = _text(value).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]+", " ", text)).strip()


def _parse_json(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        return json.loads(value) if isinstance(value, str) else {}
    except Exception:
        return {}


def _quote_value(quote: Dict[str, Any]) -> Optional[float]:
    """Return a comparable unit/quoted value, correcting obvious total-price fields."""
    direct = _safe_float(quote.get("price"))
    extracted = _parse_json(quote.get("extracted_json"))
    full_ai = extracted.get("full_ai_result") or {}
    extracted_data = full_ai.get("extracted_data") or {}
    extracted_price = _safe_float(extracted_data.get("price"))

    if direct is None:
        return extracted_price
    if extracted_price is None or extracted_price <= 0:
        return direct

    # Some uploaded quotes store the grand total in price while extracted_data.price
    # is the comparable unit price. Prefer the unit price when the discrepancy is large.
    ratio = max(direct, extracted_price) / max(min(direct, extracted_price), 1.0)
    if ratio >= 20:
        return extracted_price
    return direct


def _quote_summary(quote: Dict[str, Any], vendor: Dict[str, Any]) -> Dict[str, Any]:
    value = _quote_value(quote)
    return {
        "quote_id": quote.get("id"),
        "vendor_id": quote.get("vendor_id") or vendor.get("id"),
        "vendor_name": _text(vendor.get("vendor_name")),
        "quote_value": value,
        "delivery_days": _safe_int(quote.get("delivery_days")),
        "warranty_years": _safe_float(quote.get("warranty_years")),
        "support_level": quote.get("support_level"),
        "payment_terms": quote.get("payment_terms"),
        "compliance_score": _safe_float(quote.get("compliance_score")),
        "created_at": quote.get("created_at"),
    }


async def _fetch_vendors(active_client: Any, procurement_id: Optional[str]) -> List[Dict[str, Any]]:
    if not procurement_id:
        return []
    response = (
        active_client.table("vendors").select("*").eq("procurement_id", procurement_id).execute()
    )
    return getattr(response, "data", None) or []


async def _fetch_quotes_for_vendor(active_client: Any, vendor_id: str) -> List[Dict[str, Any]]:
    response = (
        active_client.table("vendor_quotes").select("*").eq("vendor_id", vendor_id)
        .order("created_at", desc=True).execute()
    )
    return getattr(response, "data", None) or []


async def build_procurement_context(
    procurement_id: Optional[str] = None,
    quote_id: Optional[str] = None,
    vendor_id: Optional[str] = None,
    client: Any = None,
) -> Dict[str, Any]:
    """Build current procurement context, including all current vendor quotes when needed."""
    active_client = client or (supabase_service or supabase)
    if not any([procurement_id, quote_id, vendor_id]):
        raise ValueError("Provide procurement_id, quote_id, or vendor_id.")

    procurement: Dict[str, Any] = {}
    if procurement_id:
        response = active_client.table("procurements").select("*").eq("id", procurement_id).limit(1).execute()
        rows = getattr(response, "data", None) or []
        if rows:
            procurement = rows[0]

    # Resolve an explicitly requested quote first.
    selected_quote: Dict[str, Any] = {}
    selected_vendor: Dict[str, Any] = {}

    if quote_id:
        response = active_client.table("vendor_quotes").select("*").eq("id", quote_id).limit(1).execute()
        rows = getattr(response, "data", None) or []
        if not rows:
            raise ValueError(f"No quote found for quote_id={quote_id}.")
        selected_quote = rows[0]
        vendor_id = vendor_id or _text(selected_quote.get("vendor_id"))

    if vendor_id:
        response = active_client.table("vendors").select("*").eq("id", vendor_id).limit(1).execute()
        rows = getattr(response, "data", None) or []
        if not rows:
            raise ValueError(f"No vendor found for vendor_id={vendor_id}.")
        selected_vendor = rows[0]

        if selected_quote and _text(selected_quote.get("vendor_id")) != _text(selected_vendor.get("id")):
            raise ValueError("The supplied quote_id does not belong to the supplied vendor_id.")

    vendors = await _fetch_vendors(active_client, procurement_id)
    vendor_by_id = {_text(v.get("id")): v for v in vendors if _text(v.get("id"))}
    if selected_vendor:
        vendor_by_id[_text(selected_vendor.get("id"))] = selected_vendor

    # A vendor can be supplied without procurement_id. In that case it is still valid.
    if selected_vendor and not vendors:
        vendors = [selected_vendor]

    candidate_quotes: List[Dict[str, Any]] = []
    if selected_quote:
        candidate_quotes.append(_quote_summary(selected_quote, selected_vendor))
    elif vendor_id:
        quotes = await _fetch_quotes_for_vendor(active_client, _text(vendor_id))
        if quotes:
            candidate_quotes.append(_quote_summary(quotes[0], selected_vendor))
    else:
        # Procurement-only requests: use the latest quote from EVERY vendor.
        for vendor in vendors:
            vid = _text(vendor.get("id"))
            if not vid:
                continue
            quotes = await _fetch_quotes_for_vendor(active_client, vid)
            if quotes:
                candidate_quotes.append(_quote_summary(quotes[0], vendor))

    if not candidate_quotes:
        raise ValueError("No current vendor quotes were found for this procurement.")

    # For a procurement-only request there is deliberately no arbitrary target vendor.
    target_vendor = selected_vendor or (vendor_by_id.get(_text(candidate_quotes[0].get("vendor_id"))) if len(candidate_quotes) == 1 else {})
    target_quote = selected_quote if selected_quote else (candidate_quotes[0] if len(candidate_quotes) == 1 else {})
    target_vendor_id = _text(target_vendor.get("id")) or (_text(candidate_quotes[0].get("vendor_id")) if len(candidate_quotes) == 1 else "")

    title = procurement.get("title") or procurement.get("description") or ""
    category = procurement.get("category") or ""
    department = procurement.get("department") or procurement.get("dept") or procurement.get("business_unit") or ""

    # Fetch contract/risk for all candidates. This lets the agent compare vendors when
    # procurement_id alone is supplied.
    candidate_details: List[Dict[str, Any]] = []
    for candidate in candidate_quotes:
        vid = _text(candidate.get("vendor_id"))
        vendor = vendor_by_id.get(vid, {})
        contracts_response = (
            active_client.table("contracts").select("*").eq("vendor_id", vid)
            .order("created_at", desc=True).limit(1).execute()
        )
        contracts = getattr(contracts_response, "data", None) or []
        risk_response = (
            active_client.table("vendor_risk_analysis").select("*").eq("vendor_id", vid)
            .order("created_at", desc=True).limit(1).execute()
        )
        risks = getattr(risk_response, "data", None) or []
        candidate_details.append({
            **candidate,
            "contact_person": vendor.get("contact_person"),
            "email": vendor.get("email"),
            "country": vendor.get("country"),
            "contract": contracts[0] if contracts else {},
            "risk": risks[0] if risks else {},
        })

    target_contract = {}
    target_risk = {}
    if target_vendor_id:
        for candidate in candidate_details:
            if _text(candidate.get("vendor_id")) == target_vendor_id:
                target_contract = candidate.get("contract") or {}
                target_risk = candidate.get("risk") or {}
                break

    return {
        "procurement_id": procurement_id or selected_quote.get("procurement_id"),
        "quote_id": _text(target_quote.get("quote_id") or target_quote.get("id")) or None,
        "vendor_id": target_vendor_id or None,
        "vendor_name": _text(target_vendor.get("vendor_name")) or None,
        "contact_person": target_vendor.get("contact_person"),
        "email": target_vendor.get("email"),
        "phone": target_vendor.get("phone"),
        "country": target_vendor.get("country"),
        "procurement_title": title,
        "product_family": title,
        "department": department,
        "product_category": category,
        "quote_value": _safe_float(target_quote.get("quote_value")),
        "quoted_price": _safe_float(target_quote.get("quote_value")),
        "delivery_days": target_quote.get("delivery_days"),
        "warranty": target_quote.get("warranty_years"),
        "payment_terms": target_quote.get("payment_terms"),
        "support_level": target_quote.get("support_level"),
        "compliance": target_quote.get("compliance_score"),
        "compliance_score": target_quote.get("compliance_score"),
        "quote_information": target_quote,
        "candidate_quotes": candidate_details,
        "contract_information": target_contract,
        "risk_information": target_risk,
        "risk_score": target_risk.get("overall_risk_score") or target_risk.get("risk_score"),
        "multi_vendor_procurement": len(candidate_details) > 1,
    }


async def retrieve_similar_negotiations(
    procurement_context: Optional[Dict[str, Any]] = None,
    vendor_name: Optional[str] = None,
    product_category: Optional[str] = None,
    quote_value: Optional[float] = None,
    client: Any = None,
) -> List[NegotiationHistoryRecord]:
    context = dict(procurement_context or {})
    if vendor_name and not context.get("vendor_name"):
        context["vendor_name"] = vendor_name
    if product_category and not context.get("product_category"):
        context["product_category"] = product_category
    if quote_value is not None and context.get("quote_value") is None:
        context["quote_value"] = quote_value
    if not context:
        raise ValueError("Procurement context is required for RAG retrieval.")

    rows = await retrieve_rag_evidence(context, limit=12, client=client)
    records: List[NegotiationHistoryRecord] = []
    for row in rows:
        clean = {k: v for k, v in row.items() if not k.startswith("_")}
        try:
            records.append(NegotiationHistoryRecord.model_validate(clean))
        except Exception:
            continue
    return records


async def generate_strategy(
    vendor_name: Optional[str] = None,
    product_category: Optional[str] = None,
    quote_value: Optional[float] = None,
    procurement_id: Optional[str] = None,
    quote_id: Optional[str] = None,
    vendor_id: Optional[str] = None,
    procurement_context: Optional[Dict[str, Any]] = None,
    client: Any = None,
) -> NegotiationStrategyResult:
    active_client = client or (supabase_service or supabase)
    try:
        context = procurement_context or await build_procurement_context(
            procurement_id=procurement_id,
            quote_id=quote_id,
            vendor_id=vendor_id,
            client=active_client,
        )

        if vendor_name and not context.get("vendor_name"):
            context["vendor_name"] = vendor_name
        if product_category and not context.get("product_category"):
            context["product_category"] = product_category
        if quote_value is not None and context.get("quote_value") is None:
            context["quote_value"] = quote_value

        strategy_dict = await generate_negotiation_strategy(context)
        historical_rows = strategy_dict.pop("_historical_records", [])
        historical: List[NegotiationHistoryRecord] = []
        for row in historical_rows:
            clean = {k: v for k, v in row.items() if not k.startswith("_")}
            try:
                historical.append(NegotiationHistoryRecord.model_validate(clean))
            except Exception:
                continue

        strategy = NegotiationStrategy.model_validate(strategy_dict)
        result = NegotiationStrategyResult(status="success", strategy=strategy, historical=historical)

        trace = negotiation_agent_module.get_last_strategy_trace()
        await log_agent_execution(
            agent_name="Negotiation Strategy Agent",
            action_type="generate_strategy_fallback" if trace.get("used_fallback") else "generate_strategy",
            input_payload={
                "procurement_id": context.get("procurement_id"),
                "quote_id": context.get("quote_id"),
                "vendor_id": context.get("vendor_id"),
                "vendor_name": context.get("vendor_name"),
                "product_family": context.get("product_family"),
                "product_category": context.get("product_category"),
                "candidate_quote_count": len(context.get("candidate_quotes") or []),
                "retrieved_records": len(historical),
                "tool_calls": trace.get("tool_calls", []),
            },
            output_payload=result.model_dump(),
            reasoning="Autonomous procurement RAG negotiation analysis completed.",
        )
        return result
    except Exception as exc:
        fallback = NegotiationStrategy(
            recommended_strategy="Review the available procurement evidence before committing to a negotiation position.",
            expected_discount_range="Evidence unavailable",
            confidence_score=15.0,
            reasoning=f"The negotiation workflow could not complete reliably: {exc}",
            risks=["Insufficient or unavailable evidence", "Human procurement review required"],
        )
        return NegotiationStrategyResult(status="error", strategy=fallback, historical=[])


async def generate_email(
    vendor_name: Optional[str] = None,
    recommended_strategy: str = "",
    expected_discount_range: str = "",
    procurement_id: Optional[str] = None,
    quote_id: Optional[str] = None,
    vendor_id: Optional[str] = None,
    procurement_context: Optional[Dict[str, Any]] = None,
    client: Any = None,
) -> NegotiationEmail:
    """
    Generate the real vendor-facing negotiation email.

    IMPORTANT:
    There is intentionally NO hard-coded email fallback here.
    If the LLM fails, the actual error is raised instead of silently
    returning the old "Dear Vendor / Our proposed approach..." template.
    """

    context = procurement_context or await build_procurement_context(
        procurement_id=procurement_id,
        quote_id=quote_id,
        vendor_id=vendor_id,
        client=client,
    )

    # Prefer the actual vendor resolved from Supabase.
    resolved_vendor = (
        context.get("vendor_name")
        or vendor_name
        or "Vendor"
    )

    try:
        email_result = await generate_negotiation_email(
            vendor_name=resolved_vendor,
            recommended_strategy=recommended_strategy,
            expected_discount=expected_discount_range,
            procurement_id=procurement_id,
            quote_id=quote_id,
            vendor_id=vendor_id,
        )

        # Agent already returns NegotiationEmail in the normal path,
        # but validation keeps the service boundary safe.
        if isinstance(email_result, NegotiationEmail):
            result = email_result
        else:
            result = NegotiationEmail.model_validate(email_result)

        # Verify that the result is actually vendor-facing and does not
        # contain the internal fallback wording.
        combined = f"{result.subject}\n{result.body}".lower()

        forbidden_internal_phrases = [
            "our proposed approach is",
            "our strategy is",
            "recommended strategy",
            "evidence-supported",
            "evidence supported",
            "target range",
            "rag",
            "confidence score",
            "success score",
            "historical evidence",
            "internal strategy",
            "ai agent",
        ]

        leaked = [
            phrase
            for phrase in forbidden_internal_phrases
            if phrase in combined
        ]

        if leaked:
            raise RuntimeError(
                "LLM generated an internal-facing email instead of a "
                "vendor-facing email. Forbidden content: "
                + ", ".join(leaked)
            )

        placeholder_values = [
            "[vendor name]",
            "[company name]",
            "[project name]",
            "[requirement name]",
            "[your name]",
        ]

        placeholders = [
            value for value in placeholder_values
            if value in combined
        ]

        if placeholders:
            raise RuntimeError(
                "LLM generated an email containing placeholders: "
                + ", ".join(placeholders)
            )

        return result

    except Exception as exc:
        logger.exception(
            "REAL negotiation email generation failed for vendor=%s",
            resolved_vendor,
        )

        # Do NOT return a hard-coded email.
        # The frontend/API must receive the real failure so the underlying
        # Groq/LLM problem can be diagnosed and fixed.
        raise RuntimeError(
            f"Negotiation email generation failed: {str(exc)}"
        ) from exc


async def save_accepted_negotiation(
    procurement_id: Optional[str] = None,
    quote_id: Optional[str] = None,
    vendor_id: Optional[str] = None,
    recommended_strategy: str = "",
    expected_discount_range: str = "",
    generated_email: Optional[Dict[str, str]] = None,
    risk_score: Optional[float] = None,
    vendor_rank: Optional[float] = None,
    procurement_context: Optional[Dict[str, Any]] = None,
    client: Any = None,
) -> Dict[str, Any]:
    active_client = client or (supabase_service or supabase)
    context = procurement_context or await build_procurement_context(
        procurement_id=procurement_id,
        quote_id=quote_id,
        vendor_id=vendor_id,
        client=active_client,
    )

    record = {
        "vendor_id": context.get("vendor_id"),
        "vendor_name": context.get("vendor_name"),
        "product_category": context.get("product_category"),
        "initial_quote_value": context.get("quote_value"),
        "strategy_used": recommended_strategy,
        "negotiation_date": datetime.utcnow().date().isoformat(),
        "outcome": "accepted",
        "negotiation_status": "accepted",
        "generated_email": generated_email or {},
        "reasoning": "Human approved the AI-generated negotiation strategy for use.",
        "confidence_score": None,
        "user_approved": True,
        "is_baseline": False,
        "notes": "Accepted via negotiation workflow. Actual commercial outcome is not yet known.",
        "success_score": None,
        "discount_requested": None,
        "discount_received": None,
        "final_negotiated_value": None,
        "negotiation_rounds": None,
    }

    response = active_client.table("negotiation_history").insert(record).execute()
    data = getattr(response, "data", None) or []
    if not data:
        raise RuntimeError("Negotiation approval could not be saved.")

    return {
        "status": "success",
        "record_id": data[0].get("id"),
        "message": "Strategy approval saved. It will not be treated as a successful negotiation until an actual commercial outcome is recorded.",
    }
