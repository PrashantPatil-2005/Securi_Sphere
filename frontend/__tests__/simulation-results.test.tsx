import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { SimulationResults } from "@/components/attack-lab/SimulationResults";
import type { SimulationAlert, SimulationRunResult } from "@/lib/types/simulation";

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children?: ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/components/attack-lab/GuidedInvestigationBar", () => ({
  GuidedInvestigationBar: () => <div data-testid="guided-bar" />,
}));

vi.mock("@/components/design-system/AnimatedNumber", () => ({
  AnimatedNumber: ({ value }: { value: number }) => <span>{value}</span>,
}));

function alert(partial: Partial<SimulationAlert> & { id: string }): SimulationAlert {
  return { title: partial.id, severity: "high", ...partial };
}

function result(partial: Partial<SimulationRunResult> = {}): SimulationRunResult {
  return {
    message: "Simulation brute_force_only completed",
    events: 11,
    run_id: "run-1",
    host_id: "host-1",
    scenario: "brute_force_only",
    name: "Brute Force Only",
    event_ids: ["e1", "e2"],
    alert_ids: ["a1", "a2", "a3"],
    timeline_ids: ["t1"],
    offense_ids: ["o1"],
    incident_ids: [],
    alerts: [],
    expected_alerts: [],
    ...partial,
  };
}

describe("SimulationResults", () => {
  it("renders the animated headline stats", () => {
    render(<SimulationResults result={result()} onRunAgain={() => {}} />);
    expect(screen.getByText("Simulation complete")).toBeInTheDocument();
    expect(screen.getByText("11")).toBeInTheDocument();
    expect(screen.getByText("Events")).toBeInTheDocument();
    expect(screen.getByText("Offenses")).toBeInTheDocument();
  });

  it("groups fired alerts into a kill chain ordered by stage rank", () => {
    render(
      <SimulationResults
        result={result({
          alerts: [
            alert({ id: "cpu", rule_type: "high_cpu", severity: "medium" }),
            alert({ id: "sudo", rule_type: "privilege_escalation", severity: "critical" }),
            alert({ id: "brute", rule_type: "failed_logins", severity: "high" }),
          ],
        })}
        onRunAgain={() => {}}
      />,
    );

    const stages = screen.getAllByText(/Brute force|Privilege escalation|Impact/);
    const order = stages.map((el) => el.textContent);
    expect(order).toEqual(["Brute force", "Privilege escalation", "Impact"]);
    expect(screen.getByText("high_cpu")).toBeInTheDocument();
    expect(screen.getByText("failed_logins")).toBeInTheDocument();
  });

  it("reports how many of the expected detections were raised", () => {
    render(
      <SimulationResults
        result={result({
          expected_alerts: ["failed_logins", "brute_force", "ssh_success_after_failures"],
          alerts: [
            alert({ id: "a", rule_type: "failed_logins" }),
            alert({ id: "b", rule_type: "brute_force" }),
          ],
        })}
        onRunAgain={() => {}}
      />,
    );
    expect(screen.getByText("What actually fired")).toBeInTheDocument();
    expect(screen.getByText(/expected detections raised/)).toBeInTheDocument();
    expect(screen.getByText("failed_logins")).toBeInTheDocument();
    expect(screen.getByText("brute_force")).toBeInTheDocument();
  });

  it("explains an empty outcome instead of showing an empty chain", () => {
    render(<SimulationResults result={result()} onRunAgain={() => {}} />);
    expect(screen.getByText(/No detections were raised for this run/)).toBeInTheDocument();
    expect(screen.queryByText("failed_logins")).not.toBeInTheDocument();
  });

  it("offers replay and reset for a preset run", () => {
    const onReplay = vi.fn();
    const onReset = vi.fn();
    render(
      <SimulationResults result={result()} onRunAgain={() => {}} onReplay={onReplay} onReset={onReset} />,
    );

    screen.getByText("Replay this run").click();
    expect(onReplay).toHaveBeenCalledTimes(1);

    screen.getByText("Reset this run").click();
    expect(onReset).toHaveBeenCalledTimes(1);
  });

  it("hides replay for a custom run, which stores no step list", () => {
    render(
      <SimulationResults
        result={result({ scenario: "custom", name: "Custom chain" })}
        onRunAgain={() => {}}
        onReplay={() => {}}
        onReset={() => {}}
      />,
    );
    expect(screen.queryByText("Replay this run")).not.toBeInTheDocument();
    expect(screen.getByText("Reset this run")).toBeInTheDocument();
  });
});
