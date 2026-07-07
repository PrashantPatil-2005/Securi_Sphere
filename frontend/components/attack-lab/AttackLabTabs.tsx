"use client";

import { Tabs } from "@/components/ui/Tabs";
import type { AttackLabTab } from "@/lib/types/simulation";

const TABS = [
  { id: "presets" as const, label: "Presets" },
  { id: "custom" as const, label: "Custom" },
  { id: "history" as const, label: "History" },
];

interface Props {
  active: AttackLabTab;
  onChange: (tab: AttackLabTab) => void;
}

export function AttackLabTabs({ active, onChange }: Props) {
  return (
    <Tabs
      tabs={TABS}
      active={active}
      onChange={onChange}
      ariaLabel="Attack Lab sections"
    />
  );
}
