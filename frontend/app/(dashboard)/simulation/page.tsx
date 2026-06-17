"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Host { id: string; name: string; }
interface Scenario { scenarios: string[]; }

export default function SimulationPage() {
  const [hosts, setHosts] = useState<Host[]>([]);
  const [scenarios, setScenarios] = useState<string[]>([]);
  const [hostId, setHostId] = useState("");
  const [scenario, setScenario] = useState("");
  const [result, setResult] = useState<string | null>(null);

  useEffect(() => {
    api<Host[]>("/api/v1/hosts").then((h) => { setHosts(h); if (h[0]) setHostId(h[0].id); }).catch(console.error);
    api<Scenario>("/api/v1/simulation/scenarios").then((r) => { setScenarios(r.scenarios); if (r.scenarios[0]) setScenario(r.scenarios[0]); }).catch(console.error);
  }, []);

  async function run() {
    if (!hostId || !scenario) return;
    const r = await api<{ message: string; events: number }>(`/api/v1/simulation/run/${scenario}?host_id=${hostId}`, { method: "POST" });
    setResult(`${r.message} (${r.events} events)`);
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Attack Simulation</h1>
      <p className="text-gray-500 text-sm mb-6">Inject synthetic events to test detection and correlation (admin only).</p>
      <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg max-w-lg space-y-4">
        <div>
          <label className="text-sm text-gray-400 block mb-1">Target Host</label>
          <select value={hostId} onChange={(e) => setHostId(e.target.value)} className="w-full px-3 py-2 bg-black/30 border border-[var(--border)] rounded">
            {hosts.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-sm text-gray-400 block mb-1">Scenario</label>
          <select value={scenario} onChange={(e) => setScenario(e.target.value)} className="w-full px-3 py-2 bg-black/30 border border-[var(--border)] rounded">
            {scenarios.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
          </select>
        </div>
        <button onClick={run} className="px-4 py-2 bg-red-700 hover:bg-red-600 rounded text-sm">Run Simulation</button>
        {result && <p className="text-green-400 text-sm">{result}</p>}
      </div>
    </div>
  );
}
