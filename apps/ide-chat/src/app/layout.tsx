import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IDE Chat — Agentic AI Platform",
  description: "Developer chat interface for the enterprise agentic AI platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full bg-ide-bg text-ide-text antialiased">{children}</body>
    </html>
  );
}
