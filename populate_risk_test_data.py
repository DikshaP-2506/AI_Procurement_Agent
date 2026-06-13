#!/usr/bin/env python3
"""Seed the existing vendor_risk_analysis table with mock risk snapshots.

This is intended for demos and local validation once Supabase is connected.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
BACKEND_ENV = ROOT_DIR / "backend" / ".env"
load_dotenv(BACKEND_ENV)

from supabase import create_client


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")


def main() -> None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise SystemExit("Missing SUPABASE_URL or SUPABASE key in backend/.env")

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    vendors = client.table("vendors").select("id,vendor_name").execute().data or []

    if not vendors:
        print("No vendors found. Run populate_test_data.py first.")
        return

    seeded = 0
    for vendor in vendors[:5]:
        payload = {
            "vendor_id": vendor["id"],
            "market_risk_score": 72,
            "financial_risk_score": 12,
            "supply_chain_risk_score": 8,
            "legal_risk_score": 5,
            "overall_risk_score": 61,
            "risk_level": "medium",
            "alerts": [
                {
                    "alert_type": "market_watch",
                    "severity": "medium",
                    "message": "Sample market risk alert for validation.",
                    "source": "seed_script",
                }
            ],
            "source_links": [
                {
                    "source": "seed_script",
                    "label": "market_watch",
                    "message": "Sample market risk alert for validation.",
                }
            ]
        }
        client.table("vendor_risk_analysis").insert(payload).execute()
        print(f"Seeded risk snapshot for {vendor.get('vendor_name')}")
        seeded += 1

    print(f"Done. Seeded {seeded} risk snapshots.")


if __name__ == "__main__":
    main()
