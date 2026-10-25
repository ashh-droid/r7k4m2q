"""Endpoint tests against the committed January 2026 Elexon snapshot."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.analytics import utc_datetime
from app.main import app
from app.planning import AUCTIONS, PUBLICATION_LAG, delivery_days
from app.store import load_snapshot

CLIENT = TestClient(app)


@pytest.fixture(autouse=True)
def real_snapshot(monkeypatch):
    monkeypatch.delenv('WIND_DATA_DIR', raising=False)
    load_snapshot.cache_clear()
    if not CLIENT.get('/api/health').json()['dataReady']:
        pytest.skip('real snapshot not present')


@pytest.mark.parametrize('auction', list(AUCTIONS))
def test_no_forecast_published_after_gate_on_any_day(auction):
    """The core promise, checked on every hour of every delivery day."""
    for d in delivery_days():
        body = CLIENT.get('/api/day', params={'delivery_date': d.isoformat(), 'auction': auction}).json()
        usable_at = utc_datetime(body['gateClosure']) - PUBLICATION_LAG
        for h in body['hours']:
            assert h['publishTime'] is not None
            assert utc_datetime(h['publishTime']) <= usable_at


def test_day_shape_and_known_values():
    body = CLIENT.get('/api/day', params={'delivery_date': '2026-01-21'}).json()
    assert body['gateClosure'] == '2026-01-20T09:20:00Z'
    assert body['forecastRun'] == '2026-01-20T07:30:00Z'
    assert len(body['hours']) == 24
    assert len(body['halfHourActuals']) == 48
    assert body['headline']['windforMW'] == 19390
    for h in body['hours']:
        assert h['low'] <= h['plan'] <= h['high']


def test_auctions_see_different_runs():
    runs = {a: CLIENT.get('/api/day', params={'delivery_date': '2026-01-21', 'auction': a}).json()['forecastRun']
            for a in AUCTIONS}
    assert runs['epex-hourly'] == '2026-01-20T07:30:00Z'
    assert runs['n2ex-hourly'] == '2026-01-20T09:30:00Z'
    # The 15:30 run lands as the gate shuts, so the 11:30 run is the last usable one.
    assert runs['epex-half-hourly'] == '2026-01-20T11:30:00Z'


def test_month_validation_is_out_of_sample_and_helps():
    v = CLIENT.get('/api/month').json()['validation']
    assert v['method'] == 'chronological_walk_forward'
    assert v['n'] == 552  # 23 held-out days: seven history days, plus exclusion of D-1
    assert v['levelMaeMW'] < v['flatMaeMW'] < v['rawMaeMW']
    assert 70 <= v['insideRangePct'] <= 90
    assert 75 <= v['aboveFloorPct'] <= 95


def test_revisions_only_on_the_hour_and_flags_late_versions():
    assert CLIENT.get('/api/revisions', params={'start_time': '2026-01-21T07:30:00Z'}).status_code == 422
    body = CLIENT.get('/api/revisions', params={'start_time': '2026-01-21T07:00:00Z'}).json()
    statuses = {v['status'] for v in body['versions']}
    assert {'before_gate', 'after_gate'} <= statuses
    assert sum(v['selected'] for v in body['versions']) == 1
    target = utc_datetime(body['startTime'])
    for v in body['versions']:
        if v['status'] == 'after_delivery':
            assert utc_datetime(v['publishTime']) >= target


@pytest.mark.parametrize('url', [
    '/api/day?delivery_date=2026-01-01',
    '/api/day?delivery_date=2026-02-02',
    '/api/day?auction=nordpool',
    '/api/revisions?start_time=2026-01-21T07:00:00',
    '/api/revisions?start_time=2026-03-01T07:00:00Z',
])
def test_bad_input_is_422(url):
    assert CLIENT.get(url).status_code == 422


def test_docs_are_served_under_api():
    assert CLIENT.get('/api/docs').status_code == 200


def test_calibration_uses_only_completed_past_days():
    from datetime import date
    from app.planning import planned_day
    from app.store import get_store
    s = get_store()
    early, fits, count = planned_day(date(2026, 1, 5), 'epex-hourly', s)
    assert count < 7
    assert fits is None
    assert all(h['plan'] is None and h['low'] is None for h in early)
    mature, fits, count = planned_day(date(2026, 1, 21), 'epex-hourly', s)
    assert count == 18  # January 2 to January 19; January 20 is not yet complete at gate
    assert fits is not None
    assert all(h['plan'] is not None for h in mature)


def test_future_outturn_cannot_change_prior_day_calibration():
    from datetime import date
    from copy import deepcopy
    from app.planning import planned_day, _MONTH_CACHE
    from app.store import get_store
    old = get_store()
    s = deepcopy(old)
    # Replace the Jan 25 outturn after the Jan 21 decision, then recalculate.
    rows_before, _, _ = planned_day(date(2026, 1, 21), 'epex-hourly', old)
    s['actual']['2026-01-25T07:00:00Z'] = 999999.0
    _MONTH_CACHE.clear()
    rows_after, _, _ = planned_day(date(2026, 1, 21), 'epex-hourly', s)
    assert [h['plan'] for h in rows_before] == [h['plan'] for h in rows_after]
