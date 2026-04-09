from __future__ import annotations

import mimetypes
import json
import urllib.error
import urllib.request
from typing import Any

DEFAULT_MODEL = 'image-01'
API_URL = 'https://api.minimax.io/v1/image_generation'


class MiniMaxApiError(RuntimeError):
    """Raised when the MiniMax image API returns an error."""



def generate(request) -> tuple[bytes, str, dict[str, Any]]:
    payload: dict[str, Any] = {
        'model': request.model,
        'prompt': request.prompt,
        'response_format': 'url',
        'n': 1,
    }
    if request.aspect_ratio:
        payload['aspect_ratio'] = request.aspect_ratio
    if request.width is not None:
        payload['width'] = request.width
    if request.height is not None:
        payload['height'] = request.height
    if request.prompt_optimizer is not None:
        payload['prompt_optimizer'] = request.prompt_optimizer
    if request.references:
        payload['subject_reference'] = [
            {
                'type': request.reference_type,
                'image_file': _validate_reference(reference),
            }
            for reference in request.references
        ]

    http_request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode('utf-8'),
        method='POST',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {request.api_key}',
        },
    )

    try:
        with urllib.request.urlopen(http_request, timeout=120) as response:
            body = response.read().decode('utf-8')
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        raise MiniMaxApiError(f'MiniMax request failed with HTTP {exc.code}: {detail}') from exc

    parsed = json.loads(body)
    image_urls = parsed.get('data', {}).get('image_urls') or []
    if not image_urls:
        raise MiniMaxApiError(f'MiniMax did not return any image URLs: {parsed}')

    image_url = image_urls[0]
    with urllib.request.urlopen(image_url, timeout=120) as response:
        image_bytes = response.read()
        mime_type = response.headers.get_content_type() or _guess_mime_type(image_url)

    return image_bytes, mime_type, parsed



def _validate_reference(reference: str) -> str:
    if not reference.startswith(('http://', 'https://')):
        raise MiniMaxApiError(
            'MiniMax image-to-image references must be HTTP(S) URLs, not local files.'
        )
    return reference



def _guess_mime_type(url: str) -> str:
    mime_type, _ = mimetypes.guess_type(url)
    return mime_type or 'image/png'
