'use client';

import React, { useEffect, useRef } from 'react';

interface EntityTriageRowProps {
  id: string;
  origin: string;
  volatility: number;
  status: string;
  data: number[];
}

export default function EntityTriageRow({ 
  id = 'NODE-8821', 
  origin = 'Singapore-01', 
  volatility = 72, 
  status = 'STABLE',
  data = [10, 15, 12, 18, 25, 22, 30, 28, 35, 45]
}: EntityTriageRowProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    
    // Setup dimensions for high DPI
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    
    // Clear previous drawing
    ctx.clearRect(0, 0, rect.width, rect.height);

    const width = rect.width;
    const height = rect.height;
    const step = width / (Math.max(data.length - 1, 1));

    ctx.beginPath();
    // Use emerald-500 from Tailwind (#10b981)
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    data.forEach((val, i) => {
      // Assuming max value is around 50 for mapping
      const maxVal = Math.max(...data, 50);
      const x = i * step;
      const y = height - (val / maxVal) * height;

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });

    ctx.stroke();

    // Add a subtle glow to the line
    ctx.shadowBlur = 4;
    ctx.shadowColor = '#10b981';
    ctx.stroke();
    
    // Reset shadow for future draws
    ctx.shadowBlur = 0;
  }, [data]);

  return (
    <div className="w-full group flex items-center justify-between px-6 py-4 bg-white/5 backdrop-blur-md border-b border-white/10 hover:bg-white/10 transition-all duration-300 ease-in-out">
      {/* LeftSection - Identifier */}
      <div className="flex-1">
        <a className="text-sky-400 font-mono text-sm tracking-wider font-bold animate-glow hover:text-sky-300 transition-colors" href="#">
          #{id}
        </a>
      </div>

      {/* CenterSection - Metrics */}
      <div className="flex-[3] flex items-center gap-8 px-4">
        {/* Origin Info */}
        <div className="flex flex-col">
          <span className="text-xs text-slate-500 uppercase tracking-tighter">Origin</span>
          <span className="text-slate-200 font-medium text-sm">{origin}</span>
        </div>

        {/* Volatility Progress */}
        <div className="flex-1 flex flex-col gap-1.5">
          <div className="flex justify-between items-end">
            <span className="text-[10px] text-slate-400 uppercase tracking-widest">Volatility</span>
            <span className="text-xs font-mono text-cyan-400">{volatility}%</span>
          </div>
          <div className="w-full bg-slate-800 h-1 rounded-full overflow-hidden">
            <div className="h-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.6)]" style={{ width: `${volatility}%` }}></div>
          </div>
        </div>

        {/* Status Badge */}
        <div className="flex items-center">
          <span className="px-3 py-1 rounded-full text-[10px] font-bold tracking-widest bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-[0_0_10px_rgba(16,185,129,0.2)]">
            {status}
          </span>
        </div>
      </div>

      {/* RightSection - Sparkline */}
      <div className="flex-1 flex justify-end">
        <div className="w-24 h-8">
          <canvas ref={canvasRef} style={{ width: '100%', height: '100%' }}></canvas>
        </div>
      </div>
    </div>
  );
}
