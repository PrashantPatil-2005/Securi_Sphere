"use client";

import { memo, useCallback } from "react";
import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { Drawer } from "@/components/ui/Drawer";
import { EventMetadata } from "./EventMetadata";
import { EventRawJson } from "./EventRawJson";
import { EventRelatedObjects } from "./EventRelatedObjects";
import type { EventSummary } from "@/lib/types/event";

interface EventDetailDrawerProps {
  event: EventSummary | null;
  open: boolean;
  onClose: () => void;
}

function EventDetailDrawerInner({ event, open, onClose }: EventDetailDrawerProps) {
  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);



  return (
    <Drawer
      open={open}
      onClose={handleClose}
      title="Event Details"
      description={event?.event_type}
    >
      {event && (
        <div className="space-y-6">
          {/* Event metadata */}
          <EventMetadata event={event} />

          {/* Separator */}
          <div className="border-t border-border-subtle" />

          {/* Raw log */}
          <EventRawJson data={event.raw_log} label="Raw Log" />

          {/* Separator */}
          <div className="border-t border-border-subtle" />

          {/* Related objects (placeholder — backend does not yet expose these) */}
          <EventRelatedObjects />

          {/* Navigation links */}
          <div className="border-t border-border-subtle pt-4 space-y-2">
            <Link
              href={`/events?host_id=${event.host_id}`}
              onClick={handleClose}
              className="flex items-center gap-2 text-xs text-accent hover:text-accent/80 transition-colors"
            >
              <ExternalLink className="w-3 h-3" />
              View all events for this host
            </Link>
          </div>
        </div>
      )}
    </Drawer>
  );
}

export const EventDetailDrawer = memo(EventDetailDrawerInner);
