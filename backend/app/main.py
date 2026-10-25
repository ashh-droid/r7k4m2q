"""Read-only JSON API over a fixed Elexon snapshot (FUELHH wind + WINDFOR)."""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta
from math import sqrt
from statistics import mean, median

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .analytics import LONDON, newest_at, utc_datetime, zulu
from .planning import (
    AUCTIONS, DEFAULT_AUCTION, FIRST_DELIVERY, LAST_DELIVERY, LEVELS, PUBLICATION_LAG,
    delivery_days, gate_closure, gwh, level_of, month_rows, planned_day, validation,
)
from .store import get_store
from .schemas import HealthResponse, MetaResponse, DayResponse, MonthResponse, RevisionResponse

app = FastAPI(
    title='Day-ahead wind API',
    version='2.0.0',
    description='Decision-time WINDFOR forecasts, exploratory chronology-safe adjustment and historical range, '
                'against FUELHH wind outturn. January 2026 delivery days.',
    docs_url='/api/docs',
    openapi_url='/api/openapi.json',
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://localhost:3000'],
    allow_methods=['GET'],
    allow_headers=['*'],
)


def ready_store() -> dict:
    store = get_store()
    if not store['available']:
        raise HTTPException(503, detail=store['reason'])
    return store


def check_auction(auction: str) -> str:
    if auction not in AUCTIONS:
        raise HTTPException(422, f'auction must be one of: {", ".join(AUCTIONS)}')
    return auction


def check_day(day: date) -> date:
    if not FIRST_DELIVERY <= day <= LAST_DELIVERY:
        raise HTTPException(422, 'delivery_date must be between 2026-01-02 and 2026-02-01')
    return day


def avg(values) -> float | None:
    vals = [v for v in values if v is not None]
    return round(mean(vals)) if vals else None


def mw(value: float | None) -> int | None:
    return round(value) if value is not None else None


def hour_out(r: dict) -> dict:
    return {
        'startTime': r['startTime'], 'hour': r['hour'],
        'windfor': mw(r['windfor']), 'plan': mw(r['plan']), 'low': mw(r['low']), 'high': mw(r['high']),
        'actual': mw(r['actual']), 'publishTime': r['publishTime'], 'leadHours': r['leadHours'],
    }


@app.get('/api/health', response_model=HealthResponse)
def health():
    store = get_store()
    return {'status': 'ok', 'dataReady': store['available'], 'source': store['source']}


@app.get('/api/meta', response_model=MetaResponse)
def meta():
    store = get_store()
    md = store['metadata']
    return {
        'dataReady': store['available'],
        'source': store['source'],
        'retrievedAtUTC': md.get('retrievedAtUTC'),
        'actualRows': md.get('actualRows'),
        'forecastRows': md.get('forecastRows'),
        'deliveryRange': [FIRST_DELIVERY.isoformat(), LAST_DELIVERY.isoformat()],
        'defaultDelivery': '2026-01-21',
        'publicationLagMinutes': int(PUBLICATION_LAG.total_seconds() // 60),
        'auctions': [{'id': k, **v} for k, v in AUCTIONS.items()],
        'defaultAuction': DEFAULT_AUCTION,
    }


@app.get('/api/day', response_model=DayResponse)
def day(delivery_date: date = Query(date(2026, 1, 21)), auction: str = DEFAULT_AUCTION):
    check_day(delivery_date)
    check_auction(auction)
    store = ready_store()
    rows, _, training_days = planned_day(delivery_date, auction, store)

    midnight = datetime.combine(delivery_date, time.min, LONDON)
    halves = []
    for h in range(48):
        key = zulu(midnight + timedelta(minutes=30 * h))
        halves.append({'startTime': key, 'actual': store['actual'].get(key)})

    paired = [r for r in rows if r['plan'] is not None and r['actual'] is not None]
    inside = [r for r in paired if r['low'] <= r['actual'] <= r['high']]
    levels = Counter(r['level'] for r in rows if r['level'] is not None)
    runs = sorted({r['publishTime'] for r in rows if r['publishTime']})

    return {
        'deliveryDate': delivery_date.isoformat(),
        'auction': {'id': auction, **AUCTIONS[auction]},
        'gateClosure': zulu(gate_closure(delivery_date, auction)),
        'forecastRun': runs[-1] if runs else None,
        'forecastRunCount': len(runs),
        'calibration': {
            'available': training_days >= 7,
            'trainingDays': training_days,
            'method': 'earlier_completed_delivery_days_only',
            'note': 'Exploratory adjustment; FUELHH and WINDFOR populations may differ.',
        },
        'headline': {
            'windforMW': avg(r['windfor'] for r in rows),
            'planMW': avg(r['plan'] for r in rows),
            'floorMW': avg(r['low'] for r in rows),
            'correctionMW': avg(r['windfor'] - r['plan'] for r in rows if r['plan'] is not None),
            'actualMW': avg(r['actual'] for r in rows),
            'level': LEVELS[levels.most_common(1)[0][0]][0] if levels else None,
            'hoursCompared': len(paired),
            'hoursInRange': len(inside),
            'hoursBelow': [r['hour'] for r in paired if r['actual'] < r['low']],
            'hoursAbove': [r['hour'] for r in paired if r['actual'] > r['high']],
        },
        'energy': {
            'windforGWh': gwh(r['windfor'] for r in rows),
            'planGWh': gwh(r['plan'] for r in rows),
            'floorGWh': gwh(r['low'] for r in rows),
            'actualGWh': gwh(h['actual'] * 0.5 for h in halves if h['actual'] is not None),
        },
        'hours': [hour_out(r) for r in rows],
        'halfHourActuals': halves,
    }


_MONTH: dict[tuple[str, int], dict] = {}


@app.get('/api/month', response_model=MonthResponse)
def month(auction: str = DEFAULT_AUCTION):
    check_auction(auction)
    store = ready_store()
    key = (auction, id(store))
    if key in _MONTH:
        return _MONTH[key]
    by_day = month_rows(auction, store)
    paired = [r for rows in by_day.values() for r in rows if r['error'] is not None]
    errors = [r['error'] for r in paired]

    days = []
    for d, rows in by_day.items():
        e = [r['error'] for r in rows if r['error'] is not None]
        days.append({'deliveryDate': d.isoformat(), 'biasMW': avg(e), 'maeMW': avg(abs(x) for x in e)})

    levels = []
    for i, (label, lo, hi) in enumerate(LEVELS):
        e = [r['error'] for r in paired if level_of(r['windfor']) == i]
        levels.append({'label': label, 'n': len(e), 'biasMW': avg(e), 'maeMW': avg(abs(x) for x in e)})

    horizons = []
    for h in (6, 12, 18, 24, 30, 36, 42, 48):
        e = []
        for rows in by_day.values():
            for r in rows:
                if r['actual'] is None:
                    continue
                picked = newest_at(store['forecast'].get(r['startTime'], []),
                                   utc_datetime(r['startTime']) - timedelta(hours=h))
                if picked:
                    e.append(picked['generation'] - r['actual'])
        horizons.append({'hours': h, 'maeMW': avg(abs(x) for x in e), 'n': len(e)})

    leads = []
    for a in AUCTIONS:
        lh = [r['leadHours'] for rows in month_rows(a, store).values() for r in rows if r['leadHours'] is not None]
        leads.append({'id': a, **AUCTIONS[a], 'medianLeadHours': round(median(lh), 1)})

    by_hour = []
    for h in range(24):
        e = [r['error'] for r in paired if int(r['hour'][:2]) == h]
        by_hour.append({'hour': f'{h:02}:00', 'maeMW': avg(abs(x) for x in e), 'biasMW': avg(e)})

    result = {
        'auction': {'id': auction, **AUCTIONS[auction]},
        'summary': {
            'n': len(errors),
            'biasMW': avg(errors),
            'maeMW': avg(abs(e) for e in errors),
            'rmseMW': round(sqrt(mean(e * e for e in errors))),
            'overPct': round(100 * sum(e > 0 for e in errors) / len(errors)),
        },
        'validation': validation(auction, store),
        'levels': levels,
        'days': days,
        'horizons': horizons,
        'auctionLeads': leads,
        'byHour': by_hour,
        'scatter': [[round(r['windfor']), round(r['error'])] for r in paired],
    }
    _MONTH[key] = result
    return result


@app.get('/api/revisions', response_model=RevisionResponse)
def revisions(start_time: str = Query(...), auction: str = DEFAULT_AUCTION):
    check_auction(auction)
    store = ready_store()
    try:
        target = utc_datetime(start_time)
    except ValueError as exc:
        raise HTTPException(422, 'start_time must be an ISO datetime with a timezone') from exc
    local = target.astimezone(LONDON)
    if local.minute or local.second:
        raise HTTPException(422, 'WINDFOR forecasts are hourly; start_time must be on the hour')
    check_day(local.date())
    gate = gate_closure(local.date(), auction)
    usable_at = gate - PUBLICATION_LAG
    key = zulu(target)
    records = store['forecast'].get(key, [])
    selected = newest_at(records, usable_at)
    versions = []
    for r in records:
        pub = utc_datetime(r['publishTime'])
        status = 'before_gate' if pub <= usable_at else 'after_delivery' if pub >= target else 'after_gate'
        versions.append({'publishTime': r['publishTime'], 'mw': r['generation'], 'status': status,
                         'selected': selected is not None and r['publishTime'] == selected['publishTime']})
    return {'startTime': key, 'hour': local.strftime('%H:%M'), 'gateClosure': zulu(gate),
            'actual': store['actual'].get(key), 'versions': versions}
