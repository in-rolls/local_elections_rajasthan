"""Retain positioned text from the held 2010 Zila Parishad result book.

This command extracts source words and coordinates only. The separate parser
interprets the publication's result-table columns.
"""

import argparse
import hashlib
import json
import os
import pathlib
import tempfile

import pdfplumber

from scripts.runlog import get_logger

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/source/zilla_parishad/zila_parishad_2010.pdf"
OUTPUT = ROOT / "data/extracted/zila_parishad_2010_pages.jsonl"
SOURCE_RELATIVE = "data/source/zilla_parishad/zila_parishad_2010.pdf"
SOURCE_SHA256 = "4399f7b9943ff6f71b3c728c21a2161696675fcbf17d47138af1938ca10a0272"
FIRST_PAGE = 74
LAST_PAGE = 98

LOGGER = get_logger(__name__)


def sha256(path):
    """Return the SHA-256 of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_page(page, source_page):
    """Return source-faithful words for one PDF page."""
    words = [
        {
            "text": word["text"],
            "x0": round(word["x0"], 3),
            "top": round(word["top"], 3),
            "fontname": word["fontname"],
            "size": round(word["size"], 3),
        }
        for word in page.extract_words(extra_attrs=["fontname", "size"])
    ]
    return {
        "source_path": SOURCE_RELATIVE,
        "source_sha256": SOURCE_SHA256,
        "source_page": source_page,
        "width": round(page.width, 3),
        "height": round(page.height, 3),
        "words": words,
    }


def extract(source, first_page=FIRST_PAGE, last_page=LAST_PAGE):
    """Extract the reviewed result-table interval into page records."""
    got_hash = sha256(source)
    if got_hash != SOURCE_SHA256:
        raise SystemExit(
            f"source SHA-256 is {got_hash}, expected {SOURCE_SHA256}; "
            "review the changed publication before extracting it"
        )

    records = []
    with pdfplumber.open(source) as pdf:
        if not 1 <= first_page <= last_page <= len(pdf.pages):
            raise SystemExit(
                f"invalid page interval {first_page}-{last_page} for "
                f"a {len(pdf.pages)}-page source"
            )
        for source_page in range(first_page, last_page + 1):
            records.append(extract_page(pdf.pages[source_page - 1], source_page))
            LOGGER.info(
                "source page extracted",
                extra={
                    "event": "source_page_extracted",
                    "source_path": SOURCE_RELATIVE,
                    "source_page": source_page,
                },
            )
    return records


def write_jsonl(records, output):
    """Atomically write page records as JSON Lines."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=output.parent, delete=False
    ) as stream:
        temporary = pathlib.Path(stream.name)
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            stream.write("\n")
    os.replace(temporary, output)


def main(argv=None):
    """Extract the reviewed source interval without semantic parsing."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path, default=SOURCE)
    parser.add_argument("--output", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args(argv)

    LOGGER.info(
        "extraction started",
        extra={
            "event": "extraction_started",
            "source_path": str(args.source),
            "output_path": str(args.output),
            "first_page": FIRST_PAGE,
            "last_page": LAST_PAGE,
        },
    )
    records = extract(args.source)
    write_jsonl(records, args.output)
    LOGGER.info(
        "extraction completed",
        extra={
            "event": "extraction_completed",
            "output_path": str(args.output),
            "pages": len(records),
            "words": sum(len(record["words"]) for record in records),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
