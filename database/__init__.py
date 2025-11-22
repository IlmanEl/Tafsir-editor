"""Database module for Tafsir Editor."""

from .connection import get_supabase_client, test_connection
from .schema import create_tables, drop_tables

__all__ = [
    "get_supabase_client",
    "test_connection",
    "create_tables",
    "drop_tables",
]
