from __future__ import annotations

from typing import Any, Dict

from ...services.risk_service import analyze_vendor_risk


async def risk_node(state: Dict[str, Any]) -> Dict[str, Any]:
    vendor_id = state.get("vendor_id")
    if not vendor_id:
        return {**state, "risk_output": None}

    risk_output = await analyze_vendor_risk(str(vendor_id), persist=True)
    return {**state, "risk_output": risk_output}

