"""Convert the four saved Rajasthan 2020-2022 scrape CSVs to Parquet."""

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = json.loads((ROOT / "scrape_columns.json").read_text())


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_source(path, columns):
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        if next(reader, None) != columns or len(set(columns)) != len(columns):
            raise ValueError(f"{path}: unexpected or duplicate headers")
        rows = []
        for number, values in enumerate(reader, 1):
            if len(values) != len(columns):
                raise ValueError(f"{path}:{number}: inconsistent column count")
            rows.append(dict(zip(columns, values, strict=True)))
    if not rows:
        raise ValueError(f"{path}: no data rows")
    return pa.Table.from_pylist(
        rows, schema=pa.schema([(c, pa.string()) for c in columns])
    )


def convert(data, out, check=False, contracts=CONTRACTS):
    manifest = {"format_version": 1, "files": []}
    out.mkdir(parents=True, exist_ok=True)
    for name, spec in contracts.items():
        source, target = data / name, out / spec["output"]
        table = read_source(source, spec["columns"])
        if check:
            if not table.equals(pq.read_table(target), check_metadata=True):
                raise ValueError(f"{target}: schema or values differ from source")
        else:
            temporary = target.with_suffix(".parquet.part")
            try:
                pq.write_table(table, temporary, compression="zstd")
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        manifest["files"].append(
            {
                "file": target.name,
                "sha256": digest(target),
                "rows": table.num_rows,
                "source": name,
                "source_sha256": digest(source),
                "columns": spec["columns"],
                "column_type": "string",
            }
        )
        print(f"{target.name}: {table.num_rows:,} rows")
    path = out / "MANIFEST.json"
    if check:
        if json.loads(path.read_text()) != manifest:
            raise ValueError(f"{path}: manifest differs from source")
    else:
        temporary = path.with_suffix(".json.part")
        temporary.write_text(json.dumps(manifest, indent=2) + "\n")
        temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--out", type=Path, default=ROOT / "data/fin/scrape_2020_2022")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        convert(args.data, args.out, args.check)
    except (ValueError, OSError, EOFError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
