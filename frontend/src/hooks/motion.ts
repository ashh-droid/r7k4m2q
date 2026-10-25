import { useEffect, useRef, useState } from 'react';

export function usePrefersReducedMotion(): boolean {
  const query = '(prefers-reduced-motion: reduce)';
  const [reduced, setReduced] = useState(() => typeof window !== 'undefined' && window.matchMedia(query).matches);
  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = () => setReduced(mql.matches);
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, []);
  return reduced;
}

const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);

/**
 * Animate a number from its previous value to `target`.
 * First render counts up from `from`; later changes glide between values.
 */
export function useCountTo(target: number | null, duration = 900, from = 0): number | null {
  const reduced = usePrefersReducedMotion();
  const [value, setValue] = useState<number | null>(reduced ? target : target == null ? null : from);
  const current = useRef<number>(from);

  useEffect(() => {
    if (target == null) {
      setValue(null);
      return;
    }
    if (reduced) {
      current.current = target;
      setValue(target);
      return;
    }
    const start = performance.now();
    const origin = current.current;
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const v = origin + (target - origin) * easeOutCubic(t);
      current.current = v;
      setValue(v);
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, duration, reduced]);

  return value;
}
