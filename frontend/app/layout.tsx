import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";
import { ThemeScript } from "@/components/ThemeScript";
import { inter } from "@/lib/fonts";

import { PRODUCT_NAME } from "@/lib/brand";

export const metadata: Metadata = {
  title: `${PRODUCT_NAME} | Enterprise Security Operations`,
  description: "Enterprise-grade security monitoring and threat detection platform",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const nonce = (await headers()).get("x-nonce") ?? undefined;

  return (
    <html lang="en" suppressHydrationWarning className={inter.variable}>
      <head>
        <ThemeScript nonce={nonce} />
      </head>
      <body className="antialiased min-h-screen bg-background text-foreground font-sans">
        {children}
      </body>
    </html>
  );
}
