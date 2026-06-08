from typing import Dict, Any
from ..services.renewal_service import get_renewal_analysis
from ..services.crossdeal_service import get_crossdeal_analysis
from ..services.strategic_service import analyze_strategic_opportunities
from ..models.optimization import OptimizationSummary, RenewalAlert, BundleOpportunity, StrategicRecommendation


async def get_optimization_summary() -> Dict[str, Any]:
    """
    Aggregate outputs from all three optimization agents into a comprehensive summary.
    
    Returns:
        OptimizationSummary with:
        - Renewal alerts (top HIGH/MEDIUM risks)
        - Bundle opportunities (cross-deal consolidations)
        - Strategic recommendations (AI-powered actions)
    """
    try:
        # Fetch data from all three agents
        renewal_analyses, renewal_summary = await get_renewal_analysis()
        crossdeal_opportunities, crossdeal_summary = await get_crossdeal_analysis()
        
        # Convert to dict format for strategic agent
        renewal_data = {
            "total_contracts": renewal_summary["total_contracts"],
            "high_risk_count": renewal_summary["high_risk_count"],
            "medium_risk_count": renewal_summary["medium_risk_count"],
            "low_risk_count": renewal_summary["low_risk_count"],
            "contracts": [c.model_dump() for c in renewal_analyses] if renewal_analyses else []
        }
        
        crossdeal_data = {
            "total_vendors_analyzed": crossdeal_summary["total_vendors_analyzed"],
            "vendors_with_opportunities": crossdeal_summary["vendors_with_opportunities"],
            "total_estimated_savings": crossdeal_summary["total_estimated_savings"],
            "opportunities": [o.model_dump() for o in crossdeal_opportunities] if crossdeal_opportunities else []
        }
        
        # Get strategic analysis
        strategic_result = await analyze_strategic_opportunities(renewal_data, crossdeal_data)
        strategic_analysis = strategic_result.get("strategic_analysis", {})
        
        # Build renewal alerts (sort by HIGH, then MEDIUM, limit to top 10)
        renewal_alerts = []
        for analysis in renewal_analyses:
            if analysis.risk_level in ["HIGH", "MEDIUM"]:
                renewal_alerts.append(
                    RenewalAlert(
                        vendor_name=analysis.vendor_name,
                        contract_name=analysis.contract_name,
                        days_remaining=analysis.days_remaining,
                        risk_level=analysis.risk_level,
                        recommendation=analysis.recommendation
                    )
                )
        
        # Sort by risk level (HIGH first) then by days remaining
        renewal_alerts.sort(
            key=lambda x: (x.risk_level != "HIGH", x.days_remaining),
            reverse=False
        )
        renewal_alerts = renewal_alerts[:10]  # Top 10 alerts
        
        # Build bundle opportunities
        bundle_opportunities = [
            BundleOpportunity(
                vendor_name=opp.vendor_name,
                departments=opp.departments,
                estimated_savings_percent=opp.estimated_savings_percent,
                estimated_savings_amount=opp.estimated_savings_amount
            )
            for opp in crossdeal_opportunities
        ]
        
        # Build strategic recommendations
        strategic_recommendations = [
            StrategicRecommendation(
                action=action,
                priority=strategic_analysis.get("priority", "MEDIUM"),
                estimated_savings=strategic_analysis.get("estimated_savings", "$0")
            )
            for action in strategic_analysis.get("strategic_actions", [])
        ]
        
        # Calculate overall impact
        high_risk_count = renewal_summary.get("high_risk_count", 0)
        bundle_count = len(bundle_opportunities)
        strategic_count = len(strategic_recommendations)
        
        if high_risk_count > 0 and bundle_count > 0 and strategic_count > 0:
            overall_impact = f"Identified {high_risk_count} high-risk renewals, {bundle_count} consolidation opportunities, and {strategic_count} strategic actions with total potential savings."
        elif high_risk_count > 0:
            overall_impact = f"Identified {high_risk_count} high-risk renewals requiring immediate procurement attention."
        elif bundle_count > 0:
            overall_impact = f"Identified {bundle_count} cross-department consolidation opportunities for vendor negotiations."
        else:
            overall_impact = "Procurement optimization analysis complete. Monitor contract renewals and explore bundling opportunities."
        
        summary = OptimizationSummary(
            total_renewal_alerts=len(renewal_alerts),
            high_risk_count=sum(1 for a in renewal_alerts if a.risk_level == "HIGH"),
            renewal_alerts=renewal_alerts,
            
            total_bundle_opportunities=len(bundle_opportunities),
            bundle_opportunities=bundle_opportunities,
            total_bundle_savings=crossdeal_summary.get("total_estimated_savings", 0),
            
            total_strategic_actions=len(strategic_recommendations),
            strategic_priority=strategic_analysis.get("priority", "MEDIUM"),
            strategic_recommendations=strategic_recommendations,
            total_strategic_savings=strategic_analysis.get("estimated_savings", "$0"),
            
            overall_impact=overall_impact
        )
        
        return {
            "status": "success",
            "summary": summary.model_dump(),
            "generated_at": "UTC timestamp handled by Supabase"
        }
        
    except Exception as e:
        raise Exception(f"Failed to generate optimization summary: {str(e)}")
