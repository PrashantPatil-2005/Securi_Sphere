"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Technique {
  technique_id: string;
  tactic: string;
  name: string;
  count: number;
}

export default function MitrePage() {
  const [tactics, setTactics] = useState<Record<string, Technique[]>>({});

  useEffect(() => {
    api<{ tactics: Record<string, Technique[]> }>("/api/v1/mitre/matrix")
      .then((r) => setTactics(r.tactics))
      .catch(console.error);
  }, []);

  const tacticOrder = Object.keys(tactics);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">MITRE ATT&CK Matrix</h1>
      <p className="text-gray-500 text-sm mb-6">Techniques observed in ingested events</p>
      <div className="overflow-x-auto">
        <div className="flex gap-3 min-w-max pb-4">
          {tacticOrder.map((tactic) => (
            <div key={tactic} className="w-48 shrink-0">
              <div className="bg-blue-900/40 text-blue-300 text-xs font-bold px-2 py-2 rounded-t border border-[var(--border)]">
                {tactic}
              </div>
              <div className="border border-t-0 border-[var(--border)] rounded-b min-h-[120px] p-2 space-y-1">
                {(tactics[tactic] || []).map((t) => (
                  <div
                    key={t.technique_id}
                    className={`text-xs p-2 rounded border ${t.count > 0 ? "bg-red-900/30 border-red-800" : "bg-[var(--card)] border-[var(--border)]"}`}
                    title={t.name}
                  >
                    <div className="font-mono text-gray-400">{t.technique_id}</div>
                    <div className="truncate">{t.name}</div>
                    {t.count > 0 && <div className="text-red-400 mt-1">{t.count} events</div>}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
      {tacticOrder.length === 0 && <p className="text-gray-500">Loading matrix...</p>}
    </div>
  );
}
