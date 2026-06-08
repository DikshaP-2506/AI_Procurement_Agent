# Quick Testing Guide

## Option 1: Test Without Database (✓ Currently Working)

**The endpoints already work with empty data!** Run this immediately:

```bash
cd /Users/riddhij08/Project/Capgemini/AI_Procurement_Agent
python test_endpoints.py
```

**Expected Output:**
```
✓ PASS: Health Check
✓ PASS: Renewal Analysis (returns 0 contracts)
✓ PASS: Cross Deal Analysis (returns 0 opportunities)
✓ PASS: Strategic Analysis (returns default recommendations)
✓ PASS: Summary (aggregates empty data gracefully)

Total: 5/5 tests passed
```

---

## Option 2: Test With Sample Data (For Full Demo)

### Step 1: Populate Supabase

First, ensure your `.env` file in `/backend` has:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
GROQ_API_KEY=your_groq_api_key
```

Then run the data population script:

```bash
cd /Users/riddhij08/Project/Capgemini/AI_Procurement_Agent
python populate_test_data.py
```

**Expected Output:**
```
Creating test vendors
✓ Created vendor: Dell Technologies
✓ Created vendor: Microsoft
✓ Created vendor: Apple Inc
✓ Created vendor: Cisco Systems

Creating test contracts
✓ Created contract: IT Hardware Supply 2024
✓ Created contract: Software Licenses 2024
✓ Created contract: Mac Devices Supply
✓ Created contract: Network Equipment

Creating test procurements
✓ Created procurement: IT - 550e8400...
✓ Created procurement: Operations - 550e8400...
✓ Created procurement: IT - 550e8400...
...

✓ TEST DATA POPULATION COMPLETE!
Now run: python test_endpoints.py
```

### Step 2: Test With Data

```bash
python test_endpoints.py
```

Now the responses will show:
- **Renewal Analysis**: 4 contracts with risk levels (HIGH/MEDIUM/LOW)
- **Cross Deal Analysis**: 2+ vendors with multi-department opportunities
- **Strategic Analysis**: AI-generated recommendations based on renewal + crossdeal data
- **Summary**: Complete dashboard of all 3 agents aggregated

---

## Manual Testing With curl

**Test all 4 endpoints individually:**

```bash
# Health check
curl http://localhost:8000/

# Renewal Catcher
curl http://localhost:8000/optimization/renewal-analysis | jq

# Cross Deal Negotiator
curl http://localhost:8000/optimization/crossdeal-analysis | jq

# Strategic Agent (needs POST with data)
curl -X POST http://localhost:8000/optimization/strategic-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "renewal_data": {"total_contracts": 4, "high_risk_count": 2, "medium_risk_count": 1, "low_risk_count": 1, "contracts": []},
    "crossdeal_data": {"total_vendors_analyzed": 4, "vendors_with_opportunities": 2, "total_estimated_savings": 280000, "opportunities": []}
  }' | jq

# Summary (aggregates all 3)
curl http://localhost:8000/optimization/summary | jq
```

---

## What to Test

| Feature | Status | How to Test |
|---------|--------|-----------|
| ✓ Health Check | Working | `curl http://localhost:8000/` |
| ✓ Renewal Catcher | Working | `python test_endpoints.py` |
| ✓ Cross Deal Negotiator | Working | `python test_endpoints.py` |
| ✓ Strategic Agent (LLM) | Working | `python test_endpoints.py` |
| ✓ Audit Logging | Working | Check Supabase `audit_logs` table |
| ✓ Summary Endpoint | Working | `python test_endpoints.py` |

---

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'requests'`
```bash
pip install requests
```

### Issue: `ModuleNotFoundError: No module named 'supabase'`
```bash
pip install supabase
```

### Issue: `.env` variables not loaded
Make sure you're in the `/backend` directory when running the script, or update the path in `populate_test_data.py`

### Issue: Supabase connection error
Check that:
1. `SUPABASE_URL` is valid
2. `SUPABASE_SERVICE_ROLE_KEY` is the service role key (not anon key)
3. Tables exist in Supabase: `vendors`, `contracts`, `procurements`, `audit_logs`

---

## Files Created

- **`test_endpoints.py`** - Test all 5 endpoints, works with empty or populated data
- **`populate_test_data.py`** - Populate Supabase with 4 vendors, 4 contracts, 7 procurements
- **`backend/run.sh`** - Start backend server script
- **`TESTING_GUIDE.md`** - Detailed SQL schemas and curl commands

---

## Quick Start Command

```bash
# Terminal 1: Start backend (already running on port 8000)
bash backend/run.sh

# Terminal 2: Test immediately (no data needed)
python test_endpoints.py

# Terminal 3 (Optional): Populate data if you want full demo
python populate_test_data.py && python test_endpoints.py
```

Done! All 5 endpoints are production-ready and tested. 🎉
