import os
import json
from typing import Dict, Any, List, Optional

from langchain_groq import ChatGroq

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def _make_strategic_prompt(
    renewal_data: Dict[str, Any],
    crossdeal_data: Dict[str, Any]
) -> str:
    """
    Generate strategic procurement analysis prompt.
    
    Args:
        renewal_data: Output from renewal analysis (RenewalAnalysisResponse)
        crossdeal_data: Output from cross-deal analysis (CrossDealAnalysisResponse)
    
    Returns:
        Prompt string for LLM
    """
    prompt = f"""You are a senior procurement consultant with expertise in vendor management and strategic cost optimization.

You have received two procurement analysis reports:

RENEWAL ANALYSIS REPORT:
{json.dumps(renewal_data, indent=2, default=str)}

CROSS-DEAL ANALYSIS REPORT:
{json.dumps(crossdeal_data, indent=2, default=str)}

Your task is to synthesize these insights into strategic procurement recommendations.

ANALYSIS REQUIREMENTS:

1. Identify vendor consolidation opportunities by combining renewal and cross-deal data.
2. Suggest bundled negotiations that leverage both contract renewals and multi-department opportunities.
3. Highlight immediate cost optimization opportunities with specific vendor names.
4. Estimate potential strategic savings across identified opportunities.
5. Assign business priority (HIGH, MEDIUM, LOW) based on impact and urgency.

STRATEGIC ACTIONS CRITERIA:

For HIGH priority: Combines high-risk renewals with multi-department opportunities, or very high savings potential.
For MEDIUM priority: Moderate savings or risk without immediate urgency.
For LOW priority: Less impactful but still worth tracking.

Generate strategic procurement actions that a procurement leader would execute.

Return ONLY this JSON with no explanation, no markdown, no backticks:
{{
  "strategic_actions": [
    ""
  ],
  "estimated_savings": "string with currency format like $500,000-$750,000",
  "priority": "HIGH|MEDIUM|LOW",
  "business_impact": "brief description of overall impact",
  "reasoning": "explanation of how these actions address the identified opportunities"
}}

Rules:
- Return ONLY raw JSON, nothing else
- No markdown backticks
- No explanation before or after JSON
- If no opportunities exist, return empty strategic_actions array with LOW priority
- strategic_actions should be 2-5 actionable recommendations
- Each action should reference specific vendors when possible
- Savings estimate should be realistic based on provided data
- Reasoning should connect actions directly to the analysis data
"""
    return prompt


def generate_strategic_analysis(
    renewal_data: Dict[str, Any],
    crossdeal_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate strategic procurement recommendations based on renewal and cross-deal analysis.
    
    Args:
        renewal_data: Renewal analysis response containing contract risks
        crossdeal_data: Cross-deal analysis response containing consolidation opportunities
    
    Returns:
        Dict with strategic actions, savings estimate, priority, impact, and reasoning
    """
    default_response = {
        "strategic_actions": [],
        "estimated_savings": "$0",
        "priority": "LOW",
        "business_impact": "Insufficient data for strategic analysis.",
        "reasoning": "No meaningful renewal or cross-deal opportunities identified in the current data."
    }
    
    if not GROQ_API_KEY:
        return default_response

    try:
        # Initialize LLM with same parameters as quote_agent
        llm = ChatGroq(api_key=GROQ_API_KEY, model="llama-3.1-8b-instant", temperature=0)
        
        # Generate prompt
        prompt = _make_strategic_prompt(renewal_data, crossdeal_data)
        
        # Invoke LLM
        response = llm.invoke(prompt)
        response_text = response.content.strip()
        
        # Clean response: remove markdown backticks if present
        if "```" in response_text:
            response_text = response_text.replace("```json", "").replace("```", "").strip()
        
        # Parse JSON
        parsed = json.loads(response_text)
        
        # Validate and ensure result matches expected schema
        result = {
            "strategic_actions": parsed.get("strategic_actions", []),
            "estimated_savings": parsed.get("estimated_savings", "$0"),
            "priority": parsed.get("priority", "MEDIUM"),
            "business_impact": parsed.get("business_impact", ""),
            "reasoning": parsed.get("reasoning", "")
        }
        
        # Validate priority
        if result["priority"] not in ["HIGH", "MEDIUM", "LOW"]:
            result["priority"] = "MEDIUM"
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"JSON Parsing Error: {e}")
        print(f"Response text: {response_text}")
        return default_response
    except Exception as e:
        print(f"Strategic Analysis Error: {e}")
        return default_response
