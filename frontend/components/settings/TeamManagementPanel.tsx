"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Users } from "lucide-react";
import { api } from "@/lib/api";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";
import { useToast } from "@/components/ui/Toast";

interface AdminUser {
  id: string;
  email: string;
  full_name: string | null;
  role: { name: string };
  is_active: boolean;
  last_login: string | null;
  sso_only: boolean;
  oidc_linked: boolean;
}

interface PendingInvite {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  expires_at: string;
  invite_url?: string | null;
}

const ROLES = ["admin", "analyst", "viewer"] as const;

export function TeamManagementPanel() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<(typeof ROLES)[number]>("analyst");
  const [ssoOnly, setSsoOnly] = useState(true);
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"provision" | "invite">("invite");

  const { data: users = [], isLoading, isError, refetch } = useQuery({
    queryKey: ["admin", "users"],
    queryFn: () => api<AdminUser[]>("/api/v1/users"),
    staleTime: 30_000,
  });

  const { data: invites = [], refetch: refetchInvites } = useQuery({
    queryKey: ["admin", "user-invites"],
    queryFn: () => api<PendingInvite[]>("/api/v1/users/invites"),
    staleTime: 30_000,
  });

  const provisionMutation = useMutation({
    mutationFn: () =>
      api("/api/v1/users", {
        method: "POST",
        body: JSON.stringify({
          email,
          role,
          full_name: fullName || null,
          sso_only: ssoOnly,
          password: ssoOnly ? null : password,
        }),
      }),
    onSuccess: () => {
      toast("success", "User provisioned");
      setEmail("");
      setFullName("");
      setPassword("");
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
    onError: (e: Error) => toast("error", "Provision failed", e.message),
  });

  const inviteMutation = useMutation({
    mutationFn: () =>
      api<PendingInvite>("/api/v1/users/invites", {
        method: "POST",
        body: JSON.stringify({ email, role, full_name: fullName || null }),
      }),
    onSuccess: (data) => {
      toast("success", "Invite sent", data.invite_url ? "Link copied to invite list" : undefined);
      setEmail("");
      setFullName("");
      queryClient.invalidateQueries({ queryKey: ["admin", "user-invites"] });
    },
    onError: (e: Error) => toast("error", "Invite failed", e.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, ...body }: { id: string; role?: string; is_active?: boolean }) =>
      api(`/api/v1/users/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "users"] }),
    onError: (e: Error) => toast("error", "Update failed", e.message),
  });

  const revokeMutation = useMutation({
    mutationFn: (id: string) => api(`/api/v1/users/invites/${id}`, { method: "DELETE" }),
    onSuccess: () => refetchInvites(),
    onError: (e: Error) => toast("error", "Revoke failed", e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api(`/api/v1/users/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      toast("success", "User removed");
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
    onError: (e: Error) => toast("error", "Remove failed", e.message),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (mode === "invite") inviteMutation.mutate();
    else provisionMutation.mutate();
  }

  if (isError) return <QueryError onRetry={() => refetch()} />;

  return (
    <div className="space-y-6">
      <Panel title="Add team member" subtitle="Pre-provision SSO users or send email invites">
        <div className="flex flex-wrap gap-2 mb-4">
          {(["invite", "provision"] as const).map((m) => (
            <Button
              key={m}
              type="button"
              variant="ghost"
              size="sm"
              className={mode === m ? "bg-accent/10 text-accent" : ""}
              onClick={() => setMode(m)}
            >
              {m === "invite" ? "Email invite" : "Direct provision"}
            </Button>
          ))}
        </div>
        <form onSubmit={handleSubmit} className="grid gap-3 sm:grid-cols-2">
          <Input label="Email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          <Input label="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
          <Select label="Role" value={role} onChange={(e) => setRole(e.target.value as (typeof ROLES)[number])}>
            {ROLES.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </Select>
          {mode === "provision" && (
            <>
              <label className="flex items-center gap-2 text-sm text-muted sm:col-span-2">
                <input type="checkbox" checked={ssoOnly} onChange={(e) => setSsoOnly(e.target.checked)} />
                SSO only (no local password — user signs in via identity provider)
              </label>
              {!ssoOnly && (
                <Input
                  label="Temporary password"
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="sm:col-span-2"
                />
              )}
            </>
          )}
          <div className="sm:col-span-2">
            <Button
              type="submit"
              loading={inviteMutation.isPending || provisionMutation.isPending}
            >
              {mode === "invite" ? "Send invite" : "Provision user"}
            </Button>
          </div>
        </form>
      </Panel>

      {invites.length > 0 && (
        <Panel title="Pending invites">
          <div className="space-y-2">
            {invites.map((inv) => (
              <div key={inv.id} className="flex flex-wrap items-center justify-between gap-2 p-3 rounded border border-border-subtle">
                <div>
                  <p className="font-medium text-sm">{inv.email}</p>
                  <p className="text-xs text-muted capitalize">{inv.role} · expires {new Date(inv.expires_at).toLocaleDateString()}</p>
                  {inv.invite_url && (
                    <p className="text-[10px] text-muted font-mono mt-1 break-all">{inv.invite_url}</p>
                  )}
                </div>
                <Button type="button" variant="ghost" size="sm" onClick={() => revokeMutation.mutate(inv.id)}>
                  Revoke
                </Button>
              </div>
            ))}
          </div>
        </Panel>
      )}

      <Panel title="Team members">
        {isLoading ? (
          <TableSkeleton rows={4} />
        ) : users.length === 0 ? (
          <p className="text-sm text-muted flex items-center gap-2">
            <Users className="w-4 h-4" /> No users yet.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted border-b border-border-subtle">
                  <th className="py-2 pr-3">Email</th>
                  <th className="py-2 pr-3">Role</th>
                  <th className="py-2 pr-3">Auth</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-border-subtle/50">
                    <td className="py-2 pr-3">
                      <p className="font-medium">{u.email}</p>
                      {u.full_name && <p className="text-xs text-muted">{u.full_name}</p>}
                    </td>
                    <td className="py-2 pr-3 capitalize">{u.role.name}</td>
                    <td className="py-2 pr-3 text-xs text-muted">
                      {u.oidc_linked ? "SSO linked" : u.sso_only ? "SSO ready" : "Password"}
                    </td>
                    <td className="py-2 pr-3 capitalize">{u.is_active ? "active" : "disabled"}</td>
                    <td className="py-2">
                      <div className="flex flex-wrap gap-1">
                        {ROLES.filter((r) => r !== u.role.name).map((r) => (
                          <Button
                            key={r}
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="text-xs capitalize"
                            disabled={updateMutation.isPending}
                            onClick={() => updateMutation.mutate({ id: u.id, role: r })}
                          >
                            → {r}
                          </Button>
                        ))}
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="text-xs"
                          disabled={updateMutation.isPending}
                          onClick={() => updateMutation.mutate({ id: u.id, is_active: !u.is_active })}
                        >
                          {u.is_active ? "Disable" : "Enable"}
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="text-xs text-danger"
                          disabled={deleteMutation.isPending}
                          onClick={() => {
                            if (confirm(`Remove ${u.email} from the team?`)) deleteMutation.mutate(u.id);
                          }}
                        >
                          Remove
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
