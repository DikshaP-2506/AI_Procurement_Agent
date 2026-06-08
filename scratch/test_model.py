from pydantic import ValidationError
from backend.app.models.vendor import VendorCreate
from uuid import uuid4

test_data = {
    "procurement_id": str(uuid4()),
    "vendor_name": "Dell",
    "contact_person": "John",
    "email": "john@dell.com",
    "phone": "1234567890",
    "country": "India"
}

try:
    vendor = VendorCreate(**test_data)
    print("Validation successful")
    print(vendor.model_dump())
except ValidationError as e:
    print(f"Validation failed: {e}")
except Exception as e:
    print(f"Error: {e}")
