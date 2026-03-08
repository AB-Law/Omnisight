import NextAuth from "next-auth";
import { authConfig } from "@/auth.config";

export default NextAuth(authConfig).auth;

export const config = {
  // Protect every route except: auth callbacks, static assets, and the login page
  matcher: ["/((?!api/auth|_next/static|_next/image|favicon.ico|login).*)"],
};
