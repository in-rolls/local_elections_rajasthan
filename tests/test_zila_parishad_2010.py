"""Contracts for the 2010 Zila Parishad member-seat parser."""

import pandas

from scripts import parse_zila_parishad_2010 as parser


def test_retained_extraction_parses_to_the_published_grain():
    pages = parser.load_pages(parser.EXTRACTED)
    rows = parser.parse_pages(pages)
    parser.validate(rows)

    assert len(rows) == parser.EXPECTED_ROWS
    assert len({(row["district"], row["ward_no"]) for row in rows}) == len(rows)


def test_published_parquet_matches_the_parser():
    pages = parser.load_pages(parser.EXTRACTED)
    rows = parser.parse_pages(pages)
    expected = pandas.DataFrame(rows, columns=parser.OUTPUT_COLUMNS)
    for column in parser.NULLABLE_INTEGER_COLUMNS:
        expected[column] = expected[column].astype("Int64")
    actual = pandas.read_parquet(parser.OUTPUT)
    pandas.testing.assert_frame_equal(actual, expected)


def test_wrapped_names_and_source_recodes_remain_explicit():
    frame = pandas.read_parquet(parser.OUTPUT)

    assert (
        frame.loc[
            (frame["district"] == "BANSWARA") & (frame["ward_no"] == 10),
            "winner_name",
        ].item()
        == "KAMLASHANKAR CHARPOTA"
    )
    assert (
        frame.loc[
            (frame["district"] == "BARAN") & (frame["ward_no"] == 8),
            "winner_name",
        ].item()
        == "HEMENT KUMAR SHARMA"
    )

    district_recodes = frame[frame["district_inferred"] == 1]
    assert district_recodes.groupby(["district_raw", "district"]).size().to_dict() == {
        ("KARUALI", "KARAULI"): 27,
        ("SAWAIMADHOPUR", "SAWAI MADHOPUR"): 25,
    }
    ward_recodes = frame[frame["ward_no_inferred"] == 1]
    assert len(ward_recodes) == 27
    assert set(ward_recodes["district"]) == {"CHURU"}
    assert set(ward_recodes["ward_no_raw"] - ward_recodes["ward_no"]) == {4}


def test_printed_controls_are_exact():
    frame = pandas.read_parquet(parser.OUTPUT)

    assert frame["reservation"].value_counts().to_dict() == {
        "GEN": 260,
        "GENW": 253,
        "SC": 96,
        "SCW": 83,
        "ST": 86,
        "STW": 77,
        "OBC": 85,
        "OBCW": 73,
    }
    assert frame["party"].value_counts().to_dict() == {
        "INC": 603,
        "BJP": 365,
        "IND": 35,
        "CPI(M)": 7,
        "BSP": 3,
    }
    assert frame["elected_uncontested"].sum() == 27
