import { useEffect, useState } from 'react';
import { getDay, getMeta, getMonth } from './api';
import type { Day, Meta, Month } from './types';
import { Method } from './views/Method';
import { MonthView } from './views/MonthView';
import { Tomorrow } from './views/Tomorrow';

type View = 'day' | 'month' | 'method';
const VIEWS: { id: View; label: string }[] = [
  { id: 'day', label: 'The day' },
  { id: 'month', label: 'The month' },
  { id: 'method', label: 'How it works' },
];

const viewFromHash = (): View => {
  const v = window.location.hash.replace('#/', '');
  return v === 'month' || v === 'method' ? v : 'day';
};

export default function App() {
  const [view, setView] = useState<View>(viewFromHash);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [auction, setAuction] = useState('epex-hourly');
  const [date, setDate] = useState('2026-01-21');
  const [day, setDay] = useState<Day | null>(null);
  const [month, setMonth] = useState<Month | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const onHash = () => setView(viewFromHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  useEffect(() => {
    getMeta()
      .then((m) => {
        setMeta(m);
        setAuction(m.defaultAuction);
        setDate(m.defaultDelivery);
      })
      .catch((e) => setError(`Could not reach the API. ${e.message}`));
  }, [attempt]);

  useEffect(() => {
    if (!meta?.dataReady) return;
    const ac = new AbortController();
    setLoading(true);
    setError(null);
    setDay(null); // never show a prior delivery day's data under new controls
    getDay(date, auction, ac.signal)
      .then(setDay)
      .catch((e) => {
        if (e.name === 'AbortError') return;
        setDay(null); // never leave another day's numbers on screen
        setError(`Could not load ${date}. ${e.message}`);
      })
      .finally(() => !ac.signal.aborted && setLoading(false));
    return () => ac.abort();
  }, [meta, date, auction, attempt]);

  useEffect(() => {
    if (!meta?.dataReady) return;
    const ac = new AbortController();
    setMonth(null);
    getMonth(auction, ac.signal)
      .then(setMonth)
      .catch((e) => e.name !== 'AbortError' && setMonth(null));
    return () => ac.abort();
  }, [meta, auction]);

  const go = (v: View) => {
    window.location.hash = `#/${v}`;
    setView(v);
  };

  const range = meta?.deliveryRange ?? ['2026-01-02', '2026-02-01'];

  return (
    <div className="app">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <header className="masthead">
        <a className="wordmark" href="#/day" onClick={() => go('day')} aria-label="Gate, day-ahead wind">
          <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
            <path d="M3 20V5M19 20V5M3 8h16M3 13h16" fill="none" stroke="currentColor" strokeWidth="2" />
          </svg>
          Gate
        </a>
        <nav className="views" aria-label="Views">
          {VIEWS.map((v) => (
            <a
              key={v.id}
              href={`#/${v.id}`}
              aria-current={view === v.id ? 'page' : undefined}
              onClick={() => setView(v.id)}
            >
              {v.label}
            </a>
          ))}
        </nav>
        {meta && view !== 'method' && (
          <div className="auctions" role="radiogroup" aria-label="Auction">
            {meta.auctions.map((a) => (
              <button
                key={a.id}
                role="radio"
                aria-checked={auction === a.id}
                className="auction"
                onClick={() => setAuction(a.id)}
              >
                <span className="auction__name">{a.label}</span>
                <span className="auction__time">{a.cutoff}</span>
              </button>
            ))}
          </div>
        )}
      </header>

      <main id="main" className="page">
        {meta && !meta.dataReady && (
          <div className="notice" role="alert">
            <p>The Elexon snapshot is not loaded. Run the ingestion script described in the README, then reload.</p>
          </div>
        )}
        {!meta && error && (
          <div className="notice" role="alert">
            <p>{error}</p>
            <button className="button" onClick={() => setAttempt((n) => n + 1)}>
              Try again
            </button>
          </div>
        )}
        {view === 'day' && meta?.dataReady && (
          <Tomorrow
            day={day}
            month={month}
            date={date}
            range={range}
            loading={loading}
            error={error}
            onDate={setDate}
            onRetry={() => setAttempt((n) => n + 1)}
          />
        )}
        {view === 'month' && meta?.dataReady && (
          <MonthView
            month={month}
            onOpenDay={(d) => {
              setDate(d);
              go('day');
            }}
          />
        )}
        {view === 'method' && <Method meta={meta} />}
      </main>

      <footer className="colophon">
        <p>
          Elexon BMRS · WINDFOR and FUELHH WIND · decisions 1–31 January 2026, delivery 2 January–1 February.
          Historical research pilot. The adjusted estimate is exploratory, not an instruction to purchase electricity.
        </p>
      </footer>
    </div>
  );
}
