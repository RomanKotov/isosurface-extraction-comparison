"""Inline markdown parsing: emphasis, code, links, LaTeX math, soft breaks."""
from __future__ import annotations

import re

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class TextRun:
    text: str
    bold: bool = False
    italic: bool = False
    code: bool = False


@dataclass(frozen=True)
class MathRun:
    latex: str


@dataclass(frozen=True)
class LineBreak:
    pass


Inline = TextRun | MathRun | LineBreak

SOFT_BREAK = '\x00'

_PATTERNS = (
    ('break', re.compile(r'<br\s*/?>', re.I)),
    ('html_anchor', re.compile(r'<a\s+[^>]*>(?:</a>)?|<span\s+[^>]*>(?:</span>)?', re.I)),
    ('code', re.compile(r'`([^`]+)`')),
    ('math', re.compile(r'(?<!\$)\$(?!\$)(.+?)(?<!\\)\$(?!\$)', re.S)),
    ('bold', re.compile(r'\*\*(.+?)\*\*', re.S)),
    ('italic', re.compile(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', re.S)),
    ('link', re.compile(r'\[([^\]]*)\]\(([^)]+)\)')),
)

_ESCAPE = re.compile(r'\\([\\`*_{}\[\]()#+\-.!|<>~$])')


def normalize_paragraph(text: str) -> str:
    """Collapse a raw paragraph into a single line, keeping markdown soft breaks."""
    lines = text.split('\n')
    parts: list[str] = []
    for index, line in enumerate(lines):
        hard_break = line.endswith('  ') or line.rstrip().endswith('\\')
        stripped = line.rstrip().rstrip('\\').strip()
        if index and not (parts and parts[-1] == SOFT_BREAK):
            parts.append(' ')
        parts.append(stripped)
        if hard_break and index < len(lines) - 1:
            parts.append(SOFT_BREAK)
    return ''.join(parts).strip()


def parse_inline(text: str, bold: bool = False, italic: bool = False) -> list[Inline]:
    """Split markdown text into styled runs, math fragments and soft breaks."""
    result: list[Inline] = []
    position = 0
    while position < len(text):
        match, kind = _first_match(text, position)
        if match is None:
            _emit_text(result, text[position:], bold, italic)
            break
        _emit_text(result, text[position:match.start()], bold, italic)
        if kind == 'break':
            result.append(LineBreak())
        elif kind == 'html_anchor':
            pass
        elif kind == 'code':
            result.append(TextRun(_unescape(match.group(1)), bold=bold, italic=italic, code=True))
        elif kind == 'math':
            result.append(MathRun(match.group(1).strip()))
        elif kind == 'bold':
            result.extend(parse_inline(match.group(1), bold=True, italic=italic))
        elif kind == 'italic':
            result.extend(parse_inline(match.group(1), bold=bold, italic=True))
        elif kind == 'link':
            label = match.group(1).strip() or match.group(2).strip()
            result.extend(parse_inline(label, bold=bold, italic=italic))
        position = match.end()
    return _merge(result)


def _first_match(text: str, position: int):
    best = None
    best_kind = None
    for kind, pattern in _PATTERNS:
        match = pattern.search(text, position)
        if match is None:
            continue
        if best is None or match.start() < best.start():
            best, best_kind = match, kind
    return best, best_kind


def _emit_text(result: list[Inline], chunk: str, bold: bool, italic: bool) -> None:
    if not chunk:
        return
    for index, piece in enumerate(chunk.split(SOFT_BREAK)):
        if index:
            result.append(LineBreak())
        if piece:
            result.append(TextRun(_unescape(piece), bold=bold, italic=italic))


def _unescape(text: str) -> str:
    return _ESCAPE.sub(r'\1', text)


def _merge(runs: list[Inline]) -> list[Inline]:
    """Glue adjacent text runs that share formatting to keep the docx tidy."""
    merged: list[Inline] = []
    for run in runs:
        previous = merged[-1] if merged else None
        if (isinstance(run, TextRun) and isinstance(previous, TextRun)
                and (previous.bold, previous.italic, previous.code)
                == (run.bold, run.italic, run.code)):
            merged[-1] = replace(previous, text=previous.text + run.text)
        else:
            merged.append(run)
    return merged


def plain_text(runs: list[Inline]) -> str:
    parts = []
    for run in runs:
        if isinstance(run, TextRun):
            parts.append(run.text)
        elif isinstance(run, MathRun):
            parts.append(run.latex)
        else:
            parts.append(' ')
    return ''.join(parts)
