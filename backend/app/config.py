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
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

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
GROQ_API_KEY = Config.GROQ_API_KEY
