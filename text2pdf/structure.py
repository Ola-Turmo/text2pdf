"""
Plain-text structure detector.

The core module that takes unstructured text and produces structured HTML
with auto-detected headings, paragraphs, lists, code blocks, and more.
"""

from __future__ import annotations

import hashlib
import html
import os
import re
import urllib.request
from typing import Any


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*(?:\n|$)', re.DOTALL)

HEADING_MD_RE = re.compile(r'^(#{1,6})\s+(.+?)\s*$')
NUMBERED_HEADING_RE = re.compile(r'^(\d+[.)])\s+(.+?)\s*$')
ALL_CAPS_HEADING_RE = re.compile(r'^[A-Z][A-Z0-9 ,:;!?\'"-]{5,100}$')
TITLE_CASE_RE = re.compile(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,8}$')
SECTION_DIVIDER_RE = re.compile(r'^[=\-]{3,}$')

BLOCKQUOTE_RE = re.compile(r'^>\s?(.*)')
BULLET_RE = re.compile(r'^[-*+]\s+(.+)')
ORDERED_RE = re.compile(r'^\d+[.)]\s+(.+)')
HR_RE = re.compile(r'^(?:[-*_])\s*(?:[-*_]\s*){2,}$')

INLINE_BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
INLINE_ITALIC_RE = re.compile(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)')
INLINE_CODE_RE = re.compile(r'`([^`]+)`')
INLINE_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')
INLINE_IMAGE_RE = re.compile(r'!\[([^\]]*)\]\((<[^>]+>|[^)]+?)(?:\s+"([^"]+)")?\)')

FENCE_START_RE = re.compile(r'^```([A-Za-z0-9_+.-]*)\s*$')
INDENTED_CODE_RE = re.compile(r'^(?: {4,}|\t)(.*)$')
TABLE_ROW_RE = re.compile(r'^\|(.+)\|$')
IMG_TAG_RE = re.compile(r'<img(?P<before>[^>]*?)\s+src="(?P<src>[^"]+)"(?P<after>[^>]*)>')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_structure(text: str) -> dict[str, Any]:
    """
    Analyse plain text and return a structured representation.

    Returns a dict with keys:
      - frontmatter : dict | None
      - blocks      : ordered list of normalized blocks
      - headings    : list of (level, text)
      - paragraphs  : list of HTML strings
      - lists       : list of {'type': 'ul'|'ol', 'items': [str]}
      - blockquotes : list of HTML strings
      - code_blocks : list of {'lang': str, 'code': str}
      - tables      : list of list of list of str
      - images      : list of (alt_text, url)
      - horizontal_rules : list of None
    """
    fm_match = FRONTMATTER_RE.match(text)
    frontmatter = None
    if fm_match:
        frontmatter = _parse_frontmatter(fm_match.group(1))
        text = text[fm_match.end():]

    raw_blocks = _coalesce_blocks(text.splitlines())
    elements: dict[str, Any] = {
        'frontmatter': frontmatter,
        'blocks': [],
        'headings': [],
        'paragraphs': [],
        'lists': [],
        'blockquotes': [],
        'code_blocks': [],
        'tables': [],
        'images': [],
        'horizontal_rules': [],
    }

    for block_type, content in raw_blocks:
        normalized = _normalize_block(block_type, content)
        elements['blocks'].append(normalized)

        if block_type == 'heading':
            elements['headings'].append(content)
        elif block_type == 'paragraph':
            elements['paragraphs'].append(normalized['html'])
        elif block_type == 'bullet_list':
            elements['lists'].append({'type': 'ul', 'items': normalized['items']})
        elif block_type == 'ordered_list':
            elements['lists'].append({'type': 'ol', 'items': normalized['items']})
        elif block_type == 'blockquote':
            elements['blockquotes'].append(normalized['html'])
        elif block_type == 'code_block':
            elements['code_blocks'].append({'lang': normalized['lang'], 'code': normalized['code']})
        elif block_type == 'table':
            elements['tables'].append(normalized['rows'])
        elif block_type == 'hr':
            elements['horizontal_rules'].append(None)

    for match in INLINE_IMAGE_RE.finditer(text):
        elements['images'].append((match.group(1), _clean_inline_target(match.group(2))))

    return elements



def convert_to_html(text: str, options: dict[str, Any] | None = None) -> str:
    """Convert plain text to a complete HTML document."""
    opts = dict(options or {})
    title = opts.get('title', 'Untitled Document')
    author = opts.get('author', '')
    subject = opts.get('subject', '')
    keywords = opts.get('keywords', '')
    lang = opts.get('language', 'en')
    theme_css = opts.get('theme_css', '')
    custom_css = opts.get('custom_css', '')
    page_size = opts.get('page_size', 'A4')

    structure = detect_structure(text)
    fm = structure.get('frontmatter') or {}

    title = title or fm.get('title', 'Untitled Document')
    author = author or fm.get('author', '')
    keywords = keywords or fm.get('keywords', '')
    if 'toc' in fm and not opts.get('toc_override_set', False):
        opts['toc'] = _coerce_frontmatter_bool(fm['toc'])

    body_html = _build_body(structure, opts)
    toc_html = _build_toc_html(structure['headings']) if opts.get('toc', True) else ''

    css = theme_css
    if custom_css:
        css += '\n' + custom_css

    header_html = _build_running_header(opts.get('header', ''))
    footer_html = _build_running_footer(opts.get('footer', 'Page {page} of {pages}'))

    return HTML_TEMPLATE.format(
        lang=lang,
        title=html.escape(title),
        author=html.escape(author),
        subject=html.escape(subject),
        keywords=html.escape(keywords),
        css=css,
        page_size=page_size,
        header_html=header_html,
        footer_html=footer_html,
        body=toc_html + body_html,
    )



def detect_headings(text: str) -> list[tuple[int, str]]:
    """Return list of detected headings as (level, text)."""
    structure = detect_structure(text)
    return structure['headings']


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _coalesce_blocks(lines: list[str]) -> list[tuple[str, Any]]:
    """Walk through lines and group them into typed blocks."""
    blocks: list[tuple[str, Any]] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if stripped == '':
            i += 1
            continue

        fence_match = FENCE_START_RE.match(stripped)
        if fence_match:
            lang = fence_match.group(1) or ''
            i += 1
            code_lines: list[str] = []
            while i < n and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            if i < n:
                i += 1
            blocks.append(('code_block', {'lang': lang, 'code': '\n'.join(code_lines)}))
            continue

        if INDENTED_CODE_RE.match(line):
            code_lines = []
            while i < n:
                if lines[i].strip() == '':
                    code_lines.append('')
                    i += 1
                    continue
                code_match = INDENTED_CODE_RE.match(lines[i])
                if not code_match:
                    break
                code_lines.append(code_match.group(1))
                i += 1
            while code_lines and code_lines[-1] == '':
                code_lines.pop()
            blocks.append(('code_block', {'lang': '', 'code': '\n'.join(code_lines)}))
            continue

        if HR_RE.match(stripped):
            blocks.append(('hr', None))
            i += 1
            continue

        heading_match = HEADING_MD_RE.match(stripped)
        if heading_match:
            blocks.append(('heading', (len(heading_match.group(1)), heading_match.group(2))))
            i += 1
            continue

        numbered_match = NUMBERED_HEADING_RE.match(stripped)
        if numbered_match and _looks_like_numbered_heading(lines, i):
            blocks.append(('heading', (2, numbered_match.group(2))))
            i += 1
            continue

        if ALL_CAPS_HEADING_RE.match(stripped) and not stripped.startswith('http'):
            blocks.append(('heading', (1, stripped)))
            i += 1
            continue

        if SECTION_DIVIDER_RE.match(stripped):
            blocks.append(('hr', None))
            i += 1
            continue

        if stripped.startswith('>'):
            quote_lines = []
            while i < n and lines[i].strip().startswith('>'):
                match = BLOCKQUOTE_RE.match(lines[i].strip())
                quote_lines.append(match.group(1) if match else '')
                i += 1
            blocks.append(('blockquote', ' '.join(quote_lines).strip()))
            continue

        if BULLET_RE.match(stripped):
            items = []
            while i < n and BULLET_RE.match(lines[i].strip()):
                match = BULLET_RE.match(lines[i].strip())
                items.append(match.group(1))
                i += 1
            blocks.append(('bullet_list', items))
            continue

        if ORDERED_RE.match(stripped):
            items = []
            while i < n and ORDERED_RE.match(lines[i].strip()):
                match = ORDERED_RE.match(lines[i].strip())
                items.append(match.group(1))
                i += 1
            blocks.append(('ordered_list', items))
            continue

        if stripped.startswith('|'):
            rows = []
            while i < n and TABLE_ROW_RE.match(lines[i].strip()):
                row_text = lines[i].strip().strip('|')
                cells = [cell.strip() for cell in row_text.split('|')]
                if not all(re.match(r'^[-:]+$', cell) for cell in cells):
                    rows.append(cells)
                i += 1
            if rows:
                blocks.append(('table', rows))
            continue

        paragraph_lines = []
        while i < n and lines[i].strip() != '':
            if _starts_new_block(lines, i) and paragraph_lines:
                break
            paragraph_lines.append(lines[i])
            i += 1
        blocks.append(('paragraph', ' '.join(line.strip() for line in paragraph_lines)))

    return blocks



def _starts_new_block(lines: list[str], index: int) -> bool:
    stripped = lines[index].strip()
    if index == 0:
        return False
    return bool(
        FENCE_START_RE.match(stripped)
        or INDENTED_CODE_RE.match(lines[index])
        or HR_RE.match(stripped)
        or HEADING_MD_RE.match(stripped)
        or (NUMBERED_HEADING_RE.match(stripped) and _looks_like_numbered_heading(lines, index))
        or ALL_CAPS_HEADING_RE.match(stripped)
        or stripped.startswith('>')
        or BULLET_RE.match(stripped)
        or ORDERED_RE.match(stripped)
        or stripped.startswith('|')
    )



def _looks_like_numbered_heading(lines: list[str], index: int) -> bool:
    stripped = lines[index].strip()
    match = NUMBERED_HEADING_RE.match(stripped)
    if not match:
        return False

    next_line = lines[index + 1].strip() if index + 1 < len(lines) else ''
    if ORDERED_RE.match(next_line):
        return False

    title_text = match.group(2).strip()
    return bool(
        title_text.endswith(':')
        or TITLE_CASE_RE.match(title_text)
        or ALL_CAPS_HEADING_RE.match(title_text)
        or len(title_text.split()) >= 2
    )



def _normalize_block(block_type: str, content: Any) -> dict[str, Any]:
    if block_type == 'heading':
        level, text = content
        return {'type': 'heading', 'level': level, 'text': text}
    if block_type == 'paragraph':
        return {'type': 'paragraph', 'text': content, 'html': _process_inline(content)}
    if block_type == 'bullet_list':
        return {'type': 'list', 'list_type': 'ul', 'items': [_process_inline(item) for item in content]}
    if block_type == 'ordered_list':
        return {'type': 'list', 'list_type': 'ol', 'items': [_process_inline(item) for item in content]}
    if block_type == 'blockquote':
        return {'type': 'blockquote', 'text': content, 'html': _process_inline(content)}
    if block_type == 'code_block':
        return {'type': 'code_block', 'lang': content.get('lang', ''), 'code': content.get('code', '')}
    if block_type == 'table':
        return {'type': 'table', 'rows': content}
    if block_type == 'hr':
        return {'type': 'hr'}
    raise ValueError(f'Unsupported block type: {block_type}')



def _build_body(structure: dict[str, Any], opts: dict[str, Any]) -> str:
    parts = []
    embed_images = opts.get('embed_images', False)
    image_dir = opts.get('image_dir', '')

    for block in structure['blocks']:
        block_type = block['type']
        if block_type == 'heading':
            heading_id = _slugify(block['text'])
            parts.append(f'<h{block["level"]} id="{heading_id}">{_process_inline(block["text"])}</h{block["level"]}>')
        elif block_type == 'paragraph':
            parts.append(f'<p>{block["html"]}</p>')
        elif block_type == 'list':
            items_html = ''.join(f'<li>{item}</li>' for item in block['items'])
            parts.append(f'<{block["list_type"]}>{items_html}</{block["list_type"]}>')
        elif block_type == 'blockquote':
            parts.append(f'<blockquote>{block["html"]}</blockquote>')
        elif block_type == 'code_block':
            language = block['lang'] or 'text'
            code = html.escape(block['code'])
            parts.append(f'<pre><code class="language-{language}">{code}</code></pre>')
        elif block_type == 'table':
            rows_html = []
            for row_index, row in enumerate(block['rows']):
                cell_tag = 'th' if row_index == 0 else 'td'
                cells = ''.join(f'<{cell_tag}>{html.escape(cell)}</{cell_tag}>' for cell in row)
                rows_html.append(f'<tr>{cells}</tr>')
            parts.append('<table><tbody>' + ''.join(rows_html) + '</tbody></table>')
        elif block_type == 'hr':
            parts.append('<hr>')

    body = '\n'.join(parts)
    if embed_images:
        body = _rewrite_image_sources(body, image_dir)
    return body



def _rewrite_image_sources(html_content: str, image_dir: str) -> str:
    def replace(match: re.Match[str]) -> str:
        src = match.group('src')
        if src.startswith(('http://', 'https://')):
            src = _download_image(src, image_dir)
        escaped_src = html.escape(src, quote=True)
        return f'<img{match.group("before")} src="{escaped_src}"{match.group("after")}>'

    return IMG_TAG_RE.sub(replace, html_content)



def _process_inline(text: str) -> str:
    """Apply inline markdown-like transformations, returning HTML."""
    result = text

    def img_replace(match: re.Match[str]) -> str:
        alt = match.group(1)
        url = _clean_inline_target(match.group(2))
        title = match.group(3) or ''
        title_attr = f' title="{html.escape(title)}"' if title else ''
        return f'<img src="{html.escape(url, quote=True)}" alt="{html.escape(alt)}"{title_attr}>'

    result = INLINE_IMAGE_RE.sub(img_replace, result)

    def link_replace(match: re.Match[str]) -> str:
        label, url = match.group(1), _clean_inline_target(match.group(2))
        return f'<a href="{html.escape(url, quote=True)}">{label}</a>'

    result = INLINE_LINK_RE.sub(link_replace, result)
    result = INLINE_BOLD_RE.sub(r'<strong>\1</strong>', result)
    result = INLINE_ITALIC_RE.sub(r'<em>\1</em>', result)
    result = INLINE_CODE_RE.sub(lambda match: f'<code>{html.escape(match.group(1))}</code>', result)
    return result



def _clean_inline_target(target: str) -> str:
    target = target.strip()
    if target.startswith('<') and target.endswith('>'):
        return target[1:-1].strip()
    return target



def _slugify(text: str) -> str:
    slug = text.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    return slug.strip('-')



def _build_toc_html(headings: list[tuple[int, str]], max_level: int = 3) -> str:
    if not headings:
        return ''

    items = []
    for level, text in headings:
        if level > max_level:
            continue
        heading_id = _slugify(text)
        indent = (level - 1) * 20
        items.append(
            f'<li style="margin-left:{indent}px">'
            f'<a href="#{heading_id}">{_process_inline(text)}</a></li>'
        )

    if not items:
        return ''

    return (
        '<nav id="toc" aria-label="Table of Contents">\n'
        '<h2>Table of Contents</h2>\n'
        '<ol>\n' + '\n'.join(items) + '\n</ol>\n'
        '</nav>\n<div class="page-break"></div>\n'
    )



def _build_running_header(text: str) -> str:
    if not text:
        return ''
    escaped = html.escape(text).replace('"', '\\"')
    return f'@top-left {{ content: "{escaped}"; }}'



def _build_running_footer(text: str) -> str:
    if not text:
        return ''

    parts = []
    cursor = 0
    for match in re.finditer(r'\{page\}|\{pages\}', text):
        literal = text[cursor:match.start()]
        if literal:
            parts.append(_css_string_literal(literal))
        parts.append('counter(page)' if match.group(0) == '{page}' else 'counter(pages)')
        cursor = match.end()

    tail = text[cursor:]
    if tail:
        parts.append(_css_string_literal(tail))

    if not parts:
        parts = ['""']

    return '@bottom-right { content: ' + ' '.join(parts) + '; }'


def _css_string_literal(text: str) -> str:
    escaped = html.escape(text).replace('"', '\\"')
    return f'"{escaped}"'



def _parse_frontmatter(raw: str) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    for line in raw.splitlines():
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if value.startswith('[') and value.endswith(']'):
            items = [item.strip().strip('"').strip("'") for item in value[1:-1].split(',') if item.strip()]
            meta[key] = items
        elif value.lower() in {'true', 'false'}:
            meta[key] = value.lower() == 'true'
        else:
            meta[key] = value
    return meta



def _coerce_frontmatter_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}



def _download_image(url: str, local_dir: str) -> str:
    os.makedirs(local_dir, exist_ok=True)
    extension = os.path.splitext(url.split('?')[0].split('/')[-1])[1] or '.png'
    digest = hashlib.md5(url.encode('utf-8')).hexdigest()[:12]
    local_path = os.path.join(local_dir, f'img_{digest}{extension}')

    if os.path.exists(local_path):
        return local_path

    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'text2pdf/0.1'})
        with urllib.request.urlopen(request, timeout=15) as response, open(local_path, 'wb') as handle:
            handle.write(response.read())
        return local_path
    except Exception:
        return url


# ---------------------------------------------------------------------------
# HTML document template
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="author" content="{author}">
  <meta name="subject" content="{subject}">
  <meta name="keywords" content="{keywords}">
  <title>{title}</title>
  <style>
{css}

@page {{
  size: {page_size};
  margin: 20mm 18mm 25mm 18mm;

  /* Running header */
  {header_html}

  /* Running footer */
  {footer_html}
}}

/* Base typography */
body {{
  font-family: "DejaVu Serif", "Times New Roman", Georgia, serif;
  font-size: 10.5pt;
  line-height: 1.6;
  color: #222;
  margin: 0;
  padding: 0;
  font-feature-settings: "kern" 1, "liga" 1, "onum" 1;
}}

/* Headings */
h1, h2, h3, h4, h5, h6 {{
  font-family: "DejaVu Sans", Arial, "Helvetica Neue", sans-serif;
  color: #1a1a1a;
  margin-top: 1.6em;
  margin-bottom: 0.5em;
  page-break-after: avoid;
}}
h1 {{ font-size: 1.6em; font-weight: 700; border-bottom: 2px solid #333; padding-bottom: 0.2em; }}
h2 {{ font-size: 1.3em; font-weight: 600; border-bottom: 1px solid #aaa; padding-bottom: 0.1em; }}
h3 {{ font-size: 1.1em; font-weight: 600; }}
h4, h5, h6 {{ font-size: 1em; font-weight: 600; }}

/* Paragraphs */
p {{ margin: 0 0 0.7em 0; text-align: justify; orphans: 3; widows: 3; }}
p + p {{ text-indent: 1.5em; }}

/* Paragraphs after headings or page breaks get no indent */
h1 + p, h2 + p, h3 + p, h4 + p, h5 + p, h6 + p,
.page-break + p, #toc + p {{ text-indent: 0; }}

/* Lists */
ul, ol {{ margin: 0.5em 0 0.7em 0; padding-left: 2em; }}
li {{ margin-bottom: 0.3em; line-height: 1.5; }}

/* Blockquotes */
blockquote {{
  margin: 1em 2em;
  padding: 0.5em 1em;
  border-left: 4px solid #aaa;
  background: #f8f8f8;
  font-style: italic;
  color: #444;
}}

/* Code blocks */
pre {{
  background: #f4f4f4;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 0.8em 1em;
  font-family: "DejaVu Sans Mono", "Courier New", Courier, monospace;
  font-size: 0.88em;
  line-height: 1.4;
  margin: 1em 0;
  page-break-inside: avoid;
}}
code {{
  font-family: "DejaVu Sans Mono", "Courier New", Courier, monospace;
  font-size: 0.9em;
  background: #f4f4f4;
  padding: 0.1em 0.3em;
  border-radius: 3px;
}}
pre code {{ background: none; padding: 0; font-size: inherit; }}

/* Tables */
table {{
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
  font-size: 0.92em;
  page-break-inside: avoid;
}}
th {{
  background: #2c3e50;
  color: #fff;
  font-family: -apple-system, "Segoe UI", Arial, sans-serif;
  font-weight: 600;
  padding: 0.4em 0.7em;
  text-align: left;
  border: 1px solid #1a252f;
}}
td {{
  padding: 0.35em 0.7em;
  border: 1px solid #ccc;
  vertical-align: top;
}}
tr:nth-child(even) td {{ background: #f9f9f9; }}
tr:hover td {{ background: #f0f4f8; }}

/* Images */
img {{
  max-width: 100%;
  height: auto;
  display: block;
  margin: 1em auto;
  page-break-inside: avoid;
}}

/* Horizontal rules */
hr {{
  border: none;
  border-top: 1px solid #ccc;
  margin: 2em 0;
}}

/* Links */
a {{ color: #2c5aa0; text-decoration: underline; }}

/* Table of Contents */
#toc {{
  margin-bottom: 2em;
  page-break-after: always;
}}
#toc h2 {{ font-size: 1.2em; border-bottom: 1px solid #333; }}
#toc ol {{ list-style-type: decimal; padding-left: 1.5em; }}
#toc li {{ margin-bottom: 0.3em; }}
#toc a {{ text-decoration: none; color: #2c5aa0; }}

/* Page break utility */
.page-break {{ page-break-before: always; }}

/* Orphan/widow control for headings */
h1, h2, h3 {{ orphans: 2; widows: 2; }}

/* First paragraph drop cap (optional, activated per-theme) */
.drop-cap::first-letter {{
  font-size: 3.2em;
  float: left;
  line-height: 0.8;
  margin-right: 0.1em;
  margin-top: 0.05em;
  font-weight: bold;
}}
</style>
</head>
<body>
{body}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Legacy API helpers (for backwards compatibility)
# ---------------------------------------------------------------------------


def html_to_pdf(html_content: str, output_path: str, options: dict[str, Any] | None = None) -> None:
    """Convert HTML string to PDF using WeasyPrint."""
    from text2pdf.engines import weasyprint_engine

    weasyprint_engine.render(html_content, output_path, options or {})
