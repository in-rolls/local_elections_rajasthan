"""Retain general-election events, candidate identities, and source disagreements."""

import re

import numpy as np
import pandas as pd

from local_elections_rajasthan.build.common import add_geography, normalize_string, save
from local_elections_rajasthan.paths import DATA

CANDIDATE_NUMERIC = [
    "sr_no",
    "contesting_candidate_serial_no",
    "age",
    "total_value_of_capital_assets",
    "children_before27111995",
    "children_on_or_after28111995",
]
WINNER_NUMERIC = [
    "sr_no",
    "total_no_of_contesting_candidate",
    "total_electorate_votes",
    "total_polled_votes",
    "rejected_votes",
    "total_valid_votes",
    "poll_percent",
    "vote_secure_by_winner",
    "vote_secure_by_runnerup",
    "total_no_of_nota_count",
    "tendered_votes",
]


def clean_name(name):
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def read_events(filename, row_column, numeric):
    frame = pd.read_parquet(DATA / "scrape_2020_2022" / filename).rename(
        columns=clean_name
    )
    frame = frame.drop(columns=["mobile_no", "email_address"], errors="ignore")
    for c in frame:
        frame[c] = (
            frame[c].astype("string").str.strip().replace({"": pd.NA, "NA": pd.NA})
        )
    for c in numeric:
        frame[c] = pd.to_numeric(frame[c], errors="coerce").astype("float64")
    frame[row_column] = np.arange(1, len(frame) + 1, dtype=np.int32)
    frame = frame.loc[
        frame.election_type.eq("General Election")
        & frame.election_duration.isin(["JAN-MAR 2020", "SEP-OCT 2020"])
    ]
    return frame.drop_duplicates(
        [c for c in frame if c not in [row_column, "sr_no"]]
    ).reset_index(drop=True)


def event_keys(frame, gp):
    frame["district_raw"] = frame.district.str.strip().str.upper()
    frame["samiti_raw"] = (
        frame.panchayat_samiti.str.replace(
            r" PANCHAYAT SAMITI$", "", case=False, regex=True
        )
        .str.strip()
        .str.upper()
    )
    frame["gp_std"] = frame[gp].map(normalize_string)
    frame = add_geography(frame)
    frame["event_key"] = (
        frame.election_type + "|" + frame.election_duration + "|" + frame.match_key
    )
    return frame


def add_primary(frame, primary):
    frame = frame.merge(primary, on="match_key", how="left", validate="many_to_one")
    frame["primary_reservation_available"] = frame.primary_female_reserved.notna()
    return frame


def unique_key(frame, keys):
    return frame.event_key.notna() & ~frame.duplicated(keys, keep=False)


def build():
    primary = add_geography(pd.read_parquet(DATA / "source_2020_std.parquet"))
    primary = primary.loc[
        primary.match_key.notna() & ~primary.match_key.duplicated(keep=False),
        ["match_key", "female_reserved", "caste_category", "reservation_raw"],
    ].rename(
        columns={
            "female_reserved": "primary_female_reserved",
            "caste_category": "primary_caste_category",
            "reservation_raw": "primary_reservation_raw",
        }
    )
    candidates = add_primary(
        event_keys(
            read_events(
                "ContestingSarpanch.parquet", "candidate_source_row", CANDIDATE_NUMERIC
            ),
            "name_of_gram_panchayat",
        ),
        primary,
    )
    candidates["gp_event_unique"] = candidates.match_key.notna() & candidates.groupby(
        "match_key", dropna=False
    ).event_key.transform("nunique").eq(1)
    candidates["candidate_key_unique"] = unique_key(
        candidates,
        [
            "event_key",
            "contesting_candidate_serial_no",
            "name_of_contesting_candidate",
            "father_husband_of_contesting_candidate",
        ],
    )
    candidates["candidate_name_unique"] = unique_key(
        candidates, ["event_key", "name_of_contesting_candidate"]
    )
    candidates["candidate_female"] = (
        candidates.gender.str.strip()
        .str.upper()
        .map({"F": 1, "M": 0, "O": 0})
        .astype("Int32")
    )
    sex = candidates.loc[
        candidates.candidate_key_unique & candidates.candidate_name_unique,
        ["event_key", "name_of_contesting_candidate", "candidate_female"],
    ].dropna(subset=["event_key", "name_of_contesting_candidate"])
    grouped = candidates.groupby("event_key", dropna=False, sort=True)
    reservation = grouped.agg(
        candidate_reservation_raw=(
            "category_of_gram_panchayat",
            lambda x: x.dropna().iloc[0] if x.nunique() == 1 else None,
        ),
        candidate_reservation_unique=(
            "category_of_gram_panchayat",
            lambda x: x.nunique() == 1,
        ),
        n_candidate_records=("event_key", "size"),
        n_ambiguous_candidate_records=("candidate_key_unique", lambda x: (~x).sum()),
    ).reset_index()
    winners = add_primary(
        event_keys(
            read_events("WinnerSarpanch.parquet", "winner_source_row", WINNER_NUMERIC),
            "name_of_gram_panchyat",
        ),
        primary,
    )
    winners["winner_key_unique"] = unique_key(winners, ["event_key"])
    winners["gp_event_unique"] = winners.match_key.notna() & winners.groupby(
        "match_key", dropna=False
    ).event_key.transform("nunique").eq(1)
    for column, dest in [
        ("winner_candidate_name", "female_winner_2020"),
        ("runnerup_candidate_name", "female_runnerup_2020"),
    ]:
        winners = winners.merge(
            sex.rename(
                columns={
                    "name_of_contesting_candidate": column,
                    "candidate_female": dest,
                }
            ),
            on=["event_key", column],
            how="left",
            validate="many_to_one",
        )
    winners = winners.merge(
        reservation, on="event_key", how="left", validate="many_to_one"
    )
    candidates["source_id"] = (
        "ContestingSarpanch:" + candidates.candidate_source_row.astype(str)
    )
    winners["source_id"] = "WinnerSarpanch:" + winners.winner_source_row.astype(str)
    save(
        candidates,
        "candidates_2020_events.parquet",
        integer=["candidate_source_row", "primary_female_reserved", "candidate_female"],
    )
    save(
        winners,
        "winners_2020_events.parquet",
        integer=[
            "winner_source_row",
            "primary_female_reserved",
            "female_winner_2020",
            "female_runnerup_2020",
            "n_candidate_records",
            "n_ambiguous_candidate_records",
        ],
    )


if __name__ == "__main__":
    build()
