import { gw, shortDate } from '../format';
import type { Month } from '../types';

function LevelScatter({ month }: { month: Month }) {
  const W = 1200,
    H = 420;
  const PAD = { left: 64, right: 24, top: 24, bottom: 48 };
  const xMin = 0,
    xMax = 24000,
    yMin = -6000,
    yMax = 9000;
  const x = (v: number) => PAD.left + ((v - xMin) / (xMax - xMin)) * (W - PAD.left - PAD.right);
  const y = (v: number) => PAD.top + (1 - (v - yMin) / (yMax - yMin)) * (H - PAD.top - PAD.bottom);
  const bands = [
    { lo: 0, hi: 10000 },
    { lo: 10000, hi: 14000 },
    { lo: 14000, hi: 24000 },
  ];
  return (
    <svg
      className="scatter"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label="Each January hour: WINDFOR's forecast against how far it missed. The average miss grows with the forecast."
    >
      <g className="axis">
        {[-6000, -3000, 0, 3000, 6000, 9000].map((v) => (
          <g key={v}>
            <line className={v === 0 ? 'axis__zero' : ''} x1={PAD.left} x2={W - PAD.right} y1={y(v)} y2={y(v)} />
            <text x={PAD.left - 10} y={y(v) + 4} textAnchor="end">
              {v > 0 ? `+${gw(v, 0)}` : gw(v, 0)}
            </text>
          </g>
        ))}
        {[0, 4000, 8000, 12000, 16000, 20000, 24000].map((v) => (
          <text key={v} x={x(v)} y={H - 18} textAnchor="middle">
            {gw(v, 0)}
          </text>
        ))}
        <text x={W - PAD.right} y={H - 2} textAnchor="end">
          WINDFOR forecast at the gate, GW
        </text>
        <text x={PAD.left} y={14}>
          Miss, GW (forecast minus outturn)
        </text>
      </g>
      <g className="scatter__dots">
        {month.scatter.map(([f, e], i) => (
          <circle key={i} cx={x(f)} cy={y(e)} r={3} />
        ))}
      </g>
      {month.levels.map((l, i) => (
        <g key={l.label} className="scatter__level" style={{ animationDelay: `${300 + i * 250}ms` }}>
          <line x1={x(bands[i].lo) + 4} x2={x(bands[i].hi) - 4} y1={y(l.biasMW)} y2={y(l.biasMW)} />
          <text x={(x(bands[i].lo) + x(bands[i].hi)) / 2} y={y(l.biasMW) - 12} textAnchor="middle">
            {l.label}: +{gw(l.biasMW)} GW
          </text>
        </g>
      ))}
    </svg>
  );
}

function ValidationBars({ month }: { month: Month }) {
  const v = month.validation;
  const rows = [
    { label: 'WINDFOR as published', mw: v.rawMaeMW, tone: 'raw' },
    { label: 'Minus one average correction', mw: v.flatMaeMW, tone: 'flat' },
    { label: 'Corrected by wind level', mw: v.levelMaeMW, tone: 'level' },
  ];
  // No bar can be scaled if the baseline is missing or zero.
  // A null error represents unavailable validation, not a zero-MW error.
  const baseline = v.rawMaeMW;
  return (
    <div className="vbars">
      {rows.map((r, i) => {
        const percentage =
          r.mw == null || baseline == null || baseline <= 0
            ? 0
            : Math.min(100, Math.max(0, (r.mw / baseline) * 100));
        return (
          <div key={r.label} className="vbars__row">
            <span className="vbars__label">{r.label}</span>
            <span className="vbars__track">
              <span
                className={`vbars__bar vbars__bar--${r.tone}`}
                style={{ width: `${percentage}%`, animationDelay: `${i * 160}ms` }}
              />
            </span>
            <span className="vbars__value">{r.mw == null ? 'Not available' : `${gw(r.mw, 2)} GW`}</span>
          </div>
        );
      })}
    </div>
  );
}

function HorizonChart({ month }: { month: Month }) {
  const W = 1200,
    H = 300;
  const PAD = { left: 64, right: 24, top: 40, bottom: 44 };
  const pts = month.horizons;
  const yMin = Math.floor(Math.min(...pts.map((p) => p.maeMW)) / 500) * 500 - 250;
  const yMax = Math.ceil(Math.max(...pts.map((p) => p.maeMW)) / 500) * 500;
  const x = (h: number) => PAD.left + ((h - 6) / 42) * (W - PAD.left - PAD.right);
  const y = (v: number) => PAD.top + (1 - (v - yMin) / (yMax - yMin)) * (H - PAD.top - PAD.bottom);
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${x(p.hours).toFixed(1)},${y(p.maeMW).toFixed(1)}`).join(' ');
  const at = (h: number) => {
    const j = pts.findIndex((p) => p.hours >= h);
    const a = pts[Math.max(0, j - 1)],
      b = pts[j];
    const t = (h - a.hours) / (b.hours - a.hours || 1);
    return a.maeMW + (b.maeMW - a.maeMW) * t;
  };
  return (
    <svg
      className="horizon"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label="Typical miss by how far ahead the forecast was made, with each auction's usual lead time marked"
    >
      <g className="axis">
        {[yMin + 250, (yMin + yMax) / 2, yMax].map((v) => (
          <g key={v}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(v)} y2={y(v)} />
            <text x={PAD.left - 10} y={y(v) + 4} textAnchor="end">
              {gw(v)}
            </text>
          </g>
        ))}
        {pts.map((p) => (
          <text key={p.hours} x={x(p.hours)} y={H - 18} textAnchor="middle">
            {p.hours} h
          </text>
        ))}
        <text x={W - PAD.right} y={H - 2} textAnchor="end">
          How far ahead of the hour the forecast was made
        </text>
        <text x={PAD.left} y={16}>
          Typical miss, GW
        </text>
      </g>
      <path className="horizon__line" d={d} />
      {month.auctionLeads.map((a, i) => (
        <g key={a.id} className="horizon__auction">
          <circle cx={x(a.medianLeadHours)} cy={y(at(a.medianLeadHours))} r={5} />
          <text x={x(a.medianLeadHours)} y={y(at(a.medianLeadHours)) + [-16, 28, -40][i % 3]} textAnchor="middle">
            {a.label} {a.cutoff}
          </text>
        </g>
      ))}
    </svg>
  );
}

export function MonthView({ month, onOpenDay }: { month: Month | null; onOpenDay: (date: string) => void }) {
  if (!month) return <p className="muted">Loading January…</p>;
  const s = month.summary;
  const v = month.validation;
  const worst = [...month.days].sort((a, b) => (b.maeMW ?? 0) - (a.maeMW ?? 0)).slice(0, 3);
  const byMiss = [...month.byHour].sort((a, b) => b.maeMW - a.maeMW);
  const weakHours = byMiss.slice(0, 3).map((h) => h.hour);
  const bestHours = byMiss
    .slice(-3)
    .reverse()
    .map((h) => h.hour);

  return (
    <div className="month">
      <section className="headline">
        <h1 className="headline__sentence">
          Across January, WINDFOR ran <span className="num">{gw(s.biasMW)}</span> GW above outturn on average, and the
          windier the day, the further it overshot.
        </h1>
        <p className="headline__source">
          {s.n} hourly targets compared at the {month.auction.label} gate ({month.auction.cutoff}). WINDFOR was higher
          than the FUELHH series in {s.overPct}% of comparisons. Different measurement populations or curtailment could
          contribute; neither explanation can be confirmed using these two datasets.
        </p>
      </section>

      <section className="panel">
        <h2>The miss grows with the wind</h2>
        <p className="muted">Each dot is one hour. The lines show the average miss in each wind band.</p>
        <div className="chart-scroll">
          <LevelScatter month={month} />
        </div>
      </section>

      <section className="panel panel--split">
        <div>
          <h2>Correcting for it</h2>
          <p>
            Across {v.evaluatedDays} subsequently evaluated days ({v.n} hourly observations),
            an experimental wind-level adjustment changed mean absolute difference from {gw(v.rawMaeMW)} GW to{' '}
            {gw(v.levelMaeMW)} GW. Each test date used only complete delivery days before its own decision date.
          </p>
          <p className="muted">
            In this limited walk-forward evaluation, actual generation exceeded the exploratory lower reference
            in {v.aboveFloorPct ?? '–'}% of hours, and fell within the illustrative interval in
            {` ${v.insideRangePct ?? '–'}%`}. These are observed historical frequencies, not promised coverage.
          </p>
        </div>
        <ValidationBars month={month} />
      </section>

      <section className="panel">
        <h2>The earlier the forecast, the bigger the miss</h2>
        <p className="muted">
          A forecast made 6 hours ahead misses by {gw(month.horizons[0].maeMW)} GW on a typical hour; one made 48 hours
          ahead, by {gw(month.horizons[month.horizons.length - 1].maeMW)} GW. Later auctions see fresher runs.
        </p>
        <div className="chart-scroll">
          <HorizonChart month={month} />
        </div>
      </section>

      <section className="panel panel--split">
        <div>
          <h2>The days to learn from</h2>
          <ul className="plain-list">
            {worst.map((d) => (
              <li key={d.deliveryDate}>
                <button className="link" onClick={() => onOpenDay(d.deliveryDate)}>
                  {shortDate(d.deliveryDate)}
                </button>{' '}
                missed by {gw(d.maeMW)} GW on a typical hour
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h2>The hardest hours</h2>
          <p>
            Forecasts for {weakHours.join(', ')} missed by the most; those for {bestHours.join(', ')} missed by the
            least.
          </p>
        </div>
      </section>
    </div>
  );
}
