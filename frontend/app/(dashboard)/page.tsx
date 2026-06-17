"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { parsePaginatedList } from "@/lib/parseList";
import { useTimeRange } from "@/lib/timeRange";
import TimeRangeBar from "@/components/TimeRangeBar";
import { useWebSocket } from "@/lib/websocket";

interface Overview {
  total_hosts: number;
  online_hosts: number;
  offline_hosts: number;
  active_alerts: number;
  critical_alerts: number;
}
interface Analytics {
  events_today: number;
  events_this_week: number;
  events_this_month: number;
  alerts_today: number;
  alerts_this_week: number;
  alerts_this_month: number;
}
interface ThreatScore {
  host_id: string;
  host_name: string;
  score: number;
  health_score: number;
}
interface Alert {
  id: string;
  title: string;
  severity: string;
  confidence?: number;
}
interface Event {
  id: string;
  event_type: string;
  severity: string;
  description: string | null;
  timestamp: string;
}
interface Retention {
  events: { period: string; count: number }[];
  alerts: { period: string; count: number }[];
}

export default function OverviewPage() {
  const { queryParams } = useTimeRange();
  const [data, setData] = useState<Overview | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [scores, setScores] = useState<ThreatScore[]>([]);
  const [recentAlerts, setRecentAlerts] = useState<Alert[]>([]);
  const [feed, setFeed] = useState<Event[]>([]);
  const [retentionView, setRetentionView] = useState<"daily" | "weekly" | "monthly">("daily");
  const [retention, setRetention] = useState<Retention | null>(null);

  const load = () => {
    api<Overview>("/api/v1/overview").then(setData).catch(console.error);
    api<Analytics>("/api/v1/analytics/summary").then(setAnalytics).catch(console.error);
    api<ThreatScore[]>("/api/v1/threat-scores").then(setScores).catch(console.error);
    const eq = buildQuery({ status: "open", page_size: 5 }, queryParams);
    api<{ items?: Alert[] } | Alert[]>(`/api/v1/alerts${eq}`)
      .then((r) => setRecentAlerts(parsePaginatedList(r).items))
      .catch(console.error);
    const evq = buildQuery({ page_size: 8 }, queryParams);
    api<{ items?: Event[] } | Event[]>(`/api/v1/events${evq}`)
      .then((r) => setFeed(parsePaginatedList(r).items))
      .catch(console.error);
    api<Retention>(`/api/v1/analytics/retention?view=${retentionView}`).then(setRetention).catch(console.error);
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [queryParams, retentionView]);
  useWebSocket((msg) => {
    if (["new_alert", "new_event", "host_status"].includes(msg.type)) load();
  });

  const cards = [
    { label: "Total Hosts", value: data?.total_hosts ?? "-", color: "text-blue-400" },
    { label: "Online", value: data?.online_hosts ?? "-", color: "text-green-400" },
    { label: "Offline / Critical", value: data?.offline_hosts ?? "-", color: "text-gray-400" },
    { label: "Active Alerts", value: data?.active_alerts ?? "-", color: "text-yellow-400" },
    { label: "Critical Alerts", value: data?.critical_alerts ?? "-", color: "text-red-400" },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Security Overview</h1>
      <TimeRangeBar />
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {cards.map((c) => (
          <div key={c.label} className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
            <p className="text-sm text-gray-500">{c.label}</p>
            <p className={`text-3xl font-bold ${c.color}`}>{c.value}</p>
          </div>
        ))}
      </div>
      {analytics && (
        <div className="grid md:grid-cols-2 gap-4">
          <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
            <h2 className="font-semibold mb-3">Event Volume</h2>
            <div className="grid grid-cols-3 gap-2 text-center text-sm">
              <div>
                <p className="text-gray-500">Today</p>
                <p className="text-xl font-bold">{analytics.events_today}</p>
              </div>
              <div>
                <p className="text-gray-500">This Week</p>
                <p className="text-xl font-bold">{analytics.events_this_week}</p>
              </div>
              <div>
                <p className="text-gray-500">This Month</p>
                <p className="text-xl font-bold">{analytics.events_this_month}</p>
              </div>
            </div>
          </div>
          <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
            <h2 className="font-semibold mb-3">Alert Volume</h2>
            <div className="grid grid-cols-3 gap-2 text-center text-sm">
              <div>
                <p className="text-gray-500">Today</p>
                <p className="text-xl font-bold text-yellow-400">{analytics.alerts_today}</p>
              </div>
              <div>
                <p className="text-gray-500">This Week</p>
                <p className="text-xl font-bold text-yellow-400">{analytics.alerts_this_week}</p>
              </div>
              <div>
                <p className="text-gray-500">This Month</p>
                <p className="text-xl font-bold text-yellow-400">{analytics.alerts_this_month}</p>
              </div>
            </div>
          </div>
        </div>
      )}
      <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
        <div className="flex justify-between items-center mb-4">
          <h2 className="font-semibold">90-Day Retention View</h2>
          <select
            value={retentionView}
            onChange={(e) => setRetentionView(e.target.value as typeof retentionView)}
            className="px-3 py-1 bg-black/30 border border-[var(--border)] rounded text-sm"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
        {retention && (
          <div className="grid md:grid-cols-2 gap-4 max-h-48 overflow-y-auto text-xs font-mono">
            <div>
              {retention.events.slice(-14).map((r) => (
                <div key={r.period} className="flex justify-between py-0.5">
                  <span>{r.period.slice(0, 10)}</span>
                  <span>{r.count} events</span>
                </div>
              ))}
            </div>
            <div>
              {retention.alerts.slice(-14).map((r) => (
                <div key={r.period} className="flex justify-between py-0.5">
                  <span>{r.period.slice(0, 10)}</span>
                  <span>{r.count} alerts</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
          <h2 className="font-semibold mb-4">Threat Score Heatmap</h2>
          {scores.map((s) => (
            <div key={s.host_id} className="flex items-center gap-3 mb-2">
              <span className="text-sm w-32 truncate">{s.host_name}</span>
              <div className="flex-1 h-5 bg-gray-800 rounded">
                <div className="h-full bg-red-500" style={{ width: `${Math.min(s.score, 100)}%` }} />
              </div>
              <span className="text-sm w-8">{s.score}</span>
            </div>
          ))}
        </div>
        <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
          <h2 className="font-semibold mb-4">Recent Alerts</h2>
          {recentAlerts.map((a) => (
            <div key={a.id} className="text-sm border-b border-[var(--border)] pb-2 mb-2">
              <span className={`severity-${a.severity} text-xs uppercase font-bold mr-2`}>{a.severity}</span>
              {a.title}
            </div>
          ))}
        </div>
      </div>
      <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
        <h2 className="font-semibold mb-4">Live Event Feed</h2>
        <div className="space-y-1 max-h-64 overflow-y-auto font-mono text-sm">
          {feed.map((e) => (
            <div key={e.id} className="flex gap-3 text-gray-400">
              <span className="text-gray-600">{new Date(e.timestamp).toLocaleTimeString()}</span>
              <span>{e.event_type}</span>
              <span className="truncate">{e.description}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
