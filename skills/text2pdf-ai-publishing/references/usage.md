# Usage

## Common Commands

Show available engines:

```powershell
text2pdf engines
```

Convert a basic document:

```powershell
text2pdf convert input.md -o output.pdf
```

Convert with inline AI images:

```powershell
text2pdf convert examples\photo-field-report.md `
  -o examples\photo-field-report.pdf `
  --engine pandoc `
  --theme report `
  --generate-images `
  --image-provider gemini `
  --image-dir examples\photo-field-report_assets
```

Generate a standalone image:

```powershell
text2pdf image "Photorealistic electric ferry in a Norwegian fjord" -o cover.png
```

Run tests:

```powershell
pytest -q
```

## Environment Variables

- `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- `MINIMAX_API_KEY`

## Windows Notes

- `pandoc` and `pdflatex` must be on `PATH`
- MiKTeX should have automatic package installation enabled
- If WeasyPrint reports unavailable, the Python package may be installed while the native GTK/Pango/Cairo stack is still missing

## Example Files

- `examples/sample-report.md`: non-AI sample
- `examples/photo-field-report.md`: photorealistic AI-image sample