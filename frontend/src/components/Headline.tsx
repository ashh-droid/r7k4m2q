import { clock, dayOf, gw } from '../format';
import type { Day } from '../types';

function Figure({ mw }: { mw: number | null }) {
  return <span className="num nowrap">{gw(mw)} GW</span>;
}

/** Editorial summary: first say what was forecast, then distinguish the trial adjustment. */
export function Headline({ day }: { day: Day }) {
  const h = day.headline;
  const hasEstimate = day.calibration.available && h.planMW != null;
  return (
    <section className="headline" aria-label="Decision-time forecast summary">
      <p className="headline__kicker">The forecast at the auction gate</p>
      <h1 className="headline__sentence">
        WINDFOR expected <Figure mw={h.windforMW} /> across this delivery day.
        {hasEstimate ? (
          <> Earlier January observations suggest an adjusted estimate of <Figure mw={h.planMW} />,
            with a lower reference near <Figure mw={h.floorMW} />.</>
        ) : (
          <> There were not yet enough earlier January observations to estimate a meaningful adjustment.</>
        )}
      </h1>
      <p className="headline__source">
        {day.forecastRun ? (
          <>Most recent eligible run: {clock(day.forecastRun)} on {dayOf(day.forecastRun)}.
            {day.forecastRunCount > 1 ? ` ${day.forecastRunCount} distinct runs contribute across the 24 target hours.` : ''}
          </>
        ) : (<>No eligible published forecast was found.</>)}{' '}
        {day.auction.label} closes at {day.auction.cutoff} on the day before delivery; a five-minute publication margin is assumed.
      </p>
      <p className="headline__qualification">
        {hasEstimate
          ? `Exploratory adjustment fitted to ${day.calibration.trainingDays} earlier completed delivery days only. This is not a verified trading instruction or guaranteed lower bound.`
          : `Calibration begins after seven prior completed delivery days; the published forecast remains visible without an invented adjustment.`}
      </p>
    </section>
  );
}
