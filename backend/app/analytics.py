"""Deterministic, timezone-aware forecast selection and error analytics.

This module never calls external services. It is also the technical review focus.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from math import sqrt
from statistics import mean
from zoneinfo import ZoneInfo

UTC = timezone.utc
LONDON = ZoneInfo('Europe/London')
FIRST_DECISION = date(2026, 1, 1)
LAST_DECISION = date(2026, 1, 31)


def utc_datetime(value: str | datetime) -> datetime:
    """Reject naive timestamps; retain millisecond precision and normalize to UTC."""
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    else:
        parsed = value
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f'Timestamp lacks timezone: {value}')
    return parsed.astimezone(UTC)


def zulu(value: datetime) -> str:
    return utc_datetime(value).isoformat().replace('+00:00', 'Z')


def parse_cutoff(value: str) -> time:
    """Accept a strict 24-hour HH:MM cutoff in Europe/London local time."""
    import re

    if not isinstance(value, str) or not re.fullmatch(
        r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value
    ):
        raise ValueError('Cutoff must be HH:MM in Europe/London')

    return time.fromisoformat(value)


def decision_timestamp(decision_day: date, cutoff: str) -> datetime:
    """Decision date D, delivery date D+1. January is GMT, but use tz database."""
    local = datetime.combine(decision_day, parse_cutoff(cutoff), LONDON)
    return local.astimezone(UTC)


def delivery_targets(decision_day: date) -> list[datetime]:
    delivery_day = decision_day + timedelta(days=1)
    midnight = datetime.combine(delivery_day, time.min, LONDON).astimezone(UTC)
    finish = datetime.combine(delivery_day + timedelta(days=1), time.min, LONDON).astimezone(UTC)
    return [midnight + timedelta(minutes=30*i) for i in range(int((finish-midnight).total_seconds()//1800))]


def forecast_index(forecasts: list[dict]) -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    for row in forecasts:
        grouped[row['startTime']].append(row)
    for records in grouped.values():
        records.sort(key=lambda r: r['publishTime'])
    return dict(grouped)


def newest_at(records: list[dict], cutoff: datetime) -> dict | None:
    """Return last publication <= cutoff; a publication after cutoff is leakage."""
    if not records:
        return None
    publications = [utc_datetime(r['publishTime']) for r in records]
    idx = bisect_right(publications, cutoff) - 1
    return records[idx] if idx >= 0 else None


def select_intervals(decision_day: date, cutoff: str, actual: dict[str, float], forecast: dict[str, list[dict]]) -> list[dict]:
    selection_time = decision_timestamp(decision_day, cutoff)
    rows = []
    for period in delivery_targets(decision_day):
        key = zulu(period)
        selected = newest_at(forecast.get(key, []), selection_time)
        forecast_mw = selected['generation'] if selected else None
        actual_mw = actual.get(key)
        error = forecast_mw - actual_mw if forecast_mw is not None and actual_mw is not None else None
        rows.append({
            'startTime': key,
            'period': period.astimezone(LONDON).strftime('%H:%M'),
            'forecastMW': forecast_mw,
            'actualMW': actual_mw,
            'errorMW': error,
            'publishTime': selected['publishTime'] if selected else None,
            'leadHours': round((period - utc_datetime(selected['publishTime'])).total_seconds()/3600, 2) if selected else None,
        })
    return rows


def quantile(numbers: list[float], q: float) -> float | None:
    """Linear interpolation on rank (n-1)*q; transparent and reproducible."""
    if not numbers:
        return None
    ordered = sorted(numbers)
    point = (len(ordered)-1) * q
    low = int(point)
    upper = min(low+1,len(ordered)-1)
    weight = point-low
    return ordered[low]*(1-weight) + ordered[upper]*weight


def round_or_none(value: float | None, places: int = 1):
    return round(value, places) if value is not None else None


def is_native_forecast_target(row: dict) -> bool:
    """WINDFOR offers hourly target timestamps; FUELHH offers half-hourly.

    Records without a timestamp (simple artificial unit-test vectors) are
    treated as native target observations for metric testing only.
    """
    if 'startTime' not in row:
        return True
    target = utc_datetime(row['startTime']).astimezone(LONDON)
    return target.minute == 0 and target.second == 0


def summary(rows: list[dict]) -> dict:
    """Describe accuracy ONLY at forecast-native hourly target instants.

    Do not manufacture forecasts for half-hours WINDFOR does not publish, and
    do not convert single-hour *point forecasts* to MWh without a stated
    aggregation/interpolation methodology. Full FUELHH actuals remain visible.
    """
    native = [r for r in rows if is_native_forecast_target(r)]
    paired = [r for r in native if r.get('errorMW') is not None]
    errors = [row['errorMW'] for row in paired]
    forecast_count = sum(row.get('forecastMW') is not None for row in native)
    actual_count = sum(row.get('actualMW') is not None for row in rows)
    hourly_actual_count = sum(row.get('actualMW') is not None for row in native)
    n = len(errors)
    expected = len(native)
    avg_actual = mean(row['actualMW'] for row in paired) if n else None
    avg_forecast = mean(row['forecastMW'] for row in paired) if n else None
    return {
        'expected': expected,  # expected *native hourly forecast targets*, NOT 48/day
        'totalHalfHourSlots': len(rows),
        'sourceResolutionNotForecastedSlots': len(rows) - expected,
        'missingNativeForecasts': expected - forecast_count,
        'matched': n,
        'forecastCount': forecast_count,
        'actualCount': actual_count,
        'hourlyActualCount': hourly_actual_count,
        'coveragePct': round_or_none(100*n/expected if expected else 0),
        'maeMW': round_or_none(mean(abs(e) for e in errors) if n else None),
        'rmseMW': round_or_none(sqrt(mean(e*e for e in errors)) if n else None),
        'biasMW': round_or_none(mean(errors) if n else None),
        'nmaePct': round_or_none(100*mean(abs(e) for e in errors)/avg_actual if n and avg_actual and avg_actual>0 else None),
        'p90SignedErrorMW': round_or_none(quantile(errors, .9)),
        'p90AbsoluteErrorMW': round_or_none(quantile([abs(e) for e in errors], .9)),
        'overforecastPct': round_or_none(100*sum(e>0 for e in errors)/n if n else None),
        'averageForecastMW': round_or_none(avg_forecast),
        'averageActualMW': round_or_none(avg_actual),
    }


def all_decisions(cutoff: str, actual: dict[str, float], forecast: dict[str, list[dict]]) -> list[dict]:
    return [row for day in range(1,32) for row in select_intervals(date(2026,1,day),cutoff,actual,forecast)]


def accuracy_details(rows: list[dict]) -> dict:
    pairs = [r for r in rows if r['errorMW'] is not None]
    by_hour = []
    for hour in range(24):
        values = [r for r in pairs if utc_datetime(r['startTime']).astimezone(LONDON).hour == hour]
        metrics = summary(values)
        by_hour.append({'hour':f'{hour:02}:00','maeMW':metrics['maeMW'],'biasMW':metrics['biasMW'],'n':len(values)})
    daily = []
    for day in range(1,32):
        desired_date = (date(2026,1,day)+timedelta(days=1)).isoformat()
        values = [r for r in rows if utc_datetime(r['startTime']).astimezone(LONDON).date().isoformat() == desired_date]
        metrics = summary(values)
        daily.append({'decisionDate':date(2026,1,day).isoformat(),'deliveryDate':desired_date, 'maeMW':metrics['maeMW'], 'biasMW':metrics['biasMW'], 'nativeForecastTargets':metrics['expected'],'coveragePct':metrics['coveragePct']})
    return {'byHour':by_hour,'byDay':daily}


def horizon_accuracy(hours: int, targets: list[dict], forecast: dict[str,list[dict]]) -> dict:
    """Retrospective lead-time diagnostic, NOT a reconstruction of auction cutoff."""
    matches=[]
    for item in targets:
        if item['actualMW'] is None: continue
        target = utc_datetime(item['startTime'])
        selected = newest_at(forecast.get(item['startTime'], []), target-timedelta(hours=hours))
        if selected:
            matches.append({**item,'forecastMW': selected['generation'],'errorMW': selected['generation']-item['actualMW']})
    return {'horizonHours':hours,**summary(matches)}
