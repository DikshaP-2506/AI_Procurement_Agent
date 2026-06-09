from datetime import datetime, date, timedelta
import random
import pandas as pd
from uuid import uuid5, NAMESPACE_DNS

random.seed(20260605)

# Final schema columns
cols = [
    "id",
    "vendor_id",
    "negotiation_date",
    "discount_requested",
    "discount_received",
    "successful_tactics",
    "failed_tactics",
    "outcome",
    "notes",
    "created_at",
    "vendor_name",
    "product_category",
    "initial_quote_value",
    "final_negotiated_value",
    "strategy_used",
    "negotiation_rounds",
    "success_score",
]

# Procurement-oriented vendor profiles and the categories they plausibly serve.
vendor_profiles = {
    "Dell": ["Laptops", "Servers", "Workstations"],
    "HP": ["Laptops", "Printers", "Workstations"],
    "Lenovo": ["Laptops", "Servers", "Workstations"],
    "Cisco": ["Networking Equipment", "Security Software"],
    "Microsoft": ["Software Licenses", "Security Software", "Cloud Services"],
    "Adobe": ["Software Licenses"],
    "AWS": ["Cloud Services"],
    "Google Cloud": ["Cloud Services"],
    "Oracle": ["Software Licenses", "Cloud Services"],
    "Salesforce": ["Software Licenses", "Consulting Services"],
    "SAP": ["Software Licenses", "Consulting Services"],
    "IBM": ["Consulting Services", "Security Software", "Cloud Services"],
    "FedEx": ["Logistics Services"],
    "DHL": ["Logistics Services"],
    "Maersk": ["Logistics Services"],
    "Tata Steel": ["Raw Materials"],
    "JSW Steel": ["Raw Materials"],
    "Reliance Industries": ["Raw Materials", "Packaging Materials"],
    "3M": ["Office Equipment", "Packaging Materials"],
    "IKEA Business": ["Office Equipment", "Facility Services"],
    "Schneider Electric": ["Networking Equipment", "Facility Services"],
    "Honeywell": ["Security Software", "Facility Services"],
    "Accenture": ["Consulting Services"],
    "Wipro": ["Consulting Services", "Software Licenses"],
    "TCS": ["Consulting Services"],
    "Infosys": ["Consulting Services"],
}

# Strategy patterns by category (procurement-realistic).
category_strategies = {
    "Laptops": ["Bulk Purchase", "Competitive Bidding", "Bundle Negotiation", "Vendor Consolidation"],
    "Servers": ["Bulk Purchase", "Competitive Bidding", "Volume Commitment", "Long-Term Contract"],
    "Workstations": ["Bulk Purchase", "Competitive Bidding", "Bundle Negotiation"],
    "Printers": ["Bulk Purchase", "Vendor Consolidation", "Bundle Negotiation"],
    "Networking Equipment": ["Competitive Bidding", "Bulk Purchase", "Bundle Negotiation"],
    "Software Licenses": ["Multi-Year Contract", "License Consolidation", "Vendor Consolidation", "Early Payment Incentive"],
    "Cloud Services": ["Volume Commitment", "Long-Term Contract", "Reserved Capacity", "Multi-Supplier Leverage"],
    "Logistics Services": ["Long-Term Contract", "Volume Commitment", "Competitive Bidding"],
    "Raw Materials": ["Bulk Purchase", "Multi-Supplier Leverage", "Long-Term Contract", "Vendor Consolidation"],
    "Office Equipment": ["Bundle Negotiation", "Bulk Purchase", "Vendor Consolidation"],
    "Consulting Services": ["Scope Negotiation", "Retainer Contract", "Long-Term Contract", "Competitive Bidding"],
    "Security Software": ["Multi-Year Contract", "Vendor Consolidation", "Early Payment Incentive"],
    "Facility Services": ["Long-Term Contract", "Vendor Consolidation", "Scope Negotiation"],
    "Packaging Materials": ["Bulk Purchase", "Volume Commitment", "Vendor Consolidation"],
}

# Typical category ranges and procurement logic.
category_ranges = {
    "Laptops": (70000, 180000),
    "Servers": (250000, 2200000),
    "Workstations": (90000, 320000),
    "Printers": (30000, 900000),
    "Networking Equipment": (120000, 1200000),
    "Software Licenses": (80000, 3000000),
    "Cloud Services": (200000, 5000000),
    "Logistics Services": (60000, 1200000),
    "Raw Materials": (300000, 8000000),
    "Office Equipment": (30000, 900000),
    "Consulting Services": (150000, 6000000),
    "Security Software": (120000, 2500000),
    "Facility Services": (80000, 2000000),
    "Packaging Materials": (50000, 1800000),
}

# Strategy effectiveness heuristics by category.
strategy_effect = {
    "Bulk Purchase": {"success_boost": 8, "partial_boost": 4, "failure_penalty": 3},
    "Competitive Bidding": {"success_boost": 7, "partial_boost": 3, "failure_penalty": 4},
    "Long-Term Contract": {"success_boost": 9, "partial_boost": 4, "failure_penalty": 2},
    "Volume Commitment": {"success_boost": 8, "partial_boost": 4, "failure_penalty": 2},
    "Bundle Negotiation": {"success_boost": 6, "partial_boost": 3, "failure_penalty": 3},
    "Vendor Consolidation": {"success_boost": 7, "partial_boost": 3, "failure_penalty": 3},
    "Early Payment Incentive": {"success_boost": 5, "partial_boost": 2, "failure_penalty": 2},
    "Multi-Supplier Leverage": {"success_boost": 7, "partial_boost": 3, "failure_penalty": 4},
    "Multi-Year Contract": {"success_boost": 9, "partial_boost": 4, "failure_penalty": 2},
    "License Consolidation": {"success_boost": 8, "partial_boost": 4, "failure_penalty": 2},
    "Reserved Capacity": {"success_boost": 8, "partial_boost": 4, "failure_penalty": 2},
    "Scope Negotiation": {"success_boost": 6, "partial_boost": 3, "failure_penalty": 3},
    "Retainer Contract": {"success_boost": 7, "partial_boost": 3, "failure_penalty": 2},
}

vendor_behaviors = {
    "Dell": "responds well to bulk purchases and bundle negotiations",
    "HP": "is competitive when presented with multiple quotes",
    "Lenovo": "offers better pricing on volume deals",
    "Cisco": "often needs competitive bidding and strong volume commitments",
    "Microsoft": "prefers multi-year or enterprise agreements",
    "Adobe": "usually rewards license consolidation and long-term terms",
    "AWS": "accepts volume commitments and reserved capacity deals",
    "Google Cloud": "supports committed usage discounts",
    "Oracle": "favors long-term enterprise commitments",
    "Salesforce": "responds to multi-year and scope-based negotiations",
    "SAP": "values long-term contracts and portfolio consolidation",
    "IBM": "is open to consulting-led bundle deals",
    "FedEx": "responds to route volume and long-term logistics terms",
    "DHL": "supports volume-based shipping commitments",
    "Maersk": "prefers annual contract commitments",
    "Tata Steel": "responds to large volume and long-term supply agreements",
    "JSW Steel": "offers better rates with steady procurement volumes",
    "Reliance Industries": "responds to volume and multi-year commitments",
    "3M": "works well with bundled office and packaging orders",
    "IKEA Business": "accepts facility bundle and bulk office orders",
    "Schneider Electric": "responds to bundled infrastructure purchases",
    "Honeywell": "prefers enterprise service and security package deals",
    "Accenture": "negotiates best on scope and retainer structure",
    "Wipro": "is competitive on multi-year service agreements",
    "TCS": "responds to long-term consulting commitments",
    "Infosys": "offers better pricing on recurring service scope",
}

success_templates = [
    "Negotiation closed after presenting a structured volume-based offer and vendor comparison data.",
    "Additional value secured through a bundle-based commercial discussion and clear procurement timeline.",
    "Vendor accepted revised commercial terms after enterprise commitment and renewal horizon were highlighted.",
    "Price reduction achieved by combining multiple line items into one consolidated procurement order.",
    "Successful round completed after competitor quotes and internal spend consolidation were shared.",
]
partial_templates = [
    "Vendor agreed to a partial reduction after comparing total spend across multiple business units.",
    "Some commercial concessions were achieved, but the vendor retained pricing on premium terms.",
    "Discount improved after several rounds, though the vendor limited concessions due to supply pressure.",
    "Negotiation ended with a moderate improvement by shifting from one-time purchase to commitment-based terms.",
]
failure_templates = [
    "Vendor declined additional reductions due to a fixed price floor and limited pricing flexibility.",
    "No meaningful concession was achieved because the vendor held a strong market position.",
    "Negotiation stalled after the vendor refused to move on already discounted enterprise pricing.",
    "Commercial terms remained unchanged despite alternative quotes and escalation discussions.",
]

strategy_success_tactics = {
    "Bulk Purchase": "Highlighted total unit volume, consolidated items, and requested slab-based discounts.",
    "Competitive Bidding": "Presented competing quotes and pushed for price matching or better commercial terms.",
    "Long-Term Contract": "Committed to a longer contract horizon in exchange for improved pricing.",
    "Volume Commitment": "Shared projected consumption volumes to secure tiered discounts.",
    "Bundle Negotiation": "Combined related items/services into a single procurement package.",
    "Vendor Consolidation": "Moved multiple purchases to a single vendor to improve pricing leverage.",
    "Early Payment Incentive": "Offered faster payment terms in exchange for a commercial reduction.",
    "Multi-Supplier Leverage": "Used alternative supplier options to strengthen negotiation position.",
    "Multi-Year Contract": "Extended licensing horizon to get enterprise-level pricing and support.",
    "License Consolidation": "Reduced duplicate licenses and consolidated seats into a single agreement.",
    "Reserved Capacity": "Committed capacity upfront to obtain committed-use pricing.",
    "Scope Negotiation": "Re-scoped deliverables to align cost with business priorities.",
    "Retainer Contract": "Shifted the model to ongoing support with predictable monthly billing.",
}

strategy_failure_tactics = {
    "Bulk Purchase": "Supplier was unwilling to go below its volume floor.",
    "Competitive Bidding": "Competing quotes were not close enough to force a price match.",
    "Long-Term Contract": "Vendor did not offer additional benefit for longer duration.",
    "Volume Commitment": "Forecast volume was not sufficient to unlock better tiers.",
    "Bundle Negotiation": "Package discount remained capped by the vendor's pricing policy.",
    "Vendor Consolidation": "Single-vendor consolidation was not enough to move pricing.",
    "Early Payment Incentive": "Cash discount was limited and did not materially change the quote.",
    "Multi-Supplier Leverage": "Vendor indicated it could not match alternate supplier pricing.",
    "Multi-Year Contract": "Enterprise terms were fixed and renegotiation yielded no extra concession.",
    "License Consolidation": "Consolidation reduced complexity but not the commercial rate.",
    "Reserved Capacity": "Committed-use terms were already at the lowest available rate.",
    "Scope Negotiation": "Vendor kept the same pricing due to fixed delivery scope.",
    "Retainer Contract": "Retainer terms were not improved after multiple negotiation rounds.",
}

def success_score_for(outcome, received):
    if outcome == "Success":
        base = 82 + min(15, received * 1.5)
        return round(min(100, base), 1)
    if outcome == "Partial Success":
        base = 55 + min(18, received * 1.0)
        return round(min(79, base), 1)
    return round(max(10, 48 - received * 2), 1)

# Build procurement-focused pool
pool = []
for vendor, cats in vendor_profiles.items():
    for cat in cats:
        for strat in category_strategies[cat]:
            pool.append((vendor, cat, strat))

selected = []
idx = 0
while len(selected) < 120:
    selected.append(pool[idx % len(pool)])
    idx += 7

# Overwrite early entries with high-value procurement examples
special_sequences = [
    ("Dell", "Laptops", "Bulk Purchase"),
    ("HP", "Laptops", "Competitive Bidding"),
    ("Lenovo", "Servers", "Volume Commitment"),
    ("Microsoft", "Software Licenses", "Multi-Year Contract"),
    ("AWS", "Cloud Services", "Reserved Capacity"),
    ("Google Cloud", "Cloud Services", "Volume Commitment"),
    ("Cisco", "Networking Equipment", "Competitive Bidding"),
    ("Adobe", "Software Licenses", "License Consolidation"),
    ("FedEx", "Logistics Services", "Long-Term Contract"),
    ("DHL", "Logistics Services", "Volume Commitment"),
    ("Tata Steel", "Raw Materials", "Bulk Purchase"),
    ("JSW Steel", "Raw Materials", "Long-Term Contract"),
    ("Accenture", "Consulting Services", "Scope Negotiation"),
    ("IBM", "Consulting Services", "Retainer Contract"),
    ("3M", "Office Equipment", "Bundle Negotiation"),
    ("IKEA Business", "Office Equipment", "Vendor Consolidation"),
]
for i, triplet in enumerate(special_sequences):
    selected[i] = triplet

# Outcome distribution
outcome_plan = (["Success"] * 60) + (["Partial Success"] * 30) + (["Failure"] * 30)

records = []
base_date = date(2024, 1, 3)
base_created = datetime(2024, 1, 3, 10, 30)

for i, ((vendor, category, strategy), outcome) in enumerate(zip(selected, outcome_plan), start=1):
    low, high = category_ranges[category]
    if category in ["Software Licenses", "Cloud Services", "Raw Materials", "Consulting Services"]:
        initial = random.randint(int(low * 1.1), int(high * 0.85))
    else:
        initial = random.randint(low, high)

    if category in ["Cloud Services", "Software Licenses", "Consulting Services"]:
        discount_requested = random.choice([8, 10, 12, 15, 18, 20, 22])
    elif category in ["Raw Materials", "Servers"]:
        discount_requested = random.choice([5, 8, 10, 12, 15, 18])
    else:
        discount_requested = random.choice([5, 7, 8, 10, 12, 15])

    effect = strategy_effect.get(strategy, {"success_boost": 6, "partial_boost": 3, "failure_penalty": 3})

    if outcome == "Success":
        received = min(discount_requested, random.choice([max(3, discount_requested - 2), discount_requested - 1, discount_requested]))
        negotiation_rounds = random.randint(1, 3)
        success_score = success_score_for(outcome, received) + effect["success_boost"] * 0.2
        successful_tactics = strategy_success_tactics.get(strategy, f"Applied {strategy.lower()} to improve commercial terms.")
        failed_tactics = ""
        notes = random.choice(success_templates) + f" Vendor behavior: {vendor_behaviors.get(vendor, 'aligned with procurement requirements')}."
    elif outcome == "Partial Success":
        received = max(1, min(discount_requested - 1, random.choice([discount_requested // 2, discount_requested // 2 + 1, discount_requested - 2])))
        negotiation_rounds = random.randint(2, 4)
        success_score = success_score_for(outcome, received) + effect["partial_boost"] * 0.2
        successful_tactics = strategy_success_tactics.get(strategy, f"Used {strategy.lower()} to secure partial concessions.")
        failed_tactics = random.choice([
            "Could not secure the full requested discount.",
            "Vendor maintained pricing on part of the scope.",
            "Enterprise pricing was improved but not fully aligned to target.",
        ])
        notes = random.choice(partial_templates) + f" Vendor behavior: {vendor_behaviors.get(vendor, 'showed moderate flexibility')}."
    else:
        received = 0
        negotiation_rounds = random.randint(3, 5)
        success_score = success_score_for(outcome, received) - effect["failure_penalty"] * 0.2
        successful_tactics = ""
        failed_tactics = strategy_failure_tactics.get(strategy, f"{strategy} did not move the vendor below its pricing threshold.")
        notes = random.choice(failure_templates) + f" Vendor behavior: {vendor_behaviors.get(vendor, 'had limited flexibility')}."

    final_value = round(initial * (1 - received / 100), 2)
    nd = base_date + timedelta(days=i * 3)
    ct = base_created + timedelta(days=i * 3, hours=(i % 9), minutes=(i * 7) % 60)

    vendor_id = str(uuid5(NAMESPACE_DNS, f"vendor::{vendor}"))
    record_id = str(uuid5(NAMESPACE_DNS, f"neg::{i:03d}::{vendor}::{category}::{strategy}::{outcome}"))

    records.append({
        "id": record_id,
        "vendor_id": vendor_id,
        "negotiation_date": nd.isoformat(),
        "discount_requested": discount_requested,
        "discount_received": received,
        "successful_tactics": successful_tactics,
        "failed_tactics": failed_tactics,
        "outcome": outcome,
        "notes": notes,
        "created_at": ct.isoformat(timespec="seconds"),
        "vendor_name": vendor,
        "product_category": category,
        "initial_quote_value": initial,
        "final_negotiated_value": final_value,
        "strategy_used": strategy,
        "negotiation_rounds": negotiation_rounds,
        "success_score": round(max(0, min(100, success_score)), 1),
    })

df = pd.DataFrame(records, columns=cols)
csv_path = "/mnt/data/procurement_negotiation_history_120_records.csv"
df.to_csv(csv_path, index=False)

summary = {
    "rows": len(df),
    "vendors": int(df["vendor_name"].nunique()),
    "categories": int(df["product_category"].nunique()),
    "strategies": int(df["strategy_used"].nunique()),
    "outcomes": df["outcome"].value_counts().to_dict(),
}
summary
