"""Contracts for the 2010 Panchayat Samiti member-seat parser."""

import pandas

from scripts import parse_panchayat_samiti_2010 as parser


def test_retained_extraction_parses_to_the_published_grain():
    pages = parser.load_pages(parser.EXTRACTED)
    rows = parser.parse_pages(pages)
    parser.validate(rows)

    assert len(rows) == parser.EXPECTED_ROWS
    assert len(
        {(row["district_raw"], row["samiti_raw"], row["ward_no"]) for row in rows}
    ) == len(rows)


def test_published_parquet_matches_the_parser():
    pages = parser.load_pages(parser.EXTRACTED)
    expected = pandas.DataFrame(
        parser.parse_pages(pages), columns=parser.OUTPUT_COLUMNS
    )
    actual = pandas.read_parquet(parser.OUTPUT)
    pandas.testing.assert_frame_equal(actual, expected)


def test_only_documented_recode_preserves_its_raw_value():
    frame = pandas.read_parquet(parser.OUTPUT)
    category_recodes = frame[frame["winner_category_raw"] != frame["winner_category"]]
    assert category_recodes[["serial", "source_page"]].to_dict("records") == [
        {"serial": 4036, "source_page": 318}
    ]
    assert category_recodes.iloc[0]["winner_category_raw"] == "G E N W"
    assert category_recodes.iloc[0]["winner_category"] == "GENW"

    ward_recodes = frame[frame["ward_no_raw"] != frame["ward_no"]]
    assert ward_recodes[["serial", "source_page"]].to_dict("records") == [
        {"serial": 4401, "source_page": 327}
    ]
    assert ward_recodes.iloc[0]["ward_no_raw"] == 17
    assert ward_recodes.iloc[0]["ward_no"] == 16

    conflicts = frame[frame["winner_category_sex_agree"] == 0]
    assert conflicts[
        ["serial", "source_page", "winner_sex_raw", "winner_category"]
    ].to_dict("records") == [
        {
            "serial": 71,
            "source_page": 218,
            "winner_sex_raw": "M",
            "winner_category": "OBCW",
        }
    ]
