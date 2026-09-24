# gcpwatch

Polls the Google Compute API on a timer and records instance state changes in a
local SQLite database. Writes a row only when something actually changed, so the
table is a log of events rather than a pile of identical snapshots.

Sends a desktop notification when it finds one. Silent otherwise.

## Requires

- Python 3.9+
- Application default credentials:

      gcloud auth application-default login

## Setup

    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

## Usage

Project and zone come from flags, or from the environment if the flags are
omitted. One or the other must be set.

    GCP_PROJECT=my-project GCP_ZONE=us-west1-b python3 gcpwatch.py
    python3 gcpwatch.py --project my-project --zone us-west1-b

The database is created as `gcpwatch.db` next to the script on first run.

## On a timer

    cp systemd/gcpwatch.{service,timer} ~/.config/systemd/user/
    # edit the service and set GCP_PROJECT and GCP_ZONE
    systemctl --user daemon-reload
    systemctl --user enable --now gcpwatch.timer
    loginctl enable-linger $USER

The service runs the venv's Python directly, by full path. systemd has no idea
what an activated virtual environment is, so pointing at the interpreter is how
a scheduled script gets its installed packages.

## The data

One table, four columns:

| Column    | Holds                                      |
|-----------|--------------------------------------------|
| `seen_at` | UTC timestamp, ISO format                  |
| `kind`    | resource type, currently always `instance` |
| `name`    | instance name                              |
| `detail`  | status, e.g. `RUNNING` or `TERMINATED`     |

`kind` exists so other resource types — firewall rules, disks — can share the
table later without changing its shape.

    sqlite3 gcpwatch.db -header -column \
      "SELECT * FROM snapshot ORDER BY seen_at DESC LIMIT 10"

## Why it writes only on change

Polling every few minutes and writing every time would give 288 rows a day
saying "still running". Writing only on change gives one row per event, and the
interesting questions — when did this stop, how long was it off, did anything
change overnight — become simple queries over a small table.

## Notes

**The database path is absolute**, derived from `Path(__file__).parent`. With a
relative path the file would follow the working directory, and systemd runs
from your home directory rather than the script's — so a scheduled run would
quietly use a different, empty database.

**An empty database makes every instance look new**, so the first run after
setup notifies for everything it finds. Expected.

**Deletions are not detected.** The script compares each instance's current
status against its last known one, and an instance that no longer exists is
never checked. Catching that needs a comparison of the whole set of names
between polls — worth adding, since a resource disappearing is usually more
alarming than one appearing.
