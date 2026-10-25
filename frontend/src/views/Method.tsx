import type { Meta } from '../types';

export function Method({ meta }: { meta: Meta | null }) {
  const retrieved = meta?.retrievedAtUTC
    ? new Date(meta.retrievedAtUTC).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
    : null;
  return (
    <article className="method">
      <h1 className="method__title">How it works</h1>

      <section>
        <h2>The question</h2>
        <p>
          An energy utility must decide on day-ahead electricity purchases before the final outturn is known.
          We reconstruct the wind forecast available before each auction and examine how it later compared with
          metered wind generation. Demand, prices and existing electricity positions are outside this pilot.
        </p>
      </section>

      <section>
        <h2>Which forecast counts</h2>
        <p>
          WINDFOR is republished several times a day. For each hour of the delivery day we take the newest run published
          at least {meta?.publicationLagMinutes ?? 5} minutes before the auction's gate closes. Anything later is shown
          in the revision history but never used. The tests check this for every hour of every day.
        </p>
        <table className="table">
          <thead>
            <tr>
              <th scope="col">Auction</th>
              <th scope="col">Gate closes (UK, day before)</th>
            </tr>
          </thead>
          <tbody>
            {meta?.auctions.map((a) => (
              <tr key={a.id}>
                <td>{a.label}</td>
                <td>{a.cutoff}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h2>The exploratory adjustment and its interval</h2>
        <p>
          In the January snapshot, WINDFOR was often higher than FUELHH actual generation, especially at high
          forecast levels. To explore this, hours are grouped into forecast bands (under 10 GW, 10–14 GW, over 14 GW).
          We subtract the earlier average signed difference for the relevant band. A 10th–90th percentile interval
          describes the variation in prior observations, not a guaranteed prediction interval.
        </p>
        <p>
          For delivery day D, training uses only complete delivery days on or before D−2. The day under examination
          and later days are never used for its adjustment. We require seven earlier complete days, and report
          walk-forward results only on dates with sufficient prior history. These historical retrospective measurements
          do not establish robust performance in future months.
        </p>
      </section>

      <section>
        <h2>The data</h2>
        <ul>
          <li>Outturn: Elexon FUELHH, fuel type WIND, half-hourly, in MW.</li>
          <li>Forecasts: Elexon WINDFOR, hourly targets, every published run kept.</li>
          <li>Forecasts are compared with outturn for the half-hour starting on the hour.</li>
          <li>Illustrative forecast energy sums hourly target MW as one-hour averages; actual energy sums half-hour MW × 0.5.</li>
          <li>The forecast series and metered generation may cover different wind-farm populations; differences are not proven forecast-model errors.</li>
          <li>The wind-band adjustment uses historical actuals as available in the October snapshot, not the exact publication versions available during January.</li>
          <li>Irregular publication times remain in the forecast revision record; the selection follows timestamps, not an assumed fixed publication schedule.</li>
          {meta?.actualRows != null && (
            <li>
              Snapshot: {meta.actualRows.toLocaleString('en-GB')} outturn rows and{' '}
              {meta.forecastRows?.toLocaleString('en-GB')} forecast rows{retrieved && <>, retrieved {retrieved}</>}.
            </li>
          )}
        </ul>
      </section>

      <section>
        <h2>What this is not</h2>
        <p>
          It does not know the client's demand, positions or prices, so it does not say how much to buy. FUELHH and
          WINDFOR may not cover exactly the same wind farms; part of the miss may come from that rather than from the
          forecast itself.
        </p>
        <p>
          <a href="/api/docs">Open the API documentation</a>
        </p>
      </section>
    </article>
  );
}
