import type { Day } from './types';

/** Export source-native hourly forecasts alongside all half-hourly outturns. */
export function exportDayCsv(day: Day): void {
  const byTime = new Map(day.hours.map((hour) => [hour.startTime, hour]));
  const fields = [
    'targetStartUTC', 'actualWindMW', 'publishedWINDFORMW', 'trialAdjustmentMW',
    'historicalLowerReferenceMW', 'historicalUpperReferenceMW', 'eligiblePublishTimeUTC',
    'nativeHourlyForecastTarget', 'auction', 'gateClosureUTC',
  ];
  const rows = day.halfHourActuals.map((slot) => {
    const hourly = byTime.get(slot.startTime);
    return [
      slot.startTime, slot.actual, hourly?.windfor, hourly?.plan, hourly?.low,
      hourly?.high, hourly?.publishTime, hourly ? 'yes' : 'no', day.auction.label, day.gateClosure,
    ].map((value) => value == null ? '' : String(value)).join(',');
  });
  const csv = [fields.join(','), ...rows].join('\r\n') + '\r\n';
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = `gate-${day.deliveryDate}-${day.auction.id}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
