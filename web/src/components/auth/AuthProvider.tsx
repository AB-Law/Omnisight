"use client";

import { useSession } from "next-auth/react";
import { useEffect } from "react";
import { setAuthToken } from "@/lib/api";

/**
 * Subscribes to the NextAuth session and keeps the api.ts token store in sync
 * so all fetchFromApi / sendMessage calls automatically include the Bearer header.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { data: session } = useSession();

  useEffect(() => {
    setAuthToken(session?.backendToken ?? null);
  }, [session]);

  return <>{children}</>;
}
