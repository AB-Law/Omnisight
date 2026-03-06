"use client";

import { useEffect, useState, useMemo, useRef } from "react";
import dynamic from "next/dynamic";
import { cn } from "@/lib/utils";
import { forceCollide } from "d3-force";

// Load ForceGraph2D dynamically to avoid SSR issues
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

export default function KnowledgeGraph() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  
  // Node Selection State
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [nodeDetails, setNodeDetails] = useState<any>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  
  // Edge Selection State
  const [selectedEdge, setSelectedEdge] = useState<any>(null);
  const [edgeDetails, setEdgeDetails] = useState<any>(null);
  const [loadingEdgeDetails, setLoadingEdgeDetails] = useState(false);

  const [density, setDensity] = useState(0);
  const [showPeople, setShowPeople] = useState(true);
  const [hoveredNode, setHoveredNode] = useState<any>(null);
  const graphRef = useRef<any>(null);

  // Memoize processed graph data for stability and performance
  const processedData = useMemo(() => {
    if (!data || !data.nodes) return { nodes: [], links: [] };

    // 1. Sanitize and Map ID
    const sanitizedNodes = data.nodes
      .filter((n: any) => showPeople ? true : n.type !== 'PERSON')
      .map((n: any) => ({
        ...n,
        id: (n.id || n.name) as string,
        degree: 0 // Initialize degree
      }));

    const nodeMap = new Map<string, any>(sanitizedNodes.map((n: any) => [n.id, n]));

    // 2. Process Links and Calculate Degree
    const filteredLinks = (data.edges || [])
      .filter((link: any) => {
        const sourceExists = nodeMap.has(link.source);
        const targetExists = nodeMap.has(link.target);
        const meetsDensity = (link.weight || 0) >= (density / 100);
        return sourceExists && targetExists && meetsDensity;
      })
      .map((link: any) => {
        // Increment degree for source and target
        const s = nodeMap.get(link.source);
        const t = nodeMap.get(link.target);
        if (s) (s as any).degree = ((s as any).degree || 0) + 1;
        if (t) (t as any).degree = ((t as any).degree || 0) + 1;
        return { ...link };
      });

    // 3. Filter Orphaned Satellites
    // If we're hiding people, also hide random entities (like ORGs or Topics) that were ONLY connected to those people 
    // and thus now have 0 edges. We preserve actual Companies as structural anchors.
    const finalNodes = !showPeople
      ? sanitizedNodes.filter((n: any) => n.degree > 0 || n.type === 'COMPANY')
      : sanitizedNodes;

    return { nodes: finalNodes, links: filteredLinks };
  }, [data, density, showPeople]);

  useEffect(() => {
    if (graphRef.current) {
        console.log("OS-DEBUG: Tuning Graph Physics");
        
        // Repel nodes, but not so violently that they bounce endlessly
        graphRef.current.d3Force?.('charge')?.strength(-400);
        
        // Set a reasonable link distance so edges are long enough to read text
        graphRef.current.d3Force?.('link')?.distance(150); 
        
        // Extremely strict collision detection prevents nodes (and their labels) from clustering
        const collideForce = forceCollide().radius((node: any) => {
             const degree = node.degree || 1;
             const radius = Math.sqrt(degree) * 2 + 3;
             return radius + 55; // 55px buffer guarantees names won't overlap
        }).strength(1).iterations(6);
        
        graphRef.current.d3Force?.('collide', collideForce);
        
        // Normal friction so things settle down
        if (typeof graphRef.current.d3VelocityDecay === 'function') {
            graphRef.current.d3VelocityDecay(0.4);
        }

        // Center force to keep the cluster roughly near the middle
        graphRef.current.d3Force?.('center')?.strength(0.05);

        // Re-heat simulation mildly to apply forces without throwing nodes offscreen
        if (typeof graphRef.current.d3Alpha === 'function') {
            graphRef.current.d3Alpha(0.6);
        }
        if (typeof graphRef.current.d3AlphaTarget === 'function' && typeof graphRef.current.restart === 'function') {
            graphRef.current.d3AlphaTarget(0).restart();
        }
    }
  }, [processedData]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8000/knowledge-graph");
        const json = await res.json();
        setData(json);
      } catch (err) {
        console.error("Failed to fetch knowledge graph:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  useEffect(() => {
    if (selectedNode) {
      const fetchDetails = async () => {
        setLoadingDetails(true);
        try {
          const res = await fetch(`http://127.0.0.1:8000/knowledge-graph/entity/${encodeURIComponent(selectedNode.id)}/details`);
          if (res.ok) {
            setNodeDetails(await res.json());
          }
        } catch (e) {
          console.error("Failed to fetch node details", e);
        } finally {
          setLoadingDetails(false);
        }
      };
      fetchDetails();
    }
  }, [selectedNode]);

  useEffect(() => {
    if (selectedEdge) {
      const fetchEdgeDetails = async () => {
        setLoadingEdgeDetails(true);
        try {
          // Both nodes might have their id mapped
          const source = typeof selectedEdge.source === 'object' ? selectedEdge.source.id : selectedEdge.source;
          const target = typeof selectedEdge.target === 'object' ? selectedEdge.target.id : selectedEdge.target;
          
          const res = await fetch(`http://127.0.0.1:8000/knowledge-graph/edge/details?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`);
          if (res.ok) {
            setEdgeDetails(await res.json());
          }
        } catch (e) {
             console.error("Failed to fetch edge details", e);
        } finally {
            setLoadingEdgeDetails(false);
        }
      };
      fetchEdgeDetails();
    }
  }, [selectedEdge]);

  const handleNodeClick = (node: any) => {
    setSelectedNode(node);
    setSelectedEdge(null);
    if (graphRef.current) {
        graphRef.current.centerAt(node.x, node.y, 400);
        graphRef.current.zoom(2.5, 400);
    }
  };

  const handleLinkClick = (link: any, event: any) => {
     setSelectedEdge(link);
     setSelectedNode(null);
  };

  if (loading) return <div className="text-slate-400 animate-pulse flex h-screen items-center justify-center">Synthesizing Neural Graph...</div>;

  return (
    <div className="flex flex-col h-full relative tech-grid">
      {/* Header */}
      <header className="h-16 border-b border-white/10 flex items-center justify-between px-8 bg-black/40 glass-panel z-50 shrink-0">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3 text-primary">
            <span className="material-symbols-outlined text-3xl">hub</span>
            <h2 className="text-white text-xl font-bold tracking-tight">The Knowledge Network</h2>
          </div>
          <div className="h-6 w-px bg-white/10"></div>
          <label className="relative flex items-center w-80">
            <span className="material-symbols-outlined absolute left-3 text-slate-400 text-xl">search</span>
            <input 
                className="w-full bg-white/5 border-none rounded-xl py-2 pl-10 pr-4 text-sm text-slate-100 focus:ring-1 focus:ring-primary/50 placeholder:text-slate-500 outline-none" 
                placeholder="Search nodes, entities or relations..." 
                type="text"
            />
          </label>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex gap-2">
            <button className="p-2 rounded-xl glass-panel hover:bg-white/10 transition-colors text-slate-400 flex items-center justify-center">
              <span className="material-symbols-outlined">settings</span>
            </button>
            <button className="p-2 rounded-xl glass-panel hover:bg-white/10 transition-colors text-slate-400 flex items-center justify-center">
              <span className="material-symbols-outlined">share</span>
            </button>
          </div>
          <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center font-bold text-xs text-white">JD</div>
        </div>
      </header>

      {/* Graph Area */}
      <main className="flex-1 relative overflow-hidden">
        <div className="absolute inset-0 z-0">
            {processedData.nodes.length > 0 ? (
                <ForceGraph2D
                    ref={graphRef}
                    graphData={processedData}
                    nodeLabel="id"
                    nodeRelSize={7}
                    linkColor={(link: any) => {
                        if (selectedEdge && link === selectedEdge) {
                             return 'rgba(0, 255, 135, 1)'; // Highlight selected link brightly
                        }
                        if (selectedNode) {
                            return (link.source.id === selectedNode.id || link.target.id === selectedNode.id) 
                                ? 'rgba(236, 91, 19, 0.6)' 
                                : 'rgba(255, 255, 255, 0.03)';
                        }
                        return 'rgba(255, 255, 255, 0.1)';
                    }}
                    linkWidth={(link: any) => {
                        if (selectedEdge && link === selectedEdge) return 3;
                        return selectedNode && (link.source.id === selectedNode.id || link.target.id === selectedNode.id) ? 2 : 1;
                    }}
                    linkCurvature={0.2}
                    linkDirectionalParticles={2}
                    linkDirectionalParticleSpeed={0.005}
                    linkDirectionalParticleWidth={(link: any) => (selectedEdge && link === selectedEdge) ? 4 : 1.5}
                    onNodeClick={handleNodeClick}
                    onLinkClick={handleLinkClick}
                    onNodeHover={setHoveredNode}
                    backgroundColor="transparent"
                    nodeCanvasObject={(node: any, ctx: any, globalScale: any) => {
                        const label = node.id;
                        const degree = node.degree || 1;
                        const radius = Math.sqrt(degree) * 1.2 + 2;
                        const isMainHub = degree > 4;
                        const isSelected = selectedNode?.id === node.id;
                        const isHovered = hoveredNode?.id === node.id;
                        
                        // Connection/Neighbor logic
                        let isConnected = false;
                        if (selectedNode) {
                           isConnected = processedData.links.some((l: any) => 
                               (l.source.id === node.id && l.target.id === selectedNode.id) ||
                               (l.target.id === node.id && l.source.id === selectedNode.id)
                           );
                        }

                        // Dimming logic
                        let opacity = 1;
                        if (selectedNode && !isSelected && !isConnected) opacity = 0.15;

                        ctx.globalAlpha = opacity;
                        ctx.fillStyle = node.type === 'USER' ? '#00FF87' : node.type === 'COMPANY' ? '#00D2FF' : '#ec5b13';
                        
                        ctx.beginPath(); 
                        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false); 
                        ctx.fill();

                        // Hub and Selected Glow
                        if (isMainHub || isSelected || isHovered) {
                            ctx.shadowColor = ctx.fillStyle;
                            ctx.shadowBlur = (isMainHub ? 15 : 25) / globalScale;
                            ctx.fill();
                            ctx.shadowBlur = 0;
                        }

                        // Label Rendering
                        // Render if: zoomed in OR major hub OR is highligted selection OR is a neighbor of selection
                        if (globalScale > 1.8 || isMainHub || isSelected || isConnected) {
                            const fontSize = (isMainHub || isSelected ? 14 : 11) / globalScale;
                            ctx.font = `${isSelected ? 'bold' : '500'} ${fontSize}px "Public Sans"`;
                            ctx.textAlign = 'center';
                            ctx.textBaseline = 'middle';
                            ctx.fillStyle = isSelected ? '#fff' : isConnected ? 'rgba(255, 255, 255, 0.9)' : 'rgba(255, 255, 255, 0.8)';
                            ctx.fillText(label, node.x, node.y + radius + (8 / globalScale));
                        }
                        ctx.globalAlpha = 1;
                    }}
                />
            ) : (
                <div className="flex items-center justify-center h-full text-slate-400 font-mono text-xs uppercase animate-pulse tracking-widest">
                    {loading ? "Compiling Neural Graph..." : "No relationships match signal intensity"}
                </div>
            )}
        </div>

        {/* Right Detail Panel */}
        <aside className={cn(
            "absolute top-6 right-6 bottom-6 w-[400px] max-w-[90vw] rounded-xl flex flex-col z-40 overflow-hidden border border-white/10 transition-transform duration-500 bg-[#0a0a0a]/95 backdrop-blur-2xl shadow-[0_0_40px_rgba(0,0,0,0.9)]",
            (selectedNode || selectedEdge) ? "translate-x-0" : "translate-x-[120%]"
        )}>
          {selectedNode && (
            <>
              <div className="p-6 border-b border-white/10">
                <h3 className="text-slate-400 text-xs font-bold uppercase tracking-widest mb-1">Entity Deep-Dive</h3>
                <h2 className="text-xl font-bold text-white">{selectedNode.id || "Unknown Entity"}</h2>
                <p className="text-slate-500 text-xs font-mono mt-1">UUID: {String(selectedNode.id || 'N/A').toUpperCase().slice(0,3)}-{Math.floor(Math.random()*900)+100}-OS</p>
              </div>
              <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
                {loadingDetails ? (
                   <div className="flex items-center justify-center h-full text-slate-500 animate-pulse text-xs">Analyzing Node Vectors...</div>
                ) : (
                  <>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 rounded-lg bg-white/5 border border-white/5 text-center">
                        <p className="text-slate-500 text-[10px] uppercase font-bold">Connections</p>
                        <p className="text-2xl font-bold text-cyan-node">{nodeDetails?.connections || 12}</p>
                      </div>
                      <div className="p-3 rounded-lg bg-white/5 border border-white/5 text-center">
                        <p className="text-slate-500 text-[10px] uppercase font-bold">Centrality</p>
                        <p className="text-2xl font-bold text-emerald-node">{(Math.random()*0.5 + 0.4).toFixed(2)}</p>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <p className="text-slate-400 text-xs font-medium border-b border-white/5 pb-2 uppercase tracking-tight">Recent Relations</p>
                      {(nodeDetails?.top_connections || []).map((rel: any, i: number) => (
                        <div 
                          key={i} 
                          onClick={() => {
                             const actualLink = processedData.links.find((l: any) => 
                                 (l.source.id === selectedNode.id && l.target.id === rel.name) ||
                                 (l.source.id === rel.name && l.target.id === selectedNode.id)
                             );
                             setSelectedEdge(actualLink || { source: selectedNode.id, target: rel.name, weight: rel.co_mentions });
                             setSelectedNode(null);
                          }}
                          className="flex items-center gap-3 bg-white/5 p-2 rounded-lg border border-transparent hover:border-primary/20 transition-all cursor-pointer"
                        >
                          <div className={cn("size-2 rounded-full", rel.type === 'USER' || rel.type === 'PERSON' ? 'bg-emerald-node' : rel.type === 'COMPANY' ? 'bg-cyan-node' : 'bg-primary')}></div>
                          <div className="flex-1 overflow-hidden">
                            <p className="text-sm text-slate-200 truncate">{rel.name}</p>
                            <p className="text-[10px] text-slate-500 uppercase">Co-Mentions: {rel.co_mentions}</p>
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="p-4 rounded-xl bg-primary/5 border border-primary/10">
                        <h4 className="text-[10px] font-bold text-primary uppercase mb-2">OSINT Analysis</h4>
                        <p className="text-xs text-slate-400 leading-relaxed italic">
                            {nodeDetails?.osint_summary || "Synthesizing latest entity patterns across intelligence networks..."}
                        </p>
                    </div>
                  </>
                )}
              </div>
              <div className="p-4 bg-white/5 border-t border-white/10">
                <button 
                  onClick={() => setSelectedNode(null)}
                  className="w-full bg-primary/20 hover:bg-primary/30 text-primary font-bold py-3 rounded-xl flex items-center justify-center gap-2 transition-all border border-primary/20"
                >
                  <span className="material-symbols-outlined text-lg">close</span>
                  Close Intelligence
                </button>
              </div>
            </>
          )}

          {selectedEdge && (
            <>
               <div className="p-6 border-b border-white/10">
                <h3 className="text-slate-400 text-xs font-bold uppercase tracking-widest mb-1">Relationship Evidence</h3>
                <div className="flex items-center gap-2 mt-2">
                    <span className="text-sm font-bold text-cyan-node truncate max-w-[40%]">{typeof selectedEdge.source === 'object' ? selectedEdge.source.id : selectedEdge.source}</span>
                    <span className="material-symbols-outlined text-slate-500 text-sm">sync_alt</span>
                    <span className="text-sm font-bold text-emerald-node truncate max-w-[40%]">{typeof selectedEdge.target === 'object' ? selectedEdge.target.id : selectedEdge.target}</span>
                </div>
                <p className="text-slate-500 text-xs font-mono mt-2">Weight: {selectedEdge.weight} Co-mentions</p>
              </div>
              <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
                {loadingEdgeDetails ? (
                   <div className="flex flex-col items-center justify-center h-full space-y-2">
                      <div className="size-6 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                      <div className="text-slate-500 animate-pulse text-xs uppercase tracking-widest">Retrieving Source Material...</div>
                   </div>
                ) : (
                   <div className="space-y-4">
                      {edgeDetails?.articles && edgeDetails.articles.length > 0 ? (
                         edgeDetails.articles.map((article: any, i: number) => (
                             <div key={article.id || i} className="p-4 rounded-xl bg-white/5 border border-white/10 hover:border-primary/30 transition-colors">
                                 <div className="flex items-center justify-between mb-2">
                                     <span className="text-[10px] font-bold text-primary uppercase tracking-wider">{article.source_type}</span>
                                     <span className="text-[10px] text-slate-500 font-mono">
                                         {article.created_at ? new Date(article.created_at).toLocaleDateString() : 'Unknown Date'}
                                     </span>
                                 </div>
                                 <p className="text-xs text-slate-300 leading-relaxed line-clamp-4">
                                     {article.content}
                                 </p>
                                 {article.raw_url && (
                                     <a href={article.raw_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 mt-3 text-[10px] text-primary hover:text-white transition-colors uppercase font-bold tracking-wider">
                                         View Source
                                         <span className="material-symbols-outlined text-[12px]">open_in_new</span>
                                     </a>
                                 )}
                             </div>
                         ))
                      ) : (
                          <div className="text-center p-8 text-slate-500 text-xs">
                              No definitive source articles found for this link in the current temporal window.
                          </div>
                      )}
                   </div>
                )}
              </div>
              <div className="p-4 bg-white/5 border-t border-white/10">
                <button 
                  onClick={() => setSelectedEdge(null)}
                  className="w-full bg-slate-800 hover:bg-slate-700 text-white font-bold py-3 rounded-xl flex items-center justify-center gap-2 transition-all border border-white/10"
                >
                  <span className="material-symbols-outlined text-lg">close</span>
                  Close Evidence
                </button>
              </div>
            </>
          )}
        </aside>

        {/* Floating Controls */}
        <div className="absolute left-6 bottom-32 flex flex-col gap-3 z-20">
          <button className="size-12 rounded-xl glass-panel text-white flex items-center justify-center hover:bg-primary/20 transition-all border border-white/10">
            <span className="material-symbols-outlined">add</span>
          </button>
          <button className="size-12 rounded-xl glass-panel text-white flex items-center justify-center hover:bg-primary/20 transition-all border border-white/10">
            <span className="material-symbols-outlined">remove</span>
          </button>
          <button className="size-12 rounded-xl glass-panel text-white flex items-center justify-center hover:bg-primary/20 transition-all border border-white/10">
            <span className="material-symbols-outlined">explore</span>
          </button>
        </div>

        {/* Bottom Filter Panel */}
        <div className="absolute left-6 bottom-6 right-96 h-20 glass-panel rounded-xl border border-white/10 flex items-center px-8 gap-12 z-20">
          <div className="flex items-center gap-4 min-w-[240px]">
            <div className="flex-1 flex flex-col gap-1">
              <div className="flex items-center justify-between">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter flex items-center gap-1.5">
                    Co-mention Density
                    <div className="group relative">
                        <span className="material-symbols-outlined text-[12px] cursor-help text-slate-600">info</span>
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-slate-900 text-[9px] text-slate-300 rounded border border-white/10 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                            Minimum weight threshold for displaying relationships based on cross-source co-occurrence frequency.
                        </div>
                    </div>
                </label>
                <span className="text-[10px] font-mono text-primary">{density}%</span>
              </div>
              <input 
                className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-primary" 
                type="range"
                value={density}
                onChange={(e) => setDensity(parseInt(e.target.value))}
              />
            </div>
          </div>
          <div className="h-8 w-px bg-white/10"></div>
          <div className="flex-1 flex flex-col gap-1">
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">Temporal Range (2025 - 2026)</label>
            <div className="relative w-full h-1 bg-white/10 rounded-lg">
              <div className="absolute left-1/4 right-1/4 h-full bg-primary rounded-lg shadow-[0_0_10px_rgba(236,91,19,0.4)]"></div>
              <div className="absolute left-1/4 -top-1 size-3 bg-white rounded-full border-2 border-primary shadow-lg cursor-pointer"></div>
              <div className="absolute right-1/4 -top-1 size-3 bg-white rounded-full border-2 border-primary shadow-lg cursor-pointer"></div>
            </div>
          </div>
          <div className="h-8 w-px bg-white/10"></div>
          <div className="flex gap-4 shrink-0">
            <div className="flex items-center gap-2">
              <div className="size-2 rounded-full bg-cyan-node shadow-[0_0_10px_rgba(0,210,255,0.5)]"></div>
              <span className="text-[10px] text-slate-400 font-bold uppercase">Companies</span>
            </div>
            <button 
                onClick={() => setShowPeople(!showPeople)}
                className={cn(
                  "flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all cursor-pointer",
                  showPeople ? "bg-white/5 border-white/10 hover:border-emerald-500/50" : "bg-black/40 border-slate-800 opacity-50 hover:opacity-80"
                )}
            >
              <div className="size-2 rounded-full bg-emerald-node shadow-[0_0_10px_rgba(0,255,135,0.5)]"></div>
              <span className="text-[10px] text-slate-400 font-bold uppercase line-through max-w-[50px] overflow-hidden truncate">
                {showPeople ? "Hide People" : "Show People"}
              </span>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
