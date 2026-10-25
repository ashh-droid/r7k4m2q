"""Print a transparent audit of the included Elexon January snapshot."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.planning import AUCTIONS, month_rows, validation  # noqa: E402
from app.store import get_store  # noqa: E402


def main() -> int:
    store = get_store()
    if not store['available'] or store['source'] != 'ELEXON_FUELHH_WINDFOR':
        print('Verified Elexon snapshot unavailable:', store['reason'])
        return 2

    print('Source:', store['source'])
    print('Retrieved at:', store['metadata'].get('retrievedAtUTC', 'unspecified'))
    print('FUELHH actual half-hour targets:', len(store['actual']))
    print('WINDFOR native hourly target timestamps:', len(store['forecast']))
    print('WINDFOR target/publication versions:', sum(map(len, store['forecast'].values())))
    print('\nAuction-by-auction differences at the gate (forecast minus outturn):')
    for key, auction in AUCTIONS.items():
        rows = [r for daily in month_rows(key, store).values() for r in daily if r['error'] is not None]
        errors = [r['error'] for r in rows]
        vf = validation(key, store)
        print(
            f"{auction['label']} {auction['cutoff']}: {len(rows)} matched targets, "
            f"MAE {mean(abs(e) for e in errors):,.0f} MW, bias {mean(errors):+,.0f} MW"
        )
        print(
            f"  Walk-forward: n={vf['n']}, raw MAE={vf['rawMaeMW']} MW, "
            f"trial-adjusted MAE={vf['levelMaeMW']} MW, "
            f"lower-reference coverage={vf['aboveFloorPct']}%"
        )

    print('\nSource metadata counts (historical snapshot, not a fresh retrieval):')
    print(json.dumps(store['metadata'].get('actualQuality', {}), indent=2))
    print('Note: the original snapshot was collected using overlapping inclusive API windows.')
    print('The current ingestion script queries one settlement date at a time.')
    print('Dataset population comparability remains an open limitation.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
