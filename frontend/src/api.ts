import type { Day, Meta, Month, Revisions } from './types';

async function get<T>(path: string, params: Record<string, string> = {}, signal?: AbortSignal): Promise<T> {
  const query = new URLSearchParams(params).toString();
  const response = await fetch(query ? `${path}?${query}` : path, { signal, headers: { Accept: 'application/json' } });
  if (!response.ok) {
    let message = `The server answered ${response.status}.`;
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') message = body.detail;
    } catch {
      /* keep the generic message */
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const getMeta = (signal?: AbortSignal) => get<Meta>('/api/meta', {}, signal);

export const getDay = (deliveryDate: string, auction: string, signal?: AbortSignal) =>
  get<Day>('/api/day', { delivery_date: deliveryDate, auction }, signal);

export const getMonth = (auction: string, signal?: AbortSignal) => get<Month>('/api/month', { auction }, signal);

export const getRevisions = (startTime: string, auction: string, signal?: AbortSignal) =>
  get<Revisions>('/api/revisions', { start_time: startTime, auction }, signal);
