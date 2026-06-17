"use client";

import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { api } from "@/lib/api";

function ResetForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token") || "";
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      await api("/api/v1/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, new_password: password }),
      }, false);
      router.push("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-md p-8 bg-[var(--card)] rounded-lg border border-[var(--border)]">
      <h1 className="text-2xl font-bold mb-6">Set new password</h1>
      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}
      <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8}
        placeholder="New password" className="w-full mb-6 px-3 py-2 bg-[var(--background)] border border-[var(--border)] rounded" />
      <button type="submit" className="w-full py-2 bg-blue-600 hover:bg-blue-700 rounded">Reset password</button>
      <p className="mt-4 text-sm"><Link href="/login" className="text-blue-400 hover:underline">Back to login</Link></p>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <Suspense><ResetForm /></Suspense>
    </div>
  );
}
