"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { useTheme } from "@/lib/theme/ThemeProvider";
import { trackBatched } from "@/lib/telemetry";

export function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { reducedMotion } = useTheme();
  const enteredAt = useRef(Date.now());

  useEffect(() => {
    enteredAt.current = Date.now();
    return () => {
      const dwellMs = Date.now() - enteredAt.current;
      if (dwellMs > 3000) {
        trackBatched("page_dwell", { path: pathname, dwell_ms: dwellMs });
      }
    };
  }, [pathname]);

  if (reducedMotion) {
    return <>{children}</>;
  }

  return (
    <motion.div
      key={pathname}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.15, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}
