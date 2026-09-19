"""Opening docx templates, including macro-enabled Word templates (.dotm/.dot).

python-docx refuses a ``.dotm`` because its main part carries the template content
type and the package holds VBA parts.  The package is repackaged in memory as a
plain document: content types are rewritten and the macro parts dropped, so the
styles, numbering and page setup survive while the result is a normal ``.docx``.
"""
from __future__ import annotations

import io
import re
import zipfile

from pathlib import Path

from docx import Document

TEMPLATE_EXTENSIONS = {'.dotm', '.dot', '.dotx'}

_MAIN_PART = '/word/document.xml'
_DOCUMENT_TYPE = ('application/vnd.openxmlformats-officedocument.'
                  'wordprocessingml.document.main+xml')
_TEMPLATE_TYPES = (
    'application/vnd.ms-word.template.macroEnabledTemplate.main+xml',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml',
)
_MACRO_PARTS = ('word/vbaProject.bin', 'word/vbaData.xml',
                'word/customizations.xml', 'customUI/customUI.xml')
_MACRO_RELATIONSHIP = re.compile(
    rb'<Relationship\b[^>]*Target="[^"]*(?:vbaProject\.bin|vbaData\.xml|customizations\.xml|customUI\.xml)"[^>]*/>',
    re.I)


def load_document(path: Path | None) -> Document:
    """Open ``path`` as a python-docx document; a blank one when ``path`` is None."""
    if path is None:
        return Document()
    path = Path(path)
    if path.suffix.lower() in TEMPLATE_EXTENSIONS:
        return Document(_as_document_package(path))
    return Document(str(path))


def _as_document_package(path: Path) -> io.BytesIO:
    source = zipfile.ZipFile(path)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            if item.filename in _MACRO_PARTS:
                continue
            data = source.read(item.filename)
            if item.filename == '[Content_Types].xml':
                data = _rewrite_content_types(data)
            elif item.filename.endswith('.rels'):
                data = _MACRO_RELATIONSHIP.sub(b'', data)
            target.writestr(item, data)
    source.close()
    buffer.seek(0)
    return buffer


def _rewrite_content_types(data: bytes) -> bytes:
    text = data.decode('utf-8')
    for template_type in _TEMPLATE_TYPES:
        text = text.replace(f'PartName="{_MAIN_PART}" ContentType="{template_type}"',
                            f'PartName="{_MAIN_PART}" ContentType="{_DOCUMENT_TYPE}"')
    text = re.sub(r'<Default Extension="bin"[^>]*/>', '', text)
    text = re.sub(r'<Override PartName="/(?:word/(?:vbaData|customizations)|customUI/customUI)\.xml"[^>]*/>',
                  '', text)
    return text.encode('utf-8')
