from __future__ import annotations

import base64
import json
import mimetypes
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_MODEL = 'gemini-2.5-flash-image'
API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'


class GeminiApiError(RuntimeError):
    """Raised when the Gemini image API returns an error."""



def generate(request) -> tuple[bytes, str, dict[str, Any]]:
    payload = {
        'contents': [
            {
                'parts': _build_parts(request),
            }
        ],
        'generationConfig': {
            'responseModalities': ['IMAGE'],
        },
    }

    image_config: dict[str, Any] = {}
    if request.aspect_ratio:
        image_config['aspectRatio'] = request.aspect_ratio
    if request.image_size and _supports_image_size(request.model):
        image_config['imageSize'] = request.image_size
    if image_config:
        payload['generationConfig']['imageConfig'] = image_config

    url = API_URL.format(model=urllib.parse.quote(request.model, safe=''))
    data = json.dumps(payload).encode('utf-8')
    http_request = urllib.request.Request(
        url,
        data=data,
        method='POST',
        headers={
            'Content-Type': 'application/json',
            'x-goog-api-key': request.api_key,
        },
    )

    try:
        with urllib.request.urlopen(http_request, timeout=120) as response:
            body = response.read().decode('utf-8')
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        raise GeminiApiError(f'Gemini request failed with HTTP {exc.code}: {detail}') from exc

    parsed = json.loads(body)
    image_part = _extract_image_part(parsed)
    if not image_part:
        raise GeminiApiError(f'Gemini did not return an image payload: {parsed}')

    inline_data = image_part.get('inlineData') or image_part.get('inline_data')
    mime_type = inline_data.get('mimeType') or inline_data.get('mime_type') or 'image/png'
    raw_data = inline_data.get('data')
    if not raw_data:
        raise GeminiApiError(f'Gemini image payload is missing data: {parsed}')

    return base64.b64decode(raw_data), mime_type, parsed



def _build_parts(request) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    for reference in request.references:
        payload_bytes, mime_type = _read_reference(reference)
        parts.append(
            {
                'inline_data': {
                    'mime_type': mime_type,
                    'data': base64.b64encode(payload_bytes).decode('ascii'),
                }
            }
        )
    parts.append({'text': request.prompt})
    return parts



def _read_reference(reference: str) -> tuple[bytes, str]:
    if reference.startswith(('http://', 'https://')):
        with urllib.request.urlopen(reference, timeout=60) as response:
            payload = response.read()
            mime_type = response.headers.get_content_type() or 'image/png'
            return payload, mime_type

    path = Path(reference)
    if not path.exists():
        raise GeminiApiError(f'Reference image not found: {reference}')

    mime_type, _ = mimetypes.guess_type(path.name)
    return path.read_bytes(), mime_type or 'image/png'



def _extract_image_part(response: dict[str, Any]) -> dict[str, Any] | None:
    for candidate in response.get('candidates', []):
        content = candidate.get('content', {})
        for part in content.get('parts', []):
            if 'inlineData' in part or 'inline_data' in part:
                return part
    return None



def _supports_image_size(model: str) -> bool:
    return model.startswith('gemini-3.')
