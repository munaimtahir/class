"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Sidebar from "./Sidebar";
import { api } from "../../lib/api";

type User = { name: string; email: string };

type Props = {
  children: React.ReactNode;
};

export default function AppShell({ children }: Props) {
  const [user, setUser] = useState<User | null>(null);
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const pathname = usePathname();
  const router = useRouter();

  const isHome = pathname === "/";

  useEffect(() => {
    api.authStatus()
      .then((status) => {
        if (status.authenticated && status.user) {
          setUser(status.user);
          setAuthenticated(true);
          return;
        }

        setAuthenticated(false);
        if (!isHome) {
          // Redirect unauthenticated users to the login screen
          router.replace("/");
        }
      })
      .catch(() => {
        setAuthenticated(false);
        if (!isHome) {
          router.replace("/");
        }
      });
  }, [pathname, router, isHome]);

  // While checking auth on protected pages, show a brief loading state
  if (authenticated === null && !isHome) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", background: "#f8fafc" }}>
        <div style={{ color: "#64748b", fontSize: 14 }}>Checking authentication…</div>
      </div>
    );
  }

  // Unauthenticated on home page: no sidebar, just the login screen
  if (!authenticated && isHome) {
    return <>{children}</>;
  }

  // Authenticated (any page) or still resolving home page: show sidebar layout
  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#f1f5f9" }}>
      <Sidebar user={user} />
      <main style={{
        flex: 1,
        minWidth: 0,
        overflowX: "auto",
        padding: "24px 32px",
      }}>
        {children}
      </main>
    </div>
  );
}
