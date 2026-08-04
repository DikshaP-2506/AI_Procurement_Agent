from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from uuid import UUID

class RecommendationWeights(BaseModel):
    cost: float = Field(..., description="Weight for cost slider, between 0 and 100")
    risk: float = Field(..., description="Weight for risk slider, between 0 and 100")
    support: float = Field(..., description="Weight for support slider, between 0 and 100")
    delivery: float = Field(..., description="Weight for delivery slider, between 0 and 100")
    warranty: Optional[float] = Field(default=0.0, description="Weight for warranty, between 0 and 100")
    esg: Optional[float] = Field(default=0.0, description="Weight for ESG, between 0 and 100")

class RecommendationRequest(BaseModel):
    procurement_id: UUID = Field(..., description="ID of the procurement process")
    weights: RecommendationWeights
    qualitative_adjustments: Optional[Dict[str, float]] = Field(
        default=None, 
        description="Manual adjustments for each vendor (vendor_id -> offset score from -20 to +20)"
    )
    skip_ai: Optional[bool] = Field(default=False, description="Bypass the GROQ LLM call for faster/instant response")


class ScoreComponent(BaseModel):
    raw: str | float | int
    score: float
    weighted: float

class ScoreBreakdown(BaseModel):
    cost: ScoreComponent
    risk: ScoreComponent
    support: ScoreComponent
    delivery: ScoreComponent
    warranty: Optional[ScoreComponent] = None
    esg: Optional[ScoreComponent] = None

class VendorRecommendation(BaseModel):
    vendor_id: str
    vendor_name: str
    final_score: float
    rank: int
    breakdown: ScoreBreakdown
    explanation: str
    qualitative_adjustment: float = Field(default=0.0)
    missing_information: Optional[List[str]] = Field(default_factory=list)
    confidence_score: Optional[float] = Field(default=1.0)

class ApplyRecommendationRequest(BaseModel):
    procurement_id: UUID
    selected_vendor_id: str
    weights: RecommendationWeights
    reasoning: str

class ApplyRecommendationResponse(BaseModel):
    status: str
    message: str
    procurement_id: str
    selected_vendor_id: str
    audit_log_id: str

class RecommendationResponse(BaseModel):
    recommendations: List[VendorRecommendation]
    comparison_summary: str
    warning: Optional[str] = None
    
    # Agentic AI Recommendation Fields
    recommended_vendor: Optional[str] = None
    why_selected: Optional[str] = None
    why_others_not_selected: Optional[str] = None
    dynamic_priorities: Optional[Any] = None
    criterion_importance: Optional[Any] = None
    confidence_score: Optional[float] = None
    missing_information: Optional[List[Any]] = None
    risks: Optional[Any] = None
    alternative_recommendations: Optional[Any] = None
    agent_reasoning: Optional[Any] = None
    agent_plan: Optional[Any] = None
