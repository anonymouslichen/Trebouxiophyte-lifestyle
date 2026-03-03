#!/usr/bin/env python3
"""
03_train.py
===========
Train a Random Forest classifier on hand-labeled metadata, then predict
lifestyle labels (free-living / symbiotic / ambiguous) for all unlabeled
records.

Outputs:
  - Confusion matrix PNG           -> results/figures/confusion_matrix.png
  - Classified unlabeled records   -> results/data/classified_metadata.csv

Usage:
    python scripts/03_train.py
    python scripts/03_train.py --labeled results/data/labeled_data.csv \
                                --unlabeled results/data/cleaned_metadata.csv
"""

import argparse
import logging
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import yaml
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import GridSearchCV, train_test_split

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

LABEL_ORDER = ["ambiguous", "free-living", "symbiotic"]
TEXT_COLS = ["Strain", "Isolation_source", "Host", "Title"]


def load_config(path: str) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def build_genus_pattern(config: dict) -> re.Pattern:
    """Build a compiled regex that matches any genus name in the config."""
    genera = [g.lower() for g in config["taxa"]]
    pattern = r"\b(" + "|".join(re.escape(g) for g in genera) + r")\b"
    return re.compile(pattern)


def clean_text(text: str, genus_re: re.Pattern) -> str:
    """Lowercase, strip numbers/punctuation/genus names."""
    text = text.lower()
    text = re.sub(r"\d+", "", text)
    text = re.sub(r"[^\w\s]", "", text)
    text = genus_re.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def combine_text(df: pd.DataFrame) -> pd.Series:
    """Concatenate the relevant text columns into one string per row."""
    return df[TEXT_COLS].fillna("").agg(" ".join, axis=1)


def train_and_evaluate(X_train, X_val, y_train, y_val):
    """Grid-search a Random Forest and print evaluation metrics."""
    param_grid = {
        "n_estimators": [100, 200, 500],
        "max_depth": [10, 20, 30, None],
        "min_samples_split": [2, 5, 10],
        "min_samples_leaf": [1, 2, 4],
        "class_weight": ["balanced"],
    }

    gs = GridSearchCV(
        estimator=RandomForestClassifier(random_state=42),
        param_grid=param_grid,
        cv=5,
        verbose=1,
        n_jobs=-1,
    )
    gs.fit(X_train, y_train)

    logger.info("Best parameters: %s", gs.best_params_)
    best_rf = gs.best_estimator_

    y_pred = best_rf.predict(X_val)
    logger.info("Validation accuracy: %.4f", accuracy_score(y_val, y_pred))
    print(classification_report(y_val, y_pred, labels=LABEL_ORDER))

    return best_rf, y_val, y_pred


def save_confusion_matrix(y_true, y_pred, path: str) -> None:
    """Plot and save a confusion matrix heatmap."""
    cm = confusion_matrix(y_true, y_pred, labels=LABEL_ORDER)
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues",
        xticklabels=LABEL_ORDER, yticklabels=LABEL_ORDER, ax=ax,
    )
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title("Confusion Matrix")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info("Confusion matrix saved to %s", path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/taxa.yml")
    parser.add_argument("--labeled", default="results/data/labeled_data.csv")
    parser.add_argument("--unlabeled", default="results/data/cleaned_metadata.csv")
    parser.add_argument("--out-predictions", default="results/data/classified_metadata.csv")
    parser.add_argument("--out-figure", default="results/figures/confusion_matrix.png")
    args = parser.parse_args()

    cfg = load_config(args.config)
    genus_re = build_genus_pattern(cfg)

    # --- Labeled data ---
    labeled = pd.read_csv(args.labeled)
    labeled["cleaned_text"] = combine_text(labeled).apply(
        lambda t: clean_text(t, genus_re)
    )

    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(labeled["cleaned_text"])
    y = labeled["Label"]

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    best_rf, y_val, y_pred = train_and_evaluate(X_train, X_val, y_train, y_val)

    Path(args.out_figure).parent.mkdir(parents=True, exist_ok=True)
    save_confusion_matrix(y_val, y_pred, args.out_figure)

    # --- Unlabeled data ---
    unlabeled = pd.read_csv(args.unlabeled)
    unlabeled["cleaned_text"] = combine_text(unlabeled).apply(
        lambda t: clean_text(t, genus_re)
    )
    X_unlabeled = vectorizer.transform(unlabeled["cleaned_text"])
    unlabeled["Predicted_Label"] = best_rf.predict(X_unlabeled)

    Path(args.out_predictions).parent.mkdir(parents=True, exist_ok=True)
    unlabeled.to_csv(args.out_predictions, index=False)
    logger.info("Saved %d classified rows to %s", len(unlabeled), args.out_predictions)


if __name__ == "__main__":
    main()
