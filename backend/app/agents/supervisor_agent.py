import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
from langchain_groq import ChatGroq
from ..config import GROQ_API_KEY
from ..supabase_client import supabase_service, supabase
from ..services.memory_service import write_observation, read_observation, clear_observations, get_all_observations
from .quote_agent import extract_quote_data
from ..services.risk_service import analyze_vendor_risk
from .negotiation_agent import generate_negotiation_strategy, generate_negotiation_email
from ..services.renewal_service import get_renewal_analysis
from ..services.crossdeal_service import get_crossdeal_analysis
from ..services.strategic_service import analyze_strategic_opportunities

logger = logging.getLogger("uvicorn.error")

def resolve_vendor_id(vendor_name: str) -> Optional[str]:
    """
    Search database to map a raw vendor name to its exact Supabase ID.
    """
    client = supabase_service or supabase
    try:
        resp = client.table("vendors").select("id").ilike("vendor_name", f"%{vendor_name}%").execute()
        if resp.data:
            return resp.data[0]["id"]
    except Exception as e:
        logger.error(f"Failed to resolve vendor ID for '{vendor_name}': {e}")
    return None

async def run_extract_quotes(raw_text: str) -> Dict[str, Any]:
    """
    Modular tool calling Quote Extraction sub-agent.
    """
    res = extract_quote_data(raw_text)
    write_observation("quote_extraction", res, "Quote Extraction Agent")
    return res

async def run_check_risk(vendor_name: str) -> Dict[str, Any]:
    """
    Modular tool calling Risk Intelligence sub-agent.
    """
    vendor_id = resolve_vendor_id(vendor_name)
    if not vendor_id:
        err = {"error": f"Vendor '{vendor_name}' not found."}
        write_observation(f"risk_analysis_{vendor_name}_error", err, "Risk Intelligence Agent")
        return err
    res = await analyze_vendor_risk(vendor_id, persist=True)
    write_observation(f"risk_analysis_{vendor_id}", res, "Risk Intelligence Agent")
    return res

async def run_negotiation_strategy(vendor_name: str) -> Dict[str, Any]:
    """
    Modular tool calling Negotiation sub-agent strategy logic.
    """
    vendor_id = resolve_vendor_id(vendor_name)
    if not vendor_id:
        err = {"error": f"Vendor '{vendor_name}' not found."}
        write_observation(f"negotiation_strategy_{vendor_name}_error", err, "Negotiation Agent")
        return err
    
    client = supabase_service or supabase
    vendor_resp = client.table("vendors").select("*").eq("id", vendor_id).execute()
    vendor = vendor_resp.data[0] if vendor_resp.data else {}
    
    quotes_resp = client.table("vendor_quotes").select("*").eq("vendor_id", vendor_id).execute()
    quotes = quotes_resp.data or []
    
    current_negotiation = {
        "vendor_id": vendor_id,
        "vendor_name": vendor.get("vendor_name"),
        "quote": quotes[0] if quotes else {}
    }
    
    res = generate_negotiation_strategy(current_negotiation, [])
    write_observation(f"negotiation_strategy_{vendor_id}", res, "Negotiation Agent")
    return res

async def run_strategic_bundling() -> Dict[str, Any]:
    """
    Modular tool calling Strategic Bundling sub-agent.
    """
    analyses, summary_dict = await get_renewal_analysis()
    renewal_payload = {
        "total_contracts": summary_dict.get("total_contracts", 0),
        "high_risk_count": summary_dict.get("high_risk_count", 0),
        "medium_risk_count": summary_dict.get("medium_risk_count", 0),
        "low_risk_count": summary_dict.get("low_risk_count", 0),
        "contracts": analyses or [],
        "summary": summary_dict.get("summary", "Renewal analysis complete.")
    }
    
    opportunities, cross_summary_dict = await get_crossdeal_analysis()
    crossdeal_payload = {
        "total_vendors_analyzed": cross_summary_dict.get("total_vendors_analyzed", 0),
        "vendors_with_opportunities": cross_summary_dict.get("vendors_with_opportunities", 0),
        "total_estimated_savings": cross_summary_dict.get("total_estimated_savings", 0.0),
        "opportunities": opportunities or [],
        "summary": cross_summary_dict.get("summary", "Cross-deal analysis complete.")
    }
    
    res = await analyze_strategic_opportunities(renewal_payload, crossdeal_payload)
    write_observation("strategic_bundling", res, "Strategic Bundling Agent")
    return res

async def run_draft_email(vendor_name: str, recommended_strategy: str, expected_discount: str) -> Dict[str, Any]:
    """
    Modular tool calling Negotiation sub-agent drafting email logic.
    """
    res = generate_negotiation_email(vendor_name, recommended_strategy, expected_discount)
    write_observation(f"negotiation_email_{vendor_name}", res, "Negotiation Agent")
    return res

SYSTEM_PROMPT = """You are the Supervisor Agent of a multi-agent procurement team.
You coordinate natural language requests from the user by translating them into a sequence of tasks to execute.

Available sub-agents and their parameters:
1. `run_extract_quotes(raw_text)`: Extract details from vendor quotes.
2. `run_check_risk(vendor_name)`: Evaluate a vendor's risk profile (SLA compliance, news alerts, delay probability).
3. `run_negotiation_strategy(vendor_name)`: Generate negotiation targets and target parameters.
4. `run_strategic_bundling()`: Find multi-department consolidation and renewal savings.
5. `run_draft_email(vendor_name, recommended_strategy, expected_discount)`: Write counteroffer negotiation emails.

Given the user instruction, analyze what tasks need to be performed. Construct a plan as a JSON list of tasks.
Example Plan:
[
  {"tool": "run_check_risk", "args": {"vendor_name": "Dell"}},
  {"tool": "run_strategic_bundling", "args": {}},
  {"tool": "run_draft_email", "args": {"vendor_name": "Dell", "recommended_strategy": "Consolidation Leverage", "expected_discount": "12%"}}
]

Output ONLY a valid JSON list of tasks, matching the example above. Do NOT wrap it in markdown blockquotes, do NOT add extra text or labels outside the list.
"""

async def run_supervisor_agent(instruction: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Core brain endpoint that coordinates sub-agent tools on user request.
    """
    # Clear previous board observations
    clear_observations()
    
    if not GROQ_API_KEY:
        return "Supervisor Agent active: Groq API Key is not configured."
        
    plan = []
    # 1. Ask ChatGroq to make the plan
    max_attempts = 3
    attempt = 0
    while attempt < max_attempts:
        try:
            llm = ChatGroq(api_key=GROQ_API_KEY, model="llama-3.1-8b-instant", temperature=0, max_retries=3)
            response = llm.invoke([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"User Request: {instruction}"}
            ])
            response_text = response.content.strip()
            if "```" in response_text:
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            plan = json.loads(response_text)
            break
        except Exception as e:
            attempt += 1
            if attempt < max_attempts:
                logger.warning(f"Groq API rate limit or timeout in supervisor planning. Retrying in 2 seconds (attempt {attempt}/{max_attempts})...")
                time.sleep(2)
            else:
                logger.error(f"Failed to generate execution plan: {e}")
                return f"Failed to generate execution plan: {e}"

    if not isinstance(plan, list):
        return f"Supervisor Agent Error: Created plan was not a list. Received: {plan}"

    logger.info(f"Supervisor Agent: Generated execution plan with {len(plan)} tasks: {plan}")

    # 2. Execute plan sequentially
    for task in plan:
        tool = task.get("tool")
        args = task.get("args", {})
        
        logger.info(f"Executing task: {tool} with args: {args}")
        try:
            if tool == "run_extract_quotes":
                await run_extract_quotes(**args)
            elif tool == "run_check_risk":
                await run_check_risk(**args)
            elif tool == "run_negotiation_strategy":
                await run_negotiation_strategy(**args)
            elif tool == "run_strategic_bundling":
                await run_strategic_bundling()
            elif tool == "run_draft_email":
                await run_draft_email(**args)
            else:
                logger.warning(f"Unknown supervisor tool: {tool}")
        except Exception as te:
            logger.error(f"Error executing tool {tool}: {te}")
            write_observation(f"error_{tool}", str(te), "Supervisor Agent")

    # 3. Retrieve all observations from memory service
    observations = get_all_observations()
    observations_str = json.dumps(observations, indent=2)

    # 4. Generate final narrative summary
    summary = "Execution complete."
    attempt = 0
    while attempt < max_attempts:
        try:
            summary_prompt = f"""You are the Supervisor Agent of a multi-agent procurement team.
You have coordinated and executed a sequence of tasks based on the user's request.

User Request: {instruction}

Observations written to Shared Memory during execution:
{observations_str}

Summarize these findings into a clean, professional, and comprehensive natural language response for the user. Highlight the key results from each sub-agent (extracting quotes, checking risk, strategic bundling, negotiation strategy/email) as relevant.
"""
            llm = ChatGroq(api_key=GROQ_API_KEY, model="llama-3.1-8b-instant", temperature=0, max_retries=3)
            response = llm.invoke(summary_prompt)
            summary = response.content.strip()
            break
        except Exception as e:
            attempt += 1
            if attempt < max_attempts:
                logger.warning(f"Groq API rate limit or timeout in supervisor summary. Retrying in 2 seconds (attempt {attempt}/{max_attempts})...")
                time.sleep(2)
            else:
                logger.error(f"Failed to generate summary report: {e}")
                summary = f"Execution completed with observations: {observations_str}. Failed to generate final summary: {e}"

    return summary
