import { useRef } from 'react';
import type { KeyboardEvent } from 'react';
import { gw } from '../format';
import type { Hour } from '../types';

type Props = {
  hours: Hour[];
  selected: number;
  hovered: number | null;
  revealed: boolean;
  onSelect: (i: number) => void;
  onHover: (i: number | null) => void;
};

/** One button per hour showing the floor. Arrow keys move along the day. */
export function HourStrip({ hours, selected, hovered, revealed, onSelect, onHover }: Props) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  const onKey = (e: KeyboardEvent<HTMLButtonElement>, i: number) => {
    const next =
      e.key === 'ArrowRight'
        ? i + 1
        : e.key === 'ArrowLeft'
          ? i - 1
          : e.key === 'Home'
            ? 0
            : e.key === 'End'
              ? hours.length - 1
              : null;
    if (next == null) return;
    e.preventDefault();
    const clamped = Math.max(0, Math.min(hours.length - 1, next));
    onSelect(clamped);
    refs.current[clamped]?.focus();
  };

  return (
    <div
      className="hour-strip"
      role="group"
      aria-label="Exploratory lower reference by hour, in gigawatts. Choose an hour to inspect forecast revisions."
    >
      {hours.map((h, i) => {
        const below = revealed && h.actual != null && h.low != null && h.actual < h.low;
        return (
          <button
            key={h.startTime}
            ref={(el) => {
              refs.current[i] = el;
            }}
            className={[
              'hour',
              i === selected && 'hour--selected',
              i === hovered && 'hour--hovered',
              below && 'hour--below',
            ]
              .filter(Boolean)
              .join(' ')}
            aria-pressed={i === selected}
            tabIndex={i === selected ? 0 : -1}
            onClick={() => onSelect(i)}
            onKeyDown={(e) => onKey(e, i)}
            onMouseEnter={() => onHover(i)}
            onMouseLeave={() => onHover(null)}
          >
            <span className="hour__time">{h.hour.slice(0, 2)}</span>
            <span className="hour__floor">{gw(h.low)}</span>
            {below && <span className="visually-hidden">, outturn fell below the floor</span>}
          </button>
        );
      })}
    </div>
  );
}

export function HourReadout({ hour, revealed }: { hour: Hour; revealed: boolean }) {
  return (
    <dl className="readout" aria-live="polite">
      <div>
        <dt>Hour</dt>
        <dd>{hour.hour}</dd>
      </div>
      <div>
        <dt>WINDFOR</dt>
        <dd>{gw(hour.windfor)} GW</dd>
      </div>
      <div>
        <dt>Trial adjustment</dt>
        <dd>{gw(hour.plan)} GW</dd>
      </div>
      <div>
        <dt>Historical interval</dt>
        <dd>
          {hour.low == null || hour.high == null ? 'Not calibrated' : `${gw(hour.low)} to ${gw(hour.high)} GW`}
        </dd>
      </div>
      <div className={revealed ? '' : 'readout__hidden'}>
        <dt>Outturn</dt>
        <dd>{revealed ? `${gw(hour.actual)} GW` : 'hidden'}</dd>
      </div>
    </dl>
  );
}
