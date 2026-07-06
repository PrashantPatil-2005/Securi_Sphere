"use client";

import { FormEvent, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Search, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { useDebounce } from "@/lib/hooks/useDebounce";
import { useHostsList } from "@/lib/hooks/useApiQuery";
import { useTimeRange } from "@/lib/timeRange";
import TimeRangeBar from "@/components/TimeRangeBar";
import {
  AlertResultRow,
  EventResultRow,
  HostResultRow,
  SearchResultSection,
  SearchResultsEmpty,
  SearchResultsSummary,
} from "@/components/search/SearchResults";
import { PageHeader, Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";
import { cn } from "@/lib/utils/cn";

interface SiemResult {
  backend?: string;
  events: { id: string; event_type: string; severity: string; description: string | null; timestamp: string }[];
  alerts: { id: string; title: string; severity: string; status: string }[];
  total_events: number;
  total_alerts: number;
}

interface GlobalResult {
  query: string;
  hosts: { id: string; name: string; hostname: string | null; status: string; ip: string | null }[];
  alerts: { id: string; title: string; severity: string; status: string }[];
  events: { id: string; event_type: string; description: string | null; severity: string }[];
  users: { id: string; email: string; full_name: string | null }[];
}

const FALLBACK_EXAMPLES = ["event_type:ssh_login_failure", "severity:critical", "username:root"];

export default function SearchPage() {
  return (
    <Suspense fallback={<TableSkeleton rows={6} />}>
      <SearchPageContent />
    </Suspense>
  );
}

function SearchPageContent() {
  const searchParams = useSearchParams();
  const { queryParams } = useTimeRange();
  const { data: hosts = [] } = useHostsList();
  const examples = hosts[0]
    ? [`host:${hosts[0].name} severity:critical`, "event_type:ssh_login_failure", "username:root"]
    : FALLBACK_EXAMPLES;
  const siemHint = hosts[0] ? `host:${hosts[0].name} severity:critical` : "event_type:ssh_login_failure severity:critical";
  const [mode, setMode] = useState<"siem" | "global">("siem");
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [nlQuery, setNlQuery] = useState("");
  const nlInputRef = useRef<HTMLInputElement>(null);
  const debouncedQ = useDebounce(q, 400);

  const focusNlSearch = useCallback(() => {
    document.getElementById("nl-search")?.scrollIntoView({ behavior: "smooth", block: "start" });
    nlInputRef.current?.focus();
  }, []);

  useEffect(() => {
    const param = searchParams.get("q");
    if (param) {
      setQ(param);
      setSubmitted(param);
      setMode("global");
    }
  }, [searchParams]);

  const { data: siem, isLoading: siemLoading, isFetching: siemFetching, isError: siemError, refetch: refetchSiem } = useQuery({
    queryKey: ["search", "siem", submitted, queryParams],
    queryFn: async () => {
      const query = buildQuery({ q: submitted }, queryParams);
      return api<SiemResult>(`/api/v1/search/siem${query}`);
    },
    enabled: mode === "siem" && submitted.length > 0,
    staleTime: 60_000,
  });

  const { data: global, isLoading: globalLoading, isFetching: globalFetching, isError: globalError, refetch: refetchGlobal } = useQuery({
    queryKey: ["search", "global", submitted, queryParams],
    queryFn: async () => {
      const query = buildQuery({ q: submitted }, queryParams);
      return api<GlobalResult>(`/api/v1/search${query}`);
    },
    enabled: mode === "global" && submitted.length > 0,
    staleTime: 60_000,
  });

  const { data: saved = [] } = useQuery({
    queryKey: ["saved-searches"],
    queryFn: () => api<{ id: string; name: string; query: string }[]>("/api/v1/saved-searches"),
    staleTime: 120_000,
  });

  const nlMutation = useMutation({
    mutationFn: (query: string) =>
      api<{ siem_query: string; explanation: string; provider: string; confidence: string }>(
        "/api/v1/search/nl",
        { method: "POST", body: JSON.stringify({ query }) },
      ),
    onSuccess: (data) => {
      setMode("siem");
      setQ(data.siem_query);
      setSubmitted(data.siem_query);
    },
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!debouncedQ.trim()) return;
    setSubmitted(debouncedQ.trim());
  }

  const isLoading = mode === "siem" ? siemLoading : globalLoading;
  const isFetching = mode === "siem" ? siemFetching : globalFetching;
  const isError = mode === "siem" ? siemError : globalError;
  const refetch = mode === "siem" ? refetchSiem : refetchGlobal;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Search"
        subtitle={mode === "siem" ? `SIEM query language — e.g. ${siemHint}` : "Global search across hosts, alerts, and events"}
      />
      <TimeRangeBar />

      <div id="nl-search">
        <Panel title="Natural language search" subtitle='Plain English → SIEM query, e.g. "Show failed logins from last hour"'>
          <form
            className="flex flex-col sm:flex-row gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (!nlQuery.trim()) return;
              nlMutation.mutate(nlQuery.trim());
            }}
          >
            <Input
              ref={nlInputRef}
              value={nlQuery}
              onChange={(e) => setNlQuery(e.target.value)}
              placeholder="Show failed logins from last hour"
              className="flex-1"
            />
          <Button type="submit" loading={nlMutation.isPending} disabled={!nlQuery.trim()} className="shrink-0">
            <Sparkles className="w-4 h-4" />
            Convert
          </Button>
        </form>
        {nlMutation.data && (
          <div className="mt-3 p-3 rounded-lg border border-accent/25 bg-accent/5 text-sm">
            <p className="text-muted mb-1">Generated SIEM query:</p>
            <code className="font-mono text-accent break-all">{nlMutation.data.siem_query}</code>
            <p className="text-xs text-muted mt-2">{nlMutation.data.explanation}</p>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="mt-2"
              onClick={() => {
                setQ(nlMutation.data!.siem_query);
                setSubmitted(nlMutation.data!.siem_query);
                setMode("siem");
              }}
            >
              Edit query
            </Button>
          </div>
        )}
        {nlMutation.isError && (
          <p className="text-xs text-danger mt-2">{nlMutation.error.message}</p>
        )}
        </Panel>
      </div>

      <div className="flex flex-wrap gap-2">
        {(["siem", "global"] as const).map((m) => (
          <Button
            key={m}
            type="button"
            variant="ghost"
            onClick={() => setMode(m)}
            className={cn("capitalize", mode === m && "bg-accent/10 text-accent border-accent/30")}
          >
            {m === "siem" ? "SIEM query" : "Global search"}
          </Button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2 items-end">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted pointer-events-none z-10" aria-hidden />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={mode === "siem" ? siemHint : "Search keyword…"}
            className={cn("pl-9", mode === "siem" && "font-mono")}
            aria-label="Search query"
          />
        </div>
        <Button type="submit" className="shrink-0">Run</Button>
      </form>

      {mode === "siem" && (
        <div className="flex flex-wrap gap-2">
          <span className="text-xs text-muted self-center">Examples:</span>
          {examples.map((ex) => (
            <Button key={ex} type="button" variant="ghost" size="sm" className="font-mono" onClick={() => { setQ(ex); setSubmitted(ex); }}>
              {ex}
            </Button>
          ))}
        </div>
      )}
      {saved.length > 0 && mode === "siem" && (
        <div className="flex flex-wrap gap-2">
          <span className="text-xs text-muted self-center">Saved:</span>
          {saved.map((s) => (
            <Button key={s.id} type="button" variant="ghost" size="sm" onClick={() => { setQ(s.query); setSubmitted(s.query); }}>
              {s.name}
            </Button>
          ))}
        </div>
      )}

      {isLoading && submitted.length > 0 && <TableSkeleton rows={4} />}
      {isError && submitted.length > 0 && <QueryError onRetry={() => refetch()} />}

      {mode === "siem" && siem && !isError && (
        <div className={cn("space-y-4", isFetching && "opacity-60")}>
          <SearchResultsSummary events={siem.total_events} alerts={siem.total_alerts} backend={siem.backend} />
          {siem.events.length === 0 && siem.alerts.length === 0 && (
            <SearchResultsEmpty description="Try broadening your query or time range." onTryNl={focusNlSearch} />
          )}
          <SearchResultSection title="Alerts" count={siem.alerts.length}>
            {siem.alerts.map((a) => <AlertResultRow key={a.id} alert={a} />)}
          </SearchResultSection>
          <SearchResultSection title="Events" count={siem.events.length}>
            {siem.events.map((ev) => <EventResultRow key={ev.id} event={ev} />)}
          </SearchResultSection>
        </div>
      )}

      {mode === "global" && global && !isError && (
        <div className={cn("space-y-4", isFetching && "opacity-60")}>
          <SearchResultsSummary
            events={global.events.length}
            alerts={global.alerts.length}
            hosts={global.hosts.length}
          />
          {global.hosts.length === 0 && global.alerts.length === 0 && global.events.length === 0 && (
            <SearchResultsEmpty description={`Nothing matched "${global.query}"`} onTryNl={focusNlSearch} />
          )}
          <SearchResultSection title="Hosts" count={global.hosts.length}>
            {global.hosts.map((h) => <HostResultRow key={h.id} host={h} />)}
          </SearchResultSection>
          <SearchResultSection title="Alerts" count={global.alerts.length}>
            {global.alerts.map((a) => <AlertResultRow key={a.id} alert={a} />)}
          </SearchResultSection>
          <SearchResultSection title="Events" count={global.events.length}>
            {global.events.map((e) => <EventResultRow key={e.id} event={e} />)}
          </SearchResultSection>
          {global.users.length > 0 && (
            <SearchResultSection title="Users" count={global.users.length}>
              {global.users.map((u) => (
                <div key={u.id} className="panel p-3 text-sm">
                  <p className="font-medium">{u.full_name || u.email}</p>
                  <p className="text-xs text-muted">{u.email}</p>
                </div>
              ))}
            </SearchResultSection>
          )}
        </div>
      )}

      {submitted && !isLoading && !isError && mode === "siem" && !siem && (
        <p className="text-sm text-muted">Enter a query and press Run.</p>
      )}
    </div>
  );
}
