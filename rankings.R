library(jsonlite)
library(plyr)
# Read from JSON
rankings <- unique(do.call("rbind", fromJSON("rankings.json")))

# Convert values to correct data types
rankings.intvar <-!(names(rankings) %in% c("date", "rank", "pp"))
rankings[ , rankings.intvar] <- sapply(rankings[ , rankings.intvar], as.integer)
rankings$pp <- as.numeric(rankings$pp)
# convert datetime POSIXct 

write.csv(rankings, "rankings.csv")
