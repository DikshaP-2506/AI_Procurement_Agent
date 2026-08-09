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
    Audit Layer - Expose Audit Logs API with diverse, detailed agent activity.
    """
    local_logs = get_local_audit_logs()
    try:
        client = supabase_service or supabase
        response = await asyncio.wait_for(
            asyncio.to_thread(lambda: client.table("audit_logs").select("*").order("created_at", desc=True).limit(60).execute()),
            timeout=1.0
        )
        db_logs = response.data or []
        
        # Combine local memory logs and database logs
        all_logs = list(local_logs)
        seen_keys = set(f"{l.get('agent_name')}_{l.get('action_type')}_{l.get('created_at')}" for l in local_logs)
        
        for log in db_logs:
            key = f"{log.get('agent_name')}_{log.get('action_type')}_{log.get('created_at')}"
            if key not in seen_keys:
                all_logs.append(log)
                seen_keys.add(key)
        
        # Sort combined logs by timestamp descending (newest first)
        def parse_time(item):
            return str(item.get("created_at") or "")
        
        all_logs.sort(key=parse_time, reverse=True)
        
        # Filter boilerplate duplicates and balance agent representation in timeline
        filtered = []
        last_reasoning = None
        agent_counts = {}
        
        for log in all_logs:
            if log.get("agent_name") == "Subscription Renewal Catcher":
                log["agent_name"] = "Renewal Intelligence"
            reasoning = str(log.get("reasoning") or "")
            agent = str(log.get("agent_name") or "")
            
            # Filter out old static boilerplate strings
            if (
                "Combined historical procurement performance" in reasoning
                or "issued directive to initiate immediate renegotiation before auto-renewal deadline" in reasoning
                or (reasoning.startswith("Scanned active contract renewal windows") and "Dell Technologies" in reasoning)
            ):
                continue
                
            # Avoid duplicate reasoning text
            if reasoning == last_reasoning:
                continue
            
            cnt = agent_counts.get(agent, 0)
            if cnt >= 4 and len(filtered) > 10:
                continue
                
            agent_counts[agent] = cnt + 1
            last_reasoning = reasoning
            filtered.append(log)
            
        return {"logs": filtered[:30]}
    except Exception as e:
        logger.warning(f"Unable to fetch db audit logs (using local memory logs): {e}")
        return {"logs": local_logs}


