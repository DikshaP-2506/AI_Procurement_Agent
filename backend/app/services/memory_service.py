from typing import Any, Dict, Optional
import time
from threading import Lock

# Simple in-memory thread-safe storage for observations and semantic context
_observations: Dict[str, Dict[str, Any]] = {}
_lock = Lock()

def write_observation(key: str, value: Any, agent: str) -> None:
    """
    Write an observation to the shared memory board.
    """
    with _lock:
        _observations[key] = {
            "value": value,
            "agent": agent,
            "timestamp": time.time()
        }

def read_observation(key: str) -> Optional[Dict[str, Any]]:
    """
    Read a specific observation from the shared memory board.
    """
    with _lock:
        return _observations.get(key)

def clear_observations() -> None:
    """
    Clear all observations from the shared memory board.
    """
    with _lock:
        _observations.clear()

def get_all_observations() -> Dict[str, Any]:
    """
    Get all observations currently stored on the memory board.
    """
    with _lock:
        return {k: v for k, v in _observations.items()}
