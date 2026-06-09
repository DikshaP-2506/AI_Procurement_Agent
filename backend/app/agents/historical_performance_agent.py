from __future__ import annotations

from typing import Any, Dict, List


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _average(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def analyze_historical_performance(
    vendor: Dict[str, Any],
    vendor_quotes: List[Dict[str, Any]],
    contracts: List[Dict[str, Any]],
    procurements: List[Dict[str, Any]],
    negotiations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    vendor_id = str(vendor.get("id") or vendor.get("vendor_id") or "").strip()
    if not vendor_id:
        raise ValueError("vendor.id is required for historical performance analysis")

    delivery_days = [
        _safe_float(quote.get("delivery_days"))
        for quote in vendor_quotes
        if quote.get("delivery_days") is not None
    ]
    compliance_scores = [
        _safe_float(quote.get("compliance_score"))
        for quote in vendor_quotes
        if quote.get("compliance_score") is not None
    ]

    past_projects = len(contracts) + len(procurements) + len(negotiations)
    average_delivery_days = _average(delivery_days)

    if delivery_days:
        on_time_delivery_rate = int(round(_clamp(100.0 - average_delivery_days, 0.0, 100.0)))
    else:
        on_time_delivery_rate = 75

    if compliance_scores:
        sla_compliance = int(round(_clamp(_average(compliance_scores), 0.0, 100.0)))
    else:
        sla_compliance = 75

    project_reliability = int(round(_clamp(20.0 + (past_projects * 4.0), 0.0, 100.0)))
    historical_score = int(
        round(
            _clamp(
                (on_time_delivery_rate * 0.5)
                + (sla_compliance * 0.3)
                + (project_reliability * 0.2),
                0.0,
                100.0,
            )
        )
    )

    if not (vendor_quotes or contracts or procurements or negotiations):
        historical_score = 50

    return {
        "vendor_id": vendor_id,
        "historical_score": historical_score,
        "on_time_delivery_rate": on_time_delivery_rate,
        "sla_compliance": sla_compliance,
        "past_projects": past_projects,
    }

