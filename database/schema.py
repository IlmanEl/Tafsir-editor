"""
Database schema definitions and setup.
Creates tables for Tafsir Editor using Supabase.

Note: Supabase Python client doesn't support DDL directly.
We provide SQL statements to execute via Supabase SQL Editor
or use PostgREST-compatible approaches.
"""

from typing import List, Dict, Any
from .connection import get_supabase_client


# SQL statements for creating tables
# Execute these in Supabase SQL Editor (Dashboard > SQL Editor)

SCHEMA_SQL = """
-- ============================================
-- TAFSIR EDITOR DATABASE SCHEMA
-- ============================================
-- Execute this SQL in Supabase Dashboard > SQL Editor

-- 1. Formatting Rules Table
-- Stores font settings, paragraph styles, etc.
CREATE TABLE IF NOT EXISTS formatting_rules (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,

    -- Font settings
    font_name_arabic VARCHAR(100) DEFAULT 'Traditional Arabic',
    font_name_cyrillic VARCHAR(100) DEFAULT 'Times New Roman',
    font_size_arabic INTEGER DEFAULT 14,
    font_size_cyrillic INTEGER DEFAULT 12,

    -- Paragraph settings
    line_spacing DECIMAL(3,2) DEFAULT 1.5,
    paragraph_spacing_before INTEGER DEFAULT 0,
    paragraph_spacing_after INTEGER DEFAULT 10,
    first_line_indent DECIMAL(5,2) DEFAULT 1.25,

    -- Alignment (left, right, center, justify)
    alignment_arabic VARCHAR(20) DEFAULT 'right',
    alignment_cyrillic VARCHAR(20) DEFAULT 'justify',

    -- Text direction
    rtl_arabic BOOLEAN DEFAULT TRUE,

    -- Style flags
    bold BOOLEAN DEFAULT FALSE,
    italic BOOLEAN DEFAULT FALSE,

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Document History Table
-- Logs all changes to documents
CREATE TABLE IF NOT EXISTS document_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

    -- Document info
    document_name VARCHAR(500) NOT NULL,
    document_path TEXT,

    -- Change info
    action VARCHAR(50) NOT NULL, -- 'created', 'modified', 'formatted', 'transliterated', 'exported'
    description TEXT,

    -- Change details (JSON for flexibility)
    changes_json JSONB,

    -- Statistics
    paragraphs_affected INTEGER DEFAULT 0,
    characters_changed INTEGER DEFAULT 0,

    -- Metadata
    user_name VARCHAR(255) DEFAULT 'local_user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Transliteration Rules Table
-- Rules for converting between Cyrillic and Arabic scripts
CREATE TABLE IF NOT EXISTS transliteration_rules (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

    -- Rule identification
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100), -- 'vowels', 'consonants', 'special', 'combinations'

    -- Conversion mapping
    cyrillic_pattern VARCHAR(50) NOT NULL,
    arabic_pattern VARCHAR(50) NOT NULL,

    -- Context rules (when to apply)
    context_before VARCHAR(100), -- regex pattern for preceding context
    context_after VARCHAR(100),  -- regex pattern for following context

    -- Priority (higher = applied first)
    priority INTEGER DEFAULT 100,

    -- Examples and notes
    example_cyrillic TEXT,
    example_arabic TEXT,
    notes TEXT,

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_document_history_document_name
ON document_history(document_name);

CREATE INDEX IF NOT EXISTS idx_document_history_created_at
ON document_history(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_transliteration_rules_category
ON transliteration_rules(category);

CREATE INDEX IF NOT EXISTS idx_transliteration_rules_priority
ON transliteration_rules(priority DESC);

-- ============================================
-- INITIAL DATA
-- ============================================

-- Default formatting rule for Tafsir
INSERT INTO formatting_rules (name, description, font_name_arabic, font_name_cyrillic)
VALUES (
    'tafsir_default',
    'Default formatting for Tafsir documents',
    'Traditional Arabic',
    'Times New Roman'
) ON CONFLICT (name) DO NOTHING;

-- Sample transliteration rules
INSERT INTO transliteration_rules (name, category, cyrillic_pattern, arabic_pattern, priority)
VALUES
    ('alif', 'vowels', 'а', 'ا', 100),
    ('ba', 'consonants', 'б', 'ب', 100),
    ('ta', 'consonants', 'т', 'ت', 100),
    ('tha', 'consonants', 'с̱', 'ث', 100),
    ('jim', 'consonants', 'дж', 'ج', 110),
    ('ha', 'consonants', 'х̣', 'ح', 100),
    ('kha', 'consonants', 'х', 'خ', 90),
    ('dal', 'consonants', 'д', 'د', 100),
    ('ra', 'consonants', 'р', 'ر', 100),
    ('sin', 'consonants', 'с', 'س', 90),
    ('shin', 'consonants', 'ш', 'ش', 100),
    ('ain', 'consonants', 'ъ', 'ع', 100),
    ('ghain', 'consonants', 'г̣', 'غ', 100),
    ('fa', 'consonants', 'ф', 'ف', 100),
    ('qaf', 'consonants', 'к̣', 'ق', 100),
    ('kaf', 'consonants', 'к', 'ك', 90),
    ('lam', 'consonants', 'л', 'ل', 100),
    ('mim', 'consonants', 'м', 'م', 100),
    ('nun', 'consonants', 'н', 'ن', 100),
    ('waw', 'consonants', 'в', 'و', 100),
    ('ya', 'consonants', 'й', 'ي', 100)
ON CONFLICT DO NOTHING;

-- ============================================
-- Enable Row Level Security (optional)
-- Since we use service role key, RLS is bypassed
-- ============================================

-- ALTER TABLE formatting_rules ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE document_history ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE transliteration_rules ENABLE ROW LEVEL SECURITY;

SELECT 'Schema created successfully!' as status;
"""


def get_schema_sql() -> str:
    """Return the SQL schema for manual execution."""
    return SCHEMA_SQL


def create_tables() -> bool:
    """
    Attempt to verify tables exist by querying them.

    Note: Direct DDL execution requires Supabase SQL Editor.
    This function checks if tables are accessible.

    Returns:
        bool: True if tables are accessible
    """
    client = get_supabase_client()
    tables = ["formatting_rules", "document_history", "transliteration_rules"]
    results = {}

    print("🔍 Checking database tables...")

    for table in tables:
        try:
            response = client.table(table).select("id").limit(1).execute()
            results[table] = True
            print(f"   ✅ {table}: exists")
        except Exception as e:
            if "does not exist" in str(e):
                results[table] = False
                print(f"   ❌ {table}: not found")
            else:
                results[table] = False
                print(f"   ❌ {table}: error - {e}")

    all_exist = all(results.values())

    if not all_exist:
        print("\n📋 To create tables, run this SQL in Supabase Dashboard:")
        print("   Dashboard > SQL Editor > New Query > Paste schema > Run")
        print("\n   Or use: python -c \"from database.schema import get_schema_sql; print(get_schema_sql())\"")

    return all_exist


def drop_tables() -> str:
    """Return SQL to drop all tables (for reset)."""
    return """
    -- WARNING: This will delete all data!
    DROP TABLE IF EXISTS document_history CASCADE;
    DROP TABLE IF EXISTS transliteration_rules CASCADE;
    DROP TABLE IF EXISTS formatting_rules CASCADE;
    """


def insert_test_data() -> bool:
    """Insert sample data for testing."""
    client = get_supabase_client()

    try:
        # Test insert into document_history
        client.table("document_history").insert({
            "document_name": "test_document.docx",
            "action": "created",
            "description": "Test entry"
        }).execute()

        print("✅ Test data inserted successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to insert test data: {e}")
        return False
