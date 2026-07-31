import json
import logging
import hashlib
import time
from typing import List, Dict, Any, Tuple
from langchain_groq import ChatGroq
from ..config import GROQ_API_KEY
from ..models.optimization import RenewalRiskAnalysis, DealOpportunity

logger = logging.getLogger("uvicorn.error")

# Fast 60-second TTL cache for LLM responses to eliminate page reload latency
_CACHE: Dict[str, Tuple[float, Any]] = {}
CACHE_TTL = 60.0


def _get_cache(key: str):
    if key in _CACHE:
        timestamp, value = _CACHE[key]
        if time.time() - timestamp < CACHE_TTL:
            return value
    return None


def _set_cache(key: str, value: Any):
    _CACHE[key] = (time.time(), value)


def _get_llm() -> ChatGroq | None:
    if not GROQ_API_KEY:
        return None
    try:
        return ChatGroq(
            api_key=GROQ_API_KEY,
            model="llama-3.1-8b-instant",
            temperature=0.2,
            max_tokens=2048
        )
    except Exception as e:
        logger.warning(f"Unable to initialize ChatGroq LLM: {e}")
        return None


async def enrich_renewal_analyses_with_llm(analyses: List[RenewalRiskAnalysis]) -> List[RenewalRiskAnalysis]:
    """
    Enrich deterministic renewal risk analysis objects with personalized, LLM-generated recommendations and explanations.
    Uses in-memory caching for zero latency on frequent page loads.
    """
    if not analyses:
        return []

    # Check cache
    cache_key = "renewal_" + hashlib.md5(json.dumps([a.model_dump() for a in analyses], default=str).encode()).hexdigest()
    cached = _get_cache(cache_key)
    if cached:
        return cached

    llm = _get_llm()
    if not llm:
        return analyses

    contracts_payload = [
        {
            "contract_id": a.contract_id,
            "contract_name": a.contract_name,
            "vendor_name": a.vendor_name,
            "renewal_date": str(a.renewal_date) if a.renewal_date else "N/A",
            "days_remaining": a.days_remaining,
            "risk_level": a.risk_level,
            "fallback_recommendation": a.recommendation
        }
        for a in analyses
    ]

    prompt = f"""You are an expert enterprise procurement AI consultant (SAP Ariba / Coupa style).

Below is structured contract renewal risk data computed deterministically by our risk engine:
{json.dumps(contracts_payload, indent=2)}

Task:
For EACH contract in the list, write:
1. "recommendation": A personalized, highly specific, actionable procurement directive (1-2 sentences).
2. "explainability": A clear, executive explanation of why this risk level was assigned (1-2 sentences).

CRITICAL DIVERSITY RULE TO PREVENT REPETITIVENESS:
- NEVER repeat identical sentence structures, prefixes, or boilerplate phrases across contracts.
- VARY YOUR VERBS: Use a completely different action verb for each item (e.g. "Execute", "Audit", "Consolidate", "Renegotiate", "Transition", "Re-align", "Sanction", "Migrate").
- Explicitly mention the specific contract name, vendor name, and exact days_remaining in every recommendation so that each recommendation is uniquely tailored to that contract!

STRICT RULES TO PREVENT HALLUCINATION:
- You MUST preserve all exact vendor names, contract names, dates, and days_remaining from the input.
- Do NOT introduce any new numbers, dates, or vendor names not present in the input.
- Return ONLY a raw JSON array matching this format, with no markdown backticks:
[
  {{
    "contract_id": "string",
    "recommendation": "distinct personalized recommendation string",
    "explainability": "distinct personalized explanation string"
  }}
]
"""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        if "```" in content:
            content = content.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(content)
        if isinstance(parsed, list):
            parsed_map = {item.get("contract_id"): item for item in parsed if isinstance(item, dict)}
            for a in analyses:
                if a.contract_id in parsed_map:
                    item = parsed_map[a.contract_id]
                    if item.get("recommendation"):
                        a.recommendation = str(item["recommendation"]).strip()
                    if item.get("explainability"):
                        a.explainability = str(item["explainability"]).strip()
            _set_cache(cache_key, analyses)
    except Exception as e:
        logger.warning(f"LLM renewal narrative enrichment fallback triggered: {e}")

    return analyses


async def enrich_crossdeal_opportunities_with_llm(opportunities: List[DealOpportunity]) -> List[DealOpportunity]:
    """
    Enrich deterministic cross-deal bundle opportunities with customized, LLM-generated negotiation rationale.
    Uses in-memory caching for ultra-fast performance.
    """
    if not opportunities:
        return []

    cache_key = "crossdeal_" + hashlib.md5(json.dumps([o.model_dump() for o in opportunities], default=str).encode()).hexdigest()
    cached = _get_cache(cache_key)
    if cached:
        return cached

    llm = _get_llm()
    if not llm:
        return opportunities

    opps_payload = [
        {
            "vendor_name": o.vendor_name,
            "departments": o.departments,
            "total_procurement_value": o.total_procurement_value,
            "estimated_savings_percent": o.estimated_savings_percent,
            "estimated_savings_amount": o.estimated_savings_amount,
            "confidence_score": o.confidence_score
        }
        for o in opportunities
    ]

    prompt = f"""You are an expert enterprise procurement negotiation strategist.

Below is multi-department vendor procurement data pre-calculated by our savings engine:
{json.dumps(opps_payload, indent=2)}

Task:
For EACH vendor opportunity in the input, generate:
- "recommendation": A professional, highly specific negotiation strategy explaining how to leverage cross-department volume (e.g. Master Service Agreement consolidation, payment term standardization, SLA harmonization) to capture the calculated savings.

CRITICAL DIVERSITY RULE:
- Ensure each vendor strategy is distinct and specifically highlights the vendor name, department list, and dollar spend amount. Do not reuse boilerplate phrases across vendors.

STRICT RULES TO PREVENT HALLUCINATION:
- Use ONLY the vendor names, departments, savings %, dollar amounts, and total spend provided.
- Do NOT modify any dollar amounts or percentages.
- Return ONLY a raw JSON array matching this format, with no markdown backticks:
[
  {{
    "vendor_name": "string",
    "recommendation": "customized enterprise negotiation strategy"
  }}
]
"""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        if "```" in content:
            content = content.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(content)
        if isinstance(parsed, list):
            parsed_map = {item.get("vendor_name"): item for item in parsed if isinstance(item, dict)}
            for o in opportunities:
                if o.vendor_name in parsed_map:
                    item = parsed_map[o.vendor_name]
                    if item.get("recommendation"):
                        o.recommendation = str(item["recommendation"]).strip()
            _set_cache(cache_key, opportunities)
    except Exception as e:
        logger.warning(f"LLM crossdeal narrative enrichment fallback triggered: {e}")

    return opportunities

