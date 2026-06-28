"""
Render PDF pages as PNG images.

Usage:
    python scripts/pdf_render.py                    # render all PDFs
    python scripts/pdf_render.py 1756-pm019_-en-p   # render one PDF
    python scripts/pdf_render.py --dpi 300          # custom DPI
"""

import sys
from pathlib import Path

import fitz  # pymupdf

PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
DPI = 150


def render_pdf(pdf_path: Path, dpi: int = DPI):
    stem = pdf_path.stem
    out_dir = DOCS_DIR / f"{stem}_pages"
    out_dir.mkdir(exist_ok=True)

    doc = fitz.open(pdf_path)
    pages = len(doc)

    for i in range(pages):
        page = doc[i]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        out_path = out_dir / f"page_{i + 1:04d}.png"
        pix.save(out_path)

    doc.close()

    total_bytes = sum(f.stat().st_size for f in out_dir.iterdir() if f.suffix == ".png")
    total_mb = total_bytes / (1024 * 1024)
    print(f"{stem}: {pages} pages -> {out_dir.name}/ ({total_mb:.1f} MB)")


def main():
    dpi = DPI
    args = []
    for a in sys.argv[1:]:
        if a == "--dpi" or a.startswith("--dpi="):
            if "=" in a:
                dpi = int(a.split("=")[1])
        elif not a.startswith("--"):
            args.append(a)

    if args:
        pdfs = [DOCS_DIR / (f"{a}.pdf" if not a.endswith(".pdf") else a) for a in args]
    else:
        pdfs = sorted(DOCS_DIR.glob("*.pdf"))

    for pdf_path in pdfs:
        if pdf_path.exists():
            render_pdf(pdf_path, dpi)
        else:
            print(f"SKIP: {pdf_path.name} not found")


if __name__ == "__main__":
    main()
