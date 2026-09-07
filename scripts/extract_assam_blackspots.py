"""Preserve government HTML tables as CSV; locations still need verified geocoding."""

import csv
import hashlib
import json
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.stack = []
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.stack.append({"rows": [], "row": []})
        elif tag == "tr" and self.stack:
            self.stack[-1]["row"] = []
        elif tag in ("td", "th") and self.stack:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.stack and self.cell is not None:
            self.stack[-1]["row"].append(" ".join(" ".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.stack:
            if self.stack[-1]["row"]:
                self.stack[-1]["rows"].append(self.stack[-1]["row"])
            self.stack[-1]["row"] = []
        elif tag == "table" and self.stack:
            self.tables.append(self.stack.pop()["rows"])


def main():
    raw = ROOT / "datasets/raw/road_safety/assam_pwd.html"
    parser = TableParser()
    parser.feed(raw.read_text(encoding="utf-8"))
    out = ROOT / "datasets/processed/road_safety/assam-pwd-tables"
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for index, rows in enumerate(parser.tables):
        flattened = " ".join(" ".join(row) for row in rows).lower()
        if len(rows) > 5 and any(s in flattened for s in ("black spot", "fatal", "injur")):
            path = out / f"table-{index + 1}.csv"
            with path.open("w", newline="", encoding="utf-8") as file:
                csv.writer(file).writerows(rows)
            records.append(
                {
                    "file": str(path.relative_to(ROOT)),
                    "rows_including_headers": len(rows),
                    "column_counts": sorted(set(len(row) for row in rows)),
                    "requires_review": "Merged HTML cells are not propagated. These are raw table rows, not normalized events.",
                }
            )
    receipt = {
        "source": "https://pwdroads.assam.gov.in/portlets/road-safety",
        "accessed_at": datetime.now(UTC).isoformat(),
        "sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "tables": records,
        "coordinate_status": "No verified latitude/longitude columns extracted. Do not snap place names to roads automatically.",
    }
    (out / "provenance.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"Extracted {len(records)} Assam PWD tables with source context.")


if __name__ == "__main__":
    main()
