source("scripts/election_utils.R")

best_gp <- function(name, candidates, threshold = 0.20) {
  distance <- stringdist::stringdist(name, candidates$gp_name_std, method = "jw")
  if (!length(distance) || all(is.na(distance))) {
    return(NULL)
  }
  best <- min(distance, na.rm = TRUE)
  positions <- which(distance == best)
  if (best > threshold || length(positions) != 1L) {
    return(NULL)
  }
  row <- candidates[positions, ]
  a <- gsub("[^0-9]", "", stringi::stri_trans_general(name, "Any-Latin; Latin-ASCII"))
  b <- gsub("[^0-9]", "", stringi::stri_trans_general(row$gp_name_std, "Any-Latin; Latin-ASCII"))
  if (nzchar(a) && nzchar(b) && a != b) {
    return(NULL)
  }
  row$match_distance <- best
  row
}

build_geographic_bridge <- function(panel, directory, blocks) {
  urban <- paste(c(
    "NAGAR PALIKA", "NAGAR PANCHAYAT", "MUNICIPAL", "NAGARPALIKA",
    "NAGARPANCHAYAT", "\\bWARD\\s*NO\\b", "\\bWARD\\s*[0-9]+\\b", "NAGAR PARISHAD"
  ), collapse = "|")
  election <- panel |>
    select(match_key, district_std_2010, samiti_std_2010, gp_std_2010) |>
    filter(!grepl(urban, toupper(gp_std_2010), ignore.case = TRUE))
  rows <- election |>
    mutate(district = tolower(district_std_2010), samiti = tolower(samiti_std_2010)) |>
    left_join(blocks |> transmute(
      district = tolower(elex_district),
      samiti = tolower(elex_samiti), lgd_block_code, lgd_block_name
    ), by = c("district", "samiti"), relationship = "many-to-one") |>
    mutate(elex_gp_std = normalize_string(gp_std_2010), key = paste(lgd_block_code, elex_gp_std)) |>
    filter(!is.na(lgd_block_code), !is.na(gp_std_2010))
  reference <- directory |>
    mutate(gp_name_std = normalize_string(gp_name), key = paste(block_code, gp_name_std))
  exact <- rows |> inner_join(reference, by = "key", relationship = "many-to-many")
  unmatched <- rows |> anti_join(exact, by = c("match_key", "gp_std_2010"))
  fuzzy <- list()
  for (block in unique(unmatched$lgd_block_code)) {
    queries <- unmatched |> filter(lgd_block_code == block)
    candidates <- reference |> filter(block_code == block)
    for (i in seq_len(nrow(queries))) {
      hit <- best_gp(queries$elex_gp_std[i], candidates)
      if (!is.null(hit)) {
        fuzzy[[length(fuzzy) + 1L]] <- tibble(
          match_key = queries$match_key[i], gp_std_2010 = queries$gp_std_2010[i],
          lgd_gp_code = hit$gp_code, lgd_gp_name = hit$gp_name,
          lgd_block_code = queries$lgd_block_code[i], lgd_block_name = queries$lgd_block_name[i],
          lgd_district = hit$zila_name, match_type = "fuzzy",
          match_distance = hit$match_distance, match_confidence = "unique"
        )
      }
    }
  }
  matches <- bind_rows(exact |> transmute(
    match_key, gp_std_2010,
    lgd_gp_code = gp_code, lgd_gp_name = gp_name,
    lgd_block_code, lgd_block_name = block_name, lgd_district = zila_name,
    match_type = "exact", match_distance = 0, match_confidence = "unique"
  ), bind_rows(fuzzy))
  if (anyDuplicated(matches[c("match_key", "gp_std_2010")])) {
    matches <- matches |>
      group_by(match_key, gp_std_2010) |>
      slice_min(match_distance, n = 1, with_ties = TRUE) |>
      filter(n() == 1L) |>
      ungroup()
  }
  if (anyDuplicated(matches$lgd_gp_code)) {
    matches <- matches |>
      left_join(rows |> distinct(match_key, district_std_2010, samiti_std_2010),
        by = "match_key", relationship = "many-to-one"
      ) |>
      group_by(district_std_2010, samiti_std_2010, lgd_gp_code) |>
      slice_min(match_distance, n = 1, with_ties = TRUE) |>
      filter(n() == 1L) |>
      ungroup() |>
      select(-district_std_2010, -samiti_std_2010)
  }
  election |>
    left_join(matches, by = c("match_key", "gp_std_2010"), relationship = "one-to-one") |>
    filter(!is.na(lgd_gp_code)) |>
    distinct(match_key, .keep_all = TRUE) |>
    select(
      match_key, lgd_gp_code, lgd_gp_name, lgd_block_code, lgd_block_name,
      lgd_district, match_type, match_distance, match_confidence
    )
}

if (sys.nframe() == 0L) {
  directory <- read_csv("data/source/geography/lgd_raj_block_gp.csv", show_col_types = FALSE)
  blocks <- read_csv("data/source/geography/raj_samiti_xwalk.csv", show_col_types = FALSE)
  panel <- read_parquet(file.path(product_dir, "raj_05_10.parquet"))
  save_product(build_geographic_bridge(panel, directory, blocks), "gp_lgd_crosswalk.parquet")
}
