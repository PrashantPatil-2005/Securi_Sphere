"use client";

import { useEffect, useState } from "react";
import { useSecurityFeed } from "@/lib/websocket";
import { EmotionBanner, ProgressSteps } from "@/components/ui/EmotionState";
import { useToast } from "@/components/ui/Toast";

interface LiveAttackBannerProps {
  hostName: string;
  hostId: string;
}

function LiveAttackBanner({ hostName, hostId }: LiveAttackBannerProps) {
  const { feedItems, isConnected } = useSecurityFeed();
  const [attackState, setAttackState] = useState<{
    stage: "BRUTE_FORCE" | "ACCESS_GAINED" | "PRIVILEGE_ESCALATION" | "IMPACT" | "COMPROMISE_CONFIRMED";
    failedCount: number;
    totalThreshold: number;
    successSeen: boolean;
    sudoSeen: boolean;
    serviceStopSeen: boolean;
    lastUpdate: string;
  }>({
    stage: "BRUTE_FORCE",
    failedCount: 0,
    totalThreshold: 10,
    successSeen: false,
    sudoSeen: false,
    serviceStopSeen: false,
    lastUpdate: "",
  });

  useEffect(() => {
    if (!isConnected) return;

    // Filter recent SSH auth events for this host
    const sshEvents = feedItems
      .filter(
        (item) =>
          item.host_id === hostId &&
          (item.event_type === "ssh_login_failure" ||
            item.event_type === "ssh_login_success" ||
            item.event_type === "sudo_usage")
      )
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

    let failedCount = 0;
    let successSeen = false;
    let sudoSeen = false;
    let serviceStopSeen = false;

    for (const event of sshEvents) {
      if (event.event_type === "ssh_login_failure") {
        failedCount += 1;
      } else if (event.event_type === "ssh_login_success") {
        successSeen = true;
      } else if (event.event_type === "sudo_usage") {
        sudoSeen = true;
      }
    }

    // Determine attack stage
    let stage:
      | "BRUTE_FORCE"
      | "ACCESS_GAINED"
      | "PRIVILEGE_ESCALATION"
      | "IMPACT"
      | "COMPROMISE_CONFIRMED";

    if (successSeen && sudoSeen) {
      stage = "IMPACT";
    } else if (successSeen) {
      stage = "ACCESS_GAINED";
    } else if (failedCount >= (attackState.totalThreshold || 10)) {
      stage = "BRUTE_FORCE";
    } else {
      stage = "BRUTE_FORCE";
    }

    setAttackState({
      stage,
      failedCount,
      totalThreshold: attackState.totalThreshold,
      successSeen,
      sudoSeen,
      serviceStopSeen,
      lastUpdate: new Date().toISOString(),
    });
  }, [feedItems, isConnected, hostId]);

  // Render progress steps based on stage
  const stages: string[] = [];
  const currentIndex: number = [];

  if (attackState.stage === "COMPROMISE_CONFIRMED") {
    stages.push("Brute force", "Access gained", "Privilege escalation", "Impact confirmed");
    currentIndex.push(3);
  } else if (attackState.stage === "IMPACT") {
    stages.push("Brute force", "Access gained", "Privilege escalation", "Impact");
    currentIndex.push(3);
  } else if (attackState.stage === "PRIVILEGE_ESCALATION") {
    stages.push("Brute force", "Access gained", "Privilege escalation");
    currentIndex.push(2);
  } else if (attackState.stage === "ACCESS_GAINED") {
    stages.push("Brute force", "Access gained");
    currentIndex.push(1);
  } else {
    stages.push("Brute force");
    currentIndex.push(0);
  }

  // Get progress text
  const getProgressText = () => {
    if (attackState.stage === "COMPROMISE_CONFIRMED") {
      return "Attack compromise confirmed — SSH account takeover";
    }
    if (attackState.stage === "BRUTE_FORCE") {
      return `Failing logins (${attackState.failedCount}/${attackState.totalThreshold}) → waiting for success`;
    }
    if (attackState.stage === "ACCESS_GAINED") {
      return "Success achieved → waiting for privilege escalation";
    }
    if (attackState.stage === "PRIVILEGE_ESCALATION") {
      return "Privilege escalation detected → waiting for impact";
    }
    if (attackState.stage === "IMPACT") {
      return "Impact activity detected";
    }
    return "";
  };

  // Get banner title and tone
  const getBannerInfo = () => {
    if (attackState.stage === "COMPROMISE_CONFIRMED") {
      return {
        title: "ATTACK COMPROMISED — SSH account takeover on " + hostName,
        tone: "success" as const,
      };
    }
    if (attackState.stage === "BRUTE_FORCE") {
      return {
        title: "ATTACK IN PROGRESS — SSH brute force on " + hostName,
        tone: "urgency" as const,
      };
    }
    if (attackState.stage === "ACCESS_GAINED") {
      return {
        title: "ACCESS GAINED — Successful login detected on " + hostName,
        tone: "urgency" as const,
      };
    }
    if (attackState.stage === "PRIVILEGE_ESCALATION") {
      return {
        title: "PRIVILEGE ESCALATION DETECTED on " + hostName,
        tone: "confidence" as const,
      };
    }
    if (attackState.stage === "IMPACT") {
      return {
        title: "IMPACT ACTIVITY DETECTED on " + hostName,
        tone: "urgency" as const,
      };
    }
    return {
      title: "SECURITY ALERT — " + hostName,
      tone: "calm" as const,
    };
  };

  const { title, tone } = getBannerInfo();

  if (!isConnected) {
    return null;
  }

  return (
    <EmotionBanner tone={tone} title={title}>
      <ProgressSteps steps={stages} currentIndex={currentIndex[0]} />
      <p className="mt-2 text-sm text-muted line-clamp-2">
        {getProgressText()}
      </p>
    </EmotionBanner>
  );
}

export function useLiveAttackBanner(hostId: string, hostName: string) {
  return <LiveAttackBanner hostName={hostName} hostId={hostId} />;
}