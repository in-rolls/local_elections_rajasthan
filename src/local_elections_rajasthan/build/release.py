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
from local_elections_rajasthan.paths import (
    GEOGRAPHY,
    MANIFEST,
    RELEASE,
    ROOT,
    SCRAPE,
    TABLES,
    table,
)


def describe(key):
    path = table(key)
    parquet = pq.ParquetFile(path)
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {
        "sha256": digest,
        "rows": parquet.metadata.num_rows,
        "cols": parquet.metadata.num_columns,
        "bytes": path.stat().st_size,
        "columns": parquet.schema_arrow.names,
    }


def build():
    """Record every published table in data/MANIFEST.json, keyed by its path
    under data/release/."""
    manifest = {TABLES[key]: describe(key) for key in sorted(TABLES)}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


UNITS = {
    "sarpanch_2005": "Gram Panchayat seat",
    "sarpanch_2010": "Gram Panchayat seat",
    "sarpanch_2015": "Gram Panchayat seat",
    "sarpanch_2020": "Gram Panchayat reservation record",
    "panchayat_samiti_2005": "Panchayat Samiti member seat",
    "panchayat_samiti_2010": "Panchayat Samiti member ward",
    "zila_parishad_2005": "Zila Parishad member ward",
    "zila_parishad_2010": "Zila Parishad member ward",
    "sarpanch_candidates": "Contesting Sarpanch candidate",
    "nomination_stats": "Gram Panchayat nomination-statistics record",
    "sarpanch_winners": "Sarpanch winner record",
    "ward_member_winners": "Ward-winning Panch record",
    "sarpanch_source_records": "Source record with reviewed geography and identity",
    "sarpanch_candidate_events_2020": "Candidate in a 2020 general-election phase",
    "sarpanch_winner_events_2020": "Winner in a 2020 general-election phase",
    "sarpanch_links_2005_2010": "Unambiguous GP link between 2005 and 2010",
    "sarpanch_links_2010_2015": "Unambiguous GP link between 2010 and 2015",
    "sarpanch_links_2015_2020": "Unambiguous GP link between 2015 and 2020",
    "sarpanch_links_2005_2020": "Unambiguous GP link across all four years",
    "gp_lgd_crosswalk": "Accepted election match key to LGD GP link",
}


def summary():
    lines = [
        "<!-- datasets:start -->",
        "",
        "| File | Rows | Each row represents |",
        "| --- | ---: | --- |",
    ]
    for key in sorted(TABLES, key=TABLES.get):
        path = table(key)
        rows = pq.ParquetFile(path).metadata.num_rows
        lines.append(
            f"| [{TABLES[key]}]({path.relative_to(ROOT).as_posix()}) "
            f"| {rows:,} | {UNITS[key]} |"
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


# What candidate_events, election_panels and geographic_bridge write.
PRODUCTS = [
    "sarpanch_source_records",
    "sarpanch_candidate_events_2020",
    "sarpanch_winner_events_2020",
    "sarpanch_links_2005_2010",
    "sarpanch_links_2010_2015",
    "sarpanch_links_2015_2020",
    "sarpanch_links_2005_2020",
    "gp_lgd_crosswalk",
]


def verify():
    manifest = json.loads(MANIFEST.read_text())
    if set(manifest) != set(TABLES.values()):
        raise ValueError("Published file inventory changed")
    for key in TABLES:
        if manifest[TABLES[key]] != describe(key):
            raise ValueError(f"{table(key)}: metadata differs")
    geography = GEOGRAPHY
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
    convert(SCRAPE, RELEASE, check=True)
    with tempfile.TemporaryDirectory(prefix="rajasthan-verify-") as temp:
        out = Path(temp)
        for year in (2005, 2010, 2015, 2020):
            key = f"sarpanch_{year}"
            save(
                standardize(year),
                key,
                integer=["year", "winner_woman", "reserved_woman"],
                directory=out,
            )
            same_values(
                pq.read_table(table(key)), pq.read_table(out / TABLES[key]), key
            )
        for book in (
            "panchayat_samiti_2005",
            "panchayat_samiti_2010",
            "zila_parishad_2005",
            "zila_parishad_2010",
        ):
            name = f"{book}.parquet"
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
            same_values(pq.read_table(table(book)), pq.read_table(out / name), name)
        env = {**os.environ, "ELECTION_PRODUCTS_DIR": str(out / "elections")}
        for stage in ("candidate_events", "election_panels", "geographic_bridge"):
            subprocess.run(
                [sys.executable, "-m", f"local_elections_rajasthan.build.{stage}"],
                env=env,
                check=True,
            )
        for key in PRODUCTS:
            same_values(
                pq.read_table(table(key)),
                pq.read_table(out / "elections" / TABLES[key]),
                key,
            )
    print("All 20 published tables reproduce from retained sources.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "verify", "summary"])
    args = parser.parse_args()
    {"build": build, "verify": verify, "summary": summary}[args.command]()


if __name__ == "__main__":
    main()
