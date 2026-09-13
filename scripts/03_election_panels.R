source("scripts/election_utils.R")

years <- c(2005, 2010, 2015, 2020)
sources <- setNames(lapply(years, read_election), years)
save_product(bind_rows(sources), "source_records.parquet")
sources <- lapply(sources, function(d) filter(d, !is.na(gp_std), gp_std != ""))

winners <- read_parquet(file.path(product_dir, "winners_2020_events.parquet")) |>
  filter(winner_key_unique, gp_event_unique) |>
  transmute(
    match_key,
    winner_sex_from_cand = female_winner_2020,
    candidate_reservation_raw, candidate_reservation_unique,
    candidate_reserved = case_when(
      is.na(candidate_reservation_raw) ~ NA_integer_,
      grepl("WOMAN|W$", toupper(candidate_reservation_raw)) ~ 1L,
      TRUE ~ 0L
    ),
    candidate_caste = case_when(
      grepl("^GEN", toupper(candidate_reservation_raw)) ~ "GEN",
      grepl("^OBC", toupper(candidate_reservation_raw)) ~ "OBC",
      grepl("^SC", toupper(candidate_reservation_raw)) ~ "SC",
      grepl("^ST", toupper(candidate_reservation_raw)) ~ "ST"
    )
  ) |>
  left_join(
    sources[["2020"]] |>
      group_by(match_key) |>
      filter(n() == 1) |>
      ungroup() |>
      select(match_key, female_reserved, caste_category),
    by = "match_key", relationship = "one-to-one"
  ) |>
  mutate(
    reservation_gender_conflict = candidate_reserved != female_reserved,
    reservation_caste_conflict = candidate_caste != caste_category
  ) |>
  select(-female_reserved, -caste_category)

prepare_source <- function(year) {
  sources[[as.character(year)]] |>
    select(
      match_key, district_std, samiti_std, gp_std, female_reserved,
      caste_category, winner_female, winner_name, source_id
    ) |>
    rename_with(~ paste0(.x, "_", year), -match_key)
}

remove_collisions <- function(data, year) {
  triplet <- do.call(paste, c(lapply(
    data[paste0(c("district_std_", "samiti_std_", "gp_std_"), year)],
    normalize_string
  ), sep = "_"))
  ambiguous <- tibble(triplet, match_key = data$match_key) |>
    filter(!is.na(match_key)) |>
    distinct() |>
    count(triplet) |>
    filter(n > 1)
  data[!triplet %in% ambiguous$triplet, ]
}

build_panel <- function(waves) {
  data <- Reduce(
    function(x, y) inner_join(x, y, by = "match_key", relationship = "many-to-many"),
    lapply(waves, prepare_source)
  ) |>
    group_by(match_key) |>
    filter(n() == 1) |>
    ungroup()
  last <- tail(waves, 1)
  if (last == 2020) {
    data <- data |>
      mutate(match_key_2020 = make_match_key(district_std_2020, samiti_std_2020, gp_std_2020)) |>
      left_join(winners, by = c("match_key_2020" = "match_key"), relationship = "many-to-one")
  }
  for (y in waves) data[[paste0("treat_", y)]] <- data[[paste0("female_reserved_", y)]]
  if (length(waves) == 2) data$case <- paste0(data[[paste0("treat_", waves[1])]], data[[paste0("treat_", last)]])
  for (y in waves) {
    data[[paste0("female_winner_", y)]] <- if (y == 2020) {
      coalesce(data$winner_sex_from_cand, NA_integer_)
    } else {
      data[[paste0("winner_female_", y)]]
    }
  }
  if (length(waves) == 4) {
    data <- data |> mutate(
      never_treated = as.integer(treat_2005 == 0 & treat_2010 == 0 & treat_2015 == 0),
      always_treated = as.integer(treat_2005 == 1 & treat_2010 == 1 & treat_2015 == 1),
      count_treated = treat_2005 + treat_2010 + treat_2015
    )
  }
  for (y in if (length(waves) == 4) c(2020, 2015, 2010) else last) {
    data[[paste0("dist_samiti_", y)]] <- paste0(
      tolower(data[[paste0("district_std_", y)]]),
      "_", tolower(data[[paste0("samiti_std_", y)]])
    )
  }
  for (y in waves) {
    for (caste in c("obc", "sc", "st")) {
      data[[paste0(caste, "_", y)]] <- as.integer(data[[paste0("caste_category_", y)]] == toupper(caste))
    }
  }
  if (length(waves) == 2) data <- remove_collisions(data, last)
  data |> select(-starts_with("source_id_"), starts_with("source_id_"))
}

for (waves in list(c(2005, 2010), c(2010, 2015), c(2015, 2020), years)) {
  save_product(build_panel(waves), sprintf("raj_%02d_%02d.parquet", waves[1] %% 100, tail(waves, 1) %% 100))
}
