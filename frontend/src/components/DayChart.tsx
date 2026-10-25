import { useRef } from 'react';
import type { MouseEvent } from 'react';
import { gw } from '../format';
import type { Day } from '../types';

const W = 1200;
const H = 380;
const PAD = { left: 56, right: 16, top: 16, bottom: 36 };
const PLOT_W = W - PAD.left - PAD.right;
const PLOT_H = H - PAD.top - PAD.bottom;

type Props = {
  day: Day;
  revealed: boolean;
  hovered: number | null;
  onHover: (hour: number | null) => void;
  onPick: (hour: number) => void;
};

export function DayChart({ day, revealed, hovered, onHover, onPick }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const hours = day.hours;
  const halves = day.halfHourActuals;

  const values = [...hours.flatMap((h) => [h.windfor, h.low, h.high]), ...halves.map((h) => h.actual)].filter(
    (v): v is number => v != null,
  );
  const step = 2000;
  const min = Math.max(0, Math.floor(Math.min(...values) / step) * step);
  const max = Math.ceil(Math.max(...values) / step) * step;
  const ticks: number[] = [];
  const tickStep = max - min > 14000 ? 4000 : 2000;
  for (let v = min; v <= max; v += tickStep) ticks.push(v);

  const x = (hour: number) => PAD.left + (hour / 24) * PLOT_W;
  const y = (mw: number) => PAD.top + (1 - (mw - min) / (max - min)) * PLOT_H;

  const line = (points: [number, number | null][]) => {
    let d = '';
    let pen = false;
    for (const [hx, v] of points) {
      if (v == null) {
        pen = false;
        continue;
      }
      d += `${pen ? 'L' : 'M'}${x(hx).toFixed(1)},${y(v).toFixed(1)} `;
      pen = true;
    }
    return d;
  };

  const windforD = line(hours.map((h, i) => [i, h.windfor]));
  const planD = line(hours.map((h, i) => [i, h.plan]));
  const actualD = line(halves.map((h, i) => [i / 2, h.actual]));
  const withBand = hours
    .map((h, i) => ({ i, low: h.low, high: h.high }))
    .filter((p) => p.low != null && p.high != null);
  const bandD = withBand.length
    ? `${withBand.map((p, k) => `${k ? 'L' : 'M'}${x(p.i).toFixed(1)},${y(p.high!).toFixed(1)}`).join(' ')} ` +
      `${[...withBand]
        .reverse()
        .map((p) => `L${x(p.i).toFixed(1)},${y(p.low!).toFixed(1)}`)
        .join(' ')} Z`
    : '';

  const hourFromEvent = (e: MouseEvent<SVGRectElement>) => {
    const box = svgRef.current!.getBoundingClientRect();
    const sx = ((e.clientX - box.left) / box.width) * W;
    return Math.max(0, Math.min(23, Math.round(((sx - PAD.left) / PLOT_W) * 24)));
  };

  const hh = hovered != null ? hours[hovered] : null;
  const key = `${day.deliveryDate}-${day.auction.id}`;

  return (
    <svg
      ref={svgRef}
      className="day-chart"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={`Hourly wind for ${day.deliveryDate}: WINDFOR, the corrected plan with its range${revealed ? ', and what actually happened' : ''}, in gigawatts`}
    >
      <defs>
        <clipPath id={`intro-${key}`}>
          <rect className="sweep" x={PAD.left} y={0} width={PLOT_W} height={H} />
        </clipPath>
        <clipPath id={`reveal-${key}`}>
          <rect
            className={revealed ? 'sweep sweep--slow' : 'sweep-hidden'}
            x={PAD.left}
            y={0}
            width={PLOT_W}
            height={H}
          />
        </clipPath>
      </defs>

      <g className="day-chart__grid">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} />
            <text x={PAD.left - 10} y={y(t) + 4} textAnchor="end">
              {t === ticks[ticks.length - 1] ? `${gw(t, 0)} GW` : gw(t, 0)}
            </text>
          </g>
        ))}
        {[0, 3, 6, 9, 12, 15, 18, 21].map((hx) => (
          <text key={hx} x={x(hx)} y={H - 10} textAnchor="middle">
            {String(hx).padStart(2, '0')}:00
          </text>
        ))}
      </g>

      <g key={`intro-${key}`} clipPath={`url(#intro-${key})`}>
        <path className="day-chart__band" d={bandD} />
        <path className="day-chart__windfor" d={windforD} />
        <path className="day-chart__plan" d={planD} />
      </g>

      <g key={`reveal-${key}-${revealed}`} clipPath={`url(#reveal-${key})`}>
        <path className="day-chart__actual" d={actualD} />
      </g>
      {revealed && (
        <line key={`scan-${key}`} className="scanline" x1={PAD.left} x2={PAD.left} y1={PAD.top} y2={H - PAD.bottom} />
      )}

      {hh && hovered != null && (
        <g className="day-chart__cursor" aria-hidden="true">
          <line x1={x(hovered)} x2={x(hovered)} y1={PAD.top} y2={H - PAD.bottom} />
          {hh.plan != null && <circle className="dot-plan" cx={x(hovered)} cy={y(hh.plan)} r={5} />}
          {hh.windfor != null && <circle className="dot-windfor" cx={x(hovered)} cy={y(hh.windfor)} r={4} />}
          {revealed && hh.actual != null && <circle className="dot-actual" cx={x(hovered)} cy={y(hh.actual)} r={4.5} />}
        </g>
      )}

      <rect
        className="day-chart__hit"
        x={PAD.left - 10}
        y={PAD.top}
        width={PLOT_W + 20}
        height={PLOT_H}
        onMouseMove={(e) => onHover(hourFromEvent(e))}
        onMouseLeave={() => onHover(null)}
        onClick={(e) => onPick(hourFromEvent(e))}
      />
    </svg>
  );
}
