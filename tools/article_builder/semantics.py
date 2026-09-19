"""Manuscript element semantics shared by the docx and LaTeX renderers.

Both renderers have to answer the same questions about a parsed block — is this
the title, the authors line, an abstract, a caption, a reference entry — so the
recognition rules live here and each renderer only decides how to typeset them.
"""
from __future__ import annotations

import re

from .inline import Inline, TextRun
from .mdparse import Block, Paragraph

#: "УДК 004.92" / "UDC 004.92" line of the title page.
UDC = re.compile(r'^\s*(УДК|UDC)\b', re.I)
#: A heading that opens a numbered section ("1. Вступ") ends the front matter.
NUMBERED_HEADING = re.compile(r'^\s*\d')
#: Leading "2.1." of a heading, dropped when the template numbers headings itself.
HEADING_NUMBER = re.compile(r'^\s*\d+(?:\.\d+)*\.?\s+')
REFERENCE_HEADING = re.compile(r'(література|references|бібліограф)', re.I)
ABSTRACT_HEADING = re.compile(r'^\s*(резюме|анотація|abstract|summary)\b', re.I)
KEYWORDS = re.compile(r'^\s*(ключові слова|keywords|ключевые слова)\b', re.I)


def only_bold(runs: list[Inline]) -> bool:
    """True for a paragraph typeset entirely in bold — the authors line."""
    text_runs = [run for run in runs if isinstance(run, TextRun) and run.text.strip()]
    return bool(text_runs) and all(run.bold for run in text_runs)


def strip_leading_number(runs: list[Inline]) -> list[Inline]:
    """Drop a manual "2.1." prefix so template-numbered headings do not double up."""
    for index, run in enumerate(runs):
        if not isinstance(run, TextRun):
            break
        stripped = HEADING_NUMBER.sub('', run.text, count=1)
        if stripped != run.text:
            return list(runs[:index]) + [TextRun(stripped, run.bold, run.italic, run.code)] \
                + list(runs[index + 1:])
        if run.text.strip():
            break
    return runs


def is_table_caption(block: Block) -> bool:
    return isinstance(block, Paragraph) and block.kind == 'table_caption'


def is_figure_caption(block: Block) -> bool:
    return isinstance(block, Paragraph) and block.kind == 'figure_caption'
