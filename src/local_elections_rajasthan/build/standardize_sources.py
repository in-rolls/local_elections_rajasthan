"""Standardize saved GP records without inferring missing winner attributes."""

import re
import string

import pandas as pd

from local_elections_rajasthan.build.common import latin_ascii, save
from local_elections_rajasthan.paths import DATA, ROOT


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


def standardize(year):
    filename = (
        f"sarpanch_{year}"
        + ("_manual_sex" if year == 2015 else "_clean" if year == 2020 else "")
        + ".csv"
    )
    source = pd.read_csv(
        ROOT / "data/source/sarpanch" / filename,
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
        else ["dist_name", "samiti_name", "gp", "gp_new", "reservation"]
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
    frame["winner_female"] = (
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
    frame["female_reserved"] = pd.Series([x[0] for x in results], dtype="Int32")
    frame["caste_category"] = [x[1] for x in results]
    frame["reservation_raw"] = source[names[4]]
    return frame


def main():
    for year in (2005, 2010, 2015, 2020):
        save(
            standardize(year),
            f"source_{year}_std.parquet",
            integer=["year", "winner_female", "female_reserved"],
            directory=DATA,
        )


if __name__ == "__main__":
    main()
