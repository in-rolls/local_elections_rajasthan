published <- "data/fin/elections"
rebuilt <- tempfile("rajasthan-elections-")
Sys.setenv(ELECTION_PRODUCTS_DIR = rebuilt)
source("scripts/02_candidate_events.R")
source("scripts/03_election_panels.R")
source("scripts/04_geographic_bridge.R")
directory <- read_csv("data/source/geography/lgd_raj_block_gp.csv", show_col_types = FALSE)
blocks <- read_csv("data/source/geography/raj_samiti_xwalk.csv", show_col_types = FALSE)
save_product(build_geographic_bridge(
  read_parquet(file.path(product_dir, "raj_05_10.parquet")), directory, blocks
), "gp_lgd_crosswalk.parquet")

files <- list.files(published, pattern = "[.]parquet$")
stopifnot(length(files) == 8L)
for (file in files) {
  expected <- read_parquet(file.path(published, file))
  actual <- read_parquet(file.path(rebuilt, file))
  stopifnot(identical(actual, expected))
}

records <- read_parquet(file.path(rebuilt, "source_records.parquet"))
stopifnot(!anyDuplicated(records$source_id))
for (year in years) {
  original <- read_parquet(sprintf("data/fin/source_%s_std.parquet", year))
  record <- records |> filter(.data$year == .env$year)
  stopifnot(identical(original, record[names(original)]))
}
for (file in grep("^raj_", files, value = TRUE)) {
  panel <- read_parquet(file.path(rebuilt, file))
  stopifnot(!anyDuplicated(panel$match_key))
  for (column in grep("^source_id_", names(panel), value = TRUE)) {
    stopifnot(all(panel[[column]] %in% records$source_id))
  }
}

# Names containing different numeric GP identifiers cannot be fuzzy linked.
reference <- tibble(gp_name_std = c("gram 12", "gram 13"), gp_code = c(1, 2))
stopifnot(is.null(best_gp("gram 11", reference)))
stopifnot(is.null(best_gp("gram 12", bind_rows(reference[1, ], reference[1, ]))))
stopifnot(best_gp("gram 12", reference)$gp_code == 1)
stopifnot(is.null(best_gp("zzzz", reference)))
stopifnot(normalize_string("Gram-12") != normalize_string("Gram-13"))

candidate <- read_parquet(file.path(rebuilt, "candidates_2020_events.parquet"))
winner <- read_parquet(file.path(rebuilt, "winners_2020_events.parquet"))
stopifnot(!anyDuplicated(candidate$source_id), !anyDuplicated(winner$source_id))
stopifnot(!any(c("mobile_no", "email_address") %in% union(names(candidate), names(winner))))

# A supplied study baseline verifies the migration without making the study a build dependency.
baseline <- Sys.getenv("QUOTA_RAJ_BASELINE")
if (nzchar(baseline)) {
  for (file in setdiff(files, c("source_records.parquet", "gp_lgd_crosswalk.parquet"))) {
    before <- read_parquet(file.path(baseline, file))
    after <- read_parquet(file.path(rebuilt, file))
    stopifnot(identical(before, after[names(before)]))
  }
  bridge <- read_parquet(file.path(rebuilt, "gp_lgd_crosswalk.parquet"))
  for (file in grep("^raj_", files, value = TRUE)) {
    baseline_file <- paste0("shrug_gp_", sub(".parquet", "_block.parquet", file, fixed = TRUE))
    before <- read_parquet(file.path(baseline, baseline_file))
    panel <- read_parquet(file.path(rebuilt, file))
    after <- left_join(panel, bridge, by = "match_key", relationship = "many-to-one")
    columns <- intersect(names(before), names(after))
    stopifnot(identical(before[columns], after[columns]))
  }
}
unlink(rebuilt, recursive = TRUE)
message("Eight election products rebuild exactly; source identities and linkage rules pass.")
