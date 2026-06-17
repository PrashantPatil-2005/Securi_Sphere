"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import TimeRangeBar from "@/components/TimeRangeBar";

interface Timeline {
  id: string;
  host_id: string;
  title: string;
  description: string | null;
  started_at: string;
  ended_at: string;
  mitre_techniques: string[];
  severity: string;
  confidence: number;
  status: string;
}

interface TEvent {
  id: string;
  event_type: string;
  severity: string;
  description: string | null;
  mitre_technique_id: string | null;
  timestamp: string;
}

export default function TimelinePage() {
  const { queryParams } = useTimeRange();
  const [items, setItems] = useState<Timeline[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [events, setEvents] = useState<TEvent[]>([]);

  const load = useCallback(() => {
    const q = buildQuery({ page_size: 100 }, queryParams);
    api<Timeline[]>(`/api/v1/timelines${q}`).then(setItems).catch(console.error);
  }, [queryParams]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!selected) return;
    api<TEvent[]>(`/api/v1/timelines/${selected}/events`).then(setEvents).catch(console.error);
  }, [selected]);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Attack Timelines</h1>
      <TimeRangeBar />
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="space-y-3">
          {items.map((t) => (
            <button
              key={t.id}
              onClick={() => setSelected(t.id)}
              className={`w-full text-left p-4 rounded-lg border ${selected === t.id ? "border-blue-500 bg-blue-900/20" : "border-[var(--border)] bg-[var(--card)]"}`}
            >
              <div className="flex justify-between">
                <span className="font-medium">{t.title}</span>
                <span className={`text-xs severity-${t.severity}`}>{t.severity}</span>
              </div>
              <p className="text-sm text-gray-400 mt-1">{t.description}</p>
              <div className="text-xs text-gray-500 mt-2">
                {new Date(t.started_at).toLocaleString()} — {new Date(t.ended_at).toLocaleString()}
                <span className="ml-2">Confidence: {t.confidence.toFixed(0)}%</span>
              </div>
              {t.mitre_techniques?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {t.mitre_techniques.map((m) => (
                    <span key={m} className="text-xs bg-purple-900/40 px-2 py-0.5 rounded">{m}</span>
                  ))}
                </div>
              )}
            </button>
          ))}
          {items.length === 0 && <p className="text-gray-500">No attack timelines detected yet.</p>}
        </div>
        <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
          <h2 className="font-semibold mb-4">Timeline Events</h2>
          {!selected && <p className="text-gray-500 text-sm">Select a timeline to view events.</p>}
          <div className="space-y-3">
            {events.map((e, i) => (
              <div key={e.id} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className="w-3 h-3 rounded-full bg-blue-500" />
                  {i < events.length - 1 && <div className="w-0.5 flex-1 bg-gray-700 min-h-[24px]" />}
                </div>
                <div className="pb-4">
                  <div className="text-xs text-gray-500">{new Date(e.timestamp).toLocaleString()}</div>
                  <div className="font-medium">{e.event_type}</div>
                  <div className="text-sm text-gray-400">{e.description}</div>
                  {e.mitre_technique_id && <span className="text-xs text-purple-400">{e.mitre_technique_id}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
