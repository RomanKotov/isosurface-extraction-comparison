"""Renders parsed markdown blocks into a LaTeX manuscript.

The docx renderer binds every manuscript element to a style of the Word template;
here the same roles (title, authors, abstract, keywords, ...) are bound to LaTeX
macros declared in the preamble.  Swapping in a publisher class therefore means
redefining a handful of macros in ``[latex]`` — the renderer itself stays put.
"""
from __future__ import annotations

import os
import re

from pathlib import Path

from . import semantics
from .config import LatexConfig, StyleConfig, StyleSet
from .inline import Inline, LineBreak, MathRun, TextRun, plain_text
from .mdparse import (Block, CodeBlock, DisplayMath, Figure, Heading, ListBlock,
                      Paragraph, Rule, Table)

_SECTIONS = ('section', 'subsection', 'subsubsection', 'paragraph')
_ALIGNMENT = {'left': 'l', 'center': 'c', 'right': 'r'}
_NBSP = '\x01'

_SPECIAL = {
    '\\': r'\textbackslash{}',
    '&': r'\&',
    '%': r'\%',
    '$': r'\$',
    '#': r'\#',
    '_': r'\_',
    '{': r'\{',
    '}': r'\}',
    '~': r'\textasciitilde{}',
    '^': r'\textasciicircum{}',
}
_URL = re.compile(r'https?://[^\s<>«»]+')
_URL_TAIL = '.,;:)]»'

#: Definitions emitted for the element roles when ``define_macros`` is on.
MACRO_BODIES = {
    'udc': r'\newcommand{\%s}[1]{{\noindent\bfseries #1\par}\medskip}',
    'title': r'\newcommand{\%s}[1]{{\centering\large\bfseries #1\par}\smallskip}',
    'authors': r'\newcommand{\%s}[1]{{\centering\bfseries #1\par}}',
    'affiliation': r'\newcommand{\%s}[1]{{\centering\itshape\small #1\par}\smallskip}',
    'keywords': r'\newcommand{\%s}[1]{{\noindent #1\par}\medskip}',
    'abstract': (r'\newenvironment{%s}'
                 r'{\par\small\itshape\setlength{\parindent}{0pt}}{\par\medskip}'),
}


class LatexWriter:
    """Builds a single .tex file out of markdown blocks, section by section."""

    def __init__(self, latex: LatexConfig, style: StyleConfig, styleset: StyleSet,
                 include_figures: bool = True, include_tables: bool = True,
                 heading_offset: int = 0, assets_root: Path | None = None,
                 output_dir: Path | None = None):
        self.latex = latex
        self.style = style
        self.styleset = styleset
        self.include_figures = include_figures
        self.include_tables = include_tables
        self.heading_offset = heading_offset
        self.assets_root = assets_root
        self.output_dir = output_dir
        self.warnings: list[str] = []

        self.body: list[str] = []
        self._front_matter = True
        self._in_references = False
        self._pending_authors = False
        self._pending_abstract = False
        self._pending_affiliation = False
        self._bibliography_open = False
        self._references_title = ''
        self._reference_index = 0

    # ------------------------------------------------------------------ public

    def add_section(self, blocks: list[Block], page_break: bool = False) -> None:
        if page_break and self.body:
            self._close_bibliography()
            self._emit(r'\clearpage')
        self._render_blocks(blocks)

    def save(self, path: Path, metadata: dict | None = None) -> None:
        self._close_bibliography()
        document = '\n'.join(self._preamble(metadata or {})
                             + ['', r'\begin{document}', '']
                             + self.body
                             + ['', r'\end{document}', ''])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(document, encoding='utf-8')

    # --------------------------------------------------------------- preamble

    def _preamble(self, metadata: dict) -> list[str]:
        latex = self.latex
        options = ','.join(latex.class_options)
        head = [
            '% Згенеровано tools/build_article.py — правити треба markdown у article/,',
            '% а оформлення — у розділі [latex] файлу article-build.toml.',
            '%% Рекомендований компілятор: %s' % latex.engine,
            r'\documentclass[%s]{%s}' % (options, latex.documentclass) if options
            else r'\documentclass{%s}' % latex.documentclass,
        ]
        head += self._language_packages()
        head += [
            r'\usepackage{amsmath}',
            r'\usepackage{amssymb}',
            r'\usepackage{graphicx}',
            r'\usepackage{booktabs}',
            r'\usepackage{array}',
            r'\usepackage{rotating}',
            r'\usepackage{caption}',
            r'\usepackage{setspace}',
            r'\usepackage{url}',
        ]
        if latex.geometry:
            head.append(r'\usepackage[%s]{geometry}' % latex.geometry)
        head += [r'\usepackage{%s}' % name for name in latex.packages]

        head.append('')
        head.append('% --- типографіка (узгоджена з [style] складальника) ---')
        head.append(r'\setstretch{%.2f}' % self.style.line_spacing)
        head.append(r'\setlength{\parindent}{%.2fcm}' % self.style.first_line_indent_cm)
        head.append(r'\setlength{\parskip}{%.1fpt}' % self.style.space_after_pt)
        if not self.style.justify:
            head.append(r'\raggedright')
        if not latex.number_captions:
            head.append(r'\captionsetup{labelformat=empty,labelsep=none}')
        if self._explicit_font_size():
            head.append(r'\AtBeginDocument{\fontsize{%.1f}{%.1f}\selectfont}'
                        % (self.style.size_pt, self.style.size_pt * 1.2))

        if latex.define_macros:
            head.append('')
            head.append('% --- ролі елементів рукопису (аналог стилів Word-шаблону) ---')
            for role, template in MACRO_BODIES.items():
                head.append(template % latex.macro_for(role))

        if latex.preamble.strip():
            head.append('')
            head.append('% --- додатковий преамбул з article-build.toml ---')
            head.append(latex.preamble.strip())

        title = metadata.get('title')
        author = metadata.get('author')
        if title or author:
            head.append('')
            if title:
                head.append(r'\title{%s}' % escape(str(title)))
            if author:
                head.append(r'\author{%s}' % escape(str(author)))
            head.append(r'\date{}')
        return head

    def _language_packages(self) -> list[str]:
        latex = self.latex
        if latex.engine in ('xelatex', 'lualatex'):
            lines = [r'\usepackage{fontspec}', r'\usepackage{polyglossia}',
                     r'\setmainlanguage{%s}' % latex.language]
            if latex.other_language:
                lines.append(r'\setotherlanguage{%s}' % latex.other_language)
            if latex.main_font:
                lines.append(r'\setmainfont{%s}' % latex.main_font)
            if latex.mono_font:
                lines.append(r'\setmonofont{%s}' % latex.mono_font)
            return lines
        lines = [r'\usepackage[T2A,T1]{fontenc}', r'\usepackage[utf8]{inputenc}']
        languages = [name for name in (latex.other_language, latex.language) if name]
        lines.append(r'\usepackage[%s]{babel}' % ','.join(languages))
        return lines

    def _explicit_font_size(self) -> bool:
        """The class only offers 10/11/12 pt; anything else has to be set by hand."""
        declared = {'10pt', '11pt', '12pt'} & set(self.latex.class_options)
        base = float(next(iter(declared))[:-2]) if declared else 10.0
        return abs(self.style.size_pt - base) > 0.01

    # ----------------------------------------------------------------- blocks

    def _render_blocks(self, blocks: list[Block]) -> None:
        index = 0
        while index < len(blocks):
            block = blocks[index]
            following = blocks[index + 1] if index + 1 < len(blocks) else None
            if semantics.is_table_caption(block) and isinstance(following, Table):
                self._render_table(following, caption=block)
                index += 2
                continue
            if isinstance(block, Figure) and semantics.is_figure_caption(following):
                self._render_figure(block, caption=following)
                index += 2
                continue
            self._render_block(block)
            index += 1

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
        if semantics.NUMBERED_HEADING.match(heading.text):
            self._front_matter = False
        self._pending_abstract = bool(semantics.ABSTRACT_HEADING.match(heading.text))
        self._pending_affiliation = False

        if semantics.REFERENCE_HEADING.search(heading.text):
            self._in_references = True
            self._references_title = plain_text(heading.runs).strip()
            self._pending_authors = False
            if self.latex.bibliography == 'thebibliography':
                return                      # thebibliography prints its own heading
        elif self._in_references:
            self._close_bibliography()
            self._in_references = False

        if heading.level == 1 and self._front_matter \
                and not semantics.NUMBERED_HEADING.match(heading.text):
            self._emit(r'\%s{%s}' % (self.latex.macro_for('title'), self._runs(heading.runs)))
            self._pending_authors = True
            return

        runs = heading.runs
        if self.styleset.strip_heading_numbers:
            runs = semantics.strip_leading_number(runs)
        level = max(1, min(len(_SECTIONS), heading.level + self.heading_offset))
        command = _SECTIONS[level - 1]
        star = '' if self.latex.number_headings else '*'
        self._emit('')
        self._emit(r'\%s%s{%s}' % (command, star, self._runs(runs)))
        self._pending_authors = False

    def _render_paragraph(self, block: Paragraph) -> None:
        if not block.runs:
            return
        role = self._paragraph_role(block)
        self._pending_authors = False
        self._pending_abstract = False
        self._pending_affiliation = role in ('authors', 'affiliation')
        text = self._runs(block.runs)

        if role == 'reference':
            self._write_reference(text)
        elif role == 'abstract':
            name = self.latex.macro_for('abstract')
            self._emit(r'\begin{%s}' % name)
            self._emit(text)
            self._emit(r'\end{%s}' % name)
        elif role in ('title', 'authors', 'affiliation', 'udc', 'keywords'):
            self._emit(r'\%s{%s}' % (self.latex.macro_for(role), text))
        elif role in ('figure_caption', 'table_caption'):
            # a caption that lost its figure/table (--no-figures) stays as plain text
            self._emit('')
            self._emit(r'{\centering\small %s\par}' % text)
        else:
            self._emit('')
            self._emit(text)

    def _paragraph_role(self, block: Paragraph) -> str:
        if block.kind in ('figure_caption', 'table_caption'):
            return block.kind
        text = plain_text(block.runs)
        if self._front_matter and semantics.UDC.match(text):
            return 'udc'
        if self._pending_authors and semantics.only_bold(block.runs):
            return 'authors'
        if self._pending_affiliation and self._front_matter:
            return 'affiliation'
        if self._pending_abstract:
            return 'abstract'
        if semantics.KEYWORDS.match(text):
            return 'keywords'
        if self._in_references:
            return 'reference'
        return 'body'

    def _render_equation(self, block: DisplayMath) -> None:
        environment = 'equation' if self.latex.number_equations else 'equation*'
        self._emit(r'\begin{%s}' % environment)
        self._emit('  ' + block.latex + (block.tail or ''))
        self._emit(r'\end{%s}' % environment)

    def _render_figure(self, block: Figure, caption: Paragraph | None = None) -> None:
        if not self.include_figures:
            if caption is not None:
                self._render_paragraph(caption)
            return
        path = self._resolve_asset(block.path)
        if path is None:
            self.warnings.append(f'не знайдено зображення: {block.path}')
            return
        runs = caption.runs if caption is not None else block.runs
        self._emit('')
        self._emit(r'\begin{figure}[%s]' % self.latex.figure_placement)
        self._emit(r'  \centering')
        self._emit(r'  \includegraphics[width=%s]{%s}' % (self.latex.figure_width, path))
        if runs:
            self._emit(r'  \caption{%s}' % self._runs(runs, protect_breaks=True))
        self._emit(r'\end{figure}')

    def _resolve_asset(self, reference: str) -> str | None:
        """Path to the image as written into the .tex (relative to the output file)."""
        candidate = Path(reference)
        resolved = None
        if self.assets_root is not None and (self.assets_root / candidate).is_file():
            resolved = (self.assets_root / candidate).resolve()
        elif candidate.is_file():
            resolved = candidate.resolve()
        if resolved is None:
            return None
        if self.output_dir is None:
            return resolved.as_posix()
        try:
            relative = os.path.relpath(resolved, self.output_dir.resolve())
        except ValueError:                  # different drives — keep it absolute
            return resolved.as_posix()
        return Path(relative).as_posix()

    def _render_table(self, block: Table, caption: Paragraph | None = None) -> None:
        if not self.include_tables:
            if caption is not None:
                self._render_paragraph(caption)
            return
        wide = (self.styleset.landscape_wide_tables
                and len(block.alignments) > self.latex.wide_table_columns)
        environment = 'sidewaystable' if wide else 'table'
        columns = ''.join(_ALIGNMENT.get(name, 'l') for name in block.alignments)
        self._emit('')
        self._emit(r'\begin{%s}[%s]' % (environment, self.latex.table_placement))
        self._emit(r'  \centering')
        if caption is not None:
            self._emit(r'  \caption{%s}' % self._runs(caption.runs, protect_breaks=True))
        size = self._table_size()
        if size:
            self._emit('  ' + size)
        resize = wide and self.latex.wide_table_resize
        if resize:
            # rotated tables are laid out along the page height, not its width
            self._emit(r'  \resizebox{\textheight}{!}{%')
        self._emit(r'  \begin{tabular}{%s}' % columns)
        self._emit(r'    \toprule')
        self._emit('    ' + self._row(block.header, bold=True))
        self._emit(r'    \midrule')
        for row in block.rows:
            self._emit('    ' + self._row(row))
        self._emit(r'    \bottomrule')
        self._emit(r'  \end{tabular}')
        if resize:
            self._emit('  }')
        self._emit(r'\end{%s}' % environment)

    def _table_size(self) -> str:
        """Tables are set smaller than the body, as in the docx build."""
        ratio = self.style.table_font_size_pt / max(self.style.size_pt, 1.0)
        if ratio >= 0.98:
            return ''
        return r'\footnotesize' if ratio < 0.8 else r'\small'

    def _row(self, cells: list[list[Inline]], bold: bool = False) -> str:
        rendered = []
        for cell in cells:
            text = self._runs(cell)
            rendered.append(r'\textbf{%s}' % text if bold and text else text)
        return ' & '.join(rendered) + r' \\'

    def _render_list(self, block: ListBlock) -> None:
        if self._in_references:
            for item in block.items:
                self._render_reference_item(item)
            return
        environment = 'enumerate' if block.ordered else 'itemize'
        self._emit('')
        self._emit(r'\begin{%s}' % environment)
        for item in block.items:
            if not item.blocks:
                continue
            first, *rest = item.blocks
            if isinstance(first, Paragraph):
                self._emit(r'  \item %s' % self._runs(first.runs))
            else:
                self._emit(r'  \item')
                self._render_block(first)
            self._render_blocks(rest)
        self._emit(r'\end{%s}' % environment)

    def _render_reference_item(self, item) -> None:
        if not item.blocks:
            return
        first, *rest = item.blocks
        if isinstance(first, Paragraph):
            self._write_reference(self._runs(first.runs), marker=item.marker)
        for block in rest:
            self._render_block(block)

    def _write_reference(self, text: str, marker: str = '') -> None:
        if self.latex.bibliography != 'thebibliography':
            self._emit('')
            self._emit((marker + ' ' if marker else '') + text)
            return
        self._open_bibliography()
        self._reference_index += 1
        number = marker.rstrip('.') or str(self._reference_index)
        if number.isdigit() and int(number) != self._reference_index:
            self.warnings.append(
                f'нумерація джерел збилася: у списку "{number}", за порядком '
                f'{self._reference_index} — посилання [N] у тексті можуть не збігтися')
        self._emit(r'  \bibitem{ref%s} %s' % (number, text))

    def _open_bibliography(self) -> None:
        if self._bibliography_open:
            return
        if self._references_title:
            self._emit('')
            self._emit(r'\renewcommand{\refname}{%s}' % escape(self._references_title))
        self._emit(r'\begin{thebibliography}{99}')
        self._bibliography_open = True

    def _close_bibliography(self) -> None:
        if not self._bibliography_open:
            return
        self._emit(r'\end{thebibliography}')
        self._bibliography_open = False

    def _render_code(self, block: CodeBlock) -> None:
        environment = self.latex.code_environment
        self._emit('')
        self._emit(r'\begin{%s}' % environment)
        for line in block.text.split('\n'):
            self.body.append(line)
        self._emit(r'\end{%s}' % environment)

    # ------------------------------------------------------------------- runs

    def _runs(self, runs: list[Inline], protect_breaks: bool = False) -> str:
        parts: list[str] = []
        for item in runs:
            if isinstance(item, LineBreak):
                # inside a caption the break has to survive the moving argument
                parts.append('\\protect\\\\\n' if protect_breaks else '\\\\\n')
            elif isinstance(item, MathRun):
                parts.append('$%s$' % item.latex)
            else:
                parts.append(_styled(item))
        return ''.join(parts).strip()

    def _emit(self, line: str) -> None:
        if line == '' and (not self.body or self.body[-1] == ''):
            return
        self.body.append(line)


def _styled(item: TextRun) -> str:
    text = escape(item.text)
    if item.code:
        text = r'\texttt{%s}' % text
    if item.bold:
        text = r'\textbf{%s}' % text
    if item.italic:
        text = r'\textit{%s}' % text
    return text


def escape(text: str) -> str:
    """Escape LaTeX specials, keeping bare URLs inside url{} so they can break."""
    text = text.replace(' ', _NBSP)
    parts: list[str] = []
    position = 0
    for match in _URL.finditer(text):
        url = match.group(0)
        tail = ''
        while url and url[-1] in _URL_TAIL:
            tail = url[-1] + tail
            url = url[:-1]
        parts.append(_escape_plain(text[position:match.start()]))
        parts.append(r'\url{%s}' % url)
        parts.append(_escape_plain(tail))
        position = match.end()
    parts.append(_escape_plain(text[position:]))
    return ''.join(parts).replace(_NBSP, '~')


def _escape_plain(text: str) -> str:
    return ''.join(_SPECIAL.get(character, character) for character in text)
