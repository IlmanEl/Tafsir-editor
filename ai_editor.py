from typing import Optional, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import difflib

from openai import OpenAI
from docx import Document
from docx.shared import RGBColor, Pt
from docx.enum.text import WD_COLOR_INDEX

from config import config
from document_processor import TafsirDocumentProcessor, TafsirBlock, BlockType


def get_system_prompt() -> str:
    return """Ты корректор (НЕ редактор!) текстов тафсира на русском языке.

⚠️ КРИТИЧЕСКИ ВАЖНО:
- Если текст БЕЗ ОШИБОК — верни ТОЛЬКО одно слово: ORIGINAL
- ЗАПРЕЩЕНО переписывать, переформулировать или "улучшать стиль"
- Разрешено ТОЛЬКО исправлять явные ошибки

РАЗРЕШЕННЫЕ ИСПРАВЛЕНИЯ (только если есть):
1. Грамматические ошибки (падежи, согласование, склонение)
2. Орфографические ошибки (опечатки, неправильное написание слов)
3. Пунктуация (пропущенные или лишние запятые, точки)

СТРОГО ЗАПРЕЩЕНО:
- Менять порядок слов
- Заменять слова синонимами
- Добавлять или удалять слова (кроме исправления явных ошибок)
- "Улучшать стиль" или делать текст "более литературным"
- Менять богословский смысл
- Менять структуру предложений

СТРОГИЕ ПРАВИЛА ТРАНСЛИТЕРАЦИИ АРАБСКИХ БУКВ:
⚠️ КРИТИЧЕСКИ ВАЖНО! НЕ МЕНЯЙ ЭТИ БУКВЫ:

- Буква 'h' (латинская) = ТОЛЬКО арабская 'ه' (ха)
  Примеры: Аллаh, Умм hани, Мухаммад ﷺ
  ЗАПРЕЩЕНО менять 'h' на 'х' (русскую)!

- Буква 'х' (русская) = арабская 'ح' (ха с точкой)
  Примеры: хадис, хадж, Рахман

- Буква 'г' = арабская 'غ' (гайн)
  Примеры: Магриб, Багдад

- Буква 'с̱' (межзубная) = арабская 'ث' (са)
  Пример: с̱икр (поминание)

- Буква 'з̱' (межзубная) = арабская 'ذ' (заль)
  Пример: з̱икр (вариант)

- Символ 'ʻ' (айн) = арабская 'ع'
  Примеры: ʻАрафат, ʻАббас

- Символ ''' (апостроф-хамза) = арабская 'ء'
  Примеры: Му'мин, Ка'ба

РЕЛИГИОЗНЫЕ ТЕРМИНЫ:
- Имя Бога: ТОЛЬКО «Аллаh» (с латинской 'h' в конце)
- Имена пророков: с заглавной буквы и уважительным тоном
- Символ ﷺ (صلى الله عليه وسلم) ОСТАВЛЯЙ БЕЗ ИЗМЕНЕНИЙ
- Арабские слова в скобках НЕ ТРОГАЙ: «الحمد» или (аль-хамд)

ОБЩИЕ ПРАВИЛА:
- НЕ меняй богословский смысл текста
- НЕ удаляй и НЕ изменяй арабские слова/фразы
- НЕ добавляй новую информацию от себя
- Сохраняй все цитаты и ссылки без изменений

ПРИМЕРЫ (Few-shot):

Input: "Во истину Аллаh велик."
Output: "Воистину Аллаh велик."
Причина: Орфографическая ошибка ("Во истину" → "Воистину")

Input: "Аллаh создал небеса и землю."
Output: ORIGINAL
Причина: Нет ошибок

Input: "Сказал Всевышний Аллаh в своей книге."
Output: ORIGINAL
Причина: Стиль простой, но грамматика верна. НЕ меняй на "Всевышний Аллаh изрек в Писании"!

Input: "Пророк Мухаммад ﷺ говорил что милосердие важно."
Output: "Пророк Мухаммад ﷺ говорил, что милосердие важно."
Причина: Пунктуация (пропущена запятая перед "что")

Input: "Этот хадис передали имам Бухари и Муслим."
Output: "Этот хадис передали имам Бухари и имам Муслим."
Причина: Грамматика (согласование: "имам" нужно повторить)

Input: "Аллах могущественен и мудр."
Output: "Аллаh могущественен и мудр."
Причина: Транслитерация ('х' → 'h' для имени Бога)

Input: "В суре Аль-Фатиха говорится о величии Творца."
Output: ORIGINAL
Причина: Нет ошибок (даже если можно сделать "красивее")

ФОРМАТ ОТВЕТА:
- Нет ошибок → верни: ORIGINAL
- Есть ошибки → верни ТОЛЬКО исправленный текст (без пояснений и комментариев)"""


def clean_ayah_text(text: str) -> str:
    text = text.strip()
    text = text.strip('﴿﴾')
    text = text.replace('«', '').replace('»', '')
    text = text.replace('"', '').replace('"', '').replace('"', '')
    text = text.replace("'", '').replace("'", '').replace("'", '')
    return text.strip()


@dataclass
class EditResult:
    block_index: int
    original_text: str
    edited_text: str
    was_changed: bool
    error: Optional[str] = None
    skipped_original: bool = False


class TafsirAIEditor:
    def __init__(self):
        self.client: Optional[OpenAI] = None
        self.model = config.OPENAI_MODEL
        self._init_client()

    def _init_client(self) -> bool:
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
        return self.client is not None

    def edit_text(self, text: str) -> Tuple[str, Optional[str]]:
        if not self.client:
            return text, "OpenAI client not initialized"

        if not text.strip():
            return text, None

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": text}
                ],
                temperature=0.1,
                max_tokens=len(text) * 2 + 500,
            )

            edited = response.choices[0].message.content.strip()
            return edited, None

        except Exception as e:
            return text, f"OpenAI API error: {str(e)}"

    def edit_block(self, block: TafsirBlock) -> EditResult:
        if not block.can_process_with_ai:
            return EditResult(
                block_index=block.index,
                original_text=block.text,
                edited_text=block.text,
                was_changed=False,
                error="Block is not marked for AI processing"
            )

        edited_text, error = self.edit_text(block.text)

        if edited_text.strip().upper() == "ORIGINAL":
            return EditResult(
                block_index=block.index,
                original_text=block.text,
                edited_text=block.text,
                was_changed=False,
                error=None,
                skipped_original=True
            )

        was_changed = edited_text.strip() != block.text.strip()

        return EditResult(
            block_index=block.index,
            original_text=block.text,
            edited_text=edited_text,
            was_changed=was_changed,
            error=error
        )


@dataclass
class DiffOperation:
    operation: str
    text: str


class VisualDiffWriter:
    def __init__(self, source_path: str):
        self.source_path = Path(source_path)
        self.document = Document(str(source_path))

    def _compute_word_diff(self, old_text: str, new_text: str) -> List[DiffOperation]:
        old_words = old_text.split()
        new_words = new_text.split()

        matcher = difflib.SequenceMatcher(None, old_words, new_words)
        operations = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                text = ' '.join(old_words[i1:i2])
                operations.append(DiffOperation('equal', text))

            elif tag == 'delete':
                text = ' '.join(old_words[i1:i2])
                operations.append(DiffOperation('delete', text))

            elif tag == 'insert':
                text = ' '.join(new_words[j1:j2])
                operations.append(DiffOperation('insert', text))

            elif tag == 'replace':
                if i1 < i2:
                    old_part = ' '.join(old_words[i1:i2])
                    operations.append(DiffOperation('delete', old_part))
                if j1 < j2:
                    new_part = ' '.join(new_words[j1:j2])
                    operations.append(DiffOperation('insert', new_part))

        return operations

    def apply_ayah_brackets(self, paragraph_index: int, text: str) -> bool:
        if paragraph_index >= len(self.document.paragraphs):
            return False

        paragraph = self.document.paragraphs[paragraph_index]
        paragraph.clear()

        cleaned_text = clean_ayah_text(text)

        opening_run = paragraph.add_run("\ufd3f ")
        opening_run.font.name = "Traditional Arabic"
        opening_run.font.size = Pt(16)
        opening_run.font.color.rgb = RGBColor(139, 0, 0)
        opening_run.font.bold = False

        text_run = paragraph.add_run(cleaned_text)
        text_run.font.name = "Traditional Arabic"
        text_run.font.size = Pt(16)
        text_run.font.color.rgb = RGBColor(139, 0, 0)
        text_run.font.bold = False

        closing_run = paragraph.add_run(" \ufd3e")
        closing_run.font.name = "Traditional Arabic"
        closing_run.font.size = Pt(16)
        closing_run.font.color.rgb = RGBColor(139, 0, 0)
        closing_run.font.bold = False

        return True

    def apply_visual_diff(self, paragraph_index: int, original: str, edited: str) -> bool:
        if paragraph_index >= len(self.document.paragraphs):
            return False

        if original.strip() == edited.strip():
            return False

        paragraph = self.document.paragraphs[paragraph_index]
        paragraph.clear()

        diff_ops = self._compute_word_diff(original, edited)

        for i, op in enumerate(diff_ops):
            if not op.text:
                continue

            if i > 0 and op.operation != 'equal':
                if diff_ops[i-1].operation != 'equal':
                    paragraph.add_run(" ")

            if op.operation == 'equal':
                paragraph.add_run(op.text)

            elif op.operation == 'delete':
                run = paragraph.add_run(op.text)
                run.font.strike = True
                run.font.color.rgb = RGBColor(180, 0, 0)

            elif op.operation == 'insert':
                run = paragraph.add_run(op.text)
                run.font.highlight_color = WD_COLOR_INDEX.YELLOW
                run.font.color.rgb = RGBColor(0, 100, 0)

            if i < len(diff_ops) - 1:
                next_op = diff_ops[i + 1]
                if next_op.operation == 'equal':
                    paragraph.add_run(" ")

        return True

    def apply_edits(self, edit_results: List[EditResult], ayah_blocks: List[TafsirBlock] = None) -> int:
        modified_count = 0

        for result in edit_results:
            if result.was_changed and not result.error and not result.skipped_original:
                success = self.apply_visual_diff(
                    result.block_index,
                    result.original_text,
                    result.edited_text
                )
                if success:
                    modified_count += 1

        if ayah_blocks:
            for ayah in ayah_blocks:
                self.apply_ayah_brackets(ayah.index, ayah.text)

        return modified_count

    def save(self, output_path: str) -> bool:
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
    if not output_path:
        input_file = Path(input_path)
        output_path = str(input_file.parent / f"{input_file.stem}_edited{input_file.suffix}")

    print("\n" + "=" * 70)
    print("AI-POWERED DOCUMENT CORRECTION (Surgical Word-Level Diff)")
    print("=" * 70)
    print(f"\n  Input:  {input_path}")
    print(f"  Output: {output_path}")
    print(f"  Model:  {config.OPENAI_MODEL}")
    if dry_run:
        print("  Mode:   DRY RUN (no changes will be saved)")
    print()

    editor = TafsirAIEditor()
    if not editor.is_ready():
        print("[ERROR] AI corrector not ready. Check OPENAI_API_KEY in .env")
        return 0, 0, []

    processor = TafsirDocumentProcessor()
    if not processor.load(input_path):
        return 0, 0, []

    processor.classify_document()

    ai_blocks = processor.get_ai_processable_blocks()
    ayah_blocks = processor.get_blocks_by_type(BlockType.AYAH)

    if max_blocks:
        ai_blocks = ai_blocks[:max_blocks]

    print(f"  Found {len(ai_blocks)} blocks for AI correction")
    print(f"  Found {len(ayah_blocks)} ayah blocks (will add beautiful brackets)\n")

    if not ai_blocks and not ayah_blocks:
        print("[INFO] No blocks to process")
        return 0, 0, []

    results: List[EditResult] = []
    total_changed = 0
    total_skipped = 0

    for i, block in enumerate(ai_blocks):
        block_type = "COMMENTARY" if block.block_type == BlockType.COMMENTARY else "TRANSLATION"
        print(f"  [{i+1}/{len(ai_blocks)}] Processing {block_type} block #{block.index}...", end=" ")

        result = editor.edit_block(block)
        results.append(result)

        if result.error:
            print(f"ERROR: {result.error}")
        elif result.skipped_original:
            print("ORIGINAL (already good)")
            total_skipped += 1
        elif result.was_changed:
            print("CHANGED")
            total_changed += 1
        else:
            print("no changes")

    print(f"\n  Processed: {len(results)}, Changed: {total_changed}, Skipped (ORIGINAL): {total_skipped}")

    if not dry_run and (total_changed > 0 or ayah_blocks):
        print("\n  Applying surgical word-level diff to document...")
        writer = VisualDiffWriter(input_path)
        modified = writer.apply_edits(results, ayah_blocks)
        writer.save(output_path)
        print(f"\n  [OK] {modified} paragraphs modified with word-level diff")
        if ayah_blocks:
            print(f"  [OK] {len(ayah_blocks)} ayahs beautified with ﴿﴾ brackets (Traditional Arabic font)")

    if total_changed > 0:
        print("\n" + "-" * 70)
        print("SAMPLE CHANGES:")
        print("-" * 70)

        shown = 0
        for result in results:
            if result.was_changed and not result.skipped_original and shown < 3:
                print(f"\n  Block #{result.block_index}:")
                print(f"  OLD: {result.original_text[:100]}...")
                print(f"  NEW: {result.edited_text[:100]}...")
                shown += 1

    print("\n" + "=" * 70)

    return len(results), total_changed, results
