import { useMemo, useRef, useState } from "react";
import type { TimelineBucket } from "../types";
import { platformColor, platformLabel } from "../platform";

const WIDTH = 760;
const HEIGHT = 260;
const MARGIN = { top: 16, right: 16, bottom: 28, left: 40 };
const PLOT_W = WIDTH - MARGIN.left - MARGIN.right;
const PLOT_H = HEIGHT - MARGIN.top - MARGIN.bottom;
const Y_TICKS = 4;

function buildSeries(buckets: TimelineBucket[]) {
  const platforms = Array.from(new Set(buckets.map((b) => b.platform))).sort();
  const timestamps = Array.from(new Set(buckets.map((b) => b.bucket))).sort();
  const lookup = new Map<string, number>();
  for (const b of buckets) lookup.set(`${b.bucket}|${b.platform}`, b.count);

  return {
    timestamps,
    series: platforms.map((platform) => ({
      platform,
      values: timestamps.map((t) => lookup.get(`${t}|${platform}`) ?? 0),
    })),
  };
}

function formatHour(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

export function IngestionChart({ buckets }: { buckets: TimelineBucket[] }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const { timestamps, series } = useMemo(() => buildSeries(buckets), [buckets]);

  if (timestamps.length === 0) {
    return <div className="chart-empty">No snapshots ingested yet in this window.</div>;
  }

  const yMax = Math.max(4, ...series.flatMap((s) => s.values)) * 1.15;
  const xScale = (i: number) =>
    MARGIN.left + (timestamps.length === 1 ? 0 : (i / (timestamps.length - 1)) * PLOT_W);
  const yScale = (v: number) => MARGIN.top + PLOT_H - (v / yMax) * PLOT_H;

  const yTicks = Array.from({ length: Y_TICKS + 1 }, (_, i) => Math.round((yMax / Y_TICKS) * i));
  const xTickEvery = Math.max(1, Math.ceil(timestamps.length / 6));

  function handleMove(e: React.MouseEvent<SVGRectElement>) {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const fracX = (e.clientX - rect.left) / rect.width;
    const viewBoxX = fracX * WIDTH;
    const raw = ((viewBoxX - MARGIN.left) / PLOT_W) * (timestamps.length - 1);
    const idx = Math.min(timestamps.length - 1, Math.max(0, Math.round(raw)));
    setHoverIndex(idx);
  }

  return (
    <div className="chart">
      <div className="chart__legend">
        {series.map((s) => (
          <span className="chart__legend-item" key={s.platform}>
            <span className="chart__legend-dot" style={{ background: platformColor(s.platform) }} />
            {platformLabel(s.platform)}
          </span>
        ))}
      </div>

      <div className="chart__svg-wrap">
        <svg ref={svgRef} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Snapshots ingested per hour by platform">
          {yTicks.map((tick) => (
            <g key={tick}>
              <line
                x1={MARGIN.left}
                x2={WIDTH - MARGIN.right}
                y1={yScale(tick)}
                y2={yScale(tick)}
                className="chart__gridline"
              />
              <text x={MARGIN.left - 8} y={yScale(tick)} className="chart__axis-label" textAnchor="end" dominantBaseline="middle">
                {tick}
              </text>
            </g>
          ))}

          <line
            x1={MARGIN.left}
            x2={WIDTH - MARGIN.right}
            y1={MARGIN.top + PLOT_H}
            y2={MARGIN.top + PLOT_H}
            className="chart__baseline"
          />

          {timestamps.map((t, i) =>
            i % xTickEvery === 0 ? (
              <text key={t} x={xScale(i)} y={HEIGHT - 6} className="chart__axis-label" textAnchor="middle">
                {formatHour(t)}
              </text>
            ) : null,
          )}

          {series.map((s) => (
            <path
              key={s.platform}
              d={s.values.map((v, i) => `${i === 0 ? "M" : "L"}${xScale(i)},${yScale(v)}`).join(" ")}
              fill="none"
              stroke={platformColor(s.platform)}
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          ))}

          {hoverIndex !== null && (
            <>
              <line
                x1={xScale(hoverIndex)}
                x2={xScale(hoverIndex)}
                y1={MARGIN.top}
                y2={MARGIN.top + PLOT_H}
                className="chart__crosshair"
              />
              {series.map((s) => (
                <circle
                  key={s.platform}
                  cx={xScale(hoverIndex)}
                  cy={yScale(s.values[hoverIndex])}
                  r={4}
                  fill={platformColor(s.platform)}
                  stroke="var(--surface)"
                  strokeWidth={2}
                />
              ))}
            </>
          )}

          <rect
            x={MARGIN.left}
            y={MARGIN.top}
            width={PLOT_W}
            height={PLOT_H}
            fill="transparent"
            onMouseMove={handleMove}
            onMouseLeave={() => setHoverIndex(null)}
          />
        </svg>

        {hoverIndex !== null && (
          <div
            className="chart__tooltip"
            style={{
              left: `${(xScale(hoverIndex) / WIDTH) * 100}%`,
            }}
          >
            <div className="chart__tooltip-time">{formatHour(timestamps[hoverIndex])}</div>
            {series.map((s) => (
              <div className="chart__tooltip-row" key={s.platform}>
                <span className="chart__legend-dot" style={{ background: platformColor(s.platform) }} />
                {platformLabel(s.platform)}: {s.values[hoverIndex]}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
