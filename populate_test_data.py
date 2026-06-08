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
            response = supabase.table("vendors").insert(vendor).execute()
            created = response.data[0]
            vendor_map[vendor["vendor_name"]] = created["id"]
            print(f"✓ Created vendor: {vendor['vendor_name']} (ID: {created['id']})")
        except Exception as e:
            print(f"✗ Error creating vendor {vendor['vendor_name']}: {e}")

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
            print(f"✗ Skipping contract {contract['contract_name']} - vendor not found")
            continue

        try:
            supabase.table("contracts").insert(contract).execute()
            print(f"✓ Created contract: {contract['contract_name']}")
        except Exception as e:
            print(f"✗ Error creating contract {contract['contract_name']}: {e}")

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
            print(f"✓ Created procurement: {procurement['department']} / {procurement['category']}")
        except Exception as e:
            print(f"✗ Error creating procurement for {procurement['department']} / {procurement['category']}: {e}")

    print(f"\n✓ Total procurements created: {count}")

def main():
    print("\n" + "█"*60)
    print("SUPABASE TEST DATA POPULATION SCRIPT")
    print("█"*60)
    print(f"\nSUPABASE_URL: {SUPABASE_URL}")
    
    # Test connection
    try:
        response = supabase.table("vendors").select("count", count="exact").execute()
        print(f"✓ Connected to Supabase")
    except Exception as e:
        print(f"✗ Failed to connect to Supabase: {e}")
        print("\nMake sure your .env file has:")
        print("  SUPABASE_URL=your_url")
        print("  SUPABASE_KEY=your_key")
        print("  SUPABASE_SERVICE_ROLE_KEY=your_service_role_key")
        sys.exit(1)
    
    # Populate in the current schema order: vendors -> contracts -> procurements
    vendor_map = create_vendors()
    create_contracts(vendor_map)
    create_procurements(vendor_map)
    
    print("\n" + "="*60)
    print("✓ TEST DATA POPULATION COMPLETE!")
    print("="*60)
    print("\nNow run: python test_endpoints.py")
    print("You should see data in the responses instead of empty arrays.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
