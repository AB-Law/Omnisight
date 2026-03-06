import React from 'react';

export default function TrackerConfiguration() {
  return (
    <div className="flex flex-col lg:flex-row gap-6 w-full">
      <div className="flex-1 flex flex-col gap-6">
        <div className="mb-4">
          <h1 className="text-3xl font-extrabold text-white tracking-tight">Tracker Control Center</h1>
          <p className="text-slate-400 mt-1">Configure and deploy high-fidelity autonomous data scrapers.</p>
        </div>
        
        <div className="bg-[#2d1e14]/65 backdrop-blur-md border border-primary/20 shadow-[0_0_20px_rgba(255,152,0,0.12)] rounded-2xl p-8 relative overflow-hidden">
          {/* Progress Steps */}
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
          
          <form className="space-y-8">
            <div className="space-y-6">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300 uppercase tracking-wider">Target Entity Name</label>
                <input 
                  className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-4 text-white placeholder:text-slate-600 focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all outline-none" 
                  placeholder="e.g. Project Cygnus Internal" 
                  type="text" 
                />
              </div>

              <div className="space-y-4">
                <label className="text-sm font-medium text-slate-300 uppercase tracking-wider">Source Selection</label>
                <div className="grid grid-cols-3 gap-4">
                  <button className="flex flex-col items-center justify-center gap-3 p-6 rounded-xl border border-primary bg-primary/10 transition-all group" type="button">
                    <span className="material-symbols-outlined text-3xl text-primary group-hover:scale-110 transition-transform">newspaper</span>
                    <span className="text-xs font-bold uppercase tracking-widest text-primary">Global News</span>
                  </button>
                  <button className="flex flex-col items-center justify-center gap-3 p-6 rounded-xl border border-white/10 bg-white/5 hover:border-white/30 transition-all group" type="button">
                    <span className="material-symbols-outlined text-3xl text-slate-400 group-hover:scale-110 transition-transform">forum</span>
                    <span className="text-xs font-bold uppercase tracking-widest text-slate-400">Reddit Hub</span>
                  </button>
                  <button className="flex flex-col items-center justify-center gap-3 p-6 rounded-xl border border-white/10 bg-white/5 hover:border-white/30 transition-all group" type="button">
                    <span className="material-symbols-outlined text-3xl text-slate-400 group-hover:scale-110 transition-transform">alternate_email</span>
                    <span className="text-xs font-bold uppercase tracking-widest text-slate-400">X (Twitter)</span>
                  </button>
                </div>
              </div>

              <div className="space-y-6">
                <div className="flex justify-between">
                  <label className="text-sm font-medium text-slate-300 uppercase tracking-wider">Refresh Interval</label>
                  <span className="text-primary font-mono font-bold">15m</span>
                </div>
                <div className="relative w-full h-2 bg-white/10 rounded-full">
                  <div className="absolute left-0 top-0 h-full w-1/3 bg-primary rounded-full shadow-[0_0_12px_rgba(255,152,0,0.6)]"></div>
                  <div className="absolute left-1/3 top-1/2 -translate-y-1/2 -translate-x-1/2 w-5 h-5 bg-white border-2 border-primary rounded-full cursor-pointer"></div>
                </div>
                <div className="flex justify-between text-[10px] text-slate-500 font-bold uppercase tracking-tighter">
                  <span>Realtime</span>
                  <span>5 min</span>
                  <span>15 min</span>
                  <span>1 hour</span>
                  <span>Daily</span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between pt-6 border-t border-white/10">
              <button className="text-slate-400 hover:text-white font-semibold text-sm transition-colors" type="button">Cancel Session</button>
              <button className="bg-primary hover:bg-primary/90 text-background-dark font-bold px-8 py-3 rounded-xl transition-all flex items-center gap-2 group shadow-lg shadow-primary/20" type="button">
                Next Configuration
                <span className="material-symbols-outlined text-lg group-hover:translate-x-1 transition-transform">arrow_forward</span>
              </button>
            </div>
          </form>
        </div>
      </div>

      <aside className="w-full lg:w-80 flex flex-col gap-4">
        <div className="bg-[#2d1e14]/65 backdrop-blur-md border border-primary/20 rounded-2xl p-6 flex-1 flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-sm font-bold uppercase tracking-widest text-slate-100 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-xl">memory</span>
              Active Scrapers
            </h3>
            <span className="bg-primary/10 text-primary text-[10px] px-2 py-0.5 rounded-full border border-primary/20 font-bold">4 LIVE</span>
          </div>

          <div className="space-y-4 overflow-y-auto max-h-[600px] pr-2 custom-scrollbar">
            {/* Scraper Item 1 */}
            <div className="bg-white/5 border border-white/10 rounded-xl p-4 hover:border-primary/30 transition-all cursor-pointer group">
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-[#E04000] pulse-red"></div>
                  <span className="text-xs font-bold text-white tracking-tight">CRYPTO_SENTIMENT_A1</span>
                </div>
                <span className="text-[10px] font-mono text-slate-500">PID: 8821</span>
              </div>
              <div className="flex items-center gap-2 mb-3">
                <div className="flex -space-x-2">
                  <div className="w-5 h-5 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center"><span className="material-symbols-outlined text-[10px] text-slate-400">alternate_email</span></div>
                  <div className="w-5 h-5 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center"><span className="material-symbols-outlined text-[10px] text-slate-400">forum</span></div>
                </div>
                <p className="text-[11px] text-slate-400">Scanning 142 endpoints...</p>
              </div>
              <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-[#E04000]/50 w-3/4"></div>
              </div>
            </div>

            {/* Scraper Item 2 */}
            <div className="bg-white/5 border border-white/10 rounded-xl p-4 hover:border-primary/30 transition-all cursor-pointer group">
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-[#E04000] pulse-red"></div>
                  <span className="text-xs font-bold text-white tracking-tight">MARKET_PULSE_GLOBAL</span>
                </div>
                <span className="text-[10px] font-mono text-slate-500">PID: 9012</span>
              </div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-5 h-5 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center"><span className="material-symbols-outlined text-[10px] text-slate-400">newspaper</span></div>
                <p className="text-[11px] text-slate-400">Parsing BBC, Reuters, AP...</p>
              </div>
              <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-[#E04000]/50 w-1/2"></div>
              </div>
            </div>

            {/* Scraper Item 3 */}
            <div className="bg-white/5 border border-white/10 rounded-xl p-4 hover:border-primary/30 transition-all cursor-pointer group">
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-[#E04000] pulse-red"></div>
                  <span className="text-xs font-bold text-white tracking-tight">INTEL_LEAK_TRACKER</span>
                </div>
                <span className="text-[10px] font-mono text-slate-500">PID: 4432</span>
              </div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-5 h-5 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center"><span className="material-symbols-outlined text-[10px] text-slate-400">lan</span></div>
                <p className="text-[11px] text-slate-400">Deep web surface sweep...</p>
              </div>
              <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-[#E04000]/50 w-[90%]"></div>
              </div>
            </div>
          </div>

          <div className="mt-auto pt-6">
            <div className="p-4 rounded-xl bg-primary/5 border border-primary/10">
              <div className="flex items-center gap-3 mb-2">
                <span className="material-symbols-outlined text-primary">analytics</span>
                <span className="text-xs font-bold text-slate-200">System Resources</span>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-[10px] font-mono">
                  <span className="text-slate-500 uppercase">CPU Load</span>
                  <span className="text-primary">32.4%</span>
                </div>
                <div className="flex justify-between text-[10px] font-mono">
                  <span className="text-slate-500 uppercase">Memory</span>
                  <span className="text-primary">12.1 GB / 32 GB</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div className="bg-white/5 border border-white/10 rounded-2xl p-4">
          <button className="w-full py-3 rounded-xl border border-white/10 text-white text-xs font-bold uppercase tracking-widest hover:bg-white/5 transition-all flex items-center justify-center gap-2">
            <span className="material-symbols-outlined text-sm">terminal</span>
            Open System Logs
          </button>
        </div>
      </aside>
    </div>
  );
}
