from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..agents.delay_risk_predictor import predict_delay_risk
from ..agents.historical_performance_agent import analyze_historical_performance
from ..agents.shadow_market_scout import MarketSignalProvider, RuleBasedMarketSignalProvider, analyze_shadow_market_risk
from ..supabase_client import supabase, supabase_service
from .audit_service import log_agent_execution


def _client():
    return supabase_service or supabase


def _rows(response: Any) -> List[Dict[str, Any]]:
    return response.data if getattr(response, "data", None) else []


def _average(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _final_risk_level(final_risk_score: int) -> str:
    if final_risk_score >= 67:
        return "high"
    if final_risk_score >= 34:
        return "medium"
    return "low"


def _severity_to_score(severity: str) -> int:
    normalized = str(severity).lower().strip()
    if normalized == "high":
        return 85
    if normalized == "medium":
        return 55
    return 20


def _normalize_alerts(alerts: Any) -> List[Dict[str, Any]]:
    if not isinstance(alerts, list):
        return []

    normalized: List[Dict[str, Any]] = []
    for alert in alerts:
        if isinstance(alert, dict):
            normalized.append(
                {
                    "alert_type": str(alert.get("alert_type", "risk_alert")),
                    "severity": str(alert.get("severity", "low")),
                    "message": str(alert.get("message", "")),
                    "source": str(alert.get("source", "unknown")),
                }
            )
    return normalized


def _build_source_links(market_payload: Dict[str, Any], delay_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    links: List[Dict[str, Any]] = []
    for alert in _normalize_alerts(market_payload.get("alerts", [])):
        links.append(
            {
                "source": alert["source"],
                "label": alert["alert_type"],
                "message": alert["message"],
            }
        )

    links.append(
        {
            "source": "delay_risk_predictor",
            "label": "delay_prediction",
            "message": str(delay_payload.get("prediction_reason", "")),
        }
    )
    return links


def _build_storage_row(
    historical: Dict[str, Any],
    market_risk: Dict[str, Any],
    delay_prediction: Dict[str, Any],
    contracts: List[Dict[str, Any]],
    negotiations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    historical_score = int(historical.get("historical_score", 0) or 0)
    market_risk_score = int(market_risk.get("risk_score", 0) or 0)
    delay_probability = float(delay_prediction.get("delay_probability", 0) or 0)
    supply_chain_risk_score = int(round(delay_probability * 100))
    financial_risk_score = max(0, min(100, int(round((100 - historical_score) * 0.75 + len(contracts) * 3))))
    high_alerts = sum(1 for alert in _normalize_alerts(market_risk.get("alerts", [])) if str(alert.get("severity", "")).lower() == "high")
    medium_alerts = sum(1 for alert in _normalize_alerts(market_risk.get("alerts", [])) if str(alert.get("severity", "")).lower() == "medium")
    legal_risk_score = max(0, min(100, int(round(18 + (high_alerts * 18) + (medium_alerts * 10) + max(0, len(negotiations) - 2) * 4))))

    overall_risk_score = int(
        round(
            (market_risk_score * 0.35)
            + (financial_risk_score * 0.25)
            + (supply_chain_risk_score * 0.25)
            + (legal_risk_score * 0.15)
        )
    )
    overall_risk_score = max(0, min(100, overall_risk_score))

    return {
        "market_risk_score": market_risk_score,
        "financial_risk_score": financial_risk_score,
        "supply_chain_risk_score": supply_chain_risk_score,
        "legal_risk_score": legal_risk_score,
        "overall_risk_score": overall_risk_score,
        "risk_level": _final_risk_level(overall_risk_score),
        "alerts": _normalize_alerts(market_risk.get("alerts", [])),
        "source_links": _build_source_links(market_risk, delay_prediction),
    }


def _delay_risk_level_from_score(score: int) -> str:
    if score >= 67:
        return "high"
    if score >= 34:
        return "medium"
    return "low"


def _row_to_legacy_response(row: Dict[str, Any]) -> Dict[str, Any]:
    market_risk_score = int(row.get("market_risk_score", 0) or 0)
    financial_risk_score = int(row.get("financial_risk_score", 0) or 0)
    supply_chain_risk_score = int(row.get("supply_chain_risk_score", 0) or 0)
    legal_risk_score = int(row.get("legal_risk_score", 0) or 0)
    overall_risk_score = int(row.get("overall_risk_score", market_risk_score) or 0)
    risk_level = str(row.get("risk_level") or _final_risk_level(overall_risk_score))
    alerts = _normalize_alerts(row.get("alerts", []))
    source_links = row.get("source_links", []) if isinstance(row.get("source_links", []), list) else []

    vendor_name = None
    if "vendors" in row and isinstance(row["vendors"], dict):
        vendor_name = row["vendors"].get("vendor_name")
        if vendor_name:
            vendor_name = vendor_name.strip()
    elif "vendor_name" in row:
        vendor_name = row["vendor_name"]

    from datetime import datetime
    return {
        "vendor_id": str(row.get("vendor_id") or ""),
        "vendor_name": vendor_name,
        "created_at": row.get("created_at") or datetime.now().isoformat(),
        "historical_score": max(0, min(100, 100 - financial_risk_score)),
        "on_time_delivery_rate": max(0, min(100, 100 - supply_chain_risk_score)),
        "sla_compliance": max(0, min(100, 100 - legal_risk_score)),
        "past_projects": max(1, len(source_links) or len(alerts)),
        "risk_score": market_risk_score,
        "risk_level": risk_level,
        "alerts": alerts,
        "delay_probability": round(supply_chain_risk_score / 100, 2),
        "delay_risk": _delay_risk_level_from_score(supply_chain_risk_score),
        "prediction_reason": alerts[0]["message"] if alerts else "Stored risk analysis summary.",
        "final_risk_score": overall_risk_score,
        "final_risk_level": risk_level,
    }


async def _fetch_vendor_context(client: Any, vendor_id: str) -> Dict[str, Any]:
    vendor_response = client.table("vendors").select("*").eq("id", vendor_id).execute()
    vendor_rows = _rows(vendor_response)
    vendor = vendor_rows[0] if vendor_rows else {}

    vendor_quotes = _rows(client.table("vendor_quotes").select("*").eq("vendor_id", vendor_id).execute())
    contracts = _rows(client.table("contracts").select("*").eq("vendor_id", vendor_id).execute())
    negotiations = _rows(client.table("negotiation_history").select("*").eq("vendor_id", vendor_id).execute())

    procurements: List[Dict[str, Any]] = []
    try:
        procurements = _rows(client.table("procurements").select("*").eq("vendor_id", vendor_id).execute())
    except Exception:
        procurements = []

    return {
        "vendor": vendor,
        "vendor_quotes": vendor_quotes,
        "contracts": contracts,
        "negotiations": negotiations,
        "procurements": procurements,
    }


def _compose_risk_payload(
    vendor: Dict[str, Any],
    historical: Dict[str, Any],
    market_risk: Dict[str, Any],
    delay_prediction: Dict[str, Any],
) -> Dict[str, Any]:
    historical_score = int(historical.get("historical_score", 0) or 0)
    risk_score = int(market_risk.get("risk_score", 0) or 0)
    delay_probability = float(delay_prediction.get("delay_probability", 0) or 0)

    final_risk_score = int(
        round(
            ((100 - historical_score) * 0.35)
            + (risk_score * 0.45)
            + ((delay_probability * 100) * 0.20)
        )
    )
    final_risk_score = max(0, min(100, final_risk_score))

    return {
        "vendor_id": historical.get("vendor_id") or market_risk.get("vendor_id") or vendor.get("id"),
        "vendor_name": vendor.get("vendor_name"),
        "historical_score": historical_score,
        "on_time_delivery_rate": int(historical.get("on_time_delivery_rate", 0) or 0),
        "sla_compliance": int(historical.get("sla_compliance", 0) or 0),
        "past_projects": int(historical.get("past_projects", 0) or 0),
        "risk_score": risk_score,
        "risk_level": market_risk.get("risk_level", "low"),
        "alerts": market_risk.get("alerts", []),
        "delay_probability": round(delay_probability, 2),
        "delay_risk": delay_prediction.get("delay_risk", "low"),
        "prediction_reason": delay_prediction.get("prediction_reason", ""),
        "final_risk_score": final_risk_score,
        "final_risk_level": _final_risk_level(final_risk_score),
        "risk_breakdown": {
            "historical": historical,
            "market": market_risk,
            "delay": delay_prediction,
        },
    }


async def get_historical_performance(vendor_id: str, client: Any | None = None) -> Dict[str, Any]:
    active_client = client or _client()
    context = await _fetch_vendor_context(active_client, vendor_id)
    return analyze_historical_performance(
        context["vendor"],
        context["vendor_quotes"],
        context["contracts"],
        context["procurements"],
        context["negotiations"],
    )


async def get_market_risk(
    vendor_id: str,
    historical: Optional[Dict[str, Any]] = None,
    client: Any | None = None,
    provider: Optional[MarketSignalProvider] = None,
) -> Dict[str, Any]:
    active_client = client or _client()
    context = await _fetch_vendor_context(active_client, vendor_id)
    historical_payload = historical or analyze_historical_performance(
        context["vendor"],
        context["vendor_quotes"],
        context["contracts"],
        context["procurements"],
        context["negotiations"],
    )
    return analyze_shadow_market_risk(
        context["vendor"],
        historical_payload,
        context["contracts"],
        context["procurements"],
        context["negotiations"],
        provider=provider or RuleBasedMarketSignalProvider(),
    )


async def predict_vendor_delay_risk(
    vendor_id: str,
    historical: Optional[Dict[str, Any]] = None,
    market_risk: Optional[Dict[str, Any]] = None,
    client: Any | None = None,
) -> Dict[str, Any]:
    active_client = client or _client()
    context = await _fetch_vendor_context(active_client, vendor_id)
    historical_payload = historical or analyze_historical_performance(
        context["vendor"],
        context["vendor_quotes"],
        context["contracts"],
        context["procurements"],
        context["negotiations"],
    )
    market_payload = market_risk or analyze_shadow_market_risk(
        context["vendor"],
        historical_payload,
        context["contracts"],
        context["procurements"],
        context["negotiations"],
        provider=RuleBasedMarketSignalProvider(),
    )
    vendor_history = {
        "vendor_id": vendor_id,
        "average_delivery_days": _average(
            [float(item.get("delivery_days")) for item in context["vendor_quotes"] if item.get("delivery_days") is not None]
        ),
    }
    return predict_delay_risk(historical_payload, market_payload, vendor_history)


async def analyze_vendor_risk(
    vendor_id: str,
    client: Any | None = None,
    provider: Optional[MarketSignalProvider] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    active_client = client or _client()
    context = await _fetch_vendor_context(active_client, vendor_id)
    if not context["vendor"]:
        raise ValueError(f"Vendor {vendor_id} not found")

    historical_payload = analyze_historical_performance(
        context["vendor"],
        context["vendor_quotes"],
        context["contracts"],
        context["procurements"],
        context["negotiations"],
    )
    market_payload = analyze_shadow_market_risk(
        context["vendor"],
        historical_payload,
        context["contracts"],
        context["procurements"],
        context["negotiations"],
        provider=provider or RuleBasedMarketSignalProvider(),
    )
    vendor_history = {
        "vendor_id": vendor_id,
        "average_delivery_days": _average(
            [float(item.get("delivery_days")) for item in context["vendor_quotes"] if item.get("delivery_days") is not None]
        ),
    }
    delay_payload = predict_delay_risk(historical_payload, market_payload, vendor_history)
    aggregated = _compose_risk_payload(context["vendor"], historical_payload, market_payload, delay_payload)
    storage_row = _build_storage_row(
        historical_payload,
        market_payload,
        delay_payload,
        context["contracts"],
        context["negotiations"],
    )

    if persist:
        try:
            active_client.table("vendor_risk_analysis").insert(
                {
                    "vendor_id": aggregated["vendor_id"],
                    **storage_row,
                }
            ).execute()
        except Exception as exc:
            raise Exception(f"Failed to persist vendor risk assessment: {exc}")

    v_name = context["vendor"].get("vendor_name") or vendor_id
    risk_lvl = aggregated.get("overall_risk_level", "LOW")

    if risk_lvl in ["HIGH", "CRITICAL"]:
        audit_reasoning = (
            f"Audited market signals and historical delivery performance for '{v_name}'. "
            f"Identified elevated operational risk ({risk_lvl}) and flagged vendor for active performance monitoring."
        )
    else:
        audit_reasoning = (
            f"Audited market signals and historical delivery performance for '{v_name}'. "
            f"Verified stable financial health and confirmed {risk_lvl} supply chain risk."
        )

    await log_agent_execution(
        agent_name="Risk Intelligence Agent",
        action_type="vendor_risk_analysis",
        input_payload={
            "vendor_id": vendor_id,
            "vendor_name": v_name,
            "contract_count": len(context["contracts"]),
            "quote_count": len(context["vendor_quotes"]),
            "negotiation_count": len(context["negotiations"]),
        },
        output_payload=aggregated,
        reasoning=audit_reasoning,
    )

    return aggregated


async def get_latest_vendor_risk(vendor_id: str, client: Any | None = None) -> Dict[str, Any]:
    active_client = client or _client()
    response = (
        active_client.table("vendor_risk_analysis")
        .select("*, vendors(vendor_name)")
        .eq("vendor_id", vendor_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = _rows(response)
    if rows:
        return _row_to_legacy_response(rows[0])
    return await analyze_vendor_risk(vendor_id, client=active_client, persist=True)


async def get_vendor_history(vendor_id: str, client: Any | None = None, limit: int = 12) -> List[Dict[str, Any]]:
    active_client = client or _client()
    response = (
        active_client.table("vendor_risk_analysis")
        .select("*, vendors(vendor_name)")
        .eq("vendor_id", vendor_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [_row_to_legacy_response(row) for row in _rows(response)]


async def get_risk_dashboard(procurement_id: Optional[str] = None, client: Any | None = None, limit: int = 25) -> Dict[str, Any]:
    active_client = client or _client()
    if procurement_id:
        vendors_resp = active_client.table("vendors").select("id").eq("procurement_id", procurement_id).execute()
        vendor_ids = [v["id"] for v in (vendors_resp.data or [])]
        if not vendor_ids:
            return {
                "total_vendors_analyzed": 0,
                "high_risk_vendors": 0,
                "medium_risk_vendors": 0,
                "low_risk_vendors": 0,
                "average_final_risk_score": 0,
                "assessments": [],
                "trend": [],
            }
        response = (
            active_client.table("vendor_risk_analysis")
            .select("*, vendors(vendor_name)")
            .in_("vendor_id", vendor_ids)
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        )
    else:
        response = (
            active_client.table("vendor_risk_analysis")
            .select("*, vendors(vendor_name)")
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        )
    rows = _rows(response)

    latest_by_vendor: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        vendor_id = str(row.get("vendor_id", "")).strip()
        if vendor_id and vendor_id not in latest_by_vendor:
            latest_by_vendor[vendor_id] = row

    assessments = [_row_to_legacy_response(row) for row in latest_by_vendor.values()]
    average_final_risk_score = round(_average([float(row.get("final_risk_score", 0) or 0) for row in assessments]), 2)
    high = sum(1 for row in assessments if str(row.get("final_risk_level", "low")) == "high")
    medium = sum(1 for row in assessments if str(row.get("final_risk_level", "low")) == "medium")
    low = sum(1 for row in assessments if str(row.get("final_risk_level", "low")) == "low")

    recent_trend_rows = rows[:limit]
    trend = [
        {
            "created_at": row.get("created_at"),
            "historical_score": max(0, min(100, 100 - int(row.get("financial_risk_score", 0) or 0))),
            "risk_score": int(row.get("market_risk_score", 0) or 0),
            "delay_probability": round(int(row.get("supply_chain_risk_score", 0) or 0) / 100, 2),
            "final_risk_score": int(row.get("overall_risk_score", 0) or 0),
            "final_risk_level": str(row.get("risk_level", "low")),
        }
        for row in recent_trend_rows
    ]

    return {
        "total_vendors_analyzed": len(assessments),
        "high_risk_vendors": high,
        "medium_risk_vendors": medium,
        "low_risk_vendors": low,
        "average_final_risk_score": average_final_risk_score,
        "assessments": assessments,
        "trend": trend,
    }

