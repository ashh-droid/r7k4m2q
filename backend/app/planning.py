"""Historical forecast reconstruction and exploratory chronological calibration.

The day view uses observations from completed delivery days strictly before the
purchase decision date. It NEVER fits a decision day using its future or its own
actuals. January 2026 is too short to warrant an operational reliability claim.

Signed error = forecast - actual. Positive means forecast was above outturn.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from statistics import mean

from .analytics import LONDON, UTC, newest_at, quantile, utc_datetime, zulu

# GB day-ahead auctions. `cutoff` is gate closure, Europe/London, on D-1.
AUCTIONS = {
    'epex-hourly': {'label': 'EPEX hourly', 'cutoff': '09:20'},
    'n2ex-hourly': {'label': 'N2EX hourly', 'cutoff': '09:50'},
    'epex-half-hourly': {'label': 'EPEX half-hourly', 'cutoff': '15:30'},
}
DEFAULT_AUCTION = 'epex-hourly'

# A run published at the instant the gate closes cannot be traded on.
PUBLICATION_LAG = timedelta(minutes=5)

FIRST_DELIVERY = date(2026, 1, 2)
LAST_DELIVERY = date(2026, 2, 1)

# Wind-level bands (forecast MW). Chosen as round numbers before looking at
# results; each holds 160+ January hours.
LEVELS = [
    ('Under 10 GW', 0, 10_000),
    ('10 to 14 GW', 10_000, 14_000),
    ('Over 14 GW', 14_000, 10**9),
]
MIN_BAND_SAMPLES = 40
MIN_TRAINING_DAYS = 7  # no correction until a week of complete prior delivery dates


def level_of(forecast_mw: float) -> int:
    for i, (_, lo, hi) in enumerate(LEVELS):
        if lo <= forecast_mw < hi:
            return i
    return len(LEVELS) - 1


def gate_closure(delivery_day: date, auction: str) -> datetime:
    h, m = map(int, AUCTIONS[auction]['cutoff'].split(':'))
    local = datetime.combine(delivery_day - timedelta(days=1), time(h, m), LONDON)
    return local.astimezone(UTC)


def hourly_targets(delivery_day: date) -> list[datetime]:
    start = datetime.combine(delivery_day, time.min, LONDON).astimezone(UTC)
    end = datetime.combine(delivery_day + timedelta(days=1), time.min, LONDON).astimezone(UTC)
    hours = int((end - start).total_seconds() // 3600)
    return [start + timedelta(hours=i) for i in range(hours)]


def delivery_days() -> list[date]:
    days, d = [], FIRST_DELIVERY
    while d <= LAST_DELIVERY:
        days.append(d)
        d += timedelta(days=1)
    return days


def decision_rows(delivery_day: date, auction: str, actual: dict, forecast: dict) -> list[dict]:
    """One row per hourly WINDFOR target: the forecast usable at gate closure."""
    usable_at = gate_closure(delivery_day, auction) - PUBLICATION_LAG
    rows = []
    for target in hourly_targets(delivery_day):
        key = zulu(target)
        picked = newest_at(forecast.get(key, []), usable_at)
        f = picked['generation'] if picked else None
        a = actual.get(key)
        rows.append({
            'startTime': key,
            'hour': target.astimezone(LONDON).strftime('%H:%M'),
            'windfor': f,
            'actual': a,
            'error': f - a if f is not None and a is not None else None,
            'publishTime': picked['publishTime'] if picked else None,
            'leadHours': round((target - utc_datetime(picked['publishTime'])).total_seconds() / 3600, 1) if picked else None,
        })
    return rows


@dataclass(frozen=True)
class BandFit:
    bias: float      # mean error in the band
    q10: float       # 10th percentile of error after removing bias
    q90: float       # 90th percentile of error after removing bias


def fit(rows: list[dict]) -> list[BandFit]:
    paired = [r for r in rows if r['error'] is not None]
    overall = [r['error'] for r in paired]
    fits = []
    for i in range(len(LEVELS)):
        errs = [r['error'] for r in paired if level_of(r['windfor']) == i]
        if len(errs) < MIN_BAND_SAMPLES:
            errs = overall
        b = mean(errs)
        resid = [e - b for e in errs]
        fits.append(BandFit(b, quantile(resid, 0.1), quantile(resid, 0.9)))
    return fits


def apply(row: dict, fits: list[BandFit]) -> dict:
    f = row['windfor']
    if f is None:
        return {**row, 'plan': None, 'low': None, 'high': None, 'level': None}
    band = fits[level_of(f)]
    plan = max(0.0, f - band.bias)
    # Wind power cannot be negative. A high signed-error quantile corresponds
    # to a low actual-generation reference.
    low = max(0.0, plan - band.q90)
    high = max(low, plan - band.q10)
    return {**row, 'plan': plan, 'low': low, 'high': high, 'level': level_of(f)}


_MONTH_CACHE: dict[tuple[str, int], dict[date, list[dict]]] = {}


def month_rows(auction: str, store: dict) -> dict[date, list[dict]]:
    """Decision rows for every delivery day; the snapshot is immutable, so cache."""
    key = (auction, id(store))
    if key not in _MONTH_CACHE:
        _MONTH_CACHE[key] = {
            d: decision_rows(d, auction, store['actual'], store['forecast']) for d in delivery_days()
        }
    return _MONTH_CACHE[key]


def training_rows(delivery_day: date, by_day: dict[date, list[dict]]) -> tuple[list[dict], int]:
    """Use only delivery days finished before D-1 morning's auction.

    On D-1 the delivery day is still underway; we exclude it in full rather than
    accidentally use outturn from later than the simulated purchase decision.
    """
    last_eligible = delivery_day - timedelta(days=2)
    complete = [(d, rows) for d, rows in by_day.items() if d <= last_eligible and
                len([r for r in rows if r['error'] is not None]) == len(rows)]
    training = [r for _, rows in complete for r in rows]
    return training, len(complete)


def planned_day(delivery_day: date, auction: str, store: dict) -> tuple[list[dict], list[BandFit] | None, int]:
    by_day = month_rows(auction, store)
    training, training_days = training_rows(delivery_day, by_day)
    fits = fit(training) if training_days >= MIN_TRAINING_DAYS else None
    if fits is None:
        return ([{**r, 'plan': None, 'low': None, 'high': None, 'level': None}
                 for r in by_day[delivery_day]], None, training_days)
    return [apply(r, fits) for r in by_day[delivery_day]], fits, training_days


def gwh(values) -> float | None:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / 1000, 1) if vals else None


def validation(auction: str, store: dict) -> dict:
    """Walk-forward evaluation; each test day uses only earlier complete days."""
    by_day = month_rows(auction, store)
    raw, flat, level, inside, above_floor = [], [], [], 0, 0
    evaluated_days = 0
    for d, rows in by_day.items():
        training, n_days = training_rows(d, by_day)
        if n_days < MIN_TRAINING_DAYS:
            continue
        evaluated_days += 1
        flat_bias = mean(r['error'] for r in training if r['error'] is not None)
        fits = fit(training)
        for r in rows:
            if r['error'] is None:
                continue
            p = apply(r, fits)
            raw.append(abs(r['error']))
            flat.append(abs(r['error'] - flat_bias))
            level.append(abs(r['actual'] - p['plan']))
            inside += p['low'] <= r['actual'] <= p['high']
            above_floor += r['actual'] >= p['low']
    n = len(raw)
    return {
        'method': 'chronological_walk_forward',
        'evaluatedDays': evaluated_days,
        'minTrainingDays': MIN_TRAINING_DAYS,
        'n': n,
        'rawMaeMW': round(mean(raw)) if n else None,
        'flatMaeMW': round(mean(flat)) if n else None,
        'levelMaeMW': round(mean(level)) if n else None,
        'insideRangePct': round(100 * inside / n, 1) if n else None,
        'aboveFloorPct': round(100 * above_floor / n, 1) if n else None,
    }
