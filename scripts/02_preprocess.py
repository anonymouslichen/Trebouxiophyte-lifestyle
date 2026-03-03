#!/usr/bin/env python3
"""
02_preprocess.py
================
Clean and deduplicate the raw metadata CSV produced by 01_extract.py.

Steps:
  - Lowercase and remove punctuation/stopwords from text columns
  - Remove culture-collection strains (SAG, UTEX)
  - Strip prefixes from TaxID and boilerplate from Title
  - Deduplicate on BioSample accession

Usage:
    python scripts/02_preprocess.py
    python scripts/02_preprocess.py --input results/data/species_metadata.csv \
                                     --output results/data/cleaned_metadata.csv
"""

import argparse
import logging
from pathlib import Path

import nltk
import pandas as pd

nltk.download("stopwords", quiet=True)
from nltk.corpus import stopwords

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

STOP_WORDS = set(stopwords.words("english"))

# Columns that should NOT be cleaned (identifiers)
PRESERVE_COLUMNS = {"Accession"}


def clean_text(text: str) -> str:
    """Lowercase, strip punctuation, and remove English stopwords."""
    if pd.isna(text):
        return text
    if not isinstance(text, str):
        return text
    import re

    text = text.lower()
    text = re.sub(r"[^\w\s\d]", "", text)
    text = " ".join(w for w in text.split() if w not in STOP_WORDS)
    return text


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all cleaning and deduplication steps."""
    logger.info("Starting with %d rows", len(df))

    # Clean text columns
    cols_to_clean = [c for c in df.columns if c not in PRESERVE_COLUMNS]
    for col in cols_to_clean:
        df[col] = df[col].apply(clean_text)

    # Normalise BioSample
    df["BioSample"] = df["BioSample"].astype(str).str.strip().str.lower()

    # Remove culture-collection strains (SAG / UTEX)
    mask = df["Strain"].str.contains("sag|utex", case=False, na=False)
    logger.info("Removing %d culture-collection rows (SAG/UTEX)", mask.sum())
    df = df[~mask]

    # Strip prefixes / boilerplate
    df["TaxID"] = df["TaxID"].str.replace("taxon", "", regex=False)
    df["Title"] = df["Title"].str.replace("direct submission", "", regex=False)

    # Deduplicate on BioSample (keep first), preserving rows with no BioSample
    has_biosample = df["BioSample"] != "nan"
    deduped = df[has_biosample].drop_duplicates(subset="BioSample", keep="first")
    no_biosample = df[~has_biosample]
    df = pd.concat([deduped, no_biosample], ignore_index=True)

    logger.info("Finished with %d rows after deduplication", len(df))
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="results/data/species_metadata.csv",
        help="Raw metadata CSV (default: results/data/species_metadata.csv)",
    )
    parser.add_argument(
        "--output",
        default="results/data/cleaned_metadata.csv",
        help="Cleaned output CSV (default: results/data/cleaned_metadata.csv)",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    df = preprocess(df)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    logger.info("Saved cleaned data to %s", args.output)


if __name__ == "__main__":
    main()
