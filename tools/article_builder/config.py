"""Build configuration: style sets, typography presets and assembly profiles (TOML driven)."""
from __future__ import annotations

import tomllib

from dataclasses import dataclass, field, replace
from pathlib import Path

DEFAULT_CONFIG_NAME = 'article-build.toml'

#: Roles the renderer asks a style set for; every profile resolves them to real docx styles.
ROLES = (
    'title', 'authors', 'affiliation', 'udc', 'abstract', 'keywords',
    'heading1', 'heading2', 'heading3', 'heading4',
    'body', 'body_after_heading', 'equation', 'figure', 'figure_caption',
    'table_caption', 'table_cell', 'list', 'reference', 'references_heading', 'code',
)


@dataclass(frozen=True)
class StyleConfig:
    """Typography used when the style set synthesises its own styles."""

    font: str = 'Times New Roman'
    size_pt: float = 14.0
    line_spacing: float = 1.15
    space_after_pt: float = 0.0
    first_line_indent_cm: float = 1.25
    justify: bool = True
    lang: str = 'uk-UA'

    title_size_pt: float = 14.0
    heading_space_before_pt: float = 12.0
    heading_space_after_pt: float = 6.0
    heading_bold: bool = True

    caption_size_pt: float = 13.0
    table_font_size_pt: float = 12.0
    table_min_font_size_pt: float = 8.0
    table_max_width_cm: float = 0.0     # 0 = ширина текстової колонки; більше — таблиця виходить у поля
    figure_max_width_cm: float = 16.0
    math_font: str = 'Cambria Math'
    bullet_marker: str = '–'
    list_indent_cm: float = 1.25
    reference_hanging_indent_cm: float = 0.75


#: Element roles the LaTeX renderer resolves to preamble macros.
LATEX_MACROS = {
    'title': 'arttitle',
    'authors': 'artauthors',
    'affiliation': 'artaffil',
    'udc': 'artudc',
    'abstract': 'artabstract',
    'keywords': 'artkeywords',
}


@dataclass(frozen=True)
class LatexConfig:
    """How the manuscript is rendered into LaTeX (second output next to the docx).

    Typography (font size, leading, indent) is taken from ``[style]`` so both
    outputs stay in step; everything here is LaTeX-specific plumbing.
    """

    documentclass: str = 'article'
    class_options: tuple[str, ...] = ('12pt', 'a4paper')
    engine: str = 'xelatex'                 # xelatex | lualatex | pdflatex
    language: str = 'ukrainian'
    other_language: str = 'english'
    main_font: str = 'Times New Roman'      # fontspec engines only
    mono_font: str = 'Courier New'
    geometry: str = 'a4paper,left=2.5cm,right=2.5cm,top=2cm,bottom=2cm'
    packages: tuple[str, ...] = ()          # extra \usepackage{...} lines
    preamble: str = ''                      # verbatim tail of the preamble
    define_macros: bool = True              # emit \newcommand for the element roles
    number_headings: bool = False           # numbers are already in the markdown text
    number_equations: bool = True
    number_captions: bool = False           # captions carry their own «Рис. 1.» / «Таблиця 1»
    figure_placement: str = 'htbp'
    figure_width: str = r'0.9\linewidth'
    table_placement: str = 'htbp'
    wide_table_columns: int = 6             # more columns -> own landscape page
    wide_table_resize: bool = True          # and scale it to the page height
    code_environment: str = 'verbatim'
    bibliography: str = 'thebibliography'   # thebibliography | plain
    macros: dict = field(default_factory=lambda: dict(LATEX_MACROS))

    def macro_for(self, role: str) -> str:
        return self.macros.get(role, LATEX_MACROS.get(role, role))


@dataclass(frozen=True)
class StyleSet:
    """How manuscript elements map onto the styles of one particular docx template."""

    name: str
    template: Path | None = None
    description: str = ''
    create_styles: bool = True          # synthesise "Article *" styles instead of reusing template ones
    manual_formatting: bool = True      # set fonts/sizes on runs; off = rely purely on template styles
    strip_heading_numbers: bool = False  # drop "2.1." when the template numbers headings itself
    auto_list_numbers: bool = False      # drop literal list markers when the style numbers items
    plain_title: bool = True             # cancel chapter numbering/page break a book title style carries
    equation_tab: bool = False           # lead display equations with a tab (template centres on a tab stop)
    landscape_wide_tables: bool = False  # move tables that cannot fit onto their own landscape page
    reference_tab: bool = False          # separate a reference number from its text with a tab
    fit_table_columns: bool = True
    table_style: str = 'Table Grid'
    roles: dict = field(default_factory=dict)

    def style_for(self, role: str) -> str:
        return self.roles.get(role, 'Normal')


BUILTIN_ROLES = {
    'title': 'Article Title',
    'authors': 'Article Authors',
    'affiliation': 'Article Authors',
    'udc': 'Article UDC',
    'abstract': 'Article Body',
    'keywords': 'Article Body',
    'heading1': 'Article Heading 1',
    'heading2': 'Article Heading 2',
    'heading3': 'Article Heading 3',
    'heading4': 'Article Heading 4',
    'body': 'Article Body',
    'body_after_heading': 'Article Body',
    'equation': 'Article Equation',
    'figure': 'Article Figure',
    'figure_caption': 'Article Caption',
    'table_caption': 'Article Table Caption',
    'table_cell': 'Article Table Cell',
    'list': 'Article List',
    'reference': 'Article Reference',
    'references_heading': 'Article Heading 1',
    'code': 'Article Code',
}


@dataclass(frozen=True)
class Profile:
    name: str
    output: str
    sections: tuple[str, ...]
    description: str = ''
    styleset: str = 'builtin'
    exclude: tuple[str, ...] = ()
    page_break_before: tuple[str, ...] = ()
    drop_sections: tuple[str, ...] = ()
    include_figures: bool = True
    include_tables: bool = True
    heading_offset: int = 0
    style: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    latex: dict = field(default_factory=dict)   # per-profile [latex] overrides
    latex_output: str = ''                      # defaults to output with a .tex suffix

    def output_for(self, fmt: str) -> str:
        if fmt != 'tex':
            return self.output
        return self.latex_output or str(Path(self.output).with_suffix('.tex'))


@dataclass(frozen=True)
class BuildConfig:
    root: Path
    source_dir: Path
    output_dir: Path
    template: Path | None
    assets_dir: Path | None
    style: StyleConfig
    profiles: dict[str, Profile]
    stylesets: dict[str, StyleSet]
    math_xsl: Path | None = None
    latex: LatexConfig = field(default_factory=LatexConfig)

    def profile(self, name: str) -> Profile:
        if name not in self.profiles:
            known = ', '.join(sorted(self.profiles)) or '<немає>'
            raise ValueError(f'невідомий профіль "{name}"; доступні: {known}')
        return self.profiles[name]

    def styleset_for(self, profile: Profile) -> StyleSet:
        if profile.styleset not in self.stylesets:
            known = ', '.join(sorted(self.stylesets))
            raise ValueError(f'невідомий набір стилів "{profile.styleset}"; доступні: {known}')
        styleset = self.stylesets[profile.styleset]
        if styleset.template is None and self.template is not None:
            styleset = replace(styleset, template=self.template)
        return styleset

    def style_for(self, profile: Profile) -> StyleConfig:
        if not profile.style:
            return self.style
        return replace(self.style, **_known_fields(profile.style, StyleConfig))

    def latex_for(self, profile: Profile) -> LatexConfig:
        if not profile.latex:
            return self.latex
        overrides = _latex_fields(profile.latex)
        if 'macros' in overrides:
            overrides['macros'] = {**self.latex.macros, **overrides['macros']}
        return replace(self.latex, **overrides)


def _known_fields(values: dict, target) -> dict:
    allowed = set(target.__dataclass_fields__)
    unknown = set(values) - allowed
    if unknown:
        raise ValueError(f'невідомі параметри стилю: {", ".join(sorted(unknown))}')
    return values


def _latex_fields(values: dict) -> dict:
    """Validate a ``[latex]`` table and bring TOML lists to the declared tuples."""
    resolved = dict(_known_fields(values, LatexConfig))
    macros = resolved.get('macros')
    if macros is not None:
        unknown = set(macros) - set(LATEX_MACROS)
        if unknown:
            raise ValueError(f'[latex.macros]: невідомі ролі {", ".join(sorted(unknown))}')
    for key in ('class_options', 'packages'):
        if key in resolved:
            resolved[key] = tuple(resolved[key])
    return resolved


DEFAULT_SECTIONS = (
    '00-titul-anotatsiya.md',
    '01-vstup.md',
    '02-ohlyad.md',
    '03-meta-zadachi.md',
    '04-materialy-metody.md',
    '05-rezultaty.md',
    '06-obgovorennya.md',
    '07-vysnovky.md',
)


def builtin_styleset() -> StyleSet:
    return StyleSet(name='builtin', description='Власні стилі складальника', roles=dict(BUILTIN_ROLES))


def default_config(root: Path) -> BuildConfig:
    profiles = {
        'full': Profile(
            name='full',
            output='manuscript.docx',
            sections=DEFAULT_SECTIONS,
            description='Повний рукопис за 7-розділовою схемою',
        ),
    }
    return BuildConfig(
        root=root,
        source_dir=root / 'article',
        output_dir=root / 'build',
        template=None,
        assets_dir=None,
        style=StyleConfig(),
        profiles=profiles,
        stylesets={'builtin': builtin_styleset()},
    )


def load_config(path: Path | None, root: Path) -> BuildConfig:
    if path is None:
        candidate = root / DEFAULT_CONFIG_NAME
        if not candidate.is_file():
            return default_config(root)
        path = candidate
    with path.open('rb') as stream:
        data = tomllib.load(stream)

    base = data.get('build', {})
    base_drop = tuple(base.get('drop_sections', ()))
    default_styleset = base.get('styleset', 'builtin')
    style = StyleConfig(**_known_fields(data.get('style', {}), StyleConfig))
    stylesets = _load_stylesets(data.get('stylesets', {}), root)
    latex_raw = _latex_fields(data.get('latex', {}))
    latex_raw['macros'] = {**LATEX_MACROS, **latex_raw.get('macros', {})}
    latex = LatexConfig(**latex_raw)

    profiles: dict[str, Profile] = {}
    for name, raw in data.get('profiles', {}).items():
        profiles[name] = Profile(
            name=name,
            output=raw.get('output', f'{name}.docx'),
            sections=tuple(raw.get('sections', DEFAULT_SECTIONS)),
            description=raw.get('description', ''),
            styleset=raw.get('styleset', default_styleset),
            exclude=tuple(raw.get('exclude', ())),
            page_break_before=tuple(raw.get('page_break_before', ())),
            drop_sections=tuple(raw.get('drop_sections', base_drop)),
            include_figures=bool(raw.get('include_figures', True)),
            include_tables=bool(raw.get('include_tables', True)),
            heading_offset=int(raw.get('heading_offset', 0)),
            style=raw.get('style', {}),
            metadata=raw.get('metadata', {}),
            latex=raw.get('latex', {}),
            latex_output=raw.get('latex_output', ''),
        )
    if not profiles:
        profiles = default_config(root).profiles

    return BuildConfig(
        root=root,
        source_dir=_resolve(root, base.get('source_dir', 'article')),
        output_dir=_resolve(root, base.get('output_dir', 'build')),
        template=_resolve(root, base['template']) if base.get('template') else None,
        assets_dir=_resolve(root, base['assets_dir']) if base.get('assets_dir') else None,
        style=style,
        profiles=profiles,
        stylesets=stylesets,
        math_xsl=_resolve(root, base['math_xsl']) if base.get('math_xsl') else None,
        latex=latex,
    )


def _load_stylesets(raw_sets: dict, root: Path) -> dict[str, StyleSet]:
    stylesets = {'builtin': builtin_styleset()}
    for name, raw in raw_sets.items():
        roles = dict(BUILTIN_ROLES) if raw.get('create_styles', True) else {}
        unknown = set(raw.get('styles', {})) - set(ROLES)
        if unknown:
            raise ValueError(f'набір стилів "{name}": невідомі ролі {", ".join(sorted(unknown))}')
        roles.update(raw.get('styles', {}))
        stylesets[name] = StyleSet(
            name=name,
            template=_resolve(root, raw['template']) if raw.get('template') else None,
            description=raw.get('description', ''),
            create_styles=bool(raw.get('create_styles', True)),
            manual_formatting=bool(raw.get('manual_formatting', raw.get('create_styles', True))),
            strip_heading_numbers=bool(raw.get('strip_heading_numbers', False)),
            auto_list_numbers=bool(raw.get('auto_list_numbers', False)),
            plain_title=bool(raw.get('plain_title', True)),
            equation_tab=bool(raw.get('equation_tab', False)),
            landscape_wide_tables=bool(raw.get('landscape_wide_tables', False)),
            reference_tab=bool(raw.get('reference_tab', False)),
            fit_table_columns=bool(raw.get('fit_table_columns', True)),
            table_style=raw.get('table_style', 'Table Grid'),
            roles=roles,
        )
    return stylesets


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (root / path)


def resolve_sections(config: BuildConfig, profile: Profile,
                     override: tuple[str, ...] | None = None) -> list[Path]:
    """Expand a profile's section patterns into an ordered list of markdown files."""
    patterns = override if override else profile.sections
    excluded = {p.resolve() for pattern in profile.exclude
                for p in sorted(config.source_dir.glob(pattern))}
    files: list[Path] = []
    for pattern in patterns:
        candidate = _resolve(config.source_dir, pattern)
        if candidate.is_file():
            matches = [candidate]
        else:
            matches = sorted(config.source_dir.glob(pattern))
            if not matches:
                raise FileNotFoundError(f'не знайдено розділ "{pattern}" у {config.source_dir}')
        for match in matches:
            if match.resolve() in excluded or match in files:
                continue
            files.append(match)
    return files
