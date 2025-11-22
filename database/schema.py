"""
Database schema definitions and setup.
Creates tables for Tafsir Editor using direct PostgreSQL connection.

Uses psycopg2 for DDL operations (CREATE TABLE, etc.)
"""

import psycopg2
from psycopg2 import sql
from config import config


# SQL statements for creating tables
SCHEMA_SQL = """
-- ============================================
-- TAFSIR EDITOR DATABASE SCHEMA
-- ============================================

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
    action VARCHAR(50) NOT NULL,
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
    category VARCHAR(100),

    -- Conversion mapping
    cyrillic_pattern VARCHAR(50) NOT NULL,
    arabic_pattern VARCHAR(50) NOT NULL,

    -- Context rules (when to apply)
    context_before VARCHAR(100),
    context_after VARCHAR(100),

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
"""

# Initial data to seed the database
SEED_SQL = """
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
"""

DROP_SQL = """
DROP TABLE IF EXISTS document_history CASCADE;
DROP TABLE IF EXISTS transliteration_rules CASCADE;
DROP TABLE IF EXISTS formatting_rules CASCADE;
"""


def get_db_connection():
    """
    Create a direct PostgreSQL connection using DATABASE_URL.

    Returns:
        psycopg2 connection object
    """
    if not config.DATABASE_URL:
        raise ValueError("DATABASE_URL is not set in .env file")

    return psycopg2.connect(config.DATABASE_URL)


def create_tables(seed_data: bool = True) -> bool:
    """
    Create all database tables using direct PostgreSQL connection.

    Args:
        seed_data: Whether to insert initial data (default: True)

    Returns:
        bool: True if successful, False otherwise
    """
    conn = None
    try:
        print("Connecting to PostgreSQL database...")
        conn = get_db_connection()
        cursor = conn.cursor()

        # Execute schema creation
        print("Creating tables...")
        cursor.execute(SCHEMA_SQL)
        conn.commit()
        print("   Tables created successfully")

        # Insert seed data
        if seed_data:
            print("Inserting initial data...")
            cursor.execute(SEED_SQL)
            conn.commit()
            print("   Initial data inserted")

        # Verify tables exist
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('formatting_rules', 'document_history', 'transliteration_rules')
        """)
        tables = [row[0] for row in cursor.fetchall()]

        print("\nVerifying tables:")
        for table in ['formatting_rules', 'document_history', 'transliteration_rules']:
            if table in tables:
                print(f"   [OK] {table}")
            else:
                print(f"   [MISSING] {table}")

        cursor.close()
        print("\nDatabase setup completed successfully!")
        return True

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if conn:
            conn.close()


def drop_tables() -> bool:
    """
    Drop all tables (use with caution!).

    Returns:
        bool: True if successful
    """
    conn = None
    try:
        print("WARNING: Dropping all tables...")
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(DROP_SQL)
        conn.commit()

        cursor.close()
        print("All tables dropped successfully")
        return True

    except Exception as e:
        print(f"Error dropping tables: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def check_tables_exist() -> dict:
    """
    Check which tables exist in the database.

    Returns:
        dict: Table names mapped to existence status
    """
    conn = None
    tables_status = {
        'formatting_rules': False,
        'document_history': False,
        'transliteration_rules': False
    }

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('formatting_rules', 'document_history', 'transliteration_rules')
        """)

        existing = [row[0] for row in cursor.fetchall()]
        for table in existing:
            tables_status[table] = True

        cursor.close()

    except Exception as e:
        print(f"Error checking tables: {e}")
    finally:
        if conn:
            conn.close()

    return tables_status


def get_schema_sql() -> str:
    """Return the SQL schema for reference."""
    return SCHEMA_SQL + "\n" + SEED_SQL


def test_db_connection() -> bool:
    """
    Test the direct PostgreSQL connection.

    Returns:
        bool: True if connection successful
    """
    conn = None
    try:
        print(f"Testing connection to: {config.DATABASE_URL[:50]}...")
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"   Connected to: {version[:60]}...")

        cursor.close()
        return True

    except Exception as e:
        print(f"Connection failed: {e}")
        return False
    finally:
        if conn:
            conn.close()
