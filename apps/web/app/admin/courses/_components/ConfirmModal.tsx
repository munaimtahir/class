"use client";

type Props = {
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export default function ConfirmModal({
  title,
  message,
  confirmLabel = "Confirm",
  danger = false,
  onConfirm,
  onCancel,
}: Props) {
  return (
    <div
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)",
        display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
      }}
      onClick={onCancel}
    >
      <div
        style={{
          background: "#fff", borderRadius: 10, padding: 28, maxWidth: 420, width: "90%",
          boxShadow: "0 8px 30px rgba(0,0,0,0.18)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ margin: "0 0 10px", color: danger ? "#dc2626" : "#111" }}>{title}</h3>
        <p style={{ margin: "0 0 22px", color: "#555", fontSize: 14 }}>{message}</p>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <button
            onClick={onCancel}
            style={{ padding: "8px 18px", border: "1px solid #d1d5db", borderRadius: 6, background: "#fff", cursor: "pointer" }}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            style={{
              padding: "8px 18px", border: "none", borderRadius: 6, cursor: "pointer",
              background: danger ? "#dc2626" : "#2563eb", color: "#fff", fontWeight: 600,
            }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
