from typing import List, Dict, Any, Tuple
from uuid import UUID
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

# Mapping support level strings to numerical scores
def map_support_score(support_str: str) -> float:
    support_lower = str(support_str or "").lower()
    if not support_lower:
        return 50.0
    
    # Check for highest levels
    if any(keyword in support_lower for keyword in ["24/7", "24x7", "premier", "premium", "gold", "platinum", "dedicated"]):
        return 100.0
    if any(keyword in support_lower for keyword in ["business", "silver", "priority", "9am to 6pm", "9 to 6"]):
        return 80.0
    if any(keyword in support_lower for keyword in ["standard", "bronze", "next business day"]):
        return 60.0
    if any(keyword in support_lower for keyword in ["basic", "email only", "standard hours"]):
        return 40.0
    
    return 50.0


async def get_recommendation_analysis(request: RecommendationRequest) -> RecommendationResponse:
    procurement_id = str(request.procurement_id)
    weights = request.weights
    qual_adjustments = request.qualitative_adjustments or {}
    
    client = supabase_service or supabase
    
    # 1. Fetch vendors linked to procurement
    try:
        vendors_resp = client.table("vendors").select("*").eq("procurement_id", procurement_id).execute()
        vendors = vendors_resp.data or []
    except Exception as e:
        logger.error(f"Error fetching vendors from Supabase: {e}")
        vendors = []
        
    # Fallback to all vendors if none found under specific procurement_id (robust fallback)
    if not vendors:
        try:
            vendors_resp = client.table("vendors").select("*").execute()
            vendors = vendors_resp.data or []
            logger.info(f"Fallback: Fetched all {len(vendors)} vendors because procurement_id {procurement_id} returned 0 results.")
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
            # Simple policy: keep the newest or the first quote
            if v_id not in vendor_quotes_map:
                vendor_quotes_map[v_id] = quote

    # 3. Filter down to vendors that actually have quotes
    active_vendors = [v for v in vendors if v["id"] in vendor_quotes_map]
    
    if not active_vendors:
        return RecommendationResponse(
            recommendations=[],
            comparison_summary="No active quotes found for the compared vendors. Please upload quotes to run the simulator."
        )

    # 4. Fetch risk profiles & run optimization analysis
    vendor_risk_map: Dict[str, int] = {}
    for v in active_vendors:
        v_id = v["id"]
        try:
            risk_data = await get_latest_vendor_risk(v_id, client=client)
            vendor_risk_map[v_id] = risk_data.get("final_risk_score", 50)
        except Exception as e:
            logger.warning(f"Failed to fetch risk score for vendor {v_id}, defaulting to 50: {e}")
            vendor_risk_map[v_id] = 50

    # Retrieve optimization data to influence the final recommendation
    try:
        from .renewal_service import get_renewal_analysis
        from .crossdeal_service import get_crossdeal_analysis
        renewal_analyses, _ = await get_renewal_analysis()
        crossdeal_opportunities, _ = await get_crossdeal_analysis()
    except Exception as e:
        logger.warning(f"Failed to fetch optimization data for recommendation pipeline: {e}")
        renewal_analyses, crossdeal_opportunities = [], []

    def is_vendor_match(name1: str, name2: str) -> bool:
        n1 = str(name1 or "").lower().strip()
        n2 = str(name2 or "").lower().strip()
        return n1 in n2 or n2 in n1

    # 5. Extract metrics for normalization (applying cross-deal discounts to pricing for scoring influence)
    prices_for_scoring = []
    prices_raw = []
    delivery_times = []
    
    for v in active_vendors:
        v_id = v["id"]
        v_name = v["vendor_name"]
        quote = vendor_quotes_map[v_id]
        
        raw_price = float(quote.get("price", 0) or 0)
        prices_raw.append(raw_price)
        
        # Apply cross-deal bundling discount if opportunity exists
        discount = 0.0
        for opp in crossdeal_opportunities:
            if is_vendor_match(v_name, opp.vendor_name):
                discount = opp.estimated_savings_percent / 100.0
                break
        
        prices_for_scoring.append(raw_price * (1.0 - discount))
        delivery_times.append(float(quote.get("delivery_days", 0) or 0))
    
    min_price_for_scoring = min(prices_for_scoring) if prices_for_scoring else 0.0
    min_delivery = min(delivery_times) if delivery_times else 0.0
    max_delivery = max(delivery_times) if delivery_times else 0.0

    # 6. Apply Weights & Compute Scores
    w_cost = weights.cost
    w_risk = weights.risk
    w_support = weights.support
    w_delivery = weights.delivery
    
    w_total = w_cost + w_risk + w_support + w_delivery
    warning_msg = None
    if w_total == 0:
        w_cost = w_risk = w_support = w_delivery = 25.0
        w_total = 100.0
        warning_msg = "All weights were set to 0. Internally defaulted to equal weights (25% each)."

    recommendations: List[VendorRecommendation] = []
    
    for v in active_vendors:
        v_id = v["id"]
        v_name = v["vendor_name"]
        quote = vendor_quotes_map[v_id]
        
        # Qualitative offset
        qual_adj = float(qual_adjustments.get(v_id, 0.0))
        qual_adj = max(-20.0, min(20.0, qual_adj)) # Clamped

        # Match optimization inputs
        matching_crossdeal = None
        for opp in crossdeal_opportunities:
            if is_vendor_match(v_name, opp.vendor_name):
                matching_crossdeal = opp
                break
                
        matching_renewals = [ren for ren in renewal_analyses if is_vendor_match(v_name, ren.vendor_name)]

        # Cost Score (Ratio-based using effective/scoring price)
        raw_price = float(quote.get("price", 0) or 0)
        crossdeal_discount = (matching_crossdeal.estimated_savings_percent / 100.0) if matching_crossdeal else 0.0
        price_for_scoring = raw_price * (1.0 - crossdeal_discount)
        
        if price_for_scoring > 0:
            cost_score = 100.0 * (min_price_for_scoring / price_for_scoring)
        else:
            cost_score = 100.0
            
        # Risk Score (Safety score = 100 - risk_score, higher is safer/better)
        raw_risk = float(vendor_risk_map.get(v_id, 50))
        
        # Apply Renewal Risk penalties to raw risk
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
        
        # Support Score (Mapped from string)
        raw_support = quote.get("support_level", "Basic")
        support_score = map_support_score(raw_support)
        
        # Delivery Score (Min-max, shorter is better)
        raw_delivery = float(quote.get("delivery_days", 0) or 0)
        if max_delivery != min_delivery:
            delivery_score = 100.0 * ((max_delivery - raw_delivery) / (max_delivery - min_delivery))
        else:
            delivery_score = 100.0

        # Weighted values
        cost_contrib = (cost_score * w_cost) / w_total
        risk_contrib = (risk_score * w_risk) / w_total
        support_contrib = (support_score * w_support) / w_total
        delivery_contrib = (delivery_score * w_delivery) / w_total
        
        base_score = cost_contrib + risk_contrib + support_contrib + delivery_contrib
        
        # Add Strategic Consolidation bonus (+5.0 points to final score if cross-deal bundling opportunity exists)
        strategic_bonus = 5.0 if matching_crossdeal else 0.0
        
        final_score = round(max(0.0, min(100.0, base_score + qual_adj + strategic_bonus)), 1)
        
        # Single vendor explanation
        single_expl = (
            f"{v_name} scored {final_score}/100. Strengths: "
            f"Cost score is {cost_score:.1f}/100 (raw price: ${raw_price:,.2f}), "
            f"Risk safety is {risk_score:.1f}/100 (raw risk: {raw_risk:.0f}/100), "
            f"Support rating is {support_score:.1f}/100 (level: {raw_support}), "
            f"Delivery rating is {delivery_score:.1f}/100 (delivery: {raw_delivery:.0f} days)."
        )
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
            rank=0, # Will assign after sorting
            breakdown=ScoreBreakdown(
                cost=ScoreComponent(raw=raw_price, score=round(cost_score, 1), weighted=round(cost_contrib, 1)),
                risk=ScoreComponent(raw=raw_risk, score=round(risk_score, 1), weighted=round(risk_contrib, 1)),
                support=ScoreComponent(raw=raw_support, score=round(support_score, 1), weighted=round(support_contrib, 1)),
                delivery=ScoreComponent(raw=raw_delivery, score=round(delivery_score, 1), weighted=round(delivery_contrib, 1))
            ),
            explanation=single_expl,
            qualitative_adjustment=qual_adj
        ))

    # 7. Sort and Rank (Primary: final_score desc, Secondary: raw price asc, Tertiary: name alphabetical)
    def sorting_key(item: VendorRecommendation) -> Tuple[float, float, str]:
        # raw price is inside breakdown.cost.raw
        price_val = float(item.breakdown.cost.raw)
        return (-item.final_score, price_val, item.vendor_name)

    recommendations.sort(key=sorting_key)
    
    for idx, rec in enumerate(recommendations, start=1):
        rec.rank = idx

    # 8. Generate Comparative Summary Text (Explainability Engine)
    summary_text = ""
    if len(recommendations) == 1:
        summary_text = (
            f"{recommendations[0].vendor_name} is the only vendor with an uploaded quote. "
            "Add more quotes to compare alternative choices."
        )
    else:
        # Compare #1 and #2
        v1 = recommendations[0]
        v2 = recommendations[1]
        
        # Calculate contribution differences
        diffs = {
            "Cost": v1.breakdown.cost.weighted - v2.breakdown.cost.weighted,
            "Risk Safety": v1.breakdown.risk.weighted - v2.breakdown.risk.weighted,
            "Support": v1.breakdown.support.weighted - v2.breakdown.support.weighted,
            "Delivery": v1.breakdown.delivery.weighted - v2.breakdown.delivery.weighted,
        }
        
        favors_v1 = [cat for cat, d in diffs.items() if d > 0]
        favors_v2 = [cat for cat, d in diffs.items() if d < 0]
        
        # Sort factors by impact
        favors_v1.sort(key=lambda cat: abs(diffs[cat]), reverse=True)
        favors_v2.sort(key=lambda cat: abs(diffs[cat]), reverse=True)
        
        # Base explanation
        if favors_v1:
            pos_str = " and ".join(favors_v1[:2]).lower()
            summary_text = f"{v1.vendor_name} ranked higher than {v2.vendor_name} because {pos_str} were weighted more heavily."
            
            # Detailed breakdown text
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

        # Mention qualitative adjustment if it flipped the scale
        if v1.qualitative_adjustment > 0:
            summary_text += f" A manual qualitative offset of {v1.qualitative_adjustment:+.1f} was applied to {v1.vendor_name}."

    return RecommendationResponse(
        recommendations=recommendations,
        comparison_summary=summary_text,
        warning=warning_msg
    )


async def apply_recommendation(request: ApplyRecommendationRequest) -> ApplyRecommendationResponse:
    procurement_id = str(request.procurement_id)
    selected_vendor_id = request.selected_vendor_id
    weights = request.weights
    reasoning = request.reasoning
    
    client = supabase_service or supabase
    
    # 1. Update the procurement table (Set status = 'completed' and append chosen vendor in description)
    try:
        # Fetch current record first to preserve current description if any
        current = client.table("procurements").select("description,title").eq("id", procurement_id).execute()
        current_data = current.data[0] if current.data else {}
        orig_desc = current_data.get("description") or ""
        orig_title = current_data.get("title") or "Procurement"
        
        # Fetch vendor name
        vendor_resp = client.table("vendors").select("vendor_name").eq("id", selected_vendor_id).execute()
        vendor_name = vendor_resp.data[0].get("vendor_name") if vendor_resp.data else "Selected Vendor"
        
        new_desc = (
            f"Recommendation applied: Selected {vendor_name}. "
            f"Decision weights: Cost={weights.cost}%, Risk={weights.risk}%, Support={weights.support}%, Delivery={weights.delivery}%. "
            f"Reasoning: {reasoning}. \n"
            f"[Original Description]: {orig_desc}"
        )
        
        client.table("procurements").update({
            "status": "completed",
            "description": new_desc[:1000] # Limit size to prevent DB constraints
        }).eq("id", procurement_id).execute()
        
    except Exception as e:
        logger.error(f"Failed to update procurement table: {e}")
        # Continue to insert audit log even if update table fails
        vendor_name = "Selected Vendor"
        orig_title = "Procurement"
        
    # 2. Insert into audit_logs table
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
                    "delivery": weights.delivery
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
