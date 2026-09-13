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
    published = {
        path.relative_to(DATA).as_posix()
        for path in [*DATA.glob("*_std.parquet"), *DATA.glob("elections/*.parquet")]
    }

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


def test_geographic_inputs_match_the_attributed_snapshots():
    folder = ROOT / "data" / "source" / "geography"
    manifest = json.loads((folder / "MANIFEST.json").read_text())
    assert {p.name for p in folder.glob("*.csv")} == {
        entry["file"] for entry in manifest["files"]
    }
    for entry in manifest["files"]:
        assert sha256(folder / entry["file"]) == entry["sha256"]
        assert len(entry["source_revision"]) == 40


def test_missing_gp_attributes_remain_missing():
    for year in (2005, 2010):
        table = pq.read_table(DATA / f"source_{year}_std.parquet").to_pandas()
        assert table.winner_female.isna().sum() == {2005: 1, 2010: 12}[year]
        missing_reservation = table.reservation_raw.isna()
        assert table.loc[missing_reservation, "female_reserved"].isna().all()
        assert missing_reservation.sum() == {2005: 0, 2010: 1}[year]
