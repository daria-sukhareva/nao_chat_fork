"""Check that the warehouse built from the confirmatory seed shows what ../confirmatory_scenario.md planted.

Run where analytics.duckdb is readable:
    python check_seed.py /data/analytics.duckdb
Prints one line per check and exits non-zero if any fails.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta

import duckdb

W = {n: datetime(2026, 1, 5) + timedelta(weeks=n - 1) for n in range(1, 10)}
DATA_END = datetime(2026, 3, 4, 12)


def week(n: int) -> tuple[datetime, datetime]:
    return W[n], min(W[n] + timedelta(weeks=1), DATA_END)


def day(iso: str) -> tuple[datetime, datetime]:
    start = datetime.fromisoformat(iso)
    return start, start + timedelta(days=1)


@dataclass
class Unit:
    location: str | None = None
    charger: str | None = None

    def visits_filter(self) -> str:
        if self.charger:
            return f"first_charger_id = '{self.charger}'"
        return f"location_id = '{self.location}'" if self.location else "true"

    def charger_filter(self, column: str = "charger_id") -> str:
        if self.charger:
            return f"{column} = '{self.charger}'"
        if self.location:
            return f"{column} in (select charger_id from MARTS.dim_chargers where location_id = '{self.location}')"
        return "true"


class Warehouse:
    def __init__(self, path: str):
        self.con = duckdb.connect(path, read_only=True)
        # Some marts are views over the raw catalog, which the demo attaches as RAW.
        self.con.execute(f"attach '{Path(path).with_name('raw.duckdb')}' as RAW (read_only)")

    def one(self, sql: str):
        return self.con.sql(sql).fetchone()[0]

    def visits(self, unit: Unit, period, hours=None) -> int:
        return self.one(f"select count(*) from MARTS.fact_visits where {unit.visits_filter()} {self._time(period, hours)}")

    def success_rate(self, unit: Unit, period, hours=None) -> float:
        return self.one(
            f"select avg(case when is_successful then 1.0 else 0.0 end) from MARTS.fact_visits "
            f"where is_successful is not null and {unit.visits_filter()} {self._time(period, hours)}"
        )

    def successful_visits(self, unit: Unit, period) -> int:
        return self.one(f"select count(*) from MARTS.fact_visits where is_successful and {unit.visits_filter()} {self._time(period)}")

    def first_attempt_rate(self, unit: Unit, period) -> float:
        return self.one(
            f"select avg(case when is_successful and charge_attempt_count = 1 then 1.0 else 0.0 end) "
            f"from MARTS.fact_visits where is_successful is not null and {unit.visits_filter()} {self._time(period)}"
        )

    def troubled_share(self, unit: Unit, period) -> float:
        return self.one(
            f"select avg(case when charge_attempt_count > 1 then 1.0 else 0.0 end) from MARTS.fact_visits "
            f"where is_successful and {unit.visits_filter()} {self._time(period)}"
        )

    def active_drivers(self, unit: Unit, period) -> int:
        return self.one(
            f"select count(distinct id_tag) from MARTS.fact_visits where id_tag is not null and {unit.visits_filter()} {self._time(period)}"
        )

    def failed_attempt_rate(self, unit: Unit, period) -> float:
        return self.one(
            f"select avg(case when is_successful = false then 1.0 else 0.0 end) from MARTS.fact_charge_attempts "
            f"where is_successful is not null and {unit.charger_filter()} "
            f"and charge_attempt_start_ts >= '{period[0]}' and charge_attempt_start_ts < '{period[1]}'"
        )

    def attempts(self, unit: Unit, period) -> int:
        return self.one(
            f"select count(*) from MARTS.fact_charge_attempts where {unit.charger_filter()} "
            f"and charge_attempt_start_ts >= '{period[0]}' and charge_attempt_start_ts < '{period[1]}'"
        )

    def rate_and_n(self, unit: Unit, period) -> tuple[float, int]:
        return self.success_rate(unit, period), self.one(
            f"select count(*) from MARTS.fact_visits where is_successful is not null and {unit.visits_filter()} {self._time(period)}"
        )

    def failed_attempts(self, unit: Unit, period) -> int:
        return self.one(
            f"select count(*) from MARTS.fact_charge_attempts where is_successful = false and {unit.charger_filter()} "
            f"and charge_attempt_start_ts >= '{period[0]}' and charge_attempt_start_ts < '{period[1]}'"
        )

    def uptime(self, unit: Unit, period) -> float:
        return self.one(
            f"select 1 - sum(downtime_minutes) / sum(commissioned_minutes) from MARTS.fact_uptime_daily "
            f"where {unit.charger_filter()} and date_id >= cast('{period[0]}' as date) and date_id < cast('{period[1]}' as date)"
        )

    def commissioned_ports(self, unit: Unit, at: datetime) -> int:
        return self.one(
            f"select coalesce(sum(port_count), 0) from MARTS.dim_chargers where {unit.charger_filter()} "
            f"and commissioned_ts <= '{at}' and (decommissioned_ts is null or decommissioned_ts > '{at}')"
        )

    @staticmethod
    def _time(period, hours=None) -> str:
        clause = f"and visit_start_ts >= '{period[0]}' and visit_start_ts < '{period[1]}'"
        if hours:
            clause += f" and extract(hour from visit_start_ts) >= {hours[0]} and extract(hour from visit_start_ts) < {hours[1]}"
        return clause


results: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> None:
    results.append((ok, label))
    print(f"{'PASS' if ok else 'FAIL'}  {label}")


def change(before: float, after: float) -> float:
    return (after - before) / before if before else float("inf")


def episode(wh: Warehouse, name: str, metric: str, b_value, p_value, direction: int, baseline_events: int | None) -> None:
    rel = change(b_value, p_value)
    big = abs(rel) >= 0.2 and (rel > 0) == (direction > 0)
    floor = baseline_events is None or baseline_events >= 20
    events = "" if baseline_events is None else f", {baseline_events} baseline events"
    check(big and floor, f"{name}: {metric} {b_value:.3f} to {p_value:.3f} ({rel:+.0%}{events})")


def flat(name: str, what: str, before: float, after: float, limit: float) -> None:
    rel = change(before, after)
    check(abs(rel) < limit, f"{name}: {what} {before:.3f} to {after:.3f} ({rel:+.1%}, limit {limit:.0%})")


def held(name: str, what: str, before: tuple[float, int], after: tuple[float, int]) -> None:
    """A rate held if its change is not significant: two-proportion z below 2."""
    (p1, n1), (p2, n2) = before, after
    pooled = (p1 * n1 + p2 * n2) / (n1 + n2)
    se = (pooled * (1 - pooled) * (1 / n1 + 1 / n2)) ** 0.5
    z = (p2 - p1) / se if se else 0.0
    check(abs(z) < 2, f"{name}: {what} {p1:.3f} (n={n1}) to {p2:.3f} (n={n2}), z={z:+.2f}")


def main(path: str) -> None:
    wh = Warehouse(path)
    L = lambda loc: Unit(location=loc)
    C = lambda ch: Unit(charger=ch)
    net = Unit()

    print("== Episodes")
    episode(wh, "E01", "CH-112 visit success", wh.success_rate(C("CH-112"), week(2)), wh.success_rate(C("CH-112"), week(3)), -1, wh.visits(C("CH-112"), week(2)))
    episode(wh, "E02", "CH-132 vs CH-131 visit success W2", wh.success_rate(C("CH-132"), week(2)), wh.success_rate(C("CH-131"), week(2)), -1, wh.visits(C("CH-132"), week(2)))
    episode(wh, "E03", "LOC-104 visits", wh.visits(L("LOC-104"), week(3)), wh.visits(L("LOC-104"), week(4)), -1, wh.visits(L("LOC-104"), week(3)))
    episode(wh, "E04", "LOC-106 uptime", wh.uptime(L("LOC-106"), day("2026-02-10")), wh.uptime(L("LOC-106"), day("2026-02-11")), -1, None)
    episode(wh, "E05", "LOC-102 visits 17-21h", wh.visits(L("LOC-102"), week(4), (17, 21)), wh.visits(L("LOC-102"), week(5), (17, 21)), -1, wh.visits(L("LOC-102"), week(4), (17, 21)))
    episode(wh, "E06", "LOC-101 visits", wh.visits(L("LOC-101"), week(5)), wh.visits(L("LOC-101"), week(6)), -1, wh.visits(L("LOC-101"), week(5)))
    episode(wh, "E07", "network active drivers", wh.active_drivers(net, week(3)), wh.active_drivers(net, week(4)), 1, wh.active_drivers(net, week(3)))
    episode(wh, "E08", "LOC-103 visit success", wh.success_rate(L("LOC-103"), week(6)), wh.success_rate(L("LOC-103"), week(7)), -1, wh.visits(L("LOC-103"), week(6)))
    episode(wh, "E09", "LOC-106 visits", wh.visits(L("LOC-106"), week(2)), wh.visits(L("LOC-106"), week(3)), -1, wh.visits(L("LOC-106"), week(2)))
    episode(wh, "E10", "LOC-102 visits", wh.visits(L("LOC-102"), week(1)), wh.visits(L("LOC-102"), week(2)), 1, wh.visits(L("LOC-102"), week(1)))
    episode(wh, "E11", "LOC-104 first-attempt rate", wh.first_attempt_rate(L("LOC-104"), week(6)), wh.first_attempt_rate(L("LOC-104"), week(7)), -1, wh.visits(L("LOC-104"), week(6)))
    episode(wh, "E12", "CH-171 visit success", wh.success_rate(C("CH-171"), week(2)), wh.success_rate(C("CH-171"), week(3)), -1, wh.visits(C("CH-171"), week(2)))
    episode(wh, "E13", "LOC-103 visit success", wh.success_rate(L("LOC-103"), week(3)), wh.success_rate(L("LOC-103"), week(4)), -1, wh.visits(L("LOC-103"), week(3)))
    episode(wh, "E14", "LOC-106 visits 6-10h", wh.visits(L("LOC-106"), week(7), (6, 10)), wh.visits(L("LOC-106"), week(8), (6, 10)), -1, wh.visits(L("LOC-106"), week(7), (6, 10)))
    episode(wh, "E15", "LOC-102 visit success", wh.success_rate(L("LOC-102"), day("2026-02-18")), wh.success_rate(L("LOC-102"), day("2026-02-19")), -1, wh.visits(L("LOC-102"), day("2026-02-18")))
    episode(wh, "E16", "LOC-101 visits", wh.visits(L("LOC-101"), day("2026-01-30")), wh.visits(L("LOC-101"), day("2026-01-31")), -1, wh.visits(L("LOC-101"), day("2026-01-30")))
    episode(wh, "E17", "LOC-101 vs LOC-106 uptime W5", wh.uptime(L("LOC-101"), week(5)), wh.uptime(L("LOC-106"), week(5)), -1, None)
    episode(wh, "E18", "LOC-102 vs LOC-104 visit success W1", wh.success_rate(L("LOC-102"), week(1)), wh.success_rate(L("LOC-104"), week(1)), -1, wh.visits(L("LOC-102"), week(1)))
    episode(wh, "E19", "CH-152 vs CH-151 successful visits W6", wh.successful_visits(C("CH-152"), week(6)), wh.successful_visits(C("CH-151"), week(6)), -1, wh.visits(C("CH-152"), week(6)))
    episode(wh, "E20", "LOC-107 failed-attempt rate", wh.failed_attempt_rate(L("LOC-107"), week(5)), wh.failed_attempt_rate(L("LOC-107"), week(6)), 1, wh.attempts(L("LOC-107"), week(5)))
    episode(wh, "E21", "LOC-105 visit success", wh.success_rate(L("LOC-105"), week(7)), wh.success_rate(L("LOC-105"), week(8)), -1, wh.visits(L("LOC-105"), week(7)))
    episode(wh, "E22", "CH-171 uptime", wh.uptime(C("CH-171"), week(7)), wh.uptime(C("CH-171"), week(8)), -1, None)

    print("\n== Misleading readings are false")
    held("E09", "LOC-106 visit success", wh.rate_and_n(L("LOC-106"), week(2)), wh.rate_and_n(L("LOC-106"), week(3)))
    flat("E09", "LOC-106 uptime", wh.uptime(L("LOC-106"), week(2)), wh.uptime(L("LOC-106"), week(3)), 0.05)
    for ch in ("CH-131", "CH-132", "CH-133"):
        held("E13", f"{ch} visit success", wh.rate_and_n(C(ch), week(3)), wh.rate_and_n(C(ch), week(4)))
    held("E11", "LOC-104 visit success", wh.rate_and_n(L("LOC-104"), week(6)), wh.rate_and_n(L("LOC-104"), week(7)))
    held("E20", "LOC-107 visit success", wh.rate_and_n(L("LOC-107"), week(5)), wh.rate_and_n(L("LOC-107"), week(6)))
    check(wh.troubled_share(L("LOC-104"), week(7)) > 1.2 * wh.troubled_share(L("LOC-104"), week(6)), "E11: troubled share rises")
    check(wh.commissioned_ports(L("LOC-101"), datetime(2026, 2, 8)) == 6 and wh.commissioned_ports(L("LOC-101"), datetime(2026, 2, 10)) == 4, "E06: LOC-101 ports 6 to 4")
    flat("E10", "LOC-102 commissioned ports", wh.commissioned_ports(L("LOC-102"), W[1]), wh.commissioned_ports(L("LOC-102"), W[2]), 0.01)
    flat("E08", "LOC-103 uptime", wh.uptime(L("LOC-103"), week(6)), wh.uptime(L("LOC-103"), week(7)), 0.05)
    flat("E21", "LOC-105 uptime", wh.uptime(L("LOC-105"), week(7)), wh.uptime(L("LOC-105"), week(8)), 0.05)

    print("\n== Outages")
    planted = {
        "CH-141": [("2026-01-27 00:00", "2026-01-30 00:00")], "CH-142": [("2026-01-27 00:00", "2026-01-30 00:00")],
        "CH-162": [("2026-02-11 00:00", "2026-02-12 00:00")] + [(f"2026-{d:%m-%d} 06:00", f"2026-{d:%m-%d} 10:00") for d in (W[8] + timedelta(days=i) for i in range(7))],
        "CH-161": [("2026-02-02 00:00", "2026-02-05 00:00")] + [(f"2026-{d:%m-%d} 06:00", f"2026-{d:%m-%d} 10:00") for d in (W[8] + timedelta(days=i) for i in range(7))],
        "CH-121": [(f"2026-{d:%m-%d} 17:00", f"2026-{d:%m-%d} 21:00") for d in (W[5] + timedelta(days=i) for i in range(7))],
        "CH-122": [(f"2026-{d:%m-%d} 17:00", f"2026-{d:%m-%d} 21:00") for d in (W[5] + timedelta(days=i) for i in range(7))],
    }
    outages = wh.con.sql(
        "select distinct charger_id, outage_id, outage_from_ts, outage_to_ts from MARTS.fact_downtime_daily where downtime_type = 'OFFLINE'"
    ).fetchall()
    matched = set()
    for charger, windows in planted.items():
        for start, end in windows:
            s, e = datetime.fromisoformat(start), datetime.fromisoformat(end)
            hit = [o for o in outages if o[0] == charger and abs((o[2] - s).total_seconds()) <= 600 and abs((o[3] - e).total_seconds()) <= 600]
            matched.update(o[1] for o in hit)
            # fact_downtime_daily is at port grain: one outage per port of the charger.
            check(len(hit) == 2, f"{charger} offline {start} to {end}: {len(hit)} matching port outage(s)")
    stray = [o for o in outages if o[1] not in matched]
    check(not stray, f"no other offline outages ({len(stray)} found{': ' + str(stray[:3]) if stray else ''})")

    print("\n== Tokens")
    rejected = wh.con.sql(
        "select c.location_id, a.id_tag_status, min(a.charge_attempt_start_ts), count(*) from MARTS.fact_charge_attempts a "
        "join MARTS.dim_chargers c using (charger_id) where a.failure_reason = 'AUTH_REJECTED' group by all order by 1"
    ).fetchall()
    print("   ", rejected)
    check({(r[0], r[1]) for r in rejected} <= {("LOC-103", "Expired"), ("LOC-105", "Blocked"), ("LOC-103", None), ("LOC-105", None)}, "rejections only at LOC-103 (Expired) and LOC-105 (Blocked)")
    check(all((r[0] == "LOC-103" and r[2] >= W[7]) or (r[0] == "LOC-105" and r[2] >= W[8]) for r in rejected), "no rejection before its planted start")

    print("\n== Controls")
    held("N1", "LOC-108 visit success W3 to W4", wh.rate_and_n(L("LOC-108"), week(3)), wh.rate_and_n(L("LOC-108"), week(4)))
    # N2 is the first pair of adjacent days in W2 whose visits at LOC-101 change by less than 10%.
    pairs = [(W[2] + timedelta(days=i), W[2] + timedelta(days=i + 1)) for i in range(6)]
    counts = [(a, b, wh.visits(L("LOC-101"), (a, a + timedelta(days=1))), wh.visits(L("LOC-101"), (b, b + timedelta(days=1)))) for a, b in pairs]
    chosen = next(((a, b, x, y) for a, b, x, y in counts if abs(change(x, y)) < 0.10), None)
    check(chosen is not None, f"N2: LOC-101 visits {chosen[0]:%b %d} to {chosen[1]:%b %d}, {chosen[2]} to {chosen[3]}" if chosen else "N2: no day pair in W2 within 10%")
    flat("N3", "LOC-106 uptime W1 to W2", wh.uptime(L("LOC-106"), week(1)), wh.uptime(L("LOC-106"), week(2)), 0.10)
    check(change(wh.success_rate(L("LOC-108"), week(5)), wh.success_rate(L("LOC-108"), week(6))) > -0.10, "F1: LOC-108 success didn't drop in W6")
    check(not [o for o in outages if o[0] == "CH-111" and week(3)[0] <= o[2] < week(3)[1]], "F2: CH-111 had no outage in W3")
    check(wh.commissioned_ports(L("LOC-104"), datetime(2026, 3, 1)) == 4, "F3: LOC-104 still has 4 ports in March")
    check(change(wh.active_drivers(L("LOC-108"), week(5)), wh.active_drivers(L("LOC-108"), week(6))) > -0.10, "F4: LOC-108 active drivers didn't fall in W6")
    last = wh.one("select max(visit_start_ts) from MARTS.fact_visits")
    check(datetime(2026, 3, 4, 9) < last < DATA_END, f"P1-P3: data ends inside Mar 4 before 12:00 (last visit {last})")
    check(wh.success_rate(L("LOC-103"), week(9)) < 0.9 * wh.success_rate(L("LOC-103"), week(6)), "P2: LOC-103's cause continues into W9")

    failed = [label for ok, label in results if not ok]
    print(f"\n{len(results) - len(failed)} of {len(results)} checks pass")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main(sys.argv[1])
