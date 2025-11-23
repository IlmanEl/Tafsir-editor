"""
AI Editor Module for Tafsir Documents.
Uses OpenAI GPT to improve COMMENTARY and TRANSLATION blocks.
Implements visual diff in Word documents (strikethrough + highlight).
"""

from typing import Optional, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import copy

from openai import OpenAI
from docx import Document
from docx.shared import RGBColor, Pt
from docx.enum.text import WD_COLOR_INDEX

from config import config
from document_processor import TafsirDocumentProcessor, TafsirBlock, BlockType


# System prompt for the AI editor
SYSTEM_PROMPT = """Ты профессиональный редактор исламской литературы (Тафсир) на русском языке.

ТВОЯ ЗАДАЧА:
1. Исправь грамматические и пунктуационные ошибки
2. Улучши стиль текста, сделай его более литературным и уважительным
3. Сохрани академический тон, подходящий для религиозной литературы

СТРОГИЕ ПРАВИЛА:
- НЕ меняй богословский смысл текста
- НЕ удаляй и НЕ изменяй арабские слова/фразы в скобках (например: «الحمد» или (аль-хамд))
- НЕ добавляй новую информацию от себя
- Сохраняй все цитаты и ссылки без изменений
- Если текст уже хорош — верни его без изменений

ФОРМАТ ОТВЕТА:
Верни ТОЛЬКО исправленный текст, без комментариев и пояснений."""


@dataclass
class EditResult:
    """Result of AI editing for a single block."""
    block_index: int
    original_text: str
    edited_text: str
    was_changed: bool
    error: Optional[str] = None


class TafsirAIEditor:
    """
    AI-powered editor for Tafsir documents.
    Uses OpenAI to improve text while preserving Quranic content.
    """

    def __init__(self):
        """Initialize the AI editor."""
        self.client: Optional[OpenAI] = None
        self.model = config.OPENAI_MODEL
        self._init_client()

    def _init_client(self) -> bool:
        """Initialize OpenAI client."""
        if not config.OPENAI_API_KEY:
            print("[ERROR] OPENAI_API_KEY is not set in .env")
            return False

        try:
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to initialize OpenAI client: {e}")
            return False

    def is_ready(self) -> bool:
        """Check if the editor is ready to use."""
        return self.client is not None

    def edit_text(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Send text to OpenAI for editing.

        Args:
            text: Original text to edit

        Returns:
            Tuple of (edited_text, error_message)
        """
        if not self.client:
            return text, "OpenAI client not initialized"

        if not text.strip():
            return text, None

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ],
                temperature=0.3,  # Low temperature for consistent editing
                max_tokens=len(text) * 2 + 500,  # Allow some expansion
            )

            edited = response.choices[0].message.content.strip()
            return edited, None

        except Exception as e:
            return text, f"OpenAI API error: {str(e)}"

    def edit_block(self, block: TafsirBlock) -> EditResult:
        """
        Edit a single block using AI.

        Args:
            block: TafsirBlock to edit

        Returns:
            EditResult with original and edited text
        """
        if not block.can_process_with_ai:
            return EditResult(
                block_index=block.index,
                original_text=block.text,
                edited_text=block.text,
                was_changed=False,
                error="Block is not marked for AI processing"
            )

        edited_text, error = self.edit_text(block.text)

        # Check if text actually changed
        was_changed = edited_text.strip() != block.text.strip()

        return EditResult(
            block_index=block.index,
            original_text=block.text,
            edited_text=edited_text,
            was_changed=was_changed,
            error=error
        )


class VisualDiffWriter:
    """
    Creates Word documents with visual diff.
    Old text: strikethrough
    New text: yellow highlight
    """

    def __init__(self, source_path: str):
        """
        Initialize with source document.

        Args:
            source_path: Path to original .docx file
        """
        self.source_path = Path(source_path)
        self.document = Document(str(source_path))

    def apply_visual_diff(self, paragraph_index: int, original: str, edited: str) -> bool:
        """
        Apply visual diff to a paragraph.
        Replaces paragraph content with: [strikethrough old] [highlighted new]

        Args:
            paragraph_index: Index of paragraph to modify
            original: Original text
            edited: Edited text

        Returns:
            bool: True if successfully applied
        """
        if paragraph_index >= len(self.document.paragraphs):
            return False

        if original.strip() == edited.strip():
            return False  # No changes

        paragraph = self.document.paragraphs[paragraph_index]

        # Clear existing runs
        for run in paragraph.runs:
            run.text = ""

        # If paragraph has no runs, we need to work with the paragraph directly
        # Clear and rebuild
        paragraph.clear()

        # Add OLD text with strikethrough (red)
        old_run = paragraph.add_run(original)
        old_run.font.strike = True
        old_run.font.color.rgb = RGBColor(180, 0, 0)  # Dark red

        # Add separator
        sep_run = paragraph.add_run("  →  ")
        sep_run.font.bold = True
        sep_run.font.color.rgb = RGBColor(100, 100, 100)  # Gray

        # Add NEW text with yellow highlight
        new_run = paragraph.add_run(edited)
        new_run.font.highlight_color = WD_COLOR_INDEX.YELLOW
        new_run.font.color.rgb = RGBColor(0, 100, 0)  # Dark green

        return True

    def apply_edits(self, edit_results: List[EditResult]) -> int:
        """
        Apply all edits to the document with visual diff.

        Args:
            edit_results: List of EditResult objects

        Returns:
            int: Number of paragraphs modified
        """
        modified_count = 0

        for result in edit_results:
            if result.was_changed and not result.error:
                success = self.apply_visual_diff(
                    result.block_index,
                    result.original_text,
                    result.edited_text
                )
                if success:
                    modified_count += 1

        return modified_count

    def save(self, output_path: str) -> bool:
        """
        Save the modified document.

        Args:
            output_path: Path for output file

        Returns:
            bool: True if saved successfully
        """
        try:
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            self.document.save(str(output))
            print(f"[OK] Document saved: {output}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save document: {e}")
            return False


def edit_document(
    input_path: str,
    output_path: Optional[str] = None,
    max_blocks: Optional[int] = None,
    dry_run: bool = False
) -> Tuple[int, int, List[EditResult]]:
    """
    Main function to edit a Tafsir document using AI.

    Args:
        input_path: Path to input .docx file
        output_path: Path for output file (default: input_edited.docx)
        max_blocks: Maximum number of blocks to process (for testing)
        dry_run: If True, only show what would be changed without saving

    Returns:
        Tuple of (total_processed, total_changed, list of EditResults)
    """
    # Generate output path if not provided
    if not output_path:
        input_file = Path(input_path)
        output_path = str(input_file.parent / f"{input_file.stem}_edited{input_file.suffix}")

    print("\n" + "=" * 70)
    print("AI-POWERED DOCUMENT EDITING")
    print("=" * 70)
    print(f"\n  Input:  {input_path}")
    print(f"  Output: {output_path}")
    print(f"  Model:  {config.OPENAI_MODEL}")
    if dry_run:
        print("  Mode:   DRY RUN (no changes will be saved)")
    print()

    # Initialize AI editor
    editor = TafsirAIEditor()
    if not editor.is_ready():
        print("[ERROR] AI editor not ready. Check OPENAI_API_KEY in .env")
        return 0, 0, []

    # Load and classify document
    processor = TafsirDocumentProcessor()
    if not processor.load(input_path):
        return 0, 0, []

    processor.classify_document()

    # Get AI-processable blocks
    ai_blocks = processor.get_ai_processable_blocks()
    if max_blocks:
        ai_blocks = ai_blocks[:max_blocks]

    print(f"  Found {len(ai_blocks)} blocks for AI processing\n")

    if not ai_blocks:
        print("[INFO] No blocks to process")
        return 0, 0, []

    # Process blocks
    results: List[EditResult] = []
    total_changed = 0

    for i, block in enumerate(ai_blocks):
        block_type = "COMMENTARY" if block.block_type == BlockType.COMMENTARY else "TRANSLATION"
        print(f"  [{i+1}/{len(ai_blocks)}] Processing {block_type} block #{block.index}...", end=" ")

        result = editor.edit_block(block)
        results.append(result)

        if result.error:
            print(f"ERROR: {result.error}")
        elif result.was_changed:
            print("CHANGED")
            total_changed += 1
        else:
            print("no changes")

    print(f"\n  Processed: {len(results)}, Changed: {total_changed}")

    # Apply changes to document
    if not dry_run and total_changed > 0:
        print("\n  Applying visual diff to document...")
        writer = VisualDiffWriter(input_path)
        modified = writer.apply_edits(results)
        writer.save(output_path)
        print(f"\n  [OK] {modified} paragraphs modified with visual diff")

    # Show sample changes
    if total_changed > 0:
        print("\n" + "-" * 70)
        print("SAMPLE CHANGES:")
        print("-" * 70)

        shown = 0
        for result in results:
            if result.was_changed and shown < 3:
                print(f"\n  Block #{result.block_index}:")
                print(f"  OLD: {result.original_text[:100]}...")
                print(f"  NEW: {result.edited_text[:100]}...")
                shown += 1

    print("\n" + "=" * 70)

    return len(results), total_changed, results
