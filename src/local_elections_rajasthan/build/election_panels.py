"""Build unambiguous election histories from reviewed geographic labels."""

from functools import reduce

import pandas as pd

from local_elections_rajasthan.build.common import (
    PRODUCTS,
    match_key,
    normalize_string,
    read_election,
    save,
)

YEARS = (2005, 2010, 2015, 2020)


def winner_attributes(sources):
    winners = pd.read_parquet(PRODUCTS / "winners_2020_events.parquet")
    winners = winners.loc[
        winners.winner_key_unique & winners.gp_event_unique,
        [
            "match_key",
            "female_winner_2020",
            "candidate_reservation_raw",
            "candidate_reservation_unique",
        ],
    ].rename(columns={"female_winner_2020": "winner_sex_from_cand"})
    raw = winners.candidate_reservation_raw.astype("string").str.upper()
    winners["candidate_reserved"] = raw.str.contains(r"WOMAN|W$", regex=True).astype(
        "Int32"
    )
    winners["candidate_caste"] = raw.str.extract(r"^(GEN|OBC|SC|ST)", expand=False)
    latest = sources[2020]
    latest = latest.loc[
        ~latest.match_key.duplicated(keep=False),
        ["match_key", "female_reserved", "caste_category"],
    ]
    winners = winners.merge(latest, on="match_key", how="left", validate="one_to_one")
    winners["reservation_gender_conflict"] = winners.candidate_reserved.astype(
        "Int32"
    ).ne(winners.female_reserved.astype("Int32"))
    winners["reservation_caste_conflict"] = winners.candidate_caste.astype("string").ne(
        winners.caste_category.astype("string")
    )
    return winners.drop(columns=["female_reserved", "caste_category"])


def prepare_source(frame, year):
    frame = frame[
        [
            "match_key",
            "district_std",
            "samiti_std",
            "gp_std",
            "female_reserved",
            "caste_category",
            "winner_female",
            "winner_name",
            "source_id",
        ]
    ]
    return frame.rename(columns={c: f"{c}_{year}" for c in frame if c != "match_key"})


def remove_collisions(frame, year):
    normalized = pd.DataFrame(
        {
            kind: frame[f"{kind}_{year}"].map(normalize_string)
            for kind in ["district_std", "samiti_std", "gp_std"]
        }
    )
    triplet = match_key(normalized, ["district_std", "samiti_std", "gp_std"])
    keys = (
        pd.DataFrame({"triplet": triplet, "match_key": frame.match_key})
        .dropna(subset=["match_key"])
        .drop_duplicates()
    )
    ambiguous = keys.loc[keys.triplet.duplicated(keep=False), "triplet"]
    return frame.loc[~triplet.isin(ambiguous)]


def build_panel(sources, winners, waves):
    frame = reduce(
        lambda a, b: a.merge(b, on="match_key", validate="many_to_many"),
        [prepare_source(sources[y], y) for y in waves],
    )
    frame = frame.loc[~frame.match_key.duplicated(keep=False)].copy()
    last = waves[-1]
    if last == 2020:
        frame["match_key_2020"] = match_key(
            frame, ["district_std_2020", "samiti_std_2020", "gp_std_2020"]
        )
        frame = frame.merge(
            winners.rename(columns={"match_key": "match_key_2020"}),
            on="match_key_2020",
            how="left",
            validate="many_to_one",
        )
    for year in waves:
        frame[f"treat_{year}"] = frame[f"female_reserved_{year}"].astype("Int32")
    if len(waves) == 2:
        frame["case"] = frame[f"treat_{waves[0]}"].astype("string").fillna(
            "NA"
        ) + frame[f"treat_{last}"].astype("string").fillna("NA")
    for year in waves:
        frame[f"female_winner_{year}"] = frame[
            "winner_sex_from_cand" if year == 2020 else f"winner_female_{year}"
        ].astype("Int32")
    if len(waves) == 4:
        treatment = [frame[f"treat_{y}"] for y in YEARS[:-1]]
        frame["never_treated"] = (
            treatment[0].eq(0) & treatment[1].eq(0) & treatment[2].eq(0)
        ).astype("Int32")
        frame["always_treated"] = (
            treatment[0].eq(1) & treatment[1].eq(1) & treatment[2].eq(1)
        ).astype("Int32")
        frame["count_treated"] = treatment[0] + treatment[1] + treatment[2]
    for year in (2020, 2015, 2010) if len(waves) == 4 else [last]:
        frame[f"dist_samiti_{year}"] = (
            frame[f"district_std_{year}"].astype("string").str.lower().fillna("NA")
            + "_"
            + frame[f"samiti_std_{year}"].astype("string").str.lower().fillna("NA")
        )
    for year in waves:
        for caste in ("obc", "sc", "st"):
            frame[f"{caste}_{year}"] = (
                frame[f"caste_category_{year}"]
                .astype("string")
                .eq(caste.upper())
                .astype("Int32")
            )
    if len(waves) == 2:
        frame = remove_collisions(frame, last)
    return frame[
        [c for c in frame if not c.startswith("source_id_")]
        + [c for c in frame if c.startswith("source_id_")]
    ].reset_index(drop=True)


def build():
    sources = {year: read_election(year) for year in YEARS}
    save(pd.concat(sources.values(), ignore_index=True), "source_records.parquet")
    sources = {
        year: frame.loc[frame.gp_std.notna() & frame.gp_std.ne("")].copy()
        for year, frame in sources.items()
    }
    winners = winner_attributes(sources)
    for waves in [(2005, 2010), (2010, 2015), (2015, 2020), YEARS]:
        frame = build_panel(sources, winners, waves)
        numeric_fields = [
            c
            for c in frame
            if c.startswith(
                ("female_reserved_", "winner_female_", "winner_sex_from_cand")
            )
        ]
        save(
            frame,
            f"raj_{waves[0] % 100:02d}_{waves[-1] % 100:02d}.parquet",
            integer=numeric_fields,
        )


if __name__ == "__main__":
    build()
