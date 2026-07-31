import asyncio
import datetime
from typing import Dict, Any, List
from ..supabase_client import supabase, supabase_service

# In-memory local audit log cache for 0ms response latency
_LOCAL_AUDIT_LOGS: List[Dict[str, Any]] = []


def get_local_audit_logs() -> List[Dict[str, Any]]:
    return list(reversed(_LOCAL_AUDIT_LOGS))


async def _background_supabase_insert(audit_record: dict):
    """Non-blocking background worker to write audit log to Supabase."""
    try:
        client = supabase_service if supabase_service else supabase
        await asyncio.wait_for(
            asyncio.to_thread(lambda: client.table('audit_logs').insert(audit_record).execute()),
            timeout=1.5
        )
    except Exception as e:
        pass


async def log_agent_execution(
    agent_name: str,
    action_type: str,
    input_payload: Dict[str, Any],
    output_payload: Dict[str, Any],
    reasoning: str
) -> bool:
    """
    Log an agent execution with 0ms blocking latency.
    Stores in local memory cache immediately and dispatches background insert to Supabase.
    """
    audit_record = {
        'agent_name': agent_name,
        'action_type': action_type,
        'input_payload': input_payload,
        'output_payload': output_payload,
        'reasoning': reasoning,
        'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    # Instantly record in local memory (0ms)
    _LOCAL_AUDIT_LOGS.append(audit_record)
    if len(_LOCAL_AUDIT_LOGS) > 100:
        _LOCAL_AUDIT_LOGS.pop(0)

    # Dispatch non-blocking background worker
    asyncio.create_task(_background_supabase_insert(audit_record))
    return True

