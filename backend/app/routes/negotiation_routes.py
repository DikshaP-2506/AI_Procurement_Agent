from fastapi import APIRouter, HTTPException
from ..models.negotiation import (
    NegotiationRequest,
    EmailRequest,
    NegotiationRetrievalResponse,
    NegotiationStrategyResponse,
    NegotiationEmailResponse,
)
from ..services.negotiation_service import (
    retrieve_similar_negotiations,
    generate_strategy,
    generate_email,
)

router = APIRouter(prefix="/negotiation", tags=["negotiation"])


@router.post("/negotiation-retrieval", response_model=NegotiationRetrievalResponse)
async def retrieve(request: NegotiationRequest):
    try:
        results = await retrieve_similar_negotiations(request.vendor_name, request.product_category, request.quote_value)
        return NegotiationRetrievalResponse(similar_negotiations=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategy-recommendation", response_model=NegotiationStrategyResponse)
async def strategy(request: NegotiationRequest):
    try:
        result = await generate_strategy(request.vendor_name, request.product_category, request.quote_value)
        return NegotiationStrategyResponse(
            status=result.status,
            strategy=result.strategy,
            historical=result.historical,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/email-generation", response_model=NegotiationEmailResponse)
async def email(request: EmailRequest):
    try:
        result = await generate_email(request.vendor_name, request.recommended_strategy, request.expected_discount_range)
        return NegotiationEmailResponse(status="success", email=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
