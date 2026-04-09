"""Pandoc PDF engine."""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

PANDOC_AVAILABLE = False
PANDOC_VERSION = 'unknown'
try:
    result = subprocess.run(['pandoc', '--version'], capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        PANDOC_AVAILABLE = True
        PANDOC_VERSION = result.stdout.splitlines()[0].split()[1]
except Exception:
    pass


INPUT_FORMATS = {
    'markdown': 'markdown',
    'md': 'markdown',
    'plain': 'markdown',
    'rst': 'rst',
    'html': 'html',
}



def is_available() -> bool:
    return PANDOC_AVAILABLE



def get_version() -> str:
    return PANDOC_VERSION



def render(content: str, output_path: str, options: dict | None = None) -> None:
    if not PANDOC_AVAILABLE:
        raise RuntimeError(
            'Pandoc is not installed. Install it with:\n'
            '  sudo apt-get install pandoc\n'
            '  brew install pandoc\n'
            '  or download from https://pandoc.org/installing.html'
        )

    opts = options or {}
    input_format = INPUT_FORMATS.get(opts.get('input_format', 'markdown'), 'markdown')
    pdf_engine = opts.get('pdf_engine', 'pdflatex')
    toc = opts.get('toc', True)
    metadata = opts.get('metadata', {})
    template = opts.get('template', '')
    command_timeout = int(opts.get('command_timeout', 600))

    suffix = '.html' if input_format == 'html' else '.md'
    with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False, encoding='utf-8') as handle:
        handle.write(content)
        input_path = Path(handle.name)

    try:
        try:
            _render_via_latex(
                input_path=input_path,
                output_path=Path(output_path),
                input_format=input_format,
                pdf_engine=pdf_engine,
                toc=toc,
                metadata=metadata,
                template=template,
                command_timeout=command_timeout,
            )
            logger.info('PDF written via Pandoc LaTeX route to %s', output_path)
            return
        except Exception as exc:
            logger.warning('Pandoc LaTeX route failed (%s), trying HTML/WeasyPrint fallback', exc)

        _render_via_weasyprint(
            input_path=input_path,
            output_path=Path(output_path),
            input_format=input_format,
            toc=toc,
            command_timeout=command_timeout,
        )
        logger.info('PDF written via Pandoc HTML/WeasyPrint route to %s', output_path)
    finally:
        if input_path.exists():
            input_path.unlink()



def _render_via_latex(
    *,
    input_path: Path,
    output_path: Path,
    input_format: str,
    pdf_engine: str,
    toc: bool,
    metadata: dict,
    template: str,
    command_timeout: int,
) -> None:
    command = [
        'pandoc',
        str(input_path),
        '--from',
        input_format,
        '--output',
        str(output_path),
        f'--pdf-engine={pdf_engine}',
    ]
    if toc:
        command.append('--toc')
    if template and os.path.exists(template):
        command.extend(['--template', template])
    for key, value in metadata.items():
        if value:
            command.append(f'--metadata={key}={value}')

    result = subprocess.run(command, capture_output=True, text=True, timeout=command_timeout)
    if result.returncode != 0:
        raise RuntimeError(f'Pandoc (LaTeX) failed:\nstdout: {result.stdout}\nstderr: {result.stderr}')



def _render_via_weasyprint(
    *,
    input_path: Path,
    output_path: Path,
    input_format: str,
    toc: bool,
    command_timeout: int,
) -> None:
    html_path = output_path.with_suffix('.html')
    command = [
        'pandoc',
        str(input_path),
        '--from',
        input_format,
        '--to=html',
        '--standalone',
        '--output',
        str(html_path),
    ]
    if toc:
        command.append('--toc')

    result = subprocess.run(command, capture_output=True, text=True, timeout=command_timeout)
    if result.returncode != 0:
        raise RuntimeError(f'Pandoc (HTML) failed:\nstdout: {result.stdout}\nstderr: {result.stderr}')

    try:
        from text2pdf.engines import weasyprint_engine

        if not weasyprint_engine.is_available():
            raise RuntimeError('WeasyPrint is required for the Pandoc HTML fallback route')

        html_content = html_path.read_text(encoding='utf-8')
        page_css = (
            '<style>'
            '@page { size: A4; margin: 20mm 18mm 25mm 18mm; }'
            '@page { @bottom-right { content: "Page " counter(page) " of " counter(pages); font-size: 9pt; color: #555; } }'
            '</style>'
        )
        html_content = html_content.replace('</head>', page_css + '</head>')
        weasyprint_engine.render(html_content, str(output_path))
    finally:
        if html_path.exists():
            html_path.unlink()
