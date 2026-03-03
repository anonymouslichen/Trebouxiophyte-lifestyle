# Trebouxiophyte Lifestyle Classification

A pipeline for classifying green algal genera (Trebouxiophyceae) as **free-living** or **symbiotic** using NCBI GenBank metadata and a Random Forest text classifier.

## Overview

Many trebouxiophyte algae form symbioses with fungi (lichens), but lifestyle metadata is rarely standardized in public databases. This project:

1. **Extracts** GenBank metadata for 12 trebouxiophyte genera from NCBI Entrez
2. **Preprocesses** the text fields (strain, isolation source, host, publication title)
3. **Trains** a Random Forest classifier (TF-IDF features) on a hand-labeled subset to predict lifestyle labels
4. **Visualizes** the proportion of symbiotic vs. free-living records across genera and compares to 18S substitution rates

## Repository Structure

```
.
├── scripts/
│   ├── 01_extract.py              # Fetch GenBank records from NCBI Entrez
│   ├── 02_preprocess.py           # Clean and deduplicate metadata
│   ├── 03_train.py                # Train RF classifier, predict unlabeled data
│   └── 04_visualize.R             # Plot lifestyle proportions and substitution rates
├── config/
│   └── taxa.yml                   # Taxon IDs and genus-to-accession mappings
├── results/
│   ├── figures/                   # Output plots (.png)
│   └── data/                      # Output CSVs (not tracked by git)
├── docs/
│   └── labeling_guide.md          # Criteria used for manual labeling
├── environment.yml                # Conda environment specification
├── .gitignore
├── LICENSE
└── README.md
```

## Requirements

### Python (>= 3.9)

- biopython
- pandas
- scikit-learn
- matplotlib, seaborn
- nltk
- pyyaml

### R (>= 4.1)

- dplyr, tidyr, stringr
- ggplot2, scales

A conda environment file is provided (see Setup below).

## Setup

```bash
# Clone the repository
git clone https://github.com/<your-username>/trebouxiophyte-lifestyle.git
cd trebouxiophyte-lifestyle

# Create and activate the conda environment
conda env create -f environment.yml
conda activate trebouxiophyte-lifestyle
```

## Usage

Run the scripts in order. Each step reads from the previous step output.

```bash
# 1. Download GenBank metadata from NCBI
python scripts/01_extract.py

# 2. Clean and deduplicate
python scripts/02_preprocess.py

# 3. Train the classifier and predict unlabeled records
python scripts/03_train.py

# 4. Generate figures (in R)
Rscript scripts/04_visualize.R
```

> **Note:** Step 1 makes many requests to the NCBI Entrez API. Set your email in
> `config/taxa.yml` before running. Expect the download to take several minutes
> depending on record counts.

## Data

Raw and intermediate CSVs are written to `results/data/` and are **not tracked by git**.
The hand-labeled training set (`labeled_data.csv`) should be placed in `results/data/`
before running step 3.

| Step | Input | Source |
|------|-------|--------|
| 01 | Taxon IDs | `config/taxa.yml` |
| 02 | `species_metadata.csv` | Step 01 output |
| 03 | `cleaned_metadata.csv` + `labeled_data.csv` | Step 02 + manual labels |
| 04 | `combined_labeled_metadata.csv` + `18s_branch_lengths.csv` | Step 03 + phylogenetic analysis |

## Methods

Text from the **Strain**, **Isolation_source**, **Host**, and **Title** fields is
concatenated, lowercased, and stripped of stopwords and genus names (to prevent data
leakage). TF-IDF vectors are used as features for a Random Forest classifier tuned
via 5-fold cross-validated grid search. The best model is then applied to all
unlabeled records.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
