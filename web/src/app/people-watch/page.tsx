"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { fetchFromApi } from "@/lib/api";

export default function PeopleWatch() {
  const [entities, setEntities] = useState<string[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<string>("");
  const [feedData, setFeedData] = useState<any[]>([]);
  const [associatedCompanies, setAssociatedCompanies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Management Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [personInfo, setPersonInfo] = useState<any>(null);
  const [targetInfo, setTargetInfo] = useState<any>(null);
  const [mgmtLoading, setMgmtLoading] = useState(false);
  const [newInterval, setNewInterval] = useState(1440);
  const [allowDiscovery, setAllowDiscovery] = useState(false);

  useEffect(() => {
    async function loadEntities() {
      try {
         const json = await fetchFromApi("/dashboard/filters/entities?entity_type=PERSON");
         const filtered = json.filter((e: string) => e !== "All");
         setEntities(filtered);
         if (filtered.length > 0 && !selectedEntity) setSelectedEntity(filtered[0]);
      } catch (err) {
          console.error("Init fetch error", err);
      } finally {
          setLoading(false);
      }
    }
    loadEntities();
  }, []);

  const openManagement = async () => {
    setMgmtLoading(true);
    setIsModalOpen(true);
    try {
        const [entJson, tgtJson] = await Promise.allSettled([
            fetchFromApi(`/entities/by-name/${selectedEntity}`),
            fetchFromApi(`/targets/by-entity/${selectedEntity}`),
        ]);
        if (entJson.status === "fulfilled") setPersonInfo(entJson.value);
        if (tgtJson.status === "fulfilled") {
            const tgt = tgtJson.value;
            setTargetInfo(tgt.target);
            if (tgt.target) {
                setNewInterval(tgt.target.interval);
                setAllowDiscovery(tgt.target.allow_discovery || false);
            }
        }
    } catch (e) {
        console.error("Mgmt fetch error", e);
    } finally {
        setMgmtLoading(false);
    }
  };

  const handleUpdateSchedule = async () => {
    if (!targetInfo) return;
    try {
        await fetchFromApi(`/targets/${targetInfo.id}`, {
            method: "PUT",
            body: JSON.stringify({ 
                scrape_interval_minutes: newInterval,
                scraper_params: { allow_discovery: allowDiscovery }, 
            }),
        });
        alert("Schedule updated successfully");
        setIsModalOpen(false);
    } catch (e) { alert("Failed to update schedule"); }
  };

  const handleStopJob = async () => {
    if (!targetInfo || !confirm("Stop this tracking job? All related intelligence data will be kept but no more scrapes will occur.")) return;
    try {
        await fetchFromApi(`/targets/${targetInfo.id}`, { method: "DELETE" });
        alert("Tracking job stopped.");
        setIsModalOpen(false);
        window.location.reload();
    } catch (e) { alert("Failed to stop job"); }
  };

  const handleDeletePerson = async () => {
    if (!personInfo || !confirm("Permanently delete this person and ALL their data/history? This cannot be undone.")) return;
    try {
        await fetchFromApi(`/entities/${personInfo.id}`, { method: "DELETE" });
        alert("Person deleted.");
        setIsModalOpen(false);
        window.location.reload();
    } catch (e) { alert("Failed to delete person"); }
  };

  const loadFeed = async () => {
      if (!selectedEntity) return;
      try {
        setAssociatedCompanies([]);
        const [feedResult, detailsResult] = await Promise.allSettled([
          fetchFromApi(`/dashboard/data?filter_entity=${selectedEntity}&filter_type=PERSON`),
          fetchFromApi(`/knowledge-graph/entity/${selectedEntity}/details`),
        ]);

        if (feedResult.status === "fulfilled") {
           const feed = feedResult.value;
           setFeedData(feed.data || feed);
        }
        if (detailsResult.status === "fulfilled") {
          const details = detailsResult.value;
          // Filter related for COMPANIES only, sort by co-mentions
          const companies = (details.related || []).filter((r: any) => r.type === "COMPANY").sort((a: any, b: any) => b.co_mentions - a.co_mentions);
          setAssociatedCompanies(companies);
        }
      } catch (e) {
          console.error("Failed to load people feed", e);
      }
  };

  useEffect(() => {
      if (selectedEntity) loadFeed();
  }, [selectedEntity]);

  if (loading) return <div className="text-slate-400 animate-pulse text-center flex h-screen items-center justify-center">Loading Watchlist Terminal...</div>;

  return (
    <div className="flex flex-col h-full overflow-hidden relative">
      {/* Header */}
      <header className="h-16 border-b border-primary/10 flex items-center justify-between px-8 bg-background-light/50 dark:bg-background-dark/50 backdrop-blur-md z-10 w-full shrink-0">
        <div className="flex items-center gap-6">
          <h2 className="text-lg font-bold text-white">People <span className="text-primary">Watch</span></h2>
          <div className="flex items-center gap-2 px-3 py-1 bg-primary/10 text-primary rounded-full border border-primary/20">
            <span className="material-symbols-outlined text-xs">person_search</span>
            <span className="text-[10px] font-bold uppercase tracking-tighter">Individual monitoring</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
             <label className="text-xs font-medium text-slate-500 uppercase tracking-widest">Tracking</label>
             <select 
                className="bg-white/5 border border-white/10 rounded-xl px-4 py-1.5 text-sm focus:ring-1 focus:ring-primary outline-none w-64 text-white"
                value={selectedEntity}
                onChange={(e) => setSelectedEntity(e.target.value)}
            >
                {entities.map(e => <option key={e} value={e} className="bg-slate-900">{e}</option>)}
            </select>
            <button 
                onClick={openManagement}
                className="w-10 h-10 flex items-center justify-center rounded-xl bg-primary/10 border border-primary/20 text-primary hover:bg-primary/20 transition-all"
            >
                <span className="material-symbols-outlined">settings</span>
            </button>
        </div>
      </header>

      {/* Associated Companies Bar */}
      {associatedCompanies.length > 0 && (
        <div className="bg-background-light/30 dark:bg-background-dark/30 border-b border-primary/5 px-8 py-3 flex items-center gap-4 overflow-x-auto no-scrollbar shrink-0">
          <div className="flex items-center gap-2 text-slate-500 shrink-0">
            <span className="material-symbols-outlined text-sm">business_center</span>
            <span className="text-[10px] font-bold uppercase tracking-widest">Highlighted Companies <span className="opacity-50 ml-1">({associatedCompanies.length})</span></span>
          </div>
          <div className="flex gap-3">
            {associatedCompanies.map((company, idx) => (
              <div key={idx} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 hover:border-primary/30 transition-colors shrink-0">
                 <div className="flex flex-col">
                   <span className="text-xs font-bold text-white tracking-tighter">{company.name}</span>
                   <div className="flex items-center gap-2 mt-0.5">
                     <span className="text-[9px] font-mono text-slate-500">{company.co_mentions} Mentions</span>
                     <span className={cn(
                        "w-1.5 h-1.5 rounded-full",
                        company.avg_sentiment > 0.1 ? "bg-emerald-500" :
                        company.avg_sentiment < -0.1 ? "bg-red-500" : "bg-slate-500"
                     )}/>
                   </div>
                 </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-8 space-y-6 custom-scrollbar">
        {feedData.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {feedData.map((item, idx) => (
              <div key={idx} className="glass-card rounded-xl p-6 border-t-2 border-t-primary relative group hover:border-t-primary transition-all">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{item.source_type}</span>
                  <span className={cn(
                    "px-2 py-0.5 rounded text-[10px] font-bold",
                    item.sentiment_score > 0.1 ? "bg-emerald-500 text-white shadow-lg shadow-emerald-500/20" :
                    item.sentiment_score < -0.1 ? "bg-red-500 text-white shadow-lg shadow-red-500/20" :
                    "bg-slate-800 text-slate-400"
                  )}>
                    {item.sentiment_score > 0 ? "+" : ""}{item.sentiment_score.toFixed(2)}
                  </span>
                </div>
                
                <h4 className="text-xs font-bold text-primary mb-2 uppercase tracking-tight">{item.category}</h4>
                <p className="text-sm text-slate-200 leading-relaxed mb-6 line-clamp-4">
                  {item.summary}
                </p>

                <div className="mt-auto pt-4 border-t border-white/5 flex items-center justify-between">
                  <span className="text-[10px] font-mono text-slate-500">{new Date(item.published_at || item.created_at).toLocaleDateString()}</span>
                  <a href={item.raw_url} target="_blank" className="flex items-center gap-1 text-[10px] font-bold text-primary uppercase hover:underline">
                    View Context <span className="material-symbols-outlined text-xs">open_in_new</span>
                  </a>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-64 text-slate-600">
             <span className="material-symbols-outlined text-4xl mb-4 opacity-20">person_off</span>
             <p className="italic text-sm">No activity recorded for {selectedEntity} in the current temporal window.</p>
          </div>
        )}
      </div>

       {/* Control Footer */}
       <div className="h-12 bg-primary text-white flex items-center justify-between px-8 text-[11px] font-bold uppercase tracking-widest shrink-0">
        <div className="flex gap-6">
          <span>Tracked Persona: {selectedEntity}</span>
          <span>Event Density: {feedData.length} matches</span>
        </div>
        <div className="flex items-center gap-4">
            <button className="flex items-center gap-1.5 hover:opacity-80 transition-opacity">
                <span className="material-symbols-outlined text-sm">notifications_active</span>
                Alerts On
            </button>
        </div>
      </div>

      {/* Management Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="glass-card w-full max-w-lg rounded-2xl border border-white/10 overflow-hidden shadow-2xl">
                <div className="p-6 border-b border-white/10 flex items-center justify-between bg-primary/20">
                    <div>
                        <h3 className="text-xl font-bold text-white">Persona Management</h3>
                        <p className="text-xs text-primary/80 uppercase font-bold tracking-widest mt-1">{selectedEntity}</p>
                    </div>
                    <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-white transition-colors">
                        <span className="material-symbols-outlined">close</span>
                    </button>
                </div>

                <div className="p-8 space-y-8">
                    {mgmtLoading ? (
                        <div className="py-12 text-center text-slate-400 animate-pulse">Synchronizing persona data...</div>
                    ) : (
                        <>
                            {/* Tracking Status */}
                            <div className="space-y-4">
                                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Tracking Status</label>
                                {targetInfo ? (
                                    <div className="bg-white/5 border border-white/10 rounded-xl p-4 flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                                            <div>
                                                <p className="text-sm font-bold text-white">Active Monitor</p>
                                                <p className="text-[10px] text-slate-500">Source: {targetInfo.source}</p>
                                            </div>
                                        </div>
                                        <button 
                                            onClick={handleStopJob}
                                            className="px-3 py-1.5 bg-red-500/10 text-red-500 border border-red-500/20 rounded-lg text-[10px] font-bold uppercase hover:bg-red-500/20 transition-all"
                                        >
                                            Stop Job
                                        </button>
                                    </div>
                                ) : (
                                    <div className="bg-white/5 border border-white/10 rounded-xl p-4 flex items-center gap-3 italic text-slate-500 text-sm">
                                        <span className="material-symbols-outlined">info</span>
                                        No active background job for this entity.
                                    </div>
                                )}
                            </div>

                            {/* Schedule Control */}
                            {targetInfo && (
                                <div className="space-y-4">
                                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex justify-between">
                                        Monitor Frequency
                                        <span className="text-primary">{newInterval}m</span>
                                    </label>
                                    <input 
                                        type="range" 
                                        min="60" 
                                        max="10080" 
                                        step="60"
                                        value={newInterval}
                                        onChange={(e) => setNewInterval(parseInt(e.target.value))}
                                        className="w-full accent-primary bg-white/10 h-1.5 rounded-full appearance-none cursor-pointer"
                                    />
                                    <div className="flex justify-between text-[10px] text-slate-500 font-mono pb-2 border-b border-white/5">
                                        <span>Hourly</span>
                                        <span>Daily</span>
                                        <span>Weekly</span>
                                    </div>
                                    
                                    {/* Auto Discovery Toggle */}
                                    <div className="flex items-center justify-between pt-2">
                                        <div>
                                            <p className="text-sm font-bold text-white">Auto-Discovery</p>
                                            <p className="text-[10px] text-slate-500 mt-1">Allow this person to automatically find and track other people</p>
                                        </div>
                                        <button 
                                            onClick={() => setAllowDiscovery(!allowDiscovery)}
                                            className={cn(
                                                "w-12 h-6 rounded-full transition-colors relative flex items-center px-1 shadow-inner",
                                                allowDiscovery ? "bg-primary" : "bg-white/10"
                                            )}
                                        >
                                            <div className={cn(
                                                "w-4 h-4 rounded-full bg-white transition-all shadow-md",
                                                allowDiscovery ? "translate-x-6" : "translate-x-0"
                                            )} />
                                        </button>
                                    </div>

                                    <button 
                                        onClick={handleUpdateSchedule}
                                        className="w-full py-3 bg-primary text-white font-bold text-xs uppercase tracking-widest rounded-xl hover:shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] transition-all mt-4"
                                    >
                                        Save Configuration
                                    </button>
                                </div>
                            )}

                            {/* Destructive Actions */}
                            <div className="pt-6 border-t border-white/5">
                                <button 
                                    onClick={handleDeletePerson}
                                    className="w-full py-4 border border-red-500/20 bg-red-500/5 text-red-500 hover:bg-red-500/10 rounded-xl flex items-center justify-center gap-2 transition-all"
                                >
                                    <span className="material-symbols-outlined text-sm">delete_forever</span>
                                    <span className="text-[10px] font-bold uppercase tracking-widest">Wipe Entity Data</span>
                                </button>
                                <p className="text-[9px] text-slate-600 text-center mt-3 leading-relaxed uppercase tracking-tighter">
                                    Warning: This removes all mentions, events, and tracking history for {selectedEntity}.
                                </p>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
      )}
    </div>
  );
}
