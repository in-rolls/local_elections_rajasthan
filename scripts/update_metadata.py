"""Regenerate metadata for the standardized and canonical election products."""

import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq

DATA = Path(__file__).resolve().parents[1] / "data" / "fin"


def main():
    schema = {}
    paths = sorted([*DATA.glob("*_std.parquet"), *DATA.glob("elections/*.parquet")])
    for path in paths:
        parquet = pq.ParquetFile(path)
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        schema[path.relative_to(DATA).as_posix()] = {
            "sha256": digest,
            "rows": parquet.metadata.num_rows,
            "cols": parquet.metadata.num_columns,
            "bytes": path.stat().st_size,
            "columns": parquet.schema_arrow.names,
        }
    (DATA / "SCHEMA.json").write_text(json.dumps(schema, indent=2) + "\n")
    (DATA / "CHECKSUMS.sha256").write_text(
        "".join(f"{entry['sha256']}  {name}\n" for name, entry in schema.items())
    )


if __name__ == "__main__":
    main()
