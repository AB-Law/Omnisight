"use client";

import React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  ComposedChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  ReferenceLine,
} from "recharts";

interface ChartConfig {
  title?: string;
  xKey?: string;
  lines?: Array<{ key: string; color: string; name: string; yAxisId?: string }>;
  bars?: Array<{ key: string; color: string; name: string; yAxisId?: string }>;
}

interface ChartRendererProps {
  type: string;
  data: Record<string, unknown>[];
  config?: ChartConfig;
  summary?: Record<string, unknown>;
}

const COLORS = ["#00d0ff", "#00FF87", "#FF4B2B", "#f59e0b", "#a855f7", "#ec4899"];

const tooltipStyle = {
  backgroundColor: "#0f1923",
  border: "1px solid rgba(0,208,255,0.2)",
  borderRadius: "8px",
  color: "#e2e8f0",
  fontSize: "12px",
};

const axisStyle = { fill: "#64748b", fontSize: 11 };

export default function ChartRenderer({ type, data, config, summary }: ChartRendererProps) {
  const xKey = config?.xKey ?? "date";
  const lines = config?.lines ?? [];
  const bars = config?.bars ?? [];
  const title = config?.title;

  const hasDualAxis =
    [...lines, ...bars].some((s) => s.yAxisId === "right");

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-4 mt-2 w-full">
      {title && (
        <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400 mb-3">
          {title}
        </p>
      )}

      {/* ── Line chart ─────────────────────────────────── */}
      {type === "chart:line" && (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey={xKey} tick={axisStyle} tickLine={false} />
            <YAxis yAxisId="left" tick={axisStyle} tickLine={false} domain={[-1, 1]} />
            {hasDualAxis && (
              <YAxis yAxisId="right" orientation="right" tick={axisStyle} tickLine={false} />
            )}
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />
            <ReferenceLine yAxisId="left" y={0} stroke="rgba(255,255,255,0.1)" />
            {lines.map((l) => (
              <Line
                key={l.key}
                yAxisId={l.yAxisId ?? "left"}
                type="monotone"
                dataKey={l.key}
                stroke={l.color}
                strokeWidth={2}
                dot={false}
                name={l.name}
              />
            ))}
            {bars.map((b) => (
              <Bar
                key={b.key}
                yAxisId={b.yAxisId ?? "left"}
                dataKey={b.key}
                fill={b.color}
                name={b.name}
                opacity={0.6}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}

      {/* ── Composed chart (dual-axis: sentiment + price) ── */}
      {type === "chart:composed" && (
        <>
          <ResponsiveContainer width="100%" height={220}>
            <ComposedChart data={data} margin={{ top: 4, right: 24, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey={xKey} tick={axisStyle} tickLine={false} />
              <YAxis yAxisId="left" tick={axisStyle} tickLine={false} domain={[-1, 1]} />
              <YAxis yAxisId="right" orientation="right" tick={axisStyle} tickLine={false} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />
              <ReferenceLine yAxisId="left" y={0} stroke="rgba(255,255,255,0.1)" />
              {lines.map((l) => (
                <Line
                  key={l.key}
                  yAxisId={l.yAxisId ?? "left"}
                  type="monotone"
                  dataKey={l.key}
                  stroke={l.color}
                  strokeWidth={2}
                  dot={false}
                  name={l.name}
                />
              ))}
              {bars.map((b) => (
                <Area
                  key={b.key}
                  yAxisId={b.yAxisId ?? "right"}
                  type="monotone"
                  dataKey={b.key}
                  stroke={b.color}
                  fill={b.color}
                  fillOpacity={0.15}
                  strokeWidth={1.5}
                  name={b.name}
                />
              ))}
            </ComposedChart>
          </ResponsiveContainer>
          {summary && (
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
              {summary.pearson_r !== undefined && (
                <Stat label="Pearson R" value={String((summary.pearson_r as number).toFixed(3))} />
              )}
              {summary.best_lag_days !== undefined && (
                <Stat label="Best Lag" value={`${summary.best_lag_days}d`} />
              )}
              {summary.signal_strength !== undefined && (
                <Stat label="Signal" value={`${(summary.signal_strength as number).toFixed(1)}%`} />
              )}
              {typeof summary.ticker === 'string' && <Stat label="Ticker" value={summary.ticker} />}
            </div>
          )}
          {summary?.insight && (
            <p className="mt-2 text-[11px] text-slate-400 leading-relaxed font-mono">
              {summary.insight as string}
            </p>
          )}
        </>
      )}

      {/* ── Bar chart / Sector heatmap ────────────────── */}
      {type === "chart:bar" && (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey={xKey}
              tick={{ ...axisStyle, fontSize: 10 }}
              tickLine={false}
              angle={-35}
              textAnchor="end"
            />
            <YAxis tick={axisStyle} tickLine={false} domain={[-1, 1]} />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.1)" />
            {bars.map((b) => (
              <Bar key={b.key} dataKey={b.key} name={b.name} radius={[3, 3, 0, 0]}>
                {data.map((entry, index) => {
                  const val = entry[b.key] as number;
                  return (
                    <Cell
                      key={`cell-${index}`}
                      fill={val >= 0 ? "#00FF87" : "#FF4B2B"}
                      opacity={0.8}
                    />
                  );
                })}
              </Bar>
            ))}
          </BarChart>
        </ResponsiveContainer>
      )}

      {/* ── Histogram (event volume) ──────────────────── */}
      {type === "chart:histogram" && (
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey={xKey} tick={axisStyle} tickLine={false} />
            <YAxis tick={axisStyle} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle} />
            {bars.length > 0
              ? bars.map((b) => (
                  <Bar key={b.key} dataKey={b.key} fill={b.color} name={b.name} radius={[2, 2, 0, 0]} />
                ))
              : <Bar dataKey="event_count" fill="#00d0ff" radius={[2, 2, 0, 0]} />}
          </BarChart>
        </ResponsiveContainer>
      )}

      {/* ── Pie chart (sentiment distribution) ──────── */}
      {type === "chart:pie" && (
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={80}
              strokeWidth={0}
              label={({ name, percent }) =>
                `${name} ${((percent ?? 0) * 100).toFixed(0)}%`
              }
              labelLine={false}
            >
              {data.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-white/5 border border-white/5 px-3 py-2">
      <p className="text-[9px] uppercase font-bold tracking-widest text-slate-500">{label}</p>
      <p className="text-sm font-bold text-[#00d0ff] font-mono">{value}</p>
    </div>
  );
}
