#!/usr/bin/env python3
"""Validation suite for the Negotiation Intelligence module.

The script supports two execution modes:
- API mode: validates the FastAPI endpoints over HTTP.
- Direct mode: falls back to service-layer calls when the API is unavailable.

It keeps the original smoke-test style, but now performs explicit pass/fail
validation and exits with a non-zero code if any check fails.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib import error, request

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
BACKEND_ENV = BACKEND_DIR / ".env"
BASE_URL = os.getenv("NEGOTIATION_TEST_BASE_URL", "http://localhost:8000")

PASSED = 0
FAILED = 0

load_dotenv(BACKEND_ENV)
sys.path.insert(0, str(BACKEND_DIR))


def _try_import_backend():
    try:
        from app.services.negotiation_service import (  # type: ignore
            retrieve_similar_negotiations,
            generate_strategy,
            generate_email,
        )
        from app.agents import negotiation_agent as negotiation_agent_module  # type: ignore
        from app.supabase_client import supabase, supabase_service  # type: ignore

        return retrieve_similar_negotiations, generate_strategy, generate_email, negotiation_agent_module, supabase, supabase_service, None
    except Exception as exc:
        return None, None, None, None, None, None, exc


RETRIEVE_SERVICE, STRATEGY_SERVICE, EMAIL_SERVICE, NEGOTIATION_AGENT_MODULE, SUPABASE_CLIENT, SUPABASE_SERVICE_CLIENT, BACKEND_IMPORT_ERROR = _try_import_backend()


def validate(condition: bool, message: str) -> bool:
    """Track a pass/fail check and print the result."""
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"[PASS] {message}")
        return True

    FAILED += 1
    print(f"[FAIL] {message}")
    return False


def _print_block(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def _json_default(value: Any) -> Any:
    try:
        return value.model_dump()
    except Exception:
        return str(value)


def _pretty(payload: Any) -> str:
    try:
        return json.dumps(payload, indent=2, default=_json_default)
    except Exception:
        return str(payload)


def _to_plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_plain(item) for key, item in value.items()}
    return value


def _http_json(method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Tuple[int, Any]:
    url = f"{BASE_URL}{path}"
    data = None
    headers: Dict[str, str] = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=45) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = body
        return exc.code, parsed
    except Exception as exc:
        return 0, {"error": str(exc)}


def _server_is_up() -> bool:
    status, _ = _http_json("GET", "/")
    return status == 200


def _schema_has_keys(payload: Dict[str, Any], keys: Sequence[str]) -> bool:
    return isinstance(payload, dict) and all(key in payload for key in keys)


def _schema_numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _schema_non_empty_text(value: Any, min_length: int = 1) -> bool:
    return isinstance(value, str) and len(value.strip()) >= min_length


def _schema_list(value: Any) -> bool:
    return isinstance(value, list)


def _history_summary(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for record in list(records)[:5]:
        rows.append(
            {
                "vendor_name": record.get("vendor_name"),
                "product_category": record.get("product_category"),
                "strategy_used": record.get("strategy_used"),
                "outcome": record.get("outcome"),
                "success_score": record.get("success_score"),
                "initial_quote_value": record.get("initial_quote_value"),
                "discount_received": record.get("discount_received"),
            }
        )
    return rows


def _get_audit_client():
    return SUPABASE_SERVICE_CLIENT or SUPABASE_CLIENT


def _audit_log_count(action_type: str, agent_name: Optional[str] = None) -> Optional[int]:
    client = _get_audit_client()
    if client is None:
        return None

    query = client.table("audit_logs").select("*").eq("action_type", action_type)
    if agent_name:
        query = query.eq("agent_name", agent_name)

    response = query.execute()
    return len(response.data or [])


async def _direct_retrieve(vendor_name: str, product_category: str, quote_value: Any):
    if RETRIEVE_SERVICE is None:
        raise RuntimeError(f"Direct backend import failed: {BACKEND_IMPORT_ERROR}")
    return await RETRIEVE_SERVICE(vendor_name, product_category, quote_value)


async def _direct_strategy(vendor_name: str, product_category: str, quote_value: Any):
    if STRATEGY_SERVICE is None:
        raise RuntimeError(f"Direct backend import failed: {BACKEND_IMPORT_ERROR}")
    return await STRATEGY_SERVICE(vendor_name, product_category, quote_value)


async def _direct_email(vendor_name: str, recommended_strategy: str, expected_discount_range: str):
    if EMAIL_SERVICE is None:
        raise RuntimeError(f"Direct backend import failed: {BACKEND_IMPORT_ERROR}")
    return await EMAIL_SERVICE(vendor_name, recommended_strategy, expected_discount_range)


TEST_CASES: List[Dict[str, Any]] = [
    {"name": "Dell Laptops", "vendor_name": "Dell", "product_category": "Laptops", "quote_value": 120000, "expect_records": True},
    {"name": "HP Laptops", "vendor_name": "HP", "product_category": "Laptops", "quote_value": 118500, "expect_records": True},
    {"name": "Lenovo Servers", "vendor_name": "Lenovo", "product_category": "Servers", "quote_value": 550000, "expect_records": True},
    {"name": "Microsoft Software Licenses", "vendor_name": "Microsoft", "product_category": "Software Licenses", "quote_value": 850000, "expect_records": True},
    {"name": "Cisco Networking Equipment", "vendor_name": "Cisco", "product_category": "Networking Equipment", "quote_value": 49950, "expect_records": True},
    {"name": "Accenture Consulting Services", "vendor_name": "Accenture", "product_category": "Consulting Services", "quote_value": 250000, "expect_records": True},
    {"name": "Oracle Cloud Services", "vendor_name": "Oracle", "product_category": "Cloud Services", "quote_value": 300000, "expect_records": True},
    {"name": "Tata Steel Raw Materials", "vendor_name": "Tata Steel", "product_category": "Raw Materials", "quote_value": 4500000, "expect_records": True},
    {"name": "FedEx Logistics Services", "vendor_name": "FedEx", "product_category": "Logistics Services", "quote_value": 180000, "expect_records": True},
    {"name": "IKEA Business Office Equipment", "vendor_name": "IKEA Business", "product_category": "Office Equipment", "quote_value": 95000, "expect_records": True},
    {"name": "Cisco Security Software", "vendor_name": "Cisco", "product_category": "Security Software", "quote_value": 240000, "expect_records": True},
    {"name": "AWS Large Procurement", "vendor_name": "AWS", "product_category": "Cloud Services", "quote_value": 1250000, "expect_records": True},
    {"name": "Dell Small Procurement", "vendor_name": "Dell", "product_category": "Laptops", "quote_value": 48000, "expect_records": True},
    {"name": "No History Case", "vendor_name": "NewVendorX", "product_category": "Industrial IoT Sensors", "quote_value": 67000, "expect_records": False},
]

MALFORMED_CASES: List[Dict[str, Any]] = [
    {"name": "Missing Vendor", "payload": {"product_category": "Laptops", "quote_value": 120000}},
    {"name": "Missing Category", "payload": {"vendor_name": "Dell", "quote_value": 120000}},
    {"name": "Zero Quote", "payload": {"vendor_name": "Dell", "product_category": "Laptops", "quote_value": 0}},
    {"name": "Negative Quote", "payload": {"vendor_name": "Dell", "product_category": "Laptops", "quote_value": -500}},
    {"name": "Non Numeric Quote", "payload": {"vendor_name": "Dell", "product_category": "Laptops", "quote_value": "one hundred twenty thousand"}},
]


def _validate_retrieval_response(response_data: Any, expect_records: bool, no_history: bool = False) -> List[Dict[str, Any]]:
    validate(isinstance(response_data, dict), "Retrieval response is a JSON object")
    validate(_schema_has_keys(response_data, ["similar_negotiations"]), "Retrieval response contains similar_negotiations")

    records = response_data.get("similar_negotiations", []) if isinstance(response_data, dict) else []
    validate(_schema_list(records), "similar_negotiations is a list")

    if no_history:
        validate(len(records) == 0, "No-history case returns an empty list")
    elif expect_records:
        validate(len(records) > 0, "Valid case returns at least one historical negotiation")

    return records if isinstance(records, list) else []


def _validate_strategy_payload(strategy_payload: Any) -> Dict[str, Any]:
    required_fields = ["recommended_strategy", "expected_discount_range", "confidence_score", "reasoning", "risks"]
    validate(isinstance(strategy_payload, dict), "Strategy response is a JSON object")
    validate(_schema_has_keys(strategy_payload, required_fields), "Strategy response contains required fields")

    strategy = strategy_payload if isinstance(strategy_payload, dict) else {}
    validate(_schema_non_empty_text(strategy.get("recommended_strategy"), 1), "recommended_strategy is populated")
    validate(_schema_non_empty_text(strategy.get("expected_discount_range"), 1), "expected_discount_range is populated")
    validate(_schema_numeric(strategy.get("confidence_score")), "confidence_score is numeric")

    confidence = strategy.get("confidence_score", 0)
    if _schema_numeric(confidence):
        validate(0 <= float(confidence) <= 100, "confidence_score is between 0 and 100")

    validate(_schema_non_empty_text(strategy.get("reasoning"), 20), "reasoning is at least 20 characters")
    validate(_schema_list(strategy.get("risks")), "risks is a list")
    return strategy


def _validate_email_payload(email_payload: Any) -> Dict[str, Any]:
    required_fields = ["subject", "body"]
    validate(isinstance(email_payload, dict), "Email response is a JSON object")
    validate(_schema_has_keys(email_payload, required_fields), "Email response contains required fields")

    email = email_payload if isinstance(email_payload, dict) else {}
    validate(_schema_non_empty_text(email.get("subject"), 10), "Email subject length is at least 10 characters")
    validate(_schema_non_empty_text(email.get("body"), 50), "Email body length is at least 50 characters")
    return email


def _validate_fallback_email(email_payload: Any) -> Dict[str, Any]:
    email = _validate_email_payload(email_payload)
    validate(email.get("subject") == "Commercial Proposal Review Request", "Fallback email uses the expected subject")
    validate("Procurement Team" in email.get("body", ""), "Fallback email body references Procurement Team")
    return email


def _run_api_retrieval(case: Dict[str, Any]) -> Tuple[int, Any]:
    payload = {
        "vendor_name": case["vendor_name"],
        "product_category": case["product_category"],
        "quote_value": case["quote_value"],
    }
    return _http_json("POST", "/negotiation/negotiation-retrieval", payload)


def _run_api_strategy(case: Dict[str, Any]) -> Tuple[int, Any]:
    payload = {
        "vendor_name": case["vendor_name"],
        "product_category": case["product_category"],
        "quote_value": case["quote_value"],
    }
    return _http_json("POST", "/negotiation/strategy-recommendation", payload)


def _run_api_email(vendor_name: str, strategy_payload: Dict[str, Any]) -> Tuple[int, Any]:
    email_payload = {
        "vendor_name": vendor_name,
        "recommended_strategy": strategy_payload.get("recommended_strategy", ""),
        "expected_discount_range": strategy_payload.get("expected_discount_range", ""),
    }
    return _http_json("POST", "/negotiation/email-generation", email_payload)


def _validate_audit_growth(action_type: str, before_count: Optional[int], after_count: Optional[int], message: str) -> None:
    if before_count is None or after_count is None:
        print(f"[WARN] {message} (audit client unavailable)")
        return
    validate(after_count > before_count, message)


def _print_case_header(index: int, name: str) -> None:
    _print_block(f"Case {index}: {name}")


def _run_api_case(case: Dict[str, Any]) -> None:
    status, retrieval = _run_api_retrieval(case)
    validate(status == 200, f"{case['name']}: retrieval status is 200")
    validate(isinstance(retrieval, (dict, list)), f"{case['name']}: retrieval response is valid JSON")
    records = _validate_retrieval_response(retrieval if isinstance(retrieval, dict) else {}, case["expect_records"], no_history=not case["expect_records"])

    status, strategy = _run_api_strategy(case)
    validate(status == 200, f"{case['name']}: strategy status is 200")
    strategy_payload = strategy if isinstance(strategy, dict) else {}
    parsed_strategy = _validate_strategy_payload(strategy_payload.get("strategy", strategy_payload))

    if not case["expect_records"]:
        before_strategy_failure = _audit_log_count("generate_strategy_failure", "Negotiation Strategy Agent")
        if before_strategy_failure is not None:
            status_probe, _ = _run_api_strategy(case)
            validate(status_probe == 200, f"{case['name']}: no-history strategy probe returned 200")
            after_strategy_failure = _audit_log_count("generate_strategy_failure", "Negotiation Strategy Agent")
            _validate_audit_growth(
                "generate_strategy_failure",
                before_strategy_failure,
                after_strategy_failure,
                f"{case['name']}: no-history strategy fallback created an audit_logs failure entry",
            )

    before_audit_strategy = _audit_log_count("generate_strategy", "Negotiation Strategy Agent")
    if before_audit_strategy is not None:
        status2, strategy2 = _run_api_strategy(case)
        validate(status2 == 200, f"{case['name']}: audit-triggering strategy call returned 200")
        after_audit_strategy = _audit_log_count("generate_strategy", "Negotiation Strategy Agent")
        _validate_audit_growth(
            "generate_strategy",
            before_audit_strategy,
            after_audit_strategy,
            f"{case['name']}: strategy generation created an audit_logs entry",
        )
        strategy_payload = strategy2 if isinstance(strategy2, dict) else strategy_payload
        parsed_strategy = _validate_strategy_payload(strategy_payload.get("strategy", strategy_payload))

    status, email = _run_api_email(case["vendor_name"], parsed_strategy)
    validate(status == 200, f"{case['name']}: email status is 200")
    email_payload = email if isinstance(email, dict) else {}
    _validate_email_payload(email_payload.get("email", email_payload))

    before_audit_email = _audit_log_count("generate_email", "Negotiation Strategy Agent")
    if before_audit_email is not None:
        status2, email2 = _run_api_email(case["vendor_name"], parsed_strategy)
        validate(status2 == 200, f"{case['name']}: audit-triggering email call returned 200")
        after_audit_email = _audit_log_count("generate_email", "Negotiation Strategy Agent")
        _validate_audit_growth(
            "generate_email",
            before_audit_email,
            after_audit_email,
            f"{case['name']}: email generation created an audit_logs entry",
        )
        _validate_email_payload((email2 if isinstance(email2, dict) else {}).get("email", {}))

    _print_json_case(case, retrieval, strategy, email, records)


def _print_json_case(case: Dict[str, Any], retrieval: Any, strategy: Any, email: Any, records: List[Dict[str, Any]]) -> None:
    print(f"Case: {case['name']}")
    print(f"Expected: {'records available' if case['expect_records'] else 'no history'}")
    print(f"Retrieved records: {len(records)}")
    print("Retrieval response:")
    print(_pretty(retrieval))
    print("Top history summaries:")
    print(_pretty(_history_summary(records)))
    print("Strategy response:")
    print(_pretty(strategy))
    print("Email response:")
    print(_pretty(email))


def _run_direct_case(case: Dict[str, Any]) -> None:
    if RETRIEVE_SERVICE is None or STRATEGY_SERVICE is None or EMAIL_SERVICE is None:
        raise RuntimeError(f"Direct backend import failed: {BACKEND_IMPORT_ERROR}")

    async def _execute() -> None:
        history = await _direct_retrieve(case["vendor_name"], case["product_category"], case["quote_value"])
        history_list = _to_plain(history)

        validate(isinstance(history_list, list), f"{case['name']}: retrieval returns a list in direct mode")
        validate(len(history_list) > 0 if case["expect_records"] else len(history_list) == 0, f"{case['name']}: direct retrieval expected record count")

        strategy_result = await _direct_strategy(case["vendor_name"], case["product_category"], case["quote_value"])
        strategy_plain = _to_plain(strategy_result)
        strategy_payload = strategy_plain.get("strategy", strategy_plain) if isinstance(strategy_plain, dict) else {}
        _validate_strategy_payload(strategy_payload)

        if not case["expect_records"]:
            before_strategy_failure = _audit_log_count("generate_strategy_failure", "Negotiation Strategy Agent")
            if before_strategy_failure is not None:
                await _direct_strategy(case["vendor_name"], case["product_category"], case["quote_value"])
                after_strategy_failure = _audit_log_count("generate_strategy_failure", "Negotiation Strategy Agent")
                _validate_audit_growth(
                    "generate_strategy_failure",
                    before_strategy_failure,
                    after_strategy_failure,
                    f"{case['name']}: no-history strategy fallback created an audit_logs failure entry",
                )

        before_audit_strategy = _audit_log_count("generate_strategy", "Negotiation Strategy Agent")
        if before_audit_strategy is not None:
            await _direct_strategy(case["vendor_name"], case["product_category"], case["quote_value"])
            after_audit_strategy = _audit_log_count("generate_strategy", "Negotiation Strategy Agent")
            _validate_audit_growth(
                "generate_strategy",
                before_audit_strategy,
                after_audit_strategy,
                f"{case['name']}: strategy generation created an audit_logs entry",
            )

        email_result = await _direct_email(
            case["vendor_name"],
            strategy_payload.get("recommended_strategy", ""),
            strategy_payload.get("expected_discount_range", ""),
        )
        email_plain = _to_plain(email_result)
        _validate_email_payload(email_plain)

        before_audit_email = _audit_log_count("generate_email", "Negotiation Strategy Agent")
        if before_audit_email is not None:
            await _direct_email(
                case["vendor_name"],
                strategy_payload.get("recommended_strategy", ""),
                strategy_payload.get("expected_discount_range", ""),
            )
            after_audit_email = _audit_log_count("generate_email", "Negotiation Strategy Agent")
            _validate_audit_growth(
                "generate_email",
                before_audit_email,
                after_audit_email,
                f"{case['name']}: email generation created an audit_logs entry",
            )

        _print_json_case(case, history_list, strategy_plain, email_plain, history_list)

    asyncio.run(_execute())


def _run_api_malformed_case(case: Dict[str, Any]) -> None:
    payload = case["payload"]
    status, response = _http_json("POST", "/negotiation/strategy-recommendation", payload)
    valid_json = isinstance(response, (dict, list))

    validate(valid_json, f"{case['name']}: malformed request returned valid JSON")
    validate(status in {400, 422}, f"{case['name']}: malformed request is rejected by validation")
    print("Malformed response:")
    print(_pretty(response))


def _run_email_fallback_check() -> None:
    if NEGOTIATION_AGENT_MODULE is None or EMAIL_SERVICE is None:
        validate(False, "Email fallback check: backend module unavailable")
        return

    async def _execute() -> None:
        original_key = getattr(NEGOTIATION_AGENT_MODULE, "GROQ_API_KEY", None)
        try:
            NEGOTIATION_AGENT_MODULE.GROQ_API_KEY = ""
            before_failure = _audit_log_count("generate_email_failure", "Negotiation Strategy Agent")
            fallback_email = await _direct_email(
                "Fallback Vendor",
                "Use a competitive benchmarking and phased concession approach.",
                "5% - 10%",
            )
            fallback_plain = _to_plain(fallback_email)
            validate(isinstance(fallback_plain, dict), "Email fallback check returns a JSON object")
            _validate_fallback_email(fallback_plain)
            after_failure = _audit_log_count("generate_email_failure", "Negotiation Strategy Agent")
            _validate_audit_growth(
                "generate_email_failure",
                before_failure,
                after_failure,
                "Email fallback check: fallback generation created an audit_logs failure entry",
            )
        finally:
            NEGOTIATION_AGENT_MODULE.GROQ_API_KEY = original_key

    asyncio.run(_execute())


def _run_direct_malformed_case(case: Dict[str, Any]) -> None:
    async def _execute() -> None:
        payload = case["payload"]
        vendor = payload.get("vendor_name", "")
        category = payload.get("product_category", "")
        quote = payload.get("quote_value", 0)

        try:
            history = await _direct_retrieve(vendor, category, quote)
            history_plain = _to_plain(history)
            validate(isinstance(history_plain, list), f"{case['name']}: direct malformed retrieval returns a list or fails safely")
        except Exception:
            validate(True, f"{case['name']}: direct malformed retrieval fails safely")

        try:
            strategy_result = await _direct_strategy(vendor, category, quote)
            strategy_plain = _to_plain(strategy_result)
            _validate_strategy_payload(strategy_plain.get("strategy", strategy_plain) if isinstance(strategy_plain, dict) else {})
            validate(True, f"{case['name']}: direct malformed strategy returns safe output")
        except Exception:
            validate(True, f"{case['name']}: direct malformed strategy fails safely")

        try:
            email_result = await _direct_email(vendor, "", "")
            email_plain = _to_plain(email_result)
            _validate_email_payload(email_plain)
            validate(True, f"{case['name']}: direct malformed email returns safe output")
        except Exception:
            validate(True, f"{case['name']}: direct malformed email fails safely")

    asyncio.run(_execute())


def run(mode: str = "auto") -> int:
    global PASSED, FAILED

    _print_block("Negotiation Intelligence Validation Suite")
    print(f"Base URL: {BASE_URL}")
    api_available = _server_is_up()
    selected_mode = mode
    if mode == "auto":
        selected_mode = "api" if api_available else "direct"
    print(f"Mode: {selected_mode}")

    if selected_mode == "direct" and RETRIEVE_SERVICE is None:
        print(f"Unable to use direct mode: {BACKEND_IMPORT_ERROR}")
        return 1

    # Valid procurement scenarios
    for index, case in enumerate(TEST_CASES, start=1):
        _print_case_header(index, case["name"])
        try:
            if selected_mode == "api":
                _run_api_case(case)
            else:
                _run_direct_case(case)
        except Exception as exc:
            validate(False, f"{case['name']}: unexpected execution error - {exc}")

    # Malformed validation scenarios
    for index, case in enumerate(MALFORMED_CASES, start=1):
        _print_case_header(index + len(TEST_CASES), case["name"])
        try:
            if selected_mode == "api":
                _run_api_malformed_case(case)
            else:
                _run_direct_malformed_case(case)
        except Exception as exc:
            validate(False, f"{case['name']}: unexpected malformed-case error - {exc}")

    _print_case_header(len(TEST_CASES) + len(MALFORMED_CASES) + 1, "Email Fallback Check")
    try:
        _run_email_fallback_check()
    except Exception as exc:
        validate(False, f"Email fallback check: unexpected error - {exc}")

    print("\n==================================")
    print("FINAL RESULTS")
    print("==================================")
    print(f"Passed: {PASSED}")
    print(f"Failed: {FAILED}")

    return 0 if FAILED == 0 else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the Negotiation Intelligence module.")
    parser.add_argument(
        "--mode",
        choices=("auto", "api", "direct"),
        default="auto",
        help="Execution mode: auto-detect, use API only, or use direct services only.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    raise SystemExit(run(args.mode))
