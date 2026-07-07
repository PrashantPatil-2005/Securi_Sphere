"use client";

import Link from "next/link";
import { FormEvent, Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api, establishSession } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Checkbox } from "@/components/ui/Checkbox";
import { CardSkeleton } from "@/components/ui/Skeleton";

function AcceptInviteForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(!!token);
  const [preview, setPreview] = useState<{
    email: string;
    full_name: string | null;
    role: string;
  } | null>(null);
  const [ssoOnly, setSsoOnly] = useState(false);

  useEffect(() => {
    if (!token) {
      setError("Missing invite token");
      setPreviewLoading(false);
      return;
    }
    setPreviewLoading(true);
    api<{ email: string; full_name: string | null; role: string }>(
      `/api/v1/users/invites/preview?token=${encodeURIComponent(token)}`,
    )
      .then((data) => {
        setPreview(data);
        if (data.full_name) setFullName(data.full_name);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Invalid invite"))
      .finally(() => setPreviewLoading(false));
  }, [token]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setError("");
    setLoading(true);
    try {
      await api("/api/v1/users/invites/accept", {
        method: "POST",
        body: JSON.stringify({
          token,
          password: ssoOnly ? null : password,
          full_name: fullName || null,
        }),
      });
      try {
        await establishSession();
        router.push("/");
      } catch {
        router.push("/login");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not accept invite");
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <p className="text-sm text-muted">
        Invalid link. Ask your admin for a new invite or{" "}
        <Link href="/login" className="text-accent hover:underline">sign in</Link>.
      </p>
    );
  }

  if (previewLoading) {
    return (
      <div>
        <h1 className="text-display text-foreground mb-6">Accept invitation</h1>
        <div className="space-y-4">
          <CardSkeleton />
          <CardSkeleton />
          <div className="h-10 rounded-lg bg-card animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-display text-foreground mb-2">Accept invitation</h1>
      {preview && (
        <p className="text-body text-muted mb-6">
          Joining as <strong>{preview.email}</strong> ({preview.role})
        </p>
      )}
      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg border border-danger/30 bg-danger/10 text-danger text-sm" role="alert">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input label="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
        <Checkbox
          label="I will sign in with SSO (skip password)"
          checked={ssoOnly}
          onChange={(e) => setSsoOnly(e.target.checked)}
        />
        {!ssoOnly && (
          <Input
            label="Password"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
          />
        )}
        <Button type="submit" loading={loading} className="w-full" size="lg" disabled={!preview}>
          Create account
        </Button>
      </form>
      <p className="mt-6 text-sm text-muted text-center">
        Already have an account? <Link href="/login" className="text-accent hover:underline">Sign in</Link>
      </p>
    </div>
  );
}

export default function AcceptInvitePage() {
  return (
    <Suspense fallback={<div className="animate-pulse h-48 bg-card rounded-lg" />}>
      <AcceptInviteForm />
    </Suspense>
  );
}
