from typing import List, Dict, Tuple
from ..supabase_client import supabase, supabase_service
from ..models.optimization import DealOpportunity
from .audit_service import log_agent_execution
from .savings_engine import estimate_enterprise_savings, generate_enterprise_negotiation_rationale
from collections import defaultdict
import logging
import asyncio

logger = logging.getLogger("uvicorn.error")


from typing import List, Dict, Tuple
from ..supabase_client import supabase, supabase_service
from ..models.optimization import DealOpportunity
from .audit_service import log_agent_execution
from .savings_engine import estimate_enterprise_savings, generate_enterprise_negotiation_rationale
from collections import defaultdict
import logging
import asyncio

logger = logging.getLogger("uvicorn.error")


_PROCUREMENTS_CACHE = {"timestamp": 0.0, "data": []}

async def fetch_procurements_from_supabase() -> List[dict]:
    """
    Fetch active procurements joined with vendor, quote, and contract data strictly from Supabase using parallel async fetching.
    """
    import time
    now = time.time()

    if now - _PROCUREMENTS_CACHE["timestamp"] < 30.0:
        return _PROCUREMENTS_CACHE["data"]
        
    try:
        client = supabase_service or supabase
        
        def _fetch_vendors():
            return client.table("vendors").select("*").execute().data or []

        def _fetch_procurements():
            return client.table("procurements").select("*").execute().data or []

        def _fetch_quotes():
            return client.table("vendor_quotes").select("vendor_id, price").execute().data or []

        def _fetch_contracts():
            return client.table("contracts").select("*").execute().data or []

        vendors, procs, quotes, contracts = await asyncio.wait_for(
            asyncio.gather(
                asyncio.to_thread(_fetch_vendors),
                asyncio.to_thread(_fetch_procurements),
                asyncio.to_thread(_fetch_quotes),
                asyncio.to_thread(_fetch_contracts)
            ),
            timeout=4.0
        )

        if not vendors and not procs and not contracts:
            return []

        procs_map = {p["id"]: p for p in procs if isinstance(p, dict) and "id" in p}
        quotes_map = {q["vendor_id"]: float(q.get("price", 0) or 0) for q in quotes if isinstance(q, dict) and "vendor_id" in q}

        synthesized = []
        for v in vendors:
            v_id = v.get("id")
            p_id = v.get("procurement_id")
            proc = procs_map.get(p_id, {})
            
            v_name = str(v.get("vendor_name") or "").strip()
            if not v_name or v_name.lower() == "unknown vendor":
                continue

            dept = (
                proc.get("department")
                or proc.get("dept")
                or proc.get("business_unit")
                or v.get("department")
                or proc.get("category")
                or v.get("category")
                or "Corporate"
            )
            cat = proc.get("category") or v.get("category") or "Hardware"
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

        for c in contracts:
            if not isinstance(c, dict):
                continue
            c_vendor = str(c.get("vendor_name") or "").strip()
            if not c_vendor or c_vendor.lower() == "unknown vendor":
                continue
            c_dept = c.get("department") or c.get("business_unit") or c.get("category") or "Operations"
            c_val = float(c.get("contract_value") or c.get("value") or 0.0)
            
            synthesized.append({
                "id": c.get("id"),
                "vendor_id": c.get("vendor_id") or c.get("id"),
                "vendor_name": c_vendor,
                "department": c_dept,
                "category": c.get("category", "Software Services"),
                "procurement_value": c_val,
                "has_quote": True,
                "status": "active"
            })

        _PROCUREMENTS_CACHE["timestamp"] = now
        _PROCUREMENTS_CACHE["data"] = synthesized
        return synthesized

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

    from .savings_engine import format_savings_range
    estimated_savings_range = format_savings_range(savings_amount)

    return DealOpportunity(
        vendor_name=vendor_name,
        departments=departments,
        active_procurements=len(procurements),
        total_procurement_value=total_value,
        estimated_savings_percent=savings_percent,
        estimated_savings_amount=savings_amount,
        estimated_savings_range=estimated_savings_range,
        recommendation=recommendation,
        confidence_score=confidence_score
    )


async def get_crossdeal_analysis(skip_ai: bool = False) -> Tuple[List[DealOpportunity], dict]:
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
            departments_list = [
                p.get("department")
                for p in vendor_procurements
                if p.get("department")
            ]
            unique_departments = set(departments_list)

            # If vendor has multiple procurements/contracts in the database but department values were identical/defaulted,
            # derive department contexts from category or procurement/contract title in DB
            if len(unique_departments) < 2 and len(vendor_procurements) >= 2:
                for p in vendor_procurements:
                    derived = p.get("category") or p.get("title")
                    if derived and derived != p.get("department"):
                        p["department"] = derived
                unique_departments = set(p.get("department") for p in vendor_procurements if p.get("department"))

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
    if not skip_ai:
        try:
            from .llm_narrative_service import enrich_crossdeal_opportunities_with_llm
            opportunities = await enrich_crossdeal_opportunities_with_llm(opportunities)
        except Exception as e:
            logger.warning(f"Unable to run LLM narrative enrichment on cross-deal opportunities: {e}")

    # Generate concise, human-readable audit-style description
    if opportunities:
        top_vendor = opportunities[0].vendor_name
        depts_str = " and ".join(opportunities[0].departments) if opportunities[0].departments else "multiple departments"
        audit_reasoning = (
            f"Evaluated multi-department vendor procurement data across active contracts. "
            f"Identified volume overlap for {top_vendor} across {depts_str} and recommended consolidating engagements under a Master Service Agreement."
        )
    else:
        audit_reasoning = (
            "Analyzed active vendor procurements across all enterprise departments. "
            "Determined no multi-department vendor overlaps currently exist; single-department vendor contracts remain active."
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






