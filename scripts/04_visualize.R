#!/usr/bin/env Rscript
# ============================================================
# 04_visualize.R
# ============================================================
# Generate two figures from the classified metadata:
#   1. Stacked bar chart of symbiotic vs free-living proportions per genus
#   2. Scatter plot of symbiotic proportion vs 18S substitution rate
#
# Usage:
#   Rscript scripts/04_visualize.R
#
# Expected inputs (in results/data/):
#   - combined_labeled_metadata.csv   (output of 03_train.py merged with labels)
#   - 18s_branch_lengths.csv          (from phylogenetic analysis)
#
# Outputs (in results/figures/):
#   - genus_lifestyle_proportions.png
#   - proportion_vs_substitution_rate.png
# ============================================================

library(dplyr)
library(tidyr)
library(stringr)
library(ggplot2)

# ------ paths --------------------------------------------------------
data_dir   <- "results/data"
fig_dir    <- "results/figures"
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

# ------ 1. Lifestyle proportions by genus ----------------------------
data <- read.csv(file.path(data_dir, "combined_labeled_metadata.csv"))

# Drop ambiguous records
filtered <- data %>%
  filter(Label != "ambiguous")

# Parse genus from the Organism field (handle leading "uncultured")
separated <- filtered %>%
  mutate(
    Genus = if_else(
      grepl("uncultured", Organism),
      word(Organism, 2),
      word(Organism, 1)
    ),
    Species = if_else(
      grepl("uncultured", Organism),
      word(Organism, 3, -1),
      word(Organism, 2, -1)
    )
  ) %>%
  filter(!Genus %in% c("soil", "eukaryota"))

# Summarise proportions
proportions <- separated %>%
  group_by(Genus) %>%
  summarise(
    Free_living = sum(Label == "free-living"),
    Symbiotic   = sum(Label == "symbiotic"),
    Total       = n(),
    .groups     = "drop"
  ) %>%
  mutate(
    Free_living_prop = Free_living / Total,
    Symbiotic_prop   = Symbiotic / Total
  )

# Pivot to long format for ggplot
prop_long <- proportions %>%
  select(Genus, Free_living_prop, Symbiotic_prop) %>%
  pivot_longer(
    cols      = c(Free_living_prop, Symbiotic_prop),
    names_to  = "Lifestyle",
    values_to = "Proportion"
  ) %>%
  mutate(Lifestyle = recode(Lifestyle,
    Free_living_prop = "Free-living",
    Symbiotic_prop   = "Symbiotic"
  ))

# Order genera by increasing symbiotic proportion
genus_order <- proportions %>%
  arrange(Symbiotic_prop) %>%
  pull(Genus)

p1 <- ggplot(
    prop_long,
    aes(x = factor(Genus, levels = genus_order), y = Proportion, fill = Lifestyle)
  ) +
  geom_bar(stat = "identity", position = "fill") +
  geom_text(
    data = filter(prop_long, Lifestyle == "Symbiotic"),
    aes(label = round(Proportion, 3)),
    position = position_fill(vjust = 0.45),
    color = "white", size = 4
  ) +
  scale_y_continuous(labels = scales::percent) +
  labs(
    title = "Free-living vs. Symbiotic Proportions across Genera",
    x     = "Genus",
    y     = "Proportion",
    fill  = "Lifestyle"
  ) +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))

ggsave(
  file.path(fig_dir, "genus_lifestyle_proportions.png"),
  plot = p1, width = 8, height = 6
)

# ------ 2. Proportion vs 18S substitution rate -----------------------
rRNA <- read.csv(file.path(data_dir, "18s_branch_lengths.csv"))

# Map leaf accessions to taxon names
accession_map <- c(
  "EU105209.1" = "xylochloris irregularis",
  "EU123942.1" = "trebouxia aggregata",
  "JN573893.1" = "myrmecia sp.",
  "JX127171.1" = "trebouxia sp. uncultured",
  "KM020046.1" = "lobosphaera incisa",
  "KM020112.1" = "trochisciopsis tetraspora",
  "KP318692.1" = "asterochloris erici",
  "KR952316.1" = "vulcanochloris guanchorium",
  "LC366918.1" = "myrmecia bisecta",
  "LC639356.1" = "parietochloris sp.",
  "MW866482.1" = "thorsmoerkia curvula",
  "KJ466354.1" = "chlorella vulgaris",
  "HG972969.1" = "elliptochloris bilobata",
  "AJ581913.1" = "botryococcus braunii",
  "HG973001.1" = "coccomyxa viridis",
  "FN597599.1" = "coccomyxa peltigerae"
)

rRNA <- rRNA %>%
  mutate(
    taxa  = accession_map[Leaf],
    Genus = str_extract(taxa, "^[^ ]+")
  )

combined <- prop_long %>%
  filter(Lifestyle == "Symbiotic") %>%
  right_join(rRNA, by = "Genus")

p2 <- ggplot(combined, aes(x = Proportion, y = Length)) +
  geom_point(size = 2) +
  geom_text(aes(label = Genus), vjust = -0.5, hjust = 0.5, size = 3) +
  geom_smooth(method = "lm", se = FALSE, color = "blue") +
  labs(
    title = "Symbiotic Proportion vs. 18S Substitution Rate",
    x     = "Proportion Symbiotic",
    y     = "Substitution Rate"
  ) +
  theme_minimal()

ggsave(
  file.path(fig_dir, "proportion_vs_substitution_rate.png"),
  plot = p2, width = 8, height = 6
)

message("Figures saved to ", fig_dir)
