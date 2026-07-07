"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api, establishSession } from "@/lib/api";
import { PRODUCT_NAME } from "@/lib/brand";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { PasswordStrength } from "@/components/ui/PasswordStrength";
import { CardSkeleton } from "@/components/ui/Skeleton";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [settingsLoading, setSettingsLoading] = useState(true);
  const [allowRegistration, setAllowRegistration] = useState(true);

  useEffect(() => {
    fetch("/api/v1/settings/public")
      .then((r) => (r.ok ? r.json() : null))
      .then((cfg) => {
        if (cfg && typeof cfg.allow_registration === "boolean") {
          setAllowRegistration(cfg.allow_registration);
        }
      })
      .catch(() => {})
      .finally(() => setSettingsLoading(false));
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!allowRegistration) {
      setError("Registration is disabled. Contact your administrator.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setLoading(true);
    try {
      await api("/api/v1/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }, false);
      await api("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }, false);
      await establishSession();
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  if (settingsLoading) {
    return (
      <div className="space-y-4">
        <div className="h-10 w-48 rounded-lg bg-card animate-pulse" />
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  if (!allowRegistration) {
    return (
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
        <div className="mb-8">
          <h1 className="text-display text-foreground">Registration closed</h1>
          <p className="text-body text-muted mt-2">
            Self-service sign-up is disabled on this deployment. Ask an administrator for an invite or sign in with an existing account.
          </p>
        </div>
        <Link href="/login" className="btn-primary inline-flex">
          Go to sign in
        </Link>
      </motion.div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
      <div className="mb-8">
        <h1 className="text-display text-foreground">Create account</h1>
        <p className="text-body text-muted mt-2">Set up your {PRODUCT_NAME} workspace</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {error && (
          <div className="px-4 py-3 rounded-lg border border-danger/30 bg-danger/10 text-body text-danger" role="alert">
            {error}
          </div>
        )}

        <Input label="Email address" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" required autoComplete="email" />

        <div className="space-y-2">
          <Input label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoComplete="new-password" />
          <PasswordStrength password={password} />
        </div>

        <Input label="Confirm password" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required autoComplete="new-password" error={confirm && password !== confirm ? "Passwords do not match" : undefined} />

        <Button type="submit" loading={loading} className="w-full" size="lg">Create account</Button>
      </form>

      <p className="mt-6 text-body text-muted text-center">
        Already have an account?{" "}
        <Link href="/login" className="text-accent hover:underline font-medium">Sign in</Link>
      </p>
    </motion.div>
  );
}
