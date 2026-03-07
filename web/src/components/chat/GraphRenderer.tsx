"use client";

import React, { useEffect, useRef, useCallback } from "react";

interface GraphNode {
  id: string;
  label: string;
  type?: string;
  sentiment?: number;
}

interface GraphEdge {
  source: string;
  target: string;
  weight?: number;
  sentiment?: number;
}

interface GraphRendererProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  title?: string;
}

const NODE_COLORS: Record<string, string> = {
  COMPANY: "#00d0ff",
  PERSON: "#00FF87",
  LOCATION: "#f59e0b",
  ORG: "#a855f7",
  TOPIC: "#ec4899",
  PRODUCT: "#f97316",
  UNKNOWN: "#64748b",
};

export default function GraphRenderer({ nodes, edges, title }: GraphRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(null);

  const initGraph = useCallback(async () => {
    if (!containerRef.current || nodes.length === 0) return;

    // Dynamically import to avoid SSR issues
    const ForceGraph2D = (await import("react-force-graph-2d")).default;
    const React = (await import("react")).default;
    const ReactDOM = (await import("react-dom/client")).default;

    // Unmount previous if any
    if (graphRef.current) {
      graphRef.current.unmount?.();
    }

    const graphData = {
      nodes: nodes.map((n) => ({ ...n })),
      links: edges.map((e) => ({ ...e })),
    };

    const root = ReactDOM.createRoot(containerRef.current);
    graphRef.current = root;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const graphProps: any = {
      graphData,
      width: containerRef.current.offsetWidth || 600,
      height: 380,
      backgroundColor: "transparent",
      nodeLabel: (node: GraphNode) => node.label,
      nodeColor: (node: GraphNode) =>
        NODE_COLORS[node.type ?? "UNKNOWN"] ?? NODE_COLORS.UNKNOWN,
      nodeRelSize: 5,
      linkWidth: (link: GraphEdge) =>
        Math.max(1, Math.min((link.weight ?? 1) * 0.5, 4)),
      linkColor: () => "rgba(255,255,255,0.15)",
      nodeCanvasObjectMode: () => "after",
      nodeCanvasObject: (
        node: GraphNode & { x?: number; y?: number },
        ctx: CanvasRenderingContext2D,
        globalScale: number,
      ) => {
        const label = node.label;
        const fontSize = Math.max(10, 14 / globalScale);
        ctx.font = `${fontSize}px Inter, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = "rgba(226,232,240,0.85)";
        if (node.x !== undefined && node.y !== undefined) {
          ctx.fillText(label, node.x, node.y + 8);
        }
      },
      cooldownTicks: 100,
    };

    root.render(React.createElement(ForceGraph2D, graphProps));
  }, [nodes, edges]);

  useEffect(() => {
    initGraph();
    return () => {
      graphRef.current?.unmount?.();
    };
  }, [initGraph]);

  if (nodes.length === 0) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-4 mt-2 flex items-center justify-center h-[200px]">
        <p className="text-slate-500 text-sm">No graph data available.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 mt-2 overflow-hidden">
      {title && (
        <div className="px-4 pt-3 pb-1">
          <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400">{title}</p>
        </div>
      )}
      {/* Legend */}
      <div className="px-4 pb-2 flex flex-wrap gap-3">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <span key={type} className="flex items-center gap-1 text-[10px] text-slate-500">
            <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: color }} />
            {type}
          </span>
        ))}
      </div>
      <div ref={containerRef} className="w-full" style={{ height: 380 }} />
    </div>
  );
}
