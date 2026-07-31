from typing import List, Dict, Tuple
from ..supabase_client import supabase, supabase_service
from ..models.optimization import DealOpportunity
from .audit_service import log_agent_execution
from .savings_engine import estimate_enterprise_savings, generate_enterprise_negotiation_rationale
from collections import defaultdict
import logging
import asyncio

logger = logging.getLogger("uvicorn.error")


async def fetch_procurements_from_supabase() -> List[dict]:
    """
    Fetch active procurements joined with vendor and quote data with 1.2s timeout resilience.
    """
    try:
        client = supabase_service or supabase
        
        def _query():
            vendors_resp = client.table("vendors").select("*").execute()
            vendors = vendors_resp.data or []
            if not vendors:
                return []

            proc_resp = client.table("procurements").select("*").execute()
            procs_map = {p["id"]: p for p in (proc_resp.data or [])}

            quotes_resp = client.table("vendor_quotes").select("vendor_id, price").execute()
            quotes_map = {q["vendor_id"]: float(q.get("price", 0) or 0) for q in (quotes_resp.data or [])}

            synthesized = []
            for v in vendors:
                v_id = v["id"]
                p_id = v.get("procurement_id")
                proc = procs_map.get(p_id, {})
                
                v_name = str(v.get("vendor_name") or "").strip()
                if not v_name or v_name.lower() == "unknown vendor":
                    continue

                dept = proc.get("department", "Corporate")
                cat = proc.get("category", "Hardware")
                quote_price = quotes_map.get(v_id, 0.0)

                synthesized.append({
                    "id": p_id or v_id,
                    "vendor_id": v_id,
                    "vendor_name": v_name,
                    "department": dept,
                    "category": cat,
                    "procurement_value": quote_price,
                    "has_quote": v_id in quotes_map,
                    "status": proc.get("status", "active")
                })

            return synthesized

        return await asyncio.wait_for(asyncio.to_thread(_query), timeout=1.2)
            
    except Exception as e:
        logger.warning(f"Unable to fetch procurements from Supabase: {e}")
        return []



async def fetch_vendor_name(vendor_id: str) -> str:
    """Fetch vendor name by vendor_id."""
    try:
        client = supabase_service or supabase
        response = (
            client.table("vendors")
            .select("vendor_name")
            .eq("id", vendor_id)
            .execute()
        )

        if response.data and len(response.data) > 0:
            return response.data[0].get("vendor_name", "Unknown Vendor")

        return vendor_id or "Unknown Vendor"

    except Exception:
        return vendor_id or "Unknown Vendor"


async def group_procurements_by_vendor(
    procurements: List[dict]
) -> Dict[str, List[dict]]:
    """Group procurements by vendor name for consolidation analysis."""
    grouped = defaultdict(list)

    for procurement in procurements:
        v_name = (
            procurement.get("vendor_name")
            or procurement.get("vendor_id")
        )
        if v_name:
            clean_key = str(v_name).strip()
            grouped[clean_key].append(procurement)

    return dict(grouped)


async def analyze_crossdeal_opportunity(
    vendor_key: str,
    procurements: List[dict]
) -> DealOpportunity:
    """
    Analyze cross-deal opportunity using the Enterprise Savings Engine.
    """
    departments = sorted(
        list(
            set(
                p.get("department", "")
                for p in procurements
                if p.get("department")
            )
        )
    )

    total_value = sum(
        float(p.get("procurement_value", 0) or 0)
        for p in procurements
    )

    vendor_name = procurements[0].get("vendor_name", vendor_key)
    category = procurements[0].get("category", "Software")

    # Call Enterprise Savings Engine
    savings_percent, savings_amount, confidence_score = estimate_enterprise_savings(
        vendor_name=vendor_name,
        category=category,
        departments=departments,
        procurements=procurements
    )

    # Generate enterprise rationale text
    recommendation = generate_enterprise_negotiation_rationale(
        vendor_name=vendor_name,
        category=category,
        departments=departments,
        total_value=total_value,
        savings_percent=savings_percent,
        savings_amount=savings_amount
    )

    return DealOpportunity(
        vendor_name=vendor_name,
        departments=departments,
        active_procurements=len(procurements),
        total_procurement_value=total_value,
        estimated_savings_percent=savings_percent,
        estimated_savings_amount=savings_amount,
        recommendation=recommendation,
        confidence_score=confidence_score
    )


async def get_crossdeal_analysis() -> Tuple[List[DealOpportunity], dict]:
    """
    Analyze procurements for cross-deal negotiation opportunities.
    """
    procurements = await fetch_procurements_from_supabase()

    if not procurements:
        return [], {
            "total_vendors_analyzed": 0,
            "vendors_with_opportunities": 0,
            "total_estimated_savings": 0.0,
            "summary": "No active procurement data available for cross-deal analysis."
        }

    grouped = await group_procurements_by_vendor(procurements)
    opportunities: List[DealOpportunity] = []

    for vendor_key, vendor_procurements in grouped.items():
        try:
            unique_departments = set(
                p.get("department")
                for p in vendor_procurements
                if p.get("department")
            )

            if len(unique_departments) < 2:
                continue

            opportunity = await analyze_crossdeal_opportunity(
                vendor_key,
                vendor_procurements
            )
            opportunities.append(opportunity)

        except Exception as e:
            logger.error(f"Error analyzing vendor {vendor_key}: {e}")
            continue

    opportunities.sort(
        key=lambda x: x.estimated_savings_amount,
        reverse=True
    )

    total_estimated_savings = sum(
        o.estimated_savings_amount
        for o in opportunities
    )

    if not opportunities:
        summary = (
            "No multi-department vendor overlaps detected. "
            "All active vendor engagements are scoped to single departments."
        )
    elif len(opportunities) == 1:
        opp = opportunities[0]
        summary = (
            f"1 vendor ({opp.vendor_name}) spans {len(opp.departments)} departments "
            f"with ~${total_estimated_savings:,.2f} in potential benchmark savings."
        )
    else:
        summary = (
            f"{len(opportunities)} vendors have multi-department procurement opportunities totaling "
            f"~${total_estimated_savings:,.2f} in estimated enterprise savings."
        )

    summary_dict = {
        "total_vendors_analyzed": len(grouped),
        "vendors_with_opportunities": len(opportunities),
        "total_estimated_savings": total_estimated_savings,
        "summary": summary
    }

    # Enrich bundle recommendations using grounded LLM presentation layer
    try:
        from .llm_narrative_service import enrich_crossdeal_opportunities_with_llm
        opportunities = await enrich_crossdeal_opportunities_with_llm(opportunities)
    except Exception as e:
        logger.warning(f"Unable to run LLM narrative enrichment on cross-deal opportunities: {e}")

    # Generate concise audit-style summary message
    if total_estimated_savings >= 1000000:
        savings_formatted = f"${total_estimated_savings / 1000000:.2f}M"
    elif total_estimated_savings >= 1000:
        savings_formatted = f"${total_estimated_savings / 1000:.1f}K"
    else:
        savings_formatted = f"${total_estimated_savings:,.2f}"

    if opportunities:
        audit_reasoning = (
            f"Cross-deal analysis completed. Identified {len(opportunities)} vendor consolidation opportunity with projected savings of {savings_formatted}."
        )
    else:
        audit_reasoning = (
            f"Cross-deal analysis completed. Evaluated {len(grouped)} vendors. No multi-department vendor consolidation opportunities detected."
        )

    await log_agent_execution(
        agent_name="Cross Deal Negotiator",
        action_type="crossdeal_analysis",
        input_payload={
            "source": "procurements table",
            "total_procurements_analyzed": len(procurements)
        },
        output_payload={
            "total_vendors_analyzed": len(grouped),
            "vendors_with_opportunities": len(opportunities),
            "total_estimated_savings": total_estimated_savings,
            "opportunities_found": [
                {
                    "vendor": o.vendor_name,
                    "departments": o.departments,
                    "savings": o.estimated_savings_amount
                } for o in opportunities
            ]
        },
        reasoning=audit_reasoning
    )

    return opportunities, summary_dict





