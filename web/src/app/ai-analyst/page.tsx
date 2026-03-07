import { Suspense } from "react";
import ChatInterface from "@/components/chat/ChatInterface";

export const metadata = {
  title: "AI Analyst — Omnisight",
  description: "Omni-Intelligence Bot: AI-powered intelligence analysis with entity profiling, sentiment trends, market correlation, and knowledge graph.",
};

export default function AIAnalystPage() {
  return (
    <div className="h-full flex flex-col">
      <Suspense fallback={<div className="flex-1 flex items-center justify-center text-slate-600 text-sm">Loading...</div>}>
        <ChatInterface />
      </Suspense>
    </div>
  );
}
