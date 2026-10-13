import type { SimulationAlert } from "@/lib/types/simulation";

/**
 * Shared kill-chain model for the Attack Lab.
 *
 * Both the live banner (which narrates an in-flight attack from injected
 * event types) and the post-run results (which explains which detections
 * actually fired) order their content by the same stages, so the story the
 * analyst watches unfold matches the story the report tells afterwards.
 */
export interface AttackStage {
  label: string;
  rank: number;
}

export const ATTACK_STAGES = [
  { label: "Recon", rank: 1 },
  { label: "Brute force", rank: 2 },
  { label: "Initial access", rank: 3 },
  { label: "Privilege escalation", rank: 4 },
  { label: "Defense evasion", rank: 5 },
  { label: "Persistence", rank: 5 },
  { label: "Impact", rank: 6 },
] as const;

const FALLBACK: AttackStage = { label: "Injection", rank: 1 };

/** Injected event type → kill-chain stage. */
export const EVENT_STAGE: Record<string, AttackStage> = {
  network_flow: { label: "Recon", rank: 1 },
  firewall_block: { label: "Recon", rank: 1 },
  port_scan: { label: "Recon", rank: 1 },
  ssh_login_failure: { label: "Brute force", rank: 2 },
  ssh_login_success: { label: "Initial access", rank: 3 },
  root_login: { label: "Initial access", rank: 3 },
  sudo_usage: { label: "Privilege escalation", rank: 4 },
  agent_disconnect: { label: "Defense evasion", rank: 5 },
  file_integrity: { label: "Persistence", rank: 5 },
  service_stop: { label: "Impact", rank: 6 },
  service_failure: { label: "Impact", rank: 6 },
  high_cpu: { label: "Impact", rank: 6 },
  high_memory: { label: "Impact", rank: 6 },
  high_disk: { label: "Impact", rank: 6 },
};

/** Detection rule type → kill-chain stage. */
export const RULE_STAGE: Record<string, AttackStage> = {
  network_anomaly: { label: "Recon", rank: 1 },
  firewall_block: { label: "Recon", rank: 1 },
  port_scan: { label: "Recon", rank: 1 },
  failed_logins: { label: "Brute force", rank: 2 },
  brute_force: { label: "Brute force", rank: 2 },
  ssh_success_after_failures: { label: "Initial access", rank: 3 },
  root_login: { label: "Initial access", rank: 3 },
  privilege_escalation: { label: "Privilege escalation", rank: 4 },
  agent_offline: { label: "Defense evasion", rank: 5 },
  file_integrity: { label: "Persistence", rank: 5 },
  service_failure: { label: "Impact", rank: 6 },
  service_stop: { label: "Impact", rank: 6 },
  high_cpu: { label: "Impact", rank: 6 },
  high_memory: { label: "Impact", rank: 6 },
  high_disk: { label: "Impact", rank: 6 },
};

export function stageForEvent(eventType?: string | null): AttackStage {
  return (eventType && EVENT_STAGE[eventType]) || FALLBACK;
}

export function stageForRule(ruleType?: string | null): AttackStage {
  return (ruleType && RULE_STAGE[ruleType]) || FALLBACK;
}

export const SEVERITY_RANK: Record<string, number> = {
  critical: 5,
  high: 4,
  medium: 3,
  low: 2,
  info: 1,
};

export function severityRank(severity?: string | null): number {
  return SEVERITY_RANK[(severity || "").toLowerCase()] ?? 0;
}

export interface StageGroup<T> {
  stage: AttackStage;
  items: T[];
}

/**
 * Group items into kill-chain stages, ordered by rank. Within a stage the
 * most severe items come first, which is how an analyst would read them.
 */
export function groupByStage<T>(
  items: T[],
  pickStage: (item: T) => AttackStage,
  pickSeverity: (item: T) => string | null | undefined = () => null,
): StageGroup<T>[] {
  const byRank = new Map<number, StageGroup<T>>();

  for (const item of items) {
    const stage = pickStage(item);
    let group = byRank.get(stage.rank);
    if (!group) {
      group = { stage, items: [] };
      byRank.set(stage.rank, group);
    }
    group.items.push(item);
  }

  return Array.from(byRank.values())
    .sort((a, b) => a.stage.rank - b.stage.rank)
    .map((group) => ({
      ...group,
      items: [...group.items].sort(
        (x, y) => severityRank(pickSeverity(y)) - severityRank(pickSeverity(x)),
      ),
    }));
}

/** Distinct alert rule types that fired, in kill-chain order. */
export function firedRuleTypes(alerts: SimulationAlert[]): string[] {
  const seen = new Set<string>();
  for (const alert of alerts) {
    if (alert.rule_type) seen.add(alert.rule_type);
  }
  return Array.from(seen).sort(
    (a, b) => stageForRule(a).rank - stageForRule(b).rank || a.localeCompare(b),
  );
}
