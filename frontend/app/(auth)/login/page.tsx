"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api, clearTokens, establishSession } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

interface LoginResponse {
  access_token?: string;
  refresh_token?: string;
  mfa_required?: boolean;
  mfa_token?: string;
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") || "/";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [allowRegistration, setAllowRegistration] = useState(true);
  const [oidcEnabled, setOidcEnabled] = useState(false);
  const [oidcLabel, setOidcLabel] = useState("SSO");

  useEffect(() => {
    fetch("/api/v1/settings/public")
      .then((r) => (r.ok ? r.json() : null))
      .then((cfg) => {
        if (!cfg) return;
        if (typeof cfg.allow_registration === "boolean") {
          setAllowRegistration(cfg.allow_registration);
        }
        if (typeof cfg.oidc_enabled === "boolean") {
          setOidcEnabled(cfg.oidc_enabled);
        }
        if (typeof cfg.oidc_provider_label === "string" && cfg.oidc_provider_label) {
          setOidcLabel(cfg.oidc_provider_label);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const err = searchParams.get("error");
    if (err) setError(decodeURIComponent(err));
  }, [searchParams]);

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
      const res = await api<LoginResponse>(
        "/api/v1/auth/login",
        { method: "POST", body: JSON.stringify({ email, password }) },
        false,
      );
      if (res.mfa_required && res.mfa_token) {
        setMfaToken(res.mfa_token);
        return;
      }
      await establishSession();
      router.push(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid email or password");
    } finally {
      setLoading(false);
    }
  }

  async function handleMfaSubmit(e: FormEvent) {
    e.preventDefault();
    if (!mfaToken) return;
    setError("");
    setLoading(true);
    try {
      await api("/api/v1/auth/mfa/verify", {
        method: "POST",
        body: JSON.stringify({ mfa_token: mfaToken, code: mfaCode.trim() }),
      }, false);
      await establishSession();
      router.push(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid authentication code");
    } finally {
      setLoading(false);
    }
  }

  if (mfaToken) {
    return (
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
        <div className="mb-8">
          <h1 className="text-display text-foreground">Two-factor authentication</h1>
          <p className="text-body text-muted mt-2">Enter the code from your authenticator app</p>
        </div>
        <form onSubmit={handleMfaSubmit} className="space-y-5">
          {error && (
            <div className="px-4 py-3 rounded-lg border border-danger/30 bg-danger/10 text-body text-danger" role="alert">
              {error}
            </div>
          )}
          <Input
            label="Authentication code"
            value={mfaCode}
            onChange={(e) => setMfaCode(e.target.value)}
            placeholder="000000"
            inputMode="numeric"
            autoComplete="one-time-code"
            required
          />
          <Button type="submit" loading={loading} className="w-full" size="lg">
            Verify
          </Button>
          <Button
            type="button"
            variant="ghost"
            className="w-full"
            onClick={() => {
              setMfaToken(null);
              setMfaCode("");
              setError("");
            }}
          >
            Back to sign in
          </Button>
        </form>
      </motion.div>
    );
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

        {oidcEnabled && (
          <>
            <div className="relative my-2">
              <div className="absolute inset-0 flex items-center" aria-hidden>
                <div className="w-full border-t border-border-subtle" />
              </div>
              <p className="relative flex justify-center text-xs text-muted">
                <span className="bg-card px-2">or</span>
              </p>
            </div>
            <Button
              type="button"
              variant="ghost"
              className="w-full"
              size="lg"
              onClick={() => {
                window.location.href = `/api/v1/auth/oidc/login?next=${encodeURIComponent(next)}`;
              }}
            >
              Sign in with {oidcLabel}
            </Button>
          </>
        )}
      </form>

      {allowRegistration && (
        <p className="mt-6 text-body text-muted text-center">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="text-accent hover:underline font-medium">
            Create account
          </Link>
        </p>
      )}
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
