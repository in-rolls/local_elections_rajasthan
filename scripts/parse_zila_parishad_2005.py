"""Parse the retained 2005 Zila Parishad result-table extraction.

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

from scripts.extract_zila_parishad_2005 import (
    FIRST_PAGE,
    LAST_PAGE,
    SOURCE_RELATIVE,
    SOURCE_SHA256,
)
from scripts.extract_zila_parishad_2005 import OUTPUT as EXTRACTED
from scripts.runlog import get_logger

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/fin/zila_parishad_2005_std.parquet"

EXPECTED_ROWS = 1008
EXPECTED_WINNERS = 1007
EXPECTED_DISTRICTS = 32
EXPECTED_RESERVATIONS = {
    "GEN": 340,
    "GENW": 174,
    "SC": 118,
    "SCW": 63,
    "ST": 107,
    "STW": 49,
    "OBC": 106,
    "OBCW": 51,
}
EXPECTED_WINNER_SEX_CATEGORY = {
    ("MALE", "GEN"): 164,
    ("MALE", "SC"): 111,
    ("MALE", "ST"): 113,
    ("MALE", "OBC"): 242,
    ("FEMALE", "GEN"): 93,
    ("FEMALE", "SC"): 77,
    ("FEMALE", "ST"): 73,
    ("FEMALE", "OBC"): 134,
}
EXPECTED_PARTIES = {
    "BJP": 459,
    "BSP": 8,
    "CPI": 1,
    "CPI(M)": 12,
    "INC": 494,
    "NCP": 0,
    "IND": 33,
}
EXPECTED_MARGIN_BINS = {
    "up_to_100": 30,
    "101_to_500": 159,
    "501_to_1000": 163,
    "1001_to_5000": 556,
    "above_5000": 57,
    "uncontested": 42,
    "unfilled": 1,
}
EXPECTED_INFERRED_UNCONTESTED = {(68, "JAIPUR", 2)}
EXPECTED_WARD_RECODE = {"district": "CHURU", "rows": 27, "offset": 4}
DISTRICT_RECODE = {"S.MADHOPUR": "SAWAI MADHOPUR"}
RESERVATIONS = frozenset(EXPECTED_RESERVATIONS)
CATEGORIES = {"GEN", "SC", "ST", "OBC"}
COLUMN_BOUNDS = (
    ("district_serial_raw", 70, 90),
    ("district_raw", 90, 165),
    ("ward_no", 165, 190),
    ("reservation_raw", 190, 225),
    ("winner_name", 225, 360),
    ("party_raw", 360, 395),
    ("winner_sex_raw", 395, 430),
    ("winner_category_raw", 430, 500),
    ("votes_raw", 500, 535),
    ("margin_raw", 535, 570),
)
OUTPUT_COLUMNS = [
    "year",
    "district_serial_raw",
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
    "uncontested_inferred",
    "remark_raw",
    "source_path",
    "source_page",
]
NULLABLE_INTEGER_COLUMNS = [
    "district_serial_raw",
    "winner_female",
    "winner_category_sex_agree",
    "votes_secured",
    "margin",
    "margin_below_votes",
]

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
    """Assign one positioned source line to the publication's columns."""
    return {
        name: " ".join(
            word["text"]
            for word in sorted(words, key=lambda item: item["x0"])
            if lower <= word["x0"] < upper
        ).strip()
        for name, lower, upper in COLUMN_BOUNDS
    }


def normalize_category(raw):
    """Normalize the source's optional space before the women marker."""
    return raw.replace(" ", "")


def normalize_party(raw):
    """Normalize the source's CPI(M) typography."""
    return "CPI(M)" if raw in {"CPI M", "CPI(M)"} else raw


def parse_page(page):
    """Parse member rows from one result-table page."""
    rows = []
    ward_words = [
        word
        for word in page["words"]
        if word["top"] >= 185
        and 165 <= word["x0"] < 190
        and re.fullmatch(r"[0-9]+", word["text"])
    ]
    for ward_word in ward_words:
        top = ward_word["top"]
        words = [word for word in page["words"] if abs(word["top"] - top) <= 3]
        raw = cells(words)
        if not raw["district_raw"] or not raw["reservation_raw"]:
            raise SystemExit(
                f"source page {page['source_page']} ward line at {top} "
                "has a blank district or reservation"
            )

        ward_no = int(raw["ward_no"])
        reservation = normalize_category(raw["reservation_raw"])
        unfilled = raw["winner_name"] == "UNFILLED"
        uncontested_inferred = bool(
            not unfilled and not raw["votes_raw"] and not raw["margin_raw"]
        )
        uncontested = raw["votes_raw"] == "UN-CONTESTED" or uncontested_inferred
        if unfilled:
            populated = {
                name: raw[name]
                for name in (
                    "party_raw",
                    "winner_sex_raw",
                    "winner_category_raw",
                    "votes_raw",
                    "margin_raw",
                )
                if raw[name]
            }
            if populated:
                raise SystemExit(
                    f"source page {page['source_page']} unfilled ward {ward_no} "
                    f"also has result cells {populated}"
                )
            winner_category = None
            party = None
            votes = None
            margin = None
        else:
            missing = [
                name
                for name in (
                    "winner_name",
                    "party_raw",
                    "winner_sex_raw",
                    "winner_category_raw",
                )
                if not raw[name]
            ]
            if missing:
                raise SystemExit(
                    f"source page {page['source_page']} {raw['district_raw']} "
                    f"ward {ward_no} has blank result cells: {missing}"
                )
            winner_category = normalize_category(raw["winner_category_raw"])
            party = normalize_party(raw["party_raw"])
            if uncontested:
                if raw["margin_raw"]:
                    raise SystemExit(
                        f"source page {page['source_page']} uncontested ward "
                        f"{ward_no} also has margin {raw['margin_raw']}"
                    )
                votes = None
                margin = None
            else:
                if not raw["margin_raw"]:
                    raise SystemExit(
                        f"source page {page['source_page']} ward {ward_no} "
                        "has votes but no margin"
                    )
                votes = int(raw["votes_raw"])
                margin = int(raw["margin_raw"])

        winner_female = None if unfilled else int(raw["winner_sex_raw"] == "FEMALE")
        category_sex_agree = (
            None
            if unfilled
            else int(
                not winner_category.endswith("W") or raw["winner_sex_raw"] == "FEMALE"
            )
        )
        district_serial = (
            int(raw["district_serial_raw"]) if raw["district_serial_raw"] else None
        )
        rows.append(
            {
                "year": 2005,
                "district_serial_raw": district_serial,
                "district_raw": raw["district_raw"],
                "district": DISTRICT_RECODE.get(
                    raw["district_raw"], raw["district_raw"]
                ),
                "district_inferred": int(raw["district_raw"] in DISTRICT_RECODE),
                "ward_no_raw": ward_no,
                "ward_no": ward_no,
                "ward_no_inferred": 0,
                "reservation_raw": raw["reservation_raw"],
                "reservation": reservation,
                "caste_category": reservation.removesuffix("W"),
                "female_reserved": int(reservation.endswith("W")),
                "seat_filled": int(not unfilled),
                "winner_name": None if unfilled else raw["winner_name"],
                "winner_sex_raw": None if unfilled else raw["winner_sex_raw"],
                "winner_female": winner_female,
                "winner_category_raw": (
                    None if unfilled else raw["winner_category_raw"]
                ),
                "winner_category": winner_category,
                "winner_caste_category": (
                    None if unfilled else winner_category.removesuffix("W")
                ),
                "winner_category_sex_agree": category_sex_agree,
                "party_raw": None if unfilled else raw["party_raw"],
                "party": party,
                "votes_secured": votes,
                "margin": margin,
                "margin_below_votes": (None if votes is None else int(margin <= votes)),
                "elected_uncontested": int(uncontested),
                "uncontested_inferred": int(uncontested_inferred),
                "remark_raw": "UNFILLED" if unfilled else None,
                "source_path": SOURCE_RELATIVE,
                "source_page": page["source_page"],
            }
        )
    return rows


def parse_pages(pages):
    """Parse every retained result-table page."""
    rows = [row for page in pages for row in parse_page(page)]
    district_positions = collections.Counter()
    for row in rows:
        district_positions[row["district_raw"]] += 1
        inferred_ward = district_positions[row["district_raw"]]
        row["ward_no"] = inferred_ward
        row["ward_no_inferred"] = int(row["ward_no_raw"] != inferred_ward)
    LOGGER.info(
        "result pages parsed",
        extra={
            "event": "result_pages_parsed",
            "pages": len(pages),
            "first_page": pages[0]["source_page"] if pages else None,
            "last_page": pages[-1]["source_page"] if pages else None,
            "rows": len(rows),
        },
    )
    return rows


def margin_bin(row):
    """Return the publication's margin-table bucket for one seat."""
    if not row["seat_filled"]:
        return "unfilled"
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
    district_serials = [
        row["district_serial_raw"]
        for row in rows
        if row["district_serial_raw"] is not None
    ]
    if district_serials != list(range(1, EXPECTED_DISTRICTS + 1)):
        raise SystemExit(
            f"district serials are {district_serials}, expected exactly 1..32"
        )
    district_recodes = collections.Counter(
        (row["district_raw"], row["district"])
        for row in rows
        if row["district_inferred"]
    )
    if dict(district_recodes) != {("S.MADHOPUR", "SAWAI MADHOPUR"): 25}:
        raise SystemExit(f"district recodes differ: {dict(district_recodes)}")
    ward_recodes = [row for row in rows if row["ward_no_inferred"]]
    if (
        len(ward_recodes) != EXPECTED_WARD_RECODE["rows"]
        or {row["district_raw"] for row in ward_recodes}
        != {EXPECTED_WARD_RECODE["district"]}
        or {row["ward_no_raw"] - row["ward_no"] for row in ward_recodes}
        != {EXPECTED_WARD_RECODE["offset"]}
    ):
        raise SystemExit(
            "source ward-number recodes differ from the documented CHURU offset"
        )
    LOGGER.warning(
        "ward numbers inferred from district row order",
        extra={
            "event": "source_consistency_exception",
            "district": EXPECTED_WARD_RECODE["district"],
            "rows": len(ward_recodes),
            "printed_offset": EXPECTED_WARD_RECODE["offset"],
        },
    )

    reservations = collections.Counter(row["reservation"] for row in rows)
    if dict(reservations) != EXPECTED_RESERVATIONS:
        raise SystemExit(
            f"reservation totals are {dict(reservations)}, "
            f"expected {EXPECTED_RESERVATIONS}"
        )
    if not set(reservations) <= RESERVATIONS:
        raise SystemExit("reservation contains an unrecognized value")
    winner_rows = [row for row in rows if row["seat_filled"]]
    if len(winner_rows) != EXPECTED_WINNERS:
        raise SystemExit(f"parsed {len(winner_rows)} winners, expected 1,007")
    winner_controls = collections.Counter(
        (row["winner_sex_raw"], row["winner_caste_category"]) for row in winner_rows
    )
    if dict(winner_controls) != EXPECTED_WINNER_SEX_CATEGORY:
        raise SystemExit(
            f"winner sex/category totals are {dict(winner_controls)}, "
            f"expected {EXPECTED_WINNER_SEX_CATEGORY}"
        )
    if {row["winner_caste_category"] for row in winner_rows} != CATEGORIES:
        raise SystemExit("winner category contains an unrecognized value")

    parties = collections.Counter(row["party"] for row in winner_rows)
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
    inferred_uncontested = {
        (row["source_page"], row["district_raw"], row["ward_no"])
        for row in rows
        if row["uncontested_inferred"]
    }
    if inferred_uncontested != EXPECTED_INFERRED_UNCONTESTED:
        raise SystemExit(
            f"inferred uncontested seats are {inferred_uncontested}, "
            f"expected {EXPECTED_INFERRED_UNCONTESTED}"
        )
    LOGGER.warning(
        "uncontested result inferred from blank vote and margin cells",
        extra={
            "event": "source_consistency_exception",
            "seats": sorted(inferred_uncontested),
        },
    )
    conflicts = [
        row
        for row in winner_rows
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

    LOGGER.info(
        "seat expectations passed",
        extra={
            "event": "seat_expectations_passed",
            "rows": len(rows),
            "winners": len(winner_rows),
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
    """Parse, validate, and publish the 2005 member-seat table."""
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
