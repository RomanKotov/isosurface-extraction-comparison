"""Block-level markdown parsing for the manuscript subset used in article/*.md."""
from __future__ import annotations

import re

from dataclasses import dataclass, field

from .inline import Inline, TextRun, normalize_paragraph, parse_inline, plain_text


@dataclass
class Heading:
    level: int
    runs: list[Inline]
    text: str


@dataclass
class Paragraph:
    runs: list[Inline]
    kind: str = 'body'          # body | figure_caption | table_caption


@dataclass
class DisplayMath:
    latex: str
    tail: str = ''              # trailing punctuation kept outside the equation


@dataclass
class Figure:
    path: str
    runs: list[Inline]


@dataclass
class Table:
    header: list[list[Inline]]
    rows: list[list[list[Inline]]]
    alignments: list[str]


@dataclass
class ListItem:
    marker: str
    blocks: list['Block'] = field(default_factory=list)


@dataclass
class ListBlock:
    ordered: bool
    items: list[ListItem]


@dataclass
class CodeBlock:
    text: str


@dataclass
class Rule:
    pass


Block = Heading | Paragraph | DisplayMath | Figure | Table | ListBlock | CodeBlock | Rule

_COMMENT = re.compile(r'<!--.*?-->', re.S)
_HEADING = re.compile(r'^(#{1,6})\s+(.*)$')
_RULE = re.compile(r'^\s*(?:-{3,}|\*{3,}|_{3,})\s*$')
_FENCE = re.compile(r'^\s*(`{3,}|~{3,})(.*)$')
_FIGURE = re.compile(r'^!\[(?P<alt>.*?)\]\((?P<path>[^)]+)\)\s*$')
_ORDERED = re.compile(r'^(\s*)(\d+)[.)]\s+(.*)$')
_UNORDERED = re.compile(r'^(\s*)[-*+–—]\s+(.*)$')
_TABLE_ROW = re.compile(r'^\s*\|.*\|\s*$')
_TABLE_SEPARATOR = re.compile(r'^\s*\|[\s:|-]+\|\s*$')
_DISPLAY_MATH = re.compile(r'^\s*\$\$')

_FIGURE_CAPTION = re.compile(r'^\s*\*+\s*(?:рис|fig)', re.I)
_TABLE_CAPTION = re.compile(r'^\s*\*+\s*(?:табл|table)', re.I)


def parse_markdown(text: str) -> list[Block]:
    text = _COMMENT.sub('', text.replace('\r\n', '\n').replace('﻿', ''))
    return _tag_captions(_parse_lines(text.split('\n')))


def _parse_lines(lines: list[str]) -> list[Block]:
    blocks: list[Block] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        fence = _FENCE.match(line)
        if fence:
            index, block = _read_code(lines, index, fence.group(1))
            blocks.append(block)
            continue

        heading = _HEADING.match(line)
        if heading:
            title = heading.group(2).strip().rstrip('#').strip()
            blocks.append(Heading(len(heading.group(1)), parse_inline(title), title))
            index += 1
            continue

        if _RULE.match(line):
            blocks.append(Rule())
            index += 1
            continue

        if _DISPLAY_MATH.match(line):
            index, block = _read_display_math(lines, index)
            blocks.append(block)
            continue

        figure = _FIGURE.match(line.strip())
        if figure:
            blocks.append(Figure(figure.group('path').strip(),
                                 parse_inline(figure.group('alt').strip())))
            index += 1
            continue

        if _is_table_start(lines, index):
            index, block = _read_table(lines, index)
            blocks.append(block)
            continue

        if _ORDERED.match(line) or _UNORDERED.match(line):
            index, block = _read_list(lines, index)
            blocks.append(block)
            continue

        index, block = _read_paragraph(lines, index)
        blocks.append(block)
    return blocks


def _is_table_start(lines: list[str], index: int) -> bool:
    return bool(_TABLE_ROW.match(lines[index])
                and index + 1 < len(lines)
                and _TABLE_SEPARATOR.match(lines[index + 1]))


def _read_code(lines: list[str], index: int, fence: str) -> tuple[int, CodeBlock]:
    collected: list[str] = []
    index += 1
    while index < len(lines) and not lines[index].strip().startswith(fence):
        collected.append(lines[index])
        index += 1
    return index + 1, CodeBlock('\n'.join(collected))


def _read_display_math(lines: list[str], index: int) -> tuple[int, DisplayMath]:
    stripped = lines[index].strip()
    body = stripped[2:]
    if body.rstrip().endswith('$$'):
        return index + 1, _display_math(body.rstrip()[:-2])
    collected = [body]
    index += 1
    while index < len(lines) and '$$' not in lines[index]:
        collected.append(lines[index])
        index += 1
    if index < len(lines):
        collected.append(lines[index].split('$$')[0])
        index += 1
    return index, _display_math('\n'.join(collected))


def _display_math(raw: str) -> DisplayMath:
    latex = raw.strip()
    tail = ''
    while latex and latex[-1] in ',.;':
        tail = latex[-1] + tail
        latex = latex[:-1].rstrip()
    return DisplayMath(latex, tail)


def _read_table(lines: list[str], index: int) -> tuple[int, Table]:
    header = _split_row(lines[index])
    alignments = [_alignment(cell) for cell in _split_row(lines[index + 1])]
    index += 2
    rows: list[list[str]] = []
    while index < len(lines) and _TABLE_ROW.match(lines[index]):
        rows.append(_split_row(lines[index]))
        index += 1
    width = max([len(header)] + [len(row) for row in rows])
    alignments += ['left'] * (width - len(alignments))
    return index, Table(
        header=[parse_inline(cell) for cell in _pad(header, width)],
        rows=[[parse_inline(cell) for cell in _pad(row, width)] for row in rows],
        alignments=alignments[:width],
    )


def _split_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith('|'):
        stripped = stripped[1:]
    if stripped.endswith('|'):
        stripped = stripped[:-1]
    return [cell.strip() for cell in re.split(r'(?<!\\)\|', stripped)]


def _pad(row: list[str], width: int) -> list[str]:
    return row + [''] * (width - len(row))


def _alignment(cell: str) -> str:
    cell = cell.strip()
    if cell.startswith(':') and cell.endswith(':'):
        return 'center'
    if cell.endswith(':'):
        return 'right'
    return 'left'


def _read_list(lines: list[str], index: int) -> tuple[int, ListBlock]:
    ordered = bool(_ORDERED.match(lines[index]))
    items: list[ListItem] = []
    current: list[str] | None = None
    marker = ''
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            following = _next_nonblank(lines, index + 1)
            if current is None or following is None or not _continues_list(lines[following]):
                break
            current.append('')
            index += 1
            continue
        ordered_match = _ORDERED.match(line)
        unordered_match = _UNORDERED.match(line)
        is_new_item = (ordered_match or unordered_match) and not line[:1].isspace()
        if is_new_item:
            if current is not None:
                items.append(ListItem(marker, _parse_lines(current)))
            if ordered_match:
                marker = f'{ordered_match.group(2)}.'
                current = [ordered_match.group(3)]
            else:
                marker = ''
                current = [unordered_match.group(2)]
        elif current is not None:
            current.append(_dedent(line))
        else:
            break
        index += 1
    if current is not None:
        items.append(ListItem(marker, _parse_lines(current)))
    return index, ListBlock(ordered, items)


def _continues_list(line: str) -> bool:
    return bool(line[:1].isspace() or _ORDERED.match(line) or _UNORDERED.match(line))


def _next_nonblank(lines: list[str], index: int) -> int | None:
    while index < len(lines):
        if lines[index].strip():
            return index
        index += 1
    return None


def _dedent(line: str) -> str:
    return re.sub(r'^[ \t]{1,6}', '', line)


def _read_paragraph(lines: list[str], index: int) -> tuple[int, Paragraph]:
    collected: list[str] = []
    while index < len(lines):
        line = lines[index]
        if not line.strip() or (collected and _starts_block(lines, index)):
            break
        collected.append(line)
        index += 1
    return index, Paragraph(parse_inline(normalize_paragraph('\n'.join(collected))))


def _starts_block(lines: list[str], index: int) -> bool:
    line = lines[index]
    return bool(
        _HEADING.match(line)
        or _RULE.match(line)
        or _FENCE.match(line)
        or _DISPLAY_MATH.match(line)
        or _FIGURE.match(line.strip())
        or _is_table_start(lines, index)
        or _ORDERED.match(line)
        or _UNORDERED.match(line)
    )


def drop_sections(blocks: list[Block], patterns: tuple[str, ...]) -> list[Block]:
    """Remove internal working material (source-verification tables, notes).

    A block whose text matches one of ``patterns`` is dropped together with
    everything that follows it up to the next heading of the same or higher
    rank; a paragraph anchor drops everything up to the next heading.
    """
    if not patterns:
        return blocks
    compiled = [re.compile(pattern, re.I) for pattern in patterns]
    kept: list[Block] = []
    skip_until_level: int | None = None
    for block in blocks:
        if skip_until_level is not None:
            if isinstance(block, Heading) and block.level <= skip_until_level:
                skip_until_level = None
            else:
                continue
        text = block.text if isinstance(block, Heading) else (
            plain_text(block.runs) if isinstance(block, Paragraph) else '')
        if text and any(pattern.search(text) for pattern in compiled):
            skip_until_level = block.level if isinstance(block, Heading) else 6
            continue
        kept.append(block)
    return kept


def _tag_captions(blocks: list[Block]) -> list[Block]:
    """Mark ``*Рис. N ...*`` / ``*Таблиця N*`` paragraphs so they get caption styling."""
    for position, block in enumerate(blocks):
        if not isinstance(block, Paragraph):
            continue
        raw = _raw_text(block)
        if _FIGURE_CAPTION.match(raw):
            block.kind = 'figure_caption'
        elif _TABLE_CAPTION.match(raw):
            block.kind = 'table_caption'
        elif position and isinstance(blocks[position - 1], Figure):
            block.kind = 'figure_caption'
    return blocks


def _raw_text(paragraph: Paragraph) -> str:
    runs = paragraph.runs
    if not runs:
        return ''
    first = runs[0]
    prefix = '*' if isinstance(first, TextRun) and first.italic else ''
    return prefix + plain_text(runs)
