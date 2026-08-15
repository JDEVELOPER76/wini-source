#!/usr/bin/env python3
# wn2py.py — Trasquilador (transpilador) de Wini (.wn) a Python (.py)
"""
Convierte un archivo .wn en un archivo .py equivalente y autocontenido
(incluye su propio "runtime" con las funciones nativas de Wini, así que
el resultado se ejecuta con `python salida.py` sin depender del intérprete
de Wini ni de estos módulos).

Uso:
    python wn2py.py entrada.wn
    python wn2py.py entrada.wn -o salida.py
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from transpilador import transpilar, ErrorTranspilacion
from exepciones import SintaxisError


def _leer_runtime_shim():
    """Lee el contenido de runtime_shim.py.

    __file__ funciona para hallar archivos *dentro* del binario compilado por
    Nuitka (onefile los extrae a una carpeta temporal y __file__ apunta ahí),
    así que basta con incluir runtime_shim.py como dato al compilar:

        nuitka --onefile --include-data-files=runtime_shim.py=runtime_shim.py wini.py

    Si no se encuentra ahí (p.ej. modo standalone sin ese flag), se busca
    también junto al propio ejecutable como respaldo.
    """
    candidatos = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtime_shim.py")]
    try:
        candidatos.append(os.path.join(__compiled__.containing_dir, "runtime_shim.py"))
    except NameError:
        candidatos.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "runtime_shim.py"))

    for ruta in candidatos:
        if os.path.exists(ruta):
            with open(ruta, "r", encoding="utf-8") as f:
                return f.read()

    raise FileNotFoundError(
        "No se encontró 'runtime_shim.py'. Si compilaste con Nuitka, inclúyelo con "
        "--include-data-files=runtime_shim.py=runtime_shim.py (onefile) o cópialo junto al ejecutable (standalone)."
    )


def transpilar_archivo(ruta_entrada, ruta_salida=None):
    with open(ruta_entrada, "r", encoding="utf-8") as f:
        codigo_wn = f.read()

    try:
        codigo_py, avisos = transpilar(codigo_wn, ruta_entrada)
    except SintaxisError as e:
        print(f"Error de sintaxis en '{ruta_entrada}': {e}")
        sys.exit(1)
    except ErrorTranspilacion as e:
        print(f"Error de transpilación en '{ruta_entrada}': {e}")
        sys.exit(1)

    runtime = _leer_runtime_shim()

    encabezado = (
        f"#!/usr/bin/env python3\n"
        f"# Generado automáticamente por wn2py a partir de: {os.path.basename(ruta_entrada)}\n"
        f"# NO editar la sección de runtime a mano; el código de tu programa\n"
        f"# empieza después del marcador '# === PROGRAMA ==='.\n\n"
    )

    salida = encabezado + runtime + "\n\n# === PROGRAMA ===\n\n" + codigo_py + "\n"

    if ruta_salida is None:
        base, _ = os.path.splitext(ruta_entrada)
        ruta_salida = base + ".py"

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(salida)

    if avisos:
        print("Avisos de la transpilación (revisa manualmente):")
        for a in avisos:
            print(f"  - {a}")

    print(f"OK: '{ruta_entrada}' -> '{ruta_salida}'")
    return ruta_salida


def main():
    ap = argparse.ArgumentParser(
        prog="wn2py",
        description="Trasquilador de Wini (.wn) a Python (.py)",
    )
    ap.add_argument("entrada", help="Archivo .wn a convertir")
    ap.add_argument("-o", "--salida", default=None, help="Archivo .py de salida (por defecto: mismo nombre con .py)")
    args = ap.parse_args()

    if not os.path.exists(args.entrada):
        print(f"Error: no se encontró '{args.entrada}'")
        sys.exit(1)

    transpilar_archivo(args.entrada, args.salida)


if __name__ == "__main__":
    main()