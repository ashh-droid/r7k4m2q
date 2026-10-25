import { addDays, gw, longDate, shortDate } from '../format';
import type { Month } from '../types';

type Props = {
  date: string;
  range: [string, string];
  month: Month | null;
  onChange: (date: string) => void;
};

/** Previous/next day, plus a ribbon of January where each day's bar is WINDFOR's miss. */
export function DayNav({ date, range, month, onChange }: Props) {
  const prev = addDays(date, -1);
  const next = addDays(date, 1);
  const canPrev = prev >= range[0];
  const canNext = next <= range[1];
  const maxBias = Math.max(1, ...(month?.days.map((d) => Math.abs(d.biasMW ?? 0)) ?? [1]));

  return (
    <nav className="day-nav" aria-label="Delivery day">
      <div className="day-nav__row">
        <button
          className="day-nav__step"
          disabled={!canPrev}
          onClick={() => onChange(prev)}
          aria-label={`Previous day, ${shortDate(prev)}`}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
            <path d="M10 3 5 8l5 5" fill="none" stroke="currentColor" strokeWidth="1.6" />
          </svg>
          <span>{shortDate(prev)}</span>
        </button>
        <p className="day-nav__date">{longDate(date)}</p>
        <button
          className="day-nav__step"
          disabled={!canNext}
          onClick={() => onChange(next)}
          aria-label={`Next day, ${shortDate(next)}`}
        >
          <span>{shortDate(next)}</span>
          <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
            <path d="m6 3 5 5-5 5" fill="none" stroke="currentColor" strokeWidth="1.6" />
          </svg>
        </button>
      </div>

      {month && (
        <div className="ribbon">
          <div className="ribbon__bars">
            {month.days.map((d) => {
              const b = d.biasMW ?? 0;
              const h = (Math.abs(b) / maxBias) * 26;
              const label = `${shortDate(d.deliveryDate)}: WINDFOR ${gw(Math.abs(b))} GW ${b >= 0 ? 'too high' : 'too low'}`;
              return (
                <button
                  key={d.deliveryDate}
                  className={`ribbon__day${d.deliveryDate === date ? ' ribbon__day--current' : ''}`}
                  aria-label={label}
                  aria-current={d.deliveryDate === date ? 'date' : undefined}
                  title={label}
                  onClick={() => onChange(d.deliveryDate)}
                >
                  <span
                    className={b >= 0 ? 'ribbon__bar ribbon__bar--over' : 'ribbon__bar ribbon__bar--under'}
                    style={{ height: `${Math.max(2, h)}px` }}
                  />
                </button>
              );
            })}
          </div>
          <div className="ribbon__ends" aria-hidden="true">
            <span>{shortDate(range[0])}</span>
            <span>{shortDate(range[1])}</span>
          </div>
          <p className="ribbon__caption">
            Historical comparison: each bar represents a delivery day. Amber means the forecast exceeded outturn;
            teal means it was below outturn. Future days in this ribbon are hindsight, not decision-time information.
          </p>
        </div>
      )}
    </nav>
  );
}
