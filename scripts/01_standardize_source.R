# 01a_raj_standardize_source.R
# Standardize 4 raw Rajasthan election source files
# Output: data/fin/source_YYYY_std.parquet for each year

library(readr)
library(dplyr)
library(arrow)
library(stringi)
library(here)


message("=== Standardizing Rajasthan Source Files ===")

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

standardize_reservation <- function(res) {
    res_upper <- toupper(trimws(res))

    female_reserved <- as.integer(grepl("\\bW\\b|WOMAN|W$", res_upper))

    caste_category <- case_when(
        grepl("^GEN|GENERAL", res_upper) ~ "GEN",
        grepl("^OBC|OTHER BACKWARD", res_upper) ~ "OBC",
        grepl("^SC[^H]|^SC$|SCHEDULED CASTE", res_upper) ~ "SC",
        grepl("^ST|SCHEDULED TRIBE", res_upper) ~ "ST",
        TRUE ~ NA_character_
    )

    list(female_reserved = female_reserved, caste_category = caste_category)
}

standardize_sex <- function(sex, category = NULL, infer_from_category = FALSE) {
    if (!is.null(sex) && !all(is.na(sex) | sex == "")) {
        sex_upper <- toupper(trimws(sex))
        return(as.integer(sex_upper %in% c("F", "FEMALE", "1")))
    }
    if (infer_from_category && !is.null(category)) {
        return(as.integer(grepl("WOMAN|W$|\\(W\\)", toupper(category))))
    }
    NA_integer_
}

normalize_gp_name <- function(x) {
    x <- stri_trans_general(x, "Latin-ASCII")
    x <- stri_trans_tolower(x)
    x <- gsub("\\s+", " ", x)
    x <- trimws(x)
    x <- gsub("[[:punct:]]", "", x)
    x
}

# =============================================================================
# 2005 SOURCE
# =============================================================================
message("\n--- Processing 2005 source ---")

raw_2005 <- read_csv(
    here("data/source/sarpanch/sarpanch_2005.csv"),
    show_col_types = FALSE
)
message("Read", nrow(raw_2005), "rows from 2005 source")

res_2005 <- mapply(function(r) standardize_reservation(r), raw_2005$reservation, SIMPLIFY = FALSE)

std_2005 <- raw_2005 %>%
    mutate(
        year = 2005L,
        district_raw = toupper(trimws(dist_name)),
        samiti_raw = toupper(trimws(samiti_name)),
        gp_raw = toupper(trimws(gp)),
        gp_std = normalize_gp_name(gp_new),
        winner_name = name,
        winner_female = standardize_sex(sex),
        female_reserved = sapply(res_2005, function(x) x$female_reserved),
        caste_category = sapply(res_2005, function(x) x$caste_category),
        reservation_raw = reservation
    ) %>%
    select(
        year, district_raw, samiti_raw, gp_raw, gp_std,
        winner_name, winner_female, female_reserved, caste_category, reservation_raw
    )

message("  District raw values: ", n_distinct(std_2005$district_raw))
message("  Samiti raw values: ", n_distinct(std_2005$samiti_raw))
message("  Female reserved: ", sum(std_2005$female_reserved, na.rm = TRUE), "/", nrow(std_2005))

write_parquet(std_2005, here("data/fin/source_2005_std.parquet"))
message("  Saved: data/fin/source_2005_std.parquet")

# =============================================================================
# 2010 SOURCE
# =============================================================================
message("\n--- Processing 2010 source ---")

raw_2010 <- read_csv(
    here("data/source/sarpanch/sarpanch_2010.csv"),
    show_col_types = FALSE
)
message("Read", nrow(raw_2010), "rows from 2010 source")

res_2010 <- mapply(function(r) standardize_reservation(r), raw_2010$reservation, SIMPLIFY = FALSE)

std_2010 <- raw_2010 %>%
    mutate(
        year = 2010L,
        district_raw = toupper(trimws(dist_name)),
        samiti_raw = toupper(trimws(samiti_name)),
        gp_raw = toupper(trimws(gp)),
        gp_std = normalize_gp_name(gp_new),
        winner_name = name,
        winner_female = standardize_sex(sex),
        female_reserved = sapply(res_2010, function(x) x$female_reserved),
        caste_category = sapply(res_2010, function(x) x$caste_category),
        reservation_raw = reservation
    ) %>%
    select(
        year, district_raw, samiti_raw, gp_raw, gp_std,
        winner_name, winner_female, female_reserved, caste_category, reservation_raw
    )

message("  District raw values: ", n_distinct(std_2010$district_raw))
message("  Samiti raw values: ", n_distinct(std_2010$samiti_raw))
message("  Female reserved: ", sum(std_2010$female_reserved, na.rm = TRUE), "/", nrow(std_2010))

write_parquet(std_2010, here("data/fin/source_2010_std.parquet"))
message("  Saved: data/fin/source_2010_std.parquet")

# =============================================================================
# 2015 SOURCE
# =============================================================================
message("\n--- Processing 2015 source ---")

raw_2015 <- read_csv(
    here("data/source/sarpanch/sarpanch_2015_manual_sex.csv"),
    show_col_types = FALSE
)
message("Read", nrow(raw_2015), "rows from 2015 source")

res_2015 <- mapply(function(r) standardize_reservation(r), raw_2015$reservation, SIMPLIFY = FALSE)

std_2015 <- raw_2015 %>%
    mutate(
        year = 2015L,
        district_raw = toupper(trimws(dist_name)),
        samiti_raw = toupper(trimws(samiti_name)),
        gp_raw = toupper(trimws(gp)),
        gp_std = normalize_gp_name(gp_new),
        winner_name = name,
        winner_female = standardize_sex(sex_manual),
        female_reserved = sapply(res_2015, function(x) x$female_reserved),
        caste_category = sapply(res_2015, function(x) x$caste_category),
        reservation_raw = reservation
    ) %>%
    select(
        year, district_raw, samiti_raw, gp_raw, gp_std,
        winner_name, winner_female, female_reserved, caste_category, reservation_raw
    )

message("  District raw values: ", n_distinct(std_2015$district_raw))
message("  Samiti raw values: ", n_distinct(std_2015$samiti_raw))
message("  Female reserved: ", sum(std_2015$female_reserved, na.rm = TRUE), "/", nrow(std_2015))
message("  Winner female inferred: ", sum(std_2015$winner_female == 1, na.rm = TRUE))
message("  Winner male inferred: ", sum(std_2015$winner_female == 0, na.rm = TRUE))
message("  Winner sex unknown: ", sum(is.na(std_2015$winner_female)))

write_parquet(std_2015, here("data/fin/source_2015_std.parquet"))
message("  Saved: data/fin/source_2015_std.parquet")

# =============================================================================
# 2020 SOURCE
# =============================================================================
message("\n--- Processing 2020 source ---")

raw_2020 <- read_csv(
    here("data/source/sarpanch/sarpanch_2020_clean.csv"),
    show_col_types = FALSE
)
message("Read", nrow(raw_2020), "rows from 2020 source")

res_2020 <- mapply(function(r) standardize_reservation(r), raw_2020$CategoryOfGramPanchyat, SIMPLIFY = FALSE)

std_2020 <- raw_2020 %>%
    mutate(
        year = 2020L,
        district_raw = toupper(trimws(District)),
        samiti_raw = toupper(trimws(PanchayatSamiti)),
        gp_raw = toupper(trimws(NameOfGramPanchyat)),
        gp_std = normalize_gp_name(NameOfGramPanchyat),
        winner_name = NA_character_,
        winner_female = NA_integer_,
        female_reserved = sapply(res_2020, function(x) x$female_reserved),
        caste_category = sapply(res_2020, function(x) x$caste_category),
        reservation_raw = CategoryOfGramPanchyat
    ) %>%
    select(
        year, district_raw, samiti_raw, gp_raw, gp_std,
        winner_name, winner_female, female_reserved, caste_category, reservation_raw
    )

message("  District raw values: ", n_distinct(std_2020$district_raw))
message("  Samiti raw values: ", n_distinct(std_2020$samiti_raw))
message("  Female reserved: ", sum(std_2020$female_reserved, na.rm = TRUE), "/", nrow(std_2020))

write_parquet(std_2020, here("data/fin/source_2020_std.parquet"))
message("  Saved: data/fin/source_2020_std.parquet")

# =============================================================================
# SUMMARY
# =============================================================================
message("\n=== Summary ===")
message("source_2005_std.parquet: ", nrow(std_2005), "rows")
message("source_2010_std.parquet: ", nrow(std_2010), "rows")
message("source_2015_std.parquet: ", nrow(std_2015), "rows")
message("source_2020_std.parquet: ", nrow(std_2020), "rows")
message("=== Standardization Complete ===")
