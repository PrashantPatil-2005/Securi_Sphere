"use client";

import dynamic from "next/dynamic";
import { Radio } from "lucide-react";
import { Panel } from "@/components/ui/Panel";
import { cn } from "@/lib/utils/cn";

const LiveSecurityFeed = dynamic(() => import("@/components/LiveSecurityFeed"), { ssr: false });

interface Props {
  running: boolean;
}

export function SimulationFeed({ running }: Props) {
  return (
    <Panel title="Live security feed">
      <div className="flex items-center gap-2 text-sm text-muted mb-3">
        <Radio className={cn("w-4 h-4", running ? "text-accent animate-pulse" : "text-muted")} />
        {running
          ? "Injecting simulated events — updates appear below in real time."
          : "Simulated events broadcast to the live feed. Run a scenario to see updates."}
      </div>
      <LiveSecurityFeed maxItems={20} />
    </Panel>
  );
}
