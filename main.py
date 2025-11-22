#!/usr/bin/env python3
"""
Tafsir Editor - Main Entry Point

A Python application for editing Word documents containing
Quran Tafsir (تفسير) with mixed Russian-Arabic text.

Usage:
    python main.py                      # Run full setup and demo
    python main.py --test-connection    # Test Supabase connection only
    python main.py --schema             # Print SQL schema
    python main.py --process <file>     # Process a specific document
"""

import sys
import argparse
from pathlib import Path

from config import config
from database import get_supabase_client, test_connection, create_tables
from database.schema import get_schema_sql
from document_processor import TafsirDocumentProcessor, create_sample_document


def print_banner():
    """Print application banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🕌  TAFSIR EDITOR  📖                                       ║
║   ─────────────────────────────────────────                   ║
║   Word Document Editor for Quran Tafsir                       ║
║   Supports Russian (Cyrillic) and Arabic text                 ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def test_supabase_connection() -> bool:
    """Test and report Supabase connection status."""
    print("\n" + "="*50)
    print("🔌 SUPABASE CONNECTION TEST")
    print("="*50 + "\n")

    # Validate config first
    if not config.validate():
        print("\n⚠️  Please configure your .env file first!")
        print("   Copy .env.example to .env and fill in your credentials.")
        return False

    # Test connection
    return test_connection()


def setup_database() -> bool:
    """Check database tables."""
    print("\n" + "="*50)
    print("🗄️  DATABASE SETUP")
    print("="*50 + "\n")

    return create_tables()


def print_schema():
    """Print the SQL schema for manual execution."""
    print("\n" + "="*50)
    print("📋 SQL SCHEMA")
    print("="*50)
    print("\nCopy this SQL to Supabase Dashboard > SQL Editor:\n")
    print(get_schema_sql())


def process_document(file_path: str):
    """Process a Word document."""
    print("\n" + "="*50)
    print("📄 DOCUMENT PROCESSING")
    print("="*50 + "\n")

    processor = TafsirDocumentProcessor()

    if processor.load(file_path):
        processor.print_paragraphs(limit=30)

        # Log to database if connected
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

            print("✅ Analysis logged to database")
        except Exception as e:
            print(f"⚠️  Could not log to database: {e}")


def run_demo():
    """Run a full demonstration."""
    print("\n" + "="*50)
    print("🎯 RUNNING DEMO")
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
        help="Test Supabase connection only"
    )
    parser.add_argument(
        "--schema",
        action="store_true",
        help="Print SQL schema for database setup"
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
    if args.schema:
        print_schema()
        return

    if args.test_connection:
        success = test_supabase_connection()
        sys.exit(0 if success else 1)

    if args.process:
        if not Path(args.process).exists():
            print(f"❌ File not found: {args.process}")
            sys.exit(1)
        process_document(args.process)
        return

    if args.demo:
        run_demo()
        return

    # Default: Run full setup
    print("Running initial setup...\n")

    # Step 1: Test connection
    print("Step 1/3: Testing Supabase connection...")
    if not test_supabase_connection():
        print("\n⚠️  Fix connection issues before continuing.")
        print("   Run: python main.py --schema")
        print("   to get the SQL schema for manual setup.")
        sys.exit(1)

    # Step 2: Check database
    print("\nStep 2/3: Checking database tables...")
    tables_ok = setup_database()

    if not tables_ok:
        print("\n📋 Database tables need to be created.")
        print("   Run: python main.py --schema")
        print("   Copy the SQL to Supabase Dashboard > SQL Editor > Run")

    # Step 3: Demo
    print("\nStep 3/3: Running demo...")
    run_demo()

    print("\n" + "="*50)
    print("✅ SETUP COMPLETE")
    print("="*50)
    print("""
Next steps:
1. Create .env file with your Supabase credentials (if not done)
2. Run SQL schema in Supabase Dashboard (if tables missing)
3. Process your documents:
   python main.py --process path/to/your/tafsir.docx

Commands:
   python main.py                    # Full setup
   python main.py --test-connection  # Test database
   python main.py --schema           # Show SQL schema
   python main.py --process FILE     # Process document
   python main.py --demo             # Run demo
""")


if __name__ == "__main__":
    main()
