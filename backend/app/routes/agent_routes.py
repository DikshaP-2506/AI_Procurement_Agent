from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional
from ..agents.supervisor_agent import run_supervisor_agent

router = APIRouter(prefix="/agent", tags=["agent"])

class AgentRunRequest(BaseModel):
    instruction: str
    context: Optional[Dict[str, Any]] = None

class AgentRunResponse(BaseModel):
    status: str
    result: Any
    observations: Dict[str, Any]

@router.post("/run", response_model=AgentRunResponse)
async def run_agent_endpoint(request: AgentRunRequest):
    """
    Unified agent coordinator endpoint. Takes natural language requests
    and delegates them to the Supervisor Agent.
    """
    try:
        result = await run_supervisor_agent(request.instruction, request.context)
        from ..services.memory_service import get_all_observations
        return AgentRunResponse(
            status="success",
            result=result,
            observations=get_all_observations()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
