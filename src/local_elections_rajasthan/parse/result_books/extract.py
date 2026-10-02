"""Retain positioned text from the held 2005 and 2010 SEC result books.

This command only extracts words and their source coordinates for each book's
result-table pages. The book's parser interprets the columns.
"""

import argparse
import hashlib
import json
import os
import pathlib
import tempfile

import pdfplumber

from local_elections_rajasthan.parse.result_books.books import BOOKS
from local_elections_rajasthan.runlog import get_logger

LOGGER = get_logger(__name__)


def sha256(path):
    """Return the SHA-256 of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_page(page, source_page, book):
    """Return source-faithful words for one PDF page."""
    attributes = ["fontname", "size"] if book.font_attributes else []
    words = []
    for word in page.extract_words(extra_attrs=attributes):
        record = {
            "text": word["text"],
            "x0": round(word["x0"], 3),
            "top": round(word["top"], 3),
        }
        if book.font_attributes:
            record["fontname"] = word["fontname"]
            record["size"] = round(word["size"], 3)
        words.append(record)
    return {
        "source_path": book.source_relative,
        "source_sha256": book.source_sha256,
        "source_page": source_page,
        "width": round(page.width, 3),
        "height": round(page.height, 3),
        "words": words,
    }


def extract(book, source=None):
    """Extract the book's reviewed result-table interval into page records."""
    source = source or book.source
    got_hash = sha256(source)
    if got_hash != book.source_sha256:
        raise SystemExit(
            f"source SHA-256 is {got_hash}, expected {book.source_sha256}; "
            "review the changed publication before extracting it"
        )
    records = []
    with pdfplumber.open(source) as pdf:
        if not 1 <= book.first_page <= book.last_page <= len(pdf.pages):
            raise SystemExit(
                f"invalid page interval {book.first_page}-{book.last_page} for "
                f"a {len(pdf.pages)}-page source"
            )
        for source_page in range(book.first_page, book.last_page + 1):
            records.append(extract_page(pdf.pages[source_page - 1], source_page, book))
            if source_page == book.first_page or source_page % 10 == 0:
                LOGGER.info(
                    "source page extracted",
                    extra={
                        "event": "source_page_extracted",
                        "source_path": book.source_relative,
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
    """Extract every held book, or one book to a chosen path."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", choices=sorted(BOOKS), help="extract only this book")
    parser.add_argument("--source", type=pathlib.Path, help="source PDF (with --book)")
    parser.add_argument(
        "--output", type=pathlib.Path, help="output JSON Lines (with --book)"
    )
    args = parser.parse_args(argv)
    if (args.source or args.output) and not args.book:
        parser.error("--source and --output need --book")
    books = [BOOKS[args.book]] if args.book else list(BOOKS.values())
    for book in books:
        output = args.output or book.extracted
        LOGGER.info(
            "extraction started",
            extra={
                "event": "extraction_started",
                "book": book.key,
                "output_path": str(output),
            },
        )
        records = extract(book, args.source)
        write_jsonl(records, output)
        LOGGER.info(
            "extraction completed",
            extra={
                "event": "extraction_completed",
                "book": book.key,
                "output_path": str(output),
                "pages": len(records),
                "words": sum(len(record["words"]) for record in records),
            },
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
