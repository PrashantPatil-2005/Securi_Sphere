"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { motion } from "framer-motion";
import { ArrowLeft, CheckCircle } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { PasswordStrength } from "@/components/ui/PasswordStrength";

function ResetForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!token) { setError("Invalid or missing reset token"); return; }
    if (password !== confirm) { setError("Passwords do not match"); return; }
    if (password.length < 8) { setError("Password must be at least 8 characters"); return; }
    setLoading(true);
    try {
      await api("/api/v1/auth/reset-password", { method: "POST", body: JSON.stringify({ token, new_password: password }) }, false);
      setDone(true);
      setTimeout(() => router.push("/login"), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed");
    } finally {
      setLoading(false);
    }
  }

  if (done) {
    return (
      <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} className="text-center">
        <div className="w-14 h-14 rounded-full bg-success/10 flex items-center justify-center mx-auto mb-4">
          <CheckCircle className="w-6 h-6 text-success" />
        </div>
        <h1 className="text-heading text-foreground">Password updated</h1>
        <p className="text-body text-muted mt-2">Redirecting to sign in…</p>
      </motion.div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
      <Link href="/login" className="inline-flex items-center gap-2 text-body text-muted hover:text-foreground mb-6 transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to sign in
      </Link>
      <div className="mb-8">
        <h1 className="text-display text-foreground">New password</h1>
        <p className="text-body text-muted mt-2">Choose a strong password for your account</p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-5">
        {error && <div className="px-4 py-3 rounded-lg border border-danger/30 bg-danger/10 text-body text-danger" role="alert">{error}</div>}
        {!token && <div className="px-4 py-3 rounded-lg border border-warning/30 bg-warning/10 text-body text-warning" role="alert">Missing reset token. Use the link from your email.</div>}
        <div className="space-y-2">
          <Input label="New password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoComplete="new-password" />
          <PasswordStrength password={password} />
        </div>
        <Input label="Confirm password" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required autoComplete="new-password" error={confirm && password !== confirm ? "Passwords do not match" : undefined} />
        <Button type="submit" loading={loading} className="w-full" size="lg" disabled={!token}>Update password</Button>
      </form>
    </motion.div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="animate-pulse h-64 bg-card rounded-lg" />}>
      <ResetForm />
    </Suspense>
  );
}
