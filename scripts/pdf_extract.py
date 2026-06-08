"""
Extract text + image descriptions from PDFs using PyMuPDF + llama.cpp vision model.

Usage:
    python scripts/pdf_extract.py                    # process all PDFs
    python scripts/pdf_extract.py 1756-pm019_-en-p   # process one PDF
    python scripts/pdf_extract.py --dry-run           # preview without API calls

Requires:
    A llama.cpp server running with a vision model, e.g.:
    llama-server --model Qwen3-VL-8B-Q4_K_M.gguf --mmproj mmproj-Qwen3-VL-8B.gguf --port 8080
"""

import base64
import os
import sys
import time
from pathlib import Path

import fitz  # pymupdf
from openai import OpenAI

PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
SERVER_URL = os.environ.get("LLAMA_SERVER_URL", "http://localhost:8080")
MODEL_NAME = os.environ.get("VISION_MODEL", "default")
DPI = 150
MAX_TOKENS = 2048
PROMPT = (
    "You are analyzing a page from a technical Rockwell Automation / Allen-Bradley manual. "
    "Extract ALL text on the page verbatim. Then describe any diagrams, tables, schematics, "
    "wiring diagrams, module layouts, screenshots, or other visual content in detail. "
    "For diagrams: describe components, connections, labels, and structure. "
    "For tables: reproduce the table in markdown. "
    "Be thorough — this content will be used as context for an LLM."
)


def get_client():
    return OpenAI(base_url=f"{SERVER_URL}/v1", api_key="not-needed")


def describe_page(
    client: OpenAI, image_b64: str, page_num: int, retries: int = 2
) -> str:
    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                max_tokens=MAX_TOKENS,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_b64}",
                                },
                            },
                        ],
                    }
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt < retries:
                wait = 2 ** (attempt + 1)
                print(
                    f"    Retry {attempt + 1}/{retries} after error: {e} (waiting {wait}s)"
                )
                time.sleep(wait)
            else:
                return f"[ERROR: Could not describe page {page_num}: {e}]"


def process_pdf(pdf_name: str, client: OpenAI, dry_run: bool = False):
    stem = pdf_name.replace(".pdf", "")
    pdf_path = DOCS_DIR / pdf_name
    pages_dir = DOCS_DIR / f"{stem}_pages"
    txt_path = DOCS_DIR / f"{stem}.txt"
    out_path = DOCS_DIR / f"{stem}_context.md"

    if not pdf_path.exists():
        print(f"SKIP: {pdf_name} not found")
        return

    if not pages_dir.exists():
        print(f"SKIP: {pages_dir.name} not found — run pdf_render.py first")
        return

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    text_content = ""
    if txt_path.exists():
        text_content = txt_path.read_text(encoding="utf-8")

    if dry_run:
        print(f"DRY RUN: {stem} — {total_pages} pages, text={len(text_content)} chars")
        return

    print(f"Processing {stem} ({total_pages} pages)...")

    sections = []
    for i in range(total_pages):
        page_num = i + 1
        page_img = pages_dir / f"page_{page_num:04d}.png"

        if not page_img.exists():
            print(f"  Page {page_num}: image not found, skipping")
            continue

        # Extract text for this page
        page_text = ""
        if text_content:
            markers = text_content.split(f"--- Page {page_num} ---")
            if len(markers) > 1:
                page_text = markers[1].split(f"--- Page {page_num + 1} ---")[0].strip()

        # Send page image to vision model
        print(
            f"  Page {page_num}/{total_pages}: sending to vision model...",
            end="",
            flush=True,
        )
        t0 = time.time()
        image_b64 = base64.b64encode(page_img.read_bytes()).decode("utf-8")
        description = describe_page(client, image_b64, page_num)
        elapsed = time.time() - t0
        print(f" done ({elapsed:.1f}s, {len(description)} chars)")

        # Build section: text + vision description
        section = f"## Page {page_num}\n\n"
        if page_text:
            section += f"### Extracted Text\n\n{page_text}\n\n"
        section += f"### Visual Content Description\n\n{description}\n"
        sections.append(section)

    # Write combined context file
    header = (
        f"# {stem}\n\n"
        f"Source: {pdf_name} ({total_pages} pages)\n"
        f"Extracted with: PyMuPDF (text) + llama.cpp vision model (diagrams)\n\n"
        f"---\n\n"
    )
    out_path.write_text(header + "\n\n".join(sections), encoding="utf-8")
    print(f"  -> {out_path.name} ({out_path.stat().st_size / 1024:.1f} KB)")


def main():
    dry_run = "--dry-run" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if args:
        pdfs = [f"{a}.pdf" if not a.endswith(".pdf") else a for a in args]
    else:
        pdfs = sorted(f.name for f in DOCS_DIR.glob("*.pdf"))

    if dry_run:
        print("=== DRY RUN ===\n")

    client = get_client()

    for pdf_name in pdfs:
        process_pdf(pdf_name, client, dry_run=dry_run)
        print()


if __name__ == "__main__":
    main()
