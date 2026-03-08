"use client";

import { signIn } from "next-auth/react";

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background-dark">
      <div className="w-full max-w-sm mx-4">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-10">
          <div className="p-3 bg-primary rounded-xl">
            <span className="material-symbols-outlined text-white text-3xl">shield_person</span>
          </div>
          <div>
            <h1 className="font-bold text-2xl tracking-tight text-white">OMNISIGHT</h1>
            <p className="text-[10px] uppercase tracking-[0.2em] text-primary font-bold">
              Terminal v0.0.2
            </p>
          </div>
        </div>

        {/* Card */}
        <div className="glass-card rounded-2xl p-8 border border-primary/20 shadow-[0_0_40px_rgba(236,91,19,0.08)]">
          <h2 className="text-xl font-bold text-white mb-1">Sign in</h2>
          <p className="text-sm text-slate-400 mb-8">
            Access your intelligence workspace.
          </p>

          <button
            onClick={() => signIn("google", { callbackUrl: "/" })}
            className="w-full flex items-center justify-center gap-3 py-3 px-4 rounded-xl bg-white text-gray-800 font-semibold text-sm hover:bg-gray-100 transition-all shadow-md"
          >
            {/* Google G icon */}
            <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
              <path
                d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z"
                fill="#4285F4"
              />
              <path
                d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"
                fill="#34A853"
              />
              <path
                d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"
                fill="#FBBC05"
              />
              <path
                d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"
                fill="#EA4335"
              />
            </svg>
            Continue with Google
          </button>
        </div>

        <p className="text-center text-xs text-slate-600 mt-6">
          By signing in you agree to our terms of service.
        </p>
      </div>
    </div>
  );
}
