import { describe, it, expect } from "vitest";
import {
  firedRuleTypes,
  groupByStage,
  severityRank,
  stageForEvent,
  stageForRule,
} from "@/lib/attackChain";
import type { SimulationAlert } from "@/lib/types/simulation";

describe("attackChain stages", () => {
  it("maps detection rules onto kill-chain stages in order", () => {
    expect(stageForRule("firewall_block").rank).toBeLessThan(stageForRule("failed_logins").rank);
    expect(stageForRule("failed_logins").rank).toBeLessThan(
      stageForRule("ssh_success_after_failures").rank,
    );
    expect(stageForRule("ssh_success_after_failures").rank).toBeLessThan(
      stageForRule("privilege_escalation").rank,
    );
    expect(stageForRule("privilege_escalation").rank).toBeLessThan(stageForRule("high_cpu").rank);
  });

  it("falls back safely for unknown types", () => {
    expect(stageForRule("nope")).toEqual(stageForRule(null));
    expect(stageForEvent("nope")).toEqual(stageForEvent(undefined));
  });

  it("ranks severities for ordering inside a stage", () => {
    expect(severityRank("critical")).toBeGreaterThan(severityRank("high"));
    expect(severityRank("bogus")).toBe(0);
  });
});

describe("groupByStage", () => {
  it("orders stages by rank and severities within each stage", () => {
    const items = [
      { stage: "Impact", severity: "low" },
      { stage: "Recon", severity: "high" },
      { stage: "Impact", severity: "critical" },
      { stage: "Brute force", severity: "medium" },
    ];
    const groups = groupByStage(
      items,
      (i) => ({ label: i.stage, rank: ["Recon", "Brute force", "Impact"].indexOf(i.stage) + 1 }),
      (i) => i.severity,
    );

    expect(groups.map((g) => g.stage.label)).toEqual(["Recon", "Brute force", "Impact"]);
    expect(groups[2].items.map((i) => i.severity)).toEqual(["critical", "low"]);
  });
});

describe("firedRuleTypes", () => {
  it("returns distinct rule types in kill-chain order", () => {
    const alert = (rule_type: string): SimulationAlert => ({
      id: rule_type,
      title: rule_type,
      severity: "high",
      rule_type,
    });

    expect(
      firedRuleTypes([
        alert("high_cpu"),
        alert("failed_logins"),
        alert("failed_logins"),
        alert("privilege_escalation"),
        alert("ssh_success_after_failures"),
      ]),
    ).toEqual([
      "failed_logins",
      "ssh_success_after_failures",
      "privilege_escalation",
      "high_cpu",
    ]);
  });
});
