"use client";

import { memo } from "react";
import { Server, Globe, FileCode2, Crosshair, Target } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { Card, CardHeader } from "@/components/design-system";
import type { Alert, AlertHost } from "@/lib/types/alert";

interface AlertInfoGridProps {
  alert: Alert;
  host: AlertHost;
}

interface InfoField {
  label: string;
  value: string;
  icon: React.ReactNode;
  mono?: boolean;
}

function AlertInfoGridInner({ alert, host }: AlertInfoGridProps) {
  const fields: InfoField[] = [];

  fields.push({
    label: "Host",
    value: host.hostname || host.name,
    icon: <Server className="w-3.5 h-3.5" />,
  });

  if (host.ip_address) {
    fields.push({
      label: "Source IP",
      value: host.ip_address,
      icon: <Globe className="w-3.5 h-3.5" />,
      mono: true,
    });
  }

  if (alert.rule_id) {
    fields.push({
      label: "Detection Rule",
      value: alert.rule_id,
      icon: <FileCode2 className="w-3.5 h-3.5" />,
    });
  }

  if (alert.source) {
    fields.push({
      label: "Source",
      value: alert.source,
      icon: <Crosshair className="w-3.5 h-3.5" />,
    });
  }

  if (alert.mitre_technique_id) {
    fields.push({
      label: "MITRE Technique",
      value: alert.mitre_technique_id,
      icon: <Target className="w-3.5 h-3.5" />,
    });
  }

  return (
    <Card>
      <CardHeader title="Alert Details" />
      <div className="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {fields.map((field) => (
            <div key={field.label} className="space-y-1">
              <div className="flex items-center gap-1.5 text-muted">
                {field.icon}
                <span className="text-[10px] font-semibold uppercase tracking-wider">
                  {field.label}
                </span>
              </div>
              <p
                className={cn(
                  "text-sm text-foreground",
                  field.mono && "code-text",
                )}
              >
                {field.value}
              </p>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

export const AlertInfoGrid = memo(AlertInfoGridInner);
