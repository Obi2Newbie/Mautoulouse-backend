from supabase import create_client, Client
from .config import settings


def get_supabase() -> Client:
    """Anon client — respects RLS (used for most endpoints)."""
    return create_client(settings.supabase_url, settings.supabase_key)


def get_supabase_admin() -> Client:
    """Service-role client — bypasses RLS (admin-only operations)."""
    return create_client(settings.supabase_url, settings.supabase_service_key)
