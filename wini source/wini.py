# wini.py - Intérprete del lenguaje Wini

import argparse
import os
import sys

VERSION = "2.3.0"


def ejecutar_archivo(archivo):
    """Ejecuta un archivo .wn usando el intérprete tradicional"""
    from interprete import Interprete
    
    if not os.path.exists(archivo):
        print(f"Error: Archivo '{archivo}' no encontrado")
        return False
    
    try:
        interprete = Interprete(archivo)
        interprete.ejecutar()
        return True
    except Exception as e:
        print(f"Error al ejecutar: {e}")
        import traceback
        traceback.print_exc()
        return False


def transpilar_a_python(archivo_wn, salida=None):
    """Transpila un archivo .wn a .py usando wn2py"""
    from wn2py import transpilar_archivo as wn2py_transpilar
    
    if not os.path.exists(archivo_wn):
        print(f"Error: Archivo '{archivo_wn}' no encontrado")
        return False
    
    try:
        if salida is None:
            salida = archivo_wn.replace(".wn", ".py")
        wn2py_transpilar(archivo_wn, salida)
        return True
    except Exception as e:
        print(f"Error al transpilar: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        prog="wini",
        description="Lenguaje de programación Wini - Intérprete y herramientas",
        epilog="""
╔════════════════════════════════════════════════════════════════════╗
║  COMANDOS:                                                         ║
╠════════════════════════════════════════════════════════════════════╣
║  wini programa.wn              # Ejecutar con intérprete           ║
║  wini -a_py programa.wn        # Transpilar a Python               ║
║  wini -a_py prog.wn -o salida.py # Transpilar con salida           ║
║  wini --version                # Mostrar versión                   ║
╚════════════════════════════════════════════════════════════════════╝
        """,
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("archivo", nargs="?", help="Archivo .wn a procesar")
    parser.add_argument("--version", "-v", action="version", version=f"Wini {VERSION}")
    parser.add_argument("--traceback", "-t", action="store_true", help="Mostrar traceback completo")
    parser.add_argument("-a_py", action="store_true", help="Transpilar .wn a .py")
    parser.add_argument("-o", "--salida", default=None, help="Archivo de salida (para -a_py)")

    args = parser.parse_args()

    if not args.archivo:
        parser.print_help()
        return

    archivo = args.archivo
    if not archivo.endswith(".wn"):
        if os.path.exists(archivo + ".wn"):
            archivo = archivo + ".wn"
        else:
            print(f"Error: '{args.archivo}' no es un archivo .wn")
            return

    if not os.path.exists(archivo):
        print(f"Error: Archivo '{archivo}' no encontrado")
        return

    # Modo transpilación
    if args.a_py:
        if not transpilar_a_python(archivo, args.salida):
            sys.exit(1)
        return

    # Modo interpretación (por defecto)
    exito = ejecutar_archivo(archivo)
    sys.exit(0 if exito else 1)


if __name__ == "__main__":
    main()