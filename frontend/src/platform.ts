/** Fixed categorical color order — never cycled, never reassigned when the filtered set changes. */
const COLORS: Record<string, string> = {
  kalshi: "var(--series-kalshi)",
  polymarket: "var(--series-polymarket)",
};

const FALLBACK = "var(--text-muted)";

export function platformColor(platform: string): string {
  return COLORS[platform] ?? FALLBACK;
}

export function platformLabel(platform: string): string {
  return platform.charAt(0).toUpperCase() + platform.slice(1);
}
