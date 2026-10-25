import { clock, clockAndDay, gw } from '../format';
import type { Revisions } from '../types';

const W = 1200;
const H = 240;
const PAD = { left: 56, right: 24, top: 28, bottom: 34 };

/** How one hour's forecast moved, run by run, with the gate and delivery marked. */
export function RevisionTrail({ data, revealed }: { data: Revisions; revealed: boolean }) {
  const versions = data.versions;
  if (!versions.length) return <p className="muted">No WINDFOR runs exist for this hour.</p>;

  const t = (iso: string) => new Date(iso).getTime();
  const target = t(data.startTime);
  const gate = t(data.gateClosure);
  const t0 = t(versions[0].publishTime);
  const t1 = Math.max(target, t(versions[versions.length - 1].publishTime));
  const values = versions.map((v) => v.mw).concat(revealed && data.actual != null ? [data.actual] : []);
  const min = Math.floor(Math.min(...values) / 1000) * 1000 - 1000;
  const max = Math.ceil(Math.max(...values) / 1000) * 1000 + 1000;
  const x = (ms: number) => PAD.left + ((ms - t0) / (t1 - t0)) * (W - PAD.left - PAD.right);
  const y = (mw: number) => PAD.top + (1 - (mw - min) / (max - min)) * (H - PAD.top - PAD.bottom);

  let step = '';
  versions.forEach((v, i) => {
    const vx = x(t(v.publishTime));
    const vy = y(v.mw);
    step += i ? `H${vx.toFixed(1)} V${vy.toFixed(1)} ` : `M${vx.toFixed(1)},${vy.toFixed(1)} `;
  });
  step += `H${x(t1).toFixed(1)}`;

  const atGate = versions.find((v) => v.selected);
  const beforeDelivery = [...versions].reverse().find((v) => t(v.publishTime) < target);
  const lateCount = versions.filter((v) => v.status !== 'before_gate').length;

  return (
    <div className="trail">
      <p className="trail__sentence">
        WINDFOR's forecast for {data.hour} was revised {versions.length - 1} times.{' '}
        {atGate ? <>At the gate it said {gw(atGate.mw)} GW. </> : <>Nothing was out by the gate. </>}
        {beforeDelivery && <>The last run before delivery said {gw(beforeDelivery.mw)} GW</>}
        {revealed && data.actual != null ? <>, and outturn was {gw(data.actual)} GW.</> : <>.</>}
        {lateCount > 0 && <> {lateCount} of those runs came after the gate, so they are shown but never used.</>}
      </p>
      <div className="chart-scroll">
        <svg
          className="trail__chart"
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-label={`Forecast revisions for ${data.hour}, with the gate closure and delivery time marked`}
        >
          <g className="trail__grid">
            {[min + 1000, (min + max) / 2, max - 1000].map((v) => (
              <g key={v}>
                <line x1={PAD.left} x2={W - PAD.right} y1={y(v)} y2={y(v)} />
                <text x={PAD.left - 10} y={y(v) + 4} textAnchor="end">
                  {gw(v)}
                </text>
              </g>
            ))}
          </g>
          <rect
            className="trail__after"
            x={x(gate)}
            y={PAD.top}
            width={x(t1) - x(gate)}
            height={H - PAD.top - PAD.bottom}
          />
          <line className="trail__marker" x1={x(gate)} x2={x(gate)} y1={PAD.top - 12} y2={H - PAD.bottom} />
          <text className="trail__label" x={x(gate) + 8} y={PAD.top - 2}>
            Gate closed {clock(data.gateClosure)}
          </text>
          <line className="trail__marker" x1={x(target)} x2={x(target)} y1={PAD.top - 12} y2={H - PAD.bottom} />
          <text className="trail__label" x={x(target) - 8} y={PAD.top - 2} textAnchor="end">
            Delivery {data.hour}
          </text>
          {revealed && data.actual != null && (
            <>
              <line
                className="trail__actual"
                x1={PAD.left}
                x2={W - PAD.right}
                y1={y(data.actual)}
                y2={y(data.actual)}
              />
              <text className="trail__label" x={W - PAD.right} y={y(data.actual) - 8} textAnchor="end">
                Outturn {gw(data.actual)} GW
              </text>
            </>
          )}
          <path className="trail__step" d={step} />
          {versions.map((v) => (
            <circle
              key={v.publishTime}
              className={`trail__run trail__run--${v.status}${v.selected ? ' trail__run--selected' : ''}`}
              cx={x(t(v.publishTime))}
              cy={y(v.mw)}
              r={v.selected ? 7 : 4}
            >
              <title>
                {clockAndDay(v.publishTime)}: {gw(v.mw)} GW
              </title>
            </circle>
          ))}
          <text className="trail__axis" x={PAD.left} y={H - 8}>
            {clockAndDay(versions[0].publishTime)}
          </text>
          <text className="trail__axis" x={W - PAD.right} y={H - 8} textAnchor="end">
            {clockAndDay(new Date(t1).toISOString())}
          </text>
        </svg>
      </div>
    </div>
  );
}
