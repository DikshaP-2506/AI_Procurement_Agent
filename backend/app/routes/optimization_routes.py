from fastapi import APIRouter, HTTPException
from ..models.optimization import (
    RenewalAnalysisResponse,
    CrossDealAnalysisResponse,
    StrategicAnalysisRequest,
    StrategicAnalysisResponse,
    OptimizationSummary
)
from ..services.renewal_service import get_renewal_analysis
from ..services.crossdeal_service import get_crossdeal_analysis
from ..services.strategic_service import analyze_strategic_opportunities
from ..services.summary_service import get_optimization_summary

router = APIRouter(
    prefix="/optimization",
    tags=["optimization"]
)


# ============================================================================
# SUBSCRIPTION RENEWAL CATCHER ENDPOINT
# ============================================================================

@router.get("/renewal-analysis", response_model=RenewalAnalysisResponse)
async def renewal_analysis():
    """
    Subscription Renewal Catcher Analysis
    
    Proactively identifies contracts approaching renewal and flags potential risks.
    
    Returns:
        - Contracts grouped by risk level (HIGH, MEDIUM, LOW)
        - Days remaining until renewal
        - Auto-renewal status
        - Actionable recommendations
        
    Risk Levels:
        - HIGH: Auto-renewal enabled AND renewal within notice period
        - MEDIUM: Renewal within 90 days
        - LOW: Everything else
    """
    try:
        analyses, summary_dict = await get_renewal_analysis()
        
        return RenewalAnalysisResponse(
            total_contracts=summary_dict["total_contracts"],
            high_risk_count=summary_dict["high_risk_count"],
            medium_risk_count=summary_dict["medium_risk_count"],
            low_risk_count=summary_dict["low_risk_count"],
            contracts=analyses,
            summary=summary_dict["summary"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform renewal analysis: {str(e)}"
        )


# ============================================================================
# CROSS DEAL NEGOTIATOR ENDPOINT
# ============================================================================

@router.get("/crossdeal-analysis", response_model=CrossDealAnalysisResponse)
async def crossdeal_analysis():
    """
    Cross Deal Negotiator Analysis
    
    Identifies opportunities to bundle purchases across departments and improve
    negotiation leverage with vendors.
    
    Returns:
        - Vendors appearing in multiple department procurements
        - Departments using each vendor
        - Estimated savings based on consolidation potential
        - Actionable consolidation recommendations
        
    Savings Calculation:
        - 2 departments = 5% savings
        - 3 departments = 10% savings
        - 4+ departments = 15% savings
    """
    try:
        opportunities, summary_dict = await get_crossdeal_analysis()
        
        return CrossDealAnalysisResponse(
            total_vendors_analyzed=summary_dict["total_vendors_analyzed"],
            vendors_with_opportunities=summary_dict["vendors_with_opportunities"],
            total_estimated_savings=summary_dict["total_estimated_savings"],
            opportunities=opportunities,
            summary=summary_dict["summary"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform cross-deal analysis: {str(e)}"
        )


# ============================================================================
# STRATEGIC PROCUREMENT AGENT ENDPOINT
# ============================================================================

@router.post("/strategic-analysis", response_model=StrategicAnalysisResponse)
async def strategic_analysis(request: StrategicAnalysisRequest):
    """
    Strategic Procurement Agent Analysis
    
    Synthesizes insights from Renewal Catcher and Cross Deal Negotiator to generate
    strategic procurement recommendations. Acts as a senior procurement consultant
    to identify consolidation opportunities, suggest bundled negotiations, and
    estimate strategic savings.
    
    Request Body:
        - renewal_data: Output from GET /optimization/renewal-analysis
        - crossdeal_data: Output from GET /optimization/crossdeal-analysis
    
    Returns:
        - Strategic actions (specific vendor recommendations)
        - Estimated strategic savings
        - Priority level (HIGH/MEDIUM/LOW)
        - Business impact statement
        - Detailed reasoning
        
    Strategic Actions Include:
        - Vendor consolidation opportunities
        - Bundled negotiation suggestions
        - Contract renegotiation opportunities
        - Cost optimization recommendations
    """
    try:
        result = await analyze_strategic_opportunities(
            request.renewal_data,
            request.crossdeal_data
        )
        
        return StrategicAnalysisResponse(
            status=result["status"],
            strategic_analysis={
                "strategic_actions": result["strategic_analysis"]["strategic_actions"],
                "estimated_savings": result["strategic_analysis"]["estimated_savings"],
                "priority": result["strategic_analysis"]["priority"],
                "business_impact": result["strategic_analysis"]["business_impact"],
                "reasoning": result["strategic_analysis"]["reasoning"]
            },
            input_summary=result["input_summary"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform strategic analysis: {str(e)}"
        )


# ============================================================================
# OPTIMIZATION SUMMARY ENDPOINT
# ============================================================================

@router.get("/summary", response_model=OptimizationSummary)
async def optimization_summary():
    """
    Optimization Summary - Complete Procurement Analysis
    
    Aggregates outputs from all three optimization agents into a comprehensive dashboard:
    
    1. **Renewal Alerts** (Subscription Renewal Catcher)
       - HIGH: Auto-renewal enabled AND renewal within notice period
       - MEDIUM: Renewal within 90 days
       - Sorted by urgency, limited to top 10
    
    2. **Bundle Opportunities** (Cross Deal Negotiator)
       - Vendors used by multiple departments
       - Estimated savings: 5% (2 depts), 10% (3 depts), 15% (4+ depts)
       - Sorted by savings potential
    
    3. **Strategic Recommendations** (Strategic Procurement Agent)
       - AI-powered consolidation suggestions
       - Negotiation strategies
       - Cost optimization actions
    
    Returns:
        Complete summary with:
        - Alert counts and details
        - Opportunity counts and details
        - Strategic action counts and priorities
        - Overall procurement optimization impact
    """
    try:
        result = await get_optimization_summary()
        
        summary_data = result["summary"]
        return OptimizationSummary(
            total_renewal_alerts=summary_data["total_renewal_alerts"],
            high_risk_count=summary_data["high_risk_count"],
            renewal_alerts=summary_data["renewal_alerts"],
            
            total_bundle_opportunities=summary_data["total_bundle_opportunities"],
            bundle_opportunities=summary_data["bundle_opportunities"],
            total_bundle_savings=summary_data["total_bundle_savings"],
            
            total_strategic_actions=summary_data["total_strategic_actions"],
            strategic_priority=summary_data["strategic_priority"],
            strategic_recommendations=summary_data["strategic_recommendations"],
            total_strategic_savings=summary_data["total_strategic_savings"],
            
            overall_impact=summary_data["overall_impact"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate optimization summary: {str(e)}"
        )
