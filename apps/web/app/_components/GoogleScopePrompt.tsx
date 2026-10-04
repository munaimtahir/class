"use client";

import { useState } from "react";
import { api, type ApiError } from "../../lib/api";

type Props = {
  error: ApiError;
  actionLabel?: string;
};

export default function GoogleScopePrompt({
  error,
  actionLabel = "Reconnect Google",
}: Props) {
  const [busy, setBusy] = useState(false);
  const [localError, setLocalError] = useState("");

  const handleReconnect = async () => {
    setBusy(true);
    setLocalError("");
    try {
      if (error.reauthorizeUrl) {
        window.location.href = error.reauthorizeUrl;
        return;
      }
      const start = await api.authStart({ mode: "upgrade", upgrade: error.feature });
      window.location.href = start.auth_url;
    } catch (exc: unknown) {
      setLocalError(exc instanceof Error ? exc.message : "Failed to begin reconnect flow.");
      setBusy(false);
    }
  };

  return (
    <div
      style={{
        marginTop: 10,
        border: "1px solid #fbbf24",
        background: "#fffbeb",
        borderRadius: 8,
        padding: "10px 12px",
      }}
    >
      <div style={{ fontSize: 13, color: "#92400e" }}>
        Additional Google permission is required for this action.
      </div>
      {error.feature ? (
        <div style={{ fontSize: 12, color: "#78350f", marginTop: 4 }}>
          Blocked action: <b>{error.feature}</b>
        </div>
      ) : null}
      {error.missingScopes && error.missingScopes.length > 0 ? (
        <div style={{ fontSize: 12, color: "#78350f", marginTop: 4 }}>
          Missing scopes: {error.missingScopes.join(", ")}
        </div>
      ) : null}
      <button
        onClick={handleReconnect}
        disabled={busy}
        style={{
          marginTop: 8,
          border: "none",
          borderRadius: 6,
          padding: "7px 10px",
          background: "#b45309",
          color: "#fff",
          cursor: "pointer",
          fontSize: 12,
          fontWeight: 600,
        }}
      >
        {busy ? "Starting reconnect…" : actionLabel}
      </button>
      {localError ? (
        <div style={{ fontSize: 12, color: "#b91c1c", marginTop: 6 }}>{localError}</div>
      ) : null}
    </div>
  );
}
