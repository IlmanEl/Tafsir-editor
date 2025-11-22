"""
Document Processor for Tafsir Word files.
Handles reading, parsing, and processing .docx files with mixed Russian-Arabic text.
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from config import config


@dataclass
class ParagraphInfo:
    """Information about a document paragraph."""
    index: int
    text: str
    style: Optional[str]
    has_arabic: bool
    has_cyrillic: bool
    is_mixed: bool
    word_count: int
    char_count: int


@dataclass
class DocumentStats:
    """Statistics about the document."""
    total_paragraphs: int
    total_words: int
    total_characters: int
    arabic_paragraphs: int
    cyrillic_paragraphs: int
    mixed_paragraphs: int
    empty_paragraphs: int


class TafsirDocumentProcessor:
    """
    Processor for Tafsir Word documents.
    Handles mixed Russian (Cyrillic) and Arabic text.
    """

    # Unicode ranges for script detection
    ARABIC_PATTERN = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
    CYRILLIC_PATTERN = re.compile(r'[\u0400-\u04FF\u0500-\u052F]')

    def __init__(self, file_path: Optional[str] = None):
        """
        Initialize the document processor.

        Args:
            file_path: Optional path to .docx file
        """
        self.file_path: Optional[Path] = Path(file_path) if file_path else None
        self.document: Optional[Document] = None
        self._stats: Optional[DocumentStats] = None

    def load(self, file_path: Optional[str] = None) -> bool:
        """
        Load a Word document.

        Args:
            file_path: Path to .docx file (uses init path if not provided)

        Returns:
            bool: True if loaded successfully
        """
        if file_path:
            self.file_path = Path(file_path)

        if not self.file_path:
            print("❌ No file path provided")
            return False

        if not self.file_path.exists():
            print(f"❌ File not found: {self.file_path}")
            return False

        if not self.file_path.suffix.lower() == '.docx':
            print(f"❌ Not a .docx file: {self.file_path}")
            return False

        try:
            self.document = Document(str(self.file_path))
            self._stats = None  # Reset stats cache
            print(f"✅ Document loaded: {self.file_path.name}")
            print(f"   Paragraphs: {len(self.document.paragraphs)}")
            return True
        except Exception as e:
            print(f"❌ Failed to load document: {e}")
            return False

    def has_arabic(self, text: str) -> bool:
        """Check if text contains Arabic characters."""
        return bool(self.ARABIC_PATTERN.search(text))

    def has_cyrillic(self, text: str) -> bool:
        """Check if text contains Cyrillic characters."""
        return bool(self.CYRILLIC_PATTERN.search(text))

    def analyze_paragraph(self, index: int, paragraph) -> ParagraphInfo:
        """
        Analyze a single paragraph.

        Args:
            index: Paragraph index
            paragraph: python-docx Paragraph object

        Returns:
            ParagraphInfo: Analysis results
        """
        text = paragraph.text
        has_ar = self.has_arabic(text)
        has_cyr = self.has_cyrillic(text)

        return ParagraphInfo(
            index=index,
            text=text,
            style=paragraph.style.name if paragraph.style else None,
            has_arabic=has_ar,
            has_cyrillic=has_cyr,
            is_mixed=has_ar and has_cyr,
            word_count=len(text.split()) if text else 0,
            char_count=len(text)
        )

    def iterate_paragraphs(self) -> Generator[ParagraphInfo, None, None]:
        """
        Iterate through all paragraphs with analysis.

        Yields:
            ParagraphInfo: Information about each paragraph
        """
        if not self.document:
            raise ValueError("No document loaded. Call load() first.")

        for i, para in enumerate(self.document.paragraphs):
            yield self.analyze_paragraph(i, para)

    def get_stats(self) -> DocumentStats:
        """
        Get document statistics.

        Returns:
            DocumentStats: Statistics about the document
        """
        if not self.document:
            raise ValueError("No document loaded. Call load() first.")

        if self._stats:
            return self._stats

        total_words = 0
        total_chars = 0
        arabic_count = 0
        cyrillic_count = 0
        mixed_count = 0
        empty_count = 0

        for para_info in self.iterate_paragraphs():
            total_words += para_info.word_count
            total_chars += para_info.char_count

            if not para_info.text.strip():
                empty_count += 1
            elif para_info.is_mixed:
                mixed_count += 1
            elif para_info.has_arabic:
                arabic_count += 1
            elif para_info.has_cyrillic:
                cyrillic_count += 1

        self._stats = DocumentStats(
            total_paragraphs=len(self.document.paragraphs),
            total_words=total_words,
            total_characters=total_chars,
            arabic_paragraphs=arabic_count,
            cyrillic_paragraphs=cyrillic_count,
            mixed_paragraphs=mixed_count,
            empty_paragraphs=empty_count
        )

        return self._stats

    def print_paragraphs(self, limit: Optional[int] = None, show_empty: bool = False):
        """
        Print all paragraphs to console.

        Args:
            limit: Maximum number of paragraphs to print (None = all)
            show_empty: Whether to show empty paragraphs
        """
        if not self.document:
            print("❌ No document loaded. Call load() first.")
            return

        print(f"\n{'='*60}")
        print(f"📄 Document: {self.file_path.name}")
        print(f"{'='*60}\n")

        count = 0
        for para_info in self.iterate_paragraphs():
            # Skip empty if not requested
            if not show_empty and not para_info.text.strip():
                continue

            # Check limit
            if limit and count >= limit:
                print(f"\n... (showing {limit} of {len(self.document.paragraphs)} paragraphs)")
                break

            # Determine script type indicator
            if para_info.is_mixed:
                script_indicator = "🔀 [RU+AR]"
            elif para_info.has_arabic:
                script_indicator = "🕌 [AR]"
            elif para_info.has_cyrillic:
                script_indicator = "🔤 [RU]"
            else:
                script_indicator = "📝 [OTHER]"

            # Print paragraph
            print(f"[{para_info.index:4d}] {script_indicator}")
            print(f"       {para_info.text[:200]}{'...' if len(para_info.text) > 200 else ''}")
            print()

            count += 1

        # Print stats
        stats = self.get_stats()
        print(f"\n{'='*60}")
        print("📊 DOCUMENT STATISTICS:")
        print(f"   Total paragraphs: {stats.total_paragraphs}")
        print(f"   Total words: {stats.total_words}")
        print(f"   Total characters: {stats.total_characters}")
        print(f"   Arabic paragraphs: {stats.arabic_paragraphs}")
        print(f"   Cyrillic paragraphs: {stats.cyrillic_paragraphs}")
        print(f"   Mixed paragraphs: {stats.mixed_paragraphs}")
        print(f"   Empty paragraphs: {stats.empty_paragraphs}")
        print(f"{'='*60}\n")

    def find_paragraphs_by_text(self, search_text: str, case_sensitive: bool = False) -> List[ParagraphInfo]:
        """
        Find paragraphs containing specific text.

        Args:
            search_text: Text to search for
            case_sensitive: Whether search is case-sensitive

        Returns:
            List of matching ParagraphInfo objects
        """
        if not self.document:
            return []

        results = []
        for para_info in self.iterate_paragraphs():
            text = para_info.text if case_sensitive else para_info.text.lower()
            search = search_text if case_sensitive else search_text.lower()

            if search in text:
                results.append(para_info)

        return results

    def get_arabic_paragraphs(self) -> List[ParagraphInfo]:
        """Get all paragraphs containing Arabic text."""
        return [p for p in self.iterate_paragraphs() if p.has_arabic]

    def get_cyrillic_paragraphs(self) -> List[ParagraphInfo]:
        """Get all paragraphs containing Cyrillic text."""
        return [p for p in self.iterate_paragraphs() if p.has_cyrillic]

    def get_mixed_paragraphs(self) -> List[ParagraphInfo]:
        """Get all paragraphs containing both Arabic and Cyrillic."""
        return [p for p in self.iterate_paragraphs() if p.is_mixed]


def create_sample_document(output_path: str = "documents/sample_tafsir.docx"):
    """
    Create a sample document for testing.

    Args:
        output_path: Where to save the sample document
    """
    doc = Document()

    # Add title
    doc.add_heading('Образец Тафсира - نموذج التفسير', 0)

    # Add mixed content
    doc.add_paragraph(
        'Во имя Аллаха, Милостивого, Милосердного'
    )
    doc.add_paragraph(
        'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ'
    )
    doc.add_paragraph(
        'Сура Аль-Фатиха (الفاتحة) - Открывающая книгу'
    )
    doc.add_paragraph(
        'Аят 1: الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ'
    )
    doc.add_paragraph(
        'Хвала Аллаху, Господу миров!'
    )
    doc.add_paragraph(
        'Тафсир: Слово "الحمد" (аль-хамд) означает восхваление...'
    )

    # Save document
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output))

    print(f"✅ Sample document created: {output}")
    return str(output)


# Main execution for testing
if __name__ == "__main__":
    import sys

    print("🕌 Tafsir Document Processor")
    print("="*40)

    # Check for command line argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # Create sample if no file provided
        print("\nNo file provided. Creating sample document...")
        file_path = create_sample_document()

    # Process document
    processor = TafsirDocumentProcessor()

    if processor.load(file_path):
        processor.print_paragraphs(limit=20)

        # Demo: Find specific text
        print("\n🔍 Searching for 'Аллах'...")
        results = processor.find_paragraphs_by_text("Аллах")
        print(f"   Found {len(results)} paragraphs")
        for r in results[:3]:
            print(f"   [{r.index}]: {r.text[:50]}...")
