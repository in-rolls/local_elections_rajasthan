"""Standardize saved GP records without inferring missing winner attributes."""

import re
import string

import pandas as pd

from local_elections_rajasthan.build.common import latin_ascii, save
from local_elections_rajasthan.paths import MANUAL, RAW, RELEASE


def reservation(value):
    if pd.isna(value) or not value.strip():
        return pd.NA, None
    text = value.strip().upper()
    female = int(bool(re.search(r"\bW\b|WOMAN|W$", text)))
    for pattern, category in [
        (r"^GEN|GENERAL", "GEN"),
        (r"^OBC|OTHER BACKWARD", "OBC"),
        (r"^SC[^H]|^SC$|SCHEDULED CASTE", "SC"),
        (r"^ST|SCHEDULED TRIBE", "ST"),
    ]:
        if re.search(pattern, text):
            return female, category
    return female, None


def normalize_gp(value):
    value = latin_ascii(value)
    if value is None:
        return None
    return (
        re.sub(r"\s+", " ", value.lower())
        .strip()
        .translate(str.maketrans("", "", string.punctuation))
    )


# 2020's file arrived already named as cleaned.
SUFFIX = {2020: "_clean"}


def standardize(year):
    # 2015's winner sex was coded by hand from names, so that year's input is
    # the hand-coded copy in data/manual/; the others are as received.
    source = pd.read_csv(
        MANUAL / "sarpanch/sarpanch_2015_manual_sex.csv"
        if year == 2015
        else RAW / "sarpanch" / f"sarpanch_{year}{SUFFIX.get(year, '')}.csv",
        keep_default_na=False,
        na_values=["", "NA"],
    )
    # readr trims leading and trailing whitespace on all string columns.
    for c in source.select_dtypes(include=["object", "str"]):
        source[c] = source[c].str.strip().replace("", None)
    names = (
        [
            "District",
            "PanchayatSamiti",
            "NameOfGramPanchyat",
            "NameOfGramPanchyat",
            "CategoryOfGramPanchyat",
        ]
        if year == 2020
        else [
            "dist_name",
            "samiti_name",
            "gp",
            "gp_new",
            "reservation",
        ]  # old-name: raw file header
    )
    frame = pd.DataFrame(
        {
            "year": year,
            "district_raw": source[names[0]].str.strip().str.upper(),
            "samiti_raw": source[names[1]].str.strip().str.upper(),
            "gp_raw": source[names[2]].str.strip().str.upper(),
            "gp_std": source[names[3]].map(normalize_gp),
        }
    )
    frame["winner_name"] = None if year == 2020 else source["name"]
    frame["winner_woman"] = (
        pd.Series(pd.NA, index=source.index, dtype="Int32")
        if year == 2020
        else (
            source["sex_manual" if year == 2015 else "sex"]
            .astype("string")
            .str.strip()
            .str.upper()
            .map({"F": 1, "FEMALE": 1, "1": 1, "M": 0, "MALE": 0, "0": 0})
            .astype("Int32")
        )
    )
    results = source[names[4]].map(reservation)
    frame["reserved_woman"] = pd.Series([x[0] for x in results], dtype="Int32")
    frame["reserved_caste"] = [x[1] for x in results]
    frame["reserved_raw"] = source[names[4]]
    return frame


def main():
    for year in (2005, 2010, 2015, 2020):
        save(
            standardize(year),
            f"sarpanch_{year}",
            integer=["year", "winner_woman", "reserved_woman"],
            directory=RELEASE,
        )


if __name__ == "__main__":
    main()
