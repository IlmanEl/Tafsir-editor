import psycopg2
from psycopg2 import sql
from config import config


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

SEED_SQL = """
-- Default formatting rule for Tafsir
INSERT INTO formatting_rules (name, description, font_name_arabic, font_name_cyrillic)
VALUES (
    'tafsir_default',
    'Default formatting for Tafsir documents',
    'Traditional Arabic',
    'Times New Roman'
) ON CONFLICT (name) DO NOTHING;

-- Золотой стандарт транслитерации (инструкция заказчика)
INSERT INTO transliteration_rules (name, category, cyrillic_pattern, arabic_pattern, priority, notes)
VALUES
    ('alif', 'vowels', 'а', 'ا', 100, 'Базовая гласная'),
    ('ba', 'consonants', 'б', 'ب', 100, 'Звук б'),
    ('ta', 'consonants', 'т', 'ت', 100, 'Обычная т'),
    ('tha', 'consonants', 'с̱', 'ث', 100, 'Межзубная с (с чертой снизу)'),
    ('jim', 'consonants', 'дж', 'ج', 110, 'Звук дж'),
    ('ha_soft', 'consonants', 'х', 'ح', 100, 'Русская х (ха с точкой)'),
    ('kha', 'consonants', 'х', 'خ', 90, 'Хa'),
    ('dal', 'consonants', 'д', 'د', 100, 'Звук д'),
    ('zal', 'consonants', 'з̱', 'ذ', 100, 'Межзубная з (з с чертой снизу)'),
    ('ra', 'consonants', 'р', 'ر', 100, 'Звук р'),
    ('zay', 'consonants', 'з', 'ز', 100, 'Звук з'),
    ('sin', 'consonants', 'с', 'س', 90, 'Обычная с'),
    ('shin', 'consonants', 'ш', 'ش', 100, 'Звук ш'),
    ('sad', 'consonants', 'с', 'ص', 100, 'Эмфатическая твердая с'),
    ('dad', 'consonants', 'д', 'ض', 100, 'Эмфатическая д'),
    ('ta_hard', 'consonants', 'т', 'ط', 100, 'Эмфатическая т'),
    ('za', 'consonants', 'з', 'ظ', 100, 'Эмфатическая з'),
    ('ain', 'consonants', 'ʻ', 'ع', 100, 'Перевернутый апостроф (айн)'),
    ('ghain', 'consonants', 'г', 'غ', 100, 'Звук г (гайн)'),
    ('fa', 'consonants', 'ф', 'ف', 100, 'Звук ф'),
    ('qaf', 'consonants', 'к̣', 'ق', 100, 'Кяф с точкой'),
    ('kaf', 'consonants', 'к', 'ك', 90, 'Обычная к'),
    ('lam', 'consonants', 'л', 'ل', 100, 'Звук л'),
    ('mim', 'consonants', 'м', 'م', 100, 'Звук м'),
    ('nun', 'consonants', 'н', 'ن', 100, 'Звук н'),
    ('ha_hard', 'special', 'h', 'ه', 200, 'Латинская h - КРИТИЧНО для имени Аллаh!'),
    ('waw', 'consonants', 'в', 'و', 100, 'Звук в'),
    ('ya', 'consonants', 'й', 'ي', 100, 'Звук й'),
    ('hamza', 'special', '''', 'ء', 150, 'Апостроф (хамза)')
ON CONFLICT DO NOTHING;
"""

DROP_SQL = """
DROP TABLE IF EXISTS document_history CASCADE;
DROP TABLE IF EXISTS transliteration_rules CASCADE;
DROP TABLE IF EXISTS formatting_rules CASCADE;
"""


def get_db_connection():
    if not config.DATABASE_URL:
        raise ValueError("DATABASE_URL is not set in .env file")

    return psycopg2.connect(config.DATABASE_URL)


def create_tables(seed_data: bool = True) -> bool:
    conn = None
    try:
        print("Connecting to PostgreSQL database...")
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Creating tables...")
        cursor.execute(SCHEMA_SQL)
        conn.commit()
        print("   Tables created successfully")

        if seed_data:
            print("Inserting initial data...")
            cursor.execute(SEED_SQL)
            conn.commit()
            print("   Initial data inserted")

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
    return SCHEMA_SQL + "\n" + SEED_SQL


def test_db_connection() -> bool:
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
