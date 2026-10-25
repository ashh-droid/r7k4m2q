const LONDON = 'Europe/London';

/** MW to GW with one decimal, e.g. 19390 -> "19.4". */
export const gw = (mw: number | null | undefined, digits = 1) => (mw == null ? '–' : (mw / 1000).toFixed(digits));

/** "2026-01-21" -> Date at noon UTC (safe for day arithmetic in January). */
export const parseDay = (iso: string) => new Date(`${iso}T12:00:00Z`);

export const isoDay = (d: Date) => d.toISOString().slice(0, 10);

export const addDays = (iso: string, n: number) => {
  const d = parseDay(iso);
  d.setUTCDate(d.getUTCDate() + n);
  return isoDay(d);
};

export const longDate = (iso: string) =>
  parseDay(iso).toLocaleDateString('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  });

export const shortDate = (iso: string) =>
  parseDay(iso).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' });

export const weekday = (iso: string) => parseDay(iso).toLocaleDateString('en-GB', { weekday: 'long', timeZone: 'UTC' });

export const clock = (isoTime: string) =>
  new Date(isoTime).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: LONDON,
  });

export const dayOf = (isoTime: string) =>
  new Date(isoTime).toLocaleDateString('en-GB', { weekday: 'long', timeZone: LONDON });

export const clockAndDay = (isoTime: string) =>
  new Date(isoTime).toLocaleString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: LONDON,
  });

/** ["04:00","05:00","06:00","11:00"] -> "for the 3 hours from 04:00 and at 11:00". */
export function hourWindows(hours: string[]): string {
  if (!hours.length) return '';
  const nums = hours.map((h) => Number(h.slice(0, 2))).sort((a, b) => a - b);
  const runs: [number, number][] = [];
  for (const n of nums) {
    const last = runs[runs.length - 1];
    if (last && n === last[1] + 1) last[1] = n;
    else runs.push([n, n]);
  }
  const pad = (n: number) => `${String(n % 24).padStart(2, '0')}:00`;
  const parts = runs.map(([a, b]) => (a === b ? `at ${pad(a)}` : `for the ${b - a + 1} hours from ${pad(a)}`));
  return parts.length > 1 ? `${parts.slice(0, -1).join(', ')} and ${parts[parts.length - 1]}` : parts[0];
}
