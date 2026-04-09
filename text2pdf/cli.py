#!/usr/bin/env python3
"""
text2pdf CLI.

Usage:
    text2pdf convert <input> [-o <output>] [options]
    text2pdf detect <input>
    text2pdf engines
    text2pdf image [prompt] [-o <output>] [options]
    text2pdf help-format
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import textwrap
from pathlib import Path

from text2pdf import __version__
from text2pdf import imagegen, structure as struct_mod
from text2pdf.engines import pandoc_engine, weasyprint_engine


logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
log = logging.getLogger('text2pdf')

_THEMES = {
    'report': 'report.css',
    'academic': 'academic.css',
    'modern': 'modern.css',
    'ebook': 'ebook.css',
}


# ---------------------------------------------------------------------------
# Main commands
# ---------------------------------------------------------------------------


def cmd_convert(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else Path(_default_output(str(input_path)))

    if not input_path.exists():
        log.error('Input file not found: %s', input_path)
        return 1

    if args.verbose:
        log.setLevel(logging.DEBUG)

    raw_text = input_path.read_text(encoding='utf-8', errors='replace')
    if not raw_text.strip():
        log.error('Input file is empty.')
        return 1

    image_dir = Path(args.image_dir) if args.image_dir else output_path.parent / f'{output_path.stem}_assets'

    if args.generate_images:
        defaults = _build_image_request_defaults(args, output_path=image_dir / 'generated')
        raw_text, generated = imagegen.process_image_directives(
            raw_text,
            defaults=defaults,
            output_dir=image_dir,
            relative_to=input_path.parent,
        )
        if generated:
            log.info('Generated %s image(s) in %s', len(generated), image_dir)

    fmt = args.from_format
    if fmt == 'auto':
        fmt = _detect_format(raw_text)
        log.info('Detected input format: %s', fmt)

    theme_css = _load_theme_css(args.theme)
    try:
        custom_css = _load_custom_css(args.css)
    except FileNotFoundError as exc:
        log.error(str(exc))
        return 1

    engine_name = args.engine
    if engine_name == 'auto':
        if weasyprint_engine.is_available():
            engine_name = 'weasyprint'
        elif pandoc_engine.is_available():
            engine_name = 'pandoc'
        else:
            log.error('No PDF engine available. Install weasyprint or pandoc.')
            return 1

    html_opts = {
        'title': args.title or '',
        'author': args.author or '',
        'subject': args.subject or '',
        'keywords': args.keywords or '',
        'language': args.language,
        'toc': args.toc,
        'toc_override_set': args.toc_explicit,
        'embed_images': args.embed_images,
        'image_dir': str(image_dir),
        'theme_css': theme_css,
        'custom_css': custom_css,
        'page_size': args.page_size,
        'header': args.header or '',
        'footer': args.footer or '',
    }

    if fmt == 'html':
        html = _wrap_html(raw_text, html_opts)
    else:
        html = struct_mod.convert_to_html(raw_text, html_opts)

    try:
        if engine_name == 'weasyprint':
            if not weasyprint_engine.is_available():
                log.error('WeasyPrint is not available.')
                return 1
            weasyprint_engine.render(html, str(output_path), {'presentational_hints': True})
        elif engine_name == 'pandoc':
            if not pandoc_engine.is_available():
                log.error('Pandoc is not available.')
                return 1
            pandoc_engine.render(
                html,
                str(output_path),
                {
                    'input_format': 'html',
                    'toc': args.toc,
                    'metadata': {
                        'title': args.title or '',
                        'author': args.author or '',
                    },
                },
            )
        else:
            log.error('Unknown engine: %s', engine_name)
            return 1
    except Exception as exc:
        log.error('PDF rendering failed: %s', exc)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1

    size_kb = output_path.stat().st_size // 1024
    log.info('Done! PDF written to: %s (%s KB)', output_path, size_kb)
    return 0



def cmd_detect(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    if not input_path.exists():
        log.error('File not found: %s', input_path)
        return 1

    raw_text = input_path.read_text(encoding='utf-8', errors='replace')
    structure = struct_mod.detect_structure(raw_text)
    fm = structure.get('frontmatter')

    print(f"\n{'=' * 60}")
    print(f'  Structure analysis: {input_path}')
    print(f"{'=' * 60}\n")

    if fm:
        print(f'  Frontmatter: {fm}')

    print(f"  Headings found: {len(structure['headings'])}")
    for level, text in structure['headings'][:20]:
        indent = '  ' * (level - 1)
        print(f'  {indent}[H{level}] {text[:70]}')

    if len(structure['headings']) > 20:
        print(f"  ... and {len(structure['headings']) - 20} more headings")

    print(f"\n  Paragraphs:     {len(structure['paragraphs'])}")
    print(f"  Lists:           {len(structure['lists'])}")
    print(f"  Code blocks:     {len(structure['code_blocks'])}")
    print(f"  Blockquotes:     {len(structure['blockquotes'])}")
    print(f"  Tables:          {len(structure['tables'])}")
    print(f"  Images:          {len(structure['images'])}")
    print(f"  Horizontal rules:{len(structure['horizontal_rules'])}")

    title = fm.get('title') if fm else None
    if not title and structure['headings']:
        title = structure['headings'][0][1]
    if title:
        print(f'\n  Suggested --title: "{title}"')

    print()
    return 0



def cmd_engines(args: argparse.Namespace) -> int:
    print(f'\n  text2pdf v{__version__}')
    print(f"  {'=' * 50}\n")

    weasy = weasyprint_engine.is_available()
    pandoc = pandoc_engine.is_available()

    print(f"  WeasyPrint:  {'Available (v' + weasyprint_engine.get_version() + ')' if weasy else 'Not available'}")
    print(f"  Pandoc:      {'Available (v' + pandoc_engine.get_version() + ')' if pandoc else 'Not available'}")
    print('')
    print('  Default engine: ', end='')
    if weasy:
        print('weasyprint')
    elif pandoc:
        print('pandoc')
    else:
        print('none')
        return 1
    print('')
    return 0



def cmd_image(args: argparse.Namespace) -> int:
    prompt = _resolve_prompt(args.prompt, args.prompt_file)
    if not prompt:
        log.error('Provide a prompt argument or --prompt-file.')
        return 1

    if args.verbose:
        log.setLevel(logging.DEBUG)

    output_path = Path(args.output) if args.output else imagegen.build_default_output_path(prompt)
    request = _build_image_request_defaults(args, output_path=output_path, prompt=prompt)

    try:
        result = imagegen.generate_image(request)
    except Exception as exc:
        log.error('Image generation failed: %s', exc)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1

    log.info('Image written to: %s', result.path)
    return 0



def cmd_help_format(args: argparse.Namespace) -> int:
    print(textwrap.dedent(FORMAT_HELP))
    return 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_theme_css(theme_name: str) -> str:
    filename = _THEMES.get(theme_name, 'report.css')
    try:
        from importlib.resources import files

        return (files('text2pdf.themes') / filename).read_text(encoding='utf-8')
    except Exception:
        theme_path = Path(__file__).with_name('themes') / filename
        if theme_path.exists():
            return theme_path.read_text(encoding='utf-8')
        log.warning("Theme '%s' not found, using 'report'", theme_name)
        return _load_theme_css('report')



def _load_custom_css(css_path: str | None) -> str:
    if not css_path:
        return ''

    custom_path = Path(css_path)
    if not custom_path.exists():
        raise FileNotFoundError(f'Custom CSS file not found: {custom_path}')
    return '\n' + custom_path.read_text(encoding='utf-8')



def _detect_format(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith('<!DOCTYPE html') or stripped.startswith('<html'):
        return 'html'
    if stripped.startswith('.. ') or '..  ' in stripped[:200]:
        return 'rst'

    markdown_markers = 0
    for line in text.splitlines()[:100]:
        ls = line.strip()
        if ls.startswith('# ') or '**' in ls or ('[' in ls and '](' in ls):
            markdown_markers += 1
    if markdown_markers >= 2:
        return 'markdown'
    return 'plain'



def _default_output(input_path: str) -> str:
    return os.path.splitext(input_path)[0] + '.pdf'



def _wrap_html(html_content: str, opts: dict[str, str]) -> str:
    theme_css = opts.get('theme_css', '')
    custom_css = opts.get('custom_css', '')
    lang = opts.get('language', 'en')
    title = opts.get('title', 'Document')
    page_size = opts.get('page_size', 'A4')
    header_css = struct_mod._build_running_header(opts.get('header', ''))
    footer_css = struct_mod._build_running_footer(opts.get('footer', ''))

    body_start = html_content.find('<body')
    if body_start != -1:
        body_start = html_content.find('>', body_start) + 1
        body_end = html_content.find('</body>')
        body = html_content[body_start:body_end]
    else:
        body = html_content

    css = theme_css + custom_css + (
        '\n@page {\n'
        f'  size: {page_size};\n'
        '  margin: 20mm 18mm 25mm 18mm;\n'
        f'  {header_css}\n'
        f'  {footer_css}\n'
        '}\n'
    )

    return (
        f'<!DOCTYPE html>\n<html lang="{lang}">\n<head>\n'
        '<meta charset="UTF-8">\n'
        f'<title>{title}</title>\n'
        f'<style>\n{css}\n</style>\n'
        '</head>\n<body>\n'
        f'{body}\n'
        '</body>\n</html>'
    )



def _resolve_prompt(prompt: str | None, prompt_file: str | None) -> str:
    if prompt:
        return prompt
    if prompt_file:
        return Path(prompt_file).read_text(encoding='utf-8').strip()
    return ''



def _build_image_request_defaults(
    args: argparse.Namespace,
    *,
    output_path: Path,
    prompt: str = '',
) -> imagegen.ImageGenerationRequest:
    return imagegen.ImageGenerationRequest(
        prompt=prompt,
        output_path=output_path,
        provider=args.image_provider,
        model=args.image_model,
        api_key=args.image_api_key,
        api_key_env=args.image_api_key_env,
        references=list(args.image_reference or []),
        reference_type=args.image_reference_type,
        aspect_ratio=args.image_aspect_ratio,
        image_size=args.image_size,
        width=args.image_width,
        height=args.image_height,
        prompt_optimizer=args.image_prompt_optimizer,
    )



def _add_image_args(parser: argparse.ArgumentParser, *, standalone: bool) -> None:
    parser.add_argument('--image-provider', choices=['gemini', 'minimax'], default='gemini', help='Image provider (default: gemini)')
    parser.add_argument('--image-model', default=None, help='Override the provider model name')
    parser.add_argument('--image-api-key', default=None, help='API key for the image provider')
    parser.add_argument('--image-api-key-env', default=None, help='Environment variable that contains the image provider API key')
    parser.add_argument('--image-reference', action='append', default=None, help='Reference image path or URL. Repeat to add multiple references.')
    parser.add_argument('--image-reference-type', default='character', help='MiniMax reference type for image-to-image requests (default: character)')
    parser.add_argument('--image-aspect-ratio', default='1:1', help='Aspect ratio for generated images (default: 1:1)')
    parser.add_argument('--image-size', default=None, help='Gemini image size hint, for example 1K, 2K, or 4K')
    parser.add_argument('--image-width', type=int, default=None, help='MiniMax output width in pixels')
    parser.add_argument('--image-height', type=int, default=None, help='MiniMax output height in pixels')
    parser.add_argument('--image-prompt-optimizer', action=argparse.BooleanOptionalAction, default=None, help='Enable or disable MiniMax prompt optimizer')
    if standalone:
        parser.add_argument('--prompt-file', default=None, help='Read the image prompt from a file')


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='text2pdf',
        description='Convert plain text into high-quality PDFs.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')

    sub = parser.add_subparsers(dest='command', required=True)

    conv = sub.add_parser('convert', help='Convert a file to PDF', formatter_class=argparse.RawDescriptionHelpFormatter)
    conv.add_argument('input', help='Input file (txt, md, html, rst)')
    conv.add_argument('-o', '--output', dest='output', help='Output PDF path (default: <input>.pdf)')
    conv.add_argument('--engine', choices=['auto', 'weasyprint', 'pandoc'], default='auto', help='PDF engine to use (default: auto)')
    conv.add_argument('--theme', choices=list(_THEMES.keys()), default='report', help='Built-in CSS theme (default: report)')
    conv.add_argument('--page-size', choices=['A4', 'Letter', 'Legal', 'A5'], default='A4', help='Page size (default: A4)')
    conv.add_argument('--toc', action=argparse.BooleanOptionalAction, default=True, help='Enable or disable table of contents (default: enabled)')
    conv.add_argument('--header', default='', help='Running header text')
    conv.add_argument('--footer', default='', help='Running footer text. Use {page} and {pages} for page numbers.')
    conv.add_argument('--title', default='', help='Document title')
    conv.add_argument('--author', default='', help='Document author')
    conv.add_argument('--subject', default='', help='Document subject')
    conv.add_argument('--keywords', default='', help='Document keywords (comma-separated)')
    conv.add_argument('--language', default='en', help='Language for hyphenation (default: en)')
    conv.add_argument('--css', dest='css', help='Path to custom CSS file to merge with the theme')
    conv.add_argument('--embed-images', action='store_true', help='Download remote image URLs and rewrite them to local files')
    conv.add_argument('--generate-images', action='store_true', help='Render [[image: prompt]] directives before conversion')
    conv.add_argument('--image-dir', default='', help='Directory to store downloaded and generated images (default: <output>_assets)')
    conv.add_argument('--from', dest='from_format', choices=['auto', 'markdown', 'md', 'plain', 'html', 'rst'], default='auto', help='Input format hint (default: auto-detect)')
    conv.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    conv.set_defaults(func=cmd_convert, toc_explicit=False)
    _add_image_args(conv, standalone=False)

    det = sub.add_parser('detect', help='Show detected structure of a file')
    det.add_argument('input', help='Input file to analyse')
    det.set_defaults(func=cmd_detect)

    eng = sub.add_parser('engines', help='Show available PDF engines')
    eng.set_defaults(func=cmd_engines)

    img = sub.add_parser('image', help='Generate an image with Gemini or MiniMax')
    img.add_argument('prompt', nargs='?', help='Image prompt')
    img.add_argument('-o', '--output', dest='output', help='Output image path (default: slugified prompt in current directory)')
    img.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    img.set_defaults(func=cmd_image)
    _add_image_args(img, standalone=True)

    help_format = sub.add_parser('help-format', help='Show formatting guide')
    help_format.set_defaults(func=cmd_help_format)

    return parser



def main() -> int:
    if '--help-format' in sys.argv[1:]:
        return cmd_help_format(argparse.Namespace())

    parser = build_parser()
    args = parser.parse_args()

    if getattr(args, 'command', None) == 'convert':
        args.toc_explicit = any(flag in sys.argv[1:] for flag in ('--toc', '--no-toc'))

    return args.func(args)


FORMAT_HELP = """
Formatting Guide for Input Files
================================

text2pdf auto-detects structure in plain text. The more structure
you add, the better the PDF output.

HEADINGS
--------
Markdown style (recommended):
    # Chapter 1
    ## Section 1.1
    ### Section 1.1.1

Numbered style:
    1. Chapter One
    2. Chapter Two

ALL CAPS standalone lines are also detected as H1 headings.

PARAGRAPHS
----------
Separate paragraphs with a blank line. First paragraph after a
heading does not get a text indent.

LISTS
-----
    - Bullet item one
    - Bullet item two

    1. First ordered item
    2. Second ordered item

INLINE FORMATTING
-----------------
    **bold text**
    *italic text*
    `inline code`
    [link text](https://example.com)
    ![alt text](image.png)

AI IMAGE DIRECTIVES
-------------------
Generate local images during conversion with --generate-images:
    [[image: A clean Nordic cover illustration | alt=Cover art | provider=gemini | aspect=16:9]]

CODE BLOCKS
-----------
    ```python
    def hello():
        print("world")
    ```

    Or indent with 4 spaces.

BLOCKQUOTES
-----------
    > This is a blockquote.
    > It can span multiple lines.

TABLES
------
    | Column A | Column B | Column C |
    |----------|----------|----------|
    | Value 1  | Value 2  | Value 3  |
    | Value 4  | Value 5  | Value 6  |

YAML FRONTMATTER
----------------
At the top of the file, before any content:
    ---
    title: "My Document Title"
    author: "Your Name"
    toc: true
    ---

Frontmatter values can override defaults. Explicit CLI flags take precedence.
"""
