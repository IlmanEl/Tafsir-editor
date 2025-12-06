from typing import Optional
from supabase import create_client, Client
from config import config


_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
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
    try:
        client = get_supabase_client()
        print(f"🔗 Connecting to Supabase: {config.SUPABASE_URL}")
        response = client.table("formatting_rules").select("*").limit(1).execute()
        print("✅ Connection successful!")
        print(f"   Response status: OK")
        return True

    except Exception as e:
        error_msg = str(e)
        if "relation" in error_msg and "does not exist" in error_msg:
            print("✅ Connection successful!")
            print("   ⚠️  Tables not created yet (run schema setup)")
            return True
        else:
            print(f"❌ Connection failed: {e}")
            return False


def reset_client():
    global _supabase_client
    _supabase_client = None
