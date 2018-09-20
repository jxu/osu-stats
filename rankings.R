library(jsonlite)
rankings <- do.call("rbind", fromJSON("rankings.json"))
ddply(rankings, .(user_id), count)