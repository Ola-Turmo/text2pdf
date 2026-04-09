---
title: "Sample Project Report"
author: "text2pdf"
toc: true
---

# Executive Summary

text2pdf converts lightweight source documents into printable PDFs. This sample file demonstrates headings, paragraphs, lists, tables, blockquotes, and code blocks in one small document.

## Highlights

- Automatic structure detection for plain text and Markdown-like documents
- Built-in themes for reports, academic drafts, ebooks, and modern docs
- Optional AI image generation through Gemini and MiniMax
- Optional remote image embedding for existing Markdown documents

## Example Table

| Area | Status | Notes |
|------|--------|-------|
| Packaging | Fixed | The project now installs as a real Python package |
| Rendering | Working | Verified with Pandoc and MiKTeX on Windows |
| Images | Added | Standalone and inline generation are supported |

## Example Quote

> The main goal is practical output: turn source text into a PDF without requiring a word processor.

# Implementation Notes

The parser preserves source order and recognizes fenced code blocks correctly.

## Example Code

```python
def build_report(title: str) -> str:
    return f"Report: {title}"
```

## Closing Notes

Use `text2pdf convert examples/sample-report.md -o examples/sample-report.pdf --engine pandoc` to regenerate the PDF on a Windows machine with Pandoc and MiKTeX installed.