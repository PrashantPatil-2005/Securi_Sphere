"use client";

import { Drawer } from "./Drawer";
import type { ReactNode } from "react";

interface SheetProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  side?: "left" | "right";
  className?: string;
}

/** Side sheet — wrapper over Drawer for lateral panels. */
export function Sheet({
  open,
  onClose,
  title,
  description,
  children,
  side = "right",
  className,
}: SheetProps) {
  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={title}
      description={description}
      side={side}
      className={className}
    >
      {children}
    </Drawer>
  );
}
