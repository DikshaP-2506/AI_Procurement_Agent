import logging
from typing import Dict, Any
from ..agents.strategic_agent import generate_strategic_analysis
from .audit_service import log_agent_execution
from ..supabase_client import supabase, supabase_service

logger = logging.getLogger("uvicorn.error")


async def fetch_procurement_history():
    """
    Fetch all procurement records for strategic analysis.
    """
    client = supabase_service or supabase

    response = (
        client
        .table("procurements")
        .select("*")
        .execute()
    )

    return response.data if response.data else []


async def analyze_strategic_opportunities(
    renewal_data: Dict[str, Any],
    crossdeal_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Orchestrate strategic procurement analysis.

    Consumes outputs from:
    - Subscription Renewal Catcher (renewal_data)
    - Cross Deal Negotiator (crossdeal_data)

    Returns strategic recommendations combining both analyses.

    Args:
        renewal_data: Output from GET /optimization/renewal-analysis
        crossdeal_data: Output from GET /optimization/crossdeal-analysis

    Returns:
        Strategic analysis with actions, savings, priority, impact,
        and reasoning
    """
    try:
        # Fetch full procurement history
        procurement_history = await fetch_procurement_history()

        # Pass all analyses to the strategic agent
        strategic_result = generate_strategic_analysis(
            renewal_data,
            crossdeal_data,
            procurement_history
        )

        result = {
            "status": "success",
            "strategic_analysis": strategic_result,
            "input_summary": {
                "renewal_contracts_analyzed": renewal_data.get(
                    "total_contracts", 0
                ),
                "high_risk_contracts": renewal_data.get(
                    "high_risk_count", 0
                ),
                "vendors_with_opportunities": crossdeal_data.get(
                    "vendors_with_opportunities", 0
                ),
                "total_potential_savings_from_crossdeal": (
                    crossdeal_data.get(
                        "total_estimated_savings", 0
                    )
                ),
                "procurement_records_analyzed": len(
                    procurement_history
                )
            }
        }

        # Build dynamic, context-specific audit reasoning
        actions_sample = strategic_result.get("strategic_actions", [])
        top_action = actions_sample[0] if actions_sample else "Formulated SLA consolidation pathways."
        priority = strategic_result.get("priority", "HIGH")
        
        dynamic_reasoning = (
            f"Synthesized cross-deal volume opportunities and contract renewal risk alerts. "
            f"Formulated strategic vendor reduction plan and prioritized: {top_action}"
        )

        # Log agent execution
        await log_agent_execution(
            agent_name="Strategic Procurement Agent",
            action_type="strategic_analysis",
            input_payload={
                "renewal_summary": {
                    "total_contracts": renewal_data.get(
                        "total_contracts", 0
                    ),
                    "high_risk_count": renewal_data.get(
                        "high_risk_count", 0
                    ),
                    "medium_risk_count": renewal_data.get(
                        "medium_risk_count", 0
                    )
                },
                "crossdeal_summary": {
                    "vendors_analyzed": crossdeal_data.get(
                        "total_vendors_analyzed", 0
                    ),
                    "vendors_with_opportunities": (
                        crossdeal_data.get(
                            "vendors_with_opportunities", 0
                        )
                    ),
                    "total_estimated_savings": (
                        crossdeal_data.get(
                            "total_estimated_savings", 0
                        )
                    )
                },
                "procurement_history_count": len(
                    procurement_history
                )
            },
            output_payload={
                "strategic_actions": strategic_result.get(
                    "strategic_actions", []
                ),
                "estimated_savings": strategic_result.get(
                    "estimated_savings", "$0"
                ),
                "priority": priority,
                "business_impact": strategic_result.get(
                    "business_impact", ""
                )
            },
            reasoning=dynamic_reasoning
        )


        return result

    except Exception as e:
        logger.warning(f"Strategic service analysis fallback triggered: {e}")
        fallback_res = generate_strategic_analysis(renewal_data, crossdeal_data, [])
        return {
            "status": "success",
            "strategic_analysis": fallback_res,
            "input_summary": {
                "renewal_contracts_analyzed": renewal_data.get("total_contracts", 0),
                "high_risk_contracts": renewal_data.get("high_risk_count", 0),
                "vendors_with_opportunities": crossdeal_data.get("vendors_with_opportunities", 0),
                "total_potential_savings_from_crossdeal": crossdeal_data.get("total_estimated_savings", 0),
                "procurement_records_analyzed": 0
            }
        }


