import asyncio
import logging
from typing import List, Tuple, Optional
from datetime import datetime, date, timedelta
from ..supabase_client import supabase, supabase_service
from ..models.optimization import RenewalRiskAnalysis
from .audit_service import log_agent_execution


logger = logging.getLogger("uvicorn.error")


def calculate_days_remaining(renewal_date: date) -> int:
    """Calculate days remaining until renewal date relative to today."""
    today = date.today()
    delta = renewal_date - today
    return delta.days


def determine_risk_level(
    days_remaining: int,
    auto_renewal: bool,
    notice_period_days: int
) -> str:
    """
    Determine risk level using notice-period deadline math.
    Notice Deadline = Renewal Date - Notice Period Days.
    Days to Notice Deadline = days_remaining - notice_period_days.
    """
    if days_remaining < 0:
        return "CRITICAL"

    days_to_notice = days_remaining - notice_period_days

    # Critical: Auto-renewal is enabled and notice deadline has passed or passes today
    if auto_renewal and days_to_notice <= 0:
        return "CRITICAL"

    # High: Imminent renewal within 30 days OR within 15 days of notice deadline
    if days_to_notice <= 15 or days_remaining <= 30:
        return "HIGH"

    # Medium: Renewal within 90 days OR within 45 days of notice deadline
    if days_to_notice <= 45 or days_remaining <= 90:
        return "MEDIUM"

    return "LOW"


def determine_status(days_remaining: int) -> str:
    if days_remaining < 0:
        return "EXPIRED"
    return "ACTIVE"


def generate_renewal_recommendation(
    days_remaining: int,
    auto_renewal: bool,
    notice_period_days: int,
    contract_name: str,
    vendor_name: str
) -> str:
    """Generate distinct, highly actionable recommendations tailored to contract and vendor context based on risk level."""
    days_to_notice = days_remaining - notice_period_days

    if days_remaining < 0:
        overdue_days = abs(days_remaining)
        return (
            f"Execute emergency contract extension for {contract_name} with {vendor_name} (expired {overdue_days} day{'s' if overdue_days != 1 else ''} ago) "
            f"or evaluate alternate suppliers to eliminate out-of-contract rates."
        )

    if auto_renewal:
        if days_to_notice <= 0:
            overdue_notice = abs(days_to_notice)
            return (
                f"Initiate immediate renewal negotiations for {contract_name} with {vendor_name}. Notice deadline passed {overdue_notice} day{'s' if overdue_notice != 1 else ''} ago "
                f"({notice_period_days} days notice required); issue formal non-renewal notice to preserve leverage."
            )
        elif days_to_notice <= 15:
            return (
                f"Finalize commercial negotiations and prepare renewal approval for {contract_name} with {vendor_name} before notice deadline in {days_to_notice} day{'s' if days_to_notice != 1 else ''}."
            )
        else:
            return (
                f"Schedule routine contract review and monitor vendor performance for {contract_name} with {vendor_name} ahead of notice window in {days_to_notice} days."
            )
    else:
        if days_remaining <= 30:
            return (
                f"Finalize commercial negotiations and confirm vendor pricing for {contract_name} with {vendor_name} before expiration in {days_remaining} day{'s' if days_remaining != 1 else ''}."
            )
        elif days_remaining <= 90:
            return (
                f"Complete legal review and prepare renewal approval for {contract_name} with {vendor_name} ({days_remaining} days remaining)."
            )
        else:
            return (
                f"Benchmark market pricing and prepare for future renewal cycle for {contract_name} with {vendor_name} ({days_remaining} days remaining)."
            )



async def fetch_contracts_from_supabase() -> List[dict]:
    """
    Fetch all contracts from Supabase with error resilience and fast 0.8s timeout.
    """
    try:
        client = supabase_service or supabase
        response = await asyncio.wait_for(
            asyncio.to_thread(lambda: client.table("contracts").select("*").execute()),
            timeout=0.8
        )
        return response.data if response.data else []
    except Exception as e:
        logger.warning(f"Unable to fetch contracts from Supabase (network timeout/fallback): {e}")
        return []



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
    Analyze a single contract for renewal risk using notice deadline math.
    """
    renewal_date_str = contract.get("renewal_date")
    if isinstance(renewal_date_str, str):
        renewal_date = datetime.fromisoformat(renewal_date_str.replace("Z", "")).date()
    elif isinstance(renewal_date_str, (datetime, date)):
        renewal_date = renewal_date_str if isinstance(renewal_date_str, date) else renewal_date_str.date()
    else:
        renewal_date = date.today() + timedelta(days=60)

    auto_renewal = bool(contract.get("auto_renewal", False))
    notice_period_days = int(contract.get("notice_period_days", 30) or 30)
    days_remaining = calculate_days_remaining(renewal_date)
    
    risk_level = determine_risk_level(
        days_remaining,
        auto_renewal,
        notice_period_days
    )
    
    vendor_name = contract.get("vendor_name") or await fetch_vendor_name(contract.get("vendor_id", ""))
    contract_name = contract.get("contract_name", "Vendor Contract")
    
    recommendation = generate_renewal_recommendation(
        days_remaining,
        auto_renewal,
        notice_period_days,
        contract_name,
        vendor_name
    )
    
    # Contextual explainability synthesis referencing only deterministic facts
    days_to_notice = days_remaining - notice_period_days
    
    if days_remaining < 0:
        explainability = f"CRITICAL Risk because the contract expired {abs(days_remaining)} days ago."
    elif auto_renewal and days_to_notice <= 0:
        explainability = f"CRITICAL Risk because the notice deadline passed {abs(days_to_notice)} days ago for auto-renewal on {renewal_date}."
    elif days_remaining <= 30:
        explainability = f"HIGH Risk because only {days_remaining} day{'s' if days_remaining != 1 else ''} remain before renewal."
    elif days_to_notice <= 45 or days_remaining <= 90:
        explainability = f"MEDIUM Risk because {days_remaining} days remain before renewal and notice deadline is in {days_to_notice} days."
    else:
        explainability = f"LOW Risk because the contract expires in {days_remaining} days and is currently outside its notice period."
        
    return RenewalRiskAnalysis(
        contract_id=str(contract.get("id", "")),
        contract_name=contract_name,
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
    """
    contracts = await fetch_contracts_from_supabase()

    if not contracts:
        return [], {
            "total_contracts": 0,
            "high_risk_count": 0,
            "medium_risk_count": 0,
            "low_risk_count": 0,
            "unknown_risk_count": 0,
            "summary": "No contract records found for renewal risk analysis."
        }

    analyses: List[RenewalRiskAnalysis] = []

    for contract in contracts:
        try:
            renewal_date = contract.get("renewal_date")

            if not renewal_date:
                analysis = RenewalRiskAnalysis(
                    contract_id=str(contract.get("id", "")),
                    contract_name=contract.get("contract_name", "Unspecified Contract"),
                    vendor_name=contract.get("vendor_name") or await fetch_vendor_name(contract.get("vendor_id", "")),
                    renewal_date=None,
                    days_remaining=None,
                    risk_level="UNKNOWN",
                    recommendation="Renewal date unavailable. Manual contract audit required.",
                    explainability="No renewal date specified in database contract record."
                )
                analyses.append(analysis)
                continue

            analysis = await analyze_contract_renewal(contract)
            analyses.append(analysis)

        except Exception as e:
            logger.error(f"Error analyzing contract {contract.get('id')}: {e}")
            continue

    high_risk = sum(1 for a in analyses if a.risk_level in ["HIGH", "CRITICAL"])
    medium_risk = sum(1 for a in analyses if a.risk_level == "MEDIUM")
    low_risk = sum(1 for a in analyses if a.risk_level == "LOW")
    unknown_risk = sum(1 for a in analyses if a.risk_level == "UNKNOWN")

    summary_parts = []
    if high_risk > 0:
        summary_parts.append(f"{high_risk} CRITICAL/HIGH-risk contracts requiring urgent action")
    if medium_risk > 0:
        summary_parts.append(f"{medium_risk} MEDIUM-risk contracts approaching notice deadline")
    if low_risk > 0:
        summary_parts.append(f"{low_risk} LOW-risk contracts in good standing")
    if unknown_risk > 0:
        summary_parts.append(f"{unknown_risk} contracts missing renewal dates")

    summary = ". ".join(summary_parts) if summary_parts else "All active contracts are in good standing."

    summary_dict = {
        "total_contracts": len(contracts),
        "high_risk_count": high_risk,
        "medium_risk_count": medium_risk,
        "low_risk_count": low_risk,
        "unknown_risk_count": unknown_risk,
        "summary": summary
    }

    # Enrich recommendations and explainability using grounded LLM presentation layer
    try:
        from .llm_narrative_service import enrich_renewal_analyses_with_llm
        analyses = await enrich_renewal_analyses_with_llm(analyses)
    except Exception as e:
        logger.warning(f"Unable to run LLM narrative enrichment on renewal contracts: {e}")

    # Audit summary message
    urgent_contracts = [a for a in analyses if a.risk_level in ["CRITICAL", "HIGH"]]
    audit_reasoning = (
        f"Renewal analysis completed. Evaluated {len(contracts)} contracts and identified {len(urgent_contracts)} contract{'s' if len(urgent_contracts) != 1 else ''} requiring immediate procurement action."
    )

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
            "unknown_risk_count": unknown_risk
        },
        reasoning=audit_reasoning
    )

    return analyses, summary_dict