"use client";

export interface AlertRule {
  id: string;
  name: string;
  rule_type: string;
  threshold: number | null;
  window_minutes: number | null;
  severity: string;
  enabled: boolean;
  false_positive_count: number;
  true_positive_count: number;
}
