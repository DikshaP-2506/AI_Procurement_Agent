#!/usr/bin/env python3
"""
Test script for Procurement Optimization Layer
Populates Supabase with test data and tests all endpoints
"""

import requests
import json
from datetime import datetime, timedelta
import sys

# Configuration
BASE_URL = "http://localhost:8000"
SUPABASE_URL = "https://your-supabase-url.supabase.co"  # Update with your URL
SUPABASE_KEY = "your-supabase-anon-key"  # Update with your key
SUPABASE_SERVICE_ROLE = "your-service-role-key"  # Update with your key

def test_health_check():
    """Test if backend is running"""
    print("\n" + "="*60)
    print("Testing Health Check")
    print("="*60)
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Response: {json.dumps(response.json(), indent=2)}")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_renewal_analysis():
    """Test renewal analysis endpoint"""
    print("\n" + "="*60)
    print("Testing Renewal Catcher - GET /optimization/renewal-analysis")
    print("="*60)
    try:
        response = requests.get(f"{BASE_URL}/optimization/renewal-analysis")
        print(f"✓ Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Response: {json.dumps(data, indent=2)}")
            print(f"\n  Summary:")
            print(f"    - Total Contracts: {data.get('total_contracts', 0)}")
            print(f"    - High Risk: {data.get('high_risk_count', 0)}")
            print(f"    - Medium Risk: {data.get('medium_risk_count', 0)}")
            print(f"    - Low Risk: {data.get('low_risk_count', 0)}")
        else:
            print(f"✗ Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_crossdeal_analysis():
    """Test cross-deal analysis endpoint"""
    print("\n" + "="*60)
    print("Testing Cross Deal Negotiator - GET /optimization/crossdeal-analysis")
    print("="*60)
    try:
        response = requests.get(f"{BASE_URL}/optimization/crossdeal-analysis")
        print(f"✓ Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Response: {json.dumps(data, indent=2)}")
            print(f"\n  Summary:")
            print(f"    - Total Vendors Analyzed: {data.get('total_vendors_analyzed', 0)}")
            print(f"    - Vendors with Opportunities: {data.get('vendors_with_opportunities', 0)}")
            print(f"    - Total Estimated Savings: ${data.get('total_estimated_savings', 0):,.2f}")
        else:
            print(f"✗ Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_strategic_analysis():
    """Test strategic analysis endpoint"""
    print("\n" + "="*60)
    print("Testing Strategic Procurement Agent - POST /optimization/strategic-analysis")
    print("="*60)
    
    # Sample request payload
    payload = {
        "renewal_data": {
            "total_contracts": 4,
            "high_risk_count": 2,
            "medium_risk_count": 1,
            "low_risk_count": 1,
            "contracts": []
        },
        "crossdeal_data": {
            "total_vendors_analyzed": 4,
            "vendors_with_opportunities": 2,
            "total_estimated_savings": 280000,
            "opportunities": []
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/optimization/strategic-analysis",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"✓ Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Response: {json.dumps(data, indent=2)}")
            print(f"\n  Summary:")
            analysis = data.get('strategic_analysis', {})
            print(f"    - Priority: {analysis.get('priority', 'N/A')}")
            print(f"    - Estimated Savings: {analysis.get('estimated_savings', 'N/A')}")
            print(f"    - Strategic Actions: {len(analysis.get('strategic_actions', []))}")
        else:
            print(f"✗ Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_summary():
    """Test summary endpoint"""
    print("\n" + "="*60)
    print("Testing Summary - GET /optimization/summary")
    print("="*60)
    try:
        response = requests.get(f"{BASE_URL}/optimization/summary")
        print(f"✓ Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Response: {json.dumps(data, indent=2)}")
            print(f"\n  Summary:")
            print(f"    - Renewal Alerts: {data.get('total_renewal_alerts', 0)}")
            print(f"    - High Risk Count: {data.get('high_risk_count', 0)}")
            print(f"    - Bundle Opportunities: {data.get('total_bundle_opportunities', 0)}")
            print(f"    - Total Bundle Savings: ${data.get('total_bundle_savings', 0):,.2f}")
            print(f"    - Strategic Actions: {data.get('total_strategic_actions', 0)}")
        else:
            print(f"✗ Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("\n" + "█"*60)
    print("PROCUREMENT OPTIMIZATION LAYER - TEST SUITE")
    print("█"*60)
    
    results = {
        "Health Check": test_health_check(),
        "Renewal Analysis": test_renewal_analysis(),
        "Cross Deal Analysis": test_crossdeal_analysis(),
        "Strategic Analysis": test_strategic_analysis(),
        "Summary": test_summary(),
    }
    
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
