from fastapi import APIRouter, HTTPException
from ..supabase_client import supabase
from ..models.vendor import VendorCreate

router = APIRouter(
    prefix="/vendors",
    tags=["vendors"]
)

@router.post("/")
async def create_vendor(vendor: VendorCreate):
    """
    Create a new vendor in Supabase.
    """
    try:
        data = vendor.model_dump()
        # Convert UUID to string for JSON serialization
        data['procurement_id'] = str(data['procurement_id'])
        response = supabase.table("vendors").insert(data).execute()
        
        # supabase-py returns data in response.data
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to create vendor")
            
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{vendor_id}")
async def get_vendor(vendor_id: str):
    """
    Fetch a single vendor by ID.
    """
    try:
        response = supabase.table("vendors").select("*").eq("id", vendor_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Vendor not found")
            
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def list_vendors():
    """
    List all vendors.
    """
    try:
        response = supabase.table("vendors").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
