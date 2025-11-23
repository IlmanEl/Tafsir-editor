#!/usr/bin/env python3
"""
Tafsir Editor - Main Entry Point

A Python application for editing Word documents containing
Quran Tafsir with mixed Russian-Arabic text.

Features:
- Smart block classification (AYAH, TRANSLATION, COMMENTARY)
- Automatic database setup
- AI-ready text processing (protects Quranic verses)

Usage:
    python main.py                      # Auto-setup database and run demo
    python main.py --classify <file>    # Classify document blocks
    python main.py --process <file>     # Process and log to database
    python main.py --test-connection    # Test database connections
    python main.py --setup-db           # Create/update database tables
"""

import sys
import argparse
from pathlib import Path

from config import config
from database import (
    get_supabase_client,
    test_connection,
    create_tables,
    drop_tables,
    check_tables_exist,
    test_db_connection,
)
from document_processor import (
    TafsirDocumentProcessor,
    create_sample_document,
    BlockType,
)


def print_banner():
    """Print application banner."""
    banner = """
======================================================
     TAFSIR EDITOR
     --------------
     Smart Document Parser for Quran Tafsir
     Block Classification + AI-Ready Processing
======================================================
"""
    print(banner)


def test_all_connections() -> bool:
    """Test both PostgreSQL and Supabase API connections."""
    print("\n" + "="*50)
    print("DATABASE CONNECTION TEST")
    print("="*50 + "\n")

    if not config.validate():
        print("\nPlease configure your .env file first!")
        print("Copy .env.example to .env and fill in your credentials.")
        return False

    print("\n[1/2] Testing PostgreSQL connection (for DDL)...")
    pg_ok = test_db_connection()

    print("\n[2/2] Testing Supabase API connection...")
    api_ok = test_connection()

    print("\n" + "-"*50)
    if pg_ok and api_ok:
        print("All connections successful!")
        return True
    else:
        print("Some connections failed. Check your .env settings.")
        return False


def setup_database() -> bool:
    """Automatically create database tables."""
    print("\n" + "="*50)
    print("DATABASE SETUP (AUTO)")
    print("="*50 + "\n")

    print("Checking existing tables...")
    tables = check_tables_exist()
    all_exist = all(tables.values())

    if all_exist:
        print("All tables already exist:")
        for table, exists in tables.items():
            print(f"   [OK] {table}")
        return True

    print("\nCreating tables automatically...")
    return create_tables(seed_data=True)


def drop_database():
    """Drop all tables (with confirmation)."""
    print("\n" + "="*50)
    print("DROP DATABASE TABLES")
    print("="*50 + "\n")

    print("WARNING: This will delete ALL data in the following tables:")
    print("   - formatting_rules")
    print("   - document_history")
    print("   - transliteration_rules")
    print()

    confirm = input("Type 'YES' to confirm: ")
    if confirm == "YES":
        return drop_tables()
    else:
        print("Cancelled.")
        return False


def classify_document(file_path: str):
    """
    Classify document blocks and show detailed analysis.
    This is the main function for checking block detection accuracy.
    """
    print("\n" + "="*70)
    print("SMART DOCUMENT CLASSIFICATION")
    print("="*70 + "\n")

    processor = TafsirDocumentProcessor()

    if not processor.load(file_path):
        return False

    # Run classification
    print("\nClassifying blocks...")
    processor.classify_document()

    # Print detailed classification
    processor.print_classification(limit=50)

    # Show AI processing summary
    ai_blocks = processor.get_ai_processable_blocks()
    ayah_blocks = processor.get_blocks_by_type(BlockType.AYAH)

    print("\n" + "="*70)
    print("AI PROCESSING SUMMARY")
    print("="*70)
    print(f"""
  PROTECTED (will NOT be modified by AI):
    - {len(ayah_blocks)} Quranic verses (AYAH blocks)

  READY FOR AI PROCESSING:
    - {len(ai_blocks)} blocks (TRANSLATION + COMMENTARY)
    - {sum(b.word_count for b in ai_blocks)} words total

  Next step: Add OpenAI API key and run AI processing on COMMENTARY blocks.
""")

    return True


def process_document(file_path: str):
    """Process a Word document with classification and database logging."""
    print("\n" + "="*50)
    print("DOCUMENT PROCESSING")
    print("="*50 + "\n")

    processor = TafsirDocumentProcessor()

    if not processor.load(file_path):
        return False

    # Classify and display
    processor.classify_document()
    processor.print_classification(limit=20)

    # Log to database
    try:
        client = get_supabase_client()
        stats = processor.get_stats()

        client.table("document_history").insert({
            "document_name": Path(file_path).name,
            "document_path": str(file_path),
            "action": "classified",
            "description": f"Smart classification: {stats.ayah_blocks} ayahs, {stats.commentary_blocks} commentary blocks",
            "changes_json": {
                "total_blocks": stats.total_blocks,
                "ayah_blocks": stats.ayah_blocks,
                "translation_blocks": stats.translation_blocks,
                "commentary_blocks": stats.commentary_blocks,
                "ai_processable_blocks": stats.ai_processable_blocks,
                "ai_processable_words": stats.ai_processable_words
            },
            "paragraphs_affected": stats.total_blocks,
            "characters_changed": stats.total_characters
        }).execute()

        print("[OK] Classification logged to database")
    except Exception as e:
        print(f"[WARN] Could not log to database: {e}")

    return True


def run_demo():
    """Run a full demonstration with sample document."""
    print("\n" + "="*50)
    print("RUNNING DEMO")
    print("="*50 + "\n")

    # Create sample document
    print("Creating sample Tafsir document...")
    sample_path = create_sample_document()

    # Classify it
    classify_document(sample_path)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Tafsir Editor - Smart Document Parser for Quran Tafsir"
    )
    parser.add_argument(
        "--classify",
        metavar="FILE",
        help="Classify document blocks (check AYAH vs COMMENTARY detection)"
    )
    parser.add_argument(
        "--process",
        metavar="FILE",
        help="Process document and log to database"
    )
    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="Test database connections"
    )
    parser.add_argument(
        "--setup-db",
        action="store_true",
        help="Create database tables"
    )
    parser.add_argument(
        "--drop-db",
        action="store_true",
        help="Drop all tables (WARNING: deletes data!)"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demonstration with sample document"
    )

    args = parser.parse_args()

    # Print banner
    print_banner()

    # Handle specific commands
    if args.test_connection:
        success = test_all_connections()
        sys.exit(0 if success else 1)

    if args.setup_db:
        if not config.validate():
            sys.exit(1)
        success = setup_database()
        sys.exit(0 if success else 1)

    if args.drop_db:
        if not config.validate():
            sys.exit(1)
        success = drop_database()
        sys.exit(0 if success else 1)

    if args.classify:
        if not Path(args.classify).exists():
            print(f"File not found: {args.classify}")
            sys.exit(1)
        classify_document(args.classify)
        return

    if args.process:
        if not Path(args.process).exists():
            print(f"File not found: {args.process}")
            sys.exit(1)
        process_document(args.process)
        return

    if args.demo:
        run_demo()
        return

    # ===========================================
    # DEFAULT: Full automatic setup
    # ===========================================
    print("Running automatic setup...\n")

    # Step 1: Validate configuration
    print("Step 1/4: Validating configuration...")
    if not config.validate():
        print("\nPlease create .env file with your credentials.")
        print("See .env.example for reference.")
        sys.exit(1)

    # Step 2: Test connections
    print("\nStep 2/4: Testing database connections...")
    if not test_all_connections():
        print("\nFix connection issues before continuing.")
        sys.exit(1)

    # Step 3: Setup database (auto-create tables)
    print("\nStep 3/4: Setting up database...")
    if not setup_database():
        print("\nDatabase setup failed.")
        sys.exit(1)

    # Step 4: Run demo with classification
    print("\nStep 4/4: Running demo with smart classification...")
    run_demo()

    print("\n" + "="*70)
    print("SETUP COMPLETE!")
    print("="*70)
    print("""
Your Tafsir Editor is ready!

Block Types Detected:
  [AYAH]       - Quranic verses (PROTECTED from AI)
  [TRANSLATE]  - Russian translations (can process with AI)
  [COMMENTARY] - Tafsir text (can process with AI)
  [HEADER]     - Section headers
  [REFERENCE]  - Citations and references

Commands:
  python main.py --classify FILE     # Check block classification
  python main.py --process FILE      # Process and log to DB
  python main.py --demo              # Run demo

Next steps:
  1. Place your .docx files in 'documents/' folder
  2. Run: python main.py --classify documents/your_file.docx
  3. Verify AYAH blocks are correctly detected
  4. Add OpenAI API key for AI processing (coming next)
""")


if __name__ == "__main__":
    main()



g