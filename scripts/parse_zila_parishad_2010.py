"""Parse the retained 2010 Zila Parishad result-table extraction.

The PDF is deliberately not opened here. This parser consumes positioned-word
JSON Lines, maps the publication's fixed columns, validates printed controls,
and writes one Parquet row per Zila Parishad ward.
"""

import argparse
import collections
import json
import os
import pathlib
import re
import tempfile

import pandas

from scripts.extract_zila_parishad_2010 import (
    FIRST_PAGE,
    LAST_PAGE,
    SOURCE_RELATIVE,
    SOURCE_SHA256,
)
from scripts.extract_zila_parishad_2010 import OUTPUT as EXTRACTED
from scripts.runlog import get_logger

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/fin/zila_parishad_2010_std.parquet"

EXPECTED_ROWS = 1013
EXPECTED_DISTRICTS = 33
EXPECTED_RESERVATIONS = {
    "GEN": 260,
    "GENW": 253,
    "SC": 96,
    "SCW": 83,
    "ST": 86,
    "STW": 77,
    "OBC": 85,
    "OBCW": 73,
}
EXPECTED_WINNER_SEX_CATEGORY = {
    ("Male", "GEN"): 117,
    ("Male", "SC"): 91,
    ("Male", "ST"): 88,
    ("Male", "OBC"): 175,
    ("Female", "GEN"): 137,
    ("Female", "SC"): 99,
    ("Female", "ST"): 97,
    ("Female", "OBC"): 209,
}
EXPECTED_PARTIES = {
    "BJP": 365,
    "BSP": 3,
    "CPI": 0,
    "CPI(M)": 7,
    "INC": 603,
    "NCP": 0,
    "RJD": 0,
    "IND": 35,
}
EXPECTED_MARGIN_BINS = {
    "up_to_100": 34,
    "101_to_500": 119,
    "501_to_1000": 179,
    "1001_to_5000": 599,
    "above_5000": 55,
    "uncontested": 27,
}
DISTRICT_RECODE = {
    "KARUALI": "KARAULI",
    "SAWAIMADHOPUR": "SAWAI MADHOPUR",
}
EXPECTED_DISTRICT_RECODE_COUNTS = {
    ("KARUALI", "KARAULI"): 27,
    ("SAWAIMADHOPUR", "SAWAI MADHOPUR"): 25,
}
EXPECTED_WARD_RECODE = {"district": "CHURU", "rows": 27, "offset": 4}
RESERVATIONS = frozenset(EXPECTED_RESERVATIONS)
CATEGORIES = {"GEN", "SC", "ST", "OBC"}
COLUMN_BOUNDS = (
    ("district_raw", 60, 135),
    ("ward_no", 135, 165),
    ("reservation_raw", 165, 205),
    ("winner_name", 205, 300),
    ("party_raw", 300, 330),
    ("winner_sex_raw", 330, 375),
    ("winner_category_raw", 375, 445),
    ("votes_raw", 445, 474),
    ("margin_raw", 474, 518),
    ("remark_raw", 518, 570),
)
OUTPUT_COLUMNS = [
    "year",
    "district_raw",
    "district",
    "district_inferred",
    "ward_no_raw",
    "ward_no",
    "ward_no_inferred",
    "reservation_raw",
    "reservation",
    "caste_category",
    "female_reserved",
    "seat_filled",
    "winner_name",
    "winner_sex_raw",
    "winner_female",
    "winner_category_raw",
    "winner_category",
    "winner_caste_category",
    "winner_category_sex_agree",
    "party_raw",
    "party",
    "votes_secured",
    "margin",
    "margin_below_votes",
    "elected_uncontested",
    "remark_raw",
    "source_path",
    "source_page",
]
NULLABLE_INTEGER_COLUMNS = ["margin", "margin_below_votes"]

LOGGER = get_logger(__name__)


def load_pages(path):
    """Load and validate the retained extraction and its provenance."""
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


def cells(words):
    """Assign one positioned source row to the publication's columns."""
    return {
        name: " ".join(
            word["text"]
            for word in sorted(words, key=lambda item: item["x0"])
            if lower <= word["x0"] < upper
        ).strip()
        for name, lower, upper in COLUMN_BOUNDS
    }


def normalize_party(raw):
    """Normalize the source's CPI(M) typography."""
    return "CPI(M)" if raw in {"CPI M", "CPI(M)"} else raw


def artifact_signature(word):
    """Return a stable signature for repeated positioned background text."""
    return (word["text"], round(word["x0"], 1), round(word["top"], 1))


def parse_page(page, artifacts=frozenset()):
    """Parse member rows from one result-table page."""
    page_words = [
        word
        for word in page["words"]
        if word.get("size", 0) <= 20 and artifact_signature(word) not in artifacts
    ]
    ward_words = [
        word
        for word in page_words
        if word["top"] >= 115
        and 135 <= word["x0"] < 165
        and re.fullmatch(r"[0-9]+", word["text"])
    ]
    rows = []
    for ward_word in ward_words:
        top = ward_word["top"]
        words = [word for word in page_words if abs(word["top"] - top) <= 3]
        raw = cells(words)
        name_prefix = " ".join(
            word["text"]
            for word in sorted(page_words, key=lambda item: item["x0"])
            if 205 <= word["x0"] < 300 and 7.8 <= top - word["top"] <= 9.8
        )
        if name_prefix:
            raw["winner_name"] = f"{name_prefix} {raw['winner_name']}".strip()
        missing = [
            name
            for name in (
                "district_raw",
                "reservation_raw",
                "winner_name",
                "party_raw",
                "winner_sex_raw",
                "winner_category_raw",
                "votes_raw",
                "margin_raw",
            )
            if not raw[name]
        ]
        if missing:
            raise SystemExit(
                f"source page {page['source_page']} ward {ward_word['text']} "
                f"has blank cells: {missing}"
            )

        ward_no = int(ward_word["text"])
        reservation = raw["reservation_raw"].replace(" ", "")
        winner_category = raw["winner_category_raw"].replace(" ", "")
        uncontested = raw["margin_raw"].replace(" ", "").lower() == "uncontested"
        if uncontested:
            if raw["votes_raw"] != "0":
                raise SystemExit(
                    f"source page {page['source_page']} uncontested ward "
                    f"{ward_no} prints votes {raw['votes_raw']}, expected 0"
                )
            margin = None
        else:
            margin = int(raw["margin_raw"])
        votes = int(raw["votes_raw"])
        rows.append(
            {
                "year": 2010,
                "district_raw": raw["district_raw"],
                "ward_no_raw": ward_no,
                "ward_no": ward_no,
                "ward_no_inferred": 0,
                "reservation_raw": raw["reservation_raw"],
                "reservation": reservation,
                "caste_category": reservation.removesuffix("W"),
                "female_reserved": int(reservation.endswith("W")),
                "seat_filled": 1,
                "winner_name": raw["winner_name"],
                "winner_sex_raw": raw["winner_sex_raw"],
                "winner_female": int(raw["winner_sex_raw"] == "Female"),
                "winner_category_raw": raw["winner_category_raw"],
                "winner_category": winner_category,
                "winner_caste_category": winner_category.removesuffix("W"),
                "winner_category_sex_agree": int(
                    not winner_category.endswith("W")
                    or raw["winner_sex_raw"] == "Female"
                ),
                "party_raw": raw["party_raw"],
                "party": normalize_party(raw["party_raw"]),
                "votes_secured": votes,
                "margin": margin,
                "margin_below_votes": (
                    None if margin is None else int(margin <= votes)
                ),
                "elected_uncontested": int(uncontested),
                "remark_raw": raw["remark_raw"] or None,
                "source_path": SOURCE_RELATIVE,
                "source_page": page["source_page"],
            }
        )
    return rows


def parse_pages(pages):
    """Parse every retained result-table page."""
    signature_counts = collections.Counter(
        artifact_signature(word) for page in pages for word in page["words"]
    )
    artifacts = {
        signature
        for signature, count in signature_counts.items()
        if count >= len(pages) - 2
    }
    rows = [row for page in pages for row in parse_page(page, artifacts)]
    district_positions = collections.Counter()
    current_district = None
    previous_ward = None
    for row in rows:
        if previous_ward is None or row["ward_no_raw"] < previous_ward:
            current_district = DISTRICT_RECODE.get(
                row["district_raw"], row["district_raw"]
            )
        if current_district is None:
            raise SystemExit("first parsed result row does not begin a district roster")
        row["district"] = current_district
        row["district_inferred"] = int(row["district_raw"] != current_district)
        district_positions[current_district] += 1
        inferred_ward = district_positions[current_district]
        row["ward_no"] = inferred_ward
        row["ward_no_inferred"] = int(row["ward_no_raw"] != inferred_ward)
        previous_ward = row["ward_no_raw"]
    LOGGER.info(
        "result pages parsed",
        extra={
            "event": "result_pages_parsed",
            "pages": len(pages),
            "first_page": pages[0]["source_page"] if pages else None,
            "last_page": pages[-1]["source_page"] if pages else None,
            "rows": len(rows),
            "repeated_artifacts_removed": len(artifacts),
        },
    )
    return rows


def margin_bin(row):
    """Return the publication's margin-table bucket for one seat."""
    if row["elected_uncontested"]:
        return "uncontested"
    margin = row["margin"]
    if margin <= 100:
        return "up_to_100"
    if margin <= 500:
        return "101_to_500"
    if margin <= 1000:
        return "501_to_1000"
    if margin <= 5000:
        return "1001_to_5000"
    return "above_5000"


def validate(rows):
    """Apply source and grain expectations before publication."""
    if len(rows) != EXPECTED_ROWS:
        raise SystemExit(f"parsed {len(rows):,} rows, expected {EXPECTED_ROWS:,}")
    keys = [(row["district"], row["ward_no"]) for row in rows]
    if len(set(keys)) != len(keys):
        duplicates = [
            key for key, count in collections.Counter(keys).items() if count > 1
        ]
        raise SystemExit(f"duplicate seat keys: {duplicates[:5]}")

    districts = collections.defaultdict(list)
    for row in rows:
        districts[row["district"]].append(row["ward_no"])
    if len(districts) != EXPECTED_DISTRICTS:
        raise SystemExit(
            f"parsed {len(districts)} districts, expected {EXPECTED_DISTRICTS}"
        )
    gaps = {
        district: sorted(wards)
        for district, wards in districts.items()
        if sorted(wards) != list(range(1, max(wards) + 1))
    }
    if gaps:
        raise SystemExit(f"non-contiguous ward rosters: {list(gaps)[:5]}")
    ward_recodes = [row for row in rows if row["ward_no_inferred"]]
    if (
        len(ward_recodes) != EXPECTED_WARD_RECODE["rows"]
        or {row["district"] for row in ward_recodes}
        != {EXPECTED_WARD_RECODE["district"]}
        or {row["ward_no_raw"] - row["ward_no"] for row in ward_recodes}
        != {EXPECTED_WARD_RECODE["offset"]}
    ):
        raise SystemExit(
            "source ward-number recodes differ from the documented CHURU offset"
        )
    district_recodes = collections.Counter(
        (row["district_raw"], row["district"])
        for row in rows
        if row["district_inferred"]
    )
    if dict(district_recodes) != EXPECTED_DISTRICT_RECODE_COUNTS:
        raise SystemExit(
            f"district recodes are {dict(district_recodes)}, "
            f"expected {EXPECTED_DISTRICT_RECODE_COUNTS}"
        )

    reservations = collections.Counter(row["reservation"] for row in rows)
    if dict(reservations) != EXPECTED_RESERVATIONS:
        raise SystemExit(
            f"reservation totals are {dict(reservations)}, "
            f"expected {EXPECTED_RESERVATIONS}"
        )
    if not set(reservations) <= RESERVATIONS:
        raise SystemExit("reservation contains an unrecognized value")
    winner_controls = collections.Counter(
        (row["winner_sex_raw"], row["winner_caste_category"]) for row in rows
    )
    if dict(winner_controls) != EXPECTED_WINNER_SEX_CATEGORY:
        raise SystemExit(
            f"winner sex/category totals are {dict(winner_controls)}, "
            f"expected {EXPECTED_WINNER_SEX_CATEGORY}"
        )
    if {row["winner_caste_category"] for row in rows} != CATEGORIES:
        raise SystemExit("winner category contains an unrecognized value")

    parties = collections.Counter(row["party"] for row in rows)
    printed_parties = {party: parties.get(party, 0) for party in EXPECTED_PARTIES}
    if printed_parties != EXPECTED_PARTIES or set(parties) - set(EXPECTED_PARTIES):
        raise SystemExit(
            f"party totals are {dict(parties)}, expected {EXPECTED_PARTIES}"
        )
    margin_bins = collections.Counter(margin_bin(row) for row in rows)
    if dict(margin_bins) != EXPECTED_MARGIN_BINS:
        raise SystemExit(
            f"margin totals are {dict(margin_bins)}, expected {EXPECTED_MARGIN_BINS}"
        )
    conflicts = [
        row
        for row in rows
        if row["winner_category_sex_agree"] == 0 or row["margin_below_votes"] == 0
    ]
    if conflicts:
        details = [
            (
                row["source_page"],
                row["district_raw"],
                row["ward_no"],
                row["winner_sex_raw"],
                row["winner_category"],
                row["votes_secured"],
                row["margin"],
            )
            for row in conflicts
        ]
        raise SystemExit(f"winner consistency conflicts: {details[:10]}")
    remarks = [row for row in rows if row["remark_raw"]]
    if remarks:
        raise SystemExit(f"unexpected populated remark cells: {remarks[:5]}")

    LOGGER.info(
        "seat expectations passed",
        extra={
            "event": "seat_expectations_passed",
            "rows": len(rows),
            "districts": len(districts),
            "reservation_totals": dict(reservations),
            "party_totals": dict(parties),
            "margin_totals": dict(margin_bins),
        },
    )


def write_parquet(rows, output):
    """Atomically write the analysis-ready seat table."""
    output.parent.mkdir(parents=True, exist_ok=True)
    frame = pandas.DataFrame(rows, columns=OUTPUT_COLUMNS)
    for column in NULLABLE_INTEGER_COLUMNS:
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
