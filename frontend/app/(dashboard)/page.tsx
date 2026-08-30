"use client";

import { useState } from "react";
import {
  Shield,
  Clock,
  LayoutGrid,
} from "lucide-react";
import { Button } from "@/components/design-system/Button";
import TimeRangeBar from "@/components/filters/TimeRangeBar";
import { HostRiskDrawer } from "@/components/HostRiskDrawer";
import { DashboardCustomizer } from "@/components/dashboard/DashboardCustomizer";
import { Card, CardHeader } from "@/components/design-system/Card";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import {
  SecurityKpis,
  ActiveThreats,
  HostRiskPanel,
  AttackTimelines,
  AlertTrendChart,
  SeverityBreakdown,
  SystemHealthPanel,
  LiveFeed,
  RecentOffenses,
} from "@/components/dashboard/sections";
import { useWsConnected } from "@/lib/websocket";

function SystemStatusDot() {
  const connected = useWsConnected();
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="relative flex h-2 w-2">
        <span
          className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-40 ${
            connected ? "bg-success" : "bg-danger"
          }`}
        />
        <span
          className={`relative inline-flex rounded-full h-2 w-2 ${
            connected ? "bg-success" : "bg-danger"
          }`}
        />
      </span>
      <span className="text-muted">
        System: {connected ? "Healthy" : "Disconnected"}
      </span>
    </div>
  );
}

function LastUpdated() {
  const [now] = useState(() => new Date());
  return (
    <span className="text-[11px] text-muted tabular-nums flex items-center gap-1">
      <Clock className="w-3 h-3" />
      {now.toLocaleTimeString()}
    </span>
  );
}

export default function ExecutiveDashboard() {
  const [riskHostId, setRiskHostId] = useState<string | null>(null);
  const [customizeOpen, setCustomizeOpen] = useState(false);

  return (
    <div className="space-y-5">
      {/* Header */}
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground flex items-center gap-2">
            <Shield className="w-5 h-5 text-accent" />
            Security Operations
          </h1>
          <div className="flex items-center gap-3 mt-1">
            <SystemStatusDot />
            <LastUpdated />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <TimeRangeBar />
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setCustomizeOpen(true)}
            icon={<LayoutGrid className="w-4 h-4" />}
          >
            Customize
          </Button>
        </div>
      </header>

      {/* KPI Row */}
      <ErrorBoundary>
        <SecurityKpis />
      </ErrorBoundary>

      {/* Main Grid: Active Threats + Severity */}
      <div className="grid lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <ErrorBoundary>
            <Card>
              <CardHeader
                title="Active Threats"
                subtitle="Critical and high severity alerts requiring attention"
              />
              <div className="p-4">
                <ActiveThreats />
              </div>
            </Card>
          </ErrorBoundary>
        </div>
        <div>
          <ErrorBoundary>
            <Card>
              <CardHeader
                title="Severity Distribution"
                subtitle="Alert breakdown by severity"
              />
              <div className="p-4">
                <SeverityBreakdown />
              </div>
            </Card>
          </ErrorBoundary>
        </div>
      </div>

      {/* Second Row: Host Risk + Attack Timelines */}
      <div className="grid lg:grid-cols-2 gap-5">
        <ErrorBoundary>
          <Card>
            <CardHeader
              title="Host Risk Ranking"
              subtitle="Highest risk scores in your environment"
            />
            <div className="p-4">
              <HostRiskPanel />
            </div>
          </Card>
        </ErrorBoundary>
        <ErrorBoundary>
          <Card>
            <CardHeader
              title="Attack Timelines"
              subtitle="Active correlated threat sequences"
            />
            <div className="p-4">
              <AttackTimelines />
            </div>
          </Card>
        </ErrorBoundary>
      </div>

      {/* Third Row: Alert Trend + Recent Offenses */}
      <div className="grid lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <ErrorBoundary>
            <Card>
              <CardHeader
                title="Alert Trend"
                subtitle="Event volume over time"
              />
              <div className="p-4">
                <AlertTrendChart />
              </div>
            </Card>
          </ErrorBoundary>
        </div>
        <div>
          <ErrorBoundary>
            <Card>
              <CardHeader
                title="Recent Offenses"
                subtitle="Latest correlated offense groups"
              />
              <div className="p-4">
                <RecentOffenses />
              </div>
            </Card>
          </ErrorBoundary>
        </div>
      </div>

      {/* Fourth Row: Live Feed + System Health */}
      <div className="grid lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <ErrorBoundary>
            <Card>
              <CardHeader
                title="Live Security Feed"
                subtitle="Real-time events via WebSocket"
              />
              <div className="p-4">
                <LiveFeed />
              </div>
            </Card>
          </ErrorBoundary>
        </div>
        <div>
          <ErrorBoundary>
            <Card>
              <CardHeader
                title="System Health"
                subtitle="Backend service status"
              />
              <div className="p-4">
                <SystemHealthPanel />
              </div>
            </Card>
          </ErrorBoundary>
        </div>
      </div>

      <HostRiskDrawer hostId={riskHostId} onClose={() => setRiskHostId(null)} />
      <DashboardCustomizer open={customizeOpen} onClose={() => setCustomizeOpen(false)} />
    </div>
  );
}
