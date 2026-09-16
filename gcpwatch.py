from datetime import datetime, timezone
import subprocess
from google.cloud import compute_v1
import sqlite3
from pathlib import Path
import os
import argparse

DB_PATH = Path(__file__).parent / "gcpwatch.db"

parser = argparse.ArgumentParser(description="Watch GCP instances for state changes")
parser.add_argument("--project", default=os.environ.get("GCP_PROJECT"))
parser.add_argument("--zone", default=os.environ.get("GCP_ZONE"))
args = parser.parse_args()

if not args.project or not args.zone:
    raise SystemExit("Set --project and --zone, or GCP_PROJECT and GCP_ZONE")

def collect():
    # Create a client
    client = compute_v1.InstancesClient()

    # Initialize request argument(s)
    request = compute_v1.ListInstancesRequest(
        project=args.project,
        zone=args.zone,
    )

    # Make the request
    page_result = client.list(request=request)
    return page_result

def init_db(path=DB_PATH):
    conn= sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshot(
            seen_at TEXT NOT NULL,
            kind    TEXT NOT NULL,
            name    TEXT NOT NULL,
            detail  TEXT
        )
    """)
    return conn

def store(conn,instances):
        seen_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        written = 0
        for inst in instances:
            if last_status(conn, inst.name) != inst.status:
                conn.execute(
                        "INSERT INTO snapshot(seen_at, kind, name, detail) VALUES (?, ?, ?, ?)", (seen_at, "instance", inst.name, inst.status)
                        )
                written += 1
        conn.commit()
        return written

def last_status(conn,name):
    row = conn.execute(
            "SELECT detail FROM snapshot WHERE name = ? ORDER BY seen_at DESC LIMIT 1", (name,)).fetchone()
    return row[0] if row else None

def report(conn, limit=10):
    rows = conn.execute(
        "SELECT seen_at, name, detail FROM snapshot ORDER BY seen_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    for seen_at, name, detail in rows:
        dt = datetime.fromisoformat(seen_at).astimezone()
        print(f"{dt}  {name:<20} {detail}")

def main():
    conn=init_db()
    instances=collect()
    written = store(conn, instances)
    if written:
        report(conn, limit=written)
        msg=f"{written} GCP change(s) detected"
        subprocess.run(["notify-send", "GCP Change detected", msg])
    conn.close()

main()
