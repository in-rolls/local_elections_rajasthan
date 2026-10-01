suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(readr)
})

product_dir <- Sys.getenv("ELECTION_PRODUCTS_DIR", "data/fin/elections")
dir.create(product_dir, recursive = TRUE, showWarnings = FALSE)
save_product <- function(data, name) {
  write_parquet(data, file.path(product_dir, name))
}

normalize_string <- function(x) {
  x <- stringi::stri_trans_general(x, "Latin-ASCII")
  x <- stringi::stri_trans_tolower(x)
  x <- trimws(gsub("\\s+", " ", x))
  stringi::stri_replace_all_regex(x, "\\p{P}", "")
}

make_match_key <- function(district, block, gp) {
  paste(tolower(trimws(district)), tolower(trimws(block)),
    tolower(trimws(gp)),
    sep = "_"
  )
}

districts <- read_csv("data/source/geography/raj_district_xwalk.csv",
  show_col_types = FALSE
) |>
  transmute(district_raw = elex_district_raw, district_std = toupper(shrug_district))
samitis <- read_csv("data/source/geography/raj_samiti_std.csv", show_col_types = FALSE)

add_geography <- function(data) {
  data |>
    left_join(districts, by = "district_raw", relationship = "many-to-one") |>
    mutate(district_std = coalesce(district_std, district_raw)) |>
    left_join(samitis, by = c("district_std", "samiti_raw"), relationship = "many-to-one") |>
    mutate(
      samiti_std = coalesce(samiti_std, samiti_raw),
      match_key = make_match_key(district_std, samiti_std, gp_std)
    )
}

read_election <- function(year) {
  read_parquet(sprintf("data/fin/source_%s_std.parquet", year)) |>
    mutate(source_row = row_number(), source_id = paste0("source_", year, ":", source_row)) |>
    add_geography()
}
