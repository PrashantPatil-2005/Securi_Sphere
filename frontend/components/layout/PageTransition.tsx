"use client";

import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { useTheme } from "@/lib/theme/ThemeProvider";

export function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { reducedMotion } = useTheme();

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
