from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID

class VendorBase(BaseModel):
    vendor_name: str
    contact_person: str
    email: EmailStr
    phone: str
    country: str
    procurement_id: UUID

class VendorCreate(VendorBase):
    pass

class Vendor(VendorBase):
    id: str  # Usually UUID string from Supabase
    created_at: str

    class Config:
        from_attributes = True
