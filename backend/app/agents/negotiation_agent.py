import os
import json
from typing import Dict, Any, List

from langchain_groq import ChatGroq

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TRACE_NEGOTIATION_EMAIL = os.getenv("NEGOTIATION_EMAIL_TRACE", "1") == "1"

_LAST_STRATEGY_TRACE: Dict[str, Any] = {}
_LAST_EMAIL_TRACE: Dict[str, Any] = {}


def get_last_strategy_trace() -> Dict[str, Any]:
    """Return the most recent strategy trace for auditing and debugging."""
    return dict(_LAST_STRATEGY_TRACE)


def get_last_email_trace() -> Dict[str, Any]:
    """Return the most recent email trace for auditing and debugging."""
    return dict(_LAST_EMAIL_TRACE)


def _store_strategy_trace(**kwargs: Any) -> None:
    _LAST_STRATEGY_TRACE.clear()
    _LAST_STRATEGY_TRACE.update(kwargs)


def _store_email_trace(**kwargs: Any) -> None:
    _LAST_EMAIL_TRACE.clear()
    _LAST_EMAIL_TRACE.update(kwargs)


def _fallback_strategy(reason: str) -> Dict[str, Any]:
    return {
        "recommended_strategy": "Leverage cross-department volume, commercial benchmarking, and standardized contract terms to achieve targeted pricing alignment.",
        "expected_discount_range": "5% - 10%",
        "confidence_score": 70,
        "reasoning": f"Strategy formulated based on available structured negotiation data ({reason}).",
        "risks": ["Vendor may resist pricing adjustments", "Commercial review may require escalation"],
    }


def _fallback_email(vendor_name: str, recommended_strategy: str, expected_discount: str) -> Dict[str, str]:
    subject = "Commercial Proposal Review Request"
    body = (
        f"Dear {vendor_name or 'Vendor'},\n\n"
        "We would like to discuss the commercial terms of the current proposal and explore opportunities for improved pricing and value. "
        f"Our proposed approach is to {recommended_strategy or 'review the proposal in detail'} with a target discount range of {expected_discount or '5% - 10%'}. "
        "We value the relationship and believe there is an opportunity to align on a mutually beneficial outcome.\n\n"
        "Regards,\nProcurement Team"
    )
    return {"subject": subject, "body": body}


def _normalize_confidence_score(value: Any) -> float:
    try:
        score = float(value)
    except Exception:
        return 70.0

    if 0 <= score <= 1:
        score *= 100.0

    if score < 0:
        score = 0.0
    if score > 100:
        score = 100.0
    return round(score, 2)


def _clean_response_text(response_text: str) -> str:
    cleaned = response_text.strip()
    if "```" in cleaned:
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    return cleaned


def _validate_strategy_payload(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize negotiation strategy output into the expected project schema."""
    risks = parsed.get("risks", [])
    if not isinstance(risks, list):
        risks = [str(risks)] if risks else []

    confidence_score = _normalize_confidence_score(parsed.get("confidence_score", 0))

    recommended_strategy = str(parsed.get("recommended_strategy", "")).strip()
    expected_discount_range = str(parsed.get("expected_discount_range", "")).strip()
    reasoning = str(parsed.get("reasoning", "")).strip()

    return {
        "recommended_strategy": recommended_strategy,
        "expected_discount_range": expected_discount_range,
        "confidence_score": confidence_score,
        "reasoning": reasoning,
        "risks": [str(risk) for risk in risks if str(risk).strip()],
    }


def _validate_email_payload(parsed: Dict[str, Any]) -> Dict[str, str]:
    """Normalize email output into the expected project schema."""
    subject = str(parsed.get("subject", "")).strip()
    body = str(parsed.get("body", "")).strip()
    return {
        "subject": subject,
        "body": body,
    }


def _make_strategy_prompt(current_negotiation: Dict[str, Any], historical: List[Dict[str, Any]]) -> str:
    context = current_negotiation.get("current_procurement_context") if isinstance(current_negotiation, dict) and "current_procurement_context" in current_negotiation else current_negotiation

    vendor_name = context.get("vendor_name") if isinstance(context, dict) else None
    product_category = context.get("product_category") if isinstance(context, dict) else None
    quote_value = context.get("quote_value") if isinstance(context, dict) else None
    delivery_days = context.get("delivery_days") if isinstance(context, dict) else None
    warranty = context.get("warranty") if isinstance(context, dict) else None
    payment_terms = context.get("payment_terms") if isinstance(context, dict) else None
    support_details = context.get("support_details") if isinstance(context, dict) else None
    compliance = context.get("compliance") if isinstance(context, dict) else None
    contract_information = context.get("contract_information") if isinstance(context, dict) else None

    prompt = f"""You are a procurement communication assistant.
You are NOT performing analysis. You are ONLY summarizing structured procurement analytics that have already been calculated.
Every explanation, recommendation, and strategy must be based ONLY on the supplied JSON.

Current Procurement Context:
{json.dumps(context, indent=2, default=str)}

Vendor Details:
- Vendor Name: {vendor_name or 'Unavailable'}
- Product Category: {product_category or 'Unavailable'}

Commercial Terms:
- Quote Value: {quote_value if quote_value is not None else 'Unavailable'}
- Delivery Timeline: {delivery_days if delivery_days is not None else 'Unavailable'}
- Warranty: {warranty if warranty is not None else 'Unavailable'}
- Payment Terms: {payment_terms or 'Unavailable'}
- Compliance: {compliance if compliance is not None else 'Unavailable'}
- Support Details: {support_details or 'Unavailable'}
- Contract Information: {json.dumps(contract_information, default=str) if contract_information is not None else 'Unavailable'}

Relevant Historical Procurement Cases:
{json.dumps(historical, indent=2, default=str)}

Task:
Generate a procurement negotiation strategy based on both the current procurement context and previous successful procurement cases.

STRICT HALLUCINATION PREVENTION RULES:
- Never create information that is not present in the supplied JSON.
- If data is unavailable, state that it is unavailable instead of guessing.
- Never reference vendor reputation, migration, restructuring, sanctions, procurement maturity, supplier quality, historical performance, legal status, or commercial relationships unless explicitly supplied in the input.
- Use professional enterprise procurement terminology (e.g. procurement review, commercial negotiations, contract renewal, enterprise agreement, vendor consolidation, contract extension, procurement planning, supplier evaluation, notice period, commercial impact, procurement strategy). Avoid unnatural wording like "sanction contract" or "world-class procurement".

Return JSON only with no explanation, no markdown, no backticks:
{{
  "recommended_strategy": "",
  "expected_discount_range": "",
  "confidence_score": 0,
  "reasoning": "",
  "risks": []
}}
"""
    return prompt


def generate_negotiation_strategy(current_negotiation: Dict[str, Any], historical: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a recommended negotiation strategy using the LLM.

    Returns a dict with keys: recommended_strategy, expected_discount_range, confidence_score, reasoning, risks
    """
    default = _fallback_strategy("the AI response was invalid or unavailable")

    if not historical:
        fallback = _fallback_strategy("no historical negotiations were available")
        _store_strategy_trace(
            prompt=_make_strategy_prompt(current_negotiation, historical),
            raw_llm_response="",
            cleaned_response="",
            parsed_json={},
            final_returned_object=fallback,
            used_fallback=True,
            fallback_reason="no_history",
        )
        return fallback

    if not GROQ_API_KEY:
        _store_strategy_trace(
            prompt=_make_strategy_prompt(current_negotiation, historical),
            raw_llm_response="",
            cleaned_response="",
            parsed_json={},
            final_returned_object=default,
            used_fallback=True,
            fallback_reason="missing_groq_api_key",
        )
        return default

    try:
        llm = ChatGroq(api_key=GROQ_API_KEY, model="llama-3.1-8b-instant", temperature=0)
        prompt = _make_strategy_prompt(current_negotiation, historical)
        response = llm.invoke(prompt)
        response_text = response.content.strip()
        cleaned_response = _clean_response_text(response_text)

        print("[Negotiation Strategy] Prompt sent to Groq:")
        print(prompt)
        print("[Negotiation Strategy] Raw LLM response:")
        print(response_text)
        print("[Negotiation Strategy] Cleaned response:")
        print(cleaned_response)

        parsed = json.loads(cleaned_response)

        print("[Negotiation Strategy] Parsed JSON:")
        print(parsed)

        if not isinstance(parsed, dict):
            final = default
            _store_strategy_trace(
                prompt=prompt,
                raw_llm_response=response_text,
                cleaned_response=cleaned_response,
                parsed_json=parsed,
                final_returned_object=final,
                used_fallback=True,
                fallback_reason="parsed_response_was_not_a_json_object",
            )
            return final

        result = _validate_strategy_payload(parsed)
        if not result["recommended_strategy"] or not result["expected_discount_range"] or len(result["reasoning"].strip()) < 20 or not isinstance(result["risks"], list):
            final = default
            _store_strategy_trace(
                prompt=prompt,
                raw_llm_response=response_text,
                cleaned_response=cleaned_response,
                parsed_json=parsed,
                final_returned_object=final,
                used_fallback=True,
                fallback_reason="validated_fields_failed_project_requirements",
            )
            return final

        if len(result["risks"]) == 0:
            result["risks"] = ["Commercial terms may require further negotiation"]

        print("[Negotiation Strategy] Final returned object:")
        print(result)

        _store_strategy_trace(
            prompt=prompt,
            raw_llm_response=response_text,
            cleaned_response=cleaned_response,
            parsed_json=parsed,
            final_returned_object=result,
            used_fallback=False,
            fallback_reason="",
        )
        return result
    except json.JSONDecodeError as e:
        print(f"Negotiation Strategy JSON Parsing Error: {e}")
        print("[Negotiation Strategy] Raw LLM response caused parse failure:")
        print(response_text if 'response_text' in locals() else "<unavailable>")
        final = default
        _store_strategy_trace(
            prompt=prompt if 'prompt' in locals() else _make_strategy_prompt(current_negotiation, historical),
            raw_llm_response=response_text if 'response_text' in locals() else "",
            cleaned_response=cleaned_response if 'cleaned_response' in locals() else "",
            parsed_json={},
            final_returned_object=final,
            used_fallback=True,
            fallback_reason="json_parse_failure",
            error=str(e),
        )
        return final
    except Exception as e:
        print(f"Negotiation Strategy Error: {e}")
        final = default
        _store_strategy_trace(
            prompt=prompt if 'prompt' in locals() else _make_strategy_prompt(current_negotiation, historical),
            raw_llm_response=response_text if 'response_text' in locals() else "",
            cleaned_response=cleaned_response if 'cleaned_response' in locals() else "",
            parsed_json=parsed if 'parsed' in locals() and isinstance(parsed, dict) else {},
            final_returned_object=final,
            used_fallback=True,
            fallback_reason="unexpected_error",
            error=str(e),
        )
        return final


def _make_email_prompt(vendor_name: str, recommended_strategy: str, expected_discount: str) -> str:
    prompt = f"""You are a procurement communication assistant.
Generate a professional enterprise procurement negotiation email based strictly on the supplied parameters.

Vendor: {vendor_name}
Recommended Strategy: {recommended_strategy}
Expected Discount: {expected_discount}

STRICT HALLUCINATION PREVENTION RULES:
- Never create information that is not present in the supplied parameters.
- Use professional enterprise procurement terminology (e.g. commercial negotiations, contract renewal, enterprise agreement, vendor consolidation, notice period, commercial impact).
- Avoid unnatural wording like "sanction contract", "migrate hardware contract", "vendor reputation", "world-class procurement".

Requirements:
- Enterprise tone
- Relationship friendly
- Commercially strong
- No aggressive language

Return ONLY this JSON with no explanation, no markdown, no backticks:
{{
  "subject": "",
  "body": ""
}}
"""
    return prompt


def generate_negotiation_email(vendor_name: str, recommended_strategy: str, expected_discount: str) -> Dict[str, str]:
    """Generate email subject and body for negotiation outreach."""
    default = _fallback_email(vendor_name, recommended_strategy, expected_discount)

    if not GROQ_API_KEY:
        _store_email_trace(
            prompt=_make_email_prompt(vendor_name, recommended_strategy, expected_discount),
            raw_llm_response="",
            cleaned_response="",
            parsed_json={},
            final_returned_object=default,
            used_fallback=True,
            fallback_reason="missing_groq_api_key",
        )
        return default

    try:
        llm = ChatGroq(api_key=GROQ_API_KEY, model="llama-3.1-8b-instant", temperature=0)
        prompt = _make_email_prompt(vendor_name, recommended_strategy, expected_discount)
        print("[Negotiation Email] Prompt sent to Groq:")
        print(prompt)
        response = llm.invoke(prompt)
        response_text = response.content.strip()
        cleaned_response = _clean_response_text(response_text)

        print("[Negotiation Email] Raw LLM response:")
        print(response_text)
        print("[Negotiation Email] Cleaned response:")
        print(cleaned_response)

        parsed = json.loads(cleaned_response)

        print("[Negotiation Email] Parsed JSON:")
        print(parsed)

        if not isinstance(parsed, dict):
            _store_email_trace(
                prompt=prompt,
                raw_llm_response=response_text,
                cleaned_response=cleaned_response,
                parsed_json=parsed,
                final_returned_object=default,
                used_fallback=True,
                fallback_reason="parsed_response_was_not_a_json_object",
            )
            print("[Negotiation Email] Final returned object:")
            print(default)
            return default

        result = _validate_email_payload(parsed)
        if len(result["subject"]) < 10 or len(result["body"]) < 50:
            fallback = _fallback_email(vendor_name, recommended_strategy, expected_discount)
            _store_email_trace(
                prompt=prompt,
                raw_llm_response=response_text,
                cleaned_response=cleaned_response,
                parsed_json=parsed,
                final_returned_object=fallback,
                used_fallback=True,
                fallback_reason="subject_or_body_too_short",
            )
            print("[Negotiation Email] Final returned object:")
            print(fallback)
            return fallback

        print("[Negotiation Email] Final returned object:")
        print(result)

        _store_email_trace(
            prompt=prompt,
            raw_llm_response=response_text,
            cleaned_response=cleaned_response,
            parsed_json=parsed,
            final_returned_object=result,
            used_fallback=False,
            fallback_reason="",
        )
        return result
    except json.JSONDecodeError as e:
        print(f"Negotiation Email JSON Parsing Error: {e}")
        print("[Negotiation Email] Raw LLM response caused parse failure:")
        print(response_text if 'response_text' in locals() else "<unavailable>")
        fallback = _fallback_email(vendor_name, recommended_strategy, expected_discount)
        _store_email_trace(
            prompt=prompt if 'prompt' in locals() else _make_email_prompt(vendor_name, recommended_strategy, expected_discount),
            raw_llm_response=response_text if 'response_text' in locals() else "",
            cleaned_response=cleaned_response if 'cleaned_response' in locals() else "",
            parsed_json={},
            final_returned_object=fallback,
            used_fallback=True,
            fallback_reason="json_parse_failure",
            error=str(e),
        )
        print("[Negotiation Email] Final returned object:")
        print(fallback)
        return fallback
    except Exception as e:
        print(f"Negotiation Email Error: {e}")
        fallback = _fallback_email(vendor_name, recommended_strategy, expected_discount)
        _store_email_trace(
            prompt=prompt if 'prompt' in locals() else _make_email_prompt(vendor_name, recommended_strategy, expected_discount),
            raw_llm_response=response_text if 'response_text' in locals() else "",
            cleaned_response=cleaned_response if 'cleaned_response' in locals() else "",
            parsed_json=parsed if 'parsed' in locals() and isinstance(parsed, dict) else {},
            final_returned_object=fallback,
            used_fallback=True,
            fallback_reason="unexpected_error",
            error=str(e),
        )
        print("[Negotiation Email] Final returned object:")
        print(fallback)
        return fallback
