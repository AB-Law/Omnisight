import React from 'react';

export default function GlobalIntelligenceFeed() {
  return (
    <div className="flex bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100 font-display">
      {/* Sidebar Filters */}
      <aside className="w-72 border-r border-primary/20 flex flex-col h-[calc(100vh-80px)] shrink-0">
        <nav className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* Filter Section: Source */}
          <div>
            <label className="text-[11px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-3 block px-2">Data Source</label>
            <div className="space-y-1">
              <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl bg-primary/10 text-primary border border-primary/20">
                <span className="material-symbols-outlined text-sm">public</span>
                <span className="text-sm font-medium">All Sources</span>
              </button>
              <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-primary/5 text-slate-600 dark:text-slate-400 transition-colors">
                <span className="material-symbols-outlined text-sm">alternate_email</span>
                <span className="text-sm font-medium">Twitter Feed</span>
              </button>
              <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-primary/5 text-slate-600 dark:text-slate-400 transition-colors">
                <span className="material-symbols-outlined text-sm">forum</span>
                <span className="text-sm font-medium">Reddit Pulse</span>
              </button>
              <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-primary/5 text-slate-600 dark:text-slate-400 transition-colors">
                <span className="material-symbols-outlined text-sm">newspaper</span>
                <span className="text-sm font-medium">Mainstream Media</span>
              </button>
            </div>
          </div>

          {/* Filter Section: Geography */}
          <div>
            <label className="text-[11px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-3 block px-2">Geography</label>
            <div className="space-y-1">
              <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-primary/5 text-slate-600 dark:text-slate-400 transition-colors cursor-pointer">
                <span className="material-symbols-outlined text-sm">map</span>
                <span className="text-sm font-medium">Global Map</span>
              </div>
              <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-primary/5 text-slate-600 dark:text-slate-400 transition-colors cursor-pointer">
                <span className="material-symbols-outlined text-sm">near_me</span>
                <span className="text-sm font-medium">Near Me</span>
              </div>
            </div>
          </div>

          {/* Filter Section: Sentiment */}
          <div>
            <label className="text-[11px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-3 block px-2">Sentiment Amplitude</label>
            <div className="px-2 pt-2">
              <input className="w-full h-1.5 bg-primary/20 rounded-full appearance-none flex cursor-pointer accent-primary" type="range" />
              <div className="flex justify-between mt-2 text-[10px] text-slate-500 font-medium">
                <span>STABLE</span>
                <span>VOLATILE</span>
              </div>
            </div>
          </div>
        </nav>
        <div className="p-4 border-t border-primary/10">
          <button className="w-full py-3 bg-primary hover:bg-primary/90 text-white rounded-xl font-bold text-sm shadow-lg shadow-primary/20 flex items-center justify-center gap-2 transition-all">
            <span className="material-symbols-outlined text-sm">refresh</span>
            Refresh Feed
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col relative overflow-hidden h-[calc(100vh-80px)]">
        <header className="h-16 border-b border-primary/10 flex items-center justify-between px-8 bg-background-light/50 dark:bg-background-dark/50 z-10 shrink-0">
          <div className="flex items-center gap-6">
            <h2 className="text-lg font-bold">Global Intelligence <span className="text-primary">Feed</span></h2>
            <div className="flex items-center gap-2 px-3 py-1 bg-green-500/10 text-green-500 rounded-full border border-green-500/20">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
              <span className="text-[10px] font-bold uppercase tracking-tighter">Live Stream Active</span>
            </div>
          </div>
        </header>

        {/* Scrollable Feed */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6">
          
          {/* Map Integration */}
          <div className="h-64 rounded-xl border border-primary/20 relative overflow-hidden bg-primary/5">
            <div className="absolute inset-0 opacity-30 grayscale invert dark:invert-0" style={{ backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuBx-Ukq2s_rHqN9MNdjKT7tKD2vbmSfHk8AfGhbMnta_Dq55nhiPqy_0I_b1f64ScMEZ3CvWQQbfng3RnqW0CZiA7pLr2_gYq--JUA0llquFxdU1l_4aurNaztqeSfsDnPqINdkv21LIfycx4B5Xlf3jfaVyhhmCPDKPKq_qyGA1JUXbh2mjPOjEFTov74q1X1HhXBAtzNMpp3uXbrJ3RlRUYjqbA81mdvemjEeW28Mc4vXFGxXFqcnzHyGNn3ucLkOotSkzr2BUvrZ')", backgroundSize: "cover" }}></div>
            <div className="absolute inset-0 bg-gradient-to-t from-background-dark/80 to-transparent"></div>
            <div className="absolute bottom-4 left-4 flex items-center gap-3">
              <div className="p-2 bg-primary rounded-lg">
                <span className="material-symbols-outlined text-white text-sm">my_location</span>
              </div>
              <p className="text-sm font-bold text-white uppercase tracking-widest">Active Monitoring: Region 7-A</p>
            </div>
          </div>

          {/* Feed Card 1: Critical */}
          <div className="bg-primary/5 backdrop-blur-md border border-primary/20 hover:border-primary/40 transition-colors rounded-xl p-5 relative overflow-hidden group shadow-sm">
            <div className="absolute top-0 right-0 p-4">
              <span className="px-3 py-1 bg-red-500 text-white text-[10px] font-bold rounded-full shadow-[0_0_10px_rgba(239,68,68,0.5)]">CRITICAL</span>
            </div>
            <div className="flex gap-5">
              <div className="flex flex-col items-center gap-2">
                <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20">
                  <span className="material-symbols-outlined text-blue-500">alternate_email</span>
                </div>
                <span className="text-[10px] font-bold text-slate-500">@OSINT_1</span>
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-bold mb-2 group-hover:text-primary transition-colors">Massive DDoS synchronization detected across Southeast Asian banking clusters</h3>
                <p className="text-slate-400 text-sm leading-relaxed mb-4">
                  <span className="text-primary font-bold">AI Summary:</span> Coordinated traffic spikes suggest a state-sponsored actor testing infrastructure resilience. Attack magnitude estimated at 2.4 Tbps.
                </p>
                <div className="flex items-center gap-4 text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                  <span className="flex items-center gap-1"><span className="material-symbols-outlined text-xs">schedule</span> 2m ago</span>
                  <span className="flex items-center gap-1"><span className="material-symbols-outlined text-xs">location_on</span> Singapore / Jakarta</span>
                  <span className="flex items-center gap-1"><span className="material-symbols-outlined text-xs">show_chart</span> 98% Confidence</span>
                </div>
              </div>
            </div>
          </div>

          {/* Feed Card 2: Neutral */}
          <div className="bg-primary/5 backdrop-blur-md border border-primary/20 hover:border-primary/40 transition-colors border-l-4 border-l-slate-500/40 rounded-xl p-5 relative overflow-hidden group shadow-sm">
            <div className="absolute top-0 right-0 p-4">
              <span className="px-3 py-1 bg-slate-500/20 text-slate-400 text-[10px] font-bold rounded-full border border-slate-500/30">NEUTRAL</span>
            </div>
            <div className="flex gap-5">
              <div className="flex flex-col items-center gap-2">
                <div className="w-12 h-12 rounded-xl bg-orange-500/10 flex items-center justify-center border border-orange-500/20">
                  <span className="material-symbols-outlined text-orange-500">newspaper</span>
                </div>
                <span className="text-[10px] font-bold text-slate-500">REUTERS</span>
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-bold mb-2 group-hover:text-primary transition-colors">Submarine cable repair vessel deployed to North Atlantic sector</h3>
                <p className="text-slate-400 text-sm leading-relaxed mb-4">
                  <span className="text-primary font-bold">AI Summary:</span> Scheduled maintenance or reactive repair for the 'Atlantic-3' fiber line. No immediate service degradation reported.
                </p>
                <div className="flex items-center gap-4 text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                  <span className="flex items-center gap-1"><span className="material-symbols-outlined text-xs">schedule</span> 15m ago</span>
                  <span className="flex items-center gap-1"><span className="material-symbols-outlined text-xs">location_on</span> Atlantic Ocean</span>
                  <span className="flex items-center gap-1"><span className="material-symbols-outlined text-xs">show_chart</span> 82% Confidence</span>
                </div>
              </div>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}
