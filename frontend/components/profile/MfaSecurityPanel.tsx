"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { QueryError } from "@/components/ui/QueryError";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";

interface MfaStatus {
  enabled: boolean;
  backup_codes_remaining: number;
}

interface SetupData {
  secret: string;
  otpauth_url: string;
}

export function MfaSecurityPanel() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [setup, setSetup] = useState<SetupData | null>(null);
  const [enableCode, setEnableCode] = useState("");
  const [backupCodes, setBackupCodes] = useState<string[] | null>(null);
  const [disableCode, setDisableCode] = useState("");
  const [disablePassword, setDisablePassword] = useState("");

  const { data: status, isLoading, isError, refetch } = useQuery({
    queryKey: ["mfa-status"],
    queryFn: () => api<MfaStatus>("/api/v1/auth/mfa/status"),
  });

  const setupMutation = useMutation({
    mutationFn: () => api<SetupData>("/api/v1/auth/mfa/setup", { method: "POST" }),
    onSuccess: (data) => {
      setSetup(data);
      setBackupCodes(null);
      toast("success", "Scan the secret in your authenticator app");
    },
    onError: (e: Error) => toast("error", "Setup failed", e.message),
  });

  const enableMutation = useMutation({
    mutationFn: (code: string) =>
      api<{ enabled: boolean; backup_codes: string[] }>("/api/v1/auth/mfa/enable", {
        method: "POST",
        body: JSON.stringify({ code }),
      }),
    onSuccess: (data) => {
      setBackupCodes(data.backup_codes);
      setSetup(null);
      setEnableCode("");
      queryClient.invalidateQueries({ queryKey: ["mfa-status"] });
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      toast("success", "Two-factor authentication enabled");
    },
    onError: (e: Error) => toast("error", "Enable failed", e.message),
  });

  const disableMutation = useMutation({
    mutationFn: () =>
      api("/api/v1/auth/mfa/disable", {
        method: "POST",
        body: JSON.stringify({ code: disableCode, password: disablePassword || null }),
      }),
    onSuccess: () => {
      setDisableCode("");
      setDisablePassword("");
      setSetup(null);
      setBackupCodes(null);
      queryClient.invalidateQueries({ queryKey: ["mfa-status"] });
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      toast("success", "Two-factor authentication disabled");
    },
    onError: (e: Error) => toast("error", "Disable failed", e.message),
  });

  function handleEnable(e: FormEvent) {
    e.preventDefault();
    if (!enableCode.trim()) return;
    enableMutation.mutate(enableCode.trim());
  }

  if (isLoading) return <TableSkeleton rows={4} />;
  if (isError) return <QueryError onRetry={() => refetch()} />;

  return (
    <Panel title="Two-factor authentication (TOTP)">
      <div className="flex items-start gap-3 mb-4">
        <ShieldCheck className="w-5 h-5 text-accent shrink-0 mt-0.5" />
        <p className="text-sm text-muted">
          Protect your account with a 6-digit code from Google Authenticator, Authy, or any TOTP app.
        </p>
      </div>

      {status?.enabled ? (
        <div className="space-y-4">
          <p className="text-sm text-success">MFA is enabled on your account.</p>
          <p className="text-xs text-muted">
            Backup codes remaining: {status.backup_codes_remaining}
          </p>
          <div className="space-y-2 max-w-sm">
            <Input
              label="Authentication code"
              value={disableCode}
              onChange={(e) => setDisableCode(e.target.value)}
              placeholder="6-digit code or backup code"
              autoComplete="one-time-code"
            />
            <Input
              label="Password (if you use password login)"
              type="password"
              value={disablePassword}
              onChange={(e) => setDisablePassword(e.target.value)}
              autoComplete="current-password"
            />
            <Button
              type="button"
              variant="danger"
              loading={disableMutation.isPending}
              disabled={!disableCode}
              onClick={() => disableMutation.mutate()}
            >
              Disable MFA
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {!setup && (
            <Button type="button" onClick={() => setupMutation.mutate()} loading={setupMutation.isPending}>
              Set up authenticator
            </Button>
          )}
          {setup && (
            <div className="space-y-3 rounded-lg border border-border-subtle p-4">
              <p className="text-sm font-medium">1. Add this secret to your authenticator app</p>
              <code className="block text-xs font-mono break-all bg-glass/50 p-2 rounded">{setup.secret}</code>
              <p className="text-xs text-muted break-all">{setup.otpauth_url}</p>
              <form onSubmit={handleEnable} className="space-y-2 max-w-xs">
                <p className="text-sm font-medium">2. Enter the 6-digit code to confirm</p>
                <Input
                  label="Verification code"
                  value={enableCode}
                  onChange={(e) => setEnableCode(e.target.value)}
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="000000"
                />
                <Button type="submit" loading={enableMutation.isPending} disabled={enableCode.length < 6}>
                  Enable MFA
                </Button>
              </form>
            </div>
          )}
        </div>
      )}

      {backupCodes && backupCodes.length > 0 && (
        <div className="mt-4 p-4 rounded-lg border border-warning/30 bg-warning/5">
          <p className="text-sm font-medium text-warning mb-2">Save these backup codes</p>
          <p className="text-xs text-muted mb-3">Each code works once if you lose your authenticator.</p>
          <div className="grid grid-cols-2 gap-2 font-mono text-sm">
            {backupCodes.map((c) => (
              <span key={c}>{c}</span>
            ))}
          </div>
        </div>
      )}
    </Panel>
  );
}
