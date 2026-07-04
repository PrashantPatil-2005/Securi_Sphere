"use client";

import { FormEvent, useState } from "react";
import { User, Mail, Shield } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader, Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { PasswordStrength } from "@/components/ui/PasswordStrength";
import { useToast } from "@/components/ui/Toast";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";
import { api } from "@/lib/api";
import type { UserMe } from "@/lib/hooks/useUser";

export default function ProfilePage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: user, isLoading, isError, refetch } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => api<UserMe>("/api/v1/auth/me"),
  });
  const [name, setName] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");

  const saveMutation = useMutation({
    mutationFn: (full_name: string) =>
      api<UserMe>("/api/v1/auth/me", { method: "PATCH", body: JSON.stringify({ full_name }) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      toast("success", "Profile updated");
    },
    onError: (err: Error) => toast("error", "Update failed", err.message),
  });

  const passwordMutation = useMutation({
    mutationFn: () =>
      api("/api/v1/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      }),
    onSuccess: () => {
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPasswordError("");
      toast("success", "Password updated");
    },
    onError: (err: Error) => setPasswordError(err.message),
  });

  function handlePasswordSubmit(e: FormEvent) {
    e.preventDefault();
    setPasswordError("");
    if (newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match");
      return;
    }
    if (currentPassword === newPassword) {
      setPasswordError("New password must differ from current password");
      return;
    }
    passwordMutation.mutate();
  }

  const displayName = name || user?.full_name || user?.email?.split("@")[0] || "User";

  if (isLoading) return <TableSkeleton rows={6} />;

  if (isError) {
    return (
      <div className="space-y-6 max-w-5xl">
        <PageHeader title="Profile" subtitle="Manage your account" />
        <QueryError onRetry={() => refetch()} />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <PageHeader title="Profile" subtitle="Manage your account" />
      <div className="grid lg:grid-cols-3 gap-6">
        <Panel title="Profile" className="lg:col-span-1">
          <div className="flex flex-col items-center text-center py-4">
            <div className="w-20 h-20 rounded-full bg-accent/20 flex items-center justify-center mb-4">
              <User className="w-8 h-8 text-accent" />
            </div>
            <h2 className="text-heading text-foreground">{displayName}</h2>
            <p className="text-body text-muted mt-1">{user?.email}</p>
            <span className="mt-3 inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-accent/10 text-accent text-caption normal-case capitalize">
              <Shield className="w-3 h-3" /> {user?.role?.name ?? "viewer"}
            </span>
          </div>
        </Panel>
        <div className="lg:col-span-2 space-y-6">
          <Panel title="Account details">
            <div className="space-y-4">
              <Input
                label="Display name"
                value={name || user?.full_name || ""}
                onChange={(e) => setName(e.target.value)}
              />
              <div className="flex items-center gap-3 p-3 rounded-lg bg-[var(--input-bg)] border border-border-subtle">
                <Mail className="w-4 h-4 text-muted shrink-0" />
                <div>
                  <p className="text-caption normal-case">Email</p>
                  <p className="text-body text-foreground">{user?.email}</p>
                </div>
              </div>
              <Button
                onClick={() => saveMutation.mutate(name || user?.full_name || "")}
                disabled={saveMutation.isPending}
              >
                Save changes
              </Button>
            </div>
          </Panel>

          <Panel title="Change password">
            <form onSubmit={handlePasswordSubmit} className="space-y-4">
              {passwordError && (
                <div className="px-4 py-3 rounded-lg border border-danger/30 bg-danger/10 text-body text-danger" role="alert">
                  {passwordError}
                </div>
              )}
              <Input
                label="Current password"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
              <div className="space-y-2">
                <Input
                  label="New password"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                  autoComplete="new-password"
                />
                <PasswordStrength password={newPassword} />
              </div>
              <Input
                label="Confirm new password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
                error={confirmPassword && newPassword !== confirmPassword ? "Passwords do not match" : undefined}
              />
              <Button type="submit" disabled={passwordMutation.isPending}>
                Update password
              </Button>
            </form>
          </Panel>
        </div>
      </div>
    </div>
  );
}
