import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import { SignJWT } from "jose";
import { authConfig } from "@/auth.config";

export const { handlers, signIn, signOut, auth } = NextAuth({
  ...authConfig,
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  session: { strategy: "jwt" },
  callbacks: {
    async jwt({ token, account }) {
      // Sign a short-lived backend token on every first sign-in
      if (account) {
        const secret = new TextEncoder().encode(process.env.NEXTAUTH_SECRET!);
        token.backendToken = await new SignJWT({
          sub: token.sub,
          email: token.email,
          name: token.name,
          picture: token.picture,
        })
          .setProtectedHeader({ alg: "HS256" })
          .setExpirationTime("1d")
          .sign(secret);
      }
      return token;
    },
    async session({ session, token }) {
      // Expose the backend token to the client session
      session.backendToken = token.backendToken as string;
      return session;
    },
  },
});
