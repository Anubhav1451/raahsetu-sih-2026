"""Normalize Supabase values pasted into .env without printing any secret."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
BACKUP = ROOT / "work" / ".env.before-normalize"


def extract(pattern: str, text: str, name: str, required: bool = True) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        if required:
            raise SystemExit(f"Could not identify {name}; .env was not changed")
        return None
    return match.group(1).rstrip("'\";,)")


def main() -> None:
    raw = ENV.read_text(encoding="utf-8").strip()
    database_url = extract(r"((?:postgres|postgresql)://\S+)", raw, "database connection URL")
    supabase_url = extract(
        r"(https://[a-z0-9-]+\.supabase\.co)", raw, "Supabase URL", required=False
    )
    publishable_key = extract(
        r"(sb_publishable_[A-Za-z0-9_-]+)", raw, "publishable key", required=False
    )
    if "YOUR-PASSWORD" in database_url.upper() or "[PASSWORD]" in database_url.upper():
        raise SystemExit("Database URL still contains a password placeholder; .env was not changed")

    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    BACKUP.write_text(raw, encoding="utf-8")
    values = [
        "# RaahSetu local secrets. Never commit this file.",
        "DATASET_PATH=backend/data/demo-network.json",
        "CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173",
        "GRAPH_CACHE_SIZE=1",
    ]
    if supabase_url:
        values.append(f"SUPABASE_URL={supabase_url}")
    if publishable_key:
        values.append(f"SUPABASE_PUBLISHABLE_KEY={publishable_key}")
    values.extend([f"DATABASE_URL={database_url}", ""])
    normalized = "\n".join(values)
    ENV.write_text(normalized, encoding="utf-8")
    optional = " plus API URL/key" if supabase_url and publishable_key else ""
    print(f"Normalized .env with database URL{optional}.")
    print("Private pre-normalization backup: work/.env.before-normalize")


if __name__ == "__main__":
    main()
