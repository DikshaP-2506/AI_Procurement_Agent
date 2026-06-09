from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _severity_weight(severity: str) -> int:
    normalized = severity.lower().strip()
    if normalized == "high":
        return 30
    if normalized == "medium":
        return 18
    return 8


class MarketSignalProvider(ABC):
    provider_name = "base"

    @abstractmethod
    def fetch_signals(
        self,
        vendor: Dict[str, Any],
        historical_performance: Dict[str, Any],
        contracts: List[Dict[str, Any]],
        procurements: List[Dict[str, Any]],
        negotiations: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError


class RuleBasedMarketSignalProvider(MarketSignalProvider):
    provider_name = "rule_based_mock"

    def fetch_signals(
        self,
        vendor: Dict[str, Any],
        historical_performance: Dict[str, Any],
        contracts: List[Dict[str, Any]],
        procurements: List[Dict[str, Any]],
        negotiations: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []
        vendor_name = str(vendor.get("vendor_name", "")).lower()
        on_time = int(historical_performance.get("on_time_delivery_rate", 75) or 75)
        sla = int(historical_performance.get("sla_compliance", 75) or 75)
        active_contracts = len(contracts)
        active_procurements = len(procurements)
        negotiation_count = len(negotiations)

        if contracts:
            alerts.append(
                {
                    "alert_type": "contract_renewal_pressure",
                    "severity": "medium" if len(contracts) == 1 else "high",
                    "message": "One or more contracts are approaching renewal and may increase supply chain pressure.",
                    "source": self.provider_name,
                }
            )

        if any(keyword in vendor_name for keyword in ["logistics", "shipping", "steel", "electronics", "hardware"]):
            alerts.append(
                {
                    "alert_type": "supply_chain_disruption",
                    "severity": "high" if active_procurements > 3 else "medium",
                    "message": "Vendor operates in a category with elevated external supply chain disruption exposure.",
                    "source": self.provider_name,
                }
            )

        if on_time < 80 or sla < 80:
            alerts.append(
                {
                    "alert_type": "operational_instability",
                    "severity": "high" if on_time < 70 or sla < 70 else "medium",
                    "message": "Historical service quality suggests the vendor may struggle with delivery consistency.",
                    "source": self.provider_name,
                }
            )

        if negotiation_count >= 3 and any((record.get("success_score") or 0) < 60 for record in negotiations):
            alerts.append(
                {
                    "alert_type": "commercial_friction",
                    "severity": "medium",
                    "message": "Repeated low-success negotiations can be a proxy for vendor resistance or instability.",
                    "source": self.provider_name,
                }
            )

        if active_contracts >= 4 and active_procurements >= 4:
            alerts.append(
                {
                    "alert_type": "capacity_pressure",
                    "severity": "medium",
                    "message": "High active contract and procurement volume can create fulfillment bottlenecks.",
                    "source": self.provider_name,
                }
            )

        if not alerts:
            alerts.append(
                {
                    "alert_type": "market_stable",
                    "severity": "low",
                    "message": "No material market disruption signals detected from the current rule set.",
                    "source": self.provider_name,
                }
            )

        return alerts


def analyze_shadow_market_risk(
    vendor: Dict[str, Any],
    historical_performance: Dict[str, Any],
    contracts: List[Dict[str, Any]],
    procurements: List[Dict[str, Any]],
    negotiations: List[Dict[str, Any]],
    provider: Optional[MarketSignalProvider] = None,
) -> Dict[str, Any]:
    vendor_id = str(vendor.get("id") or vendor.get("vendor_id") or "").strip()
    if not vendor_id:
        raise ValueError("vendor.id is required for shadow market analysis")

    signal_provider = provider or RuleBasedMarketSignalProvider()
    alerts = signal_provider.fetch_signals(vendor, historical_performance, contracts, procurements, negotiations)

    risk_score = 20
    for alert in alerts:
        risk_score += _severity_weight(str(alert.get("severity", "low")))

    if historical_performance.get("on_time_delivery_rate", 75) < 80:
        risk_score += 8
    if historical_performance.get("sla_compliance", 75) < 80:
        risk_score += 6

    risk_score = int(_clamp(float(risk_score), 0.0, 100.0))
    if risk_score >= 67:
        risk_level = "high"
    elif risk_score >= 34:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "vendor_id": vendor_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "alerts": alerts,
        "provider_name": signal_provider.provider_name,
        "evaluated_at": datetime.utcnow().isoformat(),
    }

