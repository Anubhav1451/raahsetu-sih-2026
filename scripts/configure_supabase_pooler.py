"""Switch a Supabase direct IPv6 DATABASE_URL to the working Mumbai session pooler."""

import os
import re
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"


def main() -> None:
    load_dotenv(ENV, override=True)
    current = os.environ.get("DATABASE_URL", "")
    parsed = urlsplit(current)
    match = re.fullmatch(r"db\.([a-z0-9]+)\.supabase\.co", parsed.hostname or "")
    if not match:
        raise SystemExit("DATABASE_URL is not a recognized Supabase direct connection URL")
    project_ref = match.group(1)
    password = unquote(parsed.password or "")
    if not password:
        raise SystemExit("DATABASE_URL has no password")

    selected = None
    errors = []
    for index in (0, 1):
        host = f"aws-{index}-ap-south-1.pooler.supabase.com"
        try:
            with psycopg.connect(
                host=host,
                port=5432,
                dbname=parsed.path.lstrip("/") or "postgres",
                user=f"postgres.{project_ref}",
                password=password,
                sslmode="require",
                connect_timeout=10,
            ) as connection:
                connection.execute("select 1").fetchone()
            selected = host
            break
        except psycopg.Error as exc:
            errors.append(f"{host}: {exc.__class__.__name__}")
    if selected is None:
        raise SystemExit("No Mumbai session pooler accepted the connection (" + "; ".join(errors) + ")")

    userinfo = f"{quote(f'postgres.{project_ref}', safe='')}:{quote(password, safe='')}"
    replacement = urlunsplit(
        ("postgresql", f"{userinfo}@{selected}:5432", parsed.path or "/postgres", "sslmode=require", "")
    )
    text = ENV.read_text(encoding="utf-8")
    updated = re.sub(r"(?m)^DATABASE_URL=.*$", f"DATABASE_URL={replacement}", text)
    ENV.write_text(updated, encoding="utf-8")
    print(f"Configured verified Mumbai session pooler: {selected}:5432")


if __name__ == "__main__":
    main()
