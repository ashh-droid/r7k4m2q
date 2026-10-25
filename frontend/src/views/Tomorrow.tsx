import { useEffect, useState } from 'react';
import { getRevisions } from '../api';
import { exportDayCsv } from '../export';
import { DayChart } from '../components/DayChart';
import { DayNav } from '../components/DayNav';
import { Headline } from '../components/Headline';
import { HourReadout, HourStrip } from '../components/HourStrip';
import { RevisionTrail } from '../components/RevisionTrail';
import { gw, hourWindows } from '../format';
import type { Day, Month, Revisions } from '../types';

type Props = {
  day: Day | null;
  month: Month | null;
  date: string;
  range: [string, string];
  loading: boolean;
  error: string | null;
  onDate: (date: string) => void;
  onRetry: () => void;
};

function Hindsight({ day }: { day: Day }) {
  const h = day.headline;
  if (h.hoursCompared === 0) {
    return <p className="hindsight">Outturn averaged {gw(h.actualMW)} GW. No adjusted interval was available for this early date.</p>;
  }
  const below = hourWindows(h.hoursBelow);
  const above = hourWindows(h.hoursAbove);
  return (
    <p className="hindsight">
      Outturn averaged {gw(h.actualMW)} GW. It landed inside the range in {h.hoursInRange} of {h.hoursCompared} hours
      {below && <>, fell below the floor {below}</>}
      {above && (
        <>
          {below ? ' and' : ','} rose above the range {above}
        </>
      )}
      .
    </p>
  );
}

export function Tomorrow({ day, month, date, range, loading, error, onDate, onRetry }: Props) {
  const [revealed, setRevealed] = useState(false);
  const [hovered, setHovered] = useState<number | null>(null);
  const [selected, setSelected] = useState(7);
  const [trail, setTrail] = useState<Revisions | null>(null);

  // A new day starts with hindsight hidden, so the reveal can be replayed.
  useEffect(() => setRevealed(false), [date, day?.auction.id]);

  useEffect(() => {
    if (!day) { setTrail(null); return; }
    setTrail(null);
    const ac = new AbortController();
    getRevisions(day.hours[selected].startTime, day.auction.id, ac.signal)
      .then(setTrail)
      .catch((e) => e.name !== 'AbortError' && setTrail(null));
    return () => ac.abort();
  }, [day, selected]);

  const focusHour = hovered ?? selected;

  return (
    <div className="tomorrow">
      <DayNav date={date} range={range} month={month} onChange={onDate} />

      {error && (
        <div className="notice" role="alert">
          <p>{error}</p>
          <button className="button" onClick={onRetry}>
            Try again
          </button>
        </div>
      )}

      {day && !error && (
        <div className={loading ? 'is-loading' : ''} aria-busy={loading}>
          <Headline day={day} />

          <section className="chart-block" aria-label="The day, hour by hour">
            <div className="chart-block__bar">
              <ul className="legend">
                <li>
                  <svg width="28" height="10" aria-hidden="true">
                    <line x1="0" y1="5" x2="28" y2="5" className="key-windfor" />
                  </svg>
                  WINDFOR as published
                </li>
                <li>
                  <svg width="28" height="12" aria-hidden="true">
                    <rect width="28" height="12" className="key-band" />
                    <line x1="0" y1="6" x2="28" y2="6" className="key-plan" />
                  </svg>
                  Trial adjustment and historical 10th–90th percentile interval
                </li>
                <li className={revealed ? '' : 'legend__off'}>
                  <svg width="28" height="10" aria-hidden="true">
                    <line x1="0" y1="5" x2="28" y2="5" className="key-actual" />
                  </svg>
                  What happened
                </li>
              </ul>
              <div className="chart-actions">
                <button className="button button--download" onClick={() => exportDayCsv(day)}>
                  Export CSV
                </button>
                <button className="button button--reveal" aria-pressed={revealed} onClick={() => setRevealed((r) => !r)}>
                  {revealed ? 'Hide what happened' : 'Show what happened'}
                </button>
              </div>
            </div>

            <div className="chart-scroll">
              <DayChart day={day} revealed={revealed} hovered={hovered} onHover={setHovered} onPick={setSelected} />
            </div>
            <HourReadout hour={day.hours[focusHour]} revealed={revealed} />
            {revealed && <Hindsight key={day.deliveryDate} day={day} />}
          </section>

          <section className="hours-block">
            <h2>A lower reference, hour by hour</h2>
            <p className="muted">
              Hourly lower reference in GW, computed from earlier complete days. This is an exploratory estimate,
              not a guaranteed minimum. Select an hour to inspect its publication history.
            </p>
            <HourStrip
              hours={day.hours}
              selected={selected}
              hovered={hovered}
              revealed={revealed}
              onSelect={setSelected}
              onHover={setHovered}
            />
            {!day.calibration.available && (
              <p className="history-note">No adjustment has been calculated for this early date. The official
                WINDFOR forecast and publication history remain available.</p>
            )}
            <p className="energy">
              Under an hourly-average power assumption: WINDFOR {day.energy.windforGWh?.toFixed(0) ?? '–'} GWh
              {day.calibration.available && <>, trial-adjusted {day.energy.planGWh?.toFixed(0) ?? '–'} GWh,
                lower reference {day.energy.floorGWh?.toFixed(0) ?? '–'} GWh</>}
              {revealed && <>, actual half-hourly energy {day.energy.actualGWh?.toFixed(0) ?? '–'} GWh</>}.
            </p>
          </section>

          {trail && trail.startTime === day.hours[selected].startTime && (
            <section className="trail-block">
              <h2>How the {trail.hour} forecast moved</h2>
              <RevisionTrail data={trail} revealed={revealed} />
            </section>
          )}
        </div>
      )}
    </div>
  );
}
