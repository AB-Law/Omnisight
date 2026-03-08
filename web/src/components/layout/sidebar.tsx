"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import { cn } from "@/lib/utils";

const navigation = [
  { name: "AI Analyst", href: "/ai-analyst", icon: "smart_toy" },
  { name: "Global Intelligence", href: "/global-intelligence", icon: "public" },
  { name: "Companies", href: "/", icon: "business" },
  { name: "Topics", href: "/topic-analysis", icon: "analytics" },
  { name: "People", href: "/people-watch", icon: "person_search" },
  { name: "Knowledge Graph", href: "/knowledge-graph", icon: "hub" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-72 bg-[#1a1310] border-r border-primary/20 flex flex-col h-full z-20 sidebar-glow">
      <div className="p-6 border-b border-primary/10">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary rounded-lg">
            <span className="material-symbols-outlined text-white">shield_person</span>
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-tight text-white">OMNISIGHT</h1>
            <p className="text-[10px] uppercase tracking-[0.2em] text-primary font-bold">Terminal v0.0.2</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">
        <div>
          <label className="text-[11px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-3 block px-2">Navigation</label>
          <div className="space-y-1">
            {navigation.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all group",
                    isActive
                      ? "bg-primary/10 text-primary border border-primary/20 shadow-[0_0_15px_rgba(236,91,19,0.05)]"
                      : "text-slate-600 dark:text-slate-400 hover:bg-primary/5 hover:text-primary"
                  )}
                >
                  <span className={cn(
                    "material-symbols-outlined text-sm transition-transform group-hover:scale-110",
                    isActive ? "text-primary" : "text-slate-500"
                  )}>
                    {item.icon}
                  </span>
                  <span className="text-sm font-medium">{item.name}</span>
                </Link>
              );
            })}
          </div>
        </div>

        {pathname === "/global-intelligence" && (
          <>
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
              </div>
            </div>
            <div>
              <label className="text-[11px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-3 block px-2">Sentiment Amplitude</label>
              <div className="px-2 pt-2">
                <input className="w-full h-1.5 bg-primary/20 rounded-full appearance-none cursor-pointer accent-primary" type="range" />
                <div className="flex justify-between mt-2 text-[10px] text-slate-500 font-medium">
                  <span>STABLE</span>
                  <span>VOLATILE</span>
                </div>
              </div>
            </div>
          </>
        )}

        <div>
          <label className="text-[11px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-3 block px-2">Management</label>
          <div className="space-y-1">
            <Link
              href="/trackers"
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all group",
                pathname === "/trackers"
                  ? "bg-primary/10 text-primary border border-primary/20 shadow-[0_0_15px_rgba(236,91,19,0.05)]"
                  : "text-slate-600 dark:text-slate-400 hover:bg-primary/5 hover:text-primary"
              )}
            >
              <span className={cn(
                "material-symbols-outlined text-sm transition-transform group-hover:scale-110",
                pathname === "/trackers" ? "text-primary" : "text-slate-500"
              )}>
                settings
              </span>
              <span className="text-sm font-medium">Active Trackers</span>
            </Link>
          </div>
        </div>
      </nav>

      <div className="p-4 border-t border-primary/10 space-y-3">
        <button
          onClick={() => window.location.reload()}
          className="w-full py-2.5 bg-primary hover:bg-primary/90 text-white rounded-xl font-bold text-sm shadow-lg shadow-primary/20 flex items-center justify-center gap-2 transition-all"
        >
          <span className="material-symbols-outlined text-sm">refresh</span>
          Sync Terminal
        </button>

        <UserPanel />
      </div>
    </aside>
  );
}

function UserPanel() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return <div className="h-10 rounded-xl bg-white/5 animate-pulse" />;
  }

  if (!session) return null;

  const initials = session.user?.name
    ?.split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("") ?? "?";

  return (
    <div className="flex items-center gap-3 px-2 py-2 rounded-xl bg-white/5">
      {session.user?.image ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={session.user.image}
          alt={session.user.name ?? ""}
          className="w-8 h-8 rounded-full object-cover shrink-0"
        />
      ) : (
        <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-primary to-orange-700 flex items-center justify-center font-bold text-xs text-white shrink-0">
          {initials}
        </div>
      )}
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold text-white truncate">{session.user?.name}</p>
        <p className="text-[10px] text-slate-500 truncate">{session.user?.email}</p>
      </div>
      <button
        onClick={() => signOut({ callbackUrl: "/login" })}
        title="Sign out"
        className="shrink-0 p-1.5 rounded-lg text-slate-400 hover:text-primary hover:bg-primary/10 transition-colors"
      >
        <span className="material-symbols-outlined text-base">logout</span>
      </button>
    </div>
  );
}
