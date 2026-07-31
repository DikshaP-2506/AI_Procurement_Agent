"""
Enterprise Procurement Savings Engine

Models negotiation savings opportunities and confidence scores using:
1. Category-specific enterprise margin benchmarks (Software ELA, Hardware OEM, Services Rate Cards)
2. Spend volume scale multipliers ($50k - $250k, $250k - $1M, $1M+)
3. Multi-department dispersion factors
4. Enterprise Data Completeness & Variance Confidence Index
"""

import math
from typing import List, Tuple, Dict, Any

CATEGORY_BENCHMARKS: Dict[str, float] = {
    "software": 12.0,       # High SaaS gross margins (80%+) allow master ELA volume discounts
    "saas": 12.0,
    "cloud": 11.0,
    "hardware": 7.0,        # Lower OEM hardware margins (25-35%)
    "infrastructure": 8.0,
    "services": 9.0,        # Blended rate card volume breaks
    "consulting": 10.0,
    "corporate": 6.0,
    "default": 7.5
}

def get_category_base_rate(category: str) -> float:
    cat_clean = str(category or "").lower().strip()
    for key, rate in CATEGORY_BENCHMARKS.items():
        if key in cat_clean:
            return rate
    return CATEGORY_BENCHMARKS["default"]

def get_volume_multiplier(total_spend: float) -> float:
    if total_spend >= 2000000:
        return 1.50
    elif total_spend >= 500000:
        return 1.35
    elif total_spend >= 100000:
        return 1.15
    elif total_spend >= 25000:
        return 1.00
    else:
        return 0.85

def get_dispersion_multiplier(num_departments: int) -> float:
    if num_departments <= 1:
        return 0.0
    elif num_departments == 2:
        return 1.10
    elif num_departments == 3:
        return 1.25
    else:
        return 1.40

def estimate_enterprise_savings(
    vendor_name: str,
    category: str,
    departments: List[str],
    procurements: List[dict]
) -> Tuple[int, float, float]:
    """
    Calculate enterprise-grade negotiation savings percentage, dollar savings amount,
    and statistical confidence score.
    """
    num_depts = len(set(departments))
    if num_depts < 2:
        return 0, 0.0, 50.0

    total_spend = sum(float(p.get("procurement_value", 0) or 0) for p in procurements)
    
    base_rate = get_category_base_rate(category)
    vol_mult = get_volume_multiplier(total_spend)
    disp_mult = get_dispersion_multiplier(num_depts)

    calculated_pct = int(round(base_rate * vol_mult * disp_mult))
    savings_pct = max(5, min(25, calculated_pct))
    savings_amount = total_spend * (savings_pct / 100.0)

    # Data Completeness Confidence Index
    has_quotes = any(p.get("has_quote", False) for p in procurements)
    quote_confidence = 15.0 if has_quotes else 5.0
    
    dept_confidence = min(20.0, (num_depts - 1) * 7.0)
    spend_confidence = 15.0 if total_spend >= 100000 else 8.0
    base_confidence = 50.0

    confidence_score = round(min(98.0, base_confidence + quote_confidence + dept_confidence + spend_confidence), 1)

    return savings_pct, savings_amount, confidence_score


def format_savings_range(amount: float) -> str:
    """Format an exact dollar savings into a realistic enterprise range string (e.g. $4.5M – $5.2M)."""
    if amount <= 0:
        return "$0"
    low = amount * 0.90
    high = amount * 1.10
    if amount >= 1000000:
        return f"${low/1000000:.1f}M – ${high/1000000:.1f}M"
    elif amount >= 1000:
        return f"${low/1000:.0f}K – ${high/1000:.0f}K"
    else:
        return f"${low:,.0f} – ${high:,.0f}"


def generate_enterprise_negotiation_rationale(
    vendor_name: str,
    category: str,
    departments: List[str],
    total_value: float,
    savings_percent: int,
    savings_amount: float
) -> str:
    """
    Generate professional enterprise procurement recommendation explaining cross-deal negotiation rationale.
    """
    num_depts = len(departments)
    dept_list_str = ", ".join(departments) if departments else "multiple departments"
    range_str = format_savings_range(savings_amount)

    if total_value >= 500000 or num_depts >= 4:
        return (
            f"Consolidate vendor engagements for {vendor_name} across {num_depts} departments ({dept_list_str}) under a unified Master Service Agreement. "
            f"Standardize payment terms and harmonize SLAs to capture an estimated {range_str} ({savings_percent}%) in enterprise volume discounts on total spend of ${total_value:,.2f}."
        )
    elif num_depts == 3:
        return (
            f"Execute Enterprise Agreement consolidation for {vendor_name} across {dept_list_str} to leverage cross-department volume, "
            f"yielding projected savings of {range_str} ({savings_percent}%) through standardized payment terms and SLA harmonization."
        )
    else:
        return (
            f"Consolidate {vendor_name} procurements between {dept_list_str} into a single Master Service Agreement to capture "
            f"volume discounts of {range_str} ({savings_percent}%) on total spend of ${total_value:,.2f}."
        )

