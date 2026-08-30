"""Parse the retained 2010 Panchayat Samiti result-table extraction.

The PDF is deliberately not opened here. This parser reads the positioned-word
JSON Lines artifact, maps the publication's fixed columns, validates the full
seat roster, and writes one Parquet row per Panchayat Samiti member ward.
"""

import argparse
import collections
import json
import os
import pathlib
import re
import tempfile

import pandas

from scripts.extract_panchayat_samiti_2010 import (
    FIRST_PAGE,
    LAST_PAGE,
    SOURCE_RELATIVE,
    SOURCE_SHA256,
)
from scripts.extract_panchayat_samiti_2010 import (
    OUTPUT as EXTRACTED,
)
from scripts.runlog import get_logger

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/fin/panchayat_samiti_2010_std.parquet"

EXPECTED_ROWS = 5273
EXPECTED_DISTRICTS = 33
EXPECTED_SAMITIS = 248
EXPECTED_RESERVATIONS = {
    "GEN": 1378,
    "GENW": 1345,
    "SC": 510,
    "SCW": 423,
    "ST": 454,
    "STW": 372,
    "OBC": 446,
    "OBCW": 345,
}
EXPECTED_CASTES = {"GEN": 2723, "SC": 933, "ST": 826, "OBC": 791}
EXPECTED_WOMEN_RESERVED = 2485
RESERVATIONS = frozenset(EXPECTED_RESERVATIONS)
PARTIES = {"BJP", "BSP", "CPI(M)", "INC", "IND", "NCP"}
EXPECTED_WINNER_CONFLICTS = {(71, 218, "M", "OBCW")}
COLUMN_BOUNDS = (
    ("serial", 90, 127),
    ("district_raw", 127, 226),
    ("samiti_raw", 226, 330),
    ("ward_no", 330, 365),
    ("reservation_raw", 365, 425),
    ("winner_name", 425, 605),
    ("winner_sex_raw", 605, 640),
    ("winner_category_raw", 640, 735),
    ("party_raw", 735, 842),
)
OUTPUT_COLUMNS = [
    "year",
    "serial",
    "district_raw",
    "samiti_raw",
    "ward_no_raw",
    "ward_no",
    "reservation_raw",
    "caste_category",
    "female_reserved",
    "winner_name",
    "winner_sex_raw",
    "winner_female",
    "winner_category_raw",
    "winner_category",
    "winner_caste_category",
    "winner_category_sex_agree",
    "party_raw",
    "source_path",
    "source_page",
]

LOGGER = get_logger(__name__)


def load_pages(path):
    """Load and validate the retained extraction, one record per source page."""
    with path.open(encoding="utf-8") as stream:
        pages = [json.loads(line) for line in stream if line.strip()]
    page_numbers = [page["source_page"] for page in pages]
    expected_pages = list(range(FIRST_PAGE, LAST_PAGE + 1))
    if page_numbers != expected_pages:
        raise SystemExit(
            f"extraction holds pages {page_numbers[:1]}..{page_numbers[-1:]}, "
            f"expected every page {FIRST_PAGE}..{LAST_PAGE} in order"
        )
    bad_provenance = [
        page["source_page"]
        for page in pages
        if page.get("source_path") != SOURCE_RELATIVE
        or page.get("source_sha256") != SOURCE_SHA256
    ]
    if bad_provenance:
        raise SystemExit(f"extraction provenance differs on pages {bad_provenance[:5]}")
    return pages


def result_page(page):
    """Whether a page carries the repeated member-result table header."""
    header = {word["text"] for word in page["words"] if word["top"] < 90}
    return {"District", "Panchayat", "Samiti", "Ward", "Sex", "Party"} <= header


def cells(words):
    """Assign one positioned source line to the publication's columns."""
    return {
        name: " ".join(
            word["text"]
            for word in sorted(words, key=lambda item: item["x0"])
            if lower <= word["x0"] < upper
        ).strip()
        for name, lower, upper in COLUMN_BOUNDS
    }


def parse_page(page):
    """Parse member rows from one retained result-table page."""
    lines = collections.defaultdict(list)
    for word in page["words"]:
        lines[round(word["top"], 1)].append(word)

    rows = []
    for words in lines.values():
        serials = [
            word
            for word in words
            if re.fullmatch(r"[0-9]+", word["text"])
            and COLUMN_BOUNDS[0][1] <= word["x0"] < COLUMN_BOUNDS[0][2]
        ]
        if not serials:
            continue
        if len(serials) != 1:
            raise SystemExit(
                f"source page {page['source_page']} has {len(serials)} serials "
                "on one text line"
            )
        raw = cells(words)
        missing = [name for name, value in raw.items() if not value]
        if missing:
            raise SystemExit(
                f"source page {page['source_page']} serial {raw['serial']} "
                f"has blank cells: {missing}"
            )

        reservation_raw = raw["reservation_raw"]
        winner_category_raw = raw["winner_category_raw"]
        winner_category = winner_category_raw.replace(" ", "")
        winner_category_sex_agree = int(
            not winner_category.endswith("W") or raw["winner_sex_raw"] == "F"
        )
        if winner_category != winner_category_raw:
            LOGGER.info(
                "winner category spacing normalized",
                extra={
                    "event": "source_recode_applied",
                    "source_page": page["source_page"],
                    "serial": int(raw["serial"]),
                    "column": "winner_category",
                    "raw_value": winner_category_raw,
                    "value": winner_category,
                },
            )
        serial = int(raw["serial"])
        ward_no_raw = int(raw["ward_no"])
        ward_no = 16 if serial == 4401 and ward_no_raw == 17 else ward_no_raw
        if ward_no != ward_no_raw:
            LOGGER.info(
                "ward number corrected from body roster",
                extra={
                    "event": "source_recode_applied",
                    "source_page": page["source_page"],
                    "serial": serial,
                    "column": "ward_no",
                    "raw_value": ward_no_raw,
                    "value": ward_no,
                },
            )
        rows.append(
            {
                "year": 2010,
                "serial": serial,
                "district_raw": raw["district_raw"],
                "samiti_raw": raw["samiti_raw"],
                "ward_no_raw": ward_no_raw,
                "ward_no": ward_no,
                "reservation_raw": reservation_raw,
                "caste_category": reservation_raw.removesuffix("W"),
                "female_reserved": int(reservation_raw.endswith("W")),
                "winner_name": raw["winner_name"],
                "winner_sex_raw": raw["winner_sex_raw"],
                "winner_female": int(raw["winner_sex_raw"] == "F"),
                "winner_category_raw": winner_category_raw,
                "winner_category": winner_category,
                "winner_caste_category": winner_category.removesuffix("W"),
                "winner_category_sex_agree": winner_category_sex_agree,
                "party_raw": raw["party_raw"],
                "source_path": SOURCE_RELATIVE,
                "source_page": page["source_page"],
            }
        )
    return rows


def parse_pages(pages):
    """Parse all and only result-table pages from the retained extraction."""
    selected = [page for page in pages if result_page(page)]
    rows = [row for page in selected for row in parse_page(page)]
    LOGGER.info(
        "result pages parsed",
        extra={
            "event": "result_pages_parsed",
            "pages": len(selected),
            "first_page": selected[0]["source_page"] if selected else None,
            "last_page": selected[-1]["source_page"] if selected else None,
            "rows": len(rows),
        },
    )
    return rows


def validate(rows):
    """Apply source and grain expectations before publication."""
    if len(rows) != EXPECTED_ROWS:
        raise SystemExit(f"parsed {len(rows):,} rows, expected {EXPECTED_ROWS:,}")
    if [row["serial"] for row in rows] != list(range(1, EXPECTED_ROWS + 1)):
        raise SystemExit("member serials are not exactly 1..5273 in source order")

    keys = [(row["district_raw"], row["samiti_raw"], row["ward_no"]) for row in rows]
    if len(set(keys)) != len(keys):
        duplicates = [
            key for key, count in collections.Counter(keys).items() if count > 1
        ]
        raise SystemExit(f"duplicate seat keys: {duplicates[:5]}")

    bodies = collections.defaultdict(list)
    for row in rows:
        bodies[(row["district_raw"], row["samiti_raw"])].append(row["ward_no"])
    if len(bodies) != EXPECTED_SAMITIS:
        raise SystemExit(f"parsed {len(bodies)} Panchayat Samitis, expected 248")
    if len({row["district_raw"] for row in rows}) != EXPECTED_DISTRICTS:
        raise SystemExit("district count differs from the publication's 33")
    gaps = {
        body: sorted(wards)
        for body, wards in bodies.items()
        if sorted(wards) != list(range(1, max(wards) + 1))
    }
    if gaps:
        raise SystemExit(f"non-contiguous ward rosters: {list(gaps)[:5]}")

    reservations = collections.Counter(row["reservation_raw"] for row in rows)
    if dict(reservations) != EXPECTED_RESERVATIONS:
        raise SystemExit(
            f"reservation totals are {dict(reservations)}, "
            f"expected {EXPECTED_RESERVATIONS}"
        )
    castes = collections.Counter(row["caste_category"] for row in rows)
    if dict(castes) != EXPECTED_CASTES:
        raise SystemExit(f"caste totals are {dict(castes)}, expected {EXPECTED_CASTES}")
    if sum(row["female_reserved"] for row in rows) != EXPECTED_WOMEN_RESERVED:
        raise SystemExit("women-reserved total differs from the printed 2,485")

    if {row["winner_sex_raw"] for row in rows} != {"F", "M"}:
        raise SystemExit("winner sex contains values outside F/M")
    if {row["winner_category"] for row in rows} != RESERVATIONS:
        raise SystemExit("winner category contains an unrecognized value")
    if {row["party_raw"] for row in rows} != PARTIES:
        raise SystemExit("party contains an unrecognized value")
    conflicts = {
        (
            row["serial"],
            row["source_page"],
            row["winner_sex_raw"],
            row["winner_category"],
        )
        for row in rows
        if not row["winner_category_sex_agree"]
    }
    if conflicts != EXPECTED_WINNER_CONFLICTS:
        raise SystemExit(
            f"winner sex/category conflicts are {conflicts}, "
            f"expected {EXPECTED_WINNER_CONFLICTS}"
        )
    LOGGER.warning(
        "source prints contradictory winner sex and category",
        extra={
            "event": "source_consistency_exception",
            "conflicts": sorted(conflicts),
        },
    )

    LOGGER.info(
        "seat expectations passed",
        extra={
            "event": "seat_expectations_passed",
            "rows": len(rows),
            "districts": EXPECTED_DISTRICTS,
            "panchayat_samitis": len(bodies),
            "women_reserved": EXPECTED_WOMEN_RESERVED,
            "reservation_totals": dict(reservations),
        },
    )


def write_parquet(rows, output):
    """Atomically write the analysis-ready seat table."""
    output.parent.mkdir(parents=True, exist_ok=True)
    frame = pandas.DataFrame(rows, columns=OUTPUT_COLUMNS)
    with tempfile.NamedTemporaryFile(
        dir=output.parent, suffix=".parquet", delete=False
    ) as stream:
        temporary = pathlib.Path(stream.name)
    try:
        frame.to_parquet(temporary, index=False)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None):
    """Parse, validate, and publish the 2010 member-seat table."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=pathlib.Path, default=EXTRACTED)
    parser.add_argument("--output", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args(argv)

    LOGGER.info(
        "parsing started",
        extra={
            "event": "parsing_started",
            "input_path": str(args.input),
            "output_path": str(args.output),
        },
    )
    pages = load_pages(args.input)
    rows = parse_pages(pages)
    validate(rows)
    write_parquet(rows, args.output)
    LOGGER.info(
        "parsing completed",
        extra={
            "event": "parsing_completed",
            "output_path": str(args.output),
            "rows": len(rows),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
