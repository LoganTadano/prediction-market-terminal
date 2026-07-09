import { useEffect, useState } from "react";
import "./App.css";
import { api } from "./api";
import { usePolling } from "./usePolling";
import { StatTiles } from "./components/StatTiles";
import { IngestionChart } from "./components/IngestionChart";
import { MarketsTable } from "./components/MarketsTable";

const STATS_POLL_MS = 10_000;
const MARKETS_LIMIT = 50;

function App() {
  const [platform, setPlatform] = useState("");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    setOffset(0);
  }, [platform, debouncedSearch]);

  const stats = usePolling(api.stats, STATS_POLL_MS, []);
  const timeline = usePolling(() => api.ingestionTimeline(24), STATS_POLL_MS, []);
  const markets = usePolling(
    () => api.markets({ platform: platform || undefined, search: debouncedSearch || undefined, limit: MARKETS_LIMIT, offset }),
    STATS_POLL_MS,
    [platform, debouncedSearch, offset],
  );

  const anyError = stats.error || timeline.error || markets.error;

  return (
    <div className="page">
      <header className="header">
        <h1>EdgeFinder ingestion dashboard</h1>
        <p className="header__sub">
          Live view of what's landing in Postgres from the Kalshi and Polymarket pollers. Auto-refreshes every 10s.
        </p>
      </header>

      {anyError && (
        <div className="banner banner--error">
          Couldn't reach the API ({anyError}). Check VITE_API_URL and that the backend is reachable.
        </div>
      )}

      {stats.data ? (
        <StatTiles stats={stats.data} />
      ) : (
        !anyError && <div className="banner">Loading stats…</div>
      )}

      <section>
        <h2 className="section-title">Snapshots ingested — last 24h</h2>
        {timeline.data && <IngestionChart buckets={timeline.data.buckets} />}
      </section>

      <section>
        <h2 className="section-title">Markets</h2>
        {markets.data && (
          <MarketsTable
            markets={markets.data.items}
            total={markets.data.total}
            platform={platform}
            search={search}
            offset={offset}
            limit={MARKETS_LIMIT}
            onPlatformChange={setPlatform}
            onSearchChange={setSearch}
            onOffsetChange={setOffset}
          />
        )}
      </section>
    </div>
  );
}

export default App;
