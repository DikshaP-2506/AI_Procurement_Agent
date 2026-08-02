from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import math
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

CATEGORY_MATCH_WEIGHT = 25.0
DEPARTMENT_MATCH_WEIGHT = 15.0
SUCCESS_SCORE_WEIGHT = 0.35
QUOTE_SIMILARITY_WEIGHT = 20.0
OUTCOME_WEIGHT = 10.0
EFFICIENCY_WEIGHT = 5.0
VENDOR_MATCH_WEIGHT = 5.0
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


def _normalize_optional_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


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
    vendor_id: Optional[str] = None,
    client: Any = None,
) -> Dict[str, Any]:
    """Build a complete procurement context object from existing procurement pipeline data."""
    active_client = client or (supabase_service or supabase)
    if not procurement_id and not quote_id and not vendor_id:
        raise ValueError("A procurement_id, quote_id, or vendor_id is required to build negotiation context.")

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

    if vendor_id:
        vendor_resp = active_client.table("vendors").select("*").eq("id", vendor_id).execute()
        vendor_rows = vendor_resp.data if getattr(vendor_resp, "data", None) else []
        if vendor_rows:
            vendor = vendor_rows[0]

    if not vendor and quote_id:
        quote_resp = active_client.table("vendor_quotes").select("*").eq("id", quote_id).execute()
        quote_rows = quote_resp.data if getattr(quote_resp, "data", None) else []
        if quote_rows:
            quote = quote_rows[0]
            resolved_quote_vendor_id = quote.get("vendor_id")
            if resolved_quote_vendor_id:
                vendor_resp = active_client.table("vendors").select("*").eq("id", resolved_quote_vendor_id).execute()
                vendor_rows = vendor_resp.data if getattr(vendor_resp, "data", None) else []
                if vendor_rows:
                    vendor = vendor_rows[0]

    if not vendor and procurement_id:
        vendor_resp = active_client.table("vendors").select("*").eq("procurement_id", procurement_id).execute()
        vendor_rows = vendor_resp.data if getattr(vendor_resp, "data", None) else []
        if vendor_rows:
            vendor = vendor_rows[0]
            if len(vendor_rows) > 1:
                selected_vendor = next(
                    (row for row in vendor_rows if _normalize_text(row.get("vendor_name"))),
                    vendor_rows[0],
                )
                vendor = selected_vendor

    if not vendor:
        raise ValueError("No vendor record found for the provided procurement_id, quote_id, or vendor_id")

    resolved_vendor_id = vendor.get("id") or quote.get("vendor_id")
    if not resolved_vendor_id:
        raise ValueError("No vendor_id could be resolved from the vendor record")

    if not _normalize_text(vendor.get("vendor_name")):
        raise ValueError(f"Vendor record {resolved_vendor_id} is missing a vendor_name")

    quote_resp = active_client.table("vendor_quotes").select("*").eq("vendor_id", resolved_vendor_id).execute()
    quote_rows = quote_resp.data if getattr(quote_resp, "data", None) else []
    if not quote_rows:
        raise ValueError(f"No quote record found for vendor_id {resolved_vendor_id}")
    quote = quote_rows[0]

    contract_resp = active_client.table("contracts").select("*").eq("vendor_id", resolved_vendor_id).execute()
    contract_rows = contract_resp.data if getattr(contract_resp, "data", None) else []
    if not contract_rows:
        raise ValueError(f"No contract record found for vendor_id {resolved_vendor_id}")
    contract = contract_rows[0]

    risk_resp = active_client.table("vendor_risk_analysis").select("*").eq("vendor_id", resolved_vendor_id).execute()
    risk_rows = risk_resp.data if getattr(risk_resp, "data", None) else []
    if not risk_rows:
        raise ValueError(f"No vendor risk analysis found for vendor_id {resolved_vendor_id}")
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
        "payment_terms": contract.get("payment_terms") or quote.get("payment_terms"),
        "support_details": contract.get("support_details") or quote.get("support_level"),
    }

    risk_information = {
        "vendor_id": resolved_vendor_id,
        "risk_score": risk_row.get("overall_risk_score") or risk_row.get("risk_score"),
        "risk_level": risk_row.get("risk_level") or risk_row.get("final_risk_level"),
        "alerts": risk_row.get("alerts") or [],
        "prediction_reason": risk_row.get("prediction_reason"),
        "delay_probability": risk_row.get("delay_probability"),
    }

    return {
        "procurement_id": procurement_id,
        "quote_id": quote_id,
        "vendor_id": resolved_vendor_id,
        "vendor_name": vendor.get("vendor_name"),
        "contact_person": vendor.get("contact_person"),
        "email": vendor.get("email"),
        "phone": vendor.get("phone"),
        "country": vendor.get("country"),
        "procurement_title": procurement.get("title"),
        "department": procurement.get("department") or procurement.get("dept") or procurement.get("business_unit") or procurement.get("team"),
        "product_category": procurement.get("category") or procurement.get("title") or "Unknown Category",
        "quoted_price": quote_value,
        "quote_value": quote_value,
        "delivery_days": delivery_days if delivery_days > 0 else None,
        "warranty": warranty if warranty > 0 else None,
        "support_details": contract_information.get("support_details") or quote.get("support_level"),
        "support_level": quote.get("support_level") or contract_information.get("support_details"),
        "payment_terms": quote.get("payment_terms") or contract_information.get("payment_terms"),
        "compliance": compliance if compliance > 0 else None,
        "compliance_score": compliance if compliance > 0 else None,
        "contract_information": contract_information,
        "risk_information": risk_information,
        "risk_score": risk_information.get("risk_score"),
        "vendor_rank": None,
    }


async def retrieve_similar_negotiations(
    procurement_context: Optional[Dict[str, Any]] = None,
    vendor_name: Optional[str] = None,
    product_category: Optional[str] = None,
    quote_value: Optional[float] = None,
    client: Any = None,
) -> List[NegotiationHistoryRecord]:
    """Retrieve the highest-ranked historical negotiation cases from negotiation_history."""
    active_client = client or (supabase_service or supabase)

    current_context = procurement_context or {}
    vendor_name = current_context.get("vendor_name") or vendor_name
    product_category = current_context.get("product_category") or current_context.get("procurement_title") or product_category
    quote_value = current_context.get("quote_value") or current_context.get("quoted_price") or quote_value
    vendor_id = current_context.get("vendor_id")
    department = current_context.get("department") or current_context.get("procurement_department")

    try:
        query = active_client.table("negotiation_history").select("*")
        if product_category and product_category != "Unknown Category":
            query = query.eq("product_category", product_category)
        resp = query.execute()
        rows = resp.data if getattr(resp, "data", None) else []
        if not rows and product_category and product_category != "Unknown Category":
            fallback_resp = active_client.table("negotiation_history").select("*").execute()
            rows = fallback_resp.data if getattr(fallback_resp, "data", None) else []

        if not rows:
            return []

        vendor_lookup: Dict[str, str] = {}
        vendor_ids = [str(row.get("vendor_id")) for row in rows if row.get("vendor_id")]
        seen_vendor_ids = set()
        for vendor_id_value in vendor_ids:
            if vendor_id_value in seen_vendor_ids:
                continue
            seen_vendor_ids.add(vendor_id_value)
            try:
                vendor_resp = active_client.table("vendors").select("*").eq("id", vendor_id_value).execute()
                vendor_rows = getattr(vendor_resp, "data", None) or []
                if vendor_rows:
                    vendor_name_value = str(vendor_rows[0].get("vendor_name") or "").strip()
                    if vendor_name_value:
                        vendor_lookup[vendor_id_value] = vendor_name_value
            except Exception:
                continue

        normalized_rows = []
        for row in rows:
            normalized_row = dict(row)
            if _normalize_optional_bool(normalized_row.get("is_baseline")):
                continue
            vendor_id_value = normalized_row.get("vendor_id")
            if not normalized_row.get("vendor_name") and vendor_id_value:
                resolved_vendor_name = vendor_lookup.get(str(vendor_id_value))
                if resolved_vendor_name:
                    normalized_row["vendor_name"] = resolved_vendor_name
            normalized_rows.append(normalized_row)

        records: List[NegotiationHistoryRecord] = [NegotiationHistoryRecord.model_validate(row) for row in normalized_rows]

        scored = []
        for record in records:
            score = 0.0
            record_department = None
            if isinstance(record, NegotiationHistoryRecord):
                record_department = None
            else:
                record_department = None

            if product_category and record.product_category:
                score += _text_similarity(product_category, record.product_category) * CATEGORY_MATCH_WEIGHT
            else:
                score += 0.0

            if department:
                record_department = None
                if hasattr(record, "model_dump"):
                    record_department = None
                raw_department = getattr(record, "department", None)
                if raw_department is None:
                    raw_department = getattr(record, "procurement_department", None)
                if raw_department:
                    record_department = raw_department
                if record_department:
                    score += _text_similarity(department, record_department) * DEPARTMENT_MATCH_WEIGHT

            score += _value_similarity(quote_value, record.initial_quote_value) * QUOTE_SIMILARITY_WEIGHT

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
                    score += EFFICIENCY_WEIGHT
            except Exception:
                pass

            if record.discount_received is not None:
                score += max(0.0, 1.0 - min(abs(_safe_float(record.discount_received) / 100.0), 1.0)) * 2.0

            if record.strategy_used:
                score += 1.0

            if vendor_id and record.vendor_id and str(vendor_id) == str(record.vendor_id):
                score += VENDOR_MATCH_WEIGHT
            elif record.vendor_name and vendor_name and record.vendor_name.lower() == vendor_name.lower():
                score += VENDOR_MATCH_WEIGHT
            else:
                score += _text_similarity(vendor_name, record.vendor_name) * VENDOR_MATCH_WEIGHT * 0.2

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
    vendor_id: Optional[str] = None,
    procurement_context: Optional[Dict[str, Any]] = None,
    client: Any = None,
) -> NegotiationStrategyResult:
    """Retrieve similar negotiations and call the negotiation strategy agent."""
    try:
        current_context = procurement_context
        if not current_context:
            try:
                current_context = await build_procurement_context(
                    procurement_id=procurement_id,
                    quote_id=quote_id,
                    vendor_id=vendor_id,
                    client=client,
                )
            except Exception as context_error:
                current_context = {
                    "vendor_name": vendor_name or "Unknown Vendor",
                    "product_category": product_category or "Unknown Category",
                    "quote_value": quote_value,
                    "procurement_id": procurement_id,
                    "quote_id": quote_id,
                    "vendor_id": vendor_id,
                    "department": None,
                    "error": str(context_error),
                }

        if not current_context.get("product_category") and product_category:
            current_context["product_category"] = product_category
        if not current_context.get("quote_value") and quote_value is not None:
            current_context["quote_value"] = quote_value
        if not current_context.get("vendor_name") and vendor_name:
            current_context["vendor_name"] = vendor_name

        historical = await retrieve_similar_negotiations(current_context, client=client)

        prompt_context = {
            "current_procurement_context": current_context,
            "historical_negotiations": [_format_negotiation_context(record) for record in historical],
        }
        if not historical:
            prompt_context["historical_negotiations"] = [
                "No historical negotiation records were found for the current category, so the strategy is based on the current procurement context only."
            ]
        historical_context = [_format_negotiation_context(record) for record in historical]
        strategy_dict = generate_negotiation_strategy(prompt_context, historical_context)
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
        fallback_strategy = NegotiationStrategy.model_validate({
            "recommended_strategy": "Leverage cross-department volume, commercial benchmarking, and standardized contract terms to achieve targeted pricing alignment.",
            "expected_discount_range": "5% - 10%",
            "confidence_score": 70,
            "reasoning": f"A safe fallback strategy was used because the negotiation workflow encountered an error: {str(e)}",
            "risks": ["Vendor may resist pricing adjustments", "Commercial review may require escalation"],
        })
        return NegotiationStrategyResult(
            status="success",
            strategy=fallback_strategy,
            historical=[],
        )


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
    """Call the email generator agent and log the result."""
    try:
        current_context = procurement_context
        if not current_context:
            current_context = await build_procurement_context(
                procurement_id=procurement_id,
                quote_id=quote_id,
                vendor_id=vendor_id,
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
        fallback_email = NegotiationEmail.model_validate({
            "subject": "Commercial Proposal Review Request",
            "body": (
                f"Dear {vendor_name or 'Vendor'},\n\n"
                "We would like to discuss the commercial terms of the current proposal and explore opportunities for improved pricing and value. "
                f"Our proposed approach is to {recommended_strategy or 'review the proposal in detail'} with a target discount range of {expected_discount_range or '5% - 10%'}. "
                "We value the relationship and believe there is an opportunity to align on a mutually beneficial outcome.\n\n"
                "Regards,\nProcurement Team"
            ),
        })
        return fallback_email


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
    """Persist an accepted negotiation strategy as organizational procurement knowledge."""
    active_client = client or (supabase_service or supabase)
    current_context = procurement_context or await build_procurement_context(
        procurement_id=procurement_id,
        quote_id=quote_id,
        vendor_id=vendor_id,
        client=active_client,
    )

    email_payload = generated_email or {}
    reasoning_text = ""
    if isinstance(email_payload, dict):
        reasoning_text = email_payload.get("body") or ""

    record = {
        "procurement_id": current_context.get("procurement_id") or procurement_id,
        "vendor_id": current_context.get("vendor_id"),
        "vendor_name": current_context.get("vendor_name"),
        "product_category": current_context.get("product_category"),
        "initial_quote_value": current_context.get("quote_value") or current_context.get("quoted_price"),
        "delivery_days": current_context.get("delivery_days"),
        "payment_terms": current_context.get("payment_terms"),
        "warranty_years": current_context.get("warranty"),
        "support_level": current_context.get("support_level") or current_context.get("support_details"),
        "compliance_score": current_context.get("compliance") or current_context.get("compliance_score"),
        "risk_score": risk_score if risk_score is not None else current_context.get("risk_score"),
        "vendor_rank": vendor_rank,
        "recommended_strategy": recommended_strategy,
        "expected_discount_range": expected_discount_range,
        "generated_email": email_payload,
        "reasoning": reasoning_text,
        "confidence_score": None,
        "strategy_used": recommended_strategy,
        "outcome": "accepted",
        "status": "accepted",
        "negotiation_status": "accepted",
        "user_approved": True,
        "is_baseline": False,
        "notes": "Accepted via negotiation workflow",
        "negotiation_date": datetime.utcnow().date().isoformat(),
        "created_at": datetime.utcnow().isoformat(),
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
