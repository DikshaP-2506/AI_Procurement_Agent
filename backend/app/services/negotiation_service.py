from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from ..supabase_client import supabase, supabase_service
from ..agents.negotiation_agent import (
    generate_negotiation_strategy,
    generate_negotiation_email,
)
from ..agents import negotiation_agent as negotiation_agent_module
from .audit_service import log_agent_execution
from ..models.negotiation import (
    NegotiationHistoryRecord,
    NegotiationStrategy,
    NegotiationEmail,
    NegotiationStrategyResult,
)

VENDOR_MATCH_WEIGHT = 50.0
SUCCESS_SCORE_WEIGHT = 0.3
QUOTE_SIMILARITY_WEIGHT = 20.0
OUTCOME_WEIGHT = 10.0
ROUND_WEIGHT = 5.0
DELIVERY_MATCH_WEIGHT = 8.0
WARRANTY_MATCH_WEIGHT = 4.0
PAYMENT_TERMS_WEIGHT = 4.0
SUPPORT_LEVEL_WEIGHT = 3.0
COMPLIANCE_WEIGHT = 6.0


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _text_similarity(value_a: Any, value_b: Any) -> float:
    left = _normalize_text(value_a).lower()
    right = _normalize_text(value_b).lower()
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if left in right or right in left:
        return 0.75
    return 0.0


def _value_similarity(current_value: Any, historical_value: Any, fallback: float = 0.0) -> float:
    current = _safe_float(current_value, 0.0)
    historical = _safe_float(historical_value, 0.0)
    if current <= 0 and historical <= 0:
        return 0.0
    base = max(abs(current), abs(historical), 1.0)
    diff = abs(current - historical)
    return max(0.0, 1.0 - min(diff / base, 1.0))


def _format_negotiation_context(record: NegotiationHistoryRecord) -> str:
    """Format a concise procurement summary for LLM consumption."""
    discount_received = f"{record.discount_received}%" if record.discount_received is not None else "N/A"
    outcome = record.outcome or "Unknown"
    success_score = record.success_score if record.success_score is not None else "N/A"
    strategy_used = record.strategy_used or "N/A"
    quote_value = record.initial_quote_value if record.initial_quote_value is not None else "N/A"

    return (
        f"Vendor: {record.vendor_name or 'Unknown'}\n"
        f"Category: {record.product_category or 'Unknown'}\n"
        f"Quote Value: {quote_value}\n"
        f"Strategy: {strategy_used}\n"
        f"Discount Received: {discount_received}\n"
        f"Outcome: {outcome}\n"
        f"Success Score: {success_score}"
    )


def _build_strategy_candidates(records: List[NegotiationHistoryRecord]) -> List[str]:
    """Extract concise negotiation patterns for audit logging."""
    candidates: List[str] = []
    for record in records[:3]:
        strategy = record.strategy_used or "Unknown"
        outcome = record.outcome or "Unknown"
        success_score = record.success_score if record.success_score is not None else "N/A"
        candidates.append(f"{record.vendor_name or 'Unknown'} | {strategy} | {outcome} | Score {success_score}")
    return candidates


async def build_procurement_context(
    procurement_id: Optional[str] = None,
    quote_id: Optional[str] = None,
    client: Any = None,
) -> Dict[str, Any]:
    """Build a single procurement context object from existing procurement pipeline data."""
    active_client = client or (supabase_service or supabase)
    if not procurement_id and not quote_id:
        raise ValueError("A procurement_id or quote_id is required to build negotiation context.")

    procurement = {}
    vendor = {}
    quote = {}
    contract = {}
    risk_row = {}

    if procurement_id:
        procurement_resp = active_client.table("procurements").select("*").eq("id", procurement_id).execute()
        procurement_rows = procurement_resp.data if getattr(procurement_resp, "data", None) else []
        if procurement_rows:
            procurement = procurement_rows[0]

    if quote_id:
        quote_resp = active_client.table("vendor_quotes").select("*").eq("id", quote_id).execute()
        quote_rows = quote_resp.data if getattr(quote_resp, "data", None) else []
        if quote_rows:
            quote = quote_rows[0]
            vendor_id = quote.get("vendor_id")
            if vendor_id:
                vendor_resp = active_client.table("vendors").select("*").eq("id", vendor_id).execute()
                vendor_rows = vendor_resp.data if getattr(vendor_resp, "data", None) else []
                if vendor_rows:
                    vendor = vendor_rows[0]
                    if not procurement_id and vendor.get("procurement_id"):
                        procurement_id = vendor.get("procurement_id")
                        procurement_resp = active_client.table("procurements").select("*").eq("id", procurement_id).execute()
                        procurement_rows = procurement_resp.data if getattr(procurement_resp, "data", None) else []
                        if procurement_rows:
                            procurement = procurement_rows[0]

    if not vendor and procurement_id:
        vendor_resp = active_client.table("vendors").select("*").eq("procurement_id", procurement_id).execute()
        vendor_rows = vendor_resp.data if getattr(vendor_resp, "data", None) else []
        if vendor_rows:
            vendor = vendor_rows[0]

    vendor_id = vendor.get("id") or quote.get("vendor_id")
    if vendor_id:
        quote_resp = active_client.table("vendor_quotes").select("*").eq("vendor_id", vendor_id).execute()
        quote_rows = quote_resp.data if getattr(quote_resp, "data", None) else []
        if quote_rows:
            quote = quote_rows[0]

    if vendor_id:
        contract_resp = active_client.table("contracts").select("*").eq("vendor_id", vendor_id).execute()
        contract_rows = contract_resp.data if getattr(contract_resp, "data", None) else []
        if contract_rows:
            contract = contract_rows[0]

    if vendor_id:
        risk_resp = active_client.table("vendor_risk_analysis").select("*").eq("vendor_id", vendor_id).execute()
        risk_rows = risk_resp.data if getattr(risk_resp, "data", None) else []
        if risk_rows:
            risk_row = risk_rows[0]

    quote_value = _safe_float(quote.get("price") or quote.get("price_usd") or quote.get("normalized_price"), 0.0)
    delivery_days = _safe_int(quote.get("delivery_days"), 0)
    warranty = _safe_float(quote.get("warranty_years") or quote.get("warranty") or quote.get("warranty_period"), 0.0)
    compliance = _safe_float(quote.get("compliance_score"), 0.0)

    contract_information = {
        "contract_name": contract.get("contract_name") or quote.get("contract_name"),
        "start_date": contract.get("start_date"),
        "end_date": contract.get("end_date"),
        "renewal_date": contract.get("renewal_date"),
        "auto_renewal": contract.get("auto_renewal"),
        "notice_period_days": contract.get("notice_period_days"),
    }

    return {
        "procurement_id": procurement_id,
        "quote_id": quote_id,
        "vendor_id": vendor_id,
        "vendor_name": vendor.get("vendor_name") or "Unknown Vendor",
        "product_category": procurement.get("category") or procurement.get("title") or "Unknown Category",
        "quote_value": quote_value,
        "delivery_days": delivery_days if delivery_days > 0 else None,
        "warranty": warranty if warranty > 0 else None,
        "payment_terms": quote.get("payment_terms") or contract.get("payment_terms"),
        "support_details": quote.get("support_level") or contract.get("support_details"),
        "compliance": compliance if compliance > 0 else None,
        "contract_information": contract_information,
        "risk_score": risk_row.get("overall_risk_score") or risk_row.get("risk_score"),
        "vendor_rank": None,
    }


async def retrieve_similar_negotiations(
    procurement_context: Optional[Dict[str, Any]] = None,
    vendor_name: Optional[str] = None,
    product_category: Optional[str] = None,
    quote_value: Optional[float] = None,
    client: Any = None,
) -> List[NegotiationHistoryRecord]:
    """Retrieve top 5 similar procurement cases from `negotiation_history`."""
    active_client = client or (supabase_service or supabase)

    current_context = procurement_context or {}
    vendor_name = current_context.get("vendor_name") or vendor_name
    product_category = current_context.get("product_category") or product_category
    quote_value = current_context.get("quote_value") or quote_value

    try:
        query = active_client.table("negotiation_history").select("*")
        if product_category:
            query = query.eq("product_category", product_category)
        resp = query.execute()
        rows = resp.data if getattr(resp, "data", None) else []

        if not rows:
            return []

        records: List[NegotiationHistoryRecord] = [NegotiationHistoryRecord.model_validate(row) for row in rows]

        scored = []
        for record in records:
            score = 0.0
            if record.vendor_name and vendor_name and record.vendor_name.lower() == vendor_name.lower():
                score += VENDOR_MATCH_WEIGHT
            else:
                score += _text_similarity(vendor_name, record.vendor_name) * VENDOR_MATCH_WEIGHT * 0.5

            if product_category and record.product_category:
                score += _text_similarity(product_category, record.product_category) * QUOTE_SIMILARITY_WEIGHT * 0.6
            else:
                score += 0.0

            score += _value_similarity(quote_value, record.initial_quote_value) * QUOTE_SIMILARITY_WEIGHT
            score += _value_similarity(current_context.get("delivery_days"), record.negotiation_rounds or None) * 0.0
            score += _value_similarity(current_context.get("delivery_days"), getattr(record, "negotiation_rounds", None)) * 0.0

            delivery_similarity = _value_similarity(current_context.get("delivery_days"), getattr(record, "negotiation_rounds", None))
            score += delivery_similarity * DELIVERY_MATCH_WEIGHT

            warranty_similarity = _value_similarity(current_context.get("warranty"), getattr(record, "negotiation_rounds", None))
            score += warranty_similarity * WARRANTY_MATCH_WEIGHT

            payment_similarity = _text_similarity(current_context.get("payment_terms"), getattr(record, "strategy_used", None))
            score += payment_similarity * PAYMENT_TERMS_WEIGHT

            support_similarity = _text_similarity(current_context.get("support_details"), getattr(record, "strategy_used", None))
            score += support_similarity * SUPPORT_LEVEL_WEIGHT

            compliance_similarity = _value_similarity(current_context.get("compliance"), record.success_score) * 0.0
            score += compliance_similarity * COMPLIANCE_WEIGHT

            success_score = record.success_score or 0
            try:
                ss = float(success_score)
            except Exception:
                ss = 0.0
            score += ss * SUCCESS_SCORE_WEIGHT

            outcome = (record.outcome or "").lower()
            if outcome in ["success", "successful", "won"]:
                score += OUTCOME_WEIGHT

            try:
                rounds = int(record.negotiation_rounds or 0)
                if rounds <= 2 and rounds > 0:
                    score += ROUND_WEIGHT
            except Exception:
                pass

            scored.append((score, record))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [item[1] for item in scored[:5]]
        return top

    except Exception as e:
        raise Exception(f"Failed to retrieve negotiations: {str(e)}")


async def generate_strategy(
    vendor_name: Optional[str] = None,
    product_category: Optional[str] = None,
    quote_value: Optional[float] = None,
    procurement_id: Optional[str] = None,
    quote_id: Optional[str] = None,
    procurement_context: Optional[Dict[str, Any]] = None,
    client: Any = None,
) -> NegotiationStrategyResult:
    """Retrieve similar negotiations and call the negotiation strategy agent."""
    try:
        current_context = procurement_context or await build_procurement_context(
            procurement_id=procurement_id,
            quote_id=quote_id,
            client=client,
        )
        historical = await retrieve_similar_negotiations(current_context, client=client)

        historical_context = [_format_negotiation_context(record) for record in historical]
        strategy_dict = generate_negotiation_strategy(current_context, historical_context)
        strategy = NegotiationStrategy.model_validate(strategy_dict)
        result = NegotiationStrategyResult(
            status="success",
            strategy=strategy,
            historical=historical,
        )

        trace = negotiation_agent_module.get_last_strategy_trace()
        if trace.get("used_fallback"):
            await log_agent_execution(
                agent_name="Negotiation Strategy Agent",
                action_type="generate_strategy_failure",
                input_payload={
                    "procurement_id": procurement_id,
                    "quote_id": quote_id,
                    "current_context": current_context,
                    "retrieved_records_count": len(historical),
                    "top_strategy_candidates": _build_strategy_candidates(historical),
                    "raw_llm_response": trace.get("raw_llm_response", ""),
                    "cleaned_response": trace.get("cleaned_response", ""),
                    "fallback_reason": trace.get("fallback_reason", ""),
                },
                output_payload=json.loads(result.model_dump_json()),
                reasoning=f"Fallback strategy used because {trace.get('fallback_reason', 'the model response was invalid')}.",
            )

        await log_agent_execution(
            agent_name="Negotiation Strategy Agent",
            action_type="generate_strategy",
            input_payload={
                "procurement_id": procurement_id,
                "quote_id": quote_id,
                "current_context": current_context,
                "retrieved_records_count": len(historical),
                "top_strategy_candidates": _build_strategy_candidates(historical),
            },
            output_payload=json.loads(result.model_dump_json()),
            reasoning="Generated negotiation strategy based on structured historical procurement patterns."
        )

        return result
    except Exception as e:
        raise Exception(f"Failed to generate strategy: {str(e)}")


async def generate_email(
    vendor_name: Optional[str] = None,
    recommended_strategy: str = "",
    expected_discount_range: str = "",
    procurement_id: Optional[str] = None,
    quote_id: Optional[str] = None,
    procurement_context: Optional[Dict[str, Any]] = None,
    client: Any = None,
) -> NegotiationEmail:
    """Call the email generator agent and log the result."""
    try:
        current_context = procurement_context or await build_procurement_context(
            procurement_id=procurement_id,
            quote_id=quote_id,
            client=client,
        )
        resolved_vendor = current_context.get("vendor_name") or vendor_name or "Vendor"
        email_dict = generate_negotiation_email(
            resolved_vendor,
            recommended_strategy,
            expected_discount_range,
        )
        email = NegotiationEmail.model_validate(email_dict)

        trace = negotiation_agent_module.get_last_email_trace()
        if trace.get("used_fallback"):
            await log_agent_execution(
                agent_name="Negotiation Strategy Agent",
                action_type="generate_email_failure",
                input_payload={
                    "procurement_id": procurement_id,
                    "quote_id": quote_id,
                    "vendor_name": resolved_vendor,
                    "recommended_strategy": recommended_strategy,
                    "expected_discount_range": expected_discount_range,
                    "raw_llm_response": trace.get("raw_llm_response", ""),
                    "cleaned_response": trace.get("cleaned_response", ""),
                    "fallback_reason": trace.get("fallback_reason", ""),
                },
                output_payload=email.model_dump(),
                reasoning=f"Fallback email used because {trace.get('fallback_reason', 'the model response was invalid')}.",
            )

        await log_agent_execution(
            agent_name="Negotiation Strategy Agent",
            action_type="generate_email",
            input_payload={
                "procurement_id": procurement_id,
                "quote_id": quote_id,
                "vendor_name": resolved_vendor,
                "recommended_strategy": recommended_strategy,
                "expected_discount_range": expected_discount_range,
            },
            output_payload=email.model_dump(),
            reasoning="Generated procurement negotiation outreach email based on the recommended negotiation strategy."
        )

        return email
    except Exception as e:
        raise Exception(f"Failed to generate email: {str(e)}")


async def save_accepted_negotiation(
    procurement_id: Optional[str] = None,
    quote_id: Optional[str] = None,
    recommended_strategy: str = "",
    expected_discount_range: str = "",
    generated_email: Optional[Dict[str, str]] = None,
    risk_score: Optional[float] = None,
    vendor_rank: Optional[float] = None,
    procurement_context: Optional[Dict[str, Any]] = None,
    client: Any = None,
) -> Dict[str, Any]:
    """Persist an accepted negotiation strategy as organizational procurement knowledge."""
    active_client = client or (supabase_service or supabase)
    current_context = procurement_context or await build_procurement_context(
        procurement_id=procurement_id,
        quote_id=quote_id,
        client=active_client,
    )

    record = {
        "procurement_id": current_context.get("procurement_id") or procurement_id,
        "vendor_id": current_context.get("vendor_id"),
        "vendor_name": current_context.get("vendor_name"),
        "product_category": current_context.get("product_category"),
        "initial_quote_value": current_context.get("quote_value"),
        "delivery_days": current_context.get("delivery_days"),
        "payment_terms": current_context.get("payment_terms"),
        "warranty_years": current_context.get("warranty"),
        "support_level": current_context.get("support_details"),
        "compliance_score": current_context.get("compliance"),
        "risk_score": risk_score if risk_score is not None else current_context.get("risk_score"),
        "vendor_rank": vendor_rank,
        "recommended_strategy": recommended_strategy,
        "expected_discount_range": expected_discount_range,
        "generated_email": generated_email or {},
        "strategy_used": recommended_strategy,
        "outcome": "accepted",
        "status": "accepted",
        "notes": "Accepted via negotiation workflow",
        "negotiation_date": datetime.utcnow().date().isoformat(),
        "success_score": 100,
    }

    try:
        response = active_client.table("negotiation_history").insert(record).execute()
        if not getattr(response, "data", None):
            raise Exception("No negotiation record returned from insert")
        return {"status": "success", "record_id": response.data[0].get("id")}
    except Exception as exc:
        try:
            fallback_record = {
                "vendor_id": current_context.get("vendor_id"),
                "vendor_name": current_context.get("vendor_name"),
                "product_category": current_context.get("product_category"),
                "initial_quote_value": current_context.get("quote_value"),
                "strategy_used": recommended_strategy,
                "outcome": "accepted",
                "notes": "Accepted via negotiation workflow",
                "negotiation_date": datetime.utcnow().date().isoformat(),
            }
            response = active_client.table("negotiation_history").insert(fallback_record).execute()
            if not getattr(response, "data", None):
                raise Exception("Fallback insert failed")
            return {"status": "success", "record_id": response.data[0].get("id"), "fallback": True}
        except Exception as fallback_error:
            raise Exception(f"Failed to save accepted negotiation strategy: {exc} | {fallback_error}")
