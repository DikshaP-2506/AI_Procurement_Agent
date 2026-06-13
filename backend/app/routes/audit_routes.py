from fastapi import APIRouter, HTTPException
from ..supabase_client import supabase, supabase_service

router = APIRouter(
    prefix="/audit",
    tags=["audit"]
)

@router.get("/logs")
async def get_audit_logs():
    """
    Audit Layer - Expose Audit Logs API
    
    Retrieves execution logs for optimization and decision agents from Supabase.
    """
    try:
        client = supabase_service or supabase
        response = client.table("audit_logs").select("*").order("created_at", desc=True).execute()
        return {"logs": response.data or []}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch audit logs: {str(e)}"
        )
