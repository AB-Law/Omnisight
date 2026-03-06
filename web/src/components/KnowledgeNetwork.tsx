import React from 'react';

export default function KnowledgeNetwork() {
  return (
    <div className="relative h-[800px] w-full rounded-2xl overflow-hidden shadow-2xl bg-[#050505] font-display text-slate-100 flex flex-col border border-white/10" style={{ backgroundImage: 'radial-gradient(circle, rgba(236, 91, 19, 0.05) 1px, transparent 1px)', backgroundSize: '30px 30px' }}>
      
      {/* Internal Header (Optionally hide if using it within a fully-fledged page layout that has its own Top Nav) */}
      <header className="flex items-center justify-between px-8 py-4 border-b border-white/10 bg-white/5 backdrop-blur-xl z-50">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3 text-primary">
            <span className="material-symbols-outlined text-3xl">hub</span>
            <h2 className="text-slate-100 text-xl font-bold tracking-tight">The Knowledge Network</h2>
          </div>
          <div className="h-6 w-px bg-white/10"></div>
          <label className="relative flex items-center w-80">
            <span className="material-symbols-outlined absolute left-3 text-slate-400 text-xl">search</span>
            <input className="w-full bg-white/5 border-none rounded-xl py-2 pl-10 pr-4 text-sm text-slate-100 focus:ring-1 focus:ring-primary/50 placeholder:text-slate-500" placeholder="Search nodes, entities or relations..." type="text" />
          </label>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex gap-2">
            <button className="p-2 rounded-xl bg-white/5 border border-white/10 backdrop-blur-xl hover:bg-white/10 transition-colors text-slate-400">
              <span className="material-symbols-outlined">settings</span>
            </button>
            <button className="p-2 rounded-xl bg-white/5 border border-white/10 backdrop-blur-xl hover:bg-white/10 transition-colors text-slate-400">
              <span className="material-symbols-outlined">share</span>
            </button>
          </div>
        </div>
      </header>
      
      <main className="flex-1 relative overflow-hidden">
        {/* Graph SVG Background */}
        <div className="absolute inset-0 z-0 overflow-hidden">
          <svg className="w-full h-full opacity-60" viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid slice">
            <path d="M200,300 Q400,100 600,400" className="stroke-[#00D2FF] opacity-30 stroke-[1px] fill-transparent" />
            <path d="M600,400 Q800,600 400,800" className="stroke-[#00FF87] opacity-30 stroke-[1px] fill-transparent" />
            <path d="M400,800 Q100,600 200,300" className="stroke-[#ec5b13] opacity-20 stroke-[1px] fill-transparent" />
            <path d="M200,300 Q500,500 800,200" className="stroke-[#00D2FF] opacity-30 stroke-[1px] fill-transparent" />
            
            <circle cx="200" cy="300" r="6" fill="#00D2FF" className="shadow-[0_0_15px_rgba(0,210,255,0.5)]" />
            <circle cx="600" cy="400" r="8" fill="#00FF87" className="shadow-[0_0_15px_rgba(0,255,135,0.5)]" />
            <circle cx="400" cy="800" r="5" fill="#00D2FF" className="shadow-[0_0_15px_rgba(0,210,255,0.5)]" />
            <circle cx="800" cy="200" r="7" fill="#00FF87" className="shadow-[0_0_15px_rgba(0,255,135,0.5)]" />
            
            {/* Center Node */}
            <circle cx="500" cy="500" r="10" fill="#ec5b13" className="shadow-[0_0_20px_rgba(236,91,19,0.6)] animate-pulse" />
            
            <circle cx="150" cy="650" r="4" fill="#00D2FF" />
            <circle cx="850" cy="750" r="5" fill="#00FF87" />
          </svg>
        </div>

        {/* Right Info Panel */}
        <aside className="absolute top-6 right-6 bottom-6 w-80 bg-white/5 border border-white/10 backdrop-blur-xl rounded-xl flex flex-col z-20 overflow-hidden">
          <div className="p-6 border-b border-white/10">
            <h3 className="text-slate-400 text-xs font-bold uppercase tracking-widest mb-1">Entity Deep-Dive</h3>
            <h2 className="text-xl font-bold text-white">NeuralLink Corp.</h2>
            <p className="text-slate-500 text-xs font-mono mt-1">UUID: NL-772-BETA</p>
          </div>
          
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 rounded-lg bg-white/5 border border-white/5">
                <p className="text-slate-500 text-[10px] uppercase font-bold">Node Degree</p>
                <p className="text-2xl font-bold text-[#00D2FF]">1,284</p>
                <p className="text-[#00FF87] text-[10px] flex items-center gap-1">
                  <span className="material-symbols-outlined text-xs">trending_up</span> +14%
                </p>
              </div>
              <div className="p-3 rounded-lg bg-white/5 border border-white/5">
                <p className="text-slate-500 text-[10px] uppercase font-bold">Centrality</p>
                <p className="text-2xl font-bold text-[#00FF87]">0.94</p>
                <p className="text-slate-400 text-[10px]">Top 1% Tier</p>
              </div>
            </div>
            
            <div className="space-y-3">
              <div className="flex justify-between items-end">
                <p className="text-slate-400 text-xs font-medium">Sentiment Trend</p>
                <span className="text-[#00FF87] text-xs font-bold">Positive</span>
              </div>
              <div className="h-24 w-full flex items-end gap-1">
                {[40, 55, 45, 70, 65, 90, 85].map((height, i) => (
                  <div key={i} className={`bg-primary/${i === 6 ? '40' : '20'} hover:bg-primary/40 transition-colors w-full rounded-t-sm ${i === 6 ? 'ring-1 ring-primary' : ''}`} style={{ height: `${height}%` }}></div>
                ))}
              </div>
              <div className="flex justify-between text-[10px] text-slate-600 font-mono">
                <span>Q1 2024</span>
                <span>PRESENT</span>
              </div>
            </div>

            <div className="space-y-4">
              <p className="text-slate-400 text-xs font-medium border-b border-white/5 pb-2">Top Relations</p>
              <div className="flex items-center gap-3">
                <div className="size-2 rounded-full bg-[#00D2FF]"></div>
                <div className="flex-1">
                  <p className="text-sm text-slate-200">Tesla Inc.</p>
                  <p className="text-[10px] text-slate-500 uppercase">Co-Mention Frequency: 88%</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="size-2 rounded-full bg-[#00FF87]"></div>
                <div className="flex-1">
                  <p className="text-sm text-slate-200">Elon Musk</p>
                  <p className="text-[10px] text-slate-500 uppercase">Executive Relation</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="size-2 rounded-full bg-primary"></div>
                <div className="flex-1">
                  <p className="text-sm text-slate-200">Brain-Computer Interface</p>
                  <p className="text-[10px] text-slate-500 uppercase">Core Industry Domain</p>
                </div>
              </div>
            </div>
          </div>
          
          <div className="p-4 bg-white/5 border-t border-white/10">
            <button className="w-full bg-primary hover:bg-primary/90 text-white font-bold py-3 rounded-xl flex items-center justify-center gap-2 transition-all">
              <span className="material-symbols-outlined text-lg">download</span>
              Export Dataset
            </button>
          </div>
        </aside>

        {/* View Controls */}
        <div className="absolute left-6 bottom-32 flex flex-col gap-3 z-20">
          {['add', 'remove', 'explore'].map(icon => (
            <button key={icon} className="size-12 rounded-xl bg-white/5 border border-white/10 backdrop-blur-xl text-white flex items-center justify-center hover:bg-primary/20 transition-all">
              <span className="material-symbols-outlined">{icon}</span>
            </button>
          ))}
        </div>

        {/* Bottom Timeline Control panel */}
        <div className="absolute hidden lg:flex left-6 bottom-6 right-96 h-20 bg-white/5 border border-white/10 backdrop-blur-xl rounded-xl items-center px-8 gap-12 z-20">
          <div className="flex items-center gap-4 min-w-[240px]">
            <div className="flex flex-col gap-1 w-full">
              <label className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">Co-mention Density</label>
              <input className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-primary" type="range" />
            </div>
            <span className="text-xs font-mono text-primary bg-primary/10 px-2 py-1 rounded">0.74</span>
          </div>
          
          <div className="h-8 w-px bg-white/10"></div>
          
          <div className="flex-1 flex flex-col gap-1 relative">
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">Temporal Range (2018 - 2024)</label>
            <div className="relative w-full h-1 bg-white/10 rounded-lg mt-1">
              <div className="absolute left-1/4 right-1/4 h-full bg-primary rounded-lg shadow-[0_0_10px_rgba(236,91,19,0.4)]"></div>
              <div className="absolute left-1/4 -top-1.5 size-4 bg-white rounded-full border-2 border-primary shadow-lg cursor-pointer"></div>
              <div className="absolute right-1/4 -top-1.5 size-4 bg-white rounded-full border-2 border-primary shadow-lg cursor-pointer"></div>
            </div>
          </div>
          
          <div className="h-8 w-px bg-white/10"></div>
          
          <div className="flex gap-4 shrink-0">
            <div className="flex items-center gap-2">
              <div className="size-2 rounded-full bg-[#00D2FF] shadow-[0_0_15px_rgba(0,210,255,0.5)]"></div>
              <span className="text-[10px] text-slate-400 font-bold uppercase">Companies</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="size-2 rounded-full bg-[#00FF87] shadow-[0_0_15px_rgba(0,255,135,0.5)]"></div>
              <span className="text-[10px] text-slate-400 font-bold uppercase">People</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
