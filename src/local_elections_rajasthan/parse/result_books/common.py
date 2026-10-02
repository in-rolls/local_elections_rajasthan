"""Helpers shared by the four result-book parsers."""

import json
import os
import pathlib
import tempfile

import pandas


def load_pages(path, book):
    """Load the book's extraction and check its page interval and provenance."""
    with path.open(encoding="utf-8") as stream:
        pages = [json.loads(line) for line in stream if line.strip()]
    page_numbers = [page["source_page"] for page in pages]
    expected_pages = list(range(book.first_page, book.last_page + 1))
    if page_numbers != expected_pages:
        raise SystemExit(
            f"extraction holds pages {page_numbers[:1]}..{page_numbers[-1:]}, "
            f"expected every page {book.first_page}..{book.last_page} in order"
        )
    bad_provenance = [
        page["source_page"]
        for page in pages
        if page.get("source_path") != book.source_relative
        or page.get("source_sha256") != book.source_sha256
    ]
    if bad_provenance:
        raise SystemExit(f"extraction provenance differs on pages {bad_provenance[:5]}")
    return pages


def cells(words, column_bounds):
    """Assign one positioned source line to the publication's columns."""
    return {
        name: " ".join(
            word["text"]
            for word in sorted(words, key=lambda item: item["x0"])
            if lower <= word["x0"] < upper
        ).strip()
        for name, lower, upper in column_bounds
    }


def normalize_party(raw):
    """Normalize the source's CPI(M) typography."""
    return "CPI(M)" if raw in {"CPI M", "CPI(M)"} else raw


def write_parquet(rows, output, columns, nullable_integer_columns=()):
    """Atomically write the analysis-ready seat table."""
    output.parent.mkdir(parents=True, exist_ok=True)
    frame = pandas.DataFrame(rows, columns=columns)
    for column in nullable_integer_columns:
        frame[column] = frame[column].astype("Int64")
    with tempfile.NamedTemporaryFile(
        dir=output.parent, suffix=".parquet", delete=False
    ) as stream:
        temporary = pathlib.Path(stream.name)
    try:
        frame.to_parquet(temporary, index=False)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
