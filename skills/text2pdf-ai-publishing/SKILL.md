---
name: text2pdf-ai-publishing
description: Use when working on the text2pdf repository to convert structured text into PDFs, generate inline AI images for report-style documents, regenerate the bundled examples, or explain the repo's full feature scope and usage. Trigger for requests about image-rich PDF examples, Windows setup for Pandoc or MiKTeX, text2pdf CLI usage, or maintaining this repo's publishing workflow.
---

# text2pdf AI Publishing

This skill is for the `text2pdf` repository. It covers the full feature scope of the project and the practical command paths needed to use, demo, and extend it.

## Use This Skill When

- The task is about the `text2pdf` repo itself
- The user wants a PDF example regenerated or improved
- The user wants a document with AI-generated images
- The user needs Windows setup guidance for `pandoc`, `MiKTeX`, or WeasyPrint
- The user wants the repo's capabilities summarized with working commands

## Core Scope

`text2pdf` currently supports:

- Plain text, Markdown, HTML, and basic reStructuredText input
- Structure detection for headings, paragraphs, lists, blockquotes, tables, code blocks, and images
- Theme-based HTML-to-PDF styling
- PDF rendering through WeasyPrint or Pandoc
- Inline remote image download with `--embed-images`
- AI image generation through Gemini and MiniMax
- Inline `[[image: ...]]` directives during `convert`
- Standalone `text2pdf image` generation

## Repository Map

- `text2pdf/cli.py`: CLI entrypoints and argument parsing
- `text2pdf/structure.py`: parsing, normalization, HTML generation
- `text2pdf/engines/`: PDF backends
- `text2pdf/imagegen.py`: provider routing and inline directive processing
- `text2pdf/providers/`: Gemini and MiniMax integrations
- `text2pdf/themes/`: built-in CSS themes
- `examples/`: source documents and generated example artifacts

For command patterns and regeneration steps, read [references/usage.md](references/usage.md).

## Working Rules

1. Check `text2pdf engines` before assuming a local PDF backend works.
2. On Windows, prefer `pandoc` plus `MiKTeX` when WeasyPrint native libraries are missing.
3. For image-rich examples, keep the Markdown source with `[[image: ...]]` directives and commit the generated example assets separately.
4. Prefer Gemini for straightforward photorealistic examples unless the task specifically needs MiniMax behavior.
5. Keep user-facing docs synchronized with actual commands and example files in `examples/`.

## Example Workflow

1. Verify local engines and environment variables.
2. Edit or create the Markdown source under `examples/`.
3. Run `text2pdf convert ... --generate-images ...`.
4. Generate preview PNGs from the resulting PDF if the repo examples need visual assets.
5. Update repo docs if commands, paths, or setup steps changed.

## Validation

- Run `pytest -q`
- Rebuild the relevant example PDF
- If the example uses AI images, confirm the generated image assets exist and the PDF render succeeds