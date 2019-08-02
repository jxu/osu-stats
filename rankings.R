library(tidyverse)
library(jsonlite)
library(plyr)

# Read from JSON and remove duplicate rows
rankings <- unique(fromJSON("rankings.json"))

# Convert values to correct data types
rankings <- colwise(parse_guess)(rankings)

write_csv(rankings, "rankings.csv")

# Basic analysis
length(unique(rankings$beatmap_id))  # ~13000 unique std maps

# Players with less than 100 top plays
rankings %>% 
  group_by(user_id) %>%
  dplyr::summarize(n = n()) %>%
  filter(n < 100)
