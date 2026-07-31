import asyncio
import logging
from fastapi import APIRouter
from ..supabase_client import supabase, supabase_service
from ..services.audit_service import get_local_audit_logs

logger = logging.getLogger("uvicorn.error")

router = APIRouter(
    prefix="/audit",
    tags=["audit"]
)

@router.get("/logs")
async def get_audit_logs():
    """
    Audit Layer - Expose Audit Logs API with ultra-fast latency.
    """
    local_logs = get_local_audit_logs()
    try:
        client = supabase_service or supabase
        response = await asyncio.wait_for(
            asyncio.to_thread(lambda: client.table("audit_logs").select("*").order("created_at", desc=True).limit(50).execute()),
            timeout=1.0
        )
        db_logs = response.data or []
        # Merge local and db logs without duplicates
        combined = list(local_logs)
        seen_ids = set(f"{l.get('agent_name')}_{l.get('created_at')}" for l in local_logs)
        for log in db_logs:
            key = f"{log.get('agent_name')}_{log.get('created_at')}"
            if key not in seen_ids:
                combined.append(log)
                seen_ids.add(key)
        return {"logs": combined}
    except Exception as e:
        logger.warning(f"Unable to fetch db audit logs (using local memory logs): {e}")
        return {"logs": local_logs}


