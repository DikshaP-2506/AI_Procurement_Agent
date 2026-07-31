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
        
        # Check if a vendor with the same name already exists in this procurement project
        existing = supabase.table("vendors").select("id").eq("vendor_name", data["vendor_name"]).eq("procurement_id", data["procurement_id"]).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="A supplier with this name is already registered in this project.")
            
        response = supabase.table("vendors").insert(data).execute()
        
        # supabase-py returns data in response.data
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to create vendor")
            
        new_vendor = response.data[0]
        
        # Automatically create one default historical negotiation record referencing this vendor
        try:
            from datetime import datetime
            from ..supabase_client import supabase_service
            
            # Retrieve procurement category if possible to populate category field
            category = "Hardware"
            if data.get("procurement_id"):
                proc_resp = supabase.table("procurements").select("category").eq("id", data["procurement_id"]).execute()
                if proc_resp.data:
                    category = proc_resp.data[0].get("category", "Hardware")

            negotiation_rec = {
                "vendor_id": new_vendor["id"],
                "vendor_name": new_vendor["vendor_name"],
                "negotiation_date": datetime.now().date().isoformat(),
                "discount_requested": 10.0,
                "discount_received": 5.0,
                "successful_tactics": ["Volume Commitment"],
                "failed_tactics": ["Early Payment Incentive"],
                "outcome": "partial",
                "notes": "Baseline negotiation profile created automatically upon vendor registration.",
                "product_category": category,
                "initial_quote_value": 50000.0,
                "final_negotiated_value": 47500.0,
                "strategy_used": "Volume Commitment",
                "negotiation_rounds": 2,
                "success_score": 75
            }
            
            client = supabase_service or supabase
            client.table("negotiation_history").insert(negotiation_rec).execute()
        except Exception as neg_err:
            # Log negotiation creation error but do not fail the main vendor creation request
            print(f"Warning: Failed to create default negotiation record: {neg_err}")

        # Automatically run initial risk analysis and persist it to vendor_risk_analysis table
        try:
            from ..services.risk_service import analyze_vendor_risk
            await analyze_vendor_risk(new_vendor["id"], persist=True)
            print(f"Automatically ran initial risk analysis for vendor {new_vendor['vendor_name']}")
        except Exception as risk_err:
            print(f"Warning: Failed to run initial risk analysis: {risk_err}")
            
        return new_vendor
    except HTTPException:
        raise
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
async def list_vendors(procurement_id: str = None):
    """
    List all vendors, optionally filtered by procurement_id.
    """
    try:
        query = supabase.table("vendors").select("*, procurements(title)")
        if procurement_id:
            query = query.eq("procurement_id", procurement_id)
        response = query.execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
