from typing import List, Dict, Any
import json
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


async def retrieve_similar_negotiations(vendor_name: str, product_category: str, quote_value: float) -> List[NegotiationHistoryRecord]:
    """Retrieve top 5 similar negotiations from `negotiation_history`.

    Retrieval logic (structured): filter by product_category, prioritize successful negotiations,
    and rank by same vendor, success_score, quote value similarity, and outcome.
    """
    client = supabase_service or supabase

    try:
        resp = client.table("negotiation_history").select("*").eq("product_category", product_category).execute()
        rows = resp.data if resp.data else []

        if not rows:
            return []

        records: List[NegotiationHistoryRecord] = [NegotiationHistoryRecord.model_validate(row) for row in rows]

        # Compute ranking score
        scored = []
        for r in records:
            score = 0.0
            # same vendor boost
            if r.vendor_name and vendor_name and r.vendor_name.lower() == vendor_name.lower():
                score += VENDOR_MATCH_WEIGHT

            # success_score contribution (assumed 0-100)
            success_score = r.success_score or 0
            try:
                ss = float(success_score)
            except Exception:
                ss = 0.0
            score += ss * SUCCESS_SCORE_WEIGHT  # higher prior success is more reusable in future negotiation

            # quote similarity (smaller diff -> higher score)
            try:
                initial_quote = float(r.initial_quote_value or 0)
                diff = abs(initial_quote - (quote_value or 0.0))
                # normalize by quote_value or initial_quote to avoid divide by zero
                norm_base = quote_value if quote_value and quote_value > 0 else (initial_quote if initial_quote > 0 else 1.0)
                similarity = max(0.0, 1.0 - min(diff / norm_base, 1.0))
            except Exception:
                similarity = 0.0
            score += similarity * QUOTE_SIMILARITY_WEIGHT  # closer quote values are stronger anchors for negotiation framing

            # outcome bonus for successful outcomes
            outcome = (r.outcome or "").lower()
            if outcome in ["success", "successful", "won"]:
                score += OUTCOME_WEIGHT

            # Slight boost if negotiation_rounds is low (efficient negotiation)
            try:
                rounds = int(r.negotiation_rounds or 0)
                if rounds <= 2 and rounds > 0:
                    score += ROUND_WEIGHT
            except Exception:
                pass

            scored.append((score, r))

        # Sort by score descending and return top 5
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [item[1] for item in scored[:5]]
        return top

    except Exception as e:
        raise Exception(f"Failed to retrieve negotiations: {str(e)}")


async def generate_strategy(vendor_name: str, product_category: str, quote_value: float) -> NegotiationStrategyResult:
    """Retrieve similar negotiations and call the negotiation strategy agent.

    Logs the agent execution via `audit_service`.
    """
    try:
        # Retrieve historical negotiations
        historical = await retrieve_similar_negotiations(vendor_name, product_category, quote_value)

        current = {
            "vendor_name": vendor_name,
            "product_category": product_category,
            "quote_value": quote_value
        }

        historical_context = [_format_negotiation_context(record) for record in historical]

        # Call agent (synchronous style consistent with other agents)
        strategy_dict = generate_negotiation_strategy(current, historical_context)
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
                    "vendor_name": vendor_name,
                    "product_category": product_category,
                    "quote_value": quote_value,
                    "retrieved_records_count": len(historical),
                    "top_strategy_candidates": _build_strategy_candidates(historical),
                    "raw_llm_response": trace.get("raw_llm_response", ""),
                    "cleaned_response": trace.get("cleaned_response", ""),
                    "fallback_reason": trace.get("fallback_reason", ""),
                },
                output_payload=json.loads(result.model_dump_json()),
                reasoning=f"Fallback strategy used because {trace.get('fallback_reason', 'the model response was invalid')}.",
            )

        # Audit log
        await log_agent_execution(
            agent_name="Negotiation Strategy Agent",
            action_type="generate_strategy",
            input_payload={
                "vendor_name": vendor_name,
                "product_category": product_category,
                "quote_value": quote_value,
                "retrieved_records_count": len(historical),
                "top_strategy_candidates": _build_strategy_candidates(historical)
            },
            output_payload=json.loads(result.model_dump_json()),
            reasoning="Generated negotiation strategy based on structured historical negotiation patterns."
        )

        return result
    except Exception as e:
        raise Exception(f"Failed to generate strategy: {str(e)}")


async def generate_email(vendor_name: str, recommended_strategy: str, expected_discount_range: str) -> NegotiationEmail:
    """Call the email generator agent and log the result."""
    try:
        email_dict = generate_negotiation_email(vendor_name, recommended_strategy, expected_discount_range)
        email = NegotiationEmail.model_validate(email_dict)

        trace = negotiation_agent_module.get_last_email_trace()
        if trace.get("used_fallback"):
            await log_agent_execution(
                agent_name="Negotiation Strategy Agent",
                action_type="generate_email_failure",
                input_payload={
                    "vendor_name": vendor_name,
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
                "vendor_name": vendor_name,
                "recommended_strategy": recommended_strategy,
                "expected_discount_range": expected_discount_range
            },
            output_payload=email.model_dump(),
            reasoning="Generated procurement negotiation outreach email based on the recommended negotiation strategy."
        )

        return email
    except Exception as e:
        raise Exception(f"Failed to generate email: {str(e)}")
