from typing import List, Dict, Tuple
from ..supabase_client import supabase, supabase_service
from ..models.optimization import DealOpportunity
from .audit_service import log_agent_execution
from collections import defaultdict


def calculate_savings_percentage(num_departments: int) -> int:
    """
    Calculate estimated savings percentage based on number of departments.

    2 departments = 5%
    3 departments = 10%
    4+ departments = 15%
    """
    if num_departments >= 4:
        return 15
    elif num_departments == 3:
        return 10
    elif num_departments >= 2:
        return 5
    else:
        return 0


def generate_crossdeal_recommendation(
    num_departments: int,
    total_value: float,
    savings_percent: int
) -> str:
    """Generate actionable recommendation for cross-deal opportunity."""
    if num_departments < 2:
        return "Single department procurement. No consolidation opportunity."

    savings_amount = total_value * (savings_percent / 100)

    if num_departments >= 4:
        return (
            f"HIGH-VALUE OPPORTUNITY: Consolidate {num_departments} departments' "
            f"negotiations for ~${savings_amount:,.2f} savings "
            f"({savings_percent}% reduction)."
        )
    elif num_departments == 3:
        return (
            f"Consolidate {num_departments} departments' procurements with this "
            f"vendor to unlock ~${savings_amount:,.2f} in negotiation leverage "
            f"({savings_percent}% potential savings)."
        )
    else:
        return (
            f"Bundle procurement across {num_departments} departments for stronger "
            f"negotiation leverage and approximately ${savings_amount:,.2f} in savings."
        )


async def fetch_procurements_from_supabase() -> List[dict]:
    """
    Fetch all active procurements from Supabase, joining with vendor and quote data.
    """
    try:
        client = supabase_service or supabase
        
        # 1. Fetch active procurements
        proc_response = (
            client.table("procurements")
            .select("*")
            .eq("status", "active")
            .execute()
        )
        procurements = proc_response.data if proc_response.data else []
        if not procurements:
            return []
            
        # 2. Fetch all vendors associated with these procurements
        procurement_ids = [p["id"] for p in procurements]
        vendors_response = (
            client.table("vendors")
            .select("*")
            .in_("procurement_id", procurement_ids)
            .execute()
        )
        vendors = vendors_response.data if vendors_response.data else []
        if not vendors:
            return []
            
        # 3. Fetch all quotes associated with these vendors
        vendor_ids = [v["id"] for v in vendors]
        quotes_response = (
            client.table("vendor_quotes")
            .select("*")
            .in_("vendor_id", vendor_ids)
            .execute()
        )
        quotes = quotes_response.data if quotes_response.data else []
        
        # Create a mapping of vendor_id -> quote price
        vendor_quote_price_map = {}
        for q in quotes:
            v_id = q.get("vendor_id")
            if v_id and v_id not in vendor_quote_price_map:
                vendor_quote_price_map[v_id] = float(q.get("price", 0) or 0)
                
        # 4. Synthesize the records as expected by the negotiator agent
        synthesized_procurements = []
        for vendor in vendors:
            v_id = vendor["id"]
            p_id = vendor["procurement_id"]
            
            # Find the corresponding procurement
            procurement = next((p for p in procurements if p["id"] == p_id), None)
            if not procurement:
                continue
                
            quote_price = vendor_quote_price_map.get(v_id, 0.0)
            
            # Synthesize record
            rec = {
                "id": procurement["id"],
                "vendor_id": v_id,
                "vendor_name": vendor["vendor_name"],
                "department": procurement.get("department", "Unknown"),
                "category": procurement.get("category", "Software"),
                "procurement_value": quote_price,
                "status": procurement.get("status", "active")
            }
            synthesized_procurements.append(rec)
            
        return synthesized_procurements
    except Exception as e:
        raise Exception(
            f"Failed to fetch procurements from Supabase: {str(e)}"
        )


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
            return response.data[0].get(
                "vendor_name",
                "Unknown Vendor"
            )

        return vendor_id or "Unknown Vendor"

    except Exception:
        return vendor_id or "Unknown Vendor"


async def group_procurements_by_vendor(
    procurements: List[dict]
) -> Dict[str, List[dict]]:
    """
    Group procurements by vendor identifier or fallback grouping key.

    Args:
        procurements: List of procurement records

    Returns:
        Dict mapping a vendor or category key to list of procurements
    """
    grouped = defaultdict(list)

    for procurement in procurements:
        vendor_key = (
            procurement.get("vendor_name")
            or procurement.get("vendor_id")
            or procurement.get("category")
        )

        if vendor_key:
            grouped[vendor_key].append(procurement)

    return dict(grouped)


async def analyze_crossdeal_opportunity(
    vendor_id: str,
    procurements: List[dict]
) -> DealOpportunity:
    """
    Analyze cross-deal opportunity for a vendor with multiple departments.

    Args:
        vendor_id: Vendor ID
        procurements: List of procurements from this vendor

    Returns:
        DealOpportunity with analysis and recommendation
    """
    # Extract unique departments and calculate totals
    departments = list(
        set(
            p.get("department", "")
            for p in procurements
            if p.get("department")
        )
    )

    total_value = sum(
        p.get("procurement_value", 0)
        for p in procurements
    )

    num_departments = len(departments)

    # Calculate savings
    savings_percent = calculate_savings_percentage(num_departments)
    savings_amount = total_value * (savings_percent / 100)

    # Fetch vendor name
    vendor_name = await fetch_vendor_name(vendor_id)

    # Generate recommendation
    recommendation = generate_crossdeal_recommendation(
        num_departments,
        total_value,
        savings_percent
    )

    # Calculate confidence score
    confidence_score = min(75.0 + (num_departments - 1) * 5.0, 95.0)

    return DealOpportunity(
        vendor_name=vendor_name,
        departments=sorted(departments),
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

    Returns:
        Tuple of (list of DealOpportunity, summary dict)
    """
    procurements = await fetch_procurements_from_supabase()

    if not procurements:
        return [], {
            "total_vendors_analyzed": 0,
            "vendors_with_opportunities": 0,
            "total_estimated_savings": 0.0,
            "summary": "No active procurements found in the system."
        }

    # Group by vendor
    grouped = await group_procurements_by_vendor(procurements)

    # Analyze opportunities (only vendors with 2+ departments)
    opportunities: List[DealOpportunity] = []

    for vendor_id, vendor_procurements in grouped.items():
        try:
            # Find unique departments using this vendor
            unique_departments = sorted(
                set(
                    procurement.get("department")
                    for procurement in vendor_procurements
                    if procurement.get("department")
                )
            )

            department_count = len(unique_departments)

            # Prevent false opportunities
            if department_count < 2:
                continue

            opportunity = await analyze_crossdeal_opportunity(
                vendor_id,
                vendor_procurements
            )

            opportunities.append(opportunity)

        except Exception as e:
            # Log error but continue processing other vendors
            print(
                f"Error analyzing vendor {vendor_id}: {str(e)}"
            )
            continue

    # Sort opportunities by savings amount (descending)
    opportunities.sort(
        key=lambda x: x.estimated_savings_amount,
        reverse=True
    )

    # Calculate totals
    total_estimated_savings = sum(
        o.estimated_savings_amount
        for o in opportunities
    )

    # Generate summary
    if not opportunities:
        summary = (
            "No cross-department procurement opportunities identified. "
            "Each vendor is only used by one department."
        )
    elif len(opportunities) == 1:
        opp = opportunities[0]
        summary = (
            f"1 vendor ({opp.vendor_name}) has cross-department "
            f"opportunity with ~${total_estimated_savings:,.2f} "
            f"in potential savings."
        )
    else:
        summary = (
            f"{len(opportunities)} vendors have multi-department "
            f"procurement opportunities totaling "
            f"~${total_estimated_savings:,.2f} in potential savings."
        )

    summary_dict = {
        "total_vendors_analyzed": len(grouped),
        "vendors_with_opportunities": len(opportunities),
        "total_estimated_savings": total_estimated_savings,
        "summary": summary
    }

    # Log agent execution
    await log_agent_execution(
        agent_name="Cross Deal Negotiator",
        action_type="crossdeal_analysis",
        input_payload={
            "source": "procurements table",
            "status_filter": "active",
            "total_procurements_analyzed": len(procurements)
        },
        output_payload={
            "total_vendors_analyzed": len(grouped),
            "vendors_with_opportunities": len(opportunities),
            "total_estimated_savings": total_estimated_savings,
            "opportunities": [
                {
                    "vendor_name": o.vendor_name,
                    "departments": o.departments,
                    "active_procurements": o.active_procurements,
                    "total_value": o.total_procurement_value,
                    "estimated_savings": o.estimated_savings_amount
                }
                for o in opportunities
            ]
        },
        reasoning=(
            "Identified vendors used by multiple departments to "
            "consolidate negotiations and unlock savings through "
            "bundled procurement."
        )
    )

    return opportunities, summary_dict

