"use client";

import { useQuery } from "@tanstack/react-query";
import { Network } from "lucide-react";
import { api } from "@/lib/api";
import { NetworkForceGraph } from "@/components/NetworkForceGraph";
import { PageHeader, EmptyState } from "@/components/ui/Panel";
import { QueryError } from "@/components/ui/QueryError";
import { TableSkeleton } from "@/components/ui/Skeleton";

interface Node {
  id: string;
  label: string;
  type: string;
  status: string;
  threat_score?: number;
  ip?: string;
}

interface Edge {
  from: string;
  to: string;
}

export default function NetworkPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["network-topology"],
    queryFn: () => api<{ nodes: Node[]; edges: Edge[] }>("/api/v1/network/topology"),
    staleTime: 30_000,
  });

  const nodes = data?.nodes ?? [];
  const edges = data?.edges ?? [];

  return (
    <div className="space-y-6">
      <PageHeader title="Network Topology" subtitle="Force-directed view of hosts connected to the SIEM" />
      {isLoading && <TableSkeleton rows={4} />}
      {isError && <QueryError onRetry={() => refetch()} />}
      {!isLoading && !isError && nodes.length === 0 && (
        <EmptyState
          title="No hosts enrolled"
          description="Add hosts and enroll agents to see the network topology."
          icon={<Network className="w-10 h-10 opacity-40" />}
          action="/hosts"
          actionLabel="Add a host"
        />
      )}
      {nodes.length > 0 && <NetworkForceGraph nodes={nodes} edges={edges} />}
      {nodes.length > 0 && (
        <p className="text-xs text-muted text-center">{edges.length} connection(s) · colors reflect host status and threat score</p>
      )}
    </div>
  );
}
