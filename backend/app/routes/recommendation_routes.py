from fastapi import APIRouter, HTTPException
from ..models.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    ApplyRecommendationRequest,
    ApplyRecommendationResponse
)
from ..services.recommendation_service import get_recommendation_analysis, apply_recommendation
import logging

logger = logging.getLogger("uvicorn.error")

router = APIRouter(
    prefix="/recommendation",
    tags=["recommendation"]
)

@router.post("/", response_model=RecommendationResponse)
async def generate_recommendation(request: RecommendationRequest):
    """
    Weighted Recommendation Engine
    
    Receives slider weights for Cost, Risk, Support, and Delivery,
    calculates normalized and weighted scores for each vendor quote,
    and returns a ranked list of vendors with structural explainability explanations.
    """
    try:
        response = await get_recommendation_analysis(request)
        return response
    except Exception as e:
        logger.error(f"Failed to generate recommendation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendation: {str(e)}"
        )

@router.post("/apply", response_model=ApplyRecommendationResponse)
async def apply_decision(request: ApplyRecommendationRequest):
    """
    Apply Recommendation
    
    Locks in the decision for a given procurement process:
    1. Sets the procurement status to 'completed' and appends reasoning.
    2. Logs the final selected vendor and weight config to the Supabase audit logs.
    """
    try:
        response = await apply_recommendation(request)
        return response
    except Exception as e:
        logger.error(f"Failed to apply decision: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply decision: {str(e)}"
        )
