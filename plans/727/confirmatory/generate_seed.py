"""Generate the confirmatory seed described in ../confirmatory_scenario.md with kwwhat's logs-generator.

Writes chargers.csv, connectors.csv, ports.csv and ocpp_1_6_synthetic_logs_14d.csv (the name duckdb-init
loads) to the output folder. Driver pools, the auth list and per-charger series stay in the work folder,
outside kwwhat, because they reveal the scenario.

Usage:
    python generate_seed.py --kwwhat ~/github/kwwhat --python <venv with ocpp and websockets>
"""

import argparse
import csv
import hashlib
import json
import random
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DATA_START = datetime(2026, 1, 5, tzinfo=timezone.utc)
DATA_END = datetime(2026, 3, 4, 12, tzinfo=timezone.utc)
POOL_SEED = 20261125

LOCATIONS = {
    "LOC-101": ["CH-111", "CH-112", "CH-113"],
    "LOC-102": ["CH-121", "CH-122"],
    "LOC-103": ["CH-131", "CH-132", "CH-133"],
    "LOC-104": ["CH-141", "CH-142"],
    "LOC-105": ["CH-151", "CH-152"],
    "LOC-106": ["CH-161", "CH-162"],
    "LOC-107": ["CH-171", "CH-172"],
    "LOC-108": ["CH-181", "CH-182"],
}
COMMISSIONED = {charger: DATA_START for chargers in LOCATIONS.values() for charger in chargers}
COMMISSIONED |= {"CH-151": datetime(2026, 1, 26, 8, tzinfo=timezone.utc), "CH-152": datetime(2026, 1, 26, 8, tzinfo=timezone.utc)}
DECOMMISSIONED = {"CH-113": datetime(2026, 2, 9, 8, tzinfo=timezone.utc)}
CONNECTORS = [(1, 1, "CCS", 150), (1, 2, "NACS", 150), (2, 3, "CCS", 50), (2, 4, "CHAdeMO", 50)]

BASE = {
    "sessions-per-port-per-day": 5.0,
    "failed-attempt-probability": 0.05,
    "fault-probability": 0.03,
    "retry-probability": 0.3,
    "authorize-probability": 0.3,
}


def week(n: int) -> tuple[date, date]:
    """First and last day of week n, W1 starting Monday Jan 5, 2026."""
    first = DATA_START.date() + timedelta(weeks=n - 1)
    return first, first + timedelta(days=6)


def in_week(day: date, n: int) -> bool:
    first, last = week(n)
    return first <= day <= last


def daily_windows(n: int, from_hour: int, to_hour: int) -> list[tuple[datetime, datetime]]:
    first, _ = week(n)
    return [
        (
            datetime.combine(first + timedelta(days=offset), datetime.min.time(), timezone.utc) + timedelta(hours=from_hour),
            datetime.combine(first + timedelta(days=offset), datetime.min.time(), timezone.utc) + timedelta(hours=to_hour),
        )
        for offset in range(7)
    ]


def at(year_month_day: str, hour: int = 0) -> datetime:
    return datetime.fromisoformat(year_month_day).replace(hour=hour, tzinfo=timezone.utc)


def day_params(charger: str, day: date) -> dict[str, float]:
    """The generator flags for one charger on one day: the baseline, changed by the episodes."""
    params = dict(BASE)
    location = next(loc for loc, chargers in LOCATIONS.items() if charger in chargers)
    if location == "LOC-105":
        params["sessions-per-port-per-day"] = 10.0
    if location == "LOC-101":  # enough daily visits for E16's 20-event floor
        params["sessions-per-port-per-day"] = 8.0
    if location == "LOC-102" and day >= week(2)[0]:  # E10
        params["sessions-per-port-per-day"] = 8.0
    if charger == "CH-112" and in_week(day, 3):  # E01
        params["fault-probability"] = 0.5
    if charger == "CH-131" and in_week(day, 2):  # E02
        params["fault-probability"] = 0.45
    if charger == "CH-133":  # E13, throughout
        params["fault-probability"] = 0.8
    if charger in ("CH-131", "CH-132") and in_week(day, 4):  # E13
        params["sessions-per-port-per-day"] = 1.5
    if location == "LOC-104" and in_week(day, 1):  # E18
        params["fault-probability"] = 0.4
    if location == "LOC-104" and in_week(day, 7):  # E11
        params["failed-attempt-probability"] = 0.35
        params["retry-probability"] = 0.9
    if location == "LOC-106" and in_week(day, 3):  # E09
        params["sessions-per-port-per-day"] = 2.5
    if charger == "CH-121" and day == date(2026, 2, 19):  # E15
        params["fault-probability"] = 0.7
    if location == "LOC-101" and day == date(2026, 1, 31):  # E16, a one-day demand drop
        params["sessions-per-port-per-day"] = 3.0
    if charger == "CH-151" and in_week(day, 6):  # E19
        params["failed-attempt-probability"] = 0.5
        params["retry-probability"] = 0.0
    if charger == "CH-171" and in_week(day, 3):  # E12
        params["failed-attempt-probability"] = 0.4
        params["retry-probability"] = 0.0
    if charger == "CH-172" and in_week(day, 6):  # E20
        params["fault-probability"] = 0.3
        params["retry-probability"] = 0.95
    if charger == "CH-171" and in_week(day, 8):  # E22: arrivals often enough that both connectors fault at once
        params["fault-probability"] = 1.0
        params["sessions-per-port-per-day"] = 20.0
    return params


def offline_windows(charger: str) -> list[tuple[datetime, datetime]]:
    windows = []
    if charger in ("CH-141", "CH-142"):  # E03
        windows.append((at("2026-01-27"), at("2026-01-30")))
    if charger == "CH-162":  # E04
        windows.append((at("2026-02-11"), at("2026-02-12")))
    if charger in ("CH-121", "CH-122"):  # E05
        windows += daily_windows(5, 17, 21)
    if charger in ("CH-161", "CH-162"):  # E14
        windows += daily_windows(8, 6, 10)
    if charger == "CH-161":  # E17
        windows.append((at("2026-02-02"), at("2026-02-05")))
    return sorted(windows)


@dataclass
class Run:
    start: datetime
    days: float
    params: dict[str, float] = field(default_factory=dict)


def runs_for(charger: str) -> list[Run]:
    """Consecutive days with the same flags become one appended run."""
    runs: list[Run] = []
    # A run before commissioning writes nothing, not even the append state, so the series starts on the
    # commissioning day and the generator cuts that run to the commissioning time.
    day = max(DATA_START, COMMISSIONED[charger]).date()
    while datetime.combine(day, datetime.min.time(), timezone.utc) < DATA_END:
        start = datetime.combine(day, datetime.min.time(), timezone.utc)
        length = min(1.0, (DATA_END - start).total_seconds() / 86400)
        params = day_params(charger, day)
        if runs and runs[-1].params == params:
            runs[-1].days += length
        else:
            runs.append(Run(start, length, params))
        day += timedelta(days=1)
    return runs


def driver_pools() -> dict[str, list[str]]:
    rng = random.Random(POOL_SEED)
    tags = [f"{rng.getrandbits(32):08X}" for _ in range(580)]
    assert len(set(tags)) == len(tags)
    return {"general": tags[:400], "LOC-103": tags[400:460], "LOC-105": tags[460:580]}


def pool_of(charger: str) -> str:
    location = next(loc for loc, chargers in LOCATIONS.items() if charger in chargers)
    return location if location in ("LOC-103", "LOC-105") else "general"


def write_reference_files(out: Path, work: Path, pools: dict[str, list[str]]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    iso = lambda ts: ts.strftime("%Y-%m-%dT%H:%M:%S.000Z") if ts else ""
    with (out / "chargers.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["charge_point_id", "location_id", "commissioned_ts", "decommissioned_ts"])
        for location, chargers in LOCATIONS.items():
            for charger in chargers:
                w.writerow([charger, location, iso(COMMISSIONED[charger]), iso(DECOMMISSIONED.get(charger))])
    with (out / "connectors.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["charge_point_id", "port_id", "connector_id", "connector_type", "max_power_kw"])
        for chargers in LOCATIONS.values():
            for charger in chargers:
                for port, connector, kind, kw in CONNECTORS:
                    w.writerow([charger, port, connector, kind, kw])
    with (out / "ports.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["charge_point_id", "port_id", "max_power_kw"])
        for chargers in LOCATIONS.values():
            for charger in chargers:
                for port, kw in sorted({(port, kw) for port, _, _, kw in CONNECTORS}):
                    w.writerow([charger, port, kw])
    for name, tags in pools.items():
        (work / f"id_tags_{name}.csv").write_text("id_tag\n" + "\n".join(tags) + "\n")
    with (work / "auth_list.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id_tag", "status", "from_ts", "expiry_date"])
        for tag in pools["LOC-103"][:30]:  # E08
            w.writerow([tag, "Expired", "2026-02-16T00:00:00Z", "2026-02-15T23:59:59Z"])
        for tag in pools["LOC-105"][:48]:  # E21, 40% of the pool
            w.writerow([tag, "Blocked", "2026-02-23T00:00:00Z", ""])


def run_seed(charger: str, run_start: datetime) -> int:
    return int(hashlib.sha256(f"{charger}|{run_start.isoformat()}".encode()).hexdigest()[:8], 16)


def generate_charger(python: str, generator: Path, out: Path, work: Path, charger: str) -> Path:
    series = work / f"{charger}.csv"
    for stale in (series, series.with_name(series.name + ".state.json")):
        stale.unlink(missing_ok=True)
    windows = [f"{a.strftime('%Y-%m-%dT%H:%M:%SZ')}/{b.strftime('%Y-%m-%dT%H:%M:%SZ')}" for a, b in offline_windows(charger)]
    for index, run in enumerate(runs_for(charger)):
        command = [
            python, "client.py", "--append", "--charge-point-id", charger, "--days", f"{run.days:g}",
            "--output", str(series), "--chargers-file", str(out / "chargers.csv"),
            "--connectors-file", str(out / "connectors.csv"),
            "--id-tags-file", str(work / f"id_tags_{pool_of(charger)}.csv"),
            "--seed", str(run_seed(charger, run.start)), "--heartbeat-interval", "300",
        ]
        if index == 0:
            command += ["--start", run.start.strftime("%Y-%m-%dT%H:%M:%SZ")]
        for name, value in run.params.items():
            command += [f"--{name}", f"{value:g}"]
        for window in windows:
            command += ["--offline", window]
        result = subprocess.run(command, cwd=generator, capture_output=True, text=True)
        if result.returncode != 0:
            sys.exit(f"{charger} run {index} failed:\n{result.stdout}\n{result.stderr}")
    return series


def merge(series: list[Path], target: Path) -> str:
    rows = []
    for path in series:
        with path.open(newline="") as f:
            rows += list(csv.DictReader(f))
    rows.sort(key=lambda row: row["timestamp"])
    with target.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["timestamp", "id", "action", "msg"])
        w.writeheader()
        w.writerows(rows)
    return hashlib.sha256(target.read_bytes()).hexdigest()


def wait_for_port(port: int, timeout_s: float = 20) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        with socket.socket() as s:
            if s.connect_ex(("localhost", port)) == 0:
                return
        time.sleep(0.2)
    sys.exit(f"the central system did not start on port {port}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kwwhat", type=Path, required=True)
    parser.add_argument("--python", default=sys.executable, help="Python with the generator's requirements.")
    parser.add_argument("--work", type=Path, default=Path(__file__).parent / "work")
    args = parser.parse_args()
    generator = args.kwwhat / "demo" / "logs-generator"
    out = args.kwwhat / "demo" / "seeds_confirmatory"
    pools = driver_pools()
    write_reference_files(out, args.work, pools)
    server = subprocess.Popen(
        [args.python, "server.py", "--auth-list", str(args.work / "auth_list.csv")],
        cwd=generator, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_port(9000)
        series = []
        for chargers in LOCATIONS.values():
            for charger in chargers:
                print(f"generating {charger}", flush=True)
                series.append(generate_charger(args.python, generator, out, args.work, charger))
    finally:
        server.terminate()
        server.wait()
    digest = merge(series, out / "ocpp_1_6_synthetic_logs_14d.csv")
    manifest = {"sha256": digest, "generator_commit": subprocess.run(
        ["git", "-C", str(args.kwwhat), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()}
    (args.work / "seed_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
