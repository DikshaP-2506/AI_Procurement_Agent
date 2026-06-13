from typing import List, Tuple, Optional
from datetime import datetime, date, timedelta
from ..supabase_client import supabase, supabase_service
from ..models.optimization import RenewalRiskAnalysis
from .audit_service import log_agent_execution


def calculate_days_remaining(renewal_date: date) -> int:
    """Calculate days remaining until renewal date."""
    today = date.today()
    delta = renewal_date - today
    return delta.days


def determine_risk_level(
    days_remaining: int,
    auto_renewal: bool,
    notice_period_days: int
) -> str:

    if days_remaining < 0:
        return "CRITICAL"

    if auto_renewal and days_remaining <= notice_period_days:
        return "HIGH"

    if days_remaining <= 30:
        return "HIGH"

    if days_remaining <= 90:
        return "MEDIUM"

    return "LOW"

def determine_status(days_remaining: int) -> str:
    if days_remaining < 0:
        return "EXPIRED"
    return "ACTIVE"

def generate_renewal_recommendation(
    days_remaining: int,
    auto_renewal: bool,
    contract_name: str
) -> str:
    """Generate actionable recommendation based on renewal context."""
    if auto_renewal:
        if days_remaining <= 0:
            return "Auto-renewal detected. Contract has already renewed. Review immediately."
        elif days_remaining <= 30:
            return f"Auto-renewal detected. Procurement action required within {days_remaining} days."
        else:
            return "Auto-renewal detected. Begin renegotiation planning to avoid forced renewal."
    else:
        if days_remaining < 0:
            return f"Contract expired {abs(days_remaining)} days ago. Immediate review required."
        elif days_remaining <= 30:
            return f"Contract renews in {days_remaining} days. Begin renegotiation immediately."
        elif days_remaining <= 90:
            return f"Contract renewal approaching in {days_remaining} days. Start negotiation process."
        else:
            return f"Contract renewal in {days_remaining} days. Schedule negotiation review."


async def fetch_contracts_from_supabase() -> List[dict]:
    """
    Fetch all contracts from Supabase.
    
    Assumes contracts table with fields:
    - id, vendor_id, contract_name, start_date, end_date, renewal_date,
      auto_renewal, notice_period_days, contract_value
    """
    try:
        client = supabase_service or supabase
        response = client.table("contracts").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        raise Exception(f"Failed to fetch contracts from Supabase: {str(e)}")


async def fetch_vendor_name(vendor_id: str) -> str:
    """Fetch vendor name by vendor_id."""
    try:
        client = supabase_service or supabase
        response = client.table("vendors").select("vendor_name").eq("id", vendor_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0].get("vendor_name", "Unknown Vendor")
        return "Unknown Vendor"
    except Exception:
        return "Unknown Vendor"


async def analyze_contract_renewal(contract: dict) -> RenewalRiskAnalysis:
    """
    Analyze a single contract for renewal risk.
    
    Args:
        contract: Contract record from Supabase
        
    Returns:
        RenewalRiskAnalysis with risk assessment and recommendation
    """
    renewal_date_str = contract.get("renewal_date")
    if isinstance(renewal_date_str, str):
        renewal_date = datetime.fromisoformat(renewal_date_str).date()
    else:
        renewal_date = renewal_date_str

    days_remaining = calculate_days_remaining(renewal_date)
    risk_level = determine_risk_level(
        days_remaining,
        contract.get("auto_renewal", False),
        contract.get("notice_period_days", 0)
    )
    
    vendor_name = contract.get("vendor_name") or await fetch_vendor_name(contract.get("vendor_id", ""))
    recommendation = generate_renewal_recommendation(
        days_remaining,
        contract.get("auto_renewal", False),
        contract.get("contract_name", "")
    )
    
    # Generate explainability string
    auto_renew_status = "enabled" if contract.get("auto_renewal", False) else "disabled"
    notice_days = contract.get("notice_period_days", 0)
    if days_remaining < 0:
        explainability = f"Contract has expired {abs(days_remaining)} days ago."
    elif contract.get("auto_renewal", False) and days_remaining <= notice_days:
        explainability = f"Auto-renewal is enabled and contract is within notice period ({days_remaining} days left vs {notice_days} days notice required)."
    elif days_remaining <= 30:
        explainability = f"Contract is expiring in {days_remaining} days, notice period is {notice_days} days with auto-renewal {auto_renew_status}."
    elif days_remaining <= 90:
        explainability = f"Contract is approaching renewal in {days_remaining} days (notice period: {notice_days} days)."
    else:
        explainability = f"Contract is in good standing with {days_remaining} days remaining (notice period: {notice_days} days)."
        
    return RenewalRiskAnalysis(
        contract_id=contract.get("id", ""),
        contract_name=contract.get("contract_name", ""),
        vendor_name=vendor_name,
        renewal_date=renewal_date,
        days_remaining=days_remaining,
        risk_level=risk_level,
        recommendation=recommendation,
        explainability=explainability
    )


async def get_renewal_analysis() -> Tuple[List[RenewalRiskAnalysis], dict]:
    """
    Analyze all contracts for renewal risk.

    Returns:
        Tuple of (list of RenewalRiskAnalysis, summary dict)
    """
    contracts = await fetch_contracts_from_supabase()

    if not contracts:
        return [], {
            "total_contracts": 0,
            "high_risk_count": 0,
            "medium_risk_count": 0,
            "low_risk_count": 0,
            "unknown_risk_count": 0,
            "summary": "No contracts found in the system."
        }

    analyses: List[RenewalRiskAnalysis] = []

    for contract in contracts:
        try:
            renewal_date = contract.get("renewal_date")

            # Handle contracts with missing renewal dates
            if not renewal_date:
                analysis = RenewalRiskAnalysis(
                    contract_id=contract.get("id", ""),
                    contract_name=contract.get("contract_name", "Unknown Contract"),
                    vendor_name=contract.get("vendor_name") or await fetch_vendor_name(contract.get("vendor_id", "")),
                    renewal_date=None,
                    days_remaining=None,
                    risk_level="UNKNOWN",
                    recommendation="Renewal date unavailable. Manual review required.",
                    explainability="No renewal date specified in database contract record."
                )

                analyses.append(analysis)
                continue

            analysis = await analyze_contract_renewal(contract)
            analyses.append(analysis)

        except Exception as e:
            # Log error but continue processing other contracts
            print(f"Error analyzing contract {contract.get('id')}: {str(e)}")
            continue

    # Count risk levels
    high_risk = sum(1 for a in analyses if a.risk_level in ["HIGH", "CRITICAL"])
    medium_risk = sum(1 for a in analyses if a.risk_level == "MEDIUM")
    low_risk = sum(1 for a in analyses if a.risk_level == "LOW")
    unknown_risk = sum(1 for a in analyses if a.risk_level == "UNKNOWN")

    # Generate summary
    summary_parts = []

    if high_risk > 0:
        summary_parts.append(
            f"{high_risk} CRITICAL/HIGH-risk contracts requiring immediate action"
        )

    if medium_risk > 0:
        summary_parts.append(
            f"{medium_risk} MEDIUM-risk contracts approaching renewal"
        )

    if low_risk > 0:
        summary_parts.append(
            f"{low_risk} LOW-risk contracts with adequate time"
        )

    if unknown_risk > 0:
        summary_parts.append(
            f"{unknown_risk} contracts missing renewal dates and requiring manual review"
        )

    summary = (
        ". ".join(summary_parts)
        if summary_parts
        else "All contracts are in good standing."
    )

    summary_dict = {
        "total_contracts": len(contracts),
        "high_risk_count": high_risk,
        "medium_risk_count": medium_risk,
        "low_risk_count": low_risk,
        "unknown_risk_count": unknown_risk,
        "summary": summary
    }

    # Log agent execution
    await log_agent_execution(
        agent_name="Subscription Renewal Catcher",
        action_type="renewal_analysis",
        input_payload={
            "source": "contracts table",
            "total_contracts_analyzed": len(contracts)
        },
        output_payload={
            "total_contracts": len(contracts),
            "high_risk_count": high_risk,
            "medium_risk_count": medium_risk,
            "low_risk_count": low_risk,
            "unknown_risk_count": unknown_risk,
            "contracts_analyzed": [
                {
                    "contract_id": a.contract_id,
                    "vendor_name": a.vendor_name,
                    "risk_level": a.risk_level,
                    "days_remaining": a.days_remaining
                }
                for a in analyses
            ]
        },
        reasoning=(
            "Analyzed all contracts for renewal risk based on auto-renewal "
            "status, notice period, days remaining, and renewal date availability."
        )
    )

    return analyses, summary_dict