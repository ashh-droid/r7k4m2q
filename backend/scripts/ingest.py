"""Acquire complete 2026-Jan decision history from ONLY the two required Elexon datasets.

Run from the repo root:
  python backend/scripts/ingest.py

Requires an Internet connection. API page ranges are intentionally conservative; retries
are bounded. On any failed request, the existing snapshot is left untouched.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import logging
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_OUT=ROOT/'data'/'processed'
BASE='https://data.elexon.co.uk/bmrs/api/v1/datasets'
LOG=logging.getLogger('elexon.ingest')


def day_windows(start: date, end_exclusive: date):
    current=start
    while current<end_exclusive:
        following=current+timedelta(days=1)
        yield current,following
        current=following


def get_stream(client:httpx.Client,path:str,params:dict,attempts=4):
    for count in range(attempts):
        try:
            response=client.get(f'{BASE}/{path}/stream',params=params)
            if response.status_code in (429,500,502,503,504) and count<attempts-1:
                pause=min(15,2**count)
                LOG.warning('Temporary Elexon %s for %s; retry after %ss',response.status_code,path,pause)
                time.sleep(pause)
                continue
            response.raise_for_status()
            rows=response.json()
            if isinstance(rows,dict) and isinstance(rows.get('data'),list):rows=rows['data']
            if not isinstance(rows,list): raise ValueError(f'Expected list for {path}, received {type(rows)}')
            return rows
        except (httpx.TimeoutException,httpx.ConnectError) as exc:
            if count>=attempts-1:raise RuntimeError(f'Elexon {path} connection failed: {exc}') from exc
            time.sleep(min(15,2**count))
    raise RuntimeError('No successful response')


def iso(value):
    from datetime import datetime
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f'Elexon timestamp is timezone naive: {value}')
    return parsed.astimezone(timezone.utc).isoformat().replace('+00:00','Z')


def wind_actuals(client):
    by_target={}
    raw_count=0
    collisions=0
    # FUELHH settlementDateTo is inclusive: request one day, avoiding overlap.
    for current,following in day_windows(date(2026,1,2),date(2026,2,2)):
        rows=get_stream(client,'FUELHH',{
            'settlementDateFrom':current.isoformat(),
            'settlementDateTo':current.isoformat(),
            'fuelType':'WIND'
        })
        LOG.info('FUELHH %s: %s records',current,len(rows))
        raw_count+=len(rows)
        for row in rows:
            if row.get('fuelType')!='WIND': continue
            start=iso(row['startTime'])
            # Some APIs use inclusive end filters. Filter by target UTC datetime for Jan dates.
            target=datetime.fromisoformat(start.replace('Z','+00:00'))
            if not datetime(2026,1,2,tzinfo=timezone.utc)<=target<datetime(2026,2,2,tzinfo=timezone.utc):continue
            if target.minute not in (0,30) or target.second!=0: continue
            value=float(row['generation'])
            if value<0: raise ValueError(f'Negative actual wind generation at {start}')
            if start in by_target:
                collisions+=1
                # FUELHH may repeat/revise intervals. Prefer latest publication/revision if provided;
                # otherwise retain last occurrence but report the ambiguity in metadata.
                old=by_target[start]
                rev=row.get('documentRevisionNumber') or 0
                pub=row.get('publishTime','')
                if (str(pub),int(rev)) >= (old['published'],old['revision']):
                    by_target[start]={'startTime':start,'generation':value,'published':str(pub),'revision':int(rev)}
            else:by_target[start]={'startTime':start,'generation':value,'published':str(row.get('publishTime','')),'revision':int(row.get('documentRevisionNumber') or 0)}
    return list(by_target.values()),{'retrievedRecords':raw_count,'duplicateTargetRows':collisions,'dedupedRecords':len(by_target)}


def wind_forecasts(client):
    latest={}
    raw_count=0
    collisions=0
    # Publication filter includes late December, for decisions on Jan 1.
    for current,following in day_windows(date(2025,12,28),date(2026,2,1)):
        rows=get_stream(client,'WINDFOR',{
            'publishDateTimeFrom':current.isoformat()+'T00:00:00Z',
            'publishDateTimeTo':following.isoformat()+'T00:00:00Z',
        })
        raw_count+=len(rows)
        LOG.info('WINDFOR publication %s: %s records',current,len(rows))
        for row in rows:
            start=iso(row['startTime'])
            publish=iso(row['publishTime'])
            target=datetime.fromisoformat(start.replace('Z','+00:00'))
            if not datetime(2026,1,2,tzinfo=timezone.utc)<=target<datetime(2026,2,2,tzinfo=timezone.utc):continue
            if target.minute not in (0,30) or target.second!=0: continue
            value=float(row['generation'])
            if value<0: raise ValueError(f'Negative forecast generation at {start}')
            key=(start,publish)
            rev=int(row.get('documentRevisionNumber') or 0)
            if key in latest:collisions+=1
            if key not in latest or rev>=latest[key]['revision']:
                latest[key]={'startTime':start,'publishTime':publish,'generation':value,'revision':rev}
    return list(latest.values()),{'retrievedRecords':raw_count,'duplicateTargetPublicationRows':collisions,'dedupedRecords':len(latest)}


def atomic_csv(path:Path,columns,rows):
    temp=path.with_suffix('.part')
    with temp.open('w',newline='',encoding='utf-8') as file:
        writer=csv.DictWriter(file,fieldnames=columns,extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def main():
    parser=argparse.ArgumentParser(description='Build a real Elexon snapshot for Jan 2026 decision days')
    parser.add_argument('--out',type=Path,default=DEFAULT_OUT)
    args=parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s')
    with httpx.Client(timeout=httpx.Timeout(35.0,connect=15.0),follow_redirects=True,headers={'Accept':'application/json','User-Agent':'Gate-research-pilot/1.0'}) as client:
        actual,actual_q=wind_actuals(client)
        forecast,forecast_q=wind_forecasts(client)
    if len(actual)<1000 or len(forecast)<1000:
        raise RuntimeError(f'Abnormally few observations: {len(actual)} actual, {len(forecast)} forecast. Refusing to replace snapshot.')
    out=args.out
    out.mkdir(parents=True,exist_ok=True)
    actual.sort(key=lambda r:r['startTime'])
    forecast.sort(key=lambda r:(r['startTime'],r['publishTime']))
    atomic_csv(out/'actuals.csv',['startTime','generation'],actual)
    atomic_csv(out/'forecasts.csv',['startTime','publishTime','generation'],forecast)
    sha={f:hashlib.sha256((out/f).read_bytes()).hexdigest() for f in ['actuals.csv','forecasts.csv']}
    metadata={
        'source':'ELEXON_FUELHH_WINDFOR','retrievedAtUTC':datetime.now(timezone.utc).isoformat(),
        'decisionDays':['2026-01-01','2026-01-31'],
        'deliveryDays':['2026-01-02','2026-02-01'],
        'forecastPublicationSearch':['2025-12-28','2026-02-01 exclusive'],
        'actualQuality':actual_q,'forecastQuality':forecast_q,
        'actualRows':len(actual),'forecastRows':len(forecast),
        'sha256':sha,'sourceEndpoints':[f'{BASE}/FUELHH/stream',f'{BASE}/WINDFOR/stream'],
        'notes':'Actual revisions retained by newest available revision where possible; verify FUELHH/WINDFOR scope equivalence separately. All values in MW.'
    }
    (out/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    LOG.info('Success: %s actual periods, %s forecast records. Saved to %s',len(actual),len(forecast),out)
    return 0

if __name__=='__main__':
    sys.exit(main())
