from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import date


# ============================================================================
# SUBSCRIPTION RENEWAL CATCHER MODELS
# ============================================================================

class ContractBase(BaseModel):
    """Base contract model for database queries."""
    id: str
    vendor_id: str
    contract_name: str
    start_date: date
    end_date: date
    renewal_date: date
    auto_renewal: bool
    notice_period_days: int
    contract_value: float


class RenewalRiskAnalysis(BaseModel):
    """Response model for individual contract renewal risk."""
    contract_id: str
    contract_name: str
    vendor_name: str
    renewal_date: date
    days_remaining: int
    risk_level: Literal["HIGH", "MEDIUM", "LOW"]
    recommendation: str

    class Config:
        from_attributes = True


class RenewalAnalysisResponse(BaseModel):
    """Aggregated renewal analysis response."""
    total_contracts: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    contracts: List[RenewalRiskAnalysis]
    summary: str

    class Config:
        from_attributes = True


# ============================================================================
# CROSS DEAL NEGOTIATOR MODELS
# ============================================================================

class ProcurementBase(BaseModel):
    """Base procurement model for database queries."""
    id: str
    vendor_id: str
    department: str
    procurement_value: float
    status: str


class DealOpportunity(BaseModel):
    """Response model for cross-department deal opportunity."""
    vendor_name: str
    departments: List[str] = Field(description="List of departments using this vendor")
    active_procurements: int = Field(description="Number of active procurements with this vendor")
    total_procurement_value: float = Field(description="Total value across all departments")
    estimated_savings_percent: int = Field(description="Estimated savings percentage")
    estimated_savings_amount: float = Field(description="Estimated savings in currency")
    recommendation: str

    class Config:
        from_attributes = True


class CrossDealAnalysisResponse(BaseModel):
    """Aggregated cross-deal negotiation analysis response."""
    total_vendors_analyzed: int
    vendors_with_opportunities: int
    total_estimated_savings: float
    opportunities: List[DealOpportunity]
    summary: str

    class Config:
        from_attributes = True


# ============================================================================
# STRATEGIC PROCUREMENT AGENT MODELS
# ============================================================================

class StrategicAnalysisRequest(BaseModel):
    """Request model for strategic procurement analysis."""
    renewal_data: dict = Field(description="Output from renewal analysis endpoint")
    crossdeal_data: dict = Field(description="Output from cross-deal analysis endpoint")

    class Config:
        from_attributes = True


class StrategicAnalysis(BaseModel):
    """Strategic procurement analysis output."""
    strategic_actions: List[str] = Field(description="List of strategic procurement recommendations")
    estimated_savings: str = Field(description="Estimated strategic savings in currency format")
    priority: Literal["HIGH", "MEDIUM", "LOW"] = Field(description="Overall priority level")
    business_impact: str = Field(description="Expected business impact of the recommendations")
    reasoning: str = Field(description="Reasoning behind the strategic recommendations")

    class Config:
        from_attributes = True


class StrategicAnalysisResponse(BaseModel):
    """Complete response for strategic analysis."""
    status: str = Field(description="Status of the analysis (success/error)")
    strategic_analysis: StrategicAnalysis
    input_summary: dict = Field(description="Summary of input data analyzed")

    class Config:
        from_attributes = True


# ============================================================================
# OPTIMIZATION SUMMARY MODELS
# ============================================================================

class RenewalAlert(BaseModel):
    """Renewal alert for the summary."""
    vendor_name: str
    contract_name: str
    days_remaining: int
    risk_level: Literal["HIGH", "MEDIUM", "LOW"]
    recommendation: str


class BundleOpportunity(BaseModel):
    """Bundle opportunity for the summary."""
    vendor_name: str
    departments: List[str]
    estimated_savings_percent: int
    estimated_savings_amount: float


class StrategicRecommendation(BaseModel):
    """Strategic recommendation for the summary."""
    action: str
    priority: Literal["HIGH", "MEDIUM", "LOW"]
    estimated_savings: str


class OptimizationSummary(BaseModel):
    """Complete optimization summary combining all three agents."""
    total_renewal_alerts: int
    high_risk_count: int
    renewal_alerts: List[RenewalAlert] = Field(description="Top renewal alerts (sorted by urgency)")
    
    total_bundle_opportunities: int
    bundle_opportunities: List[BundleOpportunity] = Field(description="Cross-deal opportunities")
    total_bundle_savings: float = Field(description="Total potential savings from bundling")
    
    total_strategic_actions: int
    strategic_priority: Literal["HIGH", "MEDIUM", "LOW"]
    strategic_recommendations: List[StrategicRecommendation] = Field(description="Strategic recommendations")
    total_strategic_savings: str
    
    overall_impact: str = Field(description="Summary of overall procurement optimization opportunity")

    class Config:
        from_attributes = True
