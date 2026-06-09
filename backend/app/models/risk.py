from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RiskAnalyzeRequest(BaseModel):
    vendor_id: str = Field(..., min_length=1, description="Vendor identifier")


class HistoricalPerformanceResponse(BaseModel):
    vendor_id: str
    historical_score: int
    on_time_delivery_rate: int
    sla_compliance: int
    past_projects: int

    class Config:
        from_attributes = True


class HistoricalPerformanceHistoryItem(BaseModel):
    created_at: datetime
    historical_score: int
    on_time_delivery_rate: int
    sla_compliance: int
    past_projects: int
    final_risk_score: int
    final_risk_level: Literal["low", "medium", "high"]


class HistoricalPerformanceHistoryResponse(HistoricalPerformanceResponse):
    history: list[HistoricalPerformanceHistoryItem]


class MarketRiskAlert(BaseModel):
    alert_type: str
    severity: Literal["low", "medium", "high"]
    message: str
    source: str


class ShadowMarketScoutResponse(BaseModel):
    vendor_id: str
    risk_score: int
    risk_level: Literal["low", "medium", "high"]
    alerts: list[MarketRiskAlert]

    class Config:
        from_attributes = True


class DelayPredictionResponse(BaseModel):
    vendor_id: str
    delay_probability: float
    delay_risk: Literal["low", "medium", "high"]
    prediction_reason: str

    class Config:
        from_attributes = True


class RiskAggregationResponse(BaseModel):
    vendor_id: str
    vendor_name: str | None = None
    historical_score: int
    on_time_delivery_rate: int
    sla_compliance: int
    past_projects: int
    risk_score: int
    risk_level: Literal["low", "medium", "high"]
    alerts: list[MarketRiskAlert]
    delay_probability: float
    delay_risk: Literal["low", "medium", "high"]
    prediction_reason: str
    final_risk_score: int
    final_risk_level: Literal["low", "medium", "high"]

    class Config:
        from_attributes = True


class RiskTrendPoint(BaseModel):
    created_at: datetime
    historical_score: int
    risk_score: int
    delay_probability: float
    final_risk_score: int
    final_risk_level: Literal["low", "medium", "high"]


class RiskDashboardResponse(BaseModel):
    total_vendors_analyzed: int
    high_risk_vendors: int
    medium_risk_vendors: int
    low_risk_vendors: int
    average_final_risk_score: float
    assessments: list[RiskAggregationResponse]
    trend: list[RiskTrendPoint]

