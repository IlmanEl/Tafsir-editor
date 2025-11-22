#!/usr/bin/env python3
"""
Tafsir Editor - Main Entry Point

A Python application for editing Word documents containing
Quran Tafsir with mixed Russian-Arabic text.

Usage:
    python main.py                      # Auto-setup database and run demo
    python main.py --test-connection    # Test database connections
    python main.py --setup-db           # Create/update database tables
    python main.py --drop-db            # Drop all tables (WARNING!)
    python main.py --process <file>     # Process a specific document
    python main.py --demo               # Run demo only
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
from document_processor import TafsirDocumentProcessor, create_sample_document


def print_banner():
    """Print application banner."""
    banner = """
======================================================
     TAFSIR EDITOR
     --------------
     Word Document Editor for Quran Tafsir
     Supports Russian (Cyrillic) and Arabic text
======================================================
"""
    print(banner)


def test_all_connections() -> bool:
    """Test both PostgreSQL and Supabase API connections."""
    print("\n" + "="*50)
    print("DATABASE CONNECTION TEST")
    print("="*50 + "\n")

    # Validate config first
    if not config.validate():
        print("\nPlease configure your .env file first!")
        print("Copy .env.example to .env and fill in your credentials.")
        return False

    # Test direct PostgreSQL connection
    print("\n[1/2] Testing PostgreSQL connection (for DDL)...")
    pg_ok = test_db_connection()

    # Test Supabase API connection
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
    """
    Automatically create database tables.
    Uses direct PostgreSQL connection via psycopg2.
    """
    print("\n" + "="*50)
    print("DATABASE SETUP (AUTO)")
    print("="*50 + "\n")

    # Check existing tables
    print("Checking existing tables...")
    tables = check_tables_exist()
    all_exist = all(tables.values())

    if all_exist:
        print("All tables already exist:")
        for table, exists in tables.items():
            print(f"   [OK] {table}")
        return True

    # Create missing tables
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


def process_document(file_path: str):
    """Process a Word document."""
    print("\n" + "="*50)
    print("DOCUMENT PROCESSING")
    print("="*50 + "\n")

    processor = TafsirDocumentProcessor()

    if processor.load(file_path):
        processor.print_paragraphs(limit=30)

        # Log to database
        try:
            client = get_supabase_client()
            stats = processor.get_stats()

            client.table("document_history").insert({
                "document_name": Path(file_path).name,
                "document_path": str(file_path),
                "action": "analyzed",
                "description": f"Document analyzed: {stats.total_paragraphs} paragraphs",
                "changes_json": {
                    "total_paragraphs": stats.total_paragraphs,
                    "arabic_paragraphs": stats.arabic_paragraphs,
                    "cyrillic_paragraphs": stats.cyrillic_paragraphs,
                    "mixed_paragraphs": stats.mixed_paragraphs
                },
                "paragraphs_affected": stats.total_paragraphs,
                "characters_changed": stats.total_characters
            }).execute()

            print("[OK] Analysis logged to database")
        except Exception as e:
            print(f"[WARN] Could not log to database: {e}")


def run_demo():
    """Run a full demonstration."""
    print("\n" + "="*50)
    print("RUNNING DEMO")
    print("="*50 + "\n")

    # Create sample document
    print("Creating sample document...")
    sample_path = create_sample_document()

    # Process it
    process_document(sample_path)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Tafsir Editor - Word Document Editor for Quran Tafsir"
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
        "--process",
        metavar="FILE",
        help="Process a specific .docx file"
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

    # Step 4: Run demo
    print("\nStep 4/4: Running demo...")
    run_demo()

    print("\n" + "="*50)
    print("SETUP COMPLETE!")
    print("="*50)
    print("""
Your database is ready. Tables created:
   - formatting_rules (font settings, paragraph styles)
   - document_history (change log)
   - transliteration_rules (cyrillic-arabic mapping)

Next steps:
   1. Place your .docx files in the 'documents' folder
   2. Process them: python main.py --process documents/your_file.docx

Commands:
   python main.py                    # Auto-setup + demo
   python main.py --test-connection  # Test connections
   python main.py --setup-db         # Create tables
   python main.py --process FILE     # Process document
   python main.py --demo             # Run demo
""")


if __name__ == "__main__":
    main()
