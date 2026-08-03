import threading
from typing import List, Optional
from ..config import GROQ_API_KEYS


class _GroqKeyManager:
    def __init__(self, keys: Optional[List[str]]):
        self.keys = keys or []
        self.lock = threading.Lock()
        self.idx = 0

    def get_key(self) -> Optional[str]:
        if not self.keys:
            return None
        with self.lock:
            k = self.keys[self.idx]
            self.idx = (self.idx + 1) % len(self.keys)
            return k


_manager = _GroqKeyManager(GROQ_API_KEYS)


def get_next_groq_key() -> Optional[str]:
    return _manager.get_key()


__all__ = ["get_next_groq_key"]
