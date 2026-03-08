import type { NextAuthConfig } from "next-auth";

/**
 * Edge-compatible auth config — no Node.js modules, no providers.
 * Used only by middleware for route protection.
 * The full config (with Google provider + JWT signing) lives in auth.ts.
 */
export const authConfig: NextAuthConfig = {
  pages: { signIn: "/login" },
  callbacks: {
    authorized({ auth }) {
      // A valid session means the user is logged in
      return !!auth;
    },
  },
  providers: [],
};
