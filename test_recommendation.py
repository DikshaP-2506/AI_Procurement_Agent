#!/usr/bin/env python3
"""
Test script for the Weighted Scoring, Ranking, Trade-Off Simulator, and Explainability Engine
"""

import requests
import json
import sys

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
BACKEND_ENV_PATH = Path(__file__).resolve().parent / "backend" / ".env"
load_dotenv(dotenv_path=BACKEND_ENV_PATH)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Fetch an active procurement
proc_resp = supabase.table("procurements").select("id").eq("status", "active").limit(1).execute()
if proc_resp.data:
    PROCUREMENT_ID = proc_resp.data[0]["id"]
else:
    PROCUREMENT_ID = "8ea2d01d-2137-4e83-8875-eb6a28d6e0c6" # Fallback

BASE_URL = "http://localhost:8000"

def test_recommendation_endpoint():
    print("\n" + "="*60)
    print("Testing Recommendation Engine - POST /recommendation")
    print("="*60)
    
    payload = {
        "procurement_id": PROCUREMENT_ID,
        "weights": {
            "cost": 40.0,
            "risk": 30.0,
            "support": 15.0,
            "delivery": 15.0
        },
        "qualitative_adjustments": {}
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/recommendation/",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"✓ Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Successfully fetched rankings!")
            print(f"✓ Summary: {data.get('comparison_summary')}")
            
            recs = data.get("recommendations", [])
            print(f"✓ Found {len(recs)} active vendor recommendations:")
            for r in recs:
                print(f"   Rank #{r.get('rank')}: {r.get('vendor_name')} (Score: {r.get('final_score')})")
                print(f"     Explanation: {r.get('explanation')}")
                
            assert len(recs) > 0, "No recommendations returned."
            assert recs[0]["rank"] == 1, "Ranks not ordered properly."
            return recs[0] # Return top ranked vendor
        else:
            print(f"✗ Failed response: {response.text}")
            return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def test_apply_endpoint(selected_vendor):
    print("\n" + "="*60)
    print("Testing Apply Recommendation - POST /recommendation/apply")
    print("="*60)
    
    if not selected_vendor:
        print("✗ Skipped: No vendor selected from previous step.")
        return False
        
    payload = {
        "procurement_id": PROCUREMENT_ID,
        "selected_vendor_id": selected_vendor["vendor_id"],
        "weights": {
            "cost": 40.0,
            "risk": 30.0,
            "support": 15.0,
            "delivery": 15.0
        },
        "reasoning": f"Selecting {selected_vendor['vendor_name']} based on top score {selected_vendor['final_score']} in trade-off simulation."
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/recommendation/apply",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"✓ Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Decision applied successfully!")
            print(f"  - Message: {data.get('message')}")
            print(f"  - Selected Vendor ID: {data.get('selected_vendor_id')}")
            print(f"  - Audit Log ID: {data.get('audit_log_id')}")
            
            assert data.get("status") == "success", "Expected success status."
            assert data.get("selected_vendor_id") == selected_vendor["vendor_id"], "Selected vendor mismatch."
            return True
        else:
            print(f"✗ Failed response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    print("Starting decision engine API validation...")
    
    # 1. Test rankings & explainability
    top_vendor = test_recommendation_endpoint()
    
    # 2. Test locking in the choice (apply decision)
    success = test_apply_endpoint(top_vendor)
    
    if top_vendor and success:
        print("\n" + "="*60)
        print("🎉 DECISION ENGINE INTEGRATION TESTS PASSED SUCCESSFULLY!")
        print("="*60)
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("✗ DECISION ENGINE INTEGRATION TESTS FAILED.")
        print("="*60)
        sys.exit(1)

if __name__ == "__main__":
    main()
