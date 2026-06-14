from supabase import create_client, Client
from .config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY

# Initialize the Supabase clients
# Use service role key if available to bypass Row Level Security (RLS) on server-side queries.
client_key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY
supabase: Client = create_client(SUPABASE_URL, client_key)

# Service role client for privileged server-side operations (inserts requiring bypassing RLS)
supabase_service: Client | None = None
if SUPABASE_SERVICE_ROLE_KEY:
	supabase_service = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
