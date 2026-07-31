import os
import json
from typing import Dict, Any

from langchain_groq import ChatGroq

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def _make_prompt(raw_text: str, today_str: str) -> str:
    prompt = f"""You are a procurement data extraction AI.
Read this vendor quote document carefully and extract these exact fields.
Today's date is: {today_str}

DOCUMENT TEXT:
{raw_text}

Extract and return ONLY this JSON with no explanation, no markdown, no backticks:
{{
  "price": ,
  "delivery_days": ,
  "warranty_years": ,
  "support_level": "",
  "payment_terms": "",
  "compliance_score": (0-100 score),
  "contract_name": "",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "renewal_date": "YYYY-MM-DD",
  "auto_renewal": (true or false),
  "notice_period_days": (integer notice days)
}}

Rules:
- Return ONLY raw JSON, nothing else
- No markdown backticks
- No explanation
- If a field is truly missing use null
- price should be numeric like 85000 not "$85,000"
- contract_name: If not mentioned, default to "Vendor Agreement"
- start_date: If not mentioned, default to "{today_str}"
- end_date: If not mentioned, default to 1 year after start_date
- renewal_date: If not mentioned, default to 30 days before end_date
- auto_renewal: Default to true if not mentioned
- notice_period_days: Default to 30 if not mentioned
"""
    return prompt


def extract_quote_data(raw_text: str, today_str: str = None) -> Dict[str, Any]:
    from datetime import datetime, timedelta
    if not today_str:
        today_str = datetime.now().date().isoformat()

    default_vals = {
        "price": None,
        "delivery_days": None,
        "warranty_years": None,
        "support_level": None,
        "payment_terms": None,
        "compliance_score": None,
        "contract_name": "Vendor Agreement",
        "start_date": today_str,
        "end_date": None,
        "renewal_date": None,
        "auto_renewal": True,
        "notice_period_days": 30,
    }
    
    if not GROQ_API_KEY:
        return default_vals

    try:
        # llama3-8b-8192 was decommissioned, switching to llama-3.1-8b-instant or similar
        llm = ChatGroq(api_key=GROQ_API_KEY, model="llama-3.1-8b-instant", temperature=0)
        prompt = _make_prompt(raw_text, today_str)
        
        response = llm.invoke(prompt)
        response_text = response.content.strip()
        
        # Clean response: remove markdown backticks if present
        if "```" in response_text:
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            
        # Parse JSON
        parsed = json.loads(response_text)
        
        # Post-process fallback dates
        start_date_str = parsed.get("start_date") or today_str
        end_date_str = parsed.get("end_date")
        if not end_date_str:
            try:
                sd = datetime.fromisoformat(start_date_str).date()
                end_date_str = (sd + timedelta(days=365)).isoformat()
            except Exception:
                end_date_str = None
                
        renewal_date_str = parsed.get("renewal_date")
        if not renewal_date_str and end_date_str:
            try:
                ed = datetime.fromisoformat(end_date_str).date()
                renewal_date_str = (ed - timedelta(days=30)).isoformat()
            except Exception:
                renewal_date_str = None

        # Ensure result matches expected schema
        return {
            "price": parsed.get("price"),
            "delivery_days": parsed.get("delivery_days"),
            "warranty_years": parsed.get("warranty_years"),
            "support_level": parsed.get("support_level"),
            "payment_terms": parsed.get("payment_terms"),
            "compliance_score": parsed.get("compliance_score"),
            "contract_name": parsed.get("contract_name") or "Vendor Agreement",
            "start_date": start_date_str,
            "end_date": end_date_str,
            "renewal_date": renewal_date_str,
            "auto_renewal": parsed.get("auto_renewal") if parsed.get("auto_renewal") is not None else True,
            "notice_period_days": parsed.get("notice_period_days") if parsed.get("notice_period_days") is not None else 30,
        }
    except Exception as e:
        print(f"Extraction Error: {e}")
        # Build calculated default dates in case LLM completely fails to respond
        try:
            sd = datetime.fromisoformat(today_str).date()
            ed = (sd + timedelta(days=365)).isoformat()
            rd = (sd + timedelta(days=335)).isoformat()
        except Exception:
            ed = None
            rd = None
        
        fallback_vals = default_vals.copy()
        fallback_vals["end_date"] = ed
        fallback_vals["renewal_date"] = rd
        return fallback_vals
