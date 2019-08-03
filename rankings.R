library(tidyverse)
library(jsonlite)

# Read from JSON and remove duplicate rows
ranking_filenames <- c(rankings0 = "rankings0.json", 
                       rankings1 = "rankings1.json", 
                       rankings2 = "rankings2.json", 
                       rankings3 = "rankings3.json")

rankings <- ranking_filenames %>% lapply(fromJSON)
rankings <- rankings %>% lapply(unique)

# Convert values to correct data types
rankings <- rankings %>% lapply(plyr::colwise(parse_guess))

write_csv(rankings$rankings0, "rankings0.csv")
write_csv(rankings$rankings1, "rankings1.csv")
write_csv(rankings$rankings2, "rankings2.csv")
write_csv(rankings$rankings3, "rankings3.csv")

# Basic analysis
rankings0 <- rankings$rankings0
length(unique(rankings0$beatmap_id))  # ~13000 unique std maps

# Players with less than 100 top plays
rankings0 %>% 
  group_by(user_id) %>%
  summarize(n = n()) %>%
  filter(n < 100)
