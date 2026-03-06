import EntityTriageRow from "@/components/EntityTriageRow";

export default function EntitiesPage() {
  // Mock data for the triage rows
  const entities = [
    { id: 'NODE-8821', origin: 'Singapore-01', volatility: 72, status: 'STABLE', data: [10, 15, 12, 18, 25, 22, 30, 28, 35, 45] },
    { id: 'NODE-4392', origin: 'Frankfurt-DX', volatility: 94, status: 'CRITICAL', data: [5, 8, 15, 25, 45, 60, 85, 90, 88, 95] },
    { id: 'NODE-1104', origin: 'US-East-Sec', volatility: 23, status: 'NOMINAL', data: [45, 42, 40, 38, 35, 30, 32, 28, 25, 22] },
  ];

  return (
    <main className="max-w-[1400px] mx-auto w-full p-4 md:p-8 space-y-8 flex-1">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-primary/20">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-white mb-2">Tracked Entities</h1>
          <p className="text-slate-400">Manage and monitor your intelligence targets.</p>
        </div>
        <div className="flex gap-3">
          <button className="px-6 py-2.5 bg-primary text-white font-bold rounded-xl shadow-lg shadow-primary/25 hover:opacity-90 transition-all">Add Entity</button>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-sm font-bold text-slate-500 uppercase tracking-widest mb-4">Priority Triage queue</h3>
        <div className="rounded-2xl border border-white/10 overflow-hidden shadow-2xl bg-black/20">
          {entities.map((entity) => (
            <EntityTriageRow key={entity.id} {...entity} />
          ))}
        </div>
      </div>
    </main>
  );
}
