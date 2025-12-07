import streamlit as st
import tempfile
from pathlib import Path
import sys

from document_processor import TafsirDocumentProcessor, BlockType
from ai_editor import TafsirAIEditor, VisualDiffWriter, EditCache
from config import config


st.set_page_config(
    page_title="Tafsir Editor",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded"
)


def render_block_html(block, show_metadata=False):
    block_type_colors = {
        BlockType.AYAH: "#8B0000",
        BlockType.TRANSLATION: "#000000",
        BlockType.COMMENTARY: "#2F4F4F",
        BlockType.EXPLANATION: "#1E4D2B",
        BlockType.HEADER: "#4B0082",
        BlockType.REFERENCE: "#696969",
    }

    color = block_type_colors.get(block.block_type, "#000000")

    padding_left = "0px"
    font_style = "normal"
    border_left = ""

    if block.block_type in (BlockType.COMMENTARY, BlockType.EXPLANATION):
        padding_left = "30px"
        border_left = "border-left: 3px solid #cccccc;"
        font_style = "italic"

    if block.block_type == BlockType.AYAH:
        text = f"﴿ {block.text} ﴾"
        font_family = "Traditional Arabic, Amiri, serif"
        font_size = "18px"
        text_align = "right"
        direction = "rtl"
    else:
        text = block.text
        font_family = "Georgia, serif"
        font_size = "16px"
        text_align = "left"
        direction = "ltr"

    metadata_html = ""
    if show_metadata:
        can_ai = "✅ AI" if block.can_process_with_ai else "🔒 Protected"
        metadata_html = f'<div style="font-size: 11px; color: #888; margin-bottom: 5px;">[Block #{block.index}] {block.block_type.value} | {can_ai}</div>'

    html = f"""
    <div style="
        margin-bottom: 20px;
        padding: 15px;
        padding-left: {padding_left};
        {border_left}
        background-color: #fafafa;
        border-radius: 5px;
    ">
        {metadata_html}
        <div style="
            color: {color};
            font-family: {font_family};
            font-size: {font_size};
            font-style: {font_style};
            line-height: 1.8;
            text-align: {text_align};
            direction: {direction};
        ">
            {text}
        </div>
    </div>
    """

    return html


def main():
    st.title("📖 Tafsir Editor - AI-Powered Document Correction")

    st.sidebar.header("⚙️ Настройки")

    show_metadata = st.sidebar.checkbox("Показать метаданные блоков", value=False)
    use_cache = st.sidebar.checkbox("Использовать кэш (resumable)", value=True)

    if st.sidebar.button("🗑️ Очистить кэш"):
        st.sidebar.success("Кэш будет очищен при следующей обработке")
        st.session_state['clear_cache'] = True

    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    **Возможности:**
    - 🔍 Умная классификация блоков
    - 🤖 AI корректор (не переписывает!)
    - 📝 Word-level diff
    - 🕌 Красивые скобки ﴿﴾ для аятов
    - 💾 Checkpoint система
    """)

    uploaded_file = st.file_uploader(
        "Загрузите документ Word (.docx)",
        type=['docx'],
        help="Выберите файл тафсира для обработки"
    )

    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name

        processor = TafsirDocumentProcessor()

        with st.spinner("Загрузка и классификация документа..."):
            if processor.load(tmp_path):
                processor.classify_document()

                stats = processor.get_stats()

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Всего блоков", stats.total_blocks)
                with col2:
                    st.metric("Аяты 🕌", stats.ayah_blocks)
                with col3:
                    st.metric("Комментарии", stats.commentary_blocks)
                with col4:
                    st.metric("Для AI", stats.ai_processable_blocks)

                tab1, tab2 = st.tabs(["📄 Оригинал", "🤖 AI Редактор"])

                with tab1:
                    st.subheader("Предпросмотр документа")

                    all_blocks = processor.blocks

                    for block in all_blocks[:50]:
                        st.markdown(render_block_html(block, show_metadata), unsafe_allow_html=True)

                    if len(all_blocks) > 50:
                        st.info(f"Показано первых 50 блоков из {len(all_blocks)}")

                with tab2:
                    st.subheader("🤖 AI-Powered Correction")

                    if not config.OPENAI_API_KEY:
                        st.error("⚠️ OPENAI_API_KEY не установлен в .env файле")
                        st.stop()

                    st.markdown("""
                    **Режим работы:** Корректор (НЕ редактор!)
                    - ✅ Исправляет орфографию, грамматику, пунктуацию
                    - ❌ НЕ переписывает стиль
                    - 🔒 Аяты защищены от изменений
                    """)

                    col_left, col_right = st.columns([2, 1])

                    with col_left:
                        custom_instruction = st.text_area(
                            "Дополнительная инструкция (опционально)",
                            placeholder="Например: Обрати внимание на транслитерацию имени Аллаh",
                            height=100
                        )

                    with col_right:
                        max_blocks = st.number_input(
                            "Лимит блоков (0 = все)",
                            min_value=0,
                            max_value=stats.ai_processable_blocks,
                            value=0,
                            help="Для тестирования можно ограничить количество"
                        )

                        dry_run = st.checkbox("Dry run (не сохранять)", value=False)

                    if st.button("🚀 Найти ошибки и исправить", type="primary"):
                        from ai_editor import edit_document

                        output_path = tmp_path.replace('.docx', '_edited.docx')

                        progress_bar = st.progress(0)
                        status_text = st.empty()

                        status_text.text("Инициализация AI корректора...")

                        clear_cache = st.session_state.get('clear_cache', False)

                        ai_blocks = processor.get_ai_processable_blocks()
                        ayah_blocks = processor.get_blocks_by_type(BlockType.AYAH)

                        if max_blocks > 0:
                            ai_blocks = ai_blocks[:max_blocks]

                        editor = TafsirAIEditor()
                        if not editor.is_ready():
                            st.error("AI editor не готов. Проверьте OPENAI_API_KEY")
                            st.stop()

                        cache_path = f"{tmp_path}.cache.json"
                        cache = EditCache(cache_path) if use_cache else None

                        if clear_cache and cache:
                            cache.clear()
                            st.session_state['clear_cache'] = False

                        if cache:
                            cache.set_metadata(tmp_path, config.OPENAI_MODEL, len(ai_blocks))

                        results = []
                        total_changed = 0
                        total_cached = 0

                        for i, block in enumerate(ai_blocks):
                            progress = (i + 1) / len(ai_blocks)
                            progress_bar.progress(progress)
                            status_text.text(f"Обработка блока {i+1}/{len(ai_blocks)}...")

                            cached_result = cache.get_result(block.index) if cache else None

                            if cached_result:
                                result = cached_result
                                total_cached += 1
                            else:
                                result = editor.edit_block(block, max_retries=3)

                                if cache:
                                    cache.save_result(result)

                                if result.error:
                                    st.error(f"Ошибка на блоке {block.index}: {result.error}")
                                    break

                            results.append(result)

                            if result.was_changed and not result.skipped_original:
                                total_changed += 1

                        if cache:
                            cache.update_metadata()

                        progress_bar.progress(1.0)
                        status_text.text("Применение изменений к документу...")

                        if not dry_run and (total_changed > 0 or ayah_blocks):
                            writer = VisualDiffWriter(tmp_path)
                            modified = writer.apply_edits(results, ayah_blocks)
                            writer.save(output_path)

                            st.success(f"✅ Готово! Обработано: {len(results)}, Изменено: {total_changed}, Из кэша: {total_cached}")

                            with open(output_path, 'rb') as f:
                                st.download_button(
                                    label="📥 Скачать отредактированный документ",
                                    data=f,
                                    file_name=f"{uploaded_file.name.replace('.docx', '_edited.docx')}",
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                                )

                            st.info("""
                            **Как проверить изменения в Word:**
                            - 🔴 Зачеркнутый текст = старый (удален)
                            - 🟡 Желтое выделение = новый (добавлен)
                            - ⚫ Обычный черный = без изменений
                            """)
                        else:
                            st.info(f"Dry run: найдено {total_changed} изменений (не сохранено)")

                        if total_changed > 0:
                            st.markdown("### 📝 Примеры изменений:")
                            shown = 0
                            for result in results:
                                if result.was_changed and not result.skipped_original and shown < 3:
                                    with st.expander(f"Блок #{result.block_index}"):
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.markdown("**Было:**")
                                            st.text(result.original_text[:200])
                                        with col2:
                                            st.markdown("**Стало:**")
                                            st.text(result.edited_text[:200])
                                    shown += 1

            else:
                st.error("Не удалось загрузить документ")

        Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
