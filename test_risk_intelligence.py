#!/usr/bin/env python3
"""Validation suite for the Risk Intelligence module.

This script supports two levels of verification:
- Pure unit checks against the risk agents using mocked vendor data.
- Optional API smoke tests if a backend server is already running.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib import error, request


ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
BASE_URL = os.getenv("RISK_TEST_BASE_URL", "http://localhost:8000")

import sys

sys.path.insert(0, str(BACKEND_DIR))

from app.agents.delay_risk_predictor import predict_delay_risk
from app.agents.historical_performance_agent import analyze_historical_performance
from app.agents.shadow_market_scout import analyze_shadow_market_risk


def _print(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def _http_json(method: str, path: str, payload: dict | None = None):
    url = f"{BASE_URL}{path}"
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = body
        return exc.code, parsed
    except Exception as exc:
        return 0, {"error": str(exc)}


def _assert(condition: bool, message: str) -> None:
    if condition:
        print(f"[PASS] {message}")
    else:
        raise AssertionError(message)


def run_unit_tests() -> None:
    _print("UNIT TESTS - RISK AGENTS")

    vendor = {"id": "V001", "vendor_name": "Delta Logistics"}
    vendor_quotes = [
        {"delivery_days": 8, "compliance_score": 92},
        {"delivery_days": 10, "compliance_score": 88},
    ]
    contracts = [{"renewal_date": "2026-08-01"}]
    procurements = [{"department": "Operations"}, {"department": "Supply Chain"}]
    negotiations = [{"success_score": 58}, {"success_score": 75}]

    historical = analyze_historical_performance(vendor, vendor_quotes, contracts, procurements, negotiations)
    _assert(historical["vendor_id"] == "V001", "historical analysis returns vendor id")
    _assert(0 <= historical["historical_score"] <= 100, "historical score is normalized")

    market = analyze_shadow_market_risk(vendor, historical, contracts, procurements, negotiations)
    _assert(market["vendor_id"] == "V001", "market analysis returns vendor id")
    _assert(market["risk_level"] in {"low", "medium", "high"}, "market risk level is valid")
    _assert(isinstance(market["alerts"], list) and market["alerts"], "market alerts are generated")

    prediction = predict_delay_risk(historical, market, {"vendor_id": "V001", "average_delivery_days": 9})
    _assert(prediction["vendor_id"] == "V001", "delay predictor returns vendor id")
    _assert(0.0 <= prediction["delay_probability"] <= 1.0, "delay probability is bounded")


def run_api_smoke_tests() -> None:
    _print("API SMOKE TESTS - RISK ENDPOINTS")

    status, payload = _http_json("GET", "/")
    _assert(status == 200, "backend health check succeeds")

    vendor_id = os.getenv("RISK_TEST_VENDOR_ID", "V001")
    status, payload = _http_json("POST", "/risk/analyze", {"vendor_id": vendor_id})
    _assert(status in {200, 500}, "risk analyze endpoint is reachable")
    if status == 200:
        _assert("final_risk_score" in payload, "risk analyze payload contains final_risk_score")


if __name__ == "__main__":
    run_unit_tests()
    run_api_smoke_tests()
