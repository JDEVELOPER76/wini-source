import { useEffect, useRef, useState } from "react";

const overlayStyle = {
  position: "fixed", inset: 0, background: "rgba(17,17,27,0.6)",
  display: "flex", alignItems: "center", justifyContent: "center",
  zIndex: 2000,
};

const boxStyle = {
  background: "#1E1E2E", border: "1px solid #313244", borderRadius: 6,
  minWidth: 320, maxWidth: 420, padding: 18,
  boxShadow: "0 8px 24px rgba(0,0,0,0.5)", color: "#CDD6F4", fontSize: 13,
};

const inputStyle = {
  width: "100%", boxSizing: "border-box", background: "#11111b",
  border: "1px solid #45475A", borderRadius: 4, color: "#CDD6F4",
  padding: "7px 9px", fontSize: 13, marginBottom: 16, outline: "none",
};

const cancelBtnStyle = {
  background: "#313244", color: "#CDD6F4", border: "1px solid #45475A",
  borderRadius: 4, cursor: "pointer", padding: "6px 14px", fontSize: 12.5,
};

const confirmBtnStyle = {
  background: "#89b4fa", color: "#11111b", border: "1px solid #89b4fa",
  borderRadius: 4, cursor: "pointer", padding: "6px 14px", fontSize: 12.5, fontWeight: 600,
};

const dangerBtnStyle = {
  ...confirmBtnStyle, background: "#F38BA8", border: "1px solid #F38BA8",
};

/**
 * Modal genérico para alert / confirm / prompt, todo en la misma página
 * (sin usar window.alert / window.confirm / window.prompt del navegador).
 *
 * `dialog` tiene la forma:
 *   { type: "alert" | "confirm" | "prompt", title, message, defaultValue?, danger?, resolve }
 */
export default function DialogModal({ dialog }) {
  const [value, setValue] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    setValue(dialog?.defaultValue || "");
  }, [dialog]);

  useEffect(() => {
    if (dialog?.type === "prompt" && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [dialog]);

  if (!dialog) return null;

  const cancel = () => {
    if (dialog.type === "alert") dialog.resolve();
    else if (dialog.type === "confirm") dialog.resolve(false);
    else dialog.resolve(null);
  };

  const confirm = () => {
    if (dialog.type === "alert") dialog.resolve();
    else if (dialog.type === "confirm") dialog.resolve(true);
    else dialog.resolve(value);
  };

  return (
    <div
      style={overlayStyle}
      onMouseDown={(e) => { if (e.target === e.currentTarget) cancel(); }}
      onKeyDown={(e) => {
        if (e.key === "Escape") cancel();
        if (e.key === "Enter" && dialog.type !== "prompt") confirm();
      }}
      tabIndex={-1}
    >
      <div style={boxStyle} onMouseDown={(e) => e.stopPropagation()}>
        <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 14 }}>{dialog.title}</div>
        <div style={{ marginBottom: dialog.type === "prompt" ? 10 : 16, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
          {dialog.message}
        </div>
        {dialog.type === "prompt" && (
          <input
            ref={inputRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") { e.preventDefault(); confirm(); }
              if (e.key === "Escape") { e.preventDefault(); cancel(); }
            }}
            style={inputStyle}
          />
        )}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          {dialog.type !== "alert" && (
            <button onClick={cancel} style={cancelBtnStyle}>Cancelar</button>
          )}
          <button onClick={confirm} style={dialog.danger ? dangerBtnStyle : confirmBtnStyle} autoFocus>
            {dialog.type === "confirm" ? (dialog.confirmLabel || "Confirmar") : "Aceptar"}
          </button>
        </div>
      </div>
    </div>
  );
}