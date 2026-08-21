// Servidor de terminal real para el Editor Wini.
//
// Abre un WebSocket local que, por cada conexión, lanza un proceso de shell
// de verdad (bash/zsh/powershell) con node-pty y transmite su entrada/salida.
//
// ⚠️ SEGURIDAD: este servidor da acceso completo a una shell del sistema.
// Corre SOLO en localhost, nunca lo expongas a internet ni a una red
// compartida sin agregar autenticación (ver nota al final del archivo).

const os = require("os");
const { WebSocketServer } = require("ws");
const pty = require("node-pty");

const PORT = Number(process.env.TERMINAL_PORT) || 4001;
const HOST = "127.0.0.1"; // solo localhost por defecto

const isWindows = os.platform() === "win32";
const defaultShell = isWindows
  ? (process.env.COMSPEC || "powershell.exe")
  : (process.env.SHELL || "/bin/bash");

const wss = new WebSocketServer({ host: HOST, port: PORT });

console.log(`🖥️  Servidor de terminal escuchando en ws://${HOST}:${PORT}`);
console.log(`   Shell por defecto: ${defaultShell}`);
console.log(`   (Ctrl+C para detenerlo)`);

wss.on("connection", (ws, req) => {
  const url = new URL(req.url, `http://${HOST}:${PORT}`);
  const requestedCwd = url.searchParams.get("cwd");

  let cwd = process.cwd();
  if (requestedCwd) {
    try {
      // Verifica que la ruta exista; si no, usa el directorio actual del server.
      require("fs").accessSync(requestedCwd);
      cwd = requestedCwd;
    } catch {
      ws.send(JSON.stringify({
        type: "data",
        data: `\r\n\x1b[33mAviso: no se encontró la ruta "${requestedCwd}", usando ${cwd}\x1b[0m\r\n`,
      }));
    }
  }

  const shellProc = pty.spawn(defaultShell, [], {
    name: "xterm-256color",
    cols: 80,
    rows: 24,
    cwd,
    env: process.env,
  });

  shellProc.onData((data) => {
    if (ws.readyState === ws.OPEN) {
      ws.send(JSON.stringify({ type: "data", data }));
    }
  });

  shellProc.onExit(({ exitCode }) => {
    if (ws.readyState === ws.OPEN) {
      ws.send(JSON.stringify({
        type: "data",
        data: `\r\n\x1b[90m[proceso finalizado, código ${exitCode}]\x1b[0m\r\n`,
      }));
      ws.close();
    }
  });

  ws.on("message", (raw) => {
    let msg;
    try {
      msg = JSON.parse(raw.toString());
    } catch {
      return;
    }
    if (msg.type === "input") {
      shellProc.write(msg.data);
    } else if (msg.type === "resize" && msg.cols && msg.rows) {
      try {
        shellProc.resize(msg.cols, msg.rows);
      } catch {
        /* ignorar si el proceso ya terminó */
      }
    }
  });

  ws.on("close", () => {
    try { shellProc.kill(); } catch { /* ya estaba muerto */ }
  });
});

// ── Nota sobre seguridad ──────────────────────────────────────────────
// Este servidor NO tiene autenticación: cualquiera que pueda conectarse
// al puerto 4001 tiene una shell completa con los permisos del usuario
// que corrió `node server.js`. Está pensado únicamente para desarrollo
// local (tú conectándote desde tu propio navegador a localhost).
// Si alguna vez necesitas exponerlo en red, agrega como mínimo:
//   - un token compartido validado en el "upgrade" de la conexión,
//   - TLS (wss://),
//   - y restringe qué comandos/directorios son accesibles.