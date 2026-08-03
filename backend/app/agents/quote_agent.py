import os
import json
import re
from typing import Dict, Any, List
from datetime import datetime, timedelta
from langchain_groq import ChatGroq
from ..services.groq_key_manager import get_next_groq_key


def _make_prompt(raw_text: str, today_str: str) -> str:
    prompt = f"""You are a procurement data extraction AI.
Read this vendor quote document carefully and extract these exact fields.
Today's date is: {today_str}

DOCUMENT TEXT:
{raw_text}

Extract and return ONLY this JSON with no explanation, no markdown, no backticks:
{{
  "price": (numeric price or "Data Not Available"),
  "delivery_days": (integer delivery days or "Data Not Available"),
  "warranty_years": (numeric warranty years or "Data Not Available"),
  "support_level": (string or "Data Not Available"),
  "payment_terms": (string or "Data Not Available"),
  "compliance_score": (0-100 score or "Data Not Available"),
  "contract_name": (string or "Data Not Available"),
  "start_date": "YYYY-MM-DD" (or "Data Not Available"),
  "end_date": "YYYY-MM-DD" (or "Data Not Available"),
  "renewal_date": "YYYY-MM-DD" (or "Data Not Available"),
  "auto_renewal": (true/false or "Data Not Available"),
  "notice_period_days": (integer notice days or "Data Not Available"),
  "invoice_number": (string or "Data Not Available"),
  "quote_number": (string or "Data Not Available"),
  "gst_number": (string or "Data Not Available"),
  "currency": (string/symbol or "Data Not Available"),
  "quantity": (numeric quantity or "Data Not Available"),
  "unit": (string or "Data Not Available"),
  "warranty_period": (string or "Data Not Available"),
  "vendor_certifications": (array of strings, e.g. ["ISO 9001", "SOC2"] or "Data Not Available"),
  "esg_info": (string describing ESG/environmental-social-governance info or "Data Not Available"),
  "extraction_confidence_score": (numeric between 0.0 and 1.0 representing confidence in extraction accuracy)
}}

Rules:
- Return ONLY raw JSON, nothing else.
- No markdown backticks (no ```json).
- No explanation.
- If a field is truly missing or unavailable, use the exact string "Data Not Available". Do NOT use null, and do NOT guess or make up values.
- price: should be numeric like 85000 (do not include currency symbols or commas, e.g., not "$85,000" or "85,000 USD").
- quantity: should be numeric like 10 or 1500.5.
- auto_renewal: must be true or false boolean, or the string "Data Not Available".
- vendor_certifications: must be an array of strings, or the string "Data Not Available".
- extraction_confidence_score: must be a float between 0.0 (low confidence) and 1.0 (high confidence).
"""
    return prompt


def standardize_date(date_str: str) -> str:
    if not date_str or date_str == "Data Not Available":
        return "Data Not Available"

    date_str = str(date_str).strip()
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%Y/%m/%d",
        "%d %b %Y",
        "%d %B %Y",
        "%Y%m%d"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt).date()
            return dt.isoformat()
        except ValueError:
            continue
    return date_str


def normalize_extracted_data(extracted: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {}

    # 1. Currency & Price Normalization
    currency_raw = extracted.get("currency")
    price_raw = extracted.get("price")

    # Map currency strings/symbols to standard ISO codes
    currency_map = {
        "$": "USD",
        "usd": "USD",
        "inr": "INR",
        "₹": "INR",
        "rs": "INR",
        "rs.": "INR",
        "eur": "EUR",
        "€": "EUR",
        "gbp": "GBP",
        "£": "GBP",
        "cad": "CAD",
        "aud": "AUD",
        "sgd": "SGD",
        "jpy": "JPY",
        "¥": "JPY"
    }

    normalized_currency = "USD"  # Default base currency
    if currency_raw and currency_raw != "Data Not Available":
        clean_cur = str(currency_raw).strip().lower()
        if clean_cur in currency_map:
            normalized_currency = currency_map[clean_cur]
        elif clean_cur.upper() in currency_map.values():
            normalized_currency = clean_cur.upper()
        else:
            normalized_currency = clean_cur.upper()

    conversion_rates = {
        "USD": 1.0,
        "INR": 0.012,  # 1 INR = 0.012 USD
        "EUR": 1.09,   # 1 EUR = 1.09 USD
        "GBP": 1.27,   # 1 GBP = 1.27 USD
        "CAD": 0.74,
        "AUD": 0.66,
        "SGD": 0.74,
        "JPY": 0.0064,
    }

    normalized_price = "Data Not Available"
    if price_raw and price_raw != "Data Not Available":
        try:
            # strip non-numeric characters except decimal point
            clean_price_str = re.sub(r"[^\d\.]", "", str(price_raw))
            val = float(clean_price_str)
            rate = conversion_rates.get(normalized_currency, 1.0)
            normalized_price = round(val * rate, 2)
        except Exception:
            normalized_price = "Data Not Available"

    normalized["price_usd"] = normalized_price
    normalized["currency"] = normalized_currency

    # 2. Unit Normalization
    unit_raw = extracted.get("unit")
    normalized_unit = "Data Not Available"
    if unit_raw and unit_raw != "Data Not Available":
        clean_unit = str(unit_raw).strip().lower()
        unit_mappings = {
            "pcs": "units",
            "pieces": "units",
            "piece": "units",
            "item": "units",
            "items": "units",
            "qty": "units",
            "kg": "kg",
            "kgs": "kg",
            "kilogram": "kg",
            "kilograms": "kg",
            "lbs": "lbs",
            "pound": "lbs",
            "pounds": "lbs",
            "hr": "hours",
            "hrs": "hours",
            "hour": "hours",
            "hours": "hours",
            "day": "days",
            "days": "days",
            "month": "months",
            "months": "months",
            "year": "years",
            "years": "years",
            "box": "box",
            "boxes": "box",
            "pack": "package",
            "packs": "package",
            "package": "package",
            "packages": "package"
        }
        normalized_unit = unit_mappings.get(clean_unit, clean_unit)

    normalized["unit"] = normalized_unit
    normalized["quantity"] = extracted.get("quantity")

    # 3. Date Standardization
    normalized["start_date"] = standardize_date(extracted.get("start_date"))
    normalized["end_date"] = standardize_date(extracted.get("end_date"))
    normalized["renewal_date"] = standardize_date(extracted.get("renewal_date"))

    return normalized


def validate_extracted_data(extracted: Dict[str, Any]) -> Dict[str, Any]:
    validation = {
        "is_valid": True,
        "missing_mandatory_fields": False,
        "gst_valid": None,
        "currency_valid": None,
        "unit_valid": None,
        "date_valid": None,
        "errors": []
    }

    # 1. Missing Mandatory Fields Check
    missing_mandatory = []
    if not extracted.get("price") or extracted.get("price") == "Data Not Available":
        missing_mandatory.append("price")
    if not extracted.get("currency") or extracted.get("currency") == "Data Not Available":
        missing_mandatory.append("currency")
    if not extracted.get("start_date") or extracted.get("start_date") == "Data Not Available":
        missing_mandatory.append("start_date")

    invoice_missing = not extracted.get("invoice_number") or extracted.get("invoice_number") == "Data Not Available"
    quote_missing = not extracted.get("quote_number") or extracted.get("quote_number") == "Data Not Available"
    if invoice_missing and quote_missing:
        missing_mandatory.append("invoice_number or quote_number")

    if missing_mandatory:
        validation["is_valid"] = False
        validation["missing_mandatory_fields"] = True
        validation["errors"].append(f"Missing mandatory fields: {', '.join(missing_mandatory)}")

    # 2. GST Validation
    gst = extracted.get("gst_number")
    if gst and gst != "Data Not Available":
        gst_str = str(gst).strip()
        indian_gst_pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
        if re.match(indian_gst_pattern, gst_str):
            validation["gst_valid"] = True
        else:
            generic_gst_pattern = r"^[A-Z0-9]{8,15}$"
            if re.match(generic_gst_pattern, gst_str.upper()):
                validation["gst_valid"] = True
            else:
                validation["gst_valid"] = False
                validation["is_valid"] = False
                validation["errors"].append(f"Invalid GST Number format: '{gst_str}'")
    else:
        validation["gst_valid"] = None

    # 3. Currency Validation
    currency = extracted.get("currency")
    if currency and currency != "Data Not Available":
        cur_str = str(currency).strip().upper()
        valid_currencies = {"USD", "INR", "EUR", "GBP", "CAD", "AUD", "SGD", "JPY", "$", "₹", "€", "£", "¥"}
        if cur_str in valid_currencies or str(currency).strip().lower() in {"usd", "inr", "eur", "gbp", "cad", "aud", "sgd", "jpy"}:
            validation["currency_valid"] = True
        else:
            validation["currency_valid"] = False
            validation["is_valid"] = False
            validation["errors"].append(f"Unrecognized currency: '{currency}'")
    else:
        validation["currency_valid"] = None

    # 4. Unit Validation
    unit = extracted.get("unit")
    if unit and unit != "Data Not Available":
        unit_str = str(unit).strip().lower()
        valid_units = {"units", "items", "pcs", "pieces", "kg", "kilograms", "lbs", "pounds", "hours", "hrs", "days", "months", "years", "lot", "box", "pack", "package"}
        if unit_str in valid_units:
            validation["unit_valid"] = True
        else:
            validation["unit_valid"] = False
            validation["is_valid"] = False
            validation["errors"].append(f"Unrecognized unit: '{unit}'")
    else:
        validation["unit_valid"] = None

    # 5. Date Validation
    start_date_str = standardize_date(extracted.get("start_date"))
    end_date_str = standardize_date(extracted.get("end_date"))
    renewal_date_str = standardize_date(extracted.get("renewal_date"))

    dates_ok = True
    parsed_start = None
    parsed_end = None
    parsed_renewal = None

    if start_date_str and start_date_str != "Data Not Available":
        try:
            parsed_start = datetime.fromisoformat(start_date_str).date()
        except ValueError:
            dates_ok = False
            validation["errors"].append(f"Invalid start_date format: '{start_date_str}'")

    if end_date_str and end_date_str != "Data Not Available":
        try:
            parsed_end = datetime.fromisoformat(end_date_str).date()
        except ValueError:
            dates_ok = False
            validation["errors"].append(f"Invalid end_date format: '{end_date_str}'")

    if renewal_date_str and renewal_date_str != "Data Not Available":
        try:
            parsed_renewal = datetime.fromisoformat(renewal_date_str).date()
        except ValueError:
            dates_ok = False
            validation["errors"].append(f"Invalid renewal_date format: '{renewal_date_str}'")

    if dates_ok:
        if parsed_start and parsed_end and parsed_start > parsed_end:
            dates_ok = False
            validation["errors"].append(f"start_date ({start_date_str}) cannot be after end_date ({end_date_str})")

        if parsed_renewal and parsed_end and parsed_renewal > parsed_end:
            dates_ok = False
            validation["errors"].append(f"renewal_date ({renewal_date_str}) cannot be after end_date ({end_date_str})")

        if parsed_start and parsed_renewal and parsed_start > parsed_renewal:
            dates_ok = False
            validation["errors"].append(f"start_date ({start_date_str}) cannot be after renewal_date ({renewal_date_str})")

    if (start_date_str == "Data Not Available" and
            end_date_str == "Data Not Available" and
            renewal_date_str == "Data Not Available"):
        validation["date_valid"] = None
    else:
        validation["date_valid"] = dates_ok
        if not dates_ok:
            validation["is_valid"] = False

    return validation


def extract_quote_data(raw_text: str, today_str: str = None, existing_quotes: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not today_str:
        today_str = datetime.now().date().isoformat()

    schema_fields = [
        "price", "delivery_days", "warranty_years", "support_level",
        "payment_terms", "compliance_score", "contract_name", "start_date",
        "end_date", "renewal_date", "auto_renewal", "notice_period_days",
        "invoice_number", "quote_number", "gst_number", "currency",
        "quantity", "unit", "warranty_period", "vendor_certifications", "esg_info"
    ]

    default_extracted = {f: "Data Not Available" for f in schema_fields}
    default_extracted["contract_name"] = "Vendor Agreement"
    default_extracted["start_date"] = today_str
    default_extracted["auto_renewal"] = True
    default_extracted["notice_period_days"] = 30

    default_res = {
        "extracted_data": default_extracted,
        "validation_status": {
            "is_valid": False,
            "missing_mandatory_fields": True,
            "gst_valid": None,
            "currency_valid": None,
            "unit_valid": None,
            "date_valid": None,
            "errors": ["Extraction failed to run or GROQ API key is missing."]
        },
        "duplicate_detection_status": {
            "is_duplicate_invoice": False,
            "is_duplicate_quotation": False,
            "details": "No verification executed."
        },
        "missing_fields": schema_fields.copy(),
        "normalized_values": {
            "price_usd": "Data Not Available",
            "currency": "USD",
            "unit": "Data Not Available",
            "quantity": "Data Not Available",
            "start_date": today_str,
            "end_date": "Data Not Available",
            "renewal_date": "Data Not Available"
        },
        "extraction_confidence_score": 0.0
    }

    key = get_next_groq_key()
    if not key:
        return default_res

    try:
        llm = ChatGroq(api_key=key, model="llama-3.1-8b-instant", temperature=0)
        prompt = _make_prompt(raw_text, today_str)

        response = llm.invoke(prompt)
        response_text = response.content.strip()

        if "```" in response_text:
            response_text = response_text.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(response_text)

        extracted = {}
        for field in schema_fields:
            val = parsed.get(field)
            if val is None or val == "":
                extracted[field] = "Data Not Available"
            else:
                extracted[field] = val

        raw_conf = parsed.get("extraction_confidence_score")
        try:
            confidence = float(raw_conf) if raw_conf is not None else 0.8
        except Exception:
            confidence = 0.8

        if extracted["vendor_certifications"] == "Data Not Available" or not isinstance(extracted["vendor_certifications"], list):
            if isinstance(extracted["vendor_certifications"], str) and extracted["vendor_certifications"] != "Data Not Available":
                extracted["vendor_certifications"] = [c.strip() for c in extracted["vendor_certifications"].split(",") if c.strip()]
            else:
                extracted["vendor_certifications"] = "Data Not Available"

        validation = validate_extracted_data(extracted)
        normalized = normalize_extracted_data(extracted)
        missing_fields = [f for f in schema_fields if extracted[f] == "Data Not Available"]

        final_result = {
            "extracted_data": extracted,
            "validation_status": validation,
            "duplicate_detection_status": {
                "is_duplicate_invoice": False,
                "is_duplicate_quotation": False,
                "details": "No duplicate check executed."
            },
            "missing_fields": missing_fields,
            "normalized_values": normalized,
            "extraction_confidence_score": confidence
        }

        if existing_quotes is not None:
            invoice_num = extracted.get("invoice_number")
            quote_num = extracted.get("quote_number")

            is_dup_inv = False
            is_dup_q = False
            details_list = []

            for eq in existing_quotes:
                eq_extracted = eq.get("extracted_json", {}).get("full_ai_result", {}).get("extracted_data", eq)

                eq_inv = eq_extracted.get("invoice_number") or eq.get("invoice_number")
                eq_q = eq_extracted.get("quote_number") or eq.get("quote_number")

                if invoice_num and invoice_num != "Data Not Available" and eq_inv == invoice_num:
                    is_dup_inv = True
                    details_list.append(f"Duplicate Invoice Number '{invoice_num}' matches quote ID {eq.get('id')}.")
                if quote_num and quote_num != "Data Not Available" and eq_q == quote_num:
                    is_dup_q = True
                    details_list.append(f"Duplicate Quotation Number '{quote_num}' matches quote ID {eq.get('id')}.")

            final_result["duplicate_detection_status"] = {
                "is_duplicate_invoice": is_dup_inv,
                "is_duplicate_quotation": is_dup_q,
                "details": " | ".join(details_list) if details_list else "No duplicates detected."
            }

        return final_result

    except Exception as e:
        print(f"Extraction Error: {e}")
        try:
            sd = datetime.fromisoformat(today_str).date()
            ed = (sd + timedelta(days=365)).isoformat()
            rd = (sd + timedelta(days=335)).isoformat()
        except Exception:
            ed = "Data Not Available"
            rd = "Data Not Available"

        default_extracted["end_date"] = ed
        default_extracted["renewal_date"] = rd

        fallback_res = default_res.copy()
        fallback_res["extracted_data"] = default_extracted
        fallback_res["validation_status"]["errors"] = [f"Extraction failed with exception: {str(e)}"]
        return fallback_res
