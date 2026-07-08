"use client";

import { useState } from "react";
import { PageHeader } from "@/components/ui/Panel";
import { Tabs, TabPanel } from "@/components/ui/Tabs";
import { BuildingBlocksPanel, ReferenceSetsPanel } from "@/components/intel/IntelPanels";
import { IntelFeedOpsPanel } from "@/components/intel/IntelFeedOpsPanel";

type IntelTab = "reference" | "blocks";

const TABS = [
  { id: "reference" as const, label: "Reference sets", panelId: "intel-panel-reference" },
  { id: "blocks" as const, label: "Building blocks", panelId: "intel-panel-blocks" },
];

export default function IntelPage() {
  const [tab, setTab] = useState<IntelTab>("reference");

  return (
    <div className="space-y-6">
      <PageHeader
        title="Threat Intel"
        subtitle="Reference sets and building blocks — QRadar-style watchlists and reusable SIEM queries"
      />
      <Tabs
        tabs={TABS}
        active={tab}
        onChange={setTab}
        variant="pill"
        ariaLabel="Threat intel sections"
      />
      {tab === "reference" && (
        <TabPanel id="intel-panel-reference" labelledBy="tab-reference">
          <div className="space-y-6">
            <IntelFeedOpsPanel />
            <ReferenceSetsPanel />
          </div>
        </TabPanel>
      )}
      {tab === "blocks" && (
        <TabPanel id="intel-panel-blocks" labelledBy="tab-blocks">
          <BuildingBlocksPanel />
        </TabPanel>
      )}
    </div>
  );
}
