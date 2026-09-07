"""Build a leakage-safe starter dataset for disruption modelling.

This does not train a model. It turns reviewed historical landslide records into
an auditable table with simple, source-derived features and a time split.
"""

import argparse
import csv
from datetime import date
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("datasets/processed/landslides/nasa-landslides-northeast.csv"))
    parser.add_argument("--output", type=Path, default=Path("datasets/processed/ml/landslide-training.csv"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.input.open(newline="", encoding="utf-8") as source, args.output.open("w", newline="", encoding="utf-8") as target:
        rows = csv.DictReader(source)
        fields = [
            "event_id", "state", "event_date", "longitude", "latitude",
            "trigger", "size", "location_accuracy_km", "fatality_count",
            "injury_count", "label_disruption", "split", "source_url",
        ]
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            event_date = date.fromisoformat(row["event_date_iso"])
            accuracy = row["location_accuracy"].replace("km", "").strip() or ""
            writer.writerow({
                "event_id": row["event_id"],
                "state": row["matched_state"],
                "event_date": event_date.isoformat(),
                "longitude": row["longitude"],
                "latitude": row["latitude"],
                "trigger": row["landslide_trigger"],
                "size": row["landslide_size"],
                "location_accuracy_km": accuracy,
                "fatality_count": row["fatality_count"] or "0",
                "injury_count": row["injury_count"] or "0",
                "label_disruption": "1",
                "split": "validation" if event_date.year >= 2015 else "train",
                "source_url": row["source_link"],
            })
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
