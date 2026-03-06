"use client";

import { useEffect, useState } from "react";
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';
import { cn } from "@/lib/utils";

export default function TopicAnalysis() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8000/dashboard/data?limit=1000");
        const json = await res.json();
        setData(json.data || json);
      } catch (err) {
        console.error("Failed to fetch dashboard data:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return <div className="text-slate-400 animate-pulse flex h-screen items-center justify-center">Loading Intelligence Data...</div>;
  }

  // Calculate KPIs - Exclude PEOPLE from global market/topic analysis
  const filteredData = data.filter(d => d.entity_type !== "PERSON");
  const totalMentions = filteredData.length;
  
  const avgSentiment = filteredData.length > 0 ? (filteredData.reduce((acc, curr) => acc + curr.sentiment_score, 0) / filteredData.length).toFixed(2) : "0.00";
  const categoryCounts = filteredData.reduce((acc: any, event: any) => {
    acc[event.category || 'Uncategorized'] = (acc[event.category || 'Uncategorized'] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  
  const topTrend = Object.entries(categoryCounts).sort((a: any, b: any) => (b[1] as number) - (a[1] as number))[0]?.[0] || "None";

  // Prepare Chart Data
  const timelineData = [...filteredData]
    .filter(d => d.published_at) 

    .sort((a, b) => new Date(a.published_at).getTime() - new Date(b.published_at).getTime())
    .map(d => ({
      date: new Date(d.published_at).toLocaleDateString(),
      sentiment: d.sentiment_score,
      entity: d.entity
    }));

  const pieData = Object.entries(categoryCounts).map(([name, value]) => ({ name, value }));
  const COLORS = ['#ec5b13', '#3b82f6', '#8b5cf6', '#d946ef', '#f43f5e', '#f97316', '#eab308', '#22c55e'];

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <header className="h-16 border-b border-primary/10 flex items-center justify-between px-8 bg-background-light/50 dark:bg-background-dark/50 backdrop-blur-md z-10 w-full shrink-0">
        <div className="flex items-center gap-6">
          <h2 className="text-lg font-bold text-white">Global Topic <span className="text-primary">Analysis</span></h2>
          <div className="flex items-center gap-2 px-3 py-1 bg-primary/10 text-primary rounded-full border border-primary/20">
            <span className="material-symbols-outlined text-xs">analytics</span>
            <span className="text-[10px] font-bold uppercase tracking-tighter">Aggregate Metrics</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 rounded-full bg-primary/20 border border-primary/30 overflow-hidden flex items-center justify-center text-primary font-bold text-xs">
            JD
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto p-8 space-y-8 custom-scrollbar">
        {/* KPI Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="glass-card rounded-xl p-6 shadow-sm border-l-4 border-l-primary">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Total Mentions</div>
            <div className="text-3xl font-bold text-white tracking-tight">{totalMentions}</div>
          </div>
          <div className="glass-card rounded-xl p-6 shadow-sm border-l-4 border-l-blue-500">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Avg Sentiment</div>
            <div className={`text-3xl font-bold tracking-tight ${Number(avgSentiment) > 0 ? 'text-emerald-400' : Number(avgSentiment) < 0 ? 'text-rose-400' : 'text-slate-200'}`}>
              {avgSentiment}
            </div>
          </div>
          <div className="glass-card rounded-xl p-6 shadow-sm border-l-4 border-l-primary/50">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Top Trend</div>
            <div className="text-3xl font-bold text-indigo-400 truncate tracking-tight" title={topTrend}>{topTrend}</div>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pb-8">
          {/* Timeline Chart */}
          <div className="glass-card rounded-2xl p-6 shadow-sm flex flex-col">
            <h3 className="text-base font-bold text-white mb-6 uppercase tracking-wider flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">show_chart</span>
                Sentiment Over Time
            </h3>
            <div className="h-80 w-full relative">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={timelineData} margin={{ top: 5, right: 20, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="date" hide />
                  <YAxis stroke="#64748b" fontSize={12} tickMargin={10} axisLine={false} tickLine={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc', borderRadius: '0.75rem' }}
                    itemStyle={{ color: '#ec5b13' }}
                  />
                  <Line type="monotone" dataKey="sentiment" stroke="#ec5b13" strokeWidth={3} dot={false} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Categories Pie Chart */}
          <div className="glass-card rounded-2xl p-6 shadow-sm flex flex-col">
            <h3 className="text-base font-bold text-white mb-6 uppercase tracking-wider flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">pie_chart</span>
                Topic Distribution
            </h3>
            <div className="min-h-[400px] w-full flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="45%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                    stroke="none"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc', borderRadius: '0.75rem' }}
                    itemStyle={{ color: '#f8fafc' }}
                  />
                  <Legend verticalAlign="bottom" height={80} iconType="circle" />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
