"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api, clearTokens, establishSession } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") || "/";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api("/api/v1/auth/me")
      .then(() => establishSession().then(() => router.replace(next)))
      .catch(() => clearTokens());
  }, [router, next]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api<{ access_token: string; refresh_token: string }>(
        "/api/v1/auth/login",
        { method: "POST", body: JSON.stringify({ email, password }) },
        false,
      );
      await establishSession();
      router.push(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid email or password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <div className="mb-8">
        <h1 className="text-display text-foreground">Sign in</h1>
        <p className="text-body text-muted mt-2">Access your security operations center</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {error && (
          <div className="px-4 py-3 rounded-lg border border-danger/30 bg-danger/10 text-body text-danger" role="alert">
            {error}
          </div>
        )}

        <Input
          label="Email address"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@company.com"
          required
          autoComplete="email"
        />

        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label htmlFor="password" className="text-body font-medium text-foreground">Password</label>
            <Link href="/forgot-password" className="text-caption normal-case text-accent hover:underline">
              Forgot password?
            </Link>
          </div>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            className="input-siem"
          />
        </div>

        <Button type="submit" loading={loading} className="w-full" size="lg">
          Sign in
        </Button>
      </form>

      <p className="mt-6 text-body text-muted text-center">
        Don&apos;t have an account?{" "}
        <Link href="/register" className="text-accent hover:underline font-medium">
          Create account
        </Link>
      </p>
    </motion.div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="animate-pulse h-64 bg-card rounded-lg" />}>
      <LoginForm />
    </Suspense>
  );
}
