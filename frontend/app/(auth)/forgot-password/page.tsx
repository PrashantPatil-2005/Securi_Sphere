"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { motion } from "framer-motion";
import { ArrowLeft, Mail } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api("/api/v1/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) }, false);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  if (sent) {
    return (
      <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} className="text-center">
        <div className="w-14 h-14 rounded-full bg-success/10 flex items-center justify-center mx-auto mb-4">
          <Mail className="w-6 h-6 text-success" />
        </div>
        <h1 className="text-heading text-foreground">Check your email</h1>
        <p className="text-body text-muted mt-2">If an account exists for {email}, you will receive a reset link shortly.</p>
        <Link href="/login" className="inline-flex items-center gap-2 mt-6 text-body text-accent hover:underline">
          <ArrowLeft className="w-4 h-4" /> Back to sign in
        </Link>
      </motion.div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
      <Link href="/login" className="inline-flex items-center gap-2 text-body text-muted hover:text-foreground mb-6 transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to sign in
      </Link>
      <div className="mb-8">
        <h1 className="text-display text-foreground">Reset password</h1>
        <p className="text-body text-muted mt-2">Enter your email and we&apos;ll send a reset link</p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-5">
        {error && <div className="px-4 py-3 rounded-lg border border-danger/30 bg-danger/10 text-body text-danger" role="alert">{error}</div>}
        <Input label="Email address" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" required autoComplete="email" />
        <Button type="submit" loading={loading} className="w-full" size="lg">Send reset link</Button>
      </form>
    </motion.div>
  );
}
