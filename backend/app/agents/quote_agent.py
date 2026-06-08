import os
import json
from typing import Dict, Any

from langchain_groq import ChatGroq

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def _make_prompt(raw_text: str) -> str:
    prompt = f"""You are a procurement data extraction AI.
Read this vendor quote document carefully and extract these exact fields.

DOCUMENT TEXT:
{raw_text}

Extract and return ONLY this JSON with no explanation, no markdown, no backticks:
{{
  "price": ,
  "delivery_days": ,
  "warranty_years": ,
  "support_level": "",
  "payment_terms": "",
  "compliance_score": (0-100 score)
}}

Rules:
- Return ONLY raw JSON, nothing else
- No markdown backticks
- No explanation
- If a field is truly missing use null
- price should be numeric like 85000 not "$85,000"
"""
    return prompt


def extract_quote_data(raw_text: str) -> Dict[str, Any]:
    default_vals = {
        "price": None,
        "delivery_days": None,
        "warranty_years": None,
        "support_level": None,
        "payment_terms": None,
        "compliance_score": None,
    }
    
    if not GROQ_API_KEY:
        return default_vals

    try:
        # llama3-8b-8192 was decommissioned, switching to llama-3.1-8b-instant or similar
        llm = ChatGroq(api_key=GROQ_API_KEY, model="llama-3.1-8b-instant", temperature=0)
        prompt = _make_prompt(raw_text)
        
        response = llm.invoke(prompt)
        response_text = response.content.strip()
        
        # Clean response: remove markdown backticks if present
        if "```" in response_text:
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            
        # Parse JSON
        parsed = json.loads(response_text)
        
        # Ensure result matches expected schema
        return {
            "price": parsed.get("price"),
            "delivery_days": parsed.get("delivery_days"),
            "warranty_years": parsed.get("warranty_years"),
            "support_level": parsed.get("support_level"),
            "payment_terms": parsed.get("payment_terms"),
            "compliance_score": parsed.get("compliance_score"),
        }
    except Exception as e:
        print(f"Extraction Error: {e}")
        return default_vals
