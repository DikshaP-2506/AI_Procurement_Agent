#!/usr/bin/env python3
"""
Populate Supabase with test data for Procurement Optimization Layer testing
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv

# Load environment variables from the backend folder where the real .env lives
BACKEND_ENV_PATH = Path(__file__).resolve().parent / "backend" / ".env"
load_dotenv(dotenv_path=BACKEND_ENV_PATH)

try:
    from supabase import create_client, Client
except ImportError:
    print("ERROR: supabase-py not installed. Run: pip install supabase")
    sys.exit(1)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print(f"ERROR: Missing SUPABASE_URL or SUPABASE_KEY in {BACKEND_ENV_PATH}")
    sys.exit(1)

# Use service role key for inserts (bypasses RLS)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY)

def create_vendors() -> Dict[str, str]:
    """Create vendors using the current vendor table schema."""
    print("\n" + "="*60)
    print("Creating test vendors")
    print("="*60)

    vendors = [
        {
            "vendor_name": "Dell Technologies",
        },
        {
            "vendor_name": "Microsoft",
        },
        {
            "vendor_name": "Apple Inc",
        },
        {
            "vendor_name": "Cisco Systems",
        },
    ]

    vendor_map: Dict[str, str] = {}

    for vendor in vendors:
        try:
            # Check if vendor already exists to prevent duplicate entries
            existing = supabase.table("vendors").select("id").eq("vendor_name", vendor["vendor_name"]).execute().data
            if existing:
                vendor_map[vendor["vendor_name"]] = existing[0]["id"]
                print(f"[OK] Vendor already exists: {vendor['vendor_name']} (ID: {existing[0]['id']})")
                continue

            response = supabase.table("vendors").insert(vendor).execute()
            created = response.data[0]
            vendor_map[vendor["vendor_name"]] = created["id"]
            print(f"[OK] Created vendor: {vendor['vendor_name']} (ID: {created['id']})")
        except Exception as e:
            print(f"[ERROR] Error creating vendor {vendor['vendor_name']}: {e}")

    return vendor_map


def create_contracts(vendor_map: Dict[str, str]):
    """Create test contracts"""
    print("\n" + "="*60)
    print("Creating test contracts")
    print("="*60)
    today = datetime.now().date()

    contracts = [
        {
            "vendor_id": vendor_map.get("Dell Technologies"),
            "contract_name": "IT Hardware Supply 2024",
            "start_date": str(today.replace(year=2024, month=1, day=1)),
            "end_date": str(today.replace(year=2025, month=12, day=31)),
            "renewal_date": str(today.replace(year=2025, month=12, day=1)),
            "auto_renewal": True,
            "notice_period_days": 30,
        },
        {
            "vendor_id": vendor_map.get("Microsoft"),
            "contract_name": "Software Licenses 2024",
            "start_date": str(today.replace(year=2024, month=1, day=1)),
            "end_date": str(today.replace(year=2026, month=6, day=30)),
            "renewal_date": str(today.replace(year=2026, month=5, day=15)),
            "auto_renewal": True,
            "notice_period_days": 45,
        },
        {
            "vendor_id": vendor_map.get("Apple Inc"),
            "contract_name": "Mac Devices Supply",
            "start_date": str(today.replace(year=2023, month=6, day=1)),
            "end_date": str(today.replace(year=2025, month=6, day=1)),
            "renewal_date": str(today.replace(year=2025, month=5, day=1)),
            "auto_renewal": False,
            "notice_period_days": 60,
        },
        {
            "vendor_id": vendor_map.get("Cisco Systems"),
            "contract_name": "Network Equipment",
            "start_date": str(today.replace(year=2024, month=1, day=1)),
            "end_date": str(today.replace(year=2025, month=12, day=31)),
            "renewal_date": str(today.replace(year=2025, month=11, day=15)),
            "auto_renewal": True,
            "notice_period_days": 30,
        }
    ]

    for contract in contracts:
        if not contract["vendor_id"]:
            print(f"[ERROR] Skipping contract {contract['contract_name']} - vendor not found")
            continue

        try:
            supabase.table("contracts").insert(contract).execute()
            print(f"[OK] Created contract: {contract['contract_name']}")
        except Exception as e:
            print(f"[ERROR] Error creating contract {contract['contract_name']}: {e}")

def create_procurements(vendor_map: Dict[str, str]):
    """Create procurement records using the current procurements schema."""
    print("\n" + "="*60)
    print("Creating test procurements")
    print("="*60)

    procurements = [
        {"department": "IT", "category": "Hardware", "status": "active"},
        {"department": "Operations", "category": "Hardware", "status": "active"},
        {"department": "IT", "category": "Software", "status": "active"},
        {"department": "HR", "category": "Software", "status": "active"},
        {"department": "Finance", "category": "Software", "status": "active"},
        {"department": "IT", "category": "Devices", "status": "active"},
        {"department": "Network", "category": "Networking", "status": "active"},
    ]

    count = 0
    for procurement in procurements:
        payload = {
            "title": f"{procurement['category']} Procurement - {procurement['department']}",
            "department": procurement["department"],
            "category": procurement["category"],
            "status": procurement["status"],
        }

        try:
            supabase.table("procurements").insert(payload).execute()
            count += 1
            print(f"[OK] Created procurement: {procurement['department']} / {procurement['category']}")
        except Exception as e:
            print(f"[ERROR] Error creating procurement for {procurement['department']} / {procurement['category']}: {e}")

    print(f"\n[OK] Total procurements created: {count}")

def create_historical_negotiations(vendor_map: Dict[str, str]):
    """Create test historical negotiation records for each vendor."""
    print("\n" + "="*60)
    print("Creating historical negotiations")
    print("="*60)

    negotiations = [
        {
            "vendor_id": vendor_map.get("Dell Technologies"),
            "vendor_name": "Dell Technologies",
            "negotiation_date": "2024-05-15",
            "discount_requested": 15.0,
            "discount_received": 10.0,
            "successful_tactics": ["Bulk Purchase", "Competitive Bidding"],
            "failed_tactics": ["Early Payment Incentive"],
            "outcome": "success",
            "notes": "Secured 10% discount on latitude laptops through volume consolidation.",
            "product_category": "Hardware",
            "initial_quote_value": 150000.0,
            "final_negotiated_value": 135000.0,
            "strategy_used": "Bulk Purchase",
            "negotiation_rounds": 3,
            "success_score": 85.0
        },
        {
            "vendor_id": vendor_map.get("Microsoft"),
            "vendor_name": "Microsoft",
            "negotiation_date": "2024-06-10",
            "discount_requested": 12.0,
            "discount_received": 8.0,
            "successful_tactics": ["Multi-Year Contract"],
            "failed_tactics": ["Competitive Bidding"],
            "outcome": "success",
            "notes": "Negotiated enterprise license discount by signing a 3-year term commitment.",
            "product_category": "Software",
            "initial_quote_value": 85000.0,
            "final_negotiated_value": 78200.0,
            "strategy_used": "Multi-Year Contract",
            "negotiation_rounds": 2,
            "success_score": 80.0
        },
        {
            "vendor_id": vendor_map.get("Apple Inc"),
            "vendor_name": "Apple Inc",
            "negotiation_date": "2024-04-20",
            "discount_requested": 10.0,
            "discount_received": 3.0,
            "successful_tactics": ["Early Payment Incentive"],
            "failed_tactics": ["Bulk Purchase"],
            "outcome": "partial",
            "notes": "Apple held firm on pricing. Secured a minor discount via 10-day early payment incentive.",
            "product_category": "Devices",
            "initial_quote_value": 60000.0,
            "final_negotiated_value": 58200.0,
            "strategy_used": "Early Payment Incentive",
            "negotiation_rounds": 2,
            "success_score": 50.0
        },
        {
            "vendor_id": vendor_map.get("Cisco Systems"),
            "vendor_name": "Cisco Systems",
            "negotiation_date": "2024-07-05",
            "discount_requested": 15.0,
            "discount_received": 9.5,
            "successful_tactics": ["Competitive Bidding", "Volume Commitment"],
            "failed_tactics": ["Long-Term Contract"],
            "outcome": "success",
            "notes": "Acquired discounts on routing equipment by leveraging bids from Juniper.",
            "product_category": "Networking",
            "initial_quote_value": 110000.0,
            "final_negotiated_value": 99550.0,
            "strategy_used": "Competitive Bidding",
            "negotiation_rounds": 3,
            "success_score": 82.0
        }
    ]

    for neg in negotiations:
        if not neg["vendor_id"]:
            print(f"[ERROR] Skipping negotiation for {neg['vendor_name']} - vendor not found")
            continue

        try:
            # Check if negotiation record already exists to prevent duplicate entries
            existing = supabase.table("negotiation_history").select("id").eq("vendor_id", neg["vendor_id"]).eq("negotiation_date", neg["negotiation_date"]).execute().data
            if existing:
                print(f"[OK] Negotiation already exists for {neg['vendor_name']}")
                continue

            supabase.table("negotiation_history").insert(neg).execute()
            print(f"[OK] Created historical negotiation for: {neg['vendor_name']}")
        except Exception as e:
            print(f"[ERROR] Error creating negotiation for {neg['vendor_name']}: {e}")

def main():
    print("\n" + "█"*60)
    print("SUPABASE TEST DATA POPULATION SCRIPT")
    print("█"*60)
    print(f"\nSUPABASE_URL: {SUPABASE_URL}")

    # Test connection
    try:
        response = supabase.table("vendors").select("count", count="exact").execute()
        print(f"[OK] Connected to Supabase")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Supabase: {e}")
        print("\nMake sure your .env file has:")
        print("  SUPABASE_URL=your_url")
        print("  SUPABASE_KEY=your_key")
        print("  SUPABASE_SERVICE_ROLE_KEY=your_service_role_key")
        sys.exit(1)

    # Populate in the current schema order: vendors -> contracts -> procurements -> historical negotiations
    vendor_map = create_vendors()
    create_contracts(vendor_map)
    create_procurements(vendor_map)
    create_historical_negotiations(vendor_map)

    print("\n" + "="*60)
    print("[OK] TEST DATA POPULATION COMPLETE!")
    print("="*60)
    print("\nNow run: python test_endpoints.py")
    print("You should see data in the responses instead of empty arrays.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
