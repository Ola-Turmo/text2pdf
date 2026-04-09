from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from text2pdf.providers import gemini, minimax

DIRECTIVE_RE = re.compile(r'^\s*\[\[image:\s*(?P<body>.+?)\s*\]\]\s*$')
DEFAULT_PROVIDER = 'gemini'
DEFAULT_API_ENV = {
    'gemini': ('GEMINI_API_KEY', 'GOOGLE_API_KEY'),
    'minimax': ('MINIMAX_API_KEY',),
}
DEFAULT_MODEL = {
    'gemini': gemini.DEFAULT_MODEL,
    'minimax': minimax.DEFAULT_MODEL,
}


@dataclass(slots=True)
class ImageGenerationRequest:
    prompt: str
    output_path: Path
    provider: str = DEFAULT_PROVIDER
    model: str | None = None
    api_key: str | None = None
    api_key_env: str | None = None
    references: list[str] = field(default_factory=list)
    reference_type: str = 'character'
    aspect_ratio: str | None = None
    image_size: str | None = None
    width: int | None = None
    height: int | None = None
    prompt_optimizer: bool | None = None


@dataclass(slots=True)
class GeneratedImageResult:
    path: Path
    provider: str
    model: str
    mime_type: str
    response: dict[str, Any]


class ImageGenerationError(RuntimeError):
    """Raised when an image provider request fails."""



def generate_image(request: ImageGenerationRequest) -> GeneratedImageResult:
    provider = request.provider.lower().strip()
    if provider not in DEFAULT_MODEL:
        raise ImageGenerationError(f'Unsupported image provider: {request.provider}')

    api_key = _resolve_api_key(provider, request.api_key, request.api_key_env)
    request = replace(
        request,
        provider=provider,
        model=request.model or DEFAULT_MODEL[provider],
        api_key=api_key,
    )

    if provider == 'gemini':
        image_bytes, mime_type, response = gemini.generate(request)
    else:
        image_bytes, mime_type, response = minimax.generate(request)

    output_path = _resolve_output_path(request.output_path, mime_type)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)

    return GeneratedImageResult(
        path=output_path,
        provider=provider,
        model=request.model or DEFAULT_MODEL[provider],
        mime_type=mime_type,
        response=response,
    )



def process_image_directives(
    text: str,
    *,
    defaults: ImageGenerationRequest,
    output_dir: str | os.PathLike[str],
    relative_to: str | os.PathLike[str] | None = None,
) -> tuple[str, list[GeneratedImageResult]]:
    """Replace [[image: ...]] directives with generated local Markdown images."""
    target_dir = Path(output_dir)
    relative_base = Path(relative_to) if relative_to is not None else target_dir
    results: list[GeneratedImageResult] = []
    rewritten_lines: list[str] = []

    for line in text.splitlines():
        match = DIRECTIVE_RE.match(line)
        if not match:
            rewritten_lines.append(line)
            continue

        prompt, options = _parse_directive_body(match.group('body'))
        sequence = len(results) + 1
        output_path = target_dir / f'image_{sequence:03d}'
        request = replace(
            defaults,
            prompt=prompt,
            output_path=output_path,
            provider=options.get('provider', defaults.provider),
            model=options.get('model', defaults.model),
            references=_split_csv(options.get('reference')) or list(defaults.references),
            reference_type=options.get('reference_type', defaults.reference_type),
            aspect_ratio=options.get('aspect', defaults.aspect_ratio),
            image_size=options.get('size', defaults.image_size),
            width=_parse_optional_int(options.get('width'), defaults.width),
            height=_parse_optional_int(options.get('height'), defaults.height),
            prompt_optimizer=_parse_optional_bool(options.get('prompt_optimizer'), defaults.prompt_optimizer),
            api_key=options.get('api_key', defaults.api_key),
            api_key_env=options.get('api_key_env', defaults.api_key_env),
        )
        result = generate_image(request)
        results.append(result)

        alt_text = options.get('alt', prompt)
        relative_path = os.path.relpath(result.path, relative_base).replace('\\', '/')
        rewritten_lines.append(f'![{alt_text}]({relative_path})')

    return '\n'.join(rewritten_lines), results



def build_default_output_path(prompt: str, directory: str | os.PathLike[str] = '.') -> Path:
    return Path(directory) / _slugify_filename(prompt)



def _resolve_output_path(output_path: Path, mime_type: str) -> Path:
    if output_path.suffix:
        return output_path
    extension = {
        'image/png': '.png',
        'image/jpeg': '.jpg',
        'image/webp': '.webp',
    }.get(mime_type, '.png')
    return output_path.with_suffix(extension)



def _resolve_api_key(provider: str, api_key: str | None, api_key_env: str | None) -> str:
    if api_key:
        return api_key

    env_names = [api_key_env] if api_key_env else list(DEFAULT_API_ENV[provider])
    for env_name in env_names:
        if not env_name:
            continue
        value = os.environ.get(env_name)
        if value:
            return value

    if api_key_env:
        raise ImageGenerationError(f'Missing image API key in environment variable: {api_key_env}')

    expected = ', '.join(DEFAULT_API_ENV[provider])
    raise ImageGenerationError(f'Missing API key for provider {provider}. Set one of: {expected}')



def _parse_directive_body(body: str) -> tuple[str, dict[str, str]]:
    segments = [segment.strip() for segment in body.split('|') if segment.strip()]
    if not segments:
        raise ImageGenerationError('Image directive is empty')

    prompt = segments[0]
    options: dict[str, str] = {}
    for segment in segments[1:]:
        if '=' not in segment:
            raise ImageGenerationError(f'Invalid image directive option: {segment}')
        key, value = segment.split('=', 1)
        options[key.strip().lower()] = value.strip()
    return prompt, options



def _parse_optional_int(value: str | None, fallback: int | None) -> int | None:
    if value is None or value == '':
        return fallback
    return int(value)



def _parse_optional_bool(value: str | None, fallback: bool | None) -> bool | None:
    if value is None or value == '':
        return fallback
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}



def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]



def _slugify_filename(prompt: str, limit: int = 48) -> str:
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', prompt).strip('-').lower()
    slug = slug[:limit] or 'generated-image'
    return slug
