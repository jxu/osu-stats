# Basic data visualization of beatmap info provided by osu! API. https://github.com/ppy/osu-api/wiki
# Only uses ranked/loved/qualified maps. Graphs focusing on standard mode. 
# (A few maps, due to ranked/loved irregularities, are actually in graveyard but included in the API
# query anyway. Ex. https://osu.ppy.sh/b/766190&m=2 with 1 loved CtB diff. )

library(ggplot2)
library(grid)
library(gridExtra)
library(plyr)


# Import data from file, ignoring special chars
t <- read.table(file = "data.tsv", sep='\t', header=TRUE, quote='', comment.char='',
                fileEncoding="UTF-8", encoding="UTF-8")
# Convert MySQL datetimes to R datetimes. As far as the new site goes, this appears to be UTC-4, but
# this may be a local thing. Probably broken. 
t$approved_date <- as.POSIXct(t$approved_date, tz="Canada/Atlantic")
t$last_update <- as.POSIXct(t$last_update, tz="Canada/Atlantic")


# Create labels and data frames for each gamemode
t$mode <- factor(t$mode, labels=c("Standard", "Taiko", "CtB", "Mania"))
std <- t[t$mode == "Standard",]
taiko <- t[t$mode == "Taiko",]
ctb <- t[t$mode == "CtB",]
mania <- t[t$mode == "Mania",]


# Various plot parameters for convenience
# These will usually leave a few outlier maps out
diff_x_scale <- scale_x_continuous(limits=c(0,10), breaks=seq(0,10,0.5))
diff_hist <- geom_histogram(binwidth=0.05)
length_x_scale <- scale_x_continuous(limits=c(0,600), breaks=seq(0,600,30))
length_hist <- geom_histogram(binwidth=1)
AR_y_scale <- scale_y_continuous(breaks=seq(0,10))
SR_y_scale <- scale_y_continuous(limits=c(0,10), breaks=seq(0,10,1))
approved_x_scale <- scale_x_datetime(date_breaks="1 year", date_labels="%Y")

legend_title_fill <- labs(fill="Mode")
legend_title_color <- labs(color="Mode")

# Center titles
theme_update(plot.title = element_text(hjust = 0.5))


# Histogram of star rating (all modes)
ggplot(t, aes(difficultyrating, fill=as.factor(mode))) + 
  ggtitle("Total Star Rating (All Modes)") + legend_title_fill +
  diff_x_scale + diff_hist

# Frequency polygon of SR (all modes)
ggplot(t, aes(difficultyrating, color=as.factor(mode))) + 
  ggtitle("Star Rating (All Modes)") + legend_title_color +
  diff_x_scale + geom_freqpoly(binwidth=0.05) 

# Histograms of SR (all modes)
diffplots0 <- ggplot(std  , aes(difficultyrating)) + diff_x_scale + diff_hist + ggtitle("Standard")
diffplots1 <- ggplot(taiko, aes(difficultyrating)) + diff_x_scale + diff_hist + ggtitle("Taiko")
diffplots2 <- ggplot(ctb  , aes(difficultyrating)) + diff_x_scale + diff_hist + ggtitle("CtB")
diffplots3 <- ggplot(mania, aes(difficultyrating)) + diff_x_scale + diff_hist + ggtitle("Mania")

grid.arrange(diffplots0, diffplots1, diffplots2, diffplots3, 
             top=textGrob("Star Rating Distributions (All Modes)", gp=gpar(fontsize=16)))

# Histogram of total length (all modes)
ggplot(t, aes(total_length, fill=as.factor(mode))) + 
  ggtitle("Total Beatmap Length (All Modes)") + legend_title_fill +
  length_x_scale + length_hist

# Frequency polygon of total length (all modes)
ggplot(t, aes(total_length, color=as.factor(mode))) + 
  ggtitle("Beatmap Length (All Modes)") + legend_title_color +
  length_x_scale + geom_freqpoly(binwidth=1)

# Histograms of total length (all modes)
lengthplots0 <- ggplot(std  , aes(total_length)) + length_x_scale + length_hist + ggtitle("Standard")
lengthplots1 <- ggplot(taiko, aes(total_length)) + length_x_scale + length_hist + ggtitle("Taiko")
lengthplots2 <- ggplot(ctb  , aes(total_length)) + length_x_scale + length_hist + ggtitle("CtB")
lengthplots3 <- ggplot(mania, aes(total_length)) + length_x_scale + length_hist + ggtitle("Mania")

grid.arrange(lengthplots0, lengthplots1, lengthplots2, lengthplots3,
             top=textGrob("Beatmap Length Distributions (All Modes)", gp=gpar(fontsize=16)))

# Frequency polygons of playcount (all modes)
ggplot(t, aes(playcount, color=as.factor(mode))) + 
  ggtitle("Playcount (All Modes)") + legend_title_color +
  scale_x_continuous(limits=c(0,1000000)) + 
  geom_freqpoly(binwidth=5000)

# Histogram of date approved (all modes)
ggplot(t, aes(approved_date, fill=as.factor(mode))) + 
  ggtitle("Total Date Approved (All Modes)") + legend_title_fill +
  approved_x_scale + geom_histogram(binwidth=3600*24*30)

# Frequency polygon of date approved (all modes)
ggplot(t, aes(approved_date, color=as.factor(mode))) +
  ggtitle("Date Approved (All Modes)") + legend_title_color +
  approved_x_scale + geom_freqpoly(binwidth=3600*24*30)


# Most frequent artists, titles, sources, and creators
head(sort(table(t$artist), decreasing=TRUE), 10)
head(sort(table(t$title), decreasing=TRUE), 10)
head(sort(table(t$source), decreasing=TRUE), 10)
head(sort(table(t$creator), decreasing=TRUE), 10)

# Most favorited mapsets (mapset defined by creator, artist, and title)
mapsets <- t[!duplicated(t[c("creator","artist","title")]),]
most_fav <- head(arrange(mapsets, desc(favourite_count)), 20)
subset(most_fav, select=c("favourite_count","creator","title"))

# Most played maps
most_played <- head(arrange(t, desc(playcount)), 20)
subset(most_played, select=c("playcount","creator","title","version"))


# Scatterplot of AR vs BPM
ggplot(std, aes(bpm, diff_approach)) + 
  ggtitle("Approach Rate vs BPM") + 
  scale_x_continuous(limits=c(0,500)) + 
  AR_y_scale + 
  geom_point(alpha=0.1)

# Scatterplot of SR vs total length time
ggplot(std, aes(total_length, difficultyrating)) + 
  ggtitle("Star Rating vs Total Length") +
  length_x_scale + 
  SR_y_scale +
  geom_point(alpha=0.1)

# Scatterplot of max combo vs drain time
ggplot(std, aes(hit_length, max_combo)) + 
  ggtitle("Max Combo vs Drain Time") + 
  length_x_scale + 
  scale_y_continuous(limits=c(0,4000)) +
  geom_point(alpha=0.05)

# High linear correlation, as expected
summary(lm(max_combo ~ hit_length, data=std))

# Scatterplot of favorite count vs playcount
ggplot(std, aes(playcount, favourite_count)) + 
  ggtitle("Favorite Count vs Playcount") + 
  scale_x_continuous(limits=c(0,1000000)) +
  scale_y_continuous(limits=c(0,1000)) +
  geom_point(alpha=0.05)

# Scatterplot of playcount vs total length
ggplot(std, aes(total_length, playcount)) +
  ggtitle("Playcount vs Total Length") + 
  length_x_scale + 
  scale_y_continuous(limits=c(0,1000000)) +
  geom_point(alpha=0.1)

# Scatterplot of AR vs date approved
ggplot(std, aes(approved_date, diff_approach)) + 
  ggtitle("Approach Rate vs Date Approved") + 
  AR_y_scale + 
  approved_x_scale + 
  geom_point(alpha=0.05)

# Scatterplot of SR vs date approved
ggplot(std, aes(approved_date, difficultyrating)) +
  ggtitle("Star Rating vs Date Approved") +
  SR_y_scale + 
  approved_x_scale + 
  geom_point(alpha=0.1)
  
# Playcount by song time, categorized by spread icon
# https://osu.ppy.sh/help/wiki/Difficulties#star-rating Not sure about values between boundaries
spread.sr = c(0, 1.51, 2.26, 3.76, 5.26, 6.76)  
spread.names = c("Easy", "Normal", "Hard", "Insane", "Expert", "Expert+")
spread.colors = c("olivedrab3", "paleturquoise", "gold", "hotpink", "purple", "darkgray")

# Assign difficulty rating by spread ranges to spread names 
t$spread_name = spread.names[cut(t$difficultyrating, spread.sr, right=FALSE, labels=FALSE)]
std <- t[t$mode == "Standard",]  # update std 

hitlength.bins = seq(0, 360, 30)
par(mfrow=c(2,3), mar=c(4,4,4,1), cex.main=2)
for (i in 1:length(spread.names)) {
  std.spread = std[std$spread_name == spread.names[i], ]
  playcount.bin.sum = sapply(split(std.spread, cut(std.spread$hit_length, hitlength.bins)),
                             function(df) sum(df$playcount))

  barplot(playcount.bin.sum, space=0, width=30, xlab="Hit length (s)", ylab="Playcount Total", main=spread.names[i],
          col=spread.colors[i], axisnames=FALSE)
  axis(1, at=hitlength.bins)
}

# Same but 150+ hitlength and stacked bars
hitlength.bins.150 = seq(150, 360, 30)
playcount.bin.mat = matrix(ncol=length(hitlength.bins.150)-1, nrow=length(spread.names))
colnames(playcount.bin.mat) = head(hitlength.bins.150, -1)
rownames(playcount.bin.mat) = spread.names

for (i in 1:nrow(playcount.bin.mat)) {
  std.spread = std[std$spread_name == spread.names[i], ]
  playcount.bin.mat[i,] = sapply(split(std.spread, cut(std.spread$hit_length, hitlength.bins.150)),
                                 function(df) sum(df$playcount))
}

dev.off()  # Reset par 
barplot(playcount.bin.mat, space=0, width=30, col=spread.colors, xlab="Hitlength (s)", ylab="Total Playcount",
        legend.text=spread.names, axisnames=FALSE, main="Total Playcount by Hitlength and Difficulty")
axis(1, at=hitlength.bins.150-hitlength.bins.150[1], labels=hitlength.bins.150)
