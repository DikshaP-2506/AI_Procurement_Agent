from fastapi import APIRouter, HTTPException
from ..models.negotiation import (
    NegotiationRequest,
    EmailRequest,
    UseStrategyRequest,
    NegotiationRetrievalResponse,
    NegotiationStrategyResponse,
    NegotiationEmailResponse,
)
from ..services.negotiation_service import (
    retrieve_similar_negotiations,
    generate_strategy,
    generate_email,
    save_accepted_negotiation,
)

router = APIRouter(prefix="/negotiation", tags=["negotiation"])


@router.post("/negotiation-retrieval", response_model=NegotiationRetrievalResponse)
async def retrieve(request: NegotiationRequest):
    try:
        procurement_context = None
        if request.procurement_id or request.quote_id:
            from ..services.negotiation_service import build_procurement_context
            procurement_context = await build_procurement_context(
                procurement_id=request.procurement_id,
                quote_id=request.quote_id,
            )
        results = await retrieve_similar_negotiations(
            procurement_context=procurement_context,
            vendor_name=request.vendor_name,
            product_category=request.product_category,
            quote_value=request.quote_value,
        )
        return NegotiationRetrievalResponse(similar_negotiations=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategy-recommendation", response_model=NegotiationStrategyResponse)
async def strategy(request: NegotiationRequest):
    try:
        result = await generate_strategy(
            vendor_name=request.vendor_name,
            product_category=request.product_category,
            quote_value=request.quote_value,
            procurement_id=request.procurement_id,
            quote_id=request.quote_id,
        )
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
        result = await generate_email(
            vendor_name=request.vendor_name,
            recommended_strategy=request.recommended_strategy,
            expected_discount_range=request.expected_discount_range,
            procurement_id=request.procurement_id,
            quote_id=request.quote_id,
        )
        return NegotiationEmailResponse(status="success", email=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/use-strategy")
async def use_strategy(request: UseStrategyRequest):
    try:
        result = await save_accepted_negotiation(
            procurement_id=request.procurement_id,
            quote_id=request.quote_id,
            recommended_strategy=request.recommended_strategy,
            expected_discount_range=request.expected_discount_range,
            generated_email=request.generated_email,
            risk_score=request.risk_score,
            vendor_rank=request.vendor_rank,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
