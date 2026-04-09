"""WeasyPrint PDF engine."""

from __future__ import annotations

import logging
import os
import warnings
import io
from contextlib import redirect_stderr, redirect_stdout

logger = logging.getLogger(__name__)
_WEASYPRINT = None
_WEASYPRINT_ERROR = None



def _load_weasyprint():
    global _WEASYPRINT, _WEASYPRINT_ERROR
    if _WEASYPRINT is not None:
        return _WEASYPRINT
    if _WEASYPRINT_ERROR is not None:
        return None

    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            import weasyprint as module
    except (ImportError, OSError) as exc:
        _WEASYPRINT_ERROR = exc
        return None

    _WEASYPRINT = module
    return module



def is_available() -> bool:
    return _load_weasyprint() is not None



def get_version() -> str:
    module = _load_weasyprint()
    if module is None:
        return 'not installed'
    return getattr(module, '__version__', 'unknown')



def render(html_content: str, output_path: str, options: dict | None = None) -> None:
    module = _load_weasyprint()
    if module is None:
        raise RuntimeError(
            'WeasyPrint is not installed or its native dependencies are missing. '
            'Install WeasyPrint plus the platform libraries required by Cairo/Pango.'
        )

    opts = options or {}

    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', category=UserWarning)
        warnings.filterwarnings('ignore', message='.*Unsupported.*')

        doc = module.HTML(string=html_content)
        stylesheets = []
        for path in opts.get('css_files', []):
            if os.path.exists(path):
                stylesheets.append(module.CSS(string=open(path, 'r', encoding='utf-8').read()))

        logger.info('Rendering PDF via WeasyPrint (%s extra CSS files)', len(stylesheets))
        doc.write_pdf(
            output_path,
            presentational_hints=opts.get('presentational_hints', True),
            stylesheets=stylesheets or None,
        )
        logger.info('PDF written to %s', output_path)



def html_to_pdf(html_content: str, output_path: str, options: dict | None = None) -> None:
    render(html_content, output_path, options)
