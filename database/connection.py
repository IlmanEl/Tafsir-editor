"""
Supabase connection module.
Uses Service Role Key for full admin access.
"""

from typing import Optional
from supabase import create_client, Client
from config import config


# Global client instance
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client instance.
    Uses Service Role Key for admin privileges.

    Returns:
        Client: Supabase client instance
    """
    global _supabase_client

    if _supabase_client is None:
        if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env"
            )

        _supabase_client = create_client(
            config.SUPABASE_URL,
            config.SUPABASE_SERVICE_ROLE_KEY
        )

    return _supabase_client


def test_connection() -> bool:
    """
    Test connection to Supabase.
    Performs a simple query to verify connectivity.

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        client = get_supabase_client()

        # Try to query a system table or perform a health check
        # Using RPC to call a simple function or just checking the client
        print(f"🔗 Connecting to Supabase: {config.SUPABASE_URL}")

        # Test by trying to list tables (this will work with service role key)
        # We'll try a simple select that should work even on empty db
        response = client.table("formatting_rules").select("*").limit(1).execute()

        print("✅ Connection successful!")
        print(f"   Response status: OK")
        return True

    except Exception as e:
        error_msg = str(e)
        if "relation" in error_msg and "does not exist" in error_msg:
            # Table doesn't exist yet, but connection works!
            print("✅ Connection successful!")
            print("   ⚠️  Tables not created yet (run schema setup)")
            return True
        else:
            print(f"❌ Connection failed: {e}")
            return False


def reset_client():
    """Reset the client instance (useful for testing)."""
    global _supabase_client
    _supabase_client = None
