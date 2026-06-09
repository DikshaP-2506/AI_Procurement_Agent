from __future__ import annotations

from typing import Any, Dict


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def predict_delay_risk(
    historical_performance: Dict[str, Any],
    market_risk: Dict[str, Any],
    vendor_history: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    vendor_id = str(
        historical_performance.get("vendor_id")
        or market_risk.get("vendor_id")
        or (vendor_history or {}).get("vendor_id")
        or ""
    ).strip()
    if not vendor_id:
        raise ValueError("vendor_id is required for delay risk prediction")

    historical_score = float(historical_performance.get("historical_score", 50) or 50)
    on_time_delivery_rate = float(historical_performance.get("on_time_delivery_rate", 75) or 75)
    sla_compliance = float(historical_performance.get("sla_compliance", 75) or 75)
    market_risk_score = float(market_risk.get("risk_score", 30) or 30)

    probability = 0.05
    probability += ((100.0 - historical_score) / 100.0) * 0.28
    probability += (market_risk_score / 100.0) * 0.32
    probability += ((100.0 - on_time_delivery_rate) / 100.0) * 0.22
    probability += ((100.0 - sla_compliance) / 100.0) * 0.10

    if vendor_history:
        avg_delay_days = float(vendor_history.get("average_delivery_days", 0) or 0)
        probability += min(avg_delay_days / 100.0, 0.08)

    probability = round(_clamp(probability, 0.02, 0.95), 2)

    if probability < 0.34:
        delay_risk = "low"
    elif probability < 0.67:
        delay_risk = "medium"
    else:
        delay_risk = "high"

    if historical_score >= 80 and market_risk_score <= 40:
        prediction_reason = "Vendor historically delivers on time and external disruption signals remain limited."
    elif market_risk_score >= 67:
        prediction_reason = "External market signals indicate operational disruption risk that could impact delivery timing."
    elif on_time_delivery_rate < 80:
        prediction_reason = "Historical delivery patterns show recurring slippage, increasing the chance of a delay."
    elif sla_compliance < 80:
        prediction_reason = "SLA performance is below target, which can translate into scheduling and fulfillment risk."
    else:
        prediction_reason = "Multiple moderate risk factors suggest the vendor should be monitored closely for delays."

    return {
        "vendor_id": vendor_id,
        "delay_probability": probability,
        "delay_risk": delay_risk,
        "prediction_reason": prediction_reason,
    }

