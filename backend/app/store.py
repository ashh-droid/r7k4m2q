"""Load an immutable CSV snapshot once per backend process; no live API in HTTP handlers."""
from __future__ import annotations
import csv
import json
import os
from functools import lru_cache
from pathlib import Path
from .analytics import forecast_index, utc_datetime, zulu

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_DIR=ROOT/'data'/'processed'


def current_path():
    return Path(os.getenv('WIND_DATA_DIR',str(DEFAULT_DIR))).resolve()


@lru_cache(maxsize=4)
def load_snapshot(path_str: str):
    folder=Path(path_str)
    metadata_path=folder/'metadata.json'
    actual_file=folder/'actuals.csv'
    fc_file=folder/'forecasts.csv'
    if not (metadata_path.exists() and actual_file.exists() and fc_file.exists()):
        return {'available':False,'reason':'Real Elexon snapshot not imported. Run the ingestion command from README.', 'source':'unavailable','actual':{},'forecast':{},'metadata':{}}
    metadata=json.loads(metadata_path.read_text(encoding='utf-8'))
    source=metadata.get('source','unverified')
    if source != 'ELEXON_FUELHH_WINDFOR':
        return {'available':False,'reason':'Only validated Elexon snapshot metadata is accepted.', 'source':source,'actual':{},'forecast':{},'metadata':metadata}
    actual={}
    with actual_file.open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            actual[zulu(utc_datetime(row['startTime']))]=float(row['generation'])
    forecast_rows=[]
    with fc_file.open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            forecast_rows.append({'startTime':zulu(utc_datetime(row['startTime'])),'publishTime':zulu(utc_datetime(row['publishTime'])),'generation':float(row['generation'])})
    return {'available':bool(actual and forecast_rows),'reason':None if actual and forecast_rows else 'Snapshot files contain no usable pairs.','source':source,'actual':actual,'forecast':forecast_index(forecast_rows),'metadata':metadata}


def get_store():
    return load_snapshot(str(current_path()))
