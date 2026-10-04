import "./globals.css";
import type { Metadata } from "next";
import AppShell from "./_components/AppShell";

export const metadata: Metadata = {
  title: "CLASS — Workspace Operations",
  description: "Google Classroom Schedule Integrator & Workspace Operations Console",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "system-ui, -apple-system, sans-serif" }}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}

