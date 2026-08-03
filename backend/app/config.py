import os
from pathlib import Path
from dotenv import load_dotenv

# Define the base directory (backend folder)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

class Config:
    """Application configuration management."""
    
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    # Support multiple GROQ keys for key-rotation: priority order
    # 1) GROQ_API_KEYS (comma-separated list)
    # 2) GROQ_API_KEY_1, GROQ_API_KEY_2, GROQ_API_KEY_3
    # 3) GROQ_API_KEY (legacy single key)
    _groq_list = os.getenv("GROQ_API_KEYS")
    if _groq_list:
        GROQ_API_KEYS = [k.strip() for k in _groq_list.split(",") if k.strip()]
    else:
        # collect numbered keys
        keys = []
        for i in (1, 2, 3):
            v = os.getenv(f"GROQ_API_KEY_{i}")
            if v:
                keys.append(v)
        single = os.getenv("GROQ_API_KEY")
        if single and not keys:
            keys = [single]
        GROQ_API_KEYS = keys
    # For backward compatibility expose first key as GROQ_API_KEY (or None)
    GROQ_API_KEY = GROQ_API_KEYS[0] if GROQ_API_KEYS else None

    @classmethod
    def validate(cls):
        """Validates that all required environment variables are set."""
        missing = []
        if not cls.SUPABASE_URL:
            missing.append("SUPABASE_URL")
        if not cls.SUPABASE_KEY:
            missing.append("SUPABASE_KEY")
        
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "Please check your .env file."
            )

# Validate config on import to catch errors early
Config.validate()

# Expose variables for easy access
SUPABASE_URL = Config.SUPABASE_URL
SUPABASE_KEY = Config.SUPABASE_KEY
SUPABASE_SERVICE_ROLE_KEY = Config.SUPABASE_SERVICE_ROLE_KEY
# GROQ_API_KEYS: list of keys (may be empty)
GROQ_API_KEYS = Config.GROQ_API_KEYS
# GROQ_API_KEY: first key for backward compatibility or None
GROQ_API_KEY = Config.GROQ_API_KEY
