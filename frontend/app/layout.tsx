import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mini SIEM | Securi",
  description: "Lightweight Security Monitoring Platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen">{children}</body>
    </html>
  );
}
