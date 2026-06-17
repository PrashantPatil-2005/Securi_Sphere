"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await api("/api/v1/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) }, false);
    setSent(true);
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={handleSubmit} className="w-full max-w-md p-8 bg-[var(--card)] rounded-lg border border-[var(--border)]">
        <h1 className="text-2xl font-bold mb-6">Reset password</h1>
        {sent ? (
          <p className="text-green-400">If the email exists, a reset link has been sent. Check backend logs in dev mode.</p>
        ) : (
          <>
            <label className="block text-sm mb-1">Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
              className="w-full mb-6 px-3 py-2 bg-[var(--background)] border border-[var(--border)] rounded" />
            <button type="submit" className="w-full py-2 bg-blue-600 hover:bg-blue-700 rounded">Send reset link</button>
          </>
        )}
        <p className="mt-4 text-sm"><Link href="/login" className="text-blue-400 hover:underline">Back to login</Link></p>
      </form>
    </div>
  );
}
