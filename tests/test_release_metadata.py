"""Contracts for the published Parquet metadata."""

import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).parents[1]
DATA = ROOT / "data" / "fin"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_schema_and_checksums_describe_every_published_parquet():
    schema = json.loads((DATA / "SCHEMA.json").read_text())
    checksums = {
        name: digest
        for digest, name in (
            line.split(maxsplit=1)
            for line in (DATA / "CHECKSUMS.sha256").read_text().splitlines()
            if line.strip()
        )
    }
    published = {path.name for path in DATA.glob("*_std.parquet")}

    assert set(schema) == published
    assert set(checksums) == published

    for name in sorted(published):
        path = DATA / name
        parquet = pq.ParquetFile(path)
        expected = schema[name]
        digest = sha256(path)

        assert checksums[name] == digest
        assert expected == {
            "sha256": digest,
            "rows": parquet.metadata.num_rows,
            "cols": parquet.metadata.num_columns,
            "bytes": path.stat().st_size,
            "columns": parquet.schema_arrow.names,
        }
