from typing import List, Dict, Any, Tuple, Optional
from uuid import UUID
import re
import os
import json
from datetime import datetime
from langchain_groq import ChatGroq
from .groq_key_manager import get_next_groq_key
from ..config import GROQ_API_KEYS
from ..supabase_client import supabase, supabase_service
from ..models.recommendation import (
    RecommendationWeights,
    RecommendationRequest,
    ScoreComponent,
    ScoreBreakdown,
    VendorRecommendation,
    RecommendationResponse,
    ApplyRecommendationRequest,
    ApplyRecommendationResponse
)
from .risk_service import get_latest_vendor_risk
from .audit_service import log_agent_execution
import logging

logger = logging.getLogger("uvicorn.error")
# Note: GROQ API keys will be rotated via get_next_groq_key()


# Mapping support level strings to numerical scores
def map_support_score(support_str: str) -> float:
    support_lower = str(support_str or "").lower()
    if not support_lower:
        return 50.0

    if any(keyword in support_lower for keyword in ["24/7", "24x7", "premier", "premium", "gold", "platinum", "dedicated"]):
        return 100.0
    if any(keyword in support_lower for keyword in ["business", "silver", "priority", "9am to 6pm", "9 to 6"]):
        return 80.0
    if any(keyword in support_lower for keyword in ["standard", "bronze", "next business day"]):
        return 60.0
    if any(keyword in support_lower for keyword in ["basic", "email only", "standard hours"]):
        return 40.0

    return 50.0


# Parse warranty period to years (numeric)
def parse_warranty_years(warranty_years: Any, warranty_period: Any) -> Optional[float]:
    if warranty_years is not None and str(warranty_years).strip().lower() != "data not available":
        try:
            return float(warranty_years)
        except (ValueError, TypeError):
            pass

    if warranty_period is not None and str(warranty_period).strip().lower() != "data not available":
        period_str = str(warranty_period).strip().lower()
        nums = re.findall(r"\d+\.?\d*", period_str)
        if nums:
            val = float(nums[0])
            if "month" in period_str:
                return round(val / 12.0, 2)
            if "year" in period_str or "yr" in period_str:
                return val
            return val

    return None


# Compute ESG score based on sustainability info and certifications
def calculate_esg_score(esg_info: str, certifications: Any) -> float:
    score = 60.0  # Base ESG score (never assign zero because data is missing)

    # Analyze certifications
    sustainability_certs = {"iso 14001", "iso 5001", "leed", "b corp", "energy star", "rohs", "weee"}
    cert_count = 0
    if isinstance(certifications, list):
        for cert in certifications:
            if str(cert).strip().lower() in sustainability_certs:
                cert_count += 1
    elif isinstance(certifications, str) and certifications.strip().lower() != "data not available":
        for cert in certifications.split(","):
            if cert.strip().lower() in sustainability_certs:
                cert_count += 1

    score += cert_count * 15.0

    # Analyze ESG info text
    sustainability_keywords = [
        "sustainability", "carbon", "emission", "renewable", "green",
        "recycle", "recycling", "solar", "diversity", "governance",
        "ethical", "environmental", "social", "clean", "efficiency"
    ]
    keyword_count = 0
    if esg_info and str(esg_info).strip().lower() != "data not available":
        text_lower = str(esg_info).lower()
        for kw in sustainability_keywords:
            if kw in text_lower:
                keyword_count += 1

    score += min(keyword_count * 5.0, 25.0)
    return min(score, 100.0)


# Agentic reasoning prompt builder
def _make_agent_prompt(
    procurement_title: str,
    procurement_description: str,
    weights_dict: Dict[str, float],
    vendors_context: str,
    today_str: str
) -> str:
    prompt = f"""You are an autonomous Agentic AI Procurement Recommendation Engine.
Analyze the following procurement scenario, perform step-by-step reasoning, and return a structured JSON recommendation report.

Today's date is: {today_str}

PROCUREMENT PROJECT:
Title: {procurement_title}
Description: {procurement_description}

USER WEIGHTS / PRIORITIES:
{json.dumps(weights_dict, indent=2)}

OBSERVED VENDORS AND QUOTES DATA:
{vendors_context}

Perform these six agentic steps:
1. OBSERVE: Gather and assess all quotes, prices, risk scores, market intelligence threat alerts, and negotiation opportunities.
2. UNDERSTAND INTENT: Map the slider weights to business intents (e.g. Lowest Cost, Sustainable Procurement, Balanced Procurement).
3. REASON: Analyze constraints (urgency, budget, high risk alerts, missing fields impact, tradeoffs). Explain reasoning.
4. PLAN: Decide evaluation criteria importance, vendor shortlist, and if additional validations or negotiation leverages are needed.
5. DECIDE: Interpret the Comparison Engine's scores alongside qualitative risk, ESG, warranty, and missing info to make the final choice.
6. EXPLAIN: Summarize the decision clearly.

Rules:
- If ESG, Warranty, or other details are missing ("Data Not Available"), do not treat it as zero. Skip or handle neutrally, reduce the confidence score, and explain the impact.
- The output MUST be a valid JSON object matching the exact structure below. Do NOT wrap in backticks or markdown, do NOT include explanation text outside the JSON.

EXPECTED JSON FORMAT:
{{
  "recommended_vendor_id": "vendor_id_here",
  "recommended_vendor_name": "vendor_name_here",
  "why_selected": "Detailed explanation of strengths and reasons for choosing this vendor...",
  "why_others_not_selected": "Explanation of why other vendors were not chosen...",
  "dynamic_priorities": "Analysis of the procurement intent based on manager weights...",
  "criterion_importance": "Evaluation of which criteria were prioritized...",
  "missing_information_impact": "Impact of missing data points like Warranty or ESG on the decision...",
  "risks_identified": "Detailed risks for the recommended and other vendors...",
  "alternative_recommendation": "Runner-up selection with trade-offs...",
  "agent_reasoning": "Step-by-step logical reasoning of the agent...",
  "agent_plan": "Proposed plan of next steps (e.g. shortlisting, validations, contract negotiations)...",
  "confidence_score": (float between 0.0 and 1.0 representing overall evaluation confidence)
}}
"""
    return prompt

def format_reasoning(val) -> str:
    if not val:
        return "No reasoning steps logged."
    if isinstance(val, list):
        return "\n".join(f"{idx+1}. {item}" for idx, item in enumerate(val))
    if isinstance(val, dict):
        return "\n".join(f"- **{k}**: {v}" for k, v in val.items())
    return str(val)

def format_risks(val) -> str:
    if not val:
        return "No risk analysis data available."
    if isinstance(val, dict):
        lines = []
        for vendor, details in val.items():
            if isinstance(details, dict):
                score = details.get("risk_score")
                vendor_risks = details.get("risks", [])
                score_str = f" (Risk Score: {score}/100)" if score is not None else ""
                lines.append(f"- **{vendor}**{score_str}:")
                if isinstance(vendor_risks, list) and vendor_risks:
                    for vr in vendor_risks:
                        lines.append(f"  * {vr}")
                elif vendor_risks:
                    lines.append(f"  * {vendor_risks}")
                else:
                    lines.append("  * No critical risks identified.")
            else:
                lines.append(f"- **{vendor}**: {details}")
        return "\n".join(lines)
    if isinstance(val, list):
        return "\n".join(f"- {item}" for item in val)
    return str(val)

def format_alternative(val) -> str:
    if not val:
        return "No alternative recommendations."
    if isinstance(val, dict):
        vendor_name = val.get("vendor_name") or val.get("recommended_vendor_name") or "Alternative Vendor"
        tradeoffs = val.get("trade-offs") or val.get("trade_offs") or val.get("explanation")
        if tradeoffs:
            return f"**Alternative Winner**: **{vendor_name}**\n**Trade-offs**: {tradeoffs}"
        return f"**Alternative Winner**: **{vendor_name}**"
    if isinstance(val, list):
        return "\n".join(f"- {item}" for item in val)
    return str(val)

def format_plan(val) -> str:
    if not val:
        return "No concrete action items planned."
    if isinstance(val, list):
        return "\n".join(f"- {item}" for item in val)
    if isinstance(val, dict):
        return "\n".join(f"- **{k}**: {v}" for k, v in val.items())
    return str(val)


async def get_recommendation_analysis(request: RecommendationRequest) -> RecommendationResponse:
    procurement_id = str(request.procurement_id)
    weights = request.weights
    qual_adjustments = request.qualitative_adjustments or {}
    skip_ai = getattr(request, "skip_ai", False) or False

    client = supabase_service or supabase

    # Fetch procurement context info and vendors in parallel
    import asyncio
    proc_title = "Procurement"
    proc_desc = ""
    vendors = []
    try:
        proc_task = asyncio.to_thread(lambda: client.table("procurements").select("title, description").eq("id", procurement_id).execute())
        vendors_task = asyncio.to_thread(lambda: client.table("vendors").select("*").eq("procurement_id", procurement_id).execute())
        
        proc_resp, vendors_resp = await asyncio.gather(proc_task, vendors_task)
        if proc_resp.data:
            proc_title = proc_resp.data[0].get("title", "Procurement")
            proc_desc = proc_resp.data[0].get("description", "")
        vendors = vendors_resp.data or []
    except Exception as pe:
        logger.warning(f"Failed to fetch procurement details or vendors in parallel: {pe}")
        # Single-threaded fallback for robustness
        try:
            proc_resp = client.table("procurements").select("title, description").eq("id", procurement_id).execute()
            if proc_resp.data:
                proc_title = proc_resp.data[0].get("title", "Procurement")
                proc_desc = proc_resp.data[0].get("description", "")
        except Exception:
            pass
        try:
            vendors_resp = client.table("vendors").select("*").eq("procurement_id", procurement_id).execute()
            vendors = vendors_resp.data or []
        except Exception:
            vendors = []

    # Fallback to all vendors if none found under specific procurement_id (robust fallback)
    if not vendors:
        try:
            vendors_resp = client.table("vendors").select("*").execute()
            all_vendors = vendors_resp.data or []

            seen_names = set()
            vendors = []
            for v in all_vendors:
                name_clean = str(v.get("vendor_name", "")).lower().strip()
                if name_clean not in seen_names:
                    seen_names.add(name_clean)
                    vendors.append(v)

            logger.info(f"Fallback: Fetched {len(vendors)} unique vendors because procurement_id {procurement_id} returned 0 results.")
        except Exception as e:
            logger.error(f"Error in fallback fetching all vendors: {e}")
            vendors = []

    if not vendors:
        return RecommendationResponse(
            recommendations=[],
            comparison_summary="No vendors found in the database. Please create vendors first."
        )

    # 2. Fetch all quotes & match them to vendors
    vendor_ids = [v["id"] for v in vendors]
    try:
        quotes_resp = client.table("vendor_quotes").select("*").in_("vendor_id", vendor_ids).execute()
        quotes_list = quotes_resp.data or []
    except Exception as e:
        logger.error(f"Error fetching quotes: {e}")
        quotes_list = []

    # Map quotes by vendor_id (take the latest quote for each vendor)
    vendor_quotes_map: Dict[str, Dict[str, Any]] = {}
    for quote in quotes_list:
        v_id = quote.get("vendor_id")
        if v_id:
            if v_id not in vendor_quotes_map:
                vendor_quotes_map[v_id] = quote

    # 3. Filter down to vendors that actually have quotes
    active_vendors = [v for v in vendors if v["id"] in vendor_quotes_map]

    if not active_vendors:
        return RecommendationResponse(
            recommendations=[],
            comparison_summary="No active quotes found for the compared vendors. Please upload quotes to run the simulator."
        )

    # 4. Fetch risk profiles & run optimization analysis concurrently
    import asyncio

    async def fetch_risk(v_id):
        try:
            risk_data = await get_latest_vendor_risk(v_id, client=client)
            return v_id, risk_data.get("final_risk_score", 50)
        except Exception as e:
            logger.warning(f"Failed to fetch risk score for vendor {v_id}, defaulting to 50: {e}")
            return v_id, 50

    try:
        from .renewal_service import get_renewal_analysis
        from .crossdeal_service import get_crossdeal_analysis
        renewal_task = get_renewal_analysis(skip_ai=skip_ai)
        crossdeal_task = get_crossdeal_analysis(skip_ai=skip_ai)
    except Exception as e:
        logger.warning(f"Failed to setup optimization tasks: {e}")
        renewal_task = None
        crossdeal_task = None

    risk_tasks = [fetch_risk(v["id"]) for v in active_vendors]
    tasks = list(risk_tasks)
    if renewal_task:
        tasks.append(renewal_task)
    if crossdeal_task:
        tasks.append(crossdeal_task)

    results = await asyncio.gather(*tasks)

    vendor_risk_map: Dict[str, int] = {}
    for i in range(len(active_vendors)):
        v_id, score = results[i]
        vendor_risk_map[v_id] = score

    renewal_analyses = []
    crossdeal_opportunities = []

    idx = len(active_vendors)
    if renewal_task:
        renewal_res = results[idx]
        renewal_analyses = renewal_res[0] if renewal_res else []
        idx += 1
    if crossdeal_task:
        crossdeal_res = results[idx]
        crossdeal_opportunities = crossdeal_res[0] if crossdeal_res else []

    def is_vendor_match(name1: str, name2: str) -> bool:
        n1 = str(name1 or "").lower().strip()
        n2 = str(name2 or "").lower().strip()
        return n1 in n2 or n2 in n1

    # 5. Extract metrics for normalization (applying cross-deal discounts to pricing for scoring influence)
    prices_for_scoring = []
    prices_raw = []
    delivery_times = []
    warranties_for_scoring = []

    for v in active_vendors:
        v_id = v["id"]
        v_name = v["vendor_name"]
        quote = vendor_quotes_map[v_id]

        raw_price = float(quote.get("price", 0) or 0)
        prices_raw.append(raw_price)

        discount = 0.0
        for opp in crossdeal_opportunities:
            if is_vendor_match(v_name, opp.vendor_name):
                discount = opp.estimated_savings_percent / 100.0
                break

        prices_for_scoring.append(raw_price * (1.0 - discount))
        delivery_times.append(float(quote.get("delivery_days", 0) or 0))

        # Check warranty parameters
        ext_json = quote.get("extracted_json", {})
        full_ai = ext_json.get("full_ai_result", {}) if isinstance(ext_json, dict) else {}
        ext_data = full_ai.get("extracted_data", {}) if isinstance(full_ai, dict) else {}

        w_years = quote.get("warranty_years") if quote.get("warranty_years") is not None else ext_data.get("warranty_years")
        w_period = quote.get("warranty_period") if quote.get("warranty_period") is not None else ext_data.get("warranty_period")

        parsed_w = parse_warranty_years(w_years, w_period)
        if parsed_w is not None:
            warranties_for_scoring.append(parsed_w)

    min_price_for_scoring = min(prices_for_scoring) if prices_for_scoring else 0.0
    min_delivery = min(delivery_times) if delivery_times else 0.0
    max_delivery = max(delivery_times) if delivery_times else 0.0
    max_warranty = max(warranties_for_scoring) if warranties_for_scoring else 0.0

    # Unpack weights safely to enable backwards compatibility
    w_cost = getattr(weights, "cost", 0.0) or 0.0
    w_risk = getattr(weights, "risk", 0.0) or 0.0
    w_support = getattr(weights, "support", 0.0) or 0.0
    w_delivery = getattr(weights, "delivery", 0.0) or 0.0
    w_warranty = getattr(weights, "warranty", 0.0) or 0.0
    w_esg = getattr(weights, "esg", 0.0) or 0.0

    w_total = w_cost + w_risk + w_support + w_delivery + w_warranty + w_esg
    warning_msg = None
    if w_total == 0:
        w_cost = w_risk = w_support = w_delivery = 20.0
        w_warranty = w_esg = 10.0
        w_total = 80.0
        warning_msg = "All weights were set to 0. Internally defaulted to equal weights."

    recommendations: List[VendorRecommendation] = []

    for v in active_vendors:
        v_id = v["id"]
        v_name = v["vendor_name"]
        quote = vendor_quotes_map[v_id]

        qual_adj = float(qual_adjustments.get(v_id, 0.0))
        qual_adj = max(-20.0, min(20.0, qual_adj))

        matching_crossdeal = None
        for opp in crossdeal_opportunities:
            if is_vendor_match(v_name, opp.vendor_name):
                matching_crossdeal = opp
                break

        matching_renewals = [ren for ren in renewal_analyses if is_vendor_match(v_name, ren.vendor_name)]

        # 1. Cost Score
        raw_price = float(quote.get("price", 0) or 0)
        crossdeal_discount = (matching_crossdeal.estimated_savings_percent / 100.0) if matching_crossdeal else 0.0
        price_for_scoring = raw_price * (1.0 - crossdeal_discount)

        if price_for_scoring > 0:
            cost_score = 100.0 * (min_price_for_scoring / price_for_scoring)
        else:
            cost_score = 100.0

        # 2. Risk Score
        raw_risk = float(vendor_risk_map.get(v_id, 50))
        risk_penalty = 0.0
        highest_renewal_risk = "LOW"
        for ren in matching_renewals:
            if ren.risk_level == "CRITICAL":
                risk_penalty = max(risk_penalty, 20.0)
                highest_renewal_risk = "CRITICAL"
            elif ren.risk_level == "HIGH":
                risk_penalty = max(risk_penalty, 15.0)
                if highest_renewal_risk != "CRITICAL":
                    highest_renewal_risk = "HIGH"
            elif ren.risk_level == "MEDIUM":
                risk_penalty = max(risk_penalty, 8.0)
                if highest_renewal_risk not in ["CRITICAL", "HIGH"]:
                    highest_renewal_risk = "MEDIUM"

        effective_risk = min(100.0, raw_risk + risk_penalty)
        risk_score = max(0.0, min(100.0, 100.0 - effective_risk))

        # 3. Support Score
        raw_support = quote.get("support_level", "Basic")
        support_score = map_support_score(raw_support)

        # 4. Delivery Score
        raw_delivery = float(quote.get("delivery_days", 0) or 0)
        if max_delivery != min_delivery:
            delivery_score = 100.0 * ((max_delivery - raw_delivery) / (max_delivery - min_delivery))
        else:
            delivery_score = 100.0

        # 5. Warranty Score
        ext_json = quote.get("extracted_json", {})
        full_ai = ext_json.get("full_ai_result", {}) if isinstance(ext_json, dict) else {}
        ext_data = full_ai.get("extracted_data", {}) if isinstance(full_ai, dict) else {}

        w_years = quote.get("warranty_years") if quote.get("warranty_years") is not None else ext_data.get("warranty_years")
        w_period = quote.get("warranty_period") if quote.get("warranty_period") is not None else ext_data.get("warranty_period")

        parsed_w = parse_warranty_years(w_years, w_period)
        has_warranty = parsed_w is not None

        missing_info = []
        base_confidence = full_ai.get("extraction_confidence_score", 1.0) if isinstance(full_ai, dict) else 1.0
        confidence_deduction = 0.0

        if has_warranty:
            if max_warranty > 0:
                warranty_score = 100.0 * (parsed_w / max_warranty)
            else:
                warranty_score = 100.0
            raw_warranty_str = f"{parsed_w} years"
        else:
            warranty_score = 0.0
            raw_warranty_str = "Data Not Available"
            missing_info.append("Warranty Information")
            confidence_deduction += 0.10

        # 6. ESG Score
        esg_info = quote.get("esg_info") if quote.get("esg_info") is not None else ext_data.get("esg_info")
        certs = quote.get("vendor_certifications") if quote.get("vendor_certifications") is not None else ext_data.get("vendor_certifications")

        has_esg = esg_info is not None and str(esg_info).strip().lower() != "data not available"
        if has_esg:
            esg_score = calculate_esg_score(esg_info, certs)
            raw_esg_str = str(esg_info)
        else:
            esg_score = 0.0
            raw_esg_str = "Data Not Available"
            missing_info.append("ESG Information")
            confidence_deduction += 0.15

        # Dynamic weight denominator adjustment to avoid penalizing missing criteria
        v_w_total = w_cost + w_risk + w_support + w_delivery
        if has_warranty:
            v_w_total += w_warranty
        if has_esg:
            v_w_total += w_esg
        if v_w_total == 0:
            v_w_total = 100.0

        # Weighted score contributions
        cost_contrib = (cost_score * w_cost) / v_w_total
        risk_contrib = (risk_score * w_risk) / v_w_total
        support_contrib = (support_score * w_support) / v_w_total
        delivery_contrib = (delivery_score * w_delivery) / v_w_total

        warranty_contrib = 0.0
        if has_warranty:
            warranty_contrib = (warranty_score * w_warranty) / v_w_total

        esg_contrib = 0.0
        if has_esg:
            esg_contrib = (esg_score * w_esg) / v_w_total

        base_score = cost_contrib + risk_contrib + support_contrib + delivery_contrib + warranty_contrib + esg_contrib
        strategic_bonus = 5.0 if matching_crossdeal else 0.0

        final_score = round(max(0.0, min(100.0, base_score + qual_adj + strategic_bonus)), 1)
        final_confidence = round(max(0.0, min(1.0, base_confidence - confidence_deduction)), 2)

        # Build detailed explainable reasoning
        single_expl = (
            f"{v_name} scored {final_score}/100. Strengths: "
            f"Cost score is {cost_score:.1f}/100 (raw price: ${raw_price:,.2f}), "
            f"Risk safety is {risk_score:.1f}/100 (raw risk: {raw_risk:.0f}/100), "
            f"Support rating is {support_score:.1f}/100 (level: {raw_support}), "
            f"Delivery rating is {delivery_score:.1f}/100 (delivery: {raw_delivery:.0f} days)."
        )

        if has_warranty:
            single_expl += f" Warranty coverage is {warranty_score:.1f}/100 ({raw_warranty_str})."
        else:
            single_expl += " Warranty information is missing."

        if has_esg:
            single_expl += f" ESG rating is {esg_score:.1f}/100."
        else:
            single_expl += " ESG information is missing (reduced evaluation confidence)."

        if matching_crossdeal:
            single_expl += f" [CROSS DEAL] Influenced by Cross-Deal Negotiator: bundling potential across {len(matching_crossdeal.departments)} departments unlocks {matching_crossdeal.estimated_savings_percent}% estimated savings (added +5.0 strategic consolidation bonus)."
        if highest_renewal_risk in ["CRITICAL", "HIGH", "MEDIUM"]:
            single_expl += f" [RENEWAL RISK] Flagged by Renewal Catcher: active contract has {highest_renewal_risk} renewal risk (applied {risk_penalty:.0f}-point risk safety penalty)."
        if qual_adj != 0:
            single_expl += f" Includes a qualitative adjustment of {qual_adj:+.1f}."

        recommendations.append(VendorRecommendation(
            vendor_id=v_id,
            vendor_name=v_name,
            final_score=final_score,
            rank=0,
            breakdown=ScoreBreakdown(
                cost=ScoreComponent(raw=raw_price, score=round(cost_score, 1), weighted=round(cost_contrib, 1)),
                risk=ScoreComponent(raw=raw_risk, score=round(risk_score, 1), weighted=round(risk_contrib, 1)),
                support=ScoreComponent(raw=raw_support, score=round(support_score, 1), weighted=round(support_contrib, 1)),
                delivery=ScoreComponent(raw=raw_delivery, score=round(delivery_score, 1), weighted=round(delivery_contrib, 1)),
                warranty=ScoreComponent(raw=raw_warranty_str, score=round(warranty_score, 1), weighted=round(warranty_contrib, 1)),
                esg=ScoreComponent(raw=raw_esg_str[:100], score=round(esg_score, 1), weighted=round(esg_contrib, 1))
            ),
            explanation=single_expl,
            qualitative_adjustment=qual_adj,
            missing_information=missing_info,
            confidence_score=final_confidence
        ))

    # Sort and Rank (Primary: final_score desc, Secondary: raw price asc, Tertiary: name alphabetical)
    def sorting_key(item: VendorRecommendation) -> Tuple[float, float, str]:
        price_val = float(item.breakdown.cost.raw)
        return (-item.final_score, price_val, item.vendor_name)

    recommendations.sort(key=sorting_key)

    for idx, rec in enumerate(recommendations, start=1):
        rec.rank = idx

    # Comparative summary text
    summary_text = ""
    if len(recommendations) == 1:
        summary_text = (
            f"{recommendations[0].vendor_name} is the only vendor with an uploaded quote. "
            "Add more quotes to compare alternative choices."
        )
    else:
        v1 = recommendations[0]
        v2 = recommendations[1]

        diffs = {
            "Cost": v1.breakdown.cost.weighted - v2.breakdown.cost.weighted,
            "Risk Safety": v1.breakdown.risk.weighted - v2.breakdown.risk.weighted,
            "Support": v1.breakdown.support.weighted - v2.breakdown.support.weighted,
            "Delivery": v1.breakdown.delivery.weighted - v2.breakdown.delivery.weighted,
            "Warranty": (v1.breakdown.warranty.weighted if v1.breakdown.warranty else 0.0) - (v2.breakdown.warranty.weighted if v2.breakdown.warranty else 0.0),
            "ESG": (v1.breakdown.esg.weighted if v1.breakdown.esg else 0.0) - (v2.breakdown.esg.weighted if v2.breakdown.esg else 0.0),
        }

        favors_v1 = [cat for cat, d in diffs.items() if d > 0]
        favors_v2 = [cat for cat, d in diffs.items() if d < 0]

        favors_v1.sort(key=lambda cat: abs(diffs[cat]), reverse=True)
        favors_v2.sort(key=lambda cat: abs(diffs[cat]), reverse=True)

        if favors_v1:
            pos_str = " and ".join(favors_v1[:2]).lower()
            summary_text = f"{v1.vendor_name} ranked higher than {v2.vendor_name} because {pos_str} were weighted more heavily."

            details = []
            for cat in favors_v1[:2]:
                val_v1 = diffs[cat]
                details.append(f"{cat} (+{val_v1:.1f} pts)")

            neg_details = []
            for cat in favors_v2[:1]:
                val_v2 = diffs[cat]
                neg_details.append(f"{cat} ({val_v2:.1f} pts)")

            summary_text += f" (Advantage in {', '.join(details)}"
            if neg_details:
                summary_text += f", offsetting {v2.vendor_name}'s edge in {', '.join(neg_details)}"
            summary_text += ")."
        else:
            summary_text = f"{v1.vendor_name} and {v2.vendor_name} are closely matched."

        if v1.qualitative_adjustment > 0:
            summary_text += f" A manual qualitative offset of {v1.qualitative_adjustment:+.1f} was applied to {v1.vendor_name}."

    # --- Agentic AI Reasoning Engine: Observe -> Understand Intent -> Reason -> Plan -> Decide -> Explain ---
    obs_context_list = []
    for rec in recommendations:
        v_name = rec.vendor_name
        v_id = rec.vendor_id
        quote = vendor_quotes_map[v_id]

        try:
            risk_score = vendor_risk_map.get(v_id, 50)
            risk_resp = client.table("vendor_risk_analysis").select("risk_level, alerts").eq("vendor_id", v_id).order("created_at", desc=True).limit(1).execute()
            risk_row = risk_resp.data[0] if risk_resp.data else {}
            risk_level = risk_row.get("risk_level") or ("HIGH" if risk_score > 70 else "MEDIUM" if risk_score > 35 else "LOW")
            risk_alerts = [a.get("message") for a in risk_row.get("alerts", [])] if isinstance(risk_row.get("alerts"), list) else []
        except Exception:
            risk_score = vendor_risk_map.get(v_id, 50)
            risk_level = "HIGH" if risk_score > 70 else "MEDIUM" if risk_score > 35 else "LOW"
            risk_alerts = []

        matching_crossdeal = None
        for opp in crossdeal_opportunities:
            if is_vendor_match(v_name, opp.vendor_name):
                matching_crossdeal = opp
                break

        matching_renewals = [ren for ren in renewal_analyses if is_vendor_match(v_name, ren.vendor_name)]

        w_val = rec.breakdown.warranty.raw if rec.breakdown.warranty else "Data Not Available"
        esg_val = rec.breakdown.esg.raw if rec.breakdown.esg else "Data Not Available"

        v_ctx = (
            f"Vendor: {v_name} (ID: {v_id})\n"
            f"- Quotation Details: Price={quote.get('price')} {quote.get('currency')}, Quantity={quote.get('quantity')} {quote.get('unit')}, Delivery={quote.get('delivery_days')} days\n"
            f"- Support: {quote.get('support_level')}, Compliance Score: {quote.get('compliance_score')}\n"
            f"- Warranty: {w_val}, ESG: {esg_val}\n"
            f"- Calculated Comparison Engine Score: {rec.final_score}/100 (Rank: {rec.rank})\n"
            f"- Risk Profile: Score {risk_score}/100 ({risk_level} Risk). Alerts: {'; '.join(risk_alerts) if risk_alerts else 'None'}\n"
        )
        if matching_crossdeal:
            v_ctx += f"- Cross-Deal: Consolidation bundling leverage is available with department overlap (unlocks {matching_crossdeal.estimated_savings_percent}% discount).\n"
        if matching_renewals:
            v_ctx += f"- Renewal Risk: Contract has renewal risk levels of {', '.join([r.risk_level for r in matching_renewals])}.\n"

        obs_context_list.append(v_ctx)

    vendors_context = "\n".join(obs_context_list)
    weights_dict = {
        "cost": w_cost,
        "risk": w_risk,
        "support": w_support,
        "delivery": w_delivery,
        "warranty": w_warranty,
        "esg": w_esg
    }

    today_str = datetime.now().date().isoformat()

    agent_data = None
    if GROQ_API_KEYS and not skip_ai:
        try:
            import time
            max_attempts = 3
            attempt = 0
            while attempt < max_attempts:
                try:
                    key = get_next_groq_key()
                    if not key:
                        raise RuntimeError("No GROQ API key available")
                    llm = ChatGroq(api_key=key, model="llama-3.1-8b-instant", temperature=0, max_retries=3)
                    prompt = _make_agent_prompt(proc_title, proc_desc, weights_dict, vendors_context, today_str)
                    response = llm.invoke(prompt)
                    response_text = response.content.strip()

                    if "```" in response_text:
                        response_text = response_text.replace("```json", "").replace("```", "").strip()

                    agent_data = json.loads(response_text)
                    break
                except Exception as e:
                    attempt += 1
                    err_str = str(e)
                    if attempt < max_attempts and ("429" in err_str or "rate limit" in err_str.lower() or "timeout" in err_str.lower()):
                        logger.warning(f"Groq API rate limit or timeout in recommendation decision engine. Retrying in 2 seconds (attempt {attempt}/{max_attempts})...")
                        time.sleep(2)
                    else:
                        raise e
        except Exception as e:
            logger.error(f"Error executing agentic reasoning: {e}")
            agent_data = None

    if agent_data:
        recommended_name = agent_data.get("recommended_vendor_name")
        rec_id = agent_data.get("recommended_vendor_id")

        matching_vendor = next((r for r in recommendations if r.vendor_id == rec_id), None)
        if not matching_vendor and recommendations:
            matching_vendor = recommendations[0]
            rec_id = matching_vendor.vendor_id
            recommended_name = matching_vendor.vendor_name

        why_selected = agent_data.get("why_selected")
        why_others = agent_data.get("why_others_not_selected")
        dyn_pri = agent_data.get("dynamic_priorities")
        crit_imp = agent_data.get("criterion_importance")
        conf_score = agent_data.get("confidence_score")

        missing_impact = agent_data.get("missing_information_impact")
        missing_list = []
        for r in recommendations:
            missing_list.extend(r.missing_information)
        missing_list = list(set(missing_list))

        if missing_impact:
            missing_list.append(f"Impact: {missing_impact}")

        risks = agent_data.get("risks_identified")
        alt_rec = agent_data.get("alternative_recommendation")
        reasoning = agent_data.get("agent_reasoning")
        plan = agent_data.get("agent_plan")

        reasoning_str = format_reasoning(reasoning)
        plan_str = format_plan(plan)
        risks_str = format_risks(risks)
        alt_str = format_alternative(alt_rec)

        agentic_summary = (
            f"### Agentic AI Recommendation Report\n\n"
            f"**Recommended Vendor**: **{recommended_name}**\n\n"
            f"#### 1. Why Selected\n{why_selected}\n\n"
            f"#### 2. Why Others Not Selected\n{why_others}\n\n"
            f"#### 3. Agent Reasoning (Observe → Understand Intent → Reason)\n{reasoning_str}\n\n"
            f"#### 4. Dynamic Procurement Plan\n{plan_str}\n\n"
            f"#### 5. Identified Risks\n{risks_str}\n\n"
            f"#### 6. Alternative Recommendation\n{alt_str}\n\n"
            f"#### 7. Dynamic Priorities & Importance\n- **Intent/Priorities**: {dyn_pri}\n- **Criterion Importance**: {crit_imp}\n\n"
            f"**Evaluation Confidence Score**: {conf_score}/1.0"
        )

        return RecommendationResponse(
            recommendations=recommendations,
            comparison_summary=agentic_summary,
            warning=warning_msg,
            recommended_vendor=recommended_name,
            why_selected=why_selected,
            why_others_not_selected=why_others,
            dynamic_priorities=dyn_pri,
            criterion_importance=crit_imp,
            confidence_score=conf_score,
            missing_information=missing_list,
            risks=risks,
            alternative_recommendations=alt_rec,
            agent_reasoning=reasoning,
            agent_plan=plan
        )

    # Fallback to rule-based agent emulator if GROQ LLM failed or bypassed
    v1 = recommendations[0] if recommendations else None
    recommended_name = v1.vendor_name if v1 else "None"

    why_selected_fallback = (
        f"{recommended_name} is recommended by the comparison engine because they achieved the highest "
        f"overall scoring of {v1.final_score}/100. Strengths include: cost scoring ({v1.breakdown.cost.score}/100) "
        f"and risk safety ({v1.breakdown.risk.score}/100)."
    ) if v1 else "No vendor quotes found."

    others_fallback = []
    for r in recommendations[1:]:
        others_fallback.append(f"{r.vendor_name} (Score {r.final_score}/100) was not selected because they scored lower than {v1.vendor_name}.")
    why_others_fallback = " ".join(others_fallback) if others_fallback else "No other vendors compared."

    missing_list = []
    for r in recommendations:
        missing_list.extend(r.missing_information)
    missing_list = list(set(missing_list))

    risks_fallback = v1.explanation if v1 else "No risks identified."
    alt_fallback = recommendations[1].vendor_name if len(recommendations) > 1 else "None available"

    agent_reasoning_fallback = (
        f"Observed that {recommended_name} holds the advantage in cost-value ratios. "
        f"We understand the manager's intent was to balance factors with weights: Cost={w_cost}%, Risk={w_risk}%, Support={w_support}%, Delivery={w_delivery}%. "
        f"We planned to shortlist vendors with scores above 50/100, which selects {recommended_name}."
    )

    agent_plan_fallback = (
        f"Shortlist {recommended_name} for procurement. "
        f"Request finalized contract templates verifying support levels."
    )

    fallback_summary = (
        f"### Agentic Recommendation Report (Fallback Mode)\n\n"
        f"**Recommended Vendor**: **{recommended_name}**\n\n"
        f"#### 1. Why Selected\n{why_selected_fallback}\n\n"
        f"#### 2. Why Others Not Selected\n{why_others_fallback}\n\n"
        f"#### 3. Agent Reasoning (Rule-Based Fallback)\n{agent_reasoning_fallback}\n\n"
        f"#### 4. Action Plan\n{agent_plan_fallback}\n\n"
        f"#### 5. Identified Risks & Explanations\n{risks_fallback}\n\n"
        f"#### 6. Alternative Recommendation\n{alt_fallback}\n\n"
        f"**Evaluation Confidence Score**: {v1.confidence_score if v1 else 1.0}/1.0"
    )

    return RecommendationResponse(
        recommendations=recommendations,
        comparison_summary=fallback_summary,
        warning=warning_msg,
        recommended_vendor=recommended_name,
        why_selected=why_selected_fallback,
        why_others_not_selected=why_others_fallback,
        dynamic_priorities=f"Cost={w_cost}%, Risk={w_risk}%, Support={w_support}%, Delivery={w_delivery}%, Warranty={w_warranty}%, ESG={w_esg}%.",
        criterion_importance="Cost dominates scoring ratios" if w_cost > 30 else "Balanced evaluation of criteria",
        confidence_score=v1.confidence_score if v1 else 1.0,
        missing_information=missing_list,
        risks=risks_fallback,
        alternative_recommendations=alt_fallback,
        agent_reasoning=agent_reasoning_fallback,
        agent_plan=agent_plan_fallback
    )


async def apply_recommendation(request: ApplyRecommendationRequest) -> ApplyRecommendationResponse:
    procurement_id = str(request.procurement_id)
    selected_vendor_id = request.selected_vendor_id
    weights = request.weights
    reasoning = request.reasoning

    client = supabase_service or supabase

    try:
        current = client.table("procurements").select("description,title").eq("id", procurement_id).execute()
        current_data = current.data[0] if current.data else {}
        orig_desc = current_data.get("description") or ""
        orig_title = current_data.get("title") or "Procurement"

        vendor_resp = client.table("vendors").select("vendor_name").eq("id", selected_vendor_id).execute()
        vendor_name = vendor_resp.data[0].get("vendor_name") if vendor_resp.data else "Selected Vendor"

        new_desc = (
            f"Recommendation applied: Selected {vendor_name}. "
            f"Decision weights: Cost={weights.cost}%, Risk={weights.risk}%, Support={weights.support}%, Delivery={weights.delivery}%, "
            f"Warranty={getattr(weights, 'warranty', 0.0)}%, ESG={getattr(weights, 'esg', 0.0)}%. "
            f"Reasoning: {reasoning}. \n"
            f"[Original Description]: {orig_desc}"
        )

        client.table("procurements").update({
            "status": "completed",
            "description": new_desc[:1000]
        }).eq("id", procurement_id).execute()

    except Exception as e:
        logger.error(f"Failed to update procurement table: {e}")
        vendor_name = "Selected Vendor"
        orig_title = "Procurement"

    audit_log_id = ""
    try:
        audit_payload = {
            "agent_name": "Decision Engine",
            "action_type": "apply_recommendation",
            "input_payload": {
                "procurement_id": procurement_id,
                "procurement_title": orig_title,
                "selected_vendor_id": selected_vendor_id,
                "selected_vendor_name": vendor_name,
                "weights": {
                    "cost": weights.cost,
                    "risk": weights.risk,
                    "support": weights.support,
                    "delivery": weights.delivery,
                    "warranty": getattr(weights, "warranty", 0.0),
                    "esg": getattr(weights, "esg", 0.0)
                }
            },
            "output_payload": {
                "status": "success",
                "message": f"Successfully locked in decision: Selected {vendor_name}."
            },
            "reasoning": reasoning
        }

        insert_resp = client.table("audit_logs").insert(audit_payload).execute()
        if insert_resp.data:
            audit_log_id = str(insert_resp.data[0].get("id", ""))
    except Exception as e:
        logger.error(f"Failed to write audit logs to Supabase: {e}")
        raise Exception(f"Failed to apply recommendation and log decision: {e}")

    return ApplyRecommendationResponse(
        status="success",
        message=f"Decision successfully applied. Selected vendor {vendor_name} for procurement.",
        procurement_id=procurement_id,
        selected_vendor_id=selected_vendor_id,
        audit_log_id=audit_log_id
    )
