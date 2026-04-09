"""Allow running text2pdf as: python -m text2pdf."""

from text2pdf.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
