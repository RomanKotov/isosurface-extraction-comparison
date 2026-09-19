#!/usr/bin/env python
"""Збирає рукопис статті з markdown-розділів у docx за шаблоном журналу або в LaTeX.

Приклади:
    python tools/build_article.py                          # профіль full, docx
    python tools/build_article.py --list                   # перелік профілів
    python tools/build_article.py -p review                # інший профіль
    python tools/build_article.py -s 05-rezultaty.md -o build/rezultaty.docx
    python tools/build_article.py -p full --no-figures
    python tools/build_article.py -f tex                   # лише manuscript.tex
    python tools/build_article.py -f both                  # docx і tex з того ж тексту
"""
from __future__ import annotations

import argparse
import sys

from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from article_builder import build, load_config                     # noqa: E402
from article_builder.config import DEFAULT_CONFIG_NAME             # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def _utf8_output() -> None:
    """Звіт складання — українською, а консоль Windows віддає cp866/cp1251."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            try:
                stream.reconfigure(encoding='utf-8')
            except (OSError, ValueError):        # перенаправлений потік — лишаємо як є
                pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='build_article',
        description='Складання docx-рукопису з markdown-розділів за шаблоном журналу.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('-p', '--profile', default='full',
                        help='профіль складання з %s (типово: full)' % DEFAULT_CONFIG_NAME)
    parser.add_argument('-c', '--config', type=Path, default=None,
                        help='шлях до файлу конфігурації')
    parser.add_argument('-s', '--sections', nargs='+', metavar='ФАЙЛ',
                        help='перевизначити склад розділів (імена файлів або glob)')
    parser.add_argument('-o', '--output', type=Path, default=None,
                        help='шлях до вихідного docx')
    parser.add_argument('-t', '--template', type=Path, default=None,
                        help='docx/dotm-шаблон, з якого беруться стилі та параметри сторінки')
    parser.add_argument('-f', '--format', default='docx', choices=('docx', 'tex', 'both'),
                        dest='fmt', help='формат складання (типово: docx)')
    parser.add_argument('--styleset', default=None,
                        help='перевизначити набір стилів профілю')
    parser.add_argument('--no-figures', action='store_true', help='зібрати без рисунків')
    parser.add_argument('--no-tables', action='store_true', help='зібрати без таблиць')
    parser.add_argument('--list', action='store_true', dest='list_profiles',
                        help='показати доступні профілі та вийти')
    parser.add_argument('-q', '--quiet', action='store_true', help='без звіту про складання')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _utf8_output()
    args = parse_args(argv)
    config = load_config(args.config, ROOT)

    if args.list_profiles:
        _print_profiles(config)
        return 0

    formats = ('docx', 'tex') if args.fmt == 'both' else (args.fmt,)
    if args.output is not None and len(formats) > 1:
        print('Помилка: --output несумісний з --format both', file=sys.stderr)
        return 1

    results = []
    try:
        profile = config.profile(args.profile)
        if args.styleset:
            profile = replace(profile, styleset=args.styleset)
        for fmt in formats:
            results.append(build(
                config,
                profile,
                fmt=fmt,
                sections=tuple(args.sections) if args.sections else None,
                output=args.output,
                include_figures=False if args.no_figures else None,
                include_tables=False if args.no_tables else None,
                template=args.template,
            ))
    except (KeyError, ValueError, FileNotFoundError) as error:
        print(f'Помилка: {error}', file=sys.stderr)
        return 1

    if not args.quiet:
        for index, result in enumerate(results):
            if index:
                print()
            _report(result, profile.name)
    return 0


def _print_profiles(config) -> None:
    print(f'Конфігурація: {config.root / DEFAULT_CONFIG_NAME}')
    print(f'Розділи:      {config.source_dir}')
    print()
    print('Набори стилів:')
    for name, styleset in sorted(config.stylesets.items()):
        template = styleset.template or config.template or '— (чистий документ)'
        print(f'  {name:<12} {styleset.description}')
        print(f'  {"":<12} шаблон: {template}')
    print()
    print('Профілі:')
    for name, profile in sorted(config.profiles.items()):
        print(f'  {name:<12} -> {profile.output} / {profile.output_for("tex")}'
              f'  [{profile.styleset}]')
        if profile.description:
            print(f'  {"":<12}    {profile.description}')
        print(f'  {"":<12}    розділів: {len(profile.sections)}'
              f'{"" if profile.include_figures else ", без рисунків"}'
              f'{"" if profile.include_tables else ", без таблиць"}')


def _report(result, profile_name: str) -> None:
    print(f'Профіль:  {profile_name} [{result.fmt}]')
    print(f'Стилі:    {result.styleset} ({result.template or "чистий документ"})')
    print(f'Розділи:  {len(result.sections)}')
    for path in result.sections:
        print(f'          - {path.name}')
    print(f'Формули:  {result.math_engine}')
    if result.math_failures:
        print(f'          не конвертовано: {len(result.math_failures)}')
        for latex in result.math_failures[:5]:
            print(f'            ! {latex[:80]}')
    for warning in result.warnings:
        print(f'Увага:    {warning}')
    print(f'Готово:   {result.output}')


if __name__ == '__main__':
    raise SystemExit(main())
