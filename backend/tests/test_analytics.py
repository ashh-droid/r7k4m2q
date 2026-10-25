from datetime import date, datetime, timezone
import pytest
from app.analytics import (decision_timestamp, delivery_targets, forecast_index, newest_at,
                           select_intervals, summary, quantile, utc_datetime, zulu, horizon_accuracy)

TARGET='2026-01-16T10:00:00Z'
FC=[
    {'startTime':TARGET,'publishTime':'2026-01-15T07:00:00Z','generation':8000},
    {'startTime':TARGET,'publishTime':'2026-01-15T08:30:00Z','generation':8200},
    {'startTime':TARGET,'publishTime':'2026-01-15T09:01:00Z','generation':9000},
]

def test_no_future_publication_leakage():
    grouped=forecast_index(FC)
    rows=select_intervals(date(2026,1,15),'09:00',{TARGET:7500},grouped)
    row=next(r for r in rows if r['startTime']==TARGET)
    assert row['forecastMW']==8200
    assert row['publishTime']=='2026-01-15T08:30:00Z'
    assert row['errorMW']==700
    assert len(rows)==48


def test_cutoff_is_inclusive():
    assert newest_at(forecast_index(FC)[TARGET],utc_datetime('2026-01-15T08:30:00Z'))['generation']==8200


def test_no_eligible_forecast_is_missing_not_zero():
    rows=select_intervals(date(2026,1,15),'06:00',{TARGET:7500},forecast_index(FC))
    row=next(r for r in rows if r['startTime']==TARGET)
    assert row['forecastMW'] is None
    assert row['errorMW'] is None
    assert row['actualMW']==7500


def test_missing_actual_remains_missing():
    row=next(r for r in select_intervals(date(2026,1,15),'09:00',{},forecast_index(FC)) if r['startTime']==TARGET)
    assert row['errorMW'] is None
    assert row['actualMW'] is None


def test_summary_known_values():
    rows=[{'forecastMW':1000,'actualMW':800,'errorMW':200},
          {'forecastMW':700,'actualMW':900,'errorMW':-200}]
    s=summary(rows)
    assert s['maeMW']==200
    assert s['rmseMW']==200
    assert s['biasMW']==0
    assert s['averageForecastMW']==850
    assert s['averageActualMW']==850
    assert s['overforecastPct']==50


def test_horizon_is_distinct_from_day_ahead_cutoff():
    records=forecast_index(FC)
    targets=[{'startTime':TARGET,'actualMW':8000,'forecastMW':None,'errorMW':None}]
    s=horizon_accuracy(24,targets,records)
    assert s['matched']==1
    assert s['biasMW']==1000  # horizon view uses 09:01 publication, not the 09:00 purchase cutoff


def test_quantiles_and_empty_sample():
    assert quantile([0,10,20,30,40],.9)==36
    assert quantile([],0.9) is None
    assert summary([])['maeMW'] is None
    assert summary([])['coveragePct']==0


def test_january_boundary_and_utc():
    assert len(delivery_targets(date(2026,1,1)))==48
    assert delivery_targets(date(2026,1,1))[0].isoformat().startswith('2026-01-02')
    assert delivery_targets(date(2026,1,31))[-1].isoformat().startswith('2026-02-01T23:30')
    assert decision_timestamp(date(2026,1,31),'09:00').hour==9
    assert zulu(utc_datetime('2026-01-15T14:30:00+05:30'))=='2026-01-15T09:00:00Z'
    with pytest.raises(ValueError):utc_datetime('2026-01-15T09:00:00')


def test_cutoff_validation():
    from app.analytics import parse_cutoff
    for value in ['nottime','24:00','09:00:01','09:00+05:30', '9:00', '09:0', '09:00:00', '09:00Z']:
        with pytest.raises(ValueError):parse_cutoff(value)


def test_valid_exact_cutoff_format():
    from app.analytics import parse_cutoff
    assert parse_cutoff("00:00").strftime("%H:%M") == "00:00"
    assert parse_cutoff("09:00").strftime("%H:%M") == "09:00"
    assert parse_cutoff("23:59").strftime("%H:%M") == "23:59"


def test_hourly_source_resolution_not_missing_forecasts():
    from datetime import timedelta
    start=utc_datetime('2026-01-16T00:00:00Z')
    rows=[]
    for i in range(48):
        stamp=zulu(start+timedelta(minutes=30*i))
        is_hourly=i%2==0
        rows.append({'startTime':stamp,'actualMW':8000,
                     'forecastMW':8200 if is_hourly else None,
                     'errorMW':200 if is_hourly else None})
    result=summary(rows)
    assert result['totalHalfHourSlots']==48
    assert result['expected']==24
    assert result['matched']==24
    assert result['coveragePct']==100.0
    assert result['missingNativeForecasts']==0
    assert result['sourceResolutionNotForecastedSlots']==24
    assert result['actualCount']==48
    assert result['maeMW']==200
    assert result['averageForecastMW']==8200
    assert 'forecastMWhPaired' not in result


def test_hourly_missing_publication_reduces_native_coverage():
    from datetime import timedelta
    start=utc_datetime('2026-01-16T00:00:00Z')
    rows=[]
    for i in range(48):
        stamp=zulu(start+timedelta(minutes=30*i))
        is_available=i%2==0 and i!=8
        rows.append({'startTime':stamp,'actualMW':8000,
                     'forecastMW':8200 if is_available else None,
                     'errorMW':200 if is_available else None})
    result=summary(rows)
    assert result['expected']==24
    assert result['matched']==23
    assert result['missingNativeForecasts']==1
    assert result['coveragePct']==95.8
