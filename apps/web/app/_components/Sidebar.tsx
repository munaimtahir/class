"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api } from "../../lib/api";
import {
  DEFAULT_BADGE_COUNTS,
  NAV_MODULES,
  getNavContext,
  isItemActive,
  loadNavBadges,
  type NavBadgeCounts,
} from "../../lib/navigation";

type User = { name: string; email: string };

type Props = {
  user: User | null;
};

const DJANGO_ADMIN_URL = "/django-admin/";

function badge(count: number | undefined) {
  if (!count || count <= 0) {
    return null;
  }
  return (
    <span
      style={{
        background: "#ef4444",
        color: "#fff",
        borderRadius: 999,
        fontSize: 10,
        fontWeight: 700,
        padding: "2px 7px",
        minWidth: 20,
        textAlign: "center",
      }}
    >
      {count}
    </span>
  );
}

function createInitialExpanded(pathname: string) {
  const expanded: Record<string, boolean> = {};
  for (const module of NAV_MODULES) {
    const hasActiveItem = module.items.some((item) => isItemActive(pathname, item));
    expanded[module.id] = hasActiveItem || module.id === "workspace" || module.id === "classroom";
  }
  return expanded;
}

function NavLink({
  href,
  label,
  active,
  badgeCount,
}: {
  href: string;
  label: string;
  active: boolean;
  badgeCount?: number;
}) {
  return (
    <Link
      href={href}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 8,
        padding: "8px 12px",
        borderRadius: 7,
        textDecoration: "none",
        fontSize: 13,
        fontWeight: active ? 700 : 500,
        color: active ? "#fff" : "#cbd5e1",
        background: active ? "rgba(99,179,237,0.24)" : "transparent",
        marginBottom: 2,
        marginLeft: 8,
      }}
    >
      <span>{label}</span>
      {badge(badgeCount)}
    </Link>
  );
}

export default function Sidebar({ user }: Props) {
  const pathname = usePathname();
  const router = useRouter();
  const [loggingOut, setLoggingOut] = useState(false);
  const [badges, setBadges] = useState<NavBadgeCounts>(DEFAULT_BADGE_COUNTS);
  const [expanded, setExpanded] = useState<Record<string, boolean>>(() =>
    createInitialExpanded(pathname),
  );

  const navContext = useMemo(() => getNavContext(pathname), [pathname]);

  useEffect(() => {
    setExpanded((current) => {
      const next = { ...current };
      for (const module of NAV_MODULES) {
        const hasActiveItem = module.items.some((item) => isItemActive(pathname, item));
        if (hasActiveItem) {
          next[module.id] = true;
        } else if (!(module.id in next)) {
          next[module.id] = module.id === "workspace" || module.id === "classroom";
        }
      }
      return next;
    });
  }, [pathname]);

  useEffect(() => {
    let cancelled = false;
    const refresh = async () => {
      const latest = await loadNavBadges();
      if (!cancelled) {
        setBadges(latest);
      }
    };
    refresh().catch(() => undefined);
    const id = window.setInterval(() => {
      refresh().catch(() => undefined);
    }, 20000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await api.logout();
    } finally {
      router.push("/");
      router.refresh();
    }
  };

  return (
    <aside
      style={{
        width: 270,
        minWidth: 270,
        background: "#111827",
        color: "#fff",
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
        position: "sticky",
        top: 0,
        height: "100vh",
        overflowY: "auto",
        flexShrink: 0,
        borderRight: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      <div
        style={{
          padding: "20px 16px 12px",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <div style={{ fontWeight: 800, fontSize: 18, letterSpacing: 0.5 }}>CLASS</div>
        <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>
          Workspace Operations
        </div>
        {navContext ? (
          <div
            style={{
              marginTop: 10,
              fontSize: 11,
              color: "#93c5fd",
              borderTop: "1px solid rgba(255,255,255,0.08)",
              paddingTop: 8,
            }}
          >
            {navContext.module} {"\u203A"} {navContext.page}
          </div>
        ) : null}
      </div>

      <nav style={{ padding: "12px 8px 8px" }}>
        {NAV_MODULES.map((module) => {
          const moduleActive = module.items.some((item) => isItemActive(pathname, item));
          const isOpen = !!expanded[module.id];
          return (
            <div key={module.id} style={{ marginBottom: 8 }}>
              <button
                onClick={() =>
                  setExpanded((current) => ({ ...current, [module.id]: !current[module.id] }))
                }
                style={{
                  width: "100%",
                  border: "none",
                  cursor: "pointer",
                  borderRadius: 7,
                  background: moduleActive ? "rgba(30,41,59,0.65)" : "transparent",
                  color: moduleActive ? "#fff" : "#94a3b8",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "8px 10px",
                  fontSize: 12,
                  fontWeight: 700,
                  letterSpacing: 0.2,
                  textTransform: "uppercase",
                }}
              >
                <span>{module.label}</span>
                <span style={{ fontSize: 10 }}>{isOpen ? "▾" : "▸"}</span>
              </button>
              {isOpen ? (
                <div style={{ marginTop: 4 }}>
                  {module.items.map((item) => (
                    <NavLink
                      key={item.href}
                      href={item.href}
                      label={item.label}
                      active={isItemActive(pathname, item)}
                      badgeCount={item.badgeKey ? badges[item.badgeKey] : undefined}
                    />
                  ))}
                </div>
              ) : null}
            </div>
          );
        })}
      </nav>

      <div style={{ padding: "0 8px 10px" }}>
        <div
          style={{
            fontSize: 11,
            fontWeight: 700,
            color: "#64748b",
            padding: "0 10px 6px",
            textTransform: "uppercase",
            letterSpacing: 0.3,
          }}
        >
          System
        </div>
        <a
          href={DJANGO_ADMIN_URL}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: "block",
            padding: "8px 12px",
            borderRadius: 7,
            textDecoration: "none",
            fontSize: 13,
            color: "#cbd5e1",
            marginLeft: 8,
          }}
        >
          Django Admin ↗
        </a>
      </div>

      <div style={{ flex: 1 }} />

      <div
        style={{
          padding: "12px 12px 20px",
          borderTop: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        {user ? (
          <div style={{ marginBottom: 10 }}>
            <div
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: "#e2e8f0",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {user.name}
            </div>
            <div
              style={{
                fontSize: 11,
                color: "#94a3b8",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {user.email}
            </div>
          </div>
        ) : null}
        <button
          onClick={handleLogout}
          disabled={loggingOut}
          style={{
            width: "100%",
            padding: "8px 12px",
            background: loggingOut ? "#374151" : "#dc2626",
            color: "#fff",
            border: "none",
            borderRadius: 7,
            cursor: "pointer",
            fontSize: 13,
            fontWeight: 600,
            textAlign: "left",
          }}
        >
          {loggingOut ? "Logging out…" : "Logout"}
        </button>
      </div>
    </aside>
  );
}
