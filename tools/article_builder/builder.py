"""Assembly pipeline: markdown sections -> parsed blocks -> docx or LaTeX file."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path

from .config import BuildConfig, Profile, resolve_sections
from .docx_writer import ArticleWriter
from .latex_writer import LatexWriter
from .mdparse import drop_sections, parse_markdown

FORMATS = ('docx', 'tex')


@dataclass
class BuildResult:
    output: Path
    sections: list[Path]
    fmt: str = 'docx'
    styleset: str = ''
    template: Path | None = None
    warnings: list[str] = field(default_factory=list)
    math_failures: list[str] = field(default_factory=list)
    math_engine: str = ''


def build(config: BuildConfig, profile: Profile, *,
          fmt: str = 'docx',
          sections: tuple[str, ...] | None = None,
          output: Path | None = None,
          include_figures: bool | None = None,
          include_tables: bool | None = None,
          template: Path | None = None) -> BuildResult:
    if fmt not in FORMATS:
        raise ValueError(f'невідомий формат "{fmt}"; доступні: {", ".join(FORMATS)}')
    files = resolve_sections(config, profile, sections)
    if not files:
        raise ValueError('не задано жодного розділу для складання')

    style = config.style_for(profile)
    styleset = config.styleset_for(profile)
    if template is not None:
        styleset = replace(styleset, template=template)
    if fmt == 'docx' and styleset.template is not None \
            and not Path(styleset.template).is_file():
        raise FileNotFoundError(f'не знайдено шаблон: {styleset.template}')

    destination = output if output is not None \
        else config.output_dir / profile.output_for(fmt)
    figures = profile.include_figures if include_figures is None else include_figures
    tables = profile.include_tables if include_tables is None else include_tables

    if fmt == 'tex':
        writer = LatexWriter(
            latex=config.latex_for(profile),
            style=style,
            styleset=styleset,
            include_figures=figures,
            include_tables=tables,
            heading_offset=profile.heading_offset,
            assets_root=config.assets_dir or config.source_dir,
            output_dir=destination.parent,
        )
    else:
        writer = ArticleWriter(
            style=style,
            styleset=styleset,
            math_xsl=config.math_xsl,
            include_figures=figures,
            include_tables=tables,
            heading_offset=profile.heading_offset,
            assets_root=config.assets_dir or config.source_dir,
        )

    breaks = {name.strip() for name in profile.page_break_before}
    for index, path in enumerate(files):
        blocks = drop_sections(parse_markdown(path.read_text(encoding='utf-8')),
                               profile.drop_sections)
        page_break = index > 0 and bool(breaks & {path.name, path.stem, str(path)})
        writer.add_section(blocks, page_break=page_break)

    writer.save(destination, metadata=profile.metadata)

    if fmt == 'tex':
        return BuildResult(
            output=destination,
            sections=files,
            fmt=fmt,
            styleset=styleset.name,
            template=None,
            warnings=writer.warnings,
            math_engine='LaTeX (формули переносяться без конвертації)',
        )
    return BuildResult(
        output=destination,
        sections=files,
        fmt=fmt,
        styleset=styleset.name,
        template=styleset.template,
        warnings=writer.warnings,
        math_failures=writer.math.failures,
        math_engine=str(writer.math.xsl_path) if writer.math.available else 'немає (формули як текст)',
    )
