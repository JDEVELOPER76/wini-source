# importador.py
"""Importación de módulos en el intérprete wini"""

import os
import sys
import importlib.util

from exepciones import RuntimeError


# ─────────────────────────────────────────────────────────────────────────────
#  LISTA BLANCA DE MÓDULOS PYTHON ESTÁNDAR PERMITIDOS
#
#  Solo los módulos listados aquí pueden importarse directamente con
#  importar("nombre").  Para exponer cualquier otro módulo Python (incluyendo
#  los tuyos propios), crea un archivo .wipy usando la API de wini_bridge.
#
#  Agregar aquí solo módulos que sean seguros de exponer a Wini completos.
#  Si quieres exponer PARTES de un módulo, usa .wipy en vez de esta lista.
# ─────────────────────────────────────────────────────────────────────────────
MODULOS_PYTHON_PERMITIDOS = {
    # Matemáticas y números
    "math",
    "random",
    "decimal",
    "fractions",
    "statistics",
    # Texto
    "re",
    "string",
    "textwrap",
    "unicodedata",
    # Colecciones
    "collections",
    "heapq",
    "bisect",
    # Fecha y hora
    "datetime",
    "calendar",
    "time",
    # Serialización (solo lectura/escritura de datos, no ejecución)
    "json",
    "csv",
    # Utilidades
    "itertools",
    "functools",
    "operator",
    "copy",
    "enum",
    "dataclasses",
    # I/O básico (sin acceso a sistema de archivos arbitrario)
    "io",
    "struct",
    "base64",
    "hashlib",
    "hmac",
    "uuid",
}

# ─────────────────────────────────────────────────────────────────────────────
#  MÓDULOS PYTHON EXPLÍCITAMENTE BLOQUEADOS
#
#  Se bloquean aunque estén en MODULOS_PYTHON_PERMITIDOS (tienen precedencia).
#  Incluye los módulos más peligrosos por defecto.
# ─────────────────────────────────────────────────────────────────────────────
MODULOS_PYTHON_BLOQUEADOS = {
    "os", "sys", "subprocess", "shutil", "pathlib",
    "socket", "http", "urllib", "ftplib", "smtplib",
    "importlib", "imp", "builtins", "ctypes",
    "multiprocessing", "threading", "concurrent",
    "pickle", "shelve", "marshal",
    "ast", "code", "codeop", "compileall",
    "gc", "inspect", "dis", "tokenize",
    "signal", "atexit", "faulthandler",
    "winreg", "winsound", "msvcrt",
}


class Importador:
    """Encapsula la lógica de importación de módulos"""

    def __init__(self, interprete):
        self.interprete = interprete
        self.modulos_cache = {}
        self._modulos_importados = set()
        self._asegurar_stdlib_en_syspath()
        self._inicializar_rutas_busqueda()

    # ── Rutas ──────────────────────────────────────────────────────────────

    def _obtener_ruta_base(self):
        # Para Nuitka (compilado con --standalone)
        if getattr(sys, 'frozen', True) and hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        # Para PyInstaller (alternativa)
        elif getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        # Modo desarrollo (normal)
        return os.path.dirname(os.path.abspath(__file__))

    def _asegurar_stdlib_en_syspath(self):
        python_lib = os.path.dirname(os.__file__)
        if python_lib and python_lib not in sys.path:
            sys.path.insert(0, python_lib)
        try:
            import site
            for sitepkg in site.getsitepackages():
                if sitepkg and sitepkg not in sys.path:
                    sys.path.insert(0, sitepkg)
        except Exception:
            pass

    def _obtener_ruta_librerias_global(self):
        ruta = os.path.join(self._obtener_ruta_base(), "librerias")
        os.makedirs(ruta, exist_ok=True)
        return ruta

    def _inicializar_rutas_busqueda(self):
        self.rutas_busqueda = []

        if hasattr(self.interprete, 'archivo') and self.interprete.archivo:
            dir_actual = os.path.dirname(self.interprete.archivo)
            if dir_actual:
                self.rutas_busqueda.append(dir_actual)
                self.rutas_busqueda.append(os.path.join(dir_actual, 'librerias'))

        cwd = os.getcwd()
        self.rutas_busqueda.append(cwd)
        self.rutas_busqueda.append(os.path.join(cwd, 'librerias'))

        self.ruta_global = self._obtener_ruta_librerias_global()
        self.rutas_busqueda.append(self.ruta_global)

        ruta_dev = self._obtener_ruta_base()
        self.rutas_busqueda.append(os.path.join(ruta_dev, 'librerias'))

        extra_paths = os.environ.get('WINI_PATH', '')
        for p in extra_paths.split(os.pathsep):
            if p and os.path.exists(p):
                self.rutas_busqueda.append(p)
                self.rutas_busqueda.append(os.path.join(p, 'librerias'))

        if hasattr(self.interprete, 'paquetes'):
            for nombre, ruta in self.interprete.paquetes.items():
                if ruta and os.path.exists(ruta) and ruta not in self.rutas_busqueda:
                    self.rutas_busqueda.append(ruta)

        self.rutas_busqueda = list(dict.fromkeys(
            os.path.normpath(r) for r in self.rutas_busqueda if r
        ))

    def agregar_ruta_busqueda(self, ruta, prioridad=False):
        ruta = os.path.normpath(ruta)
        if not ruta or not os.path.exists(ruta):
            return
        if ruta in self.rutas_busqueda:
            self.rutas_busqueda.remove(ruta)
        if prioridad:
            self.rutas_busqueda.insert(0, ruta)
        else:
            self.rutas_busqueda.append(ruta)
        librerias_ruta = os.path.normpath(os.path.join(ruta, 'librerias'))
        if os.path.exists(librerias_ruta):
            if librerias_ruta in self.rutas_busqueda:
                self.rutas_busqueda.remove(librerias_ruta)
            if prioridad:
                self.rutas_busqueda.insert(1, librerias_ruta)
            else:
                self.rutas_busqueda.append(librerias_ruta)

    def obtener_rutas_busqueda(self):
        return self.rutas_busqueda.copy()

    # ── Búsqueda de archivos ───────────────────────────────────────────────

    def _encontrar_archivo(self, nombre_modulo):
        # .wipy tiene prioridad sobre .py para mayor seguridad
        extensiones = ['.wn', '.wipy', '.py']

        for ruta in self.rutas_busqueda:
            if not ruta or not os.path.exists(ruta):
                continue

            for ext in extensiones:
                ruta_completa = os.path.normpath(
                    os.path.join(ruta, nombre_modulo + ext)
                )
                if os.path.isfile(ruta_completa):
                    return ruta_completa

            ruta_paquete = os.path.normpath(os.path.join(ruta, nombre_modulo))
            if os.path.isdir(ruta_paquete):
                for ext in extensiones:
                    init_path = os.path.join(ruta_paquete, '__init__' + ext)
                    if os.path.isfile(init_path):
                        return ruta_paquete

        return None

    def _encontrar_modulo_con_puntos(self, nombre_modulo):
        partes = nombre_modulo.split('.')

        for ruta_base in self.rutas_busqueda:
            if not ruta_base or not os.path.exists(ruta_base):
                continue

            ruta_actual = ruta_base

            for i, parte in enumerate(partes):
                ruta_actual = os.path.normpath(os.path.join(ruta_actual, parte))

                if i == len(partes) - 1:
                    for ext in ['.wn', '.wipy', '.py']:
                        ruta_archivo = ruta_actual + ext
                        if os.path.isfile(ruta_archivo):
                            return ruta_archivo

                    if os.path.isdir(ruta_actual):
                        for ext in ['.wn', '.wipy', '.py']:
                            init_path = os.path.join(ruta_actual, '__init__' + ext)
                            if os.path.isfile(init_path):
                                return ruta_actual
                else:
                    if not os.path.isdir(ruta_actual):
                        break

        return None

    # ── Punto de entrada principal ─────────────────────────────────────────

    def importar_modulo(self, nombre_modulo, alias=None):
        """
        Importa un módulo .wn, .wipy o Python (si está en la lista blanca).

        Orden de búsqueda:
          1. Cache
          2. Archivo .wn  en rutas_busqueda
          3. Archivo .wipy en rutas_busqueda
          4. Archivo .py  en rutas_busqueda
          5. Módulo Python estándar — SOLO si está en MODULOS_PYTHON_PERMITIDOS
             y NO está en MODULOS_PYTHON_BLOQUEADOS.

        Para exponer módulos Python propios de forma controlada usa .wipy.
        """
        if nombre_modulo in self.modulos_cache:
            modulo = self.modulos_cache[nombre_modulo]
            if alias:
                self._registrar_modulo(alias, modulo)
            return modulo

        if nombre_modulo in self._modulos_importados:
            modulo_temp = {
                "variables": {}, "funciones": {}, "clases": {},
                "nombre": nombre_modulo, "ruta": None, "_cargando": True
            }
            self.modulos_cache[nombre_modulo] = modulo_temp
            return modulo_temp

        self._modulos_importados.add(nombre_modulo)

        try:
            ruta = (
                self._encontrar_modulo_con_puntos(nombre_modulo)
                if '.' in nombre_modulo
                else self._encontrar_archivo(nombre_modulo)
            )

            # Buscar en paquetes registrados si no encontró todavía
            if not ruta and hasattr(self.interprete, 'paquetes'):
                for _, ruta_paquete in self.interprete.paquetes.items():
                    if ruta_paquete and os.path.isdir(ruta_paquete):
                        for ext in ['.wn', '.wipy', '.py']:
                            posible = os.path.join(ruta_paquete, nombre_modulo + ext)
                            if os.path.exists(posible):
                                ruta = posible
                                break
                    if ruta:
                        break

            # ── Sin archivo local: intentar módulo Python estándar ─────────
            if not ruta:
                modulo = self._importar_modulo_python_stdlib(nombre_modulo)
                self.modulos_cache[nombre_modulo] = modulo
                nombre_registro = alias if alias else nombre_modulo
                self._registrar_modulo(nombre_registro, modulo)
                return modulo

            # ── Importar según extensión ───────────────────────────────────
            if ruta.endswith('.wn'):
                modulo = self._importar_modulo_wn(ruta, nombre_modulo)
            elif ruta.endswith('.wipy'):
                modulo = self._importar_modulo_wipy(ruta, nombre_modulo)
            elif ruta.endswith('.py'):
                modulo = self._importar_modulo_python_archivo(ruta, nombre_modulo)
            else:
                modulo = self._importar_paquete(ruta, nombre_modulo)

            self.modulos_cache[nombre_modulo] = modulo

            nombre_base = (
                os.path.splitext(os.path.basename(ruta))[0]
                if ruta.endswith(('.wn', '.wipy', '.py'))
                else nombre_modulo.split('.')[-1]
            )
            nombre_registro = alias if alias else nombre_base
            self._registrar_modulo(nombre_registro, modulo)

            return modulo

        finally:
            self._modulos_importados.discard(nombre_modulo)

    # ── Importación de módulos Python stdlib (con lista blanca) ───────────

    def _importar_modulo_python_stdlib(self, nombre_modulo):
        """
        Importa un módulo Python de la stdlib solo si está en la lista blanca.
        Lanza RuntimeError si el módulo está bloqueado o no está permitido.
        """
        # Nombre raíz (ej: "os.path" → "os")
        nombre_raiz = nombre_modulo.split('.')[0]

        if nombre_raiz in MODULOS_PYTHON_BLOQUEADOS:
            raise RuntimeError(
                f"El módulo '{nombre_modulo}' está bloqueado por seguridad. "
                f"Si necesitas parte de su funcionalidad, crea un archivo "
                f"'{nombre_modulo}.wipy' usando la API wini_bridge."
            )

        if nombre_raiz not in MODULOS_PYTHON_PERMITIDOS:
            raise RuntimeError(
                f"El módulo Python '{nombre_modulo}' no está permitido en Wini.\n"
                f"Para usarlo, crea un archivo '{nombre_modulo}.wipy' con la "
                f"API wini_bridge y expón solo las funciones que necesites.\n"
                f"Módulos permitidos sin puente: {', '.join(sorted(MODULOS_PYTHON_PERMITIDOS))}"
            )

        try:
            import importlib as _importlib
            modulo_py = _importlib.import_module(nombre_modulo)
            return self._procesar_modulo_python(modulo_py, nombre_modulo, None)
        except (ImportError, ModuleNotFoundError):
            rutas_str = "\n  ".join(self.rutas_busqueda)
            raise RuntimeError(
                f"Módulo '{nombre_modulo}' no encontrado.\n"
                f"Rutas buscadas:\n  {rutas_str}"
            )

    # ── Importación de archivos .wipy ──────────────────────────────────

    def _importar_modulo_wipy(self, ruta, nombre_modulo):
        """
        Importa un módulo puente .wipy.

        El archivo .wipy es Python normal que debe terminar definiendo
        una variable llamada `modulo` de tipo PythonAPI (de wpython.py).
        """
        try:
            ruta_abs = os.path.abspath(ruta)

            if not os.path.isfile(ruta_abs):
                raise RuntimeError(f"No se encontró el archivo '{ruta_abs}'.")

            # importlib no reconoce .wipy como extensión Python válida,
            # así que leemos y ejecutamos el código con exec() directamente
            ruta_base = self._obtener_ruta_base()
            dir_wipy  = os.path.dirname(ruta_abs)
            sys_path_backup = sys.path.copy()
            for p in (ruta_base, dir_wipy):
                if p not in sys.path:
                    sys.path.insert(0, p)

            nombre_unico = f"wipy_{abs(hash(ruta_abs)) % 1_000_000}"
            namespace = {"__file__": ruta_abs, "__name__": nombre_unico}
            try:
                with open(ruta_abs, "r", encoding="utf-8") as f:
                    codigo = f.read()
                exec(compile(codigo, ruta_abs, "exec"), namespace)
            finally:
                sys.path = sys_path_backup

            # El archivo .wipy debe exponer una variable `modulo`
            if "modulo" not in namespace:
                raise RuntimeError(
                    f"El archivo '{ruta_abs}' no define una variable 'modulo'.\n"
                    f"Ejemplo:\n"
                    f"  from wpython import PythonAPI\n"
                    f"  modulo = PythonAPI('mi_modulo')\n"
                    f"  @modulo.funcion\n"
                    f"  def mi_funcion(x): ..."
                )

            puente = namespace["modulo"]

            if not hasattr(puente, "_a_modulo_wini"):
                raise RuntimeError(
                    f"La variable 'modulo' en '{ruta_abs}' no es un PythonAPI válido."
                )

            return puente._a_modulo_wini(ruta=ruta_abs)

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"Error al importar módulo puente '{nombre_modulo}': {e}"
            )

    # ── Importación de archivos .py locales (con advertencia) ─────────────

    def _importar_modulo_python_archivo(self, ruta, nombre_modulo):
        """
        Importa un archivo .py local.

        Se permite porque el desarrollador lo colocó explícitamente en sus
        rutas de búsqueda. Sin embargo, se recomienda migrar a .wipy
        para tener control explícito sobre lo que se expone.
        """
        try:
            from ejecutor import ClasePython  # noqa: F401 (asegura disponibilidad)

            nombre_base = os.path.splitext(os.path.basename(ruta))[0]
            nombre_unico = f"modulo_{abs(hash(ruta)) % 1_000_000}"

            spec = importlib.util.spec_from_file_location(nombre_unico, ruta)
            modulo_py = importlib.util.module_from_spec(spec)
            sys.modules[nombre_unico] = modulo_py
            spec.loader.exec_module(modulo_py)

            return self._procesar_modulo_python(modulo_py, nombre_modulo, ruta)

        except Exception as e:
            raise RuntimeError(
                f"Error al importar módulo Python '{nombre_modulo}': {e}"
            )

    # ── Métodos de soporte (sin cambios funcionales) ──────────────────────

    def _importar_paquete(self, ruta_paquete, nombre_modulo):
        init_path = None
        for ext in ['.wn', '.wipy', '.py']:
            test_path = os.path.join(ruta_paquete, '__init__' + ext)
            if os.path.exists(test_path):
                init_path = test_path
                break

        if not init_path:
            raise RuntimeError(
                f"Paquete '{nombre_modulo}' no tiene __init__"
            )

        if init_path.endswith('.wn'):
            return self._importar_modulo_wn(init_path, nombre_modulo)
        elif init_path.endswith('.wipy'):
            return self._importar_modulo_wipy(init_path, nombre_modulo)
        else:
            return self._importar_modulo_python_archivo(init_path, nombre_modulo)

    def _importar_modulo_wn(self, ruta_modulo, nombre_modulo):
        """Importa un módulo .wn  (sin cambios)"""
        try:
            from lexer import lexer
            from parser import Parser

            with open(ruta_modulo, 'r', encoding='utf-8') as f:
                codigo = f.read()

            tokens = lexer(codigo)
            parser = Parser(tokens)
            ast = parser.parse()

            modulo = {
                "_tipo": "modulo",
                "variables": {}, "funciones": {}, "clases": {},
                "nombre": nombre_modulo, "ruta": ruta_modulo
            }

            archivo_anterior = self.interprete.archivo
            directorio_anterior = self.interprete.directorio
            variables_backup = self.interprete.variables.copy()
            funciones_backup = self.interprete.funciones.copy()
            clases_backup = self.interprete.clases.copy()
            rutas_busqueda_backup = self.rutas_busqueda.copy()

            dir_modulo = os.path.dirname(os.path.abspath(ruta_modulo))
            sys_path_backup = sys.path.copy()
            if dir_modulo not in sys.path:
                sys.path.insert(0, dir_modulo)

            try:
                self.rutas_busqueda = rutas_busqueda_backup.copy()
                if dir_modulo not in self.rutas_busqueda:
                    self.rutas_busqueda.insert(0, dir_modulo)

                self.interprete.variables = modulo["variables"]
                self.interprete.funciones = modulo["funciones"]
                self.interprete.clases = modulo["clases"]
                self.interprete.archivo = os.path.abspath(ruta_modulo)
                self.interprete.directorio = dir_modulo

                for sentencia in ast.hijos:
                    self.interprete.interpretar(sentencia)
                    if self.interprete.variables is not modulo["variables"]:
                        modulo["variables"].update(self.interprete.variables)
                        self.interprete.variables = modulo["variables"]
                    if self.interprete.funciones is not modulo["funciones"]:
                        modulo["funciones"].update(self.interprete.funciones)
                        self.interprete.funciones = modulo["funciones"]
                    if self.interprete.clases is not modulo["clases"]:
                        modulo["clases"].update(self.interprete.clases)
                        self.interprete.clases = modulo["clases"]

            finally:
                self.interprete.archivo = archivo_anterior
                self.interprete.directorio = directorio_anterior
                self.interprete.variables = variables_backup
                self.interprete.funciones = funciones_backup
                self.interprete.clases = clases_backup
                self.rutas_busqueda = rutas_busqueda_backup
                sys.path = sys_path_backup

            return modulo

        except Exception as e:
            raise RuntimeError(
                f"Error al importar módulo .wn '{nombre_modulo}': {e}"
            )

    def _procesar_modulo_python(self, modulo_py, nombre_modulo, ruta_modulo):
        """Convierte un módulo Python al formato interno de Wini."""
        from ejecutor import ClasePython

        modulo = {
            "variables": {}, "funciones": {}, "clases": {},
            "nombre": nombre_modulo, "ruta": ruta_modulo, "_tipo": "modulo"
        }

        for nombre, obj in vars(modulo_py).items():
            if nombre.startswith("_"):
                continue
            if isinstance(obj, type):
                modulo["clases"][nombre] = ClasePython(nombre, obj)
            elif callable(obj):
                modulo["funciones"][nombre] = obj
            else:
                modulo["variables"][nombre] = obj

        return modulo

    def _registrar_modulo(self, nombre, modulo):
        if nombre in self.interprete.variables:
            return

        self.interprete.variables[nombre] = {
            "_tipo": "modulo",
            "_nombre": nombre,
            "variables": modulo["variables"],
            "funciones": modulo["funciones"],
            "clases": modulo["clases"],
        }