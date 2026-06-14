from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..supabase_client import supabase

router = APIRouter(
    prefix="/procurements",
    tags=["procurements"]
)

class ProcurementCreate(BaseModel):
    title: str
    department: str
    category: str

@router.get("/")
async def list_procurements():
    """
    List all active procurement projects from Supabase.
    """
    try:
        # Since we use the service role key as the main client key, RLS will be bypassed.
        response = supabase.table("procurements").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def create_procurement(procurement: ProcurementCreate):
    """
    Create a new active procurement project in Supabase.
    """
    try:
        data = procurement.model_dump()
        data["status"] = "active"
        
        # Check if a procurement project with the same title already exists
        existing = supabase.table("procurements").select("id").eq("title", data["title"]).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="A procurement project with this title already exists.")
            
        response = supabase.table("procurements").insert(data).execute()
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to create procurement project")
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

