"""Renders parsed markdown blocks into a docx built on a template's own styles."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.image.image import Image as DocxImage
from docx.oxml.ns import qn
from docx.shared import Cm, Emu, Pt
from lxml import etree

from . import semantics
from .config import StyleConfig, StyleSet
from .inline import Inline, LineBreak, MathRun, TextRun, plain_text
from .mdparse import (Block, CodeBlock, DisplayMath, Figure, Heading, ListBlock,
                      Paragraph, Rule, Table)
from .omml import MathConverter, latex_to_plain
from .template import load_document

_UDC = semantics.UDC
_NUMBERED_HEADING = semantics.NUMBERED_HEADING
_REFERENCE_HEADING = semantics.REFERENCE_HEADING
_ABSTRACT_HEADING = semantics.ABSTRACT_HEADING
_KEYWORDS = semantics.KEYWORDS
_strip_leading_number = semantics.strip_leading_number
_is_table_caption = semantics.is_table_caption
_only_bold = semantics.only_bold
_MONOSPACE = 'Consolas'


class ArticleWriter:
    """Builds a single docx out of markdown blocks, section by section."""

    def __init__(self, style: StyleConfig, styleset: StyleSet,
                 math_xsl: Path | None = None, include_figures: bool = True,
                 include_tables: bool = True, heading_offset: int = 0,
                 assets_root: Path | None = None):
        self.style = style
        self.styleset = styleset
        self.include_figures = include_figures
        self.include_tables = include_tables
        self.heading_offset = heading_offset
        self.assets_root = assets_root
        self.math = MathConverter(math_xsl, font=style.math_font,
                                  size_pt=style.size_pt if styleset.manual_formatting else None)
        self.warnings: list[str] = []

        self.document = load_document(styleset.template)
        if styleset.template is not None:
            _clear_body(self.document)
        if styleset.create_styles:
            _register_styles(self.document, style)
        self._missing_styles: set[str] = set()

        self._front_matter = True
        self._in_references = False
        self._pending_authors = False
        self._pending_abstract = False
        self._pending_affiliation = False
        self._after_heading = False

    # ------------------------------------------------------------------ public

    def add_section(self, blocks: list[Block], page_break: bool = False) -> None:
        if page_break and _has_content(self.document):
            self._paragraph('body').add_run().add_break(WD_BREAK.PAGE)
        self._render_blocks(blocks)

    def save(self, path: Path, metadata: dict | None = None) -> None:
        if metadata:
            properties = self.document.core_properties
            for key, value in metadata.items():
                if hasattr(properties, key):
                    setattr(properties, key, value)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.document.save(str(path))

    # ----------------------------------------------------------------- styles

    def _paragraph(self, role: str):
        return self.document.add_paragraph(style=self._style_name(role))

    def _style_name(self, role: str) -> str:
        name = self.styleset.style_for(role)
        try:
            self.document.styles[name]
        except KeyError:
            if name not in self._missing_styles:
                self._missing_styles.add(name)
                self.warnings.append(f'стиль "{name}" (роль {role}) відсутній у шаблоні')
            return 'Normal'
        return name

    @property
    def _formats(self) -> bool:
        """True when the renderer may set fonts and sizes on runs itself."""
        return self.styleset.manual_formatting

    # ----------------------------------------------------------------- blocks

    def _render_blocks(self, blocks: list[Block]) -> None:
        index = 0
        while index < len(blocks):
            block = blocks[index]
            caption = block if _is_table_caption(block) else None
            table = blocks[index + 1] if caption and index + 1 < len(blocks) else None
            if caption is not None and isinstance(table, Table):
                self._render_table_group(caption, table)
                index += 2
                continue
            self._render_block(block)
            index += 1

    def _render_table_group(self, caption: Paragraph, table: Table) -> None:
        """Keep a caption with its table, turning the page when the table is too wide."""
        landscape = (self.styleset.landscape_wide_tables and self.include_tables
                     and self._needs_landscape(table))
        if landscape:
            _switch_orientation(self.document, landscape=True)
        self._render_paragraph(caption)
        self._render_table(table)
        if landscape:
            _switch_orientation(self.document, landscape=False)

    def _needs_landscape(self, block: Table) -> bool:
        if not self.styleset.fit_table_columns:
            return False
        return _plan_columns(block, self.style, self._text_width_cm(),
                             self._table_limit_cm()).overflow

    def _render_block(self, block: Block) -> None:
        if isinstance(block, Heading):
            self._render_heading(block)
        elif isinstance(block, Paragraph):
            self._render_paragraph(block)
        elif isinstance(block, DisplayMath):
            self._render_equation(block)
        elif isinstance(block, Figure):
            self._render_figure(block)
        elif isinstance(block, Table):
            self._render_table(block)
        elif isinstance(block, ListBlock):
            self._render_list(block)
        elif isinstance(block, CodeBlock):
            self._render_code(block)
        elif isinstance(block, Rule):
            self._pending_authors = False
            self._pending_affiliation = False

    def _render_heading(self, heading: Heading) -> None:
        if _NUMBERED_HEADING.match(heading.text):
            self._front_matter = False
        self._in_references = bool(_REFERENCE_HEADING.search(heading.text))
        self._pending_abstract = bool(_ABSTRACT_HEADING.match(heading.text))
        self._pending_affiliation = False

        if heading.level == 1 and self._front_matter and not _NUMBERED_HEADING.match(heading.text):
            paragraph = self._paragraph('title')
            if self.styleset.plain_title:
                _plainify_title(paragraph)
            self._write_runs(paragraph, heading.runs, force_bold=self._formats)
            self._pending_authors = True
            return

        runs = heading.runs
        if self.styleset.strip_heading_numbers:
            runs = _strip_leading_number(runs)
        level = max(1, min(4, heading.level + self.heading_offset))
        role = 'references_heading' if self._in_references else f'heading{level}'
        paragraph = self._paragraph(role)
        self._write_runs(paragraph, runs, force_bold=self._formats and self.style.heading_bold)
        self._pending_authors = False
        self._after_heading = True

    def _render_paragraph(self, block: Paragraph) -> None:
        if not block.runs:
            return
        role = self._paragraph_role(block)
        if role == 'body' and self._after_heading:
            role = 'body_after_heading'
        self._pending_authors = False
        self._pending_abstract = False
        self._pending_affiliation = role in ('authors', 'affiliation')
        self._after_heading = False
        self._write_runs(self._paragraph(role), block.runs)

    def _paragraph_role(self, block: Paragraph) -> str:
        if block.kind == 'figure_caption':
            return 'figure_caption'
        if block.kind == 'table_caption':
            return 'table_caption'
        text = plain_text(block.runs)
        if self._front_matter and _UDC.match(text):
            return 'udc'
        if self._pending_authors and _only_bold(block.runs):
            return 'authors'
        if self._pending_affiliation and self._front_matter:
            return 'affiliation'
        if self._pending_abstract:
            return 'abstract'
        if _KEYWORDS.match(text):
            return 'keywords'
        if self._in_references:
            return 'reference'
        return 'body'

    def _render_equation(self, block: DisplayMath) -> None:
        paragraph = self._paragraph('equation')
        if self.styleset.create_styles:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if self.styleset.equation_tab:
            paragraph.add_run().add_tab()
        omml = self.math.to_omml(block.latex)
        if omml is None:
            self._paragraph_text(paragraph, latex_to_plain(block.latex), italic=True)
        else:
            paragraph._p.append(omml)
        if block.tail:
            paragraph.add_run(block.tail)

    def _render_figure(self, block: Figure) -> None:
        if not self.include_figures:
            return
        path = self._resolve_asset(block.path)
        if path is None:
            self.warnings.append(f'не знайдено зображення: {block.path}')
            self._paragraph_text(self._paragraph('figure_caption'),
                                 f'[відсутнє зображення: {block.path}]', italic=True)
            return
        paragraph = self._paragraph('figure')
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.first_line_indent = Cm(0)
        paragraph.add_run().add_picture(str(path), width=Cm(self._figure_width_cm(path)))

    def _figure_width_cm(self, path: Path) -> float:
        maximum = min(self.style.figure_max_width_cm, self._text_width_cm())
        try:
            image = DocxImage.from_file(str(path))
            natural = image.width / image.horz_dpi * 2.54
        except Exception:                       # noqa: BLE001 - size probing is best effort
            return maximum
        return min(maximum, natural) if natural > 0 else maximum

    def _resolve_asset(self, reference: str) -> Path | None:
        candidate = Path(reference)
        if self.assets_root is not None:
            resolved = self.assets_root / candidate
            if resolved.is_file():
                return resolved
        return candidate if candidate.is_file() else None

    def _render_table(self, block: Table) -> None:
        if not self.include_tables:
            return
        table = self.document.add_table(rows=len(block.rows) + 1, cols=len(block.alignments))
        _apply_table_style(table, self.styleset.table_style, self.warnings)
        if self.styleset.fit_table_columns:
            plan = _plan_columns(block, self.style, self._text_width_cm(), self._table_limit_cm())
            _apply_widths(table, plan.widths, plan.total_cm)
            size_pt = plan.size_pt
            if plan.overflow:
                self.warnings.append(
                    f'таблиця «{_caption_hint(block)}» не вміщується навіть за {plan.size_pt:.0f} pt — '
                    'скоротіть заголовки стовпців або розверніть її на альбомну сторінку')
        else:
            _full_width(table)
            size_pt = None
        for index, cell_runs in enumerate(block.header):
            self._fill_cell(table.rows[0].cells[index], cell_runs,
                            block.alignments[index], size_pt, bold=True)
        _repeat_header(table.rows[0])
        for row_index, row in enumerate(block.rows, start=1):
            for index, cell_runs in enumerate(row):
                self._fill_cell(table.rows[row_index].cells[index], cell_runs,
                                block.alignments[index], size_pt)
        self._paragraph('body')

    def _text_width_cm(self) -> float:
        section = self.document.sections[-1]
        if not (section.page_width and section.left_margin and section.right_margin):
            return self.style.figure_max_width_cm
        return Emu(section.page_width - section.left_margin - section.right_margin).cm

    def _table_limit_cm(self) -> float:
        """How wide a table may grow; wide ones may reach into the page margins."""
        text_width = self._text_width_cm()
        if self.style.table_max_width_cm <= 0:
            return text_width
        section = self.document.sections[-1]
        page = Emu(section.page_width).cm if section.page_width else text_width
        return max(text_width, min(self.style.table_max_width_cm, page - 2 * _MIN_MARGIN_CM))

    def _fill_cell(self, cell, runs: list[Inline], alignment: str, size_pt: float | None,
                   bold: bool = False) -> None:
        paragraph = cell.paragraphs[0]
        paragraph.style = self.document.styles[self._style_name('table_cell')]
        paragraph.alignment = _ALIGNMENT[alignment]
        paragraph.paragraph_format.first_line_indent = Cm(0)
        self._write_runs(paragraph, runs, force_bold=bold, size_pt=size_pt)

    def _render_list(self, block: ListBlock) -> None:
        for item in block.items:
            if not item.blocks:
                continue
            first, *rest = item.blocks
            if isinstance(first, Paragraph):
                role = 'reference' if self._in_references else 'list'
                paragraph = self._paragraph(role)
                marker = self._list_marker(block, item.marker)
                if marker and self._in_references and self.styleset.reference_tab:
                    paragraph.add_run(marker.strip()).add_tab()
                elif marker:
                    paragraph.add_run(marker)
                self._write_runs(paragraph, first.runs)
            else:
                self._render_block(first)
            self._render_blocks(rest)

    def _list_marker(self, block: ListBlock, marker: str) -> str:
        if self.styleset.auto_list_numbers and not self._in_references:
            return ''
        return f'{marker} ' if block.ordered else f'{self.style.bullet_marker} '

    def _render_code(self, block: CodeBlock) -> None:
        for line in block.text.split('\n'):
            self._paragraph('code').add_run(line)

    # ------------------------------------------------------------------- runs

    def _write_runs(self, paragraph, runs: list[Inline], force_bold: bool = False,
                    size_pt: float | None = None) -> None:
        for item in runs:
            if isinstance(item, LineBreak):
                paragraph.add_run().add_break()
            elif isinstance(item, MathRun):
                self._write_math(paragraph, item, size_pt)
            else:
                self._write_text(paragraph, item, force_bold, size_pt)

    def _write_text(self, paragraph, item: TextRun, force_bold: bool,
                    size_pt: float | None) -> None:
        run = paragraph.add_run(item.text)
        run.bold = item.bold or force_bold
        run.italic = item.italic
        if item.code:
            run.font.name = _MONOSPACE
            _set_run_fonts(run, _MONOSPACE)
        if size_pt:
            run.font.size = Pt(size_pt)

    def _paragraph_text(self, paragraph, text: str, italic: bool = False) -> None:
        run = paragraph.add_run(text)
        run.italic = italic

    def _write_math(self, paragraph, item: MathRun, size_pt: float | None) -> None:
        converter = self.math
        if size_pt and size_pt != converter.size_pt:
            converter = MathConverter(converter.xsl_path, font=self.style.math_font,
                                      size_pt=size_pt)
        omml = converter.to_omml(item.latex)
        if omml is None:
            run = paragraph.add_run(latex_to_plain(item.latex))
            run.italic = True
            if size_pt:
                run.font.size = Pt(size_pt)
            return
        paragraph._p.append(omml)


# --------------------------------------------------------------------- tables

_ALIGNMENT = {
    'left': WD_ALIGN_PARAGRAPH.LEFT,
    'center': WD_ALIGN_PARAGRAPH.CENTER,
    'right': WD_ALIGN_PARAGRAPH.RIGHT,
}

_CELL_PADDING_CM = 0.22
_MAX_PREFERRED_CHARS = 26
_CHAR_WIDTH_RATIO = 0.0205          # ~mean Cyrillic glyph width of Times New Roman, cm per pt
_BOLD_FACTOR = 1.08
_MIN_MARGIN_CM = 1.5                # margin a table is never allowed to eat into


@dataclass
class TablePlan:
    widths: list[float]
    total_cm: float
    size_pt: float
    overflow: bool = False


def _plan_columns(block: Table, style: StyleConfig, available_cm: float,
                  limit_cm: float) -> TablePlan:
    """Pick column widths, the table width and, for wide tables, a smaller font.

    Columns never go below the width of their longest word, so Word has no reason
    to break words mid-way.  A table that outgrows the text column is first allowed
    to reach into the page margins (up to ``limit_cm``), and only then is the font
    reduced; ``overflow`` reports that even the smallest font was not enough.
    """
    size_pt = style.table_font_size_pt
    chars = _minimum_chars(block)
    padding = len(block.alignments) * 2 * _CELL_PADDING_CM
    at_base = chars * size_pt * _CHAR_WIDTH_RATIO + padding
    total = min(max(at_base, available_cm), limit_cm)
    if at_base > total and chars > 0:
        # cell padding does not scale with the font, so solve for the size directly
        ideal = (total - padding) / (chars * _CHAR_WIDTH_RATIO)
        size_pt = max(style.table_min_font_size_pt, min(size_pt, ideal))
    minimums, preferred = _column_demands(block, size_pt)
    required = sum(minimums)
    total = min(max(required, available_cm), limit_cm)
    return TablePlan(
        widths=_distribute(minimums, preferred, total),
        total_cm=total,
        size_pt=size_pt,
        overflow=required > total + 0.01,
    )


def _column_demands(block: Table, size_pt: float) -> tuple[list[float], list[float]]:
    char_cm = size_pt * _CHAR_WIDTH_RATIO
    minimums, preferred = [], []
    for index in range(len(block.alignments)):
        cells = [(block.header[index], _BOLD_FACTOR)] + [(row[index], 1.0) for row in block.rows]
        longest_word = max((_longest_word(runs) * factor for runs, factor in cells), default=1.0)
        longest_text = max((min(len(_measured_text(runs)), _MAX_PREFERRED_CHARS) * factor
                            for runs, factor in cells), default=1.0)
        lower = longest_word * char_cm + 2 * _CELL_PADDING_CM
        minimums.append(lower)
        preferred.append(max(longest_text * char_cm + 2 * _CELL_PADDING_CM, lower))
    return minimums, preferred


def _minimum_chars(block: Table) -> float:
    """Characters the narrowest acceptable layout needs, summed over all columns."""
    total = 0.0
    for index in range(len(block.alignments)):
        cells = [(block.header[index], _BOLD_FACTOR)] + [(row[index], 1.0) for row in block.rows]
        total += max((_longest_word(runs) * factor for runs, factor in cells), default=1.0)
    return total


def _longest_word(runs: list[Inline]) -> float:
    words = _measured_text(runs).split()
    return float(max((len(word) for word in words), default=1))


def _apply_widths(table, widths: list[float], total_cm: float) -> None:
    _set_table_width(table, 'dxa', str(int(Cm(total_cm).twips)))
    grid = table._tbl.find(qn('w:tblGrid'))
    for index, width_cm in enumerate(widths):
        if grid is not None and index < len(grid):
            grid[index].set(qn('w:w'), str(int(Cm(width_cm).twips)))
        for row in table.rows:
            row.cells[index].width = Cm(width_cm)


def _full_width(table) -> None:
    _set_table_width(table, 'pct', '5000')


def _set_table_width(table, width_type: str, value: str) -> None:
    properties = table._tbl.tblPr
    width = properties.find(qn('w:tblW'))
    if width is None:
        width = etree.SubElement(properties, qn('w:tblW'))
    width.set(qn('w:type'), width_type)
    width.set(qn('w:w'), value)


def _switch_orientation(document, landscape: bool) -> None:
    """Start a new section in the requested orientation, keeping the margins."""
    section = document.add_section(WD_SECTION.NEW_PAGE)
    width, height = section.page_width, section.page_height
    is_landscape = width is not None and height is not None and width > height
    if is_landscape != landscape:
        section.page_width, section.page_height = height, width
    section.orientation = WD_ORIENT.LANDSCAPE if landscape else WD_ORIENT.PORTRAIT


def _caption_hint(block: Table) -> str:
    return ' | '.join(_measured_text(cell) for cell in block.header)[:60]


def _measured_text(runs: list[Inline]) -> str:
    """Approximate the rendered cell text; equations are measured after stripping LaTeX."""
    parts = []
    for run in runs:
        if isinstance(run, TextRun):
            parts.append(run.text)
        elif isinstance(run, MathRun):
            parts.append(latex_to_plain(run.latex))
        else:
            parts.append(' ')
    return ''.join(parts)


def _distribute(minimums: list[float], preferred: list[float], available_cm: float) -> list[float]:
    required = sum(minimums)
    if required >= available_cm:
        scale = available_cm / required
        return [value * scale for value in minimums]
    slack = available_cm - required
    growth = [pref - low for pref, low in zip(preferred, minimums)]
    total_growth = sum(growth)
    if total_growth <= 0:
        share = slack / len(minimums)
        return [value + share for value in minimums]
    factor = min(1.0, slack / total_growth)
    widths = [low + gain * factor for low, gain in zip(minimums, growth)]
    leftover = available_cm - sum(widths)
    if leftover > 0:
        share = leftover / len(widths)
        widths = [value + share for value in widths]
    return widths


def _apply_table_style(table, style_name: str, warnings: list[str]) -> None:
    try:
        table.style = style_name
    except KeyError:
        message = f'стиль таблиці "{style_name}" відсутній у шаблоні'
        if message not in warnings:
            warnings.append(message)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    properties = table._tbl.tblPr
    layout = properties.find(qn('w:tblLayout'))
    if layout is None:
        layout = etree.SubElement(properties, qn('w:tblLayout'))
    layout.set(qn('w:type'), 'fixed')


def _repeat_header(row) -> None:
    properties = row._tr.get_or_add_trPr()
    if properties.find(qn('w:tblHeader')) is None:
        etree.SubElement(properties, qn('w:tblHeader'))


# --------------------------------------------------------------------- styles


def _register_styles(document, style: StyleConfig) -> None:
    body_alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if style.justify else WD_ALIGN_PARAGRAPH.LEFT

    _define(document, 'Article Body', style, alignment=body_alignment,
            first_line_indent=Cm(style.first_line_indent_cm))
    _define(document, 'Article Title', style, alignment=WD_ALIGN_PARAGRAPH.CENTER, bold=True,
            size_pt=style.title_size_pt, space_before=Pt(6), space_after=Pt(6))
    _define(document, 'Article Authors', style, alignment=WD_ALIGN_PARAGRAPH.CENTER, bold=True,
            space_after=Pt(6))
    _define(document, 'Article UDC', style, alignment=WD_ALIGN_PARAGRAPH.LEFT, bold=True,
            space_after=Pt(6))
    for level in range(1, 5):
        _define(document, f'Article Heading {level}', style, alignment=body_alignment,
                bold=style.heading_bold,
                first_line_indent=Cm(style.first_line_indent_cm),
                space_before=Pt(style.heading_space_before_pt / level),
                space_after=Pt(style.heading_space_after_pt),
                keep_with_next=True)
    _define(document, 'Article Equation', style, alignment=WD_ALIGN_PARAGRAPH.CENTER,
            space_before=Pt(6), space_after=Pt(6))
    _define(document, 'Article Figure', style, alignment=WD_ALIGN_PARAGRAPH.CENTER,
            space_before=Pt(6), keep_with_next=True)
    _define(document, 'Article Caption', style, alignment=WD_ALIGN_PARAGRAPH.CENTER,
            size_pt=style.caption_size_pt, italic=True, space_after=Pt(6))
    _define(document, 'Article Table Caption', style, alignment=WD_ALIGN_PARAGRAPH.CENTER,
            size_pt=style.caption_size_pt, space_before=Pt(6), keep_with_next=True)
    _define(document, 'Article Table Cell', style, alignment=WD_ALIGN_PARAGRAPH.CENTER,
            size_pt=style.table_font_size_pt, line_spacing=1.0, space_after=Pt(0))
    _define(document, 'Article List', style, alignment=body_alignment,
            left_indent=Cm(style.list_indent_cm),
            first_line_indent=Cm(-style.list_indent_cm + 0.25))
    _define(document, 'Article Reference', style, alignment=body_alignment,
            left_indent=Cm(style.reference_hanging_indent_cm),
            first_line_indent=Cm(-style.reference_hanging_indent_cm))
    _define(document, 'Article Code', style, alignment=WD_ALIGN_PARAGRAPH.LEFT,
            font=_MONOSPACE, size_pt=style.table_font_size_pt, line_spacing=1.0)


def _define(document, name: str, style: StyleConfig, *,
            font: str | None = None, size_pt: float | None = None,
            bold: bool = False, italic: bool = False,
            alignment=None, line_spacing: float | None = None,
            space_before=None, space_after=None,
            first_line_indent=None, left_indent=None,
            keep_with_next: bool = False):
    from docx.enum.style import WD_STYLE_TYPE

    if name in document.styles:
        target = document.styles[name]
    else:
        target = document.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        target.base_style = document.styles['Normal']
    target.quick_style = True

    face = font or style.font
    target.font.name = face
    target.font.size = Pt(size_pt if size_pt else style.size_pt)
    target.font.bold = bold
    target.font.italic = italic
    _set_style_fonts(target, face, style.lang)

    fmt = target.paragraph_format
    fmt.alignment = alignment
    fmt.line_spacing = line_spacing if line_spacing is not None else style.line_spacing
    fmt.space_before = space_before if space_before is not None else Pt(0)
    fmt.space_after = space_after if space_after is not None else Pt(style.space_after_pt)
    fmt.first_line_indent = first_line_indent if first_line_indent is not None else Cm(0)
    fmt.left_indent = left_indent if left_indent is not None else Cm(0)
    fmt.keep_with_next = keep_with_next
    fmt.widow_control = True
    return target


def _set_style_fonts(target, face: str, lang: str) -> None:
    rpr = target.element.get_or_add_rPr()
    fonts = rpr.find(qn('w:rFonts'))
    if fonts is None:
        fonts = etree.SubElement(rpr, qn('w:rFonts'))
    for attribute in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
        fonts.set(qn(attribute), face)
    language = rpr.find(qn('w:lang'))
    if language is None:
        language = etree.SubElement(rpr, qn('w:lang'))
    language.set(qn('w:val'), lang)


def _set_run_fonts(run, face: str) -> None:
    rpr = run._element.get_or_add_rPr()
    fonts = rpr.find(qn('w:rFonts'))
    if fonts is None:
        fonts = etree.SubElement(rpr, qn('w:rFonts'))
    for attribute in ('w:ascii', 'w:hAnsi', 'w:cs'):
        fonts.set(qn(attribute), face)


# ---------------------------------------------------------------------- misc


def _plainify_title(paragraph) -> None:
    """Cancel chapter numbering and the forced page break a book title style carries.

    Springer's ``Main_Title`` is written for numbered book chapters; a journal
    article needs the same look without the "1" prefix and the page break.
    """
    properties = paragraph._p.get_or_add_pPr()
    properties.get_or_add_pageBreakBefore().set(qn('w:val'), '0')
    numbering = properties.get_or_add_numPr()
    for tag in ('w:ilvl', 'w:numId'):
        element = numbering.find(qn(tag))
        if element is None:
            element = etree.SubElement(numbering, qn(tag))
        element.set(qn('w:val'), '0')


def _clear_body(document) -> None:
    """Drop the template's sample content but keep styles and section setup."""
    body = document.element.body
    for child in list(body):
        if child.tag == qn('w:sectPr'):
            continue
        body.remove(child)


def _has_content(document) -> bool:
    body = document.element.body
    return any(child.tag != qn('w:sectPr') for child in body)
