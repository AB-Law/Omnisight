import React from 'react';

export default function SentimentGauge({ value = 84.2, label = "Cyber-Intelligence" }: { value?: number, label?: string }) {
  // Circumference = 2 * PI * r (approx 263.89 for r=42)
  const circumference = 263.89;
  const dashoffset = circumference * (1 - value / 100);
  const angle = (value / 100) * 360;

  return (
    <div className="relative flex flex-col items-center justify-center w-80 h-80 shrink-0">
      {/* SVG Gauge Structure */}
      <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
        {/* Defined Gradients for the Gauge Fill */}
        <defs>
          <linearGradient id="cyanEmeraldGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#22d3ee" /> {/* Cyan-400 */}
            <stop offset="100%" stopColor="#10b981" /> {/* Emerald-500 */}
          </linearGradient>
          {/* Filter for the glow effect on the progress bar */}
          <filter id="glow">
            <feGaussianBlur stdDeviation="1.5" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Background Track (Semi-transparent) */}
        <circle 
          cx="50" cy="50" r="42" 
          fill="transparent" 
          stroke="rgba(255, 255, 255, 0.05)" 
          strokeWidth="8" 
        />
        
        {/* Progress Fill */}
        <circle 
          className="transition-all duration-1000 ease-out" 
          cx="50" cy="50" r="42" 
          fill="transparent" 
          stroke="url(#cyanEmeraldGradient)" 
          strokeWidth="8" 
          strokeLinecap="round" 
          strokeDasharray={circumference} 
          strokeDashoffset={dashoffset} 
          filter="url(#glow)" 
        />
        
        {/* Floating Indicator at the tip */}
        <g transform={`rotate(${angle}, 50, 50)`}>
          <circle cx="92" cy="50" r="2.5" fill="white" className="glow-effect" />
        </g>
      </svg>

      {/* Center Content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {/* Main Value */}
        <div className="text-white font-bold text-4xl tracking-tighter flex items-baseline">
          <span>{value}</span>
          <span className="text-zinc-500 text-xl ml-1">/100</span>
        </div>
        
        {/* Secondary Label */}
        <div className="text-cyan-400 text-[10px] font-black uppercase tracking-[0.2em] mt-2 opacity-80">
          {label}
        </div>
      </div>

      {/* Decorative Elements */}
      <div className="absolute -inset-4 border border-cyan-500/10 rounded-full pointer-events-none" />
      <div className="absolute -inset-1 border border-emerald-500/5 rounded-full pointer-events-none" />
    </div>
  );
}
