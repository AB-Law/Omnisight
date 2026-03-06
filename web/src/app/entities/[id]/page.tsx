import SentimentGauge from "@/components/SentimentGauge";
import KnowledgeNetwork from "@/components/KnowledgeNetwork";

export default async function EntityHubPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  
  return (
    <main className="max-w-[1400px] mx-auto w-full p-4 md:p-8 space-y-8 flex-1">
      {/* Hero Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-white/10">
        <div className="flex items-center gap-6">
          <div className="size-24 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center border border-primary/20 overflow-hidden shadow-2xl shadow-primary/10 text-primary font-bold text-4xl">
            {id.substring(0, 1).toUpperCase()}
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-4xl font-bold tracking-tight text-slate-900 dark:text-white">{id.toUpperCase()}</h1>
              <span className="px-3 py-1 rounded-full text-xs font-bold tracking-widest uppercase bg-emerald-500/10 text-emerald-500 border border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.2)]">Tracked</span>
            </div>
            <div className="flex items-center gap-4 mt-2">
              <span className="text-slate-500 dark:text-slate-400 font-medium">ID: {id}</span>
              <span className="size-1 bg-slate-400 rounded-full"></span>
              <span className="text-slate-500 dark:text-slate-400">Intelligence Target</span>
            </div>
          </div>
        </div>
        <div className="flex gap-3">
          <button className="px-6 py-2.5 bg-primary text-white font-bold rounded-xl shadow-lg shadow-primary/25 hover:opacity-90 transition-all">Export Report</button>
          <button className="px-4 py-2.5 bg-white/5 border border-white/10 font-semibold rounded-xl hover:bg-white/10 transition-all">Settings</button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Knowledge Network - Using 3 columns */}
        <div className="lg:col-span-3">
          <KnowledgeNetwork />
        </div>

        {/* Sentiment Gauge Side Panel */}
        <div className="bg-[#050505] border border-white/10 rounded-2xl p-6 shadow-2xl flex flex-col items-center py-10">
          <h3 className="text-sm font-bold text-slate-500 uppercase tracking-widest mb-6">Sentiment Gauge</h3>
          <SentimentGauge value={74} label="Bullish" />
          
          <p className="mt-8 text-sm text-slate-400 leading-relaxed text-center">Social signals are currently trending positive with low volatility across 14 tracked channels.</p>
          
          <div className="mt-8 grid grid-cols-2 gap-4 w-full">
            <div className="bg-white/5 p-3 rounded-xl border border-white/5">
              <span className="block text-[10px] text-slate-500 uppercase font-bold">24h Change</span>
              <span className="text-emerald-500 font-bold">+5.2%</span>
            </div>
            <div className="bg-white/5 p-3 rounded-xl border border-white/5">
              <span className="block text-[10px] text-slate-500 uppercase font-bold">Volume</span>
              <span className="text-primary font-bold">12.4K</span>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
