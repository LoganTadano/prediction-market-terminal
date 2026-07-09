import type { MarketOut } from "../types";
import { platformColor, platformLabel } from "../platform";

function formatPct(price: number | null): string {
  if (price === null) return "—";
  return `${(price * 100).toFixed(1)}%`;
}

function formatRelative(iso: string | null): string {
  if (!iso) return "never";
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

interface Props {
  markets: MarketOut[];
  total: number;
  platform: string;
  search: string;
  offset: number;
  limit: number;
  onPlatformChange: (platform: string) => void;
  onSearchChange: (search: string) => void;
  onOffsetChange: (offset: number) => void;
}

export function MarketsTable({
  markets,
  total,
  platform,
  search,
  offset,
  limit,
  onPlatformChange,
  onSearchChange,
  onOffsetChange,
}: Props) {
  const page = Math.floor(offset / limit) + 1;
  const pageCount = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="table-section">
      <div className="table-filters">
        <select value={platform} onChange={(e) => onPlatformChange(e.target.value)}>
          <option value="">All platforms</option>
          <option value="kalshi">Kalshi</option>
          <option value="polymarket">Polymarket</option>
        </select>
        <input
          type="text"
          placeholder="Search titles…"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
        />
        <span className="table-filters__count">{total.toLocaleString()} markets</span>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Platform</th>
              <th>Title</th>
              <th>Category</th>
              <th>Yes</th>
              <th>No</th>
              <th>Updated</th>
              <th>Closes</th>
            </tr>
          </thead>
          <tbody>
            {markets.map((m) => (
              <tr key={m.id}>
                <td>
                  <span className="badge">
                    <span className="badge__dot" style={{ background: platformColor(m.platform) }} />
                    {platformLabel(m.platform)}
                  </span>
                </td>
                <td className="table-title" title={m.title}>
                  {m.title}
                </td>
                <td className="table-muted">{m.category ?? "—"}</td>
                <td className="table-numeric">{formatPct(m.latest_yes_price)}</td>
                <td className="table-numeric">{formatPct(m.latest_no_price)}</td>
                <td className="table-muted">{formatRelative(m.latest_snapshot_at)}</td>
                <td className="table-muted">
                  {m.close_time ? new Date(m.close_time).toLocaleDateString() : "—"}
                </td>
              </tr>
            ))}
            {markets.length === 0 && (
              <tr>
                <td colSpan={7} className="table-empty">
                  No markets match this filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="table-pagination">
        <button disabled={offset === 0} onClick={() => onOffsetChange(Math.max(0, offset - limit))}>
          Previous
        </button>
        <span>
          Page {page} of {pageCount}
        </span>
        <button
          disabled={offset + limit >= total}
          onClick={() => onOffsetChange(offset + limit)}
        >
          Next
        </button>
      </div>
    </div>
  );
}
