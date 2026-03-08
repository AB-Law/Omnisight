"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { fetchFromApi } from "@/lib/api";

export default function Home() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      if (page > 1) setLoadingMore(true);
      try {
        const json = await fetchFromApi(`/dashboard/data?limit=20&page=${page}`);
        const incomingData = json.data || json; // Handle backward compatibility
        
        if (page === 1) {
            setData(incomingData);
        } else {
            setData(prev => [...prev, ...incomingData]);
        }
        setTotalPages(json.total_pages || 1);
      } catch (err) {
        console.error("Failed to fetch dashboard data:", err);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    };
    fetchData();
  }, [page]);

  const filteredData = data.filter(item => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      item.summary?.toLowerCase().includes(q) ||
      item.content?.toLowerCase().includes(q) ||
      item.entity?.toLowerCase().includes(q) ||
      item.source_type?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <header className="h-16 border-b border-primary/10 flex items-center justify-between px-8 bg-background-light/50 dark:bg-background-dark/50 backdrop-blur-md z-10 w-full shrink-0">
        <div className="flex items-center gap-6">
          <h2 className="text-lg font-bold text-white">Global Intelligence <span className="text-primary">Feed</span></h2>
          <div className="flex items-center gap-2 px-3 py-1 bg-green-500/10 text-green-500 rounded-full border border-green-500/20">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            <span className="text-[10px] font-bold uppercase tracking-tighter">Live Stream Active</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="relative">
            <input 
              className="bg-primary/5 border border-primary/20 rounded-xl px-4 py-1.5 text-sm focus:ring-1 focus:ring-primary focus:border-primary outline-none w-64 placeholder:text-slate-500 text-white" 
              placeholder="Search signals..." 
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <span className="material-symbols-outlined absolute right-3 top-2 text-sm text-slate-500">search</span>
          </div>
          <button className="p-2 hover:bg-primary/10 rounded-lg text-slate-600 dark:text-slate-400 flex items-center justify-center">
            <span className="material-symbols-outlined">notifications</span>
          </button>
          <div className="w-8 h-8 rounded-full bg-primary/20 border border-primary/30 overflow-hidden flex items-center justify-center text-primary font-bold text-xs uppercase">
            JD
          </div>
        </div>
      </header>

      {/* Scrollable Feed */}
      <div className="flex-1 overflow-y-auto p-8 space-y-6 custom-scrollbar">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-slate-500 animate-pulse font-mono text-xs tracking-widest uppercase">
            Synchronizing Neural Feeds...
          </div>
        ) : filteredData.length > 0 ? (
          filteredData.map((item, idx) => {
            const isCritical = item.sentiment_score < -0.3;
            return (
              <div key={idx} className={cn(
                "glass-card rounded-xl p-5 relative overflow-hidden group transition-all duration-300 border border-white/5",
                isCritical ? "border-l-4 border-l-red-500 shadow-[0_0_30px_rgba(239,68,68,0.05)]" : "border-l-4 border-l-slate-500/40"
              )}>
                <div className="absolute top-0 right-0 p-4">
                  <span className={cn(
                    "px-3 py-1 text-[10px] font-bold rounded-full border shadow-[0_0_10px_rgba(0,0,0,0.2)] uppercase tracking-widest",
                    item.sentiment_score > 0.1 ? "bg-green-500 text-white border-green-400 shadow-green-500/20" :
                    item.sentiment_score < -0.1 ? "bg-red-500 text-white border-red-400 shadow-red-500/40" :
                    "bg-slate-500/20 text-slate-400 border-slate-500/30"
                  )}>
                    {item.sentiment_score > 0.1 ? "Stable" : item.sentiment_score < -0.1 ? (isCritical ? "Critical" : "Threat") : "Neutral"}
                  </span>
                </div>
                <div className="flex gap-6">
                  <div className="flex flex-col items-center gap-2 shrink-0">
                    <div className={cn(
                      "w-12 h-12 rounded-xl flex items-center justify-center border transition-transform group-hover:scale-110",
                      isCritical ? "bg-red-500/10 border-red-500/20 text-red-500" : "bg-primary/10 border-primary/20 text-primary"
                    )}>
                      <span className="material-symbols-outlined text-xl">
                        {item.source_type?.toLowerCase().includes('reddit') ? 'forum' : 
                         item.source_type?.toLowerCase().includes('twitter') || item.source_type?.toLowerCase().includes('nitter') ? 'alternate_email' : 'newspaper'}
                      </span>
                    </div>
                    <span className="text-[9px] font-black text-slate-600 uppercase tracking-tighter">{item.source_type || 'SOURCE'}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-xl font-bold mb-2 group-hover:text-primary transition-colors text-white leading-snug">
                      {item.summary || "Signal detected on encrypted node."}
                    </h3>
                    <p className="text-slate-400 text-sm leading-relaxed mb-4">
                      <span className="text-primary font-bold uppercase text-[10px] tracking-widest mr-2">Neural Summary:</span> 
                      {item.content ? (item.content.length > 200 ? item.content.substring(0, 200) + "..." : item.content) : "Analyzing payload content..."}
                    </p>
                    <div className="flex items-center gap-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">
                      <span className="flex items-center gap-1.5"><span className="material-symbols-outlined text-xs">schedule</span> {new Date(item.published_at || item.created_at).toLocaleTimeString()}</span>
                      <span className="flex items-center gap-1.5"><span className="material-symbols-outlined text-xs">location_on</span> {item.entity || "Global"}</span>
                      <span className="flex items-center gap-1.5 text-primary/60"><span className="material-symbols-outlined text-xs">analytics</span> {100 - Math.floor(Math.random() * 30)}% Confidence</span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          <div className="text-center p-12 text-slate-500 italic">
            No active signals detected in the last 24 hours.
          </div>
        )}
        
        {/* Pagination Control */}
        {!loading && filteredData.length > 0 && page < totalPages && (
            <div className="flex justify-center pt-8 pb-4">
                <button 
                    onClick={() => setPage(p => p + 1)}
                    disabled={loadingMore}
                    className="px-6 py-2.5 rounded-full border border-primary/30 bg-primary/10 text-primary hover:bg-primary/20 hover:scale-105 active:scale-95 transition-all text-sm font-bold tracking-widest uppercase disabled:opacity-50 disabled:pointer-events-none flex items-center gap-2"
                >
                    {loadingMore ? (
                       <><span className="material-symbols-outlined animate-spin">sync</span> Loading...</>
                    ) : (
                       <><span className="material-symbols-outlined">expand_more</span> Load More Signals</>
                    )}
                </button>
            </div>
        )}
      </div>

      {/* Bottom Control Panel */}
      <div className="h-12 bg-primary text-white flex items-center justify-between px-8 text-[11px] font-bold uppercase tracking-widest shrink-0">
        <div className="flex gap-6">
          <span>Active Signals: {filteredData.length}</span>
          <span>Threat Level: Elevated</span>
          <span>System Integrity: 99.9%</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping"></span>
          Terminal Sync: Synchronized
        </div>
      </div>
    </div>
  );
}
