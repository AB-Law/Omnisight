"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ChartRenderer from "./ChartRenderer";
import GraphRenderer from "./GraphRenderer";
import ToolCallIndicator from "./ToolCallIndicator";
import type { VizPayload } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────────

export interface StreamingToolCall {
  name: string;
  label: string;
  args?: Record<string, unknown>;
  status: "running" | "done" | "error";
  viz?: VizPayload;
  sources?: string[];
  errorMsg?: string;
}

export interface BubbleMessage {
  id: string;
  role: "user" | "assistant" | "tool";
  content: string;
  toolCalls?: StreamingToolCall[];
  sources?: string[];
  confidence?: number | null;
  isStreaming?: boolean;
  created_at?: string;
}

// ── Article list ───────────────────────────────────────────────────────────────

interface ArticleItem {
  entity?: string;
  summary?: string;
  sentiment?: number;
  category?: string;
  source?: string;
  score?: number;
  url?: string;
  published_at?: string;
}

function ArticlesTable({ items }: { items: ArticleItem[] }) {
  if (!items || items.length === 0) {
    return <p className="text-slate-500 text-xs mt-2">No articles found.</p>;
  }
  return (
    <div className="mt-2 space-y-2">
      {items.map((item, i) => {
        const sentiment = item.sentiment ?? 0;
        const sentimentColor =
          sentiment > 0.1 ? "#00FF87" : sentiment < -0.1 ? "#FF4B2B" : "#94a3b8";
        return (
          <div
            key={i}
            className="rounded-lg bg-white/5 border border-white/5 px-3 py-2 text-xs"
          >
            <div className="flex items-center justify-between gap-2 mb-1">
              <div className="flex items-center gap-2">
                {item.entity && (
                  <span className="px-1.5 py-0.5 rounded bg-primary/10 text-primary text-[10px] font-bold uppercase tracking-wide">
                    {item.entity}
                  </span>
                )}
                {item.category && (
                  <span className="text-slate-500 text-[10px]">{item.category}</span>
                )}
              </div>
              <span className="font-mono text-[10px]" style={{ color: sentimentColor }}>
                {sentiment >= 0 ? "+" : ""}
                {sentiment.toFixed(2)}
              </span>
            </div>
            <p className="text-slate-300 leading-relaxed">{item.summary}</p>
            <div className="flex items-center justify-between mt-1">
              <span className="text-slate-600 text-[10px]">{item.source}</span>
              {item.url && (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary text-[10px] hover:underline"
                >
                  Source ↗
                </a>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Entity card ────────────────────────────────────────────────────────────────

interface EntityCardData {
  label?: string;
  type?: string;
  sector?: string;
  description?: string;
  event_count?: number;
  relationship_count?: number;
  latest_sentiment?: number | null;
}

function EntityCard({ data }: { data: EntityCardData }) {
  const sentiment = data.latest_sentiment ?? null;
  const sentimentColor =
    sentiment !== null
      ? sentiment > 0.1
        ? "#00FF87"
        : sentiment < -0.1
          ? "#FF4B2B"
          : "#94a3b8"
      : "#94a3b8";

  return (
    <div className="mt-2 rounded-xl bg-white/5 border border-white/10 p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-white font-bold text-base">{data.label}</h3>
          <p className="text-slate-400 text-xs mt-0.5">
            {data.type}
            {data.sector ? ` · ${data.sector}` : ""}
          </p>
          {data.description && (
            <p className="text-slate-400 text-xs mt-2 leading-relaxed max-w-sm">
              {data.description}
            </p>
          )}
        </div>
        {sentiment !== null && (
          <div className="text-right shrink-0">
            <p className="text-[9px] uppercase font-bold tracking-widest text-slate-500">
              Sentiment
            </p>
            <p className="text-xl font-bold font-mono" style={{ color: sentimentColor }}>
              {sentiment >= 0 ? "+" : ""}
              {sentiment.toFixed(3)}
            </p>
          </div>
        )}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <div className="rounded-lg bg-white/5 border border-white/5 px-3 py-2">
          <p className="text-[9px] uppercase font-bold tracking-widest text-slate-500">
            Events
          </p>
          <p className="text-lg font-bold text-primary font-mono">
            {data.event_count ?? 0}
          </p>
        </div>
        <div className="rounded-lg bg-white/5 border border-white/5 px-3 py-2">
          <p className="text-[9px] uppercase font-bold tracking-widest text-slate-500">
            Relationships
          </p>
          <p className="text-lg font-bold text-amber-400 font-mono">
            {data.relationship_count ?? 0}
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Tracker added confirmation card ───────────────────────────────────────────

interface TrackerAddedData {
  entity_name?: string;
  entity_type?: string;
  sector?: string | null;
  sources?: string[];
  interval_minutes?: number;
  already_existed?: boolean;
}

const SOURCE_ICONS: Record<string, string> = {
  "Google News": "newspaper",
  "Global News": "newspaper",
  "Reddit Subreddit": "alternate_email",
  "Reddit Hub": "alternate_email",
  "Nitter/X User": "alternate_email",
  "X (Twitter)": "alternate_email",
  RSS: "rss_feed",
};

function TrackerAddedCard({ data }: { data: TrackerAddedData }) {
  return (
    <div className="mt-2 rounded-xl border p-4"
      style={{ background: "rgba(236,91,19,0.06)", borderColor: "rgba(236,91,19,0.25)" }}
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="material-symbols-outlined text-base text-primary">
          {data.already_existed ? "check_circle" : "add_circle"}
        </span>
        <span className="text-xs font-bold uppercase tracking-widest text-primary">
          {data.already_existed ? "Already Tracked" : "Tracker Added"}
        </span>
      </div>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-white font-bold text-base">{data.entity_name}</p>
          <p className="text-slate-400 text-xs mt-0.5">
            {data.entity_type}
            {data.sector ? ` · ${data.sector}` : ""}
          </p>
        </div>
        <div className="text-right shrink-0">
          <p className="text-[9px] uppercase font-bold tracking-widest text-slate-500">Interval</p>
          <p className="text-sm font-bold font-mono text-slate-300">
            {data.interval_minutes ?? 60}m
          </p>
        </div>
      </div>
      {data.sources && data.sources.length > 0 && (
        <div className="mt-3">
          <p className="text-[9px] uppercase font-bold tracking-widest text-slate-500 mb-1.5">Sources</p>
          <div className="flex flex-wrap gap-1.5">
            {data.sources.map((src, i) => (
              <span key={i} className="flex items-center gap-1 px-2 py-1 rounded-lg bg-white/5 border border-primary/20 text-[11px] text-slate-300">
                <span className="material-symbols-outlined text-xs text-primary">
                  {SOURCE_ICONS[src] ?? "database"}
                </span>
                {src}
              </span>
            ))}
          </div>
        </div>
      )}
      {!data.already_existed && (
        <p className="mt-3 text-[11px] text-slate-500 leading-relaxed">
          Intelligence collection is now scheduled. Data will appear as the scrapers run.
        </p>
      )}
    </div>
  );
}

// ── Entity list ────────────────────────────────────────────────────────────────

interface EntityListItem {
  label?: string;
  type?: string;
  sector?: string;
  description?: string;
}

function EntityList({ items }: { items: EntityListItem[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="mt-2 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
      {items.map((e, i) => (
        <div
          key={i}
          className="rounded-lg bg-white/5 border border-white/5 px-3 py-2 text-xs"
        >
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-200">{e.label}</span>
            <span className="text-[10px] text-slate-500">{e.type}</span>
          </div>
          {e.sector && <p className="text-slate-500 text-[10px] mt-0.5">{e.sector}</p>}
        </div>
      ))}
    </div>
  );
}

// ── Stock card ───────────────────────────────────────────────────────────────

interface StockCardData {
  ticker?: string;
  name?: string;
  current_price?: number | null;
  currency?: string;
  market_cap?: number | null;
  pe_ratio?: number | null;
  "52_week_low"?: number | null;
  "52_week_high"?: number | null;
  volume?: number | null;
  avg_volume?: number | null;
  "30d_change_pct"?: number | null;
  sector?: string | null;
  industry?: string | null;
  exchange?: string | null;
}

function formatLargeNumber(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  return n.toLocaleString();
}

function StockCard({ data }: { data: StockCardData }) {
  const change = data["30d_change_pct"];
  const changeColor = change == null ? "#94a3b8" : change >= 0 ? "#00FF87" : "#FF4B2B";
  const changeSign = change != null && change >= 0 ? "+" : "";

  return (
    <div className="mt-2 rounded-xl bg-white/5 border border-white/10 p-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-base text-primary">candlestick_chart</span>
            <h3 className="text-white font-bold text-base">{data.name ?? data.ticker}</h3>
            <span className="px-1.5 py-0.5 rounded bg-primary/10 text-primary text-[10px] font-bold font-mono">
              {data.ticker}
            </span>
          </div>
          <p className="text-slate-500 text-xs mt-0.5">
            {[data.exchange, data.sector, data.industry].filter(Boolean).join(" · ")}
          </p>
        </div>
        <div className="text-right shrink-0">
          <p className="text-2xl font-bold font-mono text-white">
            {data.current_price != null
              ? `${data.currency ?? "$"}${data.current_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : "—"}
          </p>
          {change != null && (
            <p className="text-sm font-mono font-semibold" style={{ color: changeColor }}>
              {changeSign}{change.toFixed(2)}% <span className="text-slate-600 text-xs font-normal">30d</span>
            </p>
          )}
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {([
          { label: "Market Cap", value: formatLargeNumber(data.market_cap) },
          { label: "P/E Ratio", value: data.pe_ratio != null ? data.pe_ratio.toFixed(1) : "—" },
          { label: "52W Low", value: data["52_week_low"] != null ? `$${data["52_week_low"]?.toFixed(2)}` : "—" },
          { label: "52W High", value: data["52_week_high"] != null ? `$${data["52_week_high"]?.toFixed(2)}` : "—" },
        ] as { label: string; value: string }[]).map(({ label, value }) => (
          <div key={label} className="rounded-lg bg-white/5 border border-white/5 px-3 py-2">
            <p className="text-[9px] uppercase font-bold tracking-widest text-slate-500">{label}</p>
            <p className="text-sm font-bold font-mono text-slate-200">{value}</p>
          </div>
        ))}
      </div>

      {/* Volume row */}
      {(data.volume != null || data.avg_volume != null) && (
        <div className="mt-2 flex gap-4 text-[10px] text-slate-500 font-mono px-1">
          {data.volume != null && <span>Vol {data.volume.toLocaleString()}</span>}
          {data.avg_volume != null && <span>Avg Vol {data.avg_volume.toLocaleString()}</span>}
        </div>
      )}
    </div>
  );
}

// ── VizBlock — renders the correct viz from a tool result ──────────────────────

function VizBlock({ viz }: { viz?: VizPayload }) {
  if (!viz) return null;

  if (viz.type === "articles") {
    return <ArticlesTable items={viz.data as ArticleItem[]} />;
  }
  if (viz.type === "entity_card") {
    return <EntityCard data={viz.data as EntityCardData} />;
  }
  if (viz.type === "entity_list") {
    return <EntityList items={viz.data as EntityListItem[]} />;
  }
  if (viz.type === "tracker_added") {
    return <TrackerAddedCard data={viz.data as TrackerAddedData} />;
  }
  if (viz.type === "stock_card") {
    return <StockCard data={viz.data as StockCardData} />;
  }
  if (viz.type === "graph") {
    const graphData = viz.data as { nodes: unknown[]; edges: unknown[] };
    return (
      <GraphRenderer
        nodes={graphData.nodes as Parameters<typeof GraphRenderer>[0]["nodes"]}
        edges={graphData.edges as Parameters<typeof GraphRenderer>[0]["edges"]}
        title={viz.config?.title as string | undefined}
      />
    );
  }
  if (
    viz.type === "chart:line" ||
    viz.type === "chart:composed" ||
    viz.type === "chart:bar" ||
    viz.type === "chart:histogram" ||
    viz.type === "chart:pie"
  ) {
    return (
      <ChartRenderer
        type={viz.type}
        data={viz.data as Record<string, unknown>[]}
        config={viz.config as Parameters<typeof ChartRenderer>[0]["config"]}
        summary={viz.summary as Parameters<typeof ChartRenderer>[0]["summary"]}
      />
    );
  }
  return null;
}

// ── Sentiment bar (confidence) ─────────────────────────────────────────────────

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div className="mt-3">
      <div className="flex justify-between items-center mb-1">
        <span className="text-[10px] uppercase font-bold tracking-widest text-slate-500">
          Confidence Score
        </span>
        <span className="text-[10px] font-mono text-primary">{pct}% Match</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-white/10">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${pct}%`,
            background: "linear-gradient(90deg, #ec5b13, #f59e0b)",
          }}
        />
      </div>
    </div>
  );
}

// ── Source chips ───────────────────────────────────────────────────────────────

function SourceChips({
  sources,
  toolCalls,
}: {
  sources: string[];
  toolCalls?: StreamingToolCall[];
}) {
  if (!sources || sources.length === 0) return null;

  // Build source → tool names map for hover tooltips
  const viaMap: Record<string, string[]> = {};
  if (toolCalls) {
    for (const tc of toolCalls) {
      for (const src of tc.sources ?? []) {
        if (!viaMap[src]) viaMap[src] = [];
        if (!viaMap[src].includes(tc.name)) viaMap[src].push(tc.name);
      }
    }
  }

  const icons: Record<string, string> = {
    reddit: "alternate_email",
    nitter: "alternate_email",
    rss: "rss_feed",
    news: "newspaper",
    "reuters intel": "newspaper",
    "market data": "candlestick_chart",
    "intelligence db": "database",
    "knowledge graph db": "hub",
    "system db": "database",
    yfinance: "candlestick_chart",
    duckduckgo: "travel_explore",
    "llm synthesis": "auto_awesome",
  };
  return (
    <div className="mt-3">
      <p className="text-[10px] uppercase font-bold tracking-widest text-slate-500 mb-1.5">
        Source Attribution
      </p>
      <div className="flex flex-wrap gap-1.5">
        {sources.map((src, i) => {
          const icon = icons[src.toLowerCase()] ?? "source";
          const viaTools = viaMap[src] ?? [];
          return (
            <div key={i} className="relative group">
              <span className="flex items-center gap-1 px-2 py-1 rounded-lg bg-white/5 border border-white/10 text-[11px] text-slate-300 cursor-default">
                <span className="material-symbols-outlined text-xs text-primary">{icon}</span>
                {src}
              </span>
              {viaTools.length > 0 && (
                <div
                  className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2
                             pointer-events-none opacity-0 group-hover:opacity-100
                             transition-opacity duration-150
                             min-w-max rounded-xl px-3 py-2 shadow-2xl"
                  style={{
                    background: "rgba(10, 21, 32, 0.97)",
                    border: "1px solid rgba(0,208,255,0.20)",
                  }}
                >
                  <p className="text-[9px] uppercase tracking-widest text-slate-500 mb-1.5">
                    Generated via
                  </p>
                  {viaTools.map((t, j) => (
                    <p key={j} className="flex items-center gap-1.5 font-mono text-[11px] text-primary">
                      <span className="material-symbols-outlined text-xs">function</span>
                      {t}
                    </p>
                  ))}
                  <div
                    className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0"
                    style={{
                      borderLeft: "5px solid transparent",
                      borderRight: "5px solid transparent",
                      borderTop: "5px solid rgba(0,208,255,0.20)",
                    }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Audit trail ───────────────────────────────────────────────────────────────

function formatArgs(args?: Record<string, unknown>): string | null {
  if (!args || Object.keys(args).length === 0) return null;
  return Object.entries(args)
    .map(([k, v]) => `${k}=${typeof v === "string" ? `"${v}"` : JSON.stringify(v)}`)
    .join(" · ");
}

function resultSummary(tc: StreamingToolCall): string {
  if (tc.status === "error") return tc.errorMsg ?? "error";
  const viz = tc.viz;
  if (!viz) return "—";
  const data = viz.data as unknown;
  if (Array.isArray(data))
    return `${data.length} record${data.length !== 1 ? "s" : ""} · ${viz.type}`;
  return viz.type;
}

const TOOL_AUDIT_ICONS: Record<string, string> = {
  search_intelligence: "manage_search",
  get_entity_intelligence: "person_search",
  get_sentiment_timeline: "show_chart",
  get_knowledge_graph: "hub",
  get_market_correlation: "candlestick_chart",
  get_sector_heatmap: "bar_chart",
  search_entities: "search",
  get_recent_events: "feed",
  read_article: "article",
  add_entity_tracker: "add_circle",
  compare_entities: "compare",
  get_cross_entity_events: "join_inner",
  detect_sentiment_spike: "crisis_alert",
  get_risk_signals: "warning",
  get_trending_entities: "trending_up",
  list_trackers: "list",
  set_tracker_status: "toggle_on",
  remove_entity_tracker: "delete",
  get_scrape_health: "health_and_safety",
  web_search: "travel_explore",
  fetch_url: "open_in_new",
  get_stock_info: "attach_money",
  compare_sentiment_vs_sector: "stacked_line_chart",
  find_related_entities: "account_tree",
  summarize_entity_brief: "summarize",
};

function AuditTrail({ toolCalls }: { toolCalls: StreamingToolCall[] }) {
  const [open, setOpen] = useState(false);
  const completed = toolCalls.filter(
    (tc) => tc.status === "done" || tc.status === "error",
  );
  if (completed.length === 0) return null;

  return (
    <div className="mt-3 border-t border-white/5 pt-2">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 text-[10px] uppercase tracking-widest text-slate-600 hover:text-slate-400 transition-colors"
      >
        <span className="material-symbols-outlined text-xs">
          {open ? "expand_less" : "expand_more"}
        </span>
        Audit Trail · {completed.length} tool{completed.length !== 1 ? "s" : ""} called
      </button>

      {open && (
        <div className="mt-2 space-y-1">
          {completed.map((tc, i) => {
            const icon = TOOL_AUDIT_ICONS[tc.name] ?? "function";
            const argsStr = formatArgs(tc.args);
            const resultStr = resultSummary(tc);
            const isError = tc.status === "error";

            return (
              <div
                key={i}
                className={`rounded-lg px-3 py-2 text-[10px] border ${
                  isError
                    ? "bg-red-500/5 border-red-500/15"
                    : "bg-white/5 border-white/5"
                }`}
              >
                <div className="flex items-center gap-2 mb-0.5">
                  <span
                    className={`material-symbols-outlined text-xs ${
                      isError ? "text-red-400" : "text-primary"
                    }`}
                  >
                    {icon}
                  </span>
                  <span className="font-mono font-semibold text-slate-300">{tc.name}</span>
                  <span className="text-slate-600 truncate hidden sm:block">{tc.label}</span>
                  <span
                    className={`ml-auto font-mono shrink-0 ${
                      isError ? "text-red-400" : "text-emerald-400"
                    }`}
                  >
                    {isError ? "✗ error" : "✓ done"}
                  </span>
                </div>
                {argsStr && (
                  <p className="font-mono text-slate-500 mt-0.5 break-all">
                    <span className="text-slate-600">args </span>
                    {argsStr}
                  </p>
                )}
                <p className="font-mono text-slate-500 mt-0.5">
                  <span className="text-slate-600">result </span>
                  {resultStr}
                  {tc.sources && tc.sources.length > 0 && (
                    <span className="text-slate-600">
                      {" · "}sources {tc.sources.join(", ")}
                    </span>
                  )}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Main MessageBubble component ────────────────────────────────────────────────

export default function MessageBubble({ message }: { message: BubbleMessage }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div
          className="max-w-[75%] px-4 py-3 rounded-2xl rounded-tr-sm text-sm text-slate-100 leading-relaxed"
          style={{
            background:
              "linear-gradient(135deg, rgba(236,91,19,0.12) 0%, rgba(236,91,19,0.06) 100%)",
            border: "1px solid rgba(236,91,19,0.2)",
          }}
        >
          {message.content}
          {message.created_at && (
            <p className="text-[10px] text-slate-600 mt-1.5 text-right font-mono">
              {new Date(message.created_at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </p>
          )}
        </div>
      </div>
    );
  }

  // Assistant message
  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[90%] w-full">
        {/* Card header */}
        <div className="flex items-center gap-2 mb-2">
          <div className="w-6 h-6 rounded-md bg-primary/10 border border-primary/20 flex items-center justify-center">
            <span className="material-symbols-outlined text-xs text-primary">terminal</span>
          </div>
          <span className="text-[10px] uppercase font-bold tracking-widest text-slate-500">
            {message.isStreaming ? (
              <span className="text-primary animate-pulse">PROCESSING RESPONSE...</span>
            ) : (
              "ANALYSIS COMPLETE"
            )}
          </span>
        </div>

        <div
          className="rounded-2xl rounded-tl-sm p-4"
          style={{
            background: "rgba(15, 25, 35, 0.8)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          {/* Tool call indicators (while running) */}
          {message.toolCalls &&
            message.toolCalls
              .filter((tc) => tc.status === "running")
              .map((tc, i) => (
                <ToolCallIndicator key={i} toolName={tc.name} label={tc.label} />
              ))}

          {/* Tool results (viz blocks) */}
          {message.toolCalls &&
            message.toolCalls
              .filter((tc) => tc.status === "done" && tc.viz)
              .map((tc, i) => (
                <div key={i}>
                  <VizBlock viz={tc.viz} />
                </div>
              ))}

          {/* Tool errors */}
          {message.toolCalls &&
            message.toolCalls
              .filter((tc) => tc.status === "error")
              .map((tc, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs mb-2"
                >
                  <span className="material-symbols-outlined text-sm">error</span>
                  Tool error ({tc.name}): {tc.errorMsg}
                </div>
              ))}

          {/* Text content */}
          {message.content && (
            <div className="text-sm text-slate-300 leading-relaxed prose prose-invert prose-sm max-w-none [&>p]:mb-2 [&>ul]:list-disc [&>ul]:pl-4 [&>ol]:list-decimal [&>ol]:pl-4 [&>h3]:text-slate-100 [&>h3]:font-semibold [&>code]:text-primary [&>code]:font-mono [&>strong]:text-slate-100">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}

          {/* Streaming cursor */}
          {message.isStreaming && !message.content && (
            <span className="inline-block w-2 h-4 bg-primary opacity-70 animate-pulse rounded-sm" />
          )}

          {/* Confidence bar */}
          {typeof message.confidence === "number" && message.confidence > 0 && (
            <ConfidenceBar value={message.confidence} />
          )}

          {/* Source attribution */}
          {message.sources && message.sources.length > 0 && (
            <SourceChips sources={message.sources} toolCalls={message.toolCalls} />
          )}

          {/* Audit trail */}
          {message.toolCalls && message.toolCalls.length > 0 && (
            <AuditTrail toolCalls={message.toolCalls} />
          )}

          {message.created_at && !message.isStreaming && (
            <p className="text-[10px] text-slate-600 mt-2 font-mono">
              {new Date(message.created_at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
