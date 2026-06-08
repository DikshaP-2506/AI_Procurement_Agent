from supabase import create_client, Client
from .config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY

# Initialize the Supabase clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Service role client for privileged server-side operations (inserts requiring bypassing RLS)
supabase_service: Client | None = None
if SUPABASE_SERVICE_ROLE_KEY:
	supabase_service = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
