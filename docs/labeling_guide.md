# Manual Labeling Guide

Criteria used to assign lifestyle labels to trebouxiophyte GenBank records.

## Labels

| Label | Definition |
|-------|------------|
| **symbiotic** | Record clearly associated with a lichen or other symbiosis (host field names a fungal partner, isolation source mentions lichen thallus, etc.) |
| **free-living** | Record from a non-symbiotic context (soil, freshwater, culture collection with no symbiotic origin noted) |
| **ambiguous** | Insufficient metadata to determine lifestyle, or metadata is contradictory |

## Decision Rules

1. If the **Host** field names a fungal genus or mentions "lichen" -> **symbiotic**
2. If **Isolation_source** mentions soil, water, bark (without lichen context), or rock surface -> **free-living**
3. If the record comes from a culture collection (SAG, UTEX) with no additional host/source info -> **ambiguous** (these are excluded during preprocessing)
4. If **Title** describes a lichen symbiosis study -> **symbiotic**
5. When in doubt -> **ambiguous**

## Notes

- Genus names are stripped before classification to prevent the model from learning genus-label shortcuts.
- Records labeled ambiguous are excluded from the proportion analysis but retained in the dataset for transparency.
