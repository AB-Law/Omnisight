"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { fetchFromApi } from "@/lib/api";

export default function Trackers() {
  const [trackers, setTrackers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({ name: "", type: "COMPANY", source: "Global News", interval: 60 });
  const [creating, setCreating] = useState(false);
  const [isLogOpen, setIsLogOpen] = useState(false);
  const [selectedTracker, setSelectedTracker] = useState<any>(null);
  const [systemStatus, setSystemStatus] = useState<any>({ cpu_load: "...", memory_usage: "...", latency: "...", status: "Loading" });

  useEffect(() => {
    fetchTrackers();
    fetchSystemStatus();
  }, []);

  const fetchSystemStatus = async () => {
    try {
      const json = await fetchFromApi("/system/status");
      setSystemStatus(json);
    } catch (err) {
      console.error("Failed to fetch system status:", err);
    }
  };

  const fetchTrackers = async () => {
    try {
      const json = await fetchFromApi("/targets");
      setTrackers(json);
    } catch (err) {
      console.error("Failed to fetch trackers:", err);
    } finally {
      setLoading(false);
    }
  };

  const createTracker = async () => {
    if (!formData.name) return;
    setCreating(true);
    try {
      await fetchFromApi("/targets", {
        method: "POST",
        body: JSON.stringify({
          target_name: formData.name,
          source_type: formData.source,
          entity_type: formData.type,
          scrape_interval_minutes: formData.interval,
          campaign: "General Monitoring",
        }),
      });
      setFormData({ name: "", type: "COMPANY", source: "Global News", interval: 60 });
      fetchTrackers();
    } catch (err) {
      console.error("Failed to create tracker:", err);
    } finally {
      setCreating(false);
    }
  };

  const deleteTracker = async (id: string) => {
    try {
      await fetchFromApi(`/targets/${id}`, { method: "DELETE" });
      fetchTrackers();
    } catch (err) {
      console.error("Failed to delete tracker:", err);
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <header className="h-16 border-b border-white/10 flex items-center justify-between px-8 bg-background-dark/80 backdrop-blur-md sticky top-0 z-50 shrink-0">
        <div className="flex items-center gap-8">
           <div className="flex items-center gap-3 text-primary">
              <span className="material-symbols-outlined text-3xl font-bold">radar</span>
              <h2 className="text-white text-xl font-bold tracking-tight">Omnisight <span className="text-primary/80 font-medium text-sm ml-1">v4.0.2</span></h2>
           </div>
           <nav className="hidden md:flex items-center gap-8">
              <Link href="/global-intelligence" className="text-slate-400 hover:text-primary text-sm font-medium transition-colors">Terminal</Link>
              <Link href="/trackers" className="text-primary text-sm font-medium border-b-2 border-primary pb-1">Trackers</Link>
              <Link href="/archive" className="text-slate-400 hover:text-primary text-sm font-medium transition-colors opacity-50 cursor-not-allowed">Archive</Link>
           </nav>
        </div>
        <div className="flex items-center gap-4">
          <button className="p-2 hover:bg-white/5 rounded-lg text-slate-400 flex items-center justify-center">
            <span className="material-symbols-outlined">notifications</span>
          </button>
          <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-primary to-orange-700 flex items-center justify-center font-bold text-xs text-background-dark">JD</div>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto p-6 lg:p-10 max-w-7XL mx-auto w-full custom-scrollbar">
        <div className="flex flex-col lg:flex-row gap-8">
          {/* Main Form Area */}
          <div className="flex-1 flex flex-col gap-6">
            <div className="mb-4">
              <h1 className="text-3xl font-extrabold text-white tracking-tight leading-none mb-1">Tracker Control Center</h1>
              <p className="text-slate-400">Configure and deploy high-fidelity autonomous data scrapers.</p>
            </div>

            <div className="glass-card glow-orange rounded-2xl p-8 relative overflow-hidden">
              <div className="flex items-center justify-between mb-10 px-2">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary text-background-dark flex items-center justify-center font-bold text-sm">1</div>
                  <span className="text-sm font-semibold text-white">Definition</span>
                </div>
                <div className="flex-1 h-px bg-white/10 mx-4"></div>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full border border-white/20 text-slate-400 flex items-center justify-center font-bold text-sm">2</div>
                  <span className="text-sm font-semibold text-slate-400">Sources</span>
                </div>
                <div className="flex-1 h-px bg-white/10 mx-4"></div>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full border border-white/20 text-slate-400 flex items-center justify-center font-bold text-sm">3</div>
                  <span className="text-sm font-semibold text-slate-400">Execution</span>
                </div>
              </div>

              <div className="space-y-8">
                <div className="space-y-6">
                  <div className="space-y-4">
                    <label className="text-sm font-medium text-slate-300 uppercase tracking-wider">Entity Type</label>
                    <div className="flex gap-4">
                      {['COMPANY', 'PERSON', 'TOPIC'].map((type) => (
                        <button
                          key={type}
                          onClick={() => setFormData({ ...formData, type })}
                          className={cn(
                            "flex-1 py-3 px-4 rounded-xl border text-xs font-bold transition-all",
                            formData.type === type 
                              ? "bg-primary/20 border-primary text-primary" 
                              : "bg-white/5 border-white/10 text-slate-400 hover:bg-white/10"
                          )}
                        >
                          {type}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-300 uppercase tracking-wider">Target Name</label>
                    <input 
                        className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-4 text-white placeholder:text-slate-600 focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all outline-none" 
                        placeholder={formData.type === 'PERSON' ? "e.g. @elonmusk" : formData.type === 'TOPIC' ? "e.g. Artificial Intelligence" : "e.g. NVIDIA Corporation"} 
                        type="text"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    />
                  </div>
                  
                  <div className="space-y-4">
                    <label className="text-sm font-medium text-slate-300 uppercase tracking-wider">Source Selection</label>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        <button 
                            className={cn("flex flex-col items-center justify-center gap-3 p-6 rounded-xl border transition-all group", formData.source === 'Global News' ? 'bg-primary/10 border-primary' : 'bg-white/5 border-white/10')}
                            onClick={() => setFormData({...formData, source: 'Global News'})}
                        >
                            <span className={cn("material-symbols-outlined text-3xl transition-transform group-hover:scale-110", formData.source === 'Global News' ? 'text-primary' : 'text-slate-400')}>newspaper</span>
                            <span className={cn("text-[10px] font-bold uppercase tracking-widest", formData.source === 'Global News' ? 'text-primary' : 'text-slate-400')}>Global News</span>
                        </button>
                        <button 
                            className={cn("flex flex-col items-center justify-center gap-3 p-6 rounded-xl border transition-all group", formData.source === 'Reddit Hub' ? 'bg-primary/10 border-primary' : 'bg-white/5 border-white/10')}
                            onClick={() => setFormData({...formData, source: 'Reddit Hub'})}
                        >
                            <span className={cn("material-symbols-outlined text-3xl transition-transform group-hover:scale-110", formData.source === 'Reddit Hub' ? 'text-primary' : 'text-slate-400')}>forum</span>
                            <span className={cn("text-[10px] font-bold uppercase tracking-widest", formData.source === 'Reddit Hub' ? 'text-primary' : 'text-slate-400')}>Reddit Hub</span>
                        </button>
                        <button 
                            className={cn("flex flex-col items-center justify-center gap-3 p-6 rounded-xl border transition-all group", 
                              formData.source === 'X (Twitter)' ? 'bg-primary/10 border-primary' : 'bg-white/5 border-white/10',
                              formData.type === 'PERSON' && 'border-primary/50 border-dashed'
                            )}
                            onClick={() => setFormData({...formData, source: 'X (Twitter)'})}
                        >
                            <span className={cn("material-symbols-outlined text-3xl transition-transform group-hover:scale-110", formData.source === 'X (Twitter)' ? 'text-primary' : 'text-slate-400')}>alternate_email</span>
                            <span className={cn("text-[10px] font-bold uppercase tracking-widest", formData.source === 'X (Twitter)' ? 'text-primary' : 'text-slate-400')}>X (Twitter)</span>
                        </button>
                        <button 
                            disabled
                            className="flex flex-col items-center justify-center gap-3 p-6 rounded-xl border bg-white/5 border-white/5 opacity-50 cursor-not-allowed group relative overflow-hidden"
                        >
                            <div className="absolute top-1 right-1 bg-primary text-[8px] px-1 rounded text-white font-bold tracking-tighter uppercase">Soon</div>
                            <span className="material-symbols-outlined text-3xl text-slate-600">travel_explore</span>
                            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-600 line-through">SpiderFoot</span>
                        </button>
                    </div>
                  </div>

                  <div className="space-y-4 pt-4">
                    <label className="text-sm font-medium text-slate-300 uppercase tracking-wider">Scrape Frequency (Execution)</label>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                        {[
                          { label: '5 Minutes', value: 5 },
                          { label: '30 Minutes', value: 30 },
                          { label: '1 Hour', value: 60 },
                          { label: '6 Hours', value: 360 },
                          { label: 'Daily', value: 1440 },
                          { label: 'Manual Only', value: 0 }
                        ].map((opt) => (
                          <button
                            key={opt.value}
                            onClick={() => setFormData({ ...formData, interval: opt.value })}
                            className={cn(
                              "py-3 px-2 rounded-xl border text-[10px] font-bold transition-all flex items-center justify-center gap-2",
                              formData.interval === opt.value
                                ? "bg-primary/20 border-primary text-primary"
                                : "bg-white/5 border-white/10 text-slate-400 hover:bg-white/10"
                            )}
                          >
                            <span className="material-symbols-outlined text-xs">
                              {opt.value === 0 ? 'touch_app' : 'schedule'}
                            </span>
                            {opt.label}
                          </button>
                        ))}
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-6 border-t border-white/10">
                  <button className="text-slate-400 hover:text-white font-semibold text-sm transition-colors">Clear Form</button>
                  <button 
                    onClick={createTracker}
                    disabled={creating || !formData.name}
                    className="bg-primary hover:bg-primary/90 text-background-dark font-bold px-8 py-3 rounded-xl transition-all flex items-center gap-2 group shadow-lg shadow-primary/20 disabled:opacity-50"
                  >
                    {creating ? 'Deploying...' : 'Deploy Scraper'}
                    <span className="material-symbols-outlined text-lg group-hover:translate-x-1 transition-transform">arrow_forward</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Right Sidebar */}
          <aside className="w-full lg:w-80 flex flex-col gap-4">
             <div className="glass-card rounded-2xl p-6 flex-1 flex flex-col">
                <div className="flex items-center justify-between mb-6">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-slate-100 flex items-center gap-2">
                        <span className="material-symbols-outlined text-primary text-xl">memory</span>
                        Active Scrapers
                    </h3>
                    <span className="bg-primary/10 text-primary text-[10px] px-2 py-0.5 rounded-full border border-primary/20 font-bold">{trackers.length} LIVE</span>
                </div>
                
                <div className="space-y-4 overflow-y-auto max-h-[500px] pr-2 custom-scrollbar">
                    {trackers.map((t) => (
                        <div 
                          key={t.id} 
                          onClick={() => setSelectedTracker(t)}
                          className={cn(
                            "bg-white/5 border rounded-xl p-4 transition-all group cursor-pointer",
                            selectedTracker?.id === t.id ? 'border-primary ring-1 ring-primary/30' : 'border-white/10 hover:border-primary/30'
                          )}
                        >
                            <div className="flex justify-between items-start mb-2">
                                <div className="flex items-center gap-2">
                                    <div className={cn(
                                      "w-2 h-2 rounded-full animate-pulse shadow-[0_0_10px_rgba(236,91,19,0.5)]",
                                      t.status === 'Running' ? 'bg-blue-500' : t.status === 'Error' ? 'bg-red-500' : 'bg-primary'
                                    )}></div>
                                    <span className="text-xs font-bold text-white tracking-tight truncate max-w-[120px]">{t.target_name || t.entity_name}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <button 
                                      onClick={(e) => { e.stopPropagation(); deleteTracker(t.id); }}
                                      className="material-symbols-outlined text-xs text-slate-500 hover:text-red-500 transition-colors"
                                  >
                                      delete
                                  </button>
                                </div>
                            </div>
                            <div className="flex flex-col gap-1 mb-3">
                                <p className="text-[10px] text-slate-500 uppercase tracking-tighter">
                                    {t.event_count || 0} Intelligence Signals
                                </p>
                                {t.recent_sources && t.recent_sources.length > 0 && (
                                    <div className="flex flex-wrap gap-1 mt-1">
                                        {t.recent_sources.map((domain: string, idx: number) => (
                                            <span key={idx} className="text-[8px] bg-white/5 px-1.5 py-0.5 rounded text-slate-400 border border-white/5 truncate max-w-[100px]">
                                                {domain}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                            <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
                                <div className="h-full bg-primary/40 w-[65%]"></div>
                            </div>
                        </div>
                    ))}
                    {trackers.length === 0 && (
                        <div className="text-center p-8 text-slate-500 italic text-xs">No active scrapers detected.</div>
                    )}
                </div>

                <div className="mt-auto pt-6 border-t border-white/5">
                    <div className="p-4 rounded-xl bg-primary/5 border border-primary/10">
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-3">
                                <span className="material-symbols-outlined text-primary text-sm">analytics</span>
                                <span className="text-[10px] font-bold text-slate-200 uppercase">System Status</span>
                            </div>
                            <button 
                                onClick={fetchSystemStatus}
                                className="material-symbols-outlined text-xs text-slate-500 hover:text-primary transition-colors"
                            >
                                refresh
                            </button>
                        </div>
                        <div className="space-y-2">
                             <div className="flex justify-between text-[10px] font-mono">
                                <span className="text-slate-500 uppercase">CPU Load</span>
                                <span className="text-primary">{systemStatus.cpu_load}</span>
                             </div>
                             <div className="flex justify-between text-[10px] font-mono">
                                <span className="text-slate-500 uppercase">RAM Usage</span>
                                <span className="text-primary">{systemStatus.memory_usage}</span>
                             </div>
                             <div className="flex justify-between text-[10px] font-mono">
                                <span className="text-slate-500 uppercase">System</span>
                                <span className={cn(systemStatus.status === 'Healthy' ? 'text-green-500' : 'text-red-500')}>
                                  {systemStatus.status}
                                </span>
                             </div>
                        </div>
                    </div>
                </div>
             </div>
             <button 
                onClick={() => setIsLogOpen(true)}
                disabled={!selectedTracker}
                className="w-full py-3 rounded-xl border border-white/10 text-white text-xs font-bold uppercase tracking-widest hover:bg-white/5 transition-all flex items-center justify-center gap-2 glass-card disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span className="material-symbols-outlined text-sm">terminal</span>
                Open Logs
             </button>
          </aside>
        </div>
      </main>

      {/* Logs Modal */}
      {isLogOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="glass-card w-full max-w-2xl rounded-2xl overflow-hidden border border-white/20 shadow-2xl flex flex-col max-h-[80vh]">
            <div className="p-4 border-b border-white/10 flex items-center justify-between bg-white/5">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-primary">terminal</span>
                <span className="text-xs font-bold text-white uppercase tracking-[0.2em]">Tracker Execution Logs</span>
              </div>
              <button onClick={() => setIsLogOpen(false)} className="material-symbols-outlined text-slate-400 hover:text-white transition-colors">close</button>
            </div>
            
            <div className="flex-1 p-6 font-mono text-xs overflow-y-auto bg-black/80 custom-scrollbar">
              {selectedTracker ? (
                <div className="space-y-2">
                  <div className="flex gap-4">
                    <span className="text-slate-500 text-[10px] uppercase">[{new Date().toISOString()}]</span>
                    <span className="text-primary font-bold">INFO:</span>
                    <span className="text-slate-300">Target initialized: {selectedTracker.target_name}</span>
                  </div>
                  <div className="flex gap-4">
                    <span className="text-slate-500 text-[10px] uppercase">[{selectedTracker.created_at || new Date().toISOString()}]</span>
                    <span className="text-green-500 font-bold">SUCCESS:</span>
                    <span className="text-slate-300">Persistence layer linked. UUID: {selectedTracker.id}</span>
                  </div>
                  <div className="flex gap-4">
                    <span className="text-slate-500 text-[10px] uppercase">[{selectedTracker.last_scraped || 'N/A'}]</span>
                    <span className="text-blue-500 font-bold">STATUS:</span>
                    <span className="text-slate-300">Current node state: <span className="text-white underline decoration-primary/50">{selectedTracker.status}</span></span>
                  </div>
                  {selectedTracker.error && (
                    <div className="flex gap-4 p-2 bg-red-500/10 border border-red-500/20 rounded-lg mt-4">
                      <span className="material-symbols-outlined text-red-500 text-sm">error</span>
                      <span className="text-red-400 italic">Critical failure detected: {selectedTracker.error}</span>
                    </div>
                  )}
                  <div className="pt-4 text-emerald-500 animate-pulse">Running kernel process... listening for new signals.</div>
                </div>
              ) : (
                <div className="text-slate-500 italic text-center py-20">No tracker selected for log extraction.</div>
              )}
            </div>

            <div className="p-4 bg-white/5 border-t border-white/10 flex justify-end gap-3">
               <button 
                onClick={() => setIsLogOpen(false)}
                className="px-6 py-2 rounded-lg bg-white/10 text-white text-xs font-bold hover:bg-white/20 transition-all"
               >
                Close
               </button>
               <button 
                onClick={() => fetchTrackers()}
                className="px-6 py-2 rounded-lg bg-primary text-background-dark text-xs font-bold hover:bg-primary/90 transition-all"
               >
                Refresh Data
               </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
