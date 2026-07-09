import type { StatsResponse } from "../types";
import { FreshnessBadge } from "./FreshnessBadge";
import { platformColor, platformLabel } from "../platform";

export function StatTiles({ stats }: { stats: StatsResponse }) {
  return (
    <div className="tiles">
      <div className="tile">
        <div className="tile__label">Total markets</div>
        <div className="tile__value">{stats.total_markets.toLocaleString()}</div>
      </div>
      <div className="tile">
        <div className="tile__label">Total price snapshots</div>
        <div className="tile__value">{stats.total_snapshots.toLocaleString()}</div>
      </div>
      {stats.platforms.map((p) => (
        <div className="tile" key={p.platform}>
          <div className="tile__label">
            <span
              className="tile__dot"
              style={{ background: platformColor(p.platform) }}
              aria-hidden="true"
            />
            {platformLabel(p.platform)}
            <FreshnessBadge latestSnapshotAt={p.latest_snapshot_at} />
          </div>
          <div className="tile__value">{p.market_count.toLocaleString()}</div>
          <div className="tile__sub">
            {p.snapshots_last_hour.toLocaleString()} snapshots in the last hour
          </div>
        </div>
      ))}
    </div>
  );
}
