"""
Servidor de terminal real para el Editor Wini — versión Python.

Abre un WebSocket local que, por cada conexión, lanza un proceso de shell
de verdad (bash/zsh en Linux/Mac vía el módulo estándar `pty`, o PowerShell
en Windows vía `pywinpty`) y transmite su entrada/salida.

Usa el mismo protocolo JSON que la versión Node (server.js), así que el
frontend (TerminalPanel.jsx) funciona sin cambios con cualquiera de los dos:
  → servidor a cliente: {"type": "data", "data": "<texto de la terminal>"}
  ← cliente a servidor: {"type": "input", "data": "<lo que el usuario tipeó>"}
  ← cliente a servidor: {"type": "resize", "cols": N, "rows": N}

⚠️ SEGURIDAD: este servidor da acceso completo a una shell del sistema.
Corré esto SOLO en localhost, nunca lo expongas a internet ni a una red
compartida sin agregar autenticación (ver nota al final del archivo).
"""

import asyncio
import json
import os
import signal
import sys
from urllib.parse import urlparse, parse_qs

import websockets

HOST = "127.0.0.1"  # solo localhost por defecto
PORT = int(os.environ.get("TERMINAL_PORT", 4001))
IS_WINDOWS = os.name == "nt"
DEFAULT_SHELL = os.environ.get(
    "SHELL",
    "powershell.exe" if IS_WINDOWS else "/bin/bash",
)


# ── Sesiones de PTY: una implementación por plataforma ─────────────────

class PosixPtySession:
    """Usa el módulo `pty` de la librería estándar (Linux/Mac)."""

    def __init__(self, shell, cwd):
        import pty
        self._pty = pty
        self.shell = shell
        self.cwd = cwd
        self.pid = None
        self.fd = None

    async def start(self):
        pid, fd = self._pty.fork()
        if pid == 0:
            # Proceso hijo: se convierte en la shell
            try:
                os.chdir(self.cwd)
            except OSError:
                pass
            os.execvp(self.shell, [self.shell])
        self.pid, self.fd = pid, fd
        self.resize(24, 80)

    async def read(self):
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, os.read, self.fd, 4096)
        except OSError:
            return b""

    def write(self, data):
        try:
            os.write(self.fd, data.encode())
        except OSError:
            pass

    def resize(self, rows, cols):
        import fcntl
        import struct
        import termios
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        try:
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)
        except OSError:
            pass

    def close(self):
        try:
            os.kill(self.pid, signal.SIGTERM)
        except (ProcessLookupError, TypeError):
            pass
        try:
            os.close(self.fd)
        except (OSError, TypeError):
            pass


class WindowsPtySession:
    """Usa `pywinpty` (paquete `pywinpty`, importado como `winpty`)."""

    def __init__(self, shell, cwd):
        self.shell = shell
        self.cwd = cwd
        self.proc = None

    async def start(self):
        try:
            import winpty
        except ImportError as exc:
            raise RuntimeError(
                "Falta el paquete 'pywinpty'. Instalalo con: pip install pywinpty"
            ) from exc
        self.proc = winpty.PtyProcess.spawn(self.shell, cwd=self.cwd, dimensions=(24, 80))

    async def read(self):
        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, self.proc.read, 4096)
        except EOFError:
            return b""
        return data.encode() if isinstance(data, str) else data

    def write(self, data):
        try:
            self.proc.write(data)
        except Exception:
            pass

    def resize(self, rows, cols):
        try:
            self.proc.setwinsize(rows, cols)
        except Exception:
            pass

    def close(self):
        try:
            self.proc.terminate(force=True)
        except Exception:
            pass


def make_session(shell, cwd):
    return WindowsPtySession(shell, cwd) if IS_WINDOWS else PosixPtySession(shell, cwd)


# ── Servidor WebSocket ──────────────────────────────────────────────────

async def handle_client(websocket):
    path = getattr(websocket, "path", "") or getattr(getattr(websocket, "request", None), "path", "")
    query = parse_qs(urlparse(path).query)
    requested_cwd = query.get("cwd", [None])[0]

    cwd = os.getcwd()
    if requested_cwd:
        if os.path.isdir(requested_cwd):
            cwd = requested_cwd
        else:
            await websocket.send(json.dumps({
                "type": "data",
                "data": f"\r\n\x1b[33mAviso: no se encontró la ruta \"{requested_cwd}\", usando {cwd}\x1b[0m\r\n",
            }))

    session = make_session(DEFAULT_SHELL, cwd)
    try:
        await session.start()
    except Exception as exc:
        await websocket.send(json.dumps({
            "type": "data",
            "data": f"\r\n\x1b[31mNo se pudo iniciar la shell: {exc}\x1b[0m\r\n",
        }))
        return

    async def pump_output():
        while True:
            data = await session.read()
            if not data:
                break
            try:
                await websocket.send(json.dumps({"type": "data", "data": data.decode(errors="replace")}))
            except websockets.ConnectionClosed:
                break

    reader_task = asyncio.create_task(pump_output())

    try:
        async for message in websocket:
            try:
                msg = json.loads(message)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "input":
                session.write(msg.get("data", ""))
            elif msg.get("type") == "resize":
                session.resize(msg.get("rows", 24), msg.get("cols", 80))
    finally:
        reader_task.cancel()
        session.close()


async def main():
    print(f"🖥️  Servidor de terminal (Python) escuchando en ws://{HOST}:{PORT}")
    print(f"   Shell por defecto: {DEFAULT_SHELL}")
    print("   (Ctrl+C para detenerlo)")
    async with websockets.serve(handle_client, HOST, PORT):
        await asyncio.Future()  # corre para siempre


if __name__ == "__main__":
    if IS_WINDOWS:
        try:
            import winpty  # noqa: F401
        except ImportError:
            print("⚠️  En Windows este servidor necesita 'pywinpty': pip install pywinpty")
            sys.exit(1)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

# ── Nota sobre seguridad ──────────────────────────────────────────────
# Este servidor NO tiene autenticación: cualquiera que pueda conectarse
# al puerto 4001 tiene una shell completa con los permisos del usuario
# que corrió `python server.py`. Está pensado únicamente para desarrollo
# local (vos conectándote desde tu propio navegador a localhost).
# Si alguna vez necesitas exponerlo en red, agregá como mínimo:
#   - un token compartido validado antes de aceptar la conexión,
#   - TLS (wss://, con websockets.serve(..., ssl=contexto_ssl)),
#   - y restringí qué comandos/directorios son accesibles.