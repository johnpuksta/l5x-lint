"""
Analyze PDF structure: images, vectors, metadata.

Usage:
    python scripts/pdf_analyze.py                    # analyze all PDFs
    python scripts/pdf_analyze.py 1756-pm019_-en-p   # analyze one PDF
"""

import sys
from pathlib import Path

import fitz  # pymupdf

PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"


def analyze_pdf(pdf_path: Path):
    doc = fitz.open(pdf_path)
    stem = pdf_path.stem
    total_pages = len(doc)

    print(f"\n{'=' * 60}")
    print(f"{stem} ({total_pages} pages)")
    print(f"{'=' * 60}")

    total_images = 0
    total_vectors = 0

    for i in range(total_pages):
        page = doc[i]
        imgs = page.get_images()
        drawings = page.get_drawings()
        total_images += len(imgs)
        total_vectors += len(drawings)

        if i < 10 and (imgs or drawings):
            print(f"  Page {i + 1}: {len(imgs)} images, {len(drawings)} vectors")

    print(f"\n  Totals: {total_images} images, {total_vectors} vector paths")

    # Sample a page with images
    for i in range(min(5, total_pages)):
        imgs = doc[i].get_images()
        if imgs:
            print(f"\n  Sample images (page {i + 1}):")
            for img in imgs[:5]:
                xref = img[0]
                base = doc.extract_image(xref)
                print(
                    f"    xref={xref}, {base['ext']}, "
                    f"{base['width']}x{base['height']}, "
                    f"{len(base['image'])} bytes"
                )
            break

    doc.close()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if args:
        pdfs = [DOCS_DIR / (f"{a}.pdf" if not a.endswith(".pdf") else a) for a in args]
    else:
        pdfs = sorted(DOCS_DIR.glob("*.pdf"))

    for pdf_path in pdfs:
        if pdf_path.exists():
            analyze_pdf(pdf_path)
        else:
            print(f"SKIP: {pdf_path.name} not found")


if __name__ == "__main__":
    main()
