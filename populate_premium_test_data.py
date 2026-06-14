#!/usr/bin/env python3
"""
Populate Supabase with premium, high-value test data for Procurement Optimization Layer
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

# Load environment variables
BACKEND_ENV_PATH = Path(__file__).resolve().parent / "backend" / ".env"
load_dotenv(dotenv_path=BACKEND_ENV_PATH)

try:
    from supabase import create_client, Client
except ImportError:
    print("ERROR: supabase-py not installed. Run: pip install supabase")
    sys.exit(1)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print(f"ERROR: Missing SUPABASE_URL or keys in {BACKEND_ENV_PATH}")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def clean_database():
    """Clear existing test data to start fresh in correct dependency order."""
    print("Cleaning database...")
    try:
        # Delete negotiation history first
        try:
            supabase.table("negotiation_history").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        except Exception as e:
            print(f"Note: Could not clean negotiation_history: {e}")
        # Delete vendor quotes first
        supabase.table("vendor_quotes").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        # Delete contracts
        supabase.table("contracts").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        # Delete vendor risk analysis
        try:
            supabase.table("vendor_risk_analysis").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        except Exception as e:
            print(f"Note: Could not clean vendor_risk_analysis: {e}")
        # Delete vendors
        supabase.table("vendors").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        # Delete procurements
        supabase.table("procurements").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        # Delete audit logs
        supabase.table("audit_logs").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print("[OK] Database cleaned successfully!")
    except Exception as e:
        print(f"Warning during cleaning: {e}")

def create_historical_negotiations(vendor_records, today):
    """Seed exactly 1 distinct historical negotiation related to each premium vendor."""
    print("\nCreating historical negotiations...")
    
    # Predefined templates matching our premium vendor list
    templates = {
        "Microsoft Corporation": {
            "negotiation_date": str(today - timedelta(days=90)),
            "discount_requested": 15.0,
            "discount_received": 12.0,
            "successful_tactics": ["Multi-Year Contract", "License Consolidation"],
            "failed_tactics": ["Early Payment Incentive"],
            "outcome": "success",
            "notes": "Negotiated premium enterprise software licenses. Volume bundling across IT, Finance, and HR departments secured a 12% discount.",
            "product_category": "Software",
            "initial_quote_value": 3000000.0,
            "final_negotiated_value": 2640000.0,
            "strategy_used": "License Consolidation",
            "negotiation_rounds": 3,
            "success_score": 90.0
        },
        "Dell Technologies": {
            "negotiation_date": str(today - timedelta(days=120)),
            "discount_requested": 20.0,
            "discount_received": 15.0,
            "successful_tactics": ["Bulk Purchase", "Vendor Consolidation"],
            "failed_tactics": ["Early Payment Incentive"],
            "outcome": "success",
            "notes": "Bulk hardware procurement for Latitude laptops. Pushing competitive bids from Lenovo forced a 15% discount on the hardware units.",
            "product_category": "Hardware",
            "initial_quote_value": 250000.0,
            "final_negotiated_value": 2125000.0,
            "strategy_used": "Bulk Purchase",
            "negotiation_rounds": 4,
            "success_score": 92.0
        },
        "Adobe Inc": {
            "negotiation_date": str(today - timedelta(days=60)),
            "discount_requested": 10.0,
            "discount_received": 5.0,
            "successful_tactics": ["Volume Commitment"],
            "failed_tactics": ["Competitive Bidding"],
            "outcome": "partial",
            "notes": "Creative Cloud license negotiation for Marketing. Adobe held firm on subscription pricing but allowed a 5% discount on additional seats.",
            "product_category": "Software",
            "initial_quote_value": 150000.0,
            "final_negotiated_value": 142500.0,
            "strategy_used": "Volume Commitment",
            "negotiation_rounds": 2,
            "success_score": 68.0
        },
        "Cisco Systems Inc": {
            "negotiation_date": str(today - timedelta(days=150)),
            "discount_requested": 15.0,
            "discount_received": 10.0,
            "successful_tactics": ["Competitive Bidding"],
            "failed_tactics": ["Long-Term Contract"],
            "outcome": "success",
            "notes": "Enterprise networking switches. Secured 10% discount by citing alternative pricing from Arista and committing to immediate PO release.",
            "product_category": "Networking",
            "initial_quote_value": 500000.0,
            "final_negotiated_value": 450000.0,
            "strategy_used": "Competitive Bidding",
            "negotiation_rounds": 3,
            "success_score": 84.0
        },
        "Apple Inc": {
            "negotiation_date": str(today - timedelta(days=200)),
            "discount_requested": 8.0,
            "discount_received": 2.5,
            "successful_tactics": ["Early Payment Incentive"],
            "failed_tactics": ["Bulk Purchase"],
            "outcome": "partial",
            "notes": "MacBook supply agreement. Apple does not offer volume discounts; secured 2.5% reduction via Net 10 payment terms option.",
            "product_category": "Hardware",
            "initial_quote_value": 400000.0,
            "final_negotiated_value": 390000.0,
            "strategy_used": "Early Payment Incentive",
            "negotiation_rounds": 2,
            "success_score": 45.0
        },
        "Amazon Web Services": {
            "negotiation_date": str(today - timedelta(days=30)),
            "discount_requested": 15.0,
            "discount_received": 10.0,
            "successful_tactics": ["Volume Commitment", "Reserved Capacity"],
            "failed_tactics": ["Multi-Supplier Leverage"],
            "outcome": "success",
            "notes": "AWS Cloud Hosting negotiation. Committed to a 1-year Savings Plan to obtain 10% computed discount.",
            "product_category": "Cloud Services",
            "initial_quote_value": 1200000.0,
            "final_negotiated_value": 1080000.0,
            "strategy_used": "Reserved Capacity",
            "negotiation_rounds": 2,
            "success_score": 85.0
        }
    }
    
    inserted_vendors = set()
    for rec in vendor_records:
        vendor_name = rec["vendor_name"]
        
        # Prevent inserting duplicate negotiations if the vendor exists multiple times (e.g. cross-deal)
        if vendor_name in inserted_vendors:
            continue
            
        tpl = templates.get(vendor_name)
        if tpl:
            payload = {
                "vendor_id": rec["id"],
                "vendor_name": vendor_name,
                **tpl
            }
            try:
                supabase.table("negotiation_history").insert(payload).execute()
                print(f"[OK] Seeded negotiation for vendor: {vendor_name}")
                inserted_vendors.add(vendor_name)
            except Exception as e:
                print(f"[ERROR] Failed to seed negotiation for {vendor_name}: {e}")

def main():
    print("============================================================")
    print("POPULATING PREMIUM PROCUREMENTS & CONTRACTS DATA")
    print("============================================================")
    
    clean_database()
    today = datetime.now().date()
    
    # 1. Create Procurements
    print("\nCreating procurements...")
    procurements_to_create = [
        {"title": "Software Licenses - IT", "department": "IT", "category": "Software", "status": "active"},
        {"title": "Software Licenses - Finance", "department": "Finance", "category": "Software", "status": "active"},
        {"title": "Software Licenses - HR", "department": "HR", "category": "Software", "status": "active"},
        {"title": "Hardware Procurement - IT", "department": "IT", "category": "Hardware", "status": "active"},
        {"title": "Hardware Procurement - Operations", "department": "Operations", "category": "Hardware", "status": "active"},
        {"title": "Software Licenses - Marketing", "department": "Marketing", "category": "Software", "status": "active"},
        {"title": "Networking Lease - Networking", "department": "Networking", "category": "Networking", "status": "active"}
    ]
    
    procurement_map = {}
    for p in procurements_to_create:
        try:
            resp = supabase.table("procurements").insert(p).execute()
            if resp.data:
                created = resp.data[0]
                procurement_map[p["title"]] = created["id"]
                print(f"[OK] Created Procurement: {p['title']} ({created['id']})")
        except Exception as e:
            print(f"[ERROR] Failed to create procurement {p['title']}: {e}")
            
    # 2. Create Vendors (associated with Procurements for cross-deal logic)
    print("\nCreating vendors...")
    vendors_to_create = [
        # Microsoft overlaps (IT, Finance, HR)
        {
            "procurement_id": procurement_map.get("Software Licenses - IT"),
            "vendor_name": "Microsoft Corporation",
            "contact_person": "Satya Nadella",
            "email": "satya.n@microsoft.com",
            "country": "USA"
        },
        {
            "procurement_id": procurement_map.get("Software Licenses - Finance"),
            "vendor_name": "Microsoft Corporation",
            "contact_person": "Finance Lead",
            "email": "finance@microsoft.com",
            "country": "USA"
        },
        {
            "procurement_id": procurement_map.get("Software Licenses - HR"),
            "vendor_name": "Microsoft Corporation",
            "contact_person": "HR Lead",
            "email": "hr@microsoft.com",
            "country": "USA"
        },
        # Dell overlaps (IT, Operations)
        {
            "procurement_id": procurement_map.get("Hardware Procurement - IT"),
            "vendor_name": "Dell Technologies",
            "contact_person": "Michael Dell",
            "email": "michael@dell.com",
            "country": "USA"
        },
        {
            "procurement_id": procurement_map.get("Hardware Procurement - Operations"),
            "vendor_name": "Dell Technologies",
            "contact_person": "Ops Dell",
            "email": "ops@dell.com",
            "country": "USA"
        },
        # Adobe (Marketing)
        {
            "procurement_id": procurement_map.get("Software Licenses - Marketing"),
            "vendor_name": "Adobe Inc",
            "contact_person": "Shantanu Narayen",
            "email": "shantanu@adobe.com",
            "country": "USA"
        },
        # Cisco (Networking)
        {
            "procurement_id": procurement_map.get("Networking Lease - Networking"),
            "vendor_name": "Cisco Systems Inc",
            "contact_person": "Chuck Robbins",
            "email": "chuck@cisco.com",
            "country": "USA"
        },
        # Additional vendors for contracts (without active procurements or just standalone)
        {
            "procurement_id": None,
            "vendor_name": "Apple Inc",
            "contact_person": "Tim Cook",
            "email": "tim@apple.com",
            "country": "USA"
        },
        {
            "procurement_id": None,
            "vendor_name": "Amazon Web Services",
            "contact_person": "Andy Jassy",
            "email": "andy@aws.com",
            "country": "USA"
        }
    ]
    
    vendor_records = []
    for v in vendors_to_create:
        try:
            resp = supabase.table("vendors").insert(v).execute()
            if resp.data:
                created = resp.data[0]
                vendor_records.append(created)
                print(f"[OK] Created Vendor: {v['vendor_name']} on Procurement {v['procurement_id']} ({created['id']})")
        except Exception as e:
            print(f"[ERROR] Failed to create vendor {v['vendor_name']}: {e}")
            
    # Find a specific vendor record by name & procurement_id
    def get_vendor_id(name: str, proc_title: str = None) -> str:
        for rec in vendor_records:
            if rec["vendor_name"] == name:
                if proc_title is None:
                    return rec["id"]
                p_id = procurement_map.get(proc_title)
                if rec["procurement_id"] == p_id:
                    return rec["id"]
        return None

    # 3. Create Vendor Quotes (specifying the price for each vendor)
    print("\nCreating vendor quotes...")
    quotes_to_create = [
        # Microsoft quotes
        {
            "vendor_id": get_vendor_id("Microsoft Corporation", "Software Licenses - IT"),
            "price": 6500000.0,
            "delivery_days": 10,
            "warranty_years": 3,
            "support_level": "24/7 Premium",
            "payment_terms": "Net 30",
            "compliance_score": 98.0
        },
        {
            "vendor_id": get_vendor_id("Microsoft Corporation", "Software Licenses - Finance"),
            "price": 4500000.0,
            "delivery_days": 12,
            "warranty_years": 3,
            "support_level": "24/7 Premium",
            "payment_terms": "Net 30",
            "compliance_score": 96.0
        },
        {
            "vendor_id": get_vendor_id("Microsoft Corporation", "Software Licenses - HR"),
            "price": 2500000.0,
            "delivery_days": 15,
            "warranty_years": 2,
            "support_level": "Business Standard",
            "payment_terms": "Net 45",
            "compliance_score": 95.0
        },
        # Dell quotes
        {
            "vendor_id": get_vendor_id("Dell Technologies", "Hardware Procurement - IT"),
            "price": 8000000.0,
            "delivery_days": 20,
            "warranty_years": 5,
            "support_level": "ProSupport Plus",
            "payment_terms": "Net 30",
            "compliance_score": 97.0
        },
        {
            "vendor_id": get_vendor_id("Dell Technologies", "Hardware Procurement - Operations"),
            "price": 5000000.0,
            "delivery_days": 25,
            "warranty_years": 3,
            "support_level": "ProSupport",
            "payment_terms": "Net 30",
            "compliance_score": 94.0
        },
        # Adobe quote
        {
            "vendor_id": get_vendor_id("Adobe Inc", "Software Licenses - Marketing"),
            "price": 2500000.0,
            "delivery_days": 5,
            "warranty_years": 1,
            "support_level": "Premium",
            "payment_terms": "Net 30",
            "compliance_score": 99.0
        },
        # Cisco quote
        {
            "vendor_id": get_vendor_id("Cisco Systems Inc", "Networking Lease - Networking"),
            "price": 7500000.0,
            "delivery_days": 30,
            "warranty_years": 3,
            "support_level": "SmartNet 24x7x4",
            "payment_terms": "Net 45",
            "compliance_score": 93.0
        }
    ]
    
    for q in quotes_to_create:
        if not q["vendor_id"]:
            continue
        try:
            supabase.table("vendor_quotes").insert(q).execute()
            print(f"[OK] Created Quote for Vendor {q['vendor_id']} (Price: {q['price']:,})")
        except Exception as e:
            print(f"[ERROR] Failed to create quote for vendor {q['vendor_id']}: {e}")

    # 4. Create Contracts (associated with the vendors for renewal alerts)
    print("\nCreating contracts...")
    contracts_to_create = [
        {
            "vendor_id": get_vendor_id("Apple Inc"),
            "contract_name": "MacBook Device Supply 2023",
            "start_date": str(today - timedelta(days=365)),
            "end_date": str(today - timedelta(days=15)),  # Expired (CRITICAL risk)
            "renewal_date": str(today - timedelta(days=45)),
            "auto_renewal": False,
            "notice_period_days": 30
        },
        {
            "vendor_id": get_vendor_id("Dell Technologies", "Hardware Procurement - IT"),
            "contract_name": "Enterprise Server Lease",
            "start_date": str(today - timedelta(days=300)),
            "end_date": str(today + timedelta(days=15)),  # NOTICE PERIOD ACTIVE (HIGH risk)
            "renewal_date": str(today + timedelta(days=15)),
            "auto_renewal": True,
            "notice_period_days": 30
        },
        {
            "vendor_id": get_vendor_id("Microsoft Corporation", "Software Licenses - IT"),
            "contract_name": "Office 365 Enterprise Subscription",
            "start_date": str(today - timedelta(days=180)),
            "end_date": str(today + timedelta(days=45)),  # Expiring in 45 days (MEDIUM risk)
            "renewal_date": str(today + timedelta(days=45)),
            "auto_renewal": False,
            "notice_period_days": 30
        },
        {
            "vendor_id": get_vendor_id("Amazon Web Services"),
            "contract_name": "Cloud Hosting Agreement",
            "start_date": str(today - timedelta(days=90)),
            "end_date": str(today + timedelta(days=270)),  # Expiring in 270 days (LOW risk)
            "renewal_date": str(today + timedelta(days=270)),
            "auto_renewal": True,
            "notice_period_days": 60
        },
        {
            "vendor_id": get_vendor_id("Adobe Inc", "Software Licenses - Marketing"),
            "contract_name": "Creative Cloud Licenses",
            "start_date": str(today - timedelta(days=320)),
            "end_date": str(today + timedelta(days=10)),  # Notice period active (HIGH risk)
            "renewal_date": str(today + timedelta(days=10)),
            "auto_renewal": True,
            "notice_period_days": 30
        }
    ]
    
    for c in contracts_to_create:
        if not c["vendor_id"]:
            print(f"[ERROR] Vendor not found for contract {c['contract_name']}")
            continue
        try:
            supabase.table("contracts").insert(c).execute()
            print(f"[OK] Created Contract: {c['contract_name']} for Vendor {c['vendor_id']}")
        except Exception as e:
            print(f"[ERROR] Failed to create contract {c['contract_name']}: {e}")

    # 5. Create Historical Negotiations
    create_historical_negotiations(vendor_records, today)
            
    print("\n============================================================")
    print("[OK] PREMIUM DATA POPULATION COMPLETE!")
    print("============================================================")

if __name__ == "__main__":
    main()
