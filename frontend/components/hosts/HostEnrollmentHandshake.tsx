"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, Wifi } from "lucide-react";
import { EmotionBanner } from "@/components/ui/EmotionState";
import { useWsMessages } from "@/lib/websocket";
import { useUxEnabled } from "@/lib/featureFlags";
import { track } from "@/lib/telemetry";

type HandshakeState = "waiting" | "enrolled" | "online" | "timeout";

interface Props {
  hostId: string;
  hostName: string;
  onSuccess?: () => void;
}

export function HostEnrollmentHandshake({ hostId, hostName, onSuccess }: Props) {
  const enabled = useUxEnabled("ux_enrollment_handshake_enabled");
  const [state, setState] = useState<HandshakeState>("waiting");
  const [startedAt] = useState(() => Date.now());

  useEffect(() => {
    if (!enabled) return;
    track("host_enrollment_started", { host_id: hostId });
  }, [enabled, hostId]);

  useWsMessages(["host_enrolled", "host_status"], (msg) => {
    if (!enabled) return;
    const data = msg.data;
    if (String(data.id) !== hostId) return;

    if (msg.type === "host_enrolled" || data.enrolled === true) {
      setState("enrolled");
    }
    if (data.status === "online") {
      setState("online");
      track("host_enrollment_success", {
        host_id: hostId,
        time_to_online_ms: Date.now() - startedAt,
      });
      onSuccess?.();
    }
  });

  useEffect(() => {
    if (!enabled || state === "online") return;
    const timer = setTimeout(() => {
      if (state === "waiting") setState("timeout");
    }, 120_000);
    return () => clearTimeout(timer);
  }, [enabled, state]);

  if (!enabled) return null;

  const copy: Record<HandshakeState, { tone: "calm" | "progress" | "success" | "urgency"; title: string; message: string }> = {
    waiting: {
      tone: "progress",
      title: `Waiting for ${hostName}`,
      message: "Run the install command on your VM. We'll detect the agent automatically — usually within 30 seconds.",
    },
    enrolled: {
      tone: "calm",
      title: "Agent enrolled",
      message: "Registration succeeded. Waiting for first heartbeat to mark the host online.",
    },
    online: {
      tone: "success",
      title: `${hostName} is online`,
      message: "Agent connected successfully. You can close this dialog or explore the dashboard.",
    },
    timeout: {
      tone: "urgency",
      title: "Still waiting for agent",
      message: "No connection yet. Verify network access, run as root, and check docs/AGENT_INSTALL.md.",
    },
  };

  const { tone, title, message } = copy[state];

  return (
    <div className="space-y-2">
      <EmotionBanner tone={tone} title={title} message={message} />
      <div className="flex items-center gap-2 text-xs text-muted">
        {state === "online" ? (
          <CheckCircle2 className="w-3.5 h-3.5 text-success" />
        ) : state === "timeout" ? (
          <Wifi className="w-3.5 h-3.5 text-warning" />
        ) : (
          <Loader2 className="w-3.5 h-3.5 animate-spin text-accent" />
        )}
        <span className="capitalize">{state.replace("_", " ")}</span>
      </div>
    </div>
  );
}
