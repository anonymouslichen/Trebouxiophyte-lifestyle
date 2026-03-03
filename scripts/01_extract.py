#!/usr/bin/env python3
"""
01_extract.py
=============
Fetch GenBank nucleotide records from NCBI Entrez for a set of
trebouxiophyte genera and write source-feature metadata to CSV.

Reads taxon IDs and Entrez settings from config/taxa.yml.

Usage:
    python scripts/01_extract.py
    python scripts/01_extract.py --config config/taxa.yml --output results/data/species_metadata.csv
"""

import argparse
import csv
import logging
import sys
import time
from pathlib import Path

import yaml
from Bio import Entrez, SeqIO

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Column order for the output CSV
FIELDNAMES = [
    "Accession",
    "BioSample",
    "TaxID",
    "Organism",
    "Strain",
    "Isolation_source",
    "Host",
    "Title",
    "Definition",
]


def load_config(path: str) -> dict:
    """Load YAML configuration file."""
    with open(path) as fh:
        return yaml.safe_load(fh)


def search_all_ids(
    taxid: str,
    batch_size: int = 500,
    max_retries: int = 3,
    retry_delay: int = 3,
) -> list[str]:
    """Return all nucleotide IDs for a given NCBI Taxonomy ID."""
    search_term = f"txid{taxid}[Organism]"
    all_ids: list[str] = []
    start = 0

    while True:
        for attempt in range(1, max_retries + 1):
            try:
                handle = Entrez.esearch(
                    db="nucleotide",
                    term=search_term,
                    retstart=start,
                    retmax=batch_size,
                )
                record = Entrez.read(handle)
                handle.close()
                break
            except RuntimeError as exc:
                logger.warning(
                    "Entrez error (attempt %d/%d): %s", attempt, max_retries, exc
                )
                time.sleep(retry_delay)
        else:
            logger.error("Max retries reached for taxid %s at start=%d", taxid, start)
            break

        all_ids.extend(record["IdList"])
        if len(record["IdList"]) < batch_size:
            break
        start += batch_size

    return all_ids


def fetch_records(id_list: list[str]) -> list:
    """Fetch GenBank records for a list of nucleotide IDs."""
    if not id_list:
        return []
    ids = ",".join(id_list)
    handle = Entrez.efetch(db="nucleotide", id=ids, rettype="gb", retmode="text")
    records = list(SeqIO.parse(handle, "genbank"))
    handle.close()
    return records


def extract_metadata(records: list) -> list[dict]:
    """Extract source-feature metadata from GenBank records."""
    metadata_rows = []

    for record in records:
        accession = record.id
        definition = record.description

        # BioSample from dbxrefs
        biosample = "N/A"
        for dbxref in record.dbxrefs:
            if dbxref.startswith("BioSample:"):
                biosample = dbxref.split(":")[1]

        # First reference title
        title = "N/A"
        refs = record.annotations.get("references", [])
        if refs:
            title = refs[0].title

        for feature in record.features:
            if feature.type != "source":
                continue
            q = feature.qualifiers
            metadata_rows.append(
                {
                    "Accession": accession,
                    "BioSample": biosample,
                    "TaxID": q.get("db_xref", ["N/A"])[0],
                    "Organism": q.get("organism", ["N/A"])[0],
                    "Strain": q.get("strain", ["N/A"])[0],
                    "Isolation_source": q.get("isolation_source", ["N/A"])[0],
                    "Host": q.get("host", ["N/A"])[0],
                    "Title": title,
                    "Definition": definition,
                }
            )

    return metadata_rows


def save_csv(rows: list[dict], path: str) -> None:
    """Write metadata rows to CSV."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "N/A") for k in FIELDNAMES})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="config/taxa.yml",
        help="Path to YAML config (default: config/taxa.yml)",
    )
    parser.add_argument(
        "--output",
        default="results/data/species_metadata.csv",
        help="Output CSV path (default: results/data/species_metadata.csv)",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    Entrez.email = cfg["entrez_email"]
    batch_size = cfg.get("batch_size", 500)
    max_retries = cfg.get("max_retries", 3)
    retry_delay = cfg.get("retry_delay_seconds", 3)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    all_metadata: list[dict] = []

    for genus, taxid in cfg["taxa"].items():
        logger.info("Searching NCBI for %s (txid%s)", genus, taxid)
        ids = search_all_ids(taxid, batch_size, max_retries, retry_delay)
        logger.info("  Found %d IDs", len(ids))

        records = fetch_records(ids)
        if not records:
            logger.warning("  No records returned for %s", genus)
            continue

        metadata = extract_metadata(records)
        all_metadata.extend(metadata)
        logger.info("  Extracted %d metadata rows", len(metadata))

    save_csv(all_metadata, args.output)
    logger.info("Saved %d rows to %s", len(all_metadata), args.output)


if __name__ == "__main__":
    main()
