export interface PlatformStats {
  platform: string;
  market_count: number;
  snapshot_count: number;
  snapshots_last_hour: number;
  latest_snapshot_at: string | null;
}

export interface StatsResponse {
  platforms: PlatformStats[];
  total_markets: number;
  total_snapshots: number;
}

export interface MarketOut {
  id: string;
  platform: string;
  title: string;
  category: string | null;
  close_time: string | null;
  resolved: boolean;
  latest_yes_price: number | null;
  latest_no_price: number | null;
  latest_snapshot_at: string | null;
}

export interface MarketsResponse {
  items: MarketOut[];
  total: number;
}

export interface TimelineBucket {
  bucket: string;
  platform: string;
  count: number;
}

export interface TimelineResponse {
  buckets: TimelineBucket[];
}
