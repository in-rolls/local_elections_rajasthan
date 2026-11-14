"""Build unambiguous election histories from the reviewed seat crosswalks."""

import re
from functools import reduce
from itertools import pairwise

import pandas as pd
from rapidfuzz.distance import JaroWinkler

from local_elections_rajasthan.build.common import (
    PRODUCTS,
    match_key,
    normalize_string,
    read_election,
    require,
    save,
)
from local_elections_rajasthan.paths import MANUAL, TABLES

CROSSWALKS = MANUAL / "crosswalks"
PRINTED = {
    "district": "district_raw",
    "samiti": "samiti_raw",
    "gram_panchayat": "gp_raw",
}

YEARS = (2005, 2010, 2015, 2020)


def winner_attributes(sources):
    winners = pd.read_parquet(PRODUCTS / TABLES["sarpanch_winner_events_2020"])
    winners = winners.loc[
        winners.winner_key_unique & winners.gp_event_unique,
        [
            "match_key",
            "winner_woman_2020",
            "reserved_raw_from_candidates",
            "reserved_from_candidates_unique",
        ],
    ].rename(columns={"winner_woman_2020": "winner_woman_from_candidates_2020"})
    raw = winners.reserved_raw_from_candidates.astype("string").str.upper()
    winners["reserved_woman_from_candidates"] = raw.str.contains(
        r"WOMAN|W$", regex=True
    ).astype("Int32")
    winners["reserved_caste_from_candidates"] = raw.str.extract(
        r"^(GEN|OBC|SC|ST)", expand=False
    )
    latest = sources[2020]
    latest = latest.loc[
        ~latest.match_key.duplicated(keep=False),
        ["match_key", "reserved_woman", "reserved_caste"],
    ]
    winners = winners.merge(latest, on="match_key", how="left", validate="one_to_one")
    winners["reserved_woman_conflict"] = winners.reserved_woman_from_candidates.astype(
        "Int32"
    ).ne(winners.reserved_woman.astype("Int32"))
    winners["reserved_caste_conflict"] = winners.reserved_caste_from_candidates.astype(
        "string"
    ).ne(winners.reserved_caste.astype("string"))
    return winners.drop(columns=["reserved_woman", "reserved_caste"])


def prepare_source(frame, year):
    frame = frame[
        [
            "match_key",
            "district_std",
            "samiti_std",
            "gp_std",
            "reserved_woman",
            "reserved_caste",
            "winner_woman",
            "winner_name",
            "source_id",
        ]
    ]
    return frame.rename(columns={c: f"{c}_{year}" for c in frame})


def accepted_links(sources, first, second):
    """Accepted pairs of data/manual/crosswalks/sarpanch_<first>_<second>.csv
    in which each seat appears once."""
    name = f"sarpanch_{first}_{second}.csv"
    pairs = pd.read_csv(CROSSWALKS / name, dtype="string", keep_default_na=False)
    keys = [f"source_id_{first}", f"source_id_{second}"]
    require(not pairs.duplicated(keys).any(), f"{name}: a pair is listed twice")
    require(
        pairs.decision.isin(["accept", "reject"]).all(),
        f"{name}: decision must be accept or reject",
    )
    # A source id is a row number, so the printed names guard against a
    # crosswalk that no longer points at the rows it was reviewed on.
    for year in (first, second):
        seats = sources[year].set_index("source_id")
        ids = pairs[f"source_id_{year}"]
        require(ids.isin(seats.index).all(), f"{name}: unknown {year} source id")
        for column, source in PRINTED.items():
            printed = ids.map(seats[source]).fillna("").astype("string")
            require(
                printed.eq(pairs[f"{column}_{year}"]).all(),
                f"{name}: {column}_{year} differs from the source record",
            )
    pairs = pairs.loc[pairs.decision.eq("accept")]
    # A seat accepted into two pairs is ambiguous; both pairs go.
    pairs = pairs.loc[
        ~pairs[keys[0]].duplicated(keep=False) & ~pairs[keys[1]].duplicated(keep=False)
    ]
    names = [
        pairs[f"gram_panchayat_{year}"].map(normalize_string)
        for year in (first, second)
    ]
    return pairs[keys].assign(
        link_basis=pairs.basis,
        name_score=[JaroWinkler.similarity(a, b) for a, b in zip(*names, strict=True)],
    )


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


def build_panel(sources, links, winners, waves):
    last = waves[-1]
    described = ["link_basis", "name_score"]
    frame = reduce(
        lambda a, b: a.merge(b, validate="one_to_one"),
        [
            links[pair] if len(waves) == 2 else links[pair].drop(columns=described)
            for pair in pairwise(waves)
        ],
    )
    for year in waves:
        frame = frame.merge(
            prepare_source(sources[year], year),
            on=f"source_id_{year}",
            validate="one_to_one",
        )
    # The latest wave names the panchayat; earlier waves may spell it differently.
    frame = frame.rename(columns={f"match_key_{last}": "match_key"}).drop(
        columns=[f"match_key_{year}" for year in waves[:-1]]
    )
    frame = frame[["match_key"] + [c for c in frame if c != "match_key"]]
    frame = frame.loc[~frame.match_key.duplicated(keep=False)].copy()
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
        frame[f"treat_{year}"] = frame[f"reserved_woman_{year}"].astype("Int32")
    if len(waves) == 2:
        frame["case"] = frame[f"treat_{waves[0]}"].astype("string").fillna(
            "NA"
        ) + frame[f"treat_{last}"].astype("string").fillna("NA")
    # No merged outcome column: winner_woman_<year> is the source's own record
    # (none for 2020) and winner_woman_from_candidates_2020 is read from the
    # 2020 candidate records. An analysis that wants one series combines them.
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
                frame[f"reserved_caste_{year}"]
                .astype("string")
                .eq(caste.upper())
                .astype("Int32")
            )
    if len(waves) == 2:
        frame = remove_collisions(frame, last)
    last_columns = [c for c in described if c in frame] + [
        c for c in frame if c.startswith("source_id_")
    ]
    return frame[
        [c for c in frame if c not in last_columns] + last_columns
    ].reset_index(drop=True)


def build():
    records = {year: read_election(year) for year in YEARS}
    save(pd.concat(records.values(), ignore_index=True), "sarpanch_source_records")
    links = {pair: accepted_links(records, *pair) for pair in pairwise(YEARS)}
    sources = {
        year: frame.loc[frame.gp_std.notna() & frame.gp_std.ne("")].copy()
        for year, frame in records.items()
    }
    winners = winner_attributes(sources)
    for waves in [(2005, 2010), (2010, 2015), (2015, 2020), YEARS]:
        frame = build_panel(sources, links, winners, waves)
        # the per-wave 1/0 columns, e.g. reserved_woman_2015, winner_woman_2010
        numeric_fields = [
            c
            for c in frame
            if re.fullmatch(
                r"(reserved_woman|winner_woman|winner_woman_from_candidates)_\d{4}", c
            )
        ]
        save(
            frame,
            f"sarpanch_links_{waves[0]}_{waves[-1]}",
            integer=numeric_fields,
        )


if __name__ == "__main__":
    build()
