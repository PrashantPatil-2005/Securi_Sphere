"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { api, setTokens } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const tokens = await api<{ access_token: string; refresh_token: string }>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }, false);
      setTokens(tokens);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={handleSubmit} className="w-full max-w-md p-8 bg-[var(--card)] rounded-lg border border-[var(--border)]">
        <h1 className="text-2xl font-bold mb-2">Sign in</h1>
        <p className="text-gray-500 text-sm mb-6">Mini SIEM Security Dashboard</p>
        {error && <p className="text-red-400 text-sm mb-4">{error}</p>}
        <label className="block text-sm mb-1">Email</label>
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
          className="w-full mb-4 px-3 py-2 bg-[var(--background)] border border-[var(--border)] rounded" />
        <label className="block text-sm mb-1">Password</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
          className="w-full mb-6 px-3 py-2 bg-[var(--background)] border border-[var(--border)] rounded" />
        <button type="submit" className="w-full py-2 bg-blue-600 hover:bg-blue-700 rounded font-medium">Login</button>
        <div className="mt-4 text-sm text-gray-500 flex justify-between">
          <Link href="/register" className="text-blue-400 hover:underline">Register</Link>
          <Link href="/forgot-password" className="text-blue-400 hover:underline">Forgot password?</Link>
        </div>
      </form>
    </div>
  );
}
