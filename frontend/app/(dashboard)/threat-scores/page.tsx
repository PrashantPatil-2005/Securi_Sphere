"use client";

import { useState } from "react";
import { PageHeader } from "@/components/ui/Panel";
import { ThreatScoresPanel } from "@/components/analytics/ThreatScoresPanel";
import { HostRiskDrawer } from "@/components/HostRiskDrawer";

export default function ThreatScoresPage() {
  const [riskDrawerHostId, setRiskDrawerHostId] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Threat scores"
        subtitle="Host risk ranking from alerts, severity, and health signals — click a host for details"
      />
      <ThreatScoresPanel showFactors onSelectHost={(id) => setRiskDrawerHostId(id)} />
      <HostRiskDrawer hostId={riskDrawerHostId} onClose={() => setRiskDrawerHostId(null)} />
    </div>
  );
}
