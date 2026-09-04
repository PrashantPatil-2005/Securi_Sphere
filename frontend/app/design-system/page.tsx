"use client";

import {
  AlertTriangle,
  AlertCircle,
  Shield,
  Server,
  Activity,
  Bell,
  User,
  Search,
  ChevronDown,
  RefreshCw,
} from "lucide-react";
import {
  Button,
  Input,
  Select,
  Badge,
  SeverityBadge,
  StatusBadge,
  KpiCard,
  Card,
  CardHeader,
  SearchBar,
  Dropdown,
  Tooltip,
  LoadingState,
  Skeleton,
  ErrorState,
  EmptyState,
  TimelineItem,
  DataTable,
  FilterChip,
  FilterGroup,
  Pagination,
} from "@/components/design-system";
import type { Column } from "@/components/design-system/DataTable";

interface SampleRow {
  id: string;
  name: string;
  severity: string;
  status: string;
  host: string;
}

const sampleData: SampleRow[] = [
  { id: "1", name: "Brute force detected", severity: "critical", status: "new", host: "dc-01.corp.local" },
  { id: "2", name: "Suspicious login", severity: "high", status: "investigating", host: "web-03.prod" },
  { id: "3", name: "Port scan detected", severity: "medium", status: "open", host: "fw-01.dmz" },
  { id: "4", name: "DNS query anomaly", severity: "low", status: "resolved", host: "dns-01.internal" },
  { id: "5", name: "Info: Scheduled task", severity: "info", status: "closed", host: "ws-42.corp.local" },
];

const columns: Column<SampleRow>[] = [
  { key: "name", header: "Alert", render: (r) => <span className="font-medium">{r.name}</span> },
  { key: "severity", header: "Severity", render: (r) => <SeverityBadge severity={r.severity} /> },
  { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
  { key: "host", header: "Host", render: (r) => <span className="code-text">{r.host}</span> },
];

const dropdownItems = [
  { label: "Investigate", icon: <Search className="w-4 h-4" /> },
  { label: "Assign", icon: <User className="w-4 h-4" /> },
  { separator: true, label: "" },
  { label: "Escalate", icon: <AlertTriangle className="w-4 h-4" /> },
  { label: "Close", icon: <AlertCircle className="w-4 h-4" />, danger: true },
];

export default function DesignSystemPage() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-10 space-y-12">
      <header>
        <h1 className="text-display text-foreground">Design System</h1>
        <p className="text-body text-muted mt-1">
          Securi Sphere component library and visual language reference.
        </p>
      </header>

      {/* ─── Colors ─── */}
      <section className="space-y-4">
        <h2 className="text-h2 text-foreground">Colors</h2>

        <div className="space-y-3">
          <h3 className="text-h3 text-foreground">Severity</h3>
          <div className="flex flex-wrap gap-3">
            {(["critical", "high", "medium", "low", "info"] as const).map((s) => (
              <div key={s} className="flex items-center gap-2">
                <div
                  className="w-8 h-8 rounded-md border border-border"
                  style={{ background: `var(--severity-${s})` }}
                />
                <span className="text-sm text-foreground capitalize">{s}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <h3 className="text-h3 text-foreground">Semantic</h3>
          <div className="flex flex-wrap gap-3">
            {(["accent", "success", "warning", "danger", "muted"] as const).map((s) => (
              <div key={s} className="flex items-center gap-2">
                <div
                  className="w-8 h-8 rounded-md border border-border"
                  style={{ background: `var(--${s})` }}
                />
                <span className="text-sm text-foreground">{s}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <h3 className="text-h3 text-foreground">Surfaces</h3>
          <div className="flex flex-wrap gap-3">
            {(["background", "card", "card-elevated", "card-overlay", "input-bg", "sidebar-bg"] as const).map((s) => (
              <div key={s} className="flex items-center gap-2">
                <div
                  className="w-8 h-8 rounded-md border border-border"
                  style={{ background: `var(--${s})` }}
                />
                <span className="text-sm text-foreground">{s}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Typography ─── */}
      <section className="space-y-4">
        <h2 className="text-h2 text-foreground">Typography</h2>
        <div className="space-y-3">
          <p className="text-display text-foreground">Display — The quick brown fox</p>
          <p className="text-h1 text-foreground">H1 — The quick brown fox</p>
          <p className="text-h2 text-foreground">H2 — The quick brown fox</p>
          <p className="text-h3 text-foreground">H3 — The quick brown fox</p>
          <p className="text-body text-foreground">Body — The quick brown fox jumps over the lazy dog</p>
          <p className="text-caption text-muted">Caption — The quick brown fox jumps over the lazy dog</p>
          <p className="code-text">monospace — 192.168.1.1:8080</p>
        </div>
      </section>

      {/* ─── Buttons ─── */}
      <section className="space-y-4">
        <h2 className="text-h2 text-foreground">Buttons</h2>
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="primary">Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger">Danger</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="link">Link</Button>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="primary" size="xs">Extra Small</Button>
          <Button variant="primary" size="sm">Small</Button>
          <Button variant="primary" size="md">Medium</Button>
          <Button variant="primary" size="lg">Large</Button>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="primary" loading>Loading</Button>
          <Button variant="primary" disabled>Disabled</Button>
          <Button variant="primary" icon={<Search className="w-4 h-4" />}>With Icon</Button>
          <Button variant="ghost" icon={<RefreshCw className="w-4 h-4" />}>Refresh</Button>
        </div>
      </section>

      {/* ─── Inputs ─── */}
      <section className="space-y-4">
        <h2 className="text-h2 text-foreground">Inputs</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input label="Email" placeholder="analyst@corp.local" />
          <Input label="Search" placeholder="Search events\u2026" icon={<Search className="w-4 h-4" />} />
          <Input label="With Error" placeholder="Invalid input" error="This field is required" />
          <Input label="With Hint" placeholder="Optional" hint="Enter a value" />
          <Select label="Severity">
            <option value="">All severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </Select>
          <Select label="Status">
            <option value="">All statuses</option>
            <option value="new">New</option>
            <option value="investigating">Investigating</option>
            <option value="resolved">Resolved</option>
          </Select>
        </div>
      </section>

      {/* ─── Badges ─── */}
      <section className="space-y-4">
        <h2 className="text-h2 text-foreground">Badges</h2>
        <div className="space-y-3">
          <h3 className="text-h3 text-foreground">Severity Badges</h3>
          <div className="flex flex-wrap gap-2">
            <SeverityBadge severity="critical" />
            <SeverityBadge severity="high" />
            <SeverityBadge severity="medium" />
            <SeverityBadge severity="low" />
            <SeverityBadge severity="info" />
          </div>
        </div>
        <div className="space-y-3">
          <h3 className="text-h3 text-foreground">Status Badges</h3>
          <div className="flex flex-wrap gap-2">
            <StatusBadge status="new" />
            <StatusBadge status="investigating" />
            <StatusBadge status="resolved" />
            <StatusBadge status="closed" />
            <StatusBadge status="online" />
            <StatusBadge status="offline" />
            <StatusBadge status="degraded" />
          </div>
        </div>
        <div className="space-y-3">
          <h3 className="text-h3 text-foreground">Custom Badges</h3>
          <div className="flex flex-wrap gap-2">
            <Badge variant="severity" severity="critical">Critical</Badge>
            <Badge variant="status" status="investigating" dot>Investigating</Badge>
            <Badge className="bg-accent/10 text-accent border-accent/30">Custom</Badge>
          </div>
        </div>
      </section>

      {/* ─── KPI Cards ─── */}
      <section className="space-y-4">
        <h2 className="text-h2 text-foreground">KPI Cards</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard label="Active Alerts" value={42} delta={12} deltaLabel="vs last hour" icon={<AlertTriangle className="w-4 h-4" />} />
          <KpiCard label="Hosts Online" value={128} delta={-3} deltaLabel="offline" icon={<Server className="w-4 h-4" />} />
          <KpiCard label="Events/sec" value="1.2k" icon={<Activity className="w-4 h-4" />} />
          <KpiCard label="Open Offenses" value={7} icon={<Shield className="w-4 h-4" />} loading />
        </div>
      </section>

      {/* ─── Cards ─── */}
      <section className="space-y-4">
        <h2 className="text-h2 text-foreground">Cards</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader title="Panel Header" subtitle="With subtitle" action={<Button variant="ghost" size="xs">Action</Button>} />
            <p className="text-sm text-muted">Card body content goes here.</p>
          </Card>
          <Card hoverable>
            <p className="text-sm text-foreground">Hoverable card with content.</p>
          </Card>
        </div>
      </section>

      {/* ─── Search ─── */}
      <section className="space-y-4">
        <h2 className="text-h2 text-foreground">Search Bar</h2>
        <div className="max-w-md">
          <SearchBar placeholder="Search alerts, hosts, events\u2026" />
        </div>
      </section>

      {/* ─── Dropdown ─── */}
      <section className="space-y-4">
        <h2 className="text-h2 text-foreground">Dropdown</h2>
        <div className="flex gap-4">
          <Dropdown
            trigger={
              <Button variant="ghost" size="sm">
                Actions <ChevronDown className="w-3.5 h-3.5" />
              </Button>
            }
            items={dropdownItems}
          />
        </div>
      </section>

      {/* ─── Tooltips ─── */}
      <section className="space-y-4">
        <h2 className="text-h2 text-foreground">Tooltips</h2>
        <div className="flex gap-6">
          <Tooltip content="Top tooltip">
            <Button variant="ghost" size="sm">Top</Button>
          </Tooltip>
          <Tooltip content="Bottom tooltip" side="bottom">
            <Button variant="ghost" size="sm">Bottom</Button>
          </Tooltip>
          <Tooltip content="Left tooltip" side="left">
            <Button variant="ghost" size="sm">Left</Button>
          </Tooltip>
          <Tooltip content="Right tooltip" side="right">
            <Button variant="ghost" size="sm">Right</Button>
          </Tooltip>
        </div>
      </section>

      {/* ─── Filter Chips ─── */}
      <section className="space-y-4">
        <h2 className="text-h2 text-foreground">Filter Chips</h2>
        <FilterGroup label="Severity">
          <FilterChip label="Critical" active onClick={() => {}} onClear={() => {}} />
          <FilterChip label="High" onClick={() => {}} />
          <FilterChip label="Medium" onClick={() => {}} />
          <FilterChip label="Low" onClick={() => {}} />
        </FilterGroup>
      </section>

      {/* ─── Data Table ─── */}
      <section className="space-y-4">
        <h2 className="text-h2 text-foreground">Data Table</h2>
        <DataTable<SampleRow>
          columns={columns}
          data={sampleData}
          rowKey={(r) => r.id}
          onRowClick={() => {}}
        />
      </section>

      {/* ─── Pagination ─── */}
      <section className="space-y-4">
        <h2 className="text-h2 text-foreground">Pagination</h2>
        <Pagination page={3} totalPages={10} onPageChange={() => {}} />
      </section>

      {/* ─── Timeline ─── */}
      <section className="space-y-4">
        <h2 className="text-h2 text-foreground">Timeline</h2>
        <div className="max-w-lg">
          <TimelineItem severity="critical" title="Brute force detected" timestamp="2 min ago" description="50 failed login attempts from 192.168.1.100" />
          <TimelineItem severity="high" title="Suspicious process" timestamp="5 min ago" description="powershell.exe spawned by outlook.exe" />
          <TimelineItem severity="medium" title="Port scan detected" timestamp="12 min ago" description="SYN scan from 10.0.0.50 targeting ports 22, 80, 443" />
          <TimelineItem severity="low" title="DNS query anomaly" timestamp="1 hr ago" description="Unusual DNS TXT query pattern detected" />
          <TimelineItem severity="info" title="Scheduled task created" timestamp="3 hr ago" description="Task \u2018BackupJob\u2019 registered on ws-42" />
        </div>
      </section>

      {/* ─── Loading States ─── */}
      <section className="space-y-4">
        <h2 className="text-h2 text-foreground">Loading States</h2>
        <div className="space-y-6">
          <div>
            <p className="text-sm text-muted mb-2">Inline</p>
            <LoadingState variant="inline" text="Loading alerts\u2026" />
          </div>
          <div>
            <p className="text-sm text-muted mb-2">Card</p>
            <LoadingState variant="card" />
          </div>
          <div>
            <p className="text-sm text-muted mb-2">Table</p>
            <LoadingState variant="table" rows={4} />
          </div>
        </div>
      </section>

      {/* ─── Error State ─── */}
      <section className="space-y-4">
        <h2 className="text-h2 text-foreground">Error State</h2>
        <ErrorState
          title="Failed to load alerts"
          description="The backend service is unavailable. Check your network connection."
          onRetry={() => {}}
        />
      </section>

      {/* ─── Empty State ─── */}
      <section className="space-y-4">
        <h2 className="text-h2 text-foreground">Empty State</h2>
        <EmptyState
          title="No alerts found"
          description="No alerts match your current filters. Try adjusting your search criteria."
          icon={<Bell className="w-7 h-7" />}
        />
      </section>

      {/* ─── Skeleton ─── */}
      <section className="space-y-4">
        <h2 className="text-h2 text-foreground">Skeleton</h2>
        <div className="space-y-3">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-4 w-64" />
          <Skeleton className="h-8 w-32" />
        </div>
      </section>

      <div className="border-t border-border-subtle pt-6 text-center text-caption text-muted">
        Design System v1.0 — Securi Sphere
      </div>
    </div>
  );
}
