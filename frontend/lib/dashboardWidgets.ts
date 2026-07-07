export const DASHBOARD_WIDGET_LABELS: Record<string, string> = {
  kpis: "Executive KPIs",
  onboarding: "Onboarding checklist",
  timeline: "Security timeline",
  risky_hosts: "Host risk ranking",
  attack_timelines: "Attack timelines",
  live_feed: "Live security feed",
};

export function widgetLabel(id: string): string {
  if (id.startsWith("saved_search:")) return "Saved search";
  return DASHBOARD_WIDGET_LABELS[id] ?? id;
}

export function isSavedSearchWidget(id: string): boolean {
  return id.startsWith("saved_search:");
}

export function savedSearchIdFromWidget(id: string): string | null {
  return isSavedSearchWidget(id) ? id.slice("saved_search:".length) : null;
}
