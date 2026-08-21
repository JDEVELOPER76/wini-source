import { useEffect, useRef, useState, useCallback } from "react";
import { Terminal as XTerm } from "xterm";
import { FitAddon } from "@xterm/addon-fit";
import "xterm/css/xterm.css";

const DEFAULT_WS_URL = "ws://localhost:4001";

const STATUS_META = {
  connected: { color: "#51CF66", label: "Conectado" },
  connecting: { color: "#FFA94D", label: "Conectando…" },
  disconnected: { color: "#6C7086", label: "Desconectado" },
  error: { color: "#F38BA8", label: "Error de conexión" },
};

const inputStyle = {
  background: "#1E1E2E",
  border: "1px solid #313244",
  borderRadius: 3,
  color: "#CDD6F4",
  fontSize: 11,
  padding: "3px 6px",
};

const btnStyle = {
  background: "#313244",
  color: "#CDD6F4",
  border: "1px solid #45475A",
  borderRadius: 3,
  cursor: "pointer",
  fontSize: 11,
  padding: "3px 8px",
  flexShrink: 0,
};

export default function TerminalPanel({ height, onClose, onResizeStart }) {
  const containerRef = useRef(null);
  const xtermRef = useRef(null);
  const fitAddonRef = useRef(null);
  const wsRef = useRef(null);

  const [status, setStatus] = useState("disconnected");
  const [wsUrl, setWsUrl] = useState(DEFAULT_WS_URL);
  const [cwdInput, setCwdInput] = useState("");

  const sendResize = useCallback(() => {
    const term = xtermRef.current;
    const ws = wsRef.current;
    if (!term || !ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows }));
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.onclose = null; // evitar log doble al reconectar a mano
      wsRef.current.close();
      wsRef.current = null;
    }
    let url;
    try {
      url = new URL(wsUrl);
    } catch {
      xtermRef.current?.writeln("\r\n\x1b[31mURL de WebSocket inválida.\x1b[0m");
      setStatus("error");
      return;
    }
    if (cwdInput.trim()) url.searchParams.set("cwd", cwdInput.trim());

    setStatus("connecting");
    const ws = new WebSocket(url.toString());
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      requestAnimationFrame(() => {
        fitAddonRef.current?.fit();
        sendResize();
      });
    };

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "data") xtermRef.current?.write(msg.data);
      } catch {
        xtermRef.current?.write(ev.data);
      }
    };

    ws.onclose = () => {
      setStatus("disconnected");
      xtermRef.current?.writeln(
        "\r\n\x1b[31mDesconectado. ¿Está corriendo el servidor de terminal? (npm start en terminal-server/)\x1b[0m"
      );
    };

    ws.onerror = () => setStatus("error");
  }, [wsUrl, cwdInput, sendResize]);

  // Crear la instancia de xterm una sola vez
  useEffect(() => {
    const term = new XTerm({
      convertEol: true,
      fontFamily: "Fira Code, 'Cascadia Code', Consolas, monospace",
      fontSize: 13,
      cursorBlink: true,
      theme: {
        background: "#11111b",
        foreground: "#CDD6F4",
        cursor: "#F5E0DC",
        selectionBackground: "#45475A",
      },
    });
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(containerRef.current);
    fitAddon.fit();

    term.onData((data) => {
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "input", data }));
      }
    });

    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    const resizeObserver = new ResizeObserver(() => {
      fitAddon.fit();
      sendResize();
    });
    resizeObserver.observe(containerRef.current);

    connect();

    return () => {
      resizeObserver.disconnect();
      term.dispose();
      wsRef.current?.close();
      wsRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Reajustar tamaño cuando cambia la altura del panel (drag del divisor)
  useEffect(() => {
    fitAddonRef.current?.fit();
    sendResize();
  }, [height, sendResize]);

  const meta = STATUS_META[status] || STATUS_META.disconnected;

  return (
    <div style={{ height, display: "flex", flexDirection: "column", background: "#11111b", flexShrink: 0 }}>
      <div
        onMouseDown={onResizeStart}
        title="Arrastrá para cambiar el tamaño"
        style={{ height: 4, cursor: "row-resize", background: "#313244", flexShrink: 0 }}
      />
      <div
        style={{
          display: "flex", alignItems: "center", gap: 8,
          padding: "5px 10px", background: "#181825", borderBottom: "1px solid #313244",
          fontSize: 12, color: "#9399b2", flexShrink: 0,
        }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: 5, fontWeight: 600, color: "#CDD6F4", flexShrink: 0 }}>
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: meta.color, display: "inline-block" }} />
          TERMINAL — {meta.label}
        </span>
        <input
          value={wsUrl}
          onChange={(e) => setWsUrl(e.target.value)}
          placeholder="ws://localhost:4001"
          style={{ ...inputStyle, width: 150 }}
        />
        <input
          value={cwdInput}
          onChange={(e) => setCwdInput(e.target.value)}
          placeholder="Ruta de inicio (opcional), ej: /home/tu/proyecto"
          style={{ ...inputStyle, flex: 1, minWidth: 140 }}
        />
        <button onClick={connect} style={btnStyle}>Reconectar</button>
        <button onClick={onClose} style={btnStyle}>Cerrar</button>
      </div>
      <div ref={containerRef} style={{ flex: 1, minHeight: 0, padding: "4px 8px" }} />
    </div>
  );
}