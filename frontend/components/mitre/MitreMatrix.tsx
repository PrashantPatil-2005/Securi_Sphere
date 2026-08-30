"use client";

import { memo } from "react";
import type { MitreTechniqueWithCount } from "@/lib/types/mitre";
import { MITRE_TACTIC_ORDER } from "@/lib/types/mitre";

interface MitreMatrixProps {
  tactics: Record<string, MitreTechniqueWithCount[]>;
  tacticCoverage: Record<string, number>;
  selectedTechnique: string | null;
  onSelect: (id: string | null) => void;
}

function heatClass(count: number, selected: boolean): string {
  const base =
    count > 5
      ? "bg-danger/15 border-danger/30"
      : count > 0
        ? "bg-warning/10 border-warning/25"
        : "bg-card-elevated border-border-subtle";
  const ring = selected ? " ring-2 ring-accent ring-offset-1 ring-offset-background" : "";
  return `${base}${ring}`;
}

function MitreMatrixInner({ tactics, tacticCoverage, selectedTechnique, onSelect }: MitreMatrixProps) {
  const tacticOrder = (MITRE_TACTIC_ORDER.filter((t) => tactics[t]) as string[]).concat(
    Object.keys(tactics).filter((t) => !MITRE_TACTIC_ORDER.includes(t as typeof MITRE_TACTIC_ORDER[number])),
  );

  return (
    <div className="overflow-x-auto">
      <div className="flex gap-3 min-w-max pb-4">
        {tacticOrder.map((tactic) => {
          const items = tactics[tactic] || [];
          const cov = tacticCoverage[tactic] ?? 0;
          return (
            <div key={tactic} className="w-48 shrink-0">
              <div className="px-2 py-2 rounded-t text-xs font-semibold flex justify-between gap-1 bg-card-elevated border border-border-subtle border-b-0">
                <span className="truncate">{tactic}</span>
                <span className="text-accent tabular-nums">{cov}%</span>
              </div>
              <div className="border border-t-0 border-border-subtle rounded-b min-h-[120px] p-2 space-y-1 bg-card/50">
                {items.map((t) => {
                  const selected = selectedTechnique === t.technique_id;
                  return (
                    <button
                      key={t.technique_id}
                      type="button"
                      onClick={() => onSelect(selected ? null : t.technique_id)}
                      className={`w-full text-left text-xs p-2 rounded border transition-colors hover:border-accent/50 cursor-pointer ${heatClass(t.count, selected)}`}
                      title={t.name}
                    >
                      <div className="font-mono text-muted">{t.technique_id}</div>
                      <div className="truncate">{t.name}</div>
                      {t.count > 0 && (
                        <div className="text-danger mt-1 tabular-nums">{t.count} events</div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export const MitreMatrix = memo(MitreMatrixInner);
