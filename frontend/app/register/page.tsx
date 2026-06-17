"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api("/api/v1/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }, false);
      setSuccess(true);
      setTimeout(() => router.push("/login"), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={handleSubmit} className="w-full max-w-md p-8 bg-[var(--card)] rounded-lg border border-[var(--border)]">
        <h1 className="text-2xl font-bold mb-6">Create account</h1>
        {error && <p className="text-red-400 text-sm mb-4">{error}</p>}
        {success && <p className="text-green-400 text-sm mb-4">Account created! Redirecting to login...</p>}
        <label className="block text-sm mb-1">Email</label>
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
          className="w-full mb-4 px-3 py-2 bg-[var(--background)] border border-[var(--border)] rounded" />
        <label className="block text-sm mb-1">Password (min 8 chars)</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8}
          className="w-full mb-6 px-3 py-2 bg-[var(--background)] border border-[var(--border)] rounded" />
        <button type="submit" className="w-full py-2 bg-blue-600 hover:bg-blue-700 rounded font-medium">Register</button>
        <p className="mt-4 text-sm text-gray-500"><Link href="/login" className="text-blue-400 hover:underline">Back to login</Link></p>
      </form>
    </div>
  );
}
