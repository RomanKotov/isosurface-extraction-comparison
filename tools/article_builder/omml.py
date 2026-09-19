"""LaTeX -> OMML (Office Math Markup) conversion for Word equations.

MathML is produced by ``latex2mathml`` and then transformed to OMML with the
``MML2OMML.XSL`` stylesheet shipped with Microsoft Office.  When the stylesheet
cannot be located the converter degrades gracefully: callers get ``None`` back
and fall back to plain italic text.
"""
from __future__ import annotations

import glob
import os
import re

from pathlib import Path

from lxml import etree

M_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

XSL_ENV_VAR = 'MML2OMML_XSL'

XSL_GLOBS = (
    r'C:\Program Files\Microsoft Office\root\Office*\MML2OMML.XSL',
    r'C:\Program Files (x86)\Microsoft Office\root\Office*\MML2OMML.XSL',
    r'C:\Program Files\Microsoft Office\Office*\MML2OMML.XSL',
    r'C:\Program Files (x86)\Microsoft Office\Office*\MML2OMML.XSL',
    '/usr/lib/libreoffice/share/xslt/**/MML2OMML.XSL',
)


def find_xsl(explicit: str | Path | None = None) -> Path | None:
    candidates: list[str] = []
    if explicit:
        candidates.append(str(explicit))
    if os.environ.get(XSL_ENV_VAR):
        candidates.append(os.environ[XSL_ENV_VAR])
    candidates.append(str(Path(__file__).with_name('MML2OMML.XSL')))
    for path in candidates:
        if path and Path(path).is_file():
            return Path(path)
    for pattern in XSL_GLOBS:
        for match in sorted(glob.glob(pattern, recursive=True), reverse=True):
            return Path(match)
    return None


def _qn(namespace: str, tag: str) -> str:
    return f'{{{namespace}}}{tag}'


class MathConverter:
    """Converts LaTeX snippets into OMML elements ready to be spliced into a docx."""

    def __init__(
            self,
            xsl_path: str | Path | None = None,
            font: str = 'Cambria Math',
            size_pt: float | None = 14.0,
    ):
        self.font = font
        self.size_pt = size_pt
        self.xsl_path = find_xsl(xsl_path)
        self.failures: list[str] = []
        self._transform = None
        if self.xsl_path is not None:
            self._transform = etree.XSLT(etree.parse(str(self.xsl_path)))
        self._cache: dict[str, etree._Element | None] = {}

    @property
    def available(self) -> bool:
        return self._transform is not None

    def to_omml(self, latex: str) -> etree._Element | None:
        """Return an ``m:oMath`` element for ``latex``, or ``None`` on failure."""
        if latex in self._cache:
            cached = self._cache[latex]
            return None if cached is None else copy_element(cached)
        element = self._convert(latex)
        self._cache[latex] = element
        return None if element is None else copy_element(element)

    def _convert(self, latex: str) -> etree._Element | None:
        if self._transform is None:
            return None
        try:
            import latex2mathml.converter as converter
            mathml = converter.convert(normalize_latex(latex))
            omml = self._transform(etree.fromstring(mathml.encode('utf-8'))).getroot()
        except Exception:                   # noqa: BLE001 - any LaTeX defect falls back to text
            self.failures.append(latex)
            return None
        if omml is None:
            self.failures.append(latex)
            return None
        self._apply_run_properties(omml)
        return omml

    def _apply_run_properties(self, omml: etree._Element) -> None:
        """Force a consistent math font/size so equations match the body text."""
        for run in omml.iter(_qn(M_NS, 'r')):
            run_props = run.find(_qn(W_NS, 'rPr'))
            if run_props is None:
                run_props = etree.Element(_qn(W_NS, 'rPr'))
                run.insert(0, run_props)
            fonts = run_props.find(_qn(W_NS, 'rFonts'))
            if fonts is None:
                fonts = etree.SubElement(run_props, _qn(W_NS, 'rFonts'))
            for attribute in ('ascii', 'hAnsi'):
                fonts.set(_qn(W_NS, attribute), self.font)
            if self.size_pt is None:        # template styles decide the size
                continue
            size = run_props.find(_qn(W_NS, 'sz'))
            if size is None:
                size = etree.SubElement(run_props, _qn(W_NS, 'sz'))
            size.set(_qn(W_NS, 'val'), str(int(round(self.size_pt * 2))))


def copy_element(element: etree._Element) -> etree._Element:
    return etree.fromstring(etree.tostring(element))


_TEXT_WRAPPERS = re.compile(r'\\(?:mathrm|mathbf|mathit|mathcal|mathbb|text|operatorname)\s*\{')
_SPACING = re.compile(r'\\(?:,|;|:|!|quad|qquad)')
_COMMAND = re.compile(r'\\[a-zA-Z]+')

_REPLACEMENTS = (
    (r'\;', r'\,'),
    (r'\!', ''),
    (r'\displaystyle', ''),
)


def normalize_latex(latex: str) -> str:
    """Smooth over LaTeX constructs that ``latex2mathml`` chokes on."""
    text = latex.strip()
    for source, target in _REPLACEMENTS:
        text = text.replace(source, target)
    return text.strip()


def latex_to_plain(latex: str) -> str:
    """Best-effort plain-text rendering used when OMML conversion is unavailable."""
    text = _TEXT_WRAPPERS.sub('{', latex)
    text = text.replace(r'\left', '').replace(r'\right', '')
    text = _SPACING.sub(' ', text)
    text = text.replace(r'\_', '_').replace(r'\%', '%')
    text = _COMMAND.sub(lambda match: match.group(0)[1:], text)
    text = text.replace('{', '').replace('}', '')
    return re.sub(r'\s+', ' ', text).strip()
