# text2pdf

text2pdf converts plain text, Markdown, HTML, or reStructuredText into PDFs with automatic structure detection, built-in themes, optional remote image embedding, and optional AI image generation.

## What It Does

- Detects headings, paragraphs, lists, blockquotes, code blocks, tables, and images
- Preserves source block order in the generated document
- Generates a table of contents from detected headings
- Supports running headers and footers with page counters
- Ships four built-in themes: `report`, `academic`, `modern`, `ebook`
- Accepts custom CSS on top of the built-in themes
- Downloads and rewrites remote image URLs when `--embed-images` is enabled
- Generates images through Gemini or MiniMax when `--generate-images` is enabled
- Exposes a standalone `text2pdf image` command for direct image generation
- Works as both `text2pdf ...` and `python -m text2pdf ...`

## Requirements

- Python 3.10+
- One PDF engine:
  - WeasyPrint with its native system libraries, or
  - Pandoc plus a TeX engine such as MiKTeX

## Installation

Basic install:

```bash
pip install weasyprint markdown
pip install /path/to/text2pdf
```

Development install:

```bash
git clone https://github.com/Ola-Turmo/text2pdf.git
cd text2pdf
pip install -e .[dev]
```

## PDF Engines

text2pdf supports two rendering backends.

### WeasyPrint

Best fit when you want the built-in CSS themes, paged-media styling, and predictable HTML-to-PDF output.

Python dependency:

```bash
pip install weasyprint
```

Important: On Windows, the Python package alone is not enough. You also need the native GTK/Pango/Cairo runtime libraries required by WeasyPrint.

### Pandoc

Useful when you already have a TeX toolchain installed or want Pandoc's document conversion path.

Requirements:

- `pandoc` on `PATH`
- A PDF engine such as `pdflatex`, `xelatex`, or `lualatex` on `PATH`

text2pdf uses Pandoc's LaTeX route first. If that fails and WeasyPrint is available, it falls back to Pandoc HTML plus WeasyPrint.

## Windows Setup

This is the simplest Windows path if you want a working PDF engine without debugging WeasyPrint's GTK stack.

### Option A: Pandoc plus MiKTeX

Install both with `winget`:

```powershell
winget install --id JohnMacFarlane.Pandoc -e --accept-package-agreements --accept-source-agreements --silent
winget install --id MiKTeX.MiKTeX -e --accept-package-agreements --accept-source-agreements --silent
```

After installation, restart your shell so the new PATH entries are visible.

For MiKTeX, enable automatic package installation so first-run LaTeX renders do not block on prompts:

```powershell
initexmf --set-config-value=[MPM]AutoInstall=1
initexmf --enable-installer
```

If those commands are not yet on `PATH`, the MiKTeX default binary directory is usually:

```text
C:\Users\<you>\AppData\Local\Programs\MiKTeX\miktex\bin\x64
```

The Pandoc `winget` install used on this machine ended up under:

```text
C:\Users\<you>\AppData\Local\Microsoft\WinGet\Packages\JohnMacFarlane.Pandoc_Microsoft.Winget.Source_8wekyb3d8bbwe\pandoc-<version>
```

### Option B: WeasyPrint

Install the Python package:

```bash
pip install weasyprint
```

Then install the native libraries required by WeasyPrint for Windows. If those libraries are missing, `text2pdf engines` will report WeasyPrint as unavailable even though the Python package is installed.

## Quick Start

Basic conversion:

```bash
text2pdf convert input.txt -o output.pdf
```

Report with TOC and metadata:

```bash
text2pdf convert doc.txt -o output.pdf --theme report --toc --title "My Report" --author "Ola Turmo"
```

Disable the TOC:

```bash
text2pdf convert doc.txt -o output.pdf --no-toc
```

Inspect detected structure:

```bash
text2pdf detect doc.txt
```

Show installed engines:

```bash
text2pdf engines
```

Use the module entrypoint:

```bash
python -m text2pdf convert doc.md -o output.pdf
```

## Examples

Pre-generated example assets are included in [examples/README.md](examples/README.md).

- Source document: [examples/sample-report.md](examples/sample-report.md)
- Generated PDF: [examples/sample-report.pdf](examples/sample-report.pdf)
- Preview image: [examples/assets/sample-report-page1.png](examples/assets/sample-report-page1.png)
- AI image source: [examples/photo-field-report.md](examples/photo-field-report.md)
- AI image PDF: [examples/photo-field-report.pdf](examples/photo-field-report.pdf)
- AI image previews: [examples/assets/photo-field-report-page1.png](examples/assets/photo-field-report-page1.png) and [examples/assets/photo-field-report-page2.png](examples/assets/photo-field-report-page2.png)

## CLI Commands

```text
text2pdf convert <input> -o <output> [options]
text2pdf detect <input>
text2pdf engines
text2pdf image [prompt] [-o <output>] [options]
text2pdf help-format
```

### `convert`

```text
--engine [auto|weasyprint|pandoc]
--theme [report|academic|modern|ebook]
--page-size [A4|Letter|Legal|A5]
--toc / --no-toc
--header TEXT
--footer TEXT
--title TEXT
--author TEXT
--subject TEXT
--keywords TEXT
--language LANG
--css FILE.css
--embed-images
--generate-images
--image-dir DIR
--from [auto|markdown|plain|html|rst]
-v, --verbose
```

### `image`

```text
--image-provider [gemini|minimax]
--image-model MODEL
--image-api-key KEY
--image-api-key-env ENV_NAME
--image-reference PATH_OR_URL
--image-reference-type TYPE
--image-aspect-ratio RATIO
--image-size SIZE
--image-width PX
--image-height PX
--image-prompt-optimizer / --no-image-prompt-optimizer
--prompt-file FILE
-v, --verbose
```

## Input Formats

### Plain text and Markdown

text2pdf auto-detects structure. These markers work well:

````markdown
---
title: "My Document"
author: "Ola Turmo"
toc: true
---

# Chapter 1: Introduction

This is a paragraph. Separate paragraphs with blank lines.

## Section 1.1

- Bullet list item
- Another item

```python
def hello():
    print("world")
```

> This is a blockquote.

| Column A | Column B |
|----------|----------|
| Value 1  | Value 2  |

![Image caption](https://example.com/image.png)
````

### HTML

If the input is already HTML, text2pdf wraps it in a full document, injects theme CSS, and renders it.

### reStructuredText

Basic RST detection is supported. It goes through the same structure-to-HTML path used for plain text and Markdown-like input.

## Themes

| Theme | Best for |
|-------|----------|
| `report` | Business reports, technical docs, formal papers |
| `academic` | Double-spaced academic drafts |
| `modern` | Minimal documentation and clean internal docs |
| `ebook` | Long-form reading and compact printable books |

## AI Image Generation

Image generation is optional. The core text-to-PDF flow still works without any external image provider.

Supported providers:

- Gemini via `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- MiniMax via `MINIMAX_API_KEY`

The repository does not store provider keys. Set them in your shell environment.

### Standalone image generation

Gemini text-to-image:

```bash
text2pdf image "A clean Nordic book cover illustration" -o cover.png
```

Gemini with a prompt file:

```bash
text2pdf image --prompt-file prompt.txt -o cover.png
```

MiniMax with a remote reference image:

```bash
text2pdf image "Turn this into a cinematic poster" \
  --image-provider minimax \
  --image-reference https://example.com/reference.png \
  --image-width 1024 \
  --image-height 1024 \
  -o poster.jpg
```

Note: the current MiniMax image-to-image path accepts HTTP(S) reference URLs, not local files.

### Inline image directives during conversion

Enable image generation during conversion:

```bash
text2pdf convert report.md -o report.pdf --generate-images
```

Then place directives in the source file:

```markdown
# Travel Report

[[image: A cinematic fjord at sunrise | alt=Cover image | provider=gemini | aspect=16:9]]

This report describes the route and conditions.
```

Supported directive options:

- `alt=...`
- `provider=gemini|minimax`
- `model=...`
- `aspect=...`
- `size=1K|2K|4K` for Gemini preview image models that support size hints
- `reference=url1,url2`
- `reference_type=...`
- `width=...`
- `height=...`
- `prompt_optimizer=true|false`
- `api_key=...`
- `api_key_env=...`

Generated images are written into `--image-dir` or, by default, `<output>_assets`.

## Repo Skill

This repo now includes an installable local skill at [skills/text2pdf-ai-publishing/SKILL.md](skills/text2pdf-ai-publishing/SKILL.md).

It covers:

- the repo's functional scope
- when to use each engine
- how to regenerate the examples
- how to work with inline AI image directives
- the main command patterns for this project

It has also been installed locally into `C:\Users\heial\.codex\skills\text2pdf-ai-publishing`.

## Remote Image Embedding

If your source already contains remote image URLs, use:

```bash
text2pdf convert doc.md -o output.pdf --embed-images
```

This downloads the remote assets and rewrites the generated HTML to point at local files before rendering.

## Development

Run tests:

```bash
pytest -q
```

Install in editable mode:

```bash
pip install -e .[dev]
```

## Troubleshooting

### `text2pdf engines` shows no available engines

You do not currently have a usable PDF backend on `PATH`, or WeasyPrint is missing native system libraries.

### WeasyPrint says it is not available on Windows

That usually means the Python package is installed, but the GTK/Pango/Cairo runtime libraries are not.

### Pandoc is installed but PDF conversion still fails

Check all of the following:

- `pandoc --version` works in the same shell where you run `text2pdf`
- `pdflatex --version` works in the same shell
- MiKTeX automatic package installation is enabled
- The first Pandoc render may take longer because MiKTeX is downloading missing packages

### A fresh MiKTeX install takes a long time on first render

That is normal. The first PDF render often includes on-demand package installation.

### MiniMax reference images fail

The current MiniMax provider path accepts remote HTTP(S) references. Local file references are rejected for that provider.

## Architecture

```text
input.md
  -> text2pdf.structure.detect_structure()
  -> text2pdf.structure.convert_to_html()
  -> text2pdf.themes/*.css
  -> text2pdf.engines.weasyprint_engine or text2pdf.engines.pandoc_engine
  -> output.pdf
```

AI image generation is optional and is injected before structure detection when `--generate-images` is enabled.

## License

MIT License
