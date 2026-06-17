"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useWebSocket } from "@/lib/websocket";

interface Event {
  id: string;
  host_id: string;
  event_type: string;
  severity: string;
  description: string | null;
  timestamp: string;
}

export default function EventsPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [severity, setSeverity] = useState("");
  const [eventType, setEventType] = useState("");

  const load = () => {
    const params = new URLSearchParams();
    if (severity) params.set("severity", severity);
    if (eventType) params.set("event_type", eventType);
    api<{ items: Event[] }>(`/api/v1/events?${params}`).then((r) => setEvents(r.items)).catch(console.error);
  };

  useEffect(() => { load(); }, [severity, eventType]);
  useWebSocket((msg) => { if (msg.type === "new_event") load(); });

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Events</h1>
      <div className="flex gap-4 mb-4">
        <select value={severity} onChange={(e) => setSeverity(e.target.value)}
          className="px-3 py-2 bg-[var(--background)] border border-[var(--border)] rounded text-sm">
          <option value="">All severities</option>
          {["info", "low", "medium", "high", "critical"].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <input value={eventType} onChange={(e) => setEventType(e.target.value)} placeholder="Event type filter"
          className="px-3 py-2 bg-[var(--background)] border border-[var(--border)] rounded text-sm" />
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 border-b border-[var(--border)]">
            <th className="pb-2">Timestamp</th><th className="pb-2">Type</th><th className="pb-2">Severity</th><th className="pb-2">Description</th>
          </tr>
        </thead>
        <tbody>
          {events.map((e) => (
            <tr key={e.id} className="border-b border-[var(--border)]/50">
              <td className="py-2 text-gray-400">{new Date(e.timestamp).toLocaleString()}</td>
              <td>{e.event_type}</td>
              <td><span className={`px-2 py-0.5 rounded text-xs severity-${e.severity}`}>{e.severity}</span></td>
              <td>{e.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {events.length === 0 && <p className="text-gray-500 mt-4">No events yet.</p>}
    </div>
  );
}
