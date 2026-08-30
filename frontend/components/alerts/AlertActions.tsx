"use client";

import { memo } from "react";
import Link from "next/link";
import {
  Play,
  CheckCircle2,
  XCircle,
  RotateCcw,
  ExternalLink,
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  Cpu,
  Activity,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { Button, Card, CardHeader } from "@/components/design-system";
import type { Alert } from "@/lib/types/alert";

interface AlertActionsProps {
  alert: Alert;
  hostId: string;
  onStatusChange: (id: string, status: string) => void;
  onFeedback: (label: "false_positive" | "true_positive") => void;
  isUpdating?: boolean;
  isFeedbackPending?: boolean;
  onAskAi?: () => void;
}

function AlertActionsInner({
  alert,
  hostId,
  onStatusChange,
  onFeedback,
  isUpdating = false,
  isFeedbackPending = false,
  onAskAi,
}: AlertActionsProps) {
  const statusActions: { label: string; target: string; variant: "primary" | "danger" | "outline"; icon: React.ReactNode }[] = [];

  switch (alert.status) {
    case "open":
      statusActions.push(
        {
          label: "Start Investigation",
          target: "investigating",
          variant: "primary",
          icon: <Play className="w-3.5 h-3.5" />,
        },
        {
          label: "Resolve",
          target: "resolved",
          variant: "danger",
          icon: <CheckCircle2 className="w-3.5 h-3.5" />,
        },
      );
      break;
    case "investigating":
      statusActions.push(
        {
          label: "Resolve",
          target: "resolved",
          variant: "primary",
          icon: <CheckCircle2 className="w-3.5 h-3.5" />,
        },
        {
          label: "Close",
          target: "closed",
          variant: "danger",
          icon: <XCircle className="w-3.5 h-3.5" />,
        },
      );
      break;
    case "resolved":
      statusActions.push({
        label: "Reopen",
        target: "open",
        variant: "outline",
        icon: <RotateCcw className="w-3.5 h-3.5" />,
      });
      break;
    case "closed":
      statusActions.push({
        label: "Reopen",
        target: "open",
        variant: "outline",
        icon: <RotateCcw className="w-3.5 h-3.5" />,
      });
      break;
  }

  return (
    <Card>
      <CardHeader title="Actions" />
      <div className="p-4 space-y-4">
        {/* Status transitions */}
        <div className="space-y-2">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">
            Status
          </span>
          <div className="flex flex-wrap gap-2">
            {statusActions.map((action) => (
              <Button
                key={action.target}
                variant={action.variant}
                size="sm"
                loading={isUpdating}
                icon={action.icon}
                onClick={() => onStatusChange(alert.id, action.target)}
              >
                {action.label}
              </Button>
            ))}
          </div>
        </div>

        {/* Feedback */}
        <div className="space-y-2">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">
            Feedback
          </span>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              loading={isFeedbackPending}
              icon={<ThumbsUp className="w-3.5 h-3.5" />}
              onClick={() => onFeedback("true_positive")}
            >
              Mark true positive
            </Button>
            <Button
              variant="outline"
              size="sm"
              loading={isFeedbackPending}
              icon={<ThumbsDown className="w-3.5 h-3.5" />}
              onClick={() => onFeedback("false_positive")}
            >
              Mark false positive
            </Button>
          </div>
        </div>

        {/* AI */}
        {onAskAi && (
          <div className="space-y-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">
              AI
            </span>
            <div>
              <Button
                variant="outline"
                size="sm"
                icon={<Cpu className="w-3.5 h-3.5" />}
                onClick={onAskAi}
              >
                Ask AI
              </Button>
            </div>
          </div>
        )}

        {/* Navigation links */}
        <div className="space-y-2">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">
            Investigate
          </span>
          <div className="flex flex-col gap-1.5">
            <Link
              href={`/events?host_id=${hostId}`}
              className={cn(
                "inline-flex items-center gap-2 text-xs font-medium",
                "text-muted hover:text-foreground transition-colors",
              )}
            >
              <Activity className="w-3.5 h-3.5" />
              All host events
              <ExternalLink className="w-3 h-3 opacity-40" />
            </Link>
            <Link
              href={`/timeline?host=${hostId}`}
              className={cn(
                "inline-flex items-center gap-2 text-xs font-medium",
                "text-muted hover:text-foreground transition-colors",
              )}
            >
              <FileText className="w-3.5 h-3.5" />
              Full timeline
              <ExternalLink className="w-3 h-3 opacity-40" />
            </Link>
            <Link
              href={`/investigation?alert=${alert.id}`}
              className={cn(
                "inline-flex items-center gap-2 text-xs font-medium",
                "text-muted hover:text-foreground transition-colors",
              )}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              Open Case Workspace
              <ExternalLink className="w-3 h-3 opacity-40" />
            </Link>
          </div>
        </div>
      </div>
    </Card>
  );
}

export const AlertActions = memo(AlertActionsInner);
