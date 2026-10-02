"""Regenerate metadata for the standardized and canonical election products."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from local_elections_rajasthan.build.common import save
from local_elections_rajasthan.build.standardize_sources import standardize
from local_elections_rajasthan.parse.scrape.convert import convert
from local_elections_rajasthan.paths import DATA, ROOT


def build():
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


UNITS = {
    "source_2005_std.parquet": "Gram Panchayat seat",
    "source_2010_std.parquet": "Gram Panchayat seat",
    "source_2015_std.parquet": "Gram Panchayat seat",
    "source_2020_std.parquet": "Gram Panchayat reservation record",
    "panchayat_samiti_2005_std.parquet": "Panchayat Samiti member seat",
    "panchayat_samiti_2010_std.parquet": "Panchayat Samiti member ward",
    "zila_parishad_2005_std.parquet": "Zila Parishad member ward",
    "zila_parishad_2010_std.parquet": "Zila Parishad member ward",
    "ContestingSarpanch.parquet": "Contesting Sarpanch candidate",
    "StatsNomination.parquet": "Gram Panchayat nomination-statistics record",
    "WinnerSarpanch.parquet": "Sarpanch winner record",
    "WarnWinningPanch.parquet": "Ward-winning Panch record",
    "source_records.parquet": "Source record with reviewed geography and identity",
    "candidates_2020_events.parquet": "Candidate in a 2020 general-election phase",
    "winners_2020_events.parquet": "Winner in a 2020 general-election phase",
    "raj_05_10.parquet": "Unambiguous GP link between 2005 and 2010",
    "raj_10_15.parquet": "Unambiguous GP link between 2010 and 2015",
    "raj_15_20.parquet": "Unambiguous GP link between 2015 and 2020",
    "raj_05_20.parquet": "Unambiguous GP link across all four years",
    "gp_lgd_crosswalk.parquet": "Accepted election match key to LGD GP link",
}


def summary():
    lines = [
        "<!-- datasets:start -->",
        "",
        "| File | Rows | Each row represents |",
        "| --- | ---: | --- |",
    ]
    for path in sorted(DATA.rglob("*.parquet")):
        name = path.relative_to(ROOT).as_posix()
        rows = pq.ParquetFile(path).metadata.num_rows
        lines.append(
            f"| [{path.relative_to(DATA)}]({name}) | {rows:,} | {UNITS[path.name]} |"
        )
    lines.extend(["", "<!-- datasets:end -->"])
    readme = ROOT / "README.md"
    pattern = r"<!-- datasets:start -->.*?<!-- datasets:end -->"
    text = readme.read_text()
    if len(re.findall(pattern, text, flags=re.S)) != 1:
        raise ValueError("README must contain one dataset inventory block")
    readme.write_text(re.sub(pattern, lambda _: "\n".join(lines), text, flags=re.S))


def same_values(expected, actual, name):
    if (
        expected.column_names != actual.column_names
        or expected.num_rows != actual.num_rows
    ):
        raise ValueError(f"{name}: row count or columns changed")
    for column in expected.column_names:
        a, b = expected[column], actual[column]
        if a.type != b.type:
            raise ValueError(f"{name}.{column}: type changed: {a.type} -> {b.type}")
        if a.equals(b):
            continue
        # Distance arithmetic can differ in the last bit across platforms.
        if (
            pa.types.is_floating(a.type)
            and "distance" in column
            and np.allclose(
                a.to_numpy(), b.to_numpy(), rtol=0, atol=1e-14, equal_nan=True
            )
        ):
            continue
        raise ValueError(
            f"{name}.{column}: published values differ from rebuilt source"
        )


def verify():
    schema = json.loads((DATA / "SCHEMA.json").read_text())
    paths = sorted([*DATA.glob("*_std.parquet"), *DATA.glob("elections/*.parquet")])
    if set(schema) != {p.relative_to(DATA).as_posix() for p in paths}:
        raise ValueError("Published file inventory changed")
    checksums = []
    for path in paths:
        entry = schema[path.relative_to(DATA).as_posix()]
        parquet = pq.ParquetFile(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if entry != dict(
            sha256=digest,
            rows=parquet.metadata.num_rows,
            cols=parquet.metadata.num_columns,
            bytes=path.stat().st_size,
            columns=parquet.schema_arrow.names,
        ):
            raise ValueError(f"{path}: metadata differs")
        checksums.append(f"{digest}  {path.relative_to(DATA).as_posix()}\n")
    if (DATA / "CHECKSUMS.sha256").read_text() != "".join(checksums):
        raise ValueError("Published checksums differ")
    geography = ROOT / "data/source/geography"
    manifest = json.loads((geography / "MANIFEST.json").read_text())
    if {p.name for p in geography.glob("*.csv")} != {
        e["file"] for e in manifest["files"]
    }:
        raise ValueError("Geographic input inventory changed")
    for entry in manifest["files"]:
        if (
            hashlib.sha256((geography / entry["file"]).read_bytes()).hexdigest()
            != entry["sha256"]
        ):
            raise ValueError(f"Geographic input changed: {entry['file']}")
    convert(ROOT / "data", DATA / "scrape_2020_2022", check=True)
    with tempfile.TemporaryDirectory(prefix="rajasthan-verify-") as temp:
        out = Path(temp)
        for year in (2005, 2010, 2015, 2020):
            name = f"source_{year}_std.parquet"
            save(
                standardize(year),
                name,
                integer=["year", "winner_female", "female_reserved"],
                directory=out,
            )
            same_values(pq.read_table(DATA / name), pq.read_table(out / name), name)
        for book in (
            "panchayat_samiti_2005",
            "panchayat_samiti_2010",
            "zila_parishad_2005",
            "zila_parishad_2010",
        ):
            name = f"{book}_std.parquet"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    f"local_elections_rajasthan.parse.result_books.{book}",
                    "--output",
                    str(out / name),
                ],
                check=True,
            )
            same_values(pq.read_table(DATA / name), pq.read_table(out / name), name)
        env = {**os.environ, "ELECTION_PRODUCTS_DIR": str(out / "elections")}
        for stage in ("candidate_events", "election_panels", "geographic_bridge"):
            subprocess.run(
                [sys.executable, "-m", f"local_elections_rajasthan.build.{stage}"],
                env=env,
                check=True,
            )
        for path in sorted((DATA / "elections").glob("*.parquet")):
            same_values(
                pq.read_table(path),
                pq.read_table(out / "elections" / path.name),
                path.name,
            )
    print("All 20 published tables reproduce from retained sources.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "verify", "summary"])
    args = parser.parse_args()
    {"build": build, "verify": verify, "summary": summary}[args.command]()


if __name__ == "__main__":
    main()
