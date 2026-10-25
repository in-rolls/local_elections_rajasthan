"""Retain general-election events, candidate identities, and source disagreements."""

import numpy as np
import pandas as pd

from local_elections_rajasthan.build.common import add_geography, normalize_string, save
from local_elections_rajasthan.paths import table

CANDIDATE_NUMERIC = [
    "gp_no",
    "candidate_serial_no",
    "candidate_age",
    "candidate_assets_inr",
    "candidate_children_before_1995_11_27",
    "candidate_children_from_1995_11_28",
]
WINNER_NUMERIC = [
    "gp_no",
    "contesting_candidates",
    "electors",
    "votes_polled",
    "votes_rejected",
    "votes_valid",
    "turnout_pct",
    "winner_votes",
    "runner_up_votes",
    "votes_nota",
    "votes_tendered",
]


def read_events(key, row_column, numeric):
    frame = pd.read_parquet(table(key))
    frame = frame.drop(columns=["candidate_mobile", "candidate_email"], errors="ignore")
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
        [c for c in frame if c not in [row_column, "gp_no"]]
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
    frame["primary_reserved_available"] = frame.primary_reserved_woman.notna()
    return frame


def unique_key(frame, keys):
    return frame.event_key.notna() & ~frame.duplicated(keys, keep=False)


def build():
    primary = add_geography(pd.read_parquet(table("sarpanch_2020")))
    primary = primary.loc[
        primary.match_key.notna() & ~primary.match_key.duplicated(keep=False),
        ["match_key", "reserved_woman", "reserved_caste", "reserved_raw"],
    ].rename(
        columns={
            "reserved_woman": "primary_reserved_woman",
            "reserved_caste": "primary_reserved_caste",
            "reserved_raw": "primary_reserved_raw",
        }
    )
    candidates = add_primary(
        event_keys(
            read_events(
                "sarpanch_candidates", "candidate_source_row", CANDIDATE_NUMERIC
            ),
            "gram_panchayat",
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
            "candidate_serial_no",
            "candidate_name",
            "candidate_relation_name",
        ],
    )
    candidates["candidate_name_unique"] = unique_key(
        candidates, ["event_key", "candidate_name"]
    )
    candidates["candidate_woman"] = (
        candidates.candidate_woman_raw.str.strip()
        .str.upper()
        .map({"F": 1, "M": 0, "O": 0})
        .astype("Int32")
    )
    sex = candidates.loc[
        candidates.candidate_key_unique & candidates.candidate_name_unique,
        ["event_key", "candidate_name", "candidate_woman"],
    ].dropna(subset=["event_key", "candidate_name"])
    grouped = candidates.groupby("event_key", dropna=False, sort=True)
    reservation = grouped.agg(
        reserved_raw_from_candidates=(
            "reserved_raw",
            lambda x: x.dropna().iloc[0] if x.nunique() == 1 else None,
        ),
        reserved_from_candidates_unique=(
            "reserved_raw",
            lambda x: x.nunique() == 1,
        ),
        n_candidate_records=("event_key", "size"),
        n_ambiguous_candidate_records=("candidate_key_unique", lambda x: (~x).sum()),
    ).reset_index()
    winners = add_primary(
        event_keys(
            read_events("sarpanch_winners", "winner_source_row", WINNER_NUMERIC),
            "gram_panchayat",
        ),
        primary,
    )
    winners["winner_key_unique"] = unique_key(winners, ["event_key"])
    winners["gp_event_unique"] = winners.match_key.notna() & winners.groupby(
        "match_key", dropna=False
    ).event_key.transform("nunique").eq(1)
    for column, dest in [
        ("winner_name", "winner_woman_2020"),
        ("runner_up_name", "runner_up_woman_2020"),
    ]:
        winners = winners.merge(
            sex.rename(
                columns={
                    "candidate_name": column,
                    "candidate_woman": dest,
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
        "sarpanch_candidates:" + candidates.candidate_source_row.astype(str)
    )
    winners["source_id"] = "sarpanch_winners:" + winners.winner_source_row.astype(str)
    save(
        candidates,
        "sarpanch_candidate_events_2020",
        integer=["candidate_source_row", "primary_reserved_woman", "candidate_woman"],
    )
    save(
        winners,
        "sarpanch_winner_events_2020",
        integer=[
            "winner_source_row",
            "primary_reserved_woman",
            "winner_woman_2020",
            "runner_up_woman_2020",
            "n_candidate_records",
            "n_ambiguous_candidate_records",
        ],
    )


if __name__ == "__main__":
    build()
