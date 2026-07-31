from typing import Optional
from fastapi import APIRouter, HTTPException

from ..models.risk import (
    HistoricalPerformanceHistoryResponse,
    RiskAggregationResponse,
    RiskAnalyzeRequest,
    RiskDashboardResponse,
)
from ..services.risk_service import (
    analyze_vendor_risk,
    get_historical_performance,
    get_latest_vendor_risk,
    get_risk_dashboard,
    get_vendor_history,
)


router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/history/{vendor_id}", response_model=HistoricalPerformanceHistoryResponse)
async def historical_performance(vendor_id: str):
    try:
        historical = await get_historical_performance(vendor_id)
        history = await get_vendor_history(vendor_id)
        return HistoricalPerformanceHistoryResponse(
            vendor_id=historical["vendor_id"],
            historical_score=historical["historical_score"],
            on_time_delivery_rate=historical["on_time_delivery_rate"],
            sla_compliance=historical["sla_compliance"],
            past_projects=historical["past_projects"],
            history=history,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/vendor/{vendor_id}", response_model=RiskAggregationResponse)
async def vendor_risk(vendor_id: str):
    try:
        result = await get_latest_vendor_risk(vendor_id)
        return RiskAggregationResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/dashboard", response_model=RiskDashboardResponse)
async def dashboard(procurement_id: Optional[str] = None):
    try:
        result = await get_risk_dashboard(procurement_id=procurement_id)
        return RiskDashboardResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/analyze", response_model=RiskAggregationResponse)
async def analyze(request: RiskAnalyzeRequest):
    try:
        result = await analyze_vendor_risk(request.vendor_id, persist=True)
        return RiskAggregationResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

