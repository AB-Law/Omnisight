"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  AreaChart, Area 
} from 'recharts';
import { cn } from "@/lib/utils";

export default function EntityIntelligenceHub() {
  const router = useRouter();
  const [entities, setEntities] = useState<string[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<string>("");
  const [heatmapData, setHeatmapData] = useState<any[]>([]);
  const [correlationData, setCorrelationData] = useState<any | null>(null);
  const [feedData, setFeedData] = useState<any[]>([]);
  const [networkData, setNetworkData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  
  // Hub Settings Modal State
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [entityTrackers, setEntityTrackers] = useState<any[]>([]);
  const [settingsSaving, setSettingsSaving] = useState(false);

  const [deepDiveStatus, setDeepDiveStatus] = useState<"idle" | "scanning" | "complete">("idle");

  useEffect(() => {
    async function loadInitData() {
      try {
         const [entRes, heatRes] = await Promise.all([
             fetch("http://127.0.0.1:8000/dashboard/filters/entities?entity_type=COMPANY"),
             fetch("http://127.0.0.1:8000/market/sector-heatmap")
         ]);
         const entJson = await entRes.json();
         const heatJson = await heatRes.json();
         
         const validEntities = entJson.filter((e: string) => e !== "All");
         setEntities(validEntities);
         
         if (heatJson.sectors) setHeatmapData(heatJson.sectors);
         
         if (validEntities.length > 0) {
             setSelectedEntity(validEntities[0]);
         } else {
             // If no entities are tracked, push to trackers page
             router.push("/trackers");
         }

      } catch (err) {
          console.error("Init fetch error", err);
      } finally {
          setLoading(false);
      }
    }
    loadInitData();
  }, [router]);

  const runAnalysis = async (entityName: string) => {
    if (!entityName) return;
    setAnalyzing(true);
    try {
        const [corrRes, feedRes, netRes] = await Promise.all([
             fetch(`http://127.0.0.1:8000/market/correlation/${entityName}?days=90`),
             fetch(`http://127.0.0.1:8000/dashboard/data?filter_entity=${entityName}&filter_type=COMPANY`),
             fetch(`http://127.0.0.1:8000/knowledge-graph/entity/${entityName}/details`)
        ]);
        
        if (corrRes.ok) setCorrelationData(await corrRes.json());
        if (feedRes.ok) {
            const feedJson = await feedRes.json();
            setFeedData(feedJson.data || feedJson);
        }
        if (netRes.ok) {
            const netJson = await netRes.json();
            setNetworkData(netJson.top_connections || []);
        }
    } catch (err) {
        console.error("Analysis error", err);
    } finally {
        setAnalyzing(false);
    }
  };

  useEffect(() => {
      if (selectedEntity) runAnalysis(selectedEntity);
  }, [selectedEntity]);

  const loadEntityTrackers = async () => {
    try {
        const res = await fetch("http://127.0.0.1:8000/targets");
        if (res.ok) {
           const data = await res.json();
           const filtered = data.filter((t: any) => t.target_name.toLowerCase() === selectedEntity.toLowerCase());
           setEntityTrackers(filtered);
        }
    } catch(e) { console.error(e) }
  };

  const updateTrackerInterval = async (id: string, newInterval: number) => {
      setSettingsSaving(true);
      try {
          await fetch(`http://127.0.0.1:8000/targets/${id}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                  target_name: selectedEntity, // Required by TargetIn, though we don't change it here
                  source_type: "Any", // Required by schema
                  scrape_interval_minutes: newInterval
              })
          });
          await loadEntityTrackers();
      } catch (e) {
          console.error(e);
      } finally {
          setSettingsSaving(false);
      }
  };

  const triggerDeepDive = async () => {
      if (!selectedEntity || deepDiveStatus === "scanning") return;
      setDeepDiveStatus("scanning");
      try {
          const res = await fetch(`http://127.0.0.1:8000/targets/by-entity/${selectedEntity}`);
          if (res.ok) {
              const data = await res.json();
              if (data.target && data.target.id) {
                  const runRes = await fetch(`http://127.0.0.1:8000/targets/${data.target.id}/run`, { method: "POST" });
                  if (runRes.ok) {
                      setTimeout(() => {
                          setDeepDiveStatus("complete");
                          runAnalysis(selectedEntity);
                          setTimeout(() => setDeepDiveStatus("idle"), 3000);
                      }, 1500);
                  } else {
                      setDeepDiveStatus("idle");
                  }
              } else {
                  console.warn("No target found for deep dive.");
                  setDeepDiveStatus("idle");
              }
          }
      } catch (err) {
          console.error(err);
          setDeepDiveStatus("idle");
      }
  };

  const handleExport = () => {
      if (!selectedEntity) return;
      window.open(`http://127.0.0.1:8000/market/export/${encodeURIComponent(selectedEntity)}`, '_blank');
  };

  if (loading || (!selectedEntity && entities.length === 0)) return <div className="text-slate-400 font-mono text-[10px] uppercase tracking-widest flex h-screen items-center justify-center animate-pulse">Initializing Neural Hub...</div>;

  return (
    <div className="flex flex-col h-full overflow-hidden bg-background-dark">
      {/* Top Header / Selector */}
      <header className="h-14 border-b border-white/5 flex items-center justify-between px-8 bg-black/10 backdrop-blur-xl z-50 shrink-0">
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-3">
             <div className="p-1.5 bg-primary/20 rounded-lg">
                <span className="material-symbols-outlined text-primary text-xl">hub</span>
             </div>
             <h2 className="text-white text-base font-bold tracking-tight">Entity Intelligence Hub</h2>
          </div>
          <nav className="hidden md:flex items-center gap-6">
            <span className="text-slate-500 text-xs font-medium cursor-pointer hover:text-white transition-colors">Dashboard</span>
            <span className="text-primary text-xs font-bold border-b-2 border-primary pb-1">Entities</span>
            <span className="text-slate-500 text-xs font-medium cursor-pointer hover:text-white transition-colors">Reports</span>
          </nav>
        </div>
        <div className="flex items-center gap-4">
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Active Focus</label>
            <select 
                className="bg-white/5 border border-white/10 rounded-xl px-3 py-1 text-xs focus:ring-1 focus:ring-primary outline-none min-w-[180px] text-white"
                value={selectedEntity}
                onChange={(e) => setSelectedEntity(e.target.value)}
            >
                {entities.map((e: string) => <option key={e} value={e} className="bg-slate-900">{e}</option>)}
            </select>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto p-6 md:p-8 space-y-8 custom-scrollbar">
        {/* Hero Section */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-white/5">
          <div className="flex items-center gap-6">
            <div className="size-20 rounded-2xl bg-white/5 flex items-center justify-center border border-primary/20 shadow-2xl shadow-primary/5 relative overflow-hidden">
                <span className="material-symbols-outlined text-3xl text-primary/80 absolute z-0">domain</span>
                {selectedEntity && (
                    <img 
                        src={`http://127.0.0.1:8000/entity/logo/${encodeURIComponent(selectedEntity)}`} 
                        alt={selectedEntity}
                        className="w-full h-full object-contain p-2 absolute inset-0 z-10 bg-white/10 backdrop-blur-sm"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none';
                        }}
                    />
                )}
            </div>
            <div>
              <div className="flex items-center gap-4 mb-1">
                <h1 className="text-3xl font-bold tracking-tighter text-white">{selectedEntity}</h1>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-widest uppercase bg-emerald-500/10 text-emerald-500 border border-emerald-500/30 animate-pulse">Tracked</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-slate-500 font-mono text-[10px] uppercase">NASDAQ: {correlationData?.ticker_symbol || "----"}</span>
                <span className="size-1 bg-slate-700 rounded-full"></span>
                <span className="text-slate-500 text-[10px] font-bold uppercase tracking-wide">{correlationData?.industry || "INDUSTRIAL CLUSTER"}</span>
              </div>
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={handleExport} className="px-5 py-2 bg-primary text-white text-xs font-bold rounded-xl shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-[0.98] transition-all">Export Analysis</button>
            <button onClick={() => { loadEntityTrackers(); setIsSettingsOpen(true); }} className="px-4 py-2 bg-white/5 border border-white/10 text-slate-300 text-xs font-semibold rounded-xl hover:bg-white/10 transition-all">Hub Settings</button>
          </div>
        </div>

        {/* Main Analytics Row */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-3 glass-card rounded-2xl p-6 border border-white/5">
            <div className="flex items-center justify-between mb-8">
              <div>
                <h3 className="text-base font-bold text-white tracking-tight">OSINT Sentiment vs Market Velocity</h3>
                <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-2">
                    Alpha Correlation: <span className="text-primary font-bold">{correlationData?.pearson_r?.toFixed(2) || "0.00"}</span>
                    <span className="size-1 rounded-full bg-slate-700"></span>
                    <span className="text-[10px] uppercase font-bold text-slate-600">{correlationData?.pearson_r > 0.5 ? "Synchronous" : "Asynchronous"}</span>
                </p>
              </div>
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-2">
                  <span className="size-2 rounded-full bg-blue-sentiment shadow-[0_0_8px_rgba(59,130,246,0.6)]"></span>
                  <span className="text-[10px] font-bold text-slate-500 uppercase">Sentiment</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="size-2 rounded-full bg-primary shadow-[0_0_8px_rgba(236,91,19,0.8)]"></span>
                  <span className="text-[10px] font-bold text-slate-500 uppercase">Velocity</span>
                </div>
              </div>
            </div>
            
            <div className="h-80 w-full relative">
               {analyzing && (
                   <div className="absolute inset-0 flex items-center justify-center bg-background-dark/20 backdrop-blur-sm z-30 rounded-xl">
                       <span className="text-primary font-mono text-[10px] animate-pulse uppercase tracking-[0.3em]">Neural Recalibration...</span>
                   </div>
               )}
               <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={correlationData?.aligned_data || []}>
                        <defs>
                            <linearGradient id="colorSentiment" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15}/>
                                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                            </linearGradient>
                            <filter id="lineGlow">
                                <feGaussianBlur stdDeviation="3" result="blur" />
                                <feComposite in="SourceGraphic" in2="blur" operator="over" />
                            </filter>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
                        <XAxis dataKey="date" hide />
                        <YAxis yAxisId="left" hide domain={['auto', 'auto']} />
                        <YAxis yAxisId="right" hide domain={[-1, 1]} />
                        <Tooltip 
                            contentStyle={{ backgroundColor: '#1a120e', borderColor: '#ec5b1333', borderRadius: '1rem', border: '1px solid rgba(236,91,19,0.1)' }}
                            itemStyle={{ fontSize: '10px', fontWeight: 'bold' }}
                            labelStyle={{ color: '#94a3b8', fontSize: '10px' }}
                        />
                        <Area yAxisId="right" type="monotone" dataKey="sentiment" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorSentiment)" />
                        <Line yAxisId="left" type="monotone" dataKey="close_price" stroke="#ec5b13" strokeWidth={4} dot={false} strokeLinecap="round" filter="url(#lineGlow)" />
                    </AreaChart>
               </ResponsiveContainer>
            </div>
          </div>

          {/* Right Panel: Gauge */}
          <div className="glass-card rounded-2xl p-6 border border-white/5 flex flex-col items-center justify-center text-center relative overflow-hidden">
             <div className="absolute top-4 left-6">
                <h3 className="text-[10px] font-black text-slate-600 uppercase tracking-[0.2em]">Signal Gauge</h3>
             </div>
             
             <div className="relative size-44 mt-4">
                <svg className="size-full -rotate-90" viewBox="0 0 100 100">
                    <circle className="text-white/5" cx="50" cy="50" fill="none" r="40" stroke="currentColor" strokeDasharray="125.6 251.2" strokeLinecap="round" strokeWidth="8"></circle>
                    <circle className="text-primary transition-all duration-1000" cx="50" cy="50" fill="none" r="40" stroke="currentColor" strokeDasharray={`${((correlationData?.signal_strength || 0) / 100) * 125.6} 251.2`} strokeLinecap="round" strokeWidth="10" filter="url(#glow)"></circle>
                    <defs>
                        <filter id="glow">
                            <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                            <feMerge>
                                <feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/>
                            </feMerge>
                        </filter>
                    </defs>
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center pt-8">
                    <span className="text-5xl font-black text-white tracking-tighter">{correlationData?.signal_strength || 0}</span>
                    <span className="text-[10px] font-bold text-primary uppercase tracking-[0.3em] mt-1">{correlationData?.pearson_r > 0 ? 'Bullish' : 'Bearish'}</span>
                </div>
             </div>

             <div className="mt-8 space-y-4 w-full px-2">
                <div className="text-[10px] text-slate-500 leading-relaxed font-medium line-clamp-2 text-center">
                    {correlationData?.insight || "Calibrating signal vectors for the selected entity..."}
                </div>
                <div className="grid grid-cols-2 gap-3 pt-2">
                    <div className="bg-white/5 p-3 rounded-xl border border-white/5 flex flex-col items-center">
                        <span className="text-[8px] font-bold text-slate-600 uppercase">Best Lag</span>
                        <span className="text-xs font-bold text-white">{correlationData?.best_lag_days || 0}D</span>
                    </div>
                    <div className="bg-white/5 p-3 rounded-xl border border-white/5 flex flex-col items-center">
                        <span className="text-[8px] font-bold text-slate-600 uppercase">P-Value</span>
                        <span className="text-xs font-bold text-primary">0.05*</span>
                    </div>
                </div>
             </div>
          </div>
        </div>

        {/* Bottom Detail Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Intelligence Feed */}
          <div className="lg:col-span-2 glass-card rounded-2xl overflow-hidden border border-white/5 flex flex-col shadow-2xl shadow-black/40">
            <div className="p-5 border-b border-white/5 flex items-center justify-between bg-white/[0.02]">
              <h3 className="text-sm font-bold flex items-center gap-3 text-white">
                <span className="material-symbols-outlined text-primary">radar</span>
                Intelligence Streams
              </h3>
              <button className="text-[10px] text-primary font-black uppercase tracking-widest hover:brightness-125 transition-all">Archive Access</button>
            </div>
            <div className="flex-1 overflow-y-auto max-h-[460px] p-5 space-y-4 custom-scrollbar">
              {feedData.length > 0 ? feedData.map((item: any, idx: number) => (
                <div key={idx} className="flex gap-5 p-5 rounded-2xl bg-white/[0.02] hover:bg-white/[0.05] transition-all border border-white/5 group relative overflow-hidden">
                  <div className="shrink-0">
                    <div className={cn(
                        "p-3 rounded-xl text-xl transition-transform group-hover:scale-110",
                        item.sentiment_score > 0.1 ? "text-emerald-500 bg-emerald-500/10" :
                        item.sentiment_score < -0.1 ? "text-rose-500 bg-rose-500/10" :
                        "text-blue-500 bg-blue-500/10"
                    )}>
                      <span className="material-symbols-outlined">
                        {item.source_type?.toLowerCase().includes('reddit') ? 'forum' : 
                         item.source_type?.toLowerCase().includes('news') ? 'newspaper' : 'public'}
                      </span>
                    </div>
                    <div className="mt-2 text-center">
                         <span className="text-[8px] font-bold text-slate-600 uppercase tracking-tighter">{item.source_type}</span>
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-2">
                       <span className="px-2 py-0.5 rounded text-[8px] font-black tracking-widest bg-white/5 border border-white/10 text-slate-400 uppercase">{item.category}</span>
                       <span className={cn(
                           "text-[9px] font-bold",
                           item.sentiment_score > 0.1 ? "text-emerald-500" :
                           item.sentiment_score < -0.1 ? "text-rose-500" :
                           "text-slate-500"
                       )}>
                           {item.sentiment_score > 0.1 ? "NEURAL POSITIVE" : item.sentiment_score < -0.1 ? "NEURAL NEGATIVE" : "NEURAL NEUTRAL"}
                       </span>
                    </div>
                    <p className="text-sm font-medium leading-relaxed text-slate-200">{item.summary}</p>
                    <div className="mt-4 flex items-center gap-4">
                        <span className="text-[10px] text-slate-600 font-mono tracking-tighter capitalize">{new Date(item.published_at || item.created_at).toLocaleDateString()}</span>
                        <div className="h-0.5 w-6 bg-white/5"></div>
                        <a href={item.raw_url || "#"} target="_blank" rel="noopener noreferrer" className="text-[10px] text-primary/60 font-bold uppercase tracking-widest hover:text-primary transition-colors">View Source</a>
                    </div>
                  </div>
                </div>
              )) : (
                  <div className="text-center p-12 text-slate-600 italic font-mono text-xs">Awaiting signal ingestion for chosen node...</div>
              )}
            </div>
          </div>

          {/* Connections Card */}
          <div className="glass-card rounded-2xl p-6 border border-white/5 flex flex-col shadow-2xl">
            <h3 className="text-sm font-bold mb-8 flex items-center gap-3 text-white">
              <span className="material-symbols-outlined text-primary">account_tree</span>
              Network Latency
            </h3>
            <div className="space-y-6 flex-1">
              {networkData.length > 0 ? networkData.slice(0, 5).map((conn: any, i: number) => {
                const affinity = Math.min(conn.co_mentions > 0 ? conn.co_mentions * 2 : 10, 100);
                const colors = ["bg-primary", "bg-primary/80", "bg-primary/70", "bg-primary/50", "bg-primary/30"];
                return (
                <div key={i} className="space-y-2 p-1">
                  <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-widest text-slate-500">
                    <span className="text-slate-200 uppercase">{conn.name}</span>
                    <span className="text-primary/80">{affinity}% AFFINITY</span>
                  </div>
                  <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden border border-white/[0.02]">
                    <div 
                        className={cn("h-full rounded-full transition-all duration-1000", colors[i] || "bg-primary/20")} 
                        style={{ width: `${affinity}%` }}
                    ></div>
                  </div>
                </div>
              )}) : (
                <div className="flex items-center justify-center h-full text-slate-600 italic text-[10px] uppercase tracking-widest">
                    Mapping Neural Clusters...
                </div>
              )}
            </div>
            
            <div className="mt-auto pt-8">
               <div 
                 onClick={triggerDeepDive}
                 className="p-4 rounded-2xl bg-primary/5 border border-primary/10 relative overflow-hidden group hover:bg-primary/10 transition-all cursor-pointer">
                 <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition-all">
                    <span className={cn(
                        "material-symbols-outlined text-4xl transform transition-transform",
                        deepDiveStatus === "scanning" ? "animate-spin text-primary opacity-50" : "-rotate-12"
                    )}>
                        {deepDiveStatus === "scanning" ? "radar" : deepDiveStatus === "complete" ? "check_circle" : "lightbulb"}
                    </span>
                 </div>
                 <h4 className="text-[9px] font-black text-primary uppercase mb-2 tracking-[0.2em]">
                    {deepDiveStatus === "scanning" ? "Initiating Deep-Dive..." : deepDiveStatus === "complete" ? "Scan Complete" : "Live Intelligence Update"}
                 </h4>
                 <p className="text-xs text-slate-400 leading-relaxed italic pr-8">
                    {selectedEntity ? (
                        deepDiveStatus === "scanning" 
                        ? `Real-time correlation monitoring active for ${selectedEntity}. Deep-dive scan in progress.`
                        : deepDiveStatus === "complete"
                        ? `Intelligence feeds updated for ${selectedEntity}. Displaying latest correlations.`
                        : `Click to trigger an emergent deep-dive scan for ${selectedEntity}.`
                    ) : "Select an entity to initialize recommendation engine."}
                 </p>
               </div>
            </div>
          </div>
        </div>
      </main>
      
      {/* Dynamic Background Elements */}
      <div className="fixed inset-0 -z-10 bg-[#0c0806] pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] size-[60%] bg-primary/10 rounded-full blur-[160px] animate-pulse"></div>
        <div className="absolute bottom-[-10%] right-[-10%] size-[40%] bg-blue-500/5 rounded-full blur-[140px]"></div>
      </div>

      {/* Hub Settings Modal */}
      {isSettingsOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
           <div className="glass-card w-full max-w-lg rounded-2xl overflow-hidden border border-white/20 shadow-2xl flex flex-col">
              <div className="p-5 border-b border-white/10 flex items-center justify-between bg-white/5">
                <div className="flex items-center gap-3">
                   <span className="material-symbols-outlined text-primary">settings</span>
                   <h3 className="text-sm font-bold text-white tracking-tight">Hub Settings - {selectedEntity}</h3>
                </div>
                <button onClick={() => setIsSettingsOpen(false)} className="material-symbols-outlined text-slate-400 hover:text-white transition-colors">close</button>
              </div>

              <div className="p-6 space-y-6">
                 <div>
                    <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-4">Active Scanning Jobs</h4>
                    {entityTrackers.length > 0 ? (
                        <div className="space-y-4">
                            {entityTrackers.map(t => (
                                <div key={t.id} className="p-4 rounded-xl border border-white/10 bg-white/5 flex flex-col gap-3">
                                   <div className="flex justify-between items-center">
                                       <span className="text-xs font-bold text-white">{t.source_type} Scraper</span>
                                       <span className={cn("text-[10px] font-bold px-2 py-0.5 rounded uppercase", t.status === 'Running' ? 'bg-blue-500/20 text-blue-400' : 'bg-white/10 text-slate-400')}>{t.status}</span>
                                   </div>
                                   <div className="flex items-center gap-4 mt-2">
                                       <label className="text-[10px] text-slate-400 uppercase font-bold">Scrape Frequency</label>
                                       <select 
                                          disabled={settingsSaving}
                                          value={t.interval}
                                          onChange={(e) => updateTrackerInterval(t.id, parseInt(e.target.value))}
                                          className="bg-black/40 border border-white/10 rounded py-1 px-2 text-xs text-white focus:ring-1 focus:ring-primary outline-none"
                                       >
                                           <option value="5">Every 5 Minutes</option>
                                           <option value="30">Every 30 Minutes</option>
                                           <option value="60">Hourly</option>
                                           <option value="360">Every 6 Hours</option>
                                           <option value="1440">Daily</option>
                                           <option value="0">Manual Only</option>
                                       </select>
                                   </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-sm text-slate-500 italic">No active trackers found for this entity. Create one in the Trackers dashboard.</p>
                    )}
                 </div>
              </div>

              <div className="p-4 bg-white/5 border-t border-white/10 flex justify-end">
                 <button onClick={() => setIsSettingsOpen(false)} className="px-6 py-2 rounded-xl bg-white/10 text-white text-xs font-bold hover:bg-white/20 transition-all">Done</button>
              </div>
           </div>
        </div>
      )}
    </div>
  );
}
