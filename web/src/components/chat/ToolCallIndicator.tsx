"use client";

import React from "react";

const TOOL_ICONS: Record<string, string> = {
  search_intelligence: "search",
  get_entity_intelligence: "person_search",
  get_sentiment_timeline: "show_chart",
  get_knowledge_graph: "hub",
  get_market_correlation: "candlestick_chart",
  get_sector_heatmap: "bar_chart",
  search_entities: "manage_search",
  get_recent_events: "feed",
  read_article: "article",
  add_entity_tracker: "add_circle",
};

interface ToolCallIndicatorProps {
  toolName: string;
  label: string;
}

export default function ToolCallIndicator({ toolName, label }: ToolCallIndicatorProps) {
  const icon = TOOL_ICONS[toolName] ?? "smart_toy";

  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 border border-primary/20 text-primary text-xs font-mono w-fit my-1">
      <span
        className="material-symbols-outlined text-sm animate-pulse"
        style={{ color: "#ec5b13" }}
      >
        {icon}
      </span>
      <span className="animate-pulse">{label}</span>
      <span className="flex gap-0.5 ml-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-1 h-1 rounded-full bg-primary"
            style={{
              animation: `bounce 1s ease-in-out ${i * 0.2}s infinite`,
            }}
          />
        ))}
      </span>
    </div>
  );
}
