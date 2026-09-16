# gcpwatch

Polls the Google Compute API on a timer and records instance state changes to a
local SQLite database. Writes a row only when something actually changed, so the
table is an event log rather than a pile of identical snapshots.

Sends a desktop notification when a change is detected. Silent otherwise.

## Requires

- Python 3.9+
- An authenticated `gcloud`, or application default credentials:

      gcloud auth application-default login

## Setup

    git clone <this repo> ~/gcpwatch
    cd ~/gcpwatch
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

## Usage

Project and zone come from flags, or from the environment if the flags are
omitted. One or the other must be set.

    GCP_PROJECT=my-project GCP_ZONE=us-west1-b python3 gcpwatch.py

    python3 gcpwatch.py --project my-project --zone us-west1-b

The database is created as `gcpwatch.db` next to the script on first run.

## Running on a timer

    cp systemd/gcpwatch.service systemd/gcpwatch.timer ~/.config/systemd/user/

Edit `~/.config/systemd/user/gcpwatch.service` and set `GCP_PROJECT` and
`GCP_ZONE` to your own values. Then:

    systemctl --user daemon-reload
    systemctl --user enable --now gcpwatch.timer
    loginctl enable-linger $USER

The last line is needed or the timer stops when you log out.

Check it:

    systemctl --user list-timers gcpwatch.timer
    journalctl --user -u gcpwatch.service -n 20

## The data

One table, four columns:

| column  | holds                                          |
|---------|------------------------------------------------|
| seen_at | UTC timestamp, ISO format                      |
| kind    | resource type, currently always `instance`     |
| name    | instance name                                  |
| detail  | status, e.g. `RUNNING` or `TERMINATED`         |

`kind` exists so other resource types (firewall rules, disks) can share the
table later without a schema change.

Query it directly:

    sqlite3 gcpwatch.db -header -column "SELECT * FROM snapshot ORDER BY seen_at DESC LIMIT 10"

## Notes

An empty database means every instance looks like a change, so the first run
after setup will notify for everything it finds. This is expected.
