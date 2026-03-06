import React from 'react';

export default function HealthMonitorCard() {
  return (
    <article className="relative w-full max-w-[280px] p-5 rounded-xl border border-white/10 bg-[#0f0f14]/70 backdrop-blur-md shadow-[0_8px_32px_0_rgba(0,0,0,0.8)] overflow-hidden group shrink-0">
      {/* Background Decor/Accent */}
      <div className="absolute top-0 right-0 p-3 opacity-20 group-hover:opacity-40 transition-opacity">
        <svg className="text-neutral-400" fill="none" height="24" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" viewBox="0 0 24 24" width="24" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2v8"></path>
          <path d="m16 6-4 4-4-4"></path>
          <rect height="8" rx="2" width="20" x="2" y="14"></rect>
          <path d="M6 18h.01"></path>
          <path d="M10 18h.01"></path>
        </svg>
      </div>

      {/* Main Content */}
      <div className="flex flex-col gap-4">
        
        {/* Title and Pulse Indicator */}
        <div className="flex items-center gap-3">
          {/* Pulsing Dot Container */}
          <div className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500 shadow-[0_0_8px_#10b981,0_0_12px_rgba(16,185,129,0.4)]"></span>
          </div>
          <h2 className="text-sm font-semibold tracking-wider text-neutral-100 uppercase font-mono">
            Neural Core Alpha
          </h2>
        </div>

        {/* Divider */}
        <hr className="border-t border-white/10" />

        {/* Stats Section */}
        <div className="space-y-1">
          <p className="text-[10px] uppercase tracking-widest text-neutral-500 font-medium">
            Sync Status
          </p>
          <div className="flex justify-between items-end">
            <span className="text-xs text-neutral-300 font-mono">
              Last Pulse: <span className="text-neutral-100">2m ago</span>
            </span>
            {/* Signal Strength Micro-Visualizer */}
            <div className="flex gap-0.5 mb-0.5">
              <div className="w-1 h-2 bg-emerald-500 rounded-sm"></div>
              <div className="w-1 h-3 bg-emerald-500 rounded-sm"></div>
              <div className="w-1 h-4 bg-emerald-500 rounded-sm"></div>
              <div className="w-1 h-3 bg-neutral-700 rounded-sm"></div>
            </div>
          </div>
        </div>

        {/* Mini Footer/ID */}
        <div className="flex items-center justify-between mt-2">
          <span className="text-[9px] font-mono text-neutral-600">ID: N-ALPHA-0192</span>
          <div className="px-1.5 py-0.5 rounded bg-neutral-800 border border-neutral-700">
            <span className="text-[8px] text-neutral-400 font-bold uppercase">Active</span>
          </div>
        </div>
      </div>

      {/* Scanning Animation Effect Overlay */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden rounded-xl">
        <div className="w-full h-[1px] bg-gradient-to-r from-transparent via-emerald-500/20 to-transparent absolute top-0 animate-scan"></div>
      </div>
    </article>
  );
}
