import asyncio
import unittest
from unittest.mock import MagicMock

from app.services import negotiation_service


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeTable:
    def __init__(self, rows):
        self.rows = rows
        self._filters = []

    def select(self, *args, **kwargs):
        return self

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def execute(self):
        if self._filters:
            column, value = self._filters[-1]
            return FakeResponse([row for row in self.rows if row.get(column) == value])
        return FakeResponse(self.rows)


class NegotiationServiceContextTests(unittest.TestCase):
    def test_build_procurement_context_uses_procurement_and_quote_data(self):
        procurement_row = {
            "id": "proc-1",
            "category": "Laptops",
            "title": "Q3 Laptop Renewal",
        }
        vendor_row = {
            "id": "vendor-1",
            "vendor_name": "Dell",
            "procurement_id": "proc-1",
        }
        quote_row = {
            "id": "quote-1",
            "vendor_id": "vendor-1",
            "price": 125000.0,
            "delivery_days": 14,
            "warranty_years": 3,
            "payment_terms": "Net 30",
            "support_level": "Premium",
            "compliance_score": 95,
            "extracted_json": {
                "full_ai_result": {
                    "extracted_data": {
                        "contract_name": "Enterprise Agreement",
                        "start_date": "2026-01-01",
                        "end_date": "2026-12-31",
                    }
                }
            },
        }

        fake_client = MagicMock()
        fake_client.table.side_effect = lambda name: {
            "procurements": FakeTable([procurement_row]),
            "vendors": FakeTable([vendor_row]),
            "vendor_quotes": FakeTable([quote_row]),
            "contracts": FakeTable([]),
            "negotiation_history": FakeTable([]),
        }[name]

        context = asyncio.run(
            negotiation_service.build_procurement_context("proc-1", client=fake_client)
        )

        self.assertEqual(context["procurement_id"], "proc-1")
        self.assertEqual(context["vendor_name"], "Dell")
        self.assertEqual(context["product_category"], "Laptops")
        self.assertEqual(context["quote_value"], 125000.0)
        self.assertEqual(context["delivery_days"], 14)
        self.assertEqual(context["warranty"], 3)
        self.assertEqual(context["payment_terms"], "Net 30")
        self.assertEqual(context["support_details"], "Premium")
        self.assertEqual(context["compliance"], 95)
        self.assertEqual(context["vendor_id"], "vendor-1")


if __name__ == "__main__":
    unittest.main()
