import { useEffect, useRef, useState } from "react";

interface PollingState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

/** Fetches on mount, then again every `intervalMs`, until the deps change or the component unmounts. */
export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
  deps: unknown[],
): PollingState<T> {
  const [state, setState] = useState<PollingState<T>>({ data: null, error: null, loading: true });
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    let cancelled = false;
    let timer: number;

    async function tick() {
      try {
        const result = await fetcherRef.current();
        if (!cancelled) setState({ data: result, error: null, loading: false });
      } catch (e) {
        if (!cancelled) {
          setState((prev) => ({
            data: prev.data,
            error: e instanceof Error ? e.message : "Unknown error",
            loading: false,
          }));
        }
      }
      if (!cancelled) timer = window.setTimeout(tick, intervalMs);
    }

    setState((prev) => ({ ...prev, loading: true }));
    tick();

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
