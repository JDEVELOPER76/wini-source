# interprete.py
"""Intérprete principal para el lenguaje wini.

Soporta una forma simple de importación de módulos:
    importar modulo
    importar modulo como alias
    importar carpeta.modulo como alias
Cada módulo es otro archivo .wn ubicado junto al archivo actual (o en
subcarpetas si se usa notación de punto). Se ejecuta en su propio
sub-intérprete y se expone como un diccionario {"_tipo": "modulo", ...}
con sus funciones y variables, tal como ya esperaba evaluador.py
(ACCESO_ATRIBUTO).
"""

import os 
import sys
import importlib.machinery
import importlib.util
from lexer import lexer
from parser import Parser
from exepciones import *
from evaluador import Evaluador
from ejecutor import Ejecutor


def _directorio_ejecutable():
    """Carpeta donde vive el .exe (o el script) real."""
    try:
        return __compiled__.containing_dir  # Nuitka onefile/standalone
    except NameError:
        pass
    try:
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    except Exception:
        return os.getcwd()


class Interprete:
    """Intérprete principal del lenguaje wini"""

    def __init__(self, archivo, _cache_modulos=None, _pila_importando=None):
        self.archivo = os.path.abspath(archivo)
        self.directorio = os.path.dirname(self.archivo)
        self.variables = {}
        
        # Funciones nativas
        self.funciones = {
            "rango": self._rango_nativo,
        }
        
        self.paquetes = {}
        self.default_paquete = None

        # Caché de módulos ya importados (compartida entre sub-intérpretes
        # para no volver a ejecutar el mismo archivo dos veces) y pila de
        # rutas en proceso de importación (para detectar ciclos).
        self._cache_modulos = _cache_modulos if _cache_modulos is not None else {}
        self._pila_importando = _pila_importando if _pila_importando is not None else []
        
        # Crear evaluador y ejecutor
        self.evaluador = Evaluador(self)
        self.ejecutor = Ejecutor(self)

        # Tabla de despacho: tipo de nodo -> método manejador. interpretar()
        # se invoca por cada sentencia del programa, en cada iteración de
        # cada bucle (mientras/para), así que evitar la cadena de if/elif
        # (O(n) en el número de tipos de sentencia) es tan importante aquí
        # como en Evaluador.evaluar().
        self._dispatch = {
            "PROGRAMA": self._int_programa,
            "MIENTRAS": self._ejecutar_mientras,
            "PARA": self._ejecutar_para,
            "ROMPER": self._int_romper,
            "CONTINUAR": self._int_continuar,
            "ASIGNACION": self._int_asignacion,
            "ASIGNACION_INDEX": self._ejecutar_asignacion_index,
            "LLAMADA": self._int_llamada,
            "LLAMADA_METODO": self._int_llamada_metodo,
            "RETORNO": self._int_retorno,
            "INTENTAR": self._ejecutar_intentar,
            "LANZAR": self._ejecutar_lanzar,
            "IMPORTAR": self._ejecutar_importar,
            "FUNCION": self._definir_funcion,
            "SI": self._ejecutar_si,
        }
    
    def ejecutar(self):
        """Lee y ejecuta el archivo"""
        try:
            with open(self.archivo, 'r', encoding='utf-8') as f:
                codigo = f.read()
            tokens = lexer(codigo)
            parser = Parser(tokens)
            ast = parser.parse()
            self.interpretar(ast)
        except FileNotFoundError:
            print(f"Error: El archivo '{self.archivo}' no existe")
            sys.exit(1)
        except (SintaxisError, RuntimeError) as e:
            self._mostrar_error(e)
            sys.exit(1)
        except Exception as e:
            print(f"Error inesperado: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def _mostrar_error(self, e):
        """Muestra un error con información de línea y código"""
        print(f"Error: {e.mensaje}")
        if e.linea:
            print(f"  Línea {e.linea}" + (f", columna {e.columna}" if e.columna else ""))
            if e.texto:
                print(f"  {e.texto}")
            else:
                try:
                    with open(self.archivo, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    if 1 <= e.linea <= len(lines):
                        print(f"  {lines[e.linea-1].rstrip()}")
                except:
                    pass
    
    def _normalizar_iterable(self, iterable, linea):
        """Convierte cualquier objeto a un iterable Python estándar"""
        if isinstance(iterable, (list, str, tuple, range)):
            if isinstance(iterable, str):
                return list(iterable)
            return list(iterable)
        if isinstance(iterable, dict):
            return list(iterable.keys())
        try:
            return list(iterable)
        except TypeError:
            raise RuntimeError(f"No se puede iterar sobre '{type(iterable).__name__}'", linea=linea)

    def interpretar(self, nodo):
        """Interpreta un nodo del AST.

        Despacha por diccionario (O(1)) en vez de una cadena de if/elif
        (O(n) en el número de tipos de sentencia). Ver el comentario en
        __init__ sobre self._dispatch: esta función se llama por cada
        sentencia ejecutada, en cada iteración de cada bucle, así que es
        una de las rutas más calientes de todo el intérprete."""
        manejador = self._dispatch.get(nodo.tipo)
        if manejador is not None:
            return manejador(nodo)

    # ---------- Manejadores simples inline (usados por self._dispatch) ----------

    def _int_programa(self, nodo):
        for hijo in nodo.hijos:
            self.interpretar(hijo)

    def _int_romper(self, nodo):
        raise RomperException()

    def _int_continuar(self, nodo):
        raise ContinuarException()

    def _int_asignacion(self, nodo):
        valor = self.evaluador.evaluar(nodo.hijos[0])
        self.variables[nodo.valor] = valor

    def _int_llamada(self, nodo):
        return self.ejecutor.ejecutar_funcion(nodo)

    def _int_llamada_metodo(self, nodo):
        return self.ejecutor.ejecutar_metodo(nodo)

    def _int_retorno(self, nodo):
        valor = self.evaluador.evaluar(nodo.hijos[0])
        raise RetornoException(valor)

    # ------------------- Métodos auxiliares para interpretación -------------------
    
    def _ejecutar_mientras(self, nodo):
        """Ejecuta un bucle mientras en Python puro"""
        condicion_nodo = nodo.hijos[0]
        bloque_nodo = nodo.hijos[1]
        
        while True:
            resultado_condicion = self.evaluador.evaluar(condicion_nodo)
            
            if not resultado_condicion:
                break
                
            try:
                for sentencia in bloque_nodo.hijos:
                    self.interpretar(sentencia)
            except RomperException:
                break
            except ContinuarException:
                continue
    
    def _ejecutar_para(self, nodo):
        variable_nombre = nodo.hijos[0].valor
        iterable_evaluado = self.evaluador.evaluar(nodo.hijos[1])
        bloque_sentencias = nodo.hijos[2]

        # Iteración directa sin instanciar list(iterable_evaluado)
        try:
            iterador = iter(iterable_evaluado)
        except TypeError:
            raise RuntimeError(
                f"El objeto de tipo '{type(iterable_evaluado).__name__}' no es iterable",
                linea=nodo.linea
            )

        for elemento in iterador:
            self.variables[variable_nombre] = elemento
            try:
                for sentencia in bloque_sentencias.hijos:
                    self.interpretar(sentencia)
            except RomperException:
                break
            except ContinuarException:
                continue
    
    def _ejecutar_asignacion_index(self, nodo):
        """Ejecuta una asignación por índice"""
        variable = nodo.valor
        if variable not in self.variables:
            raise RuntimeError(f"Variable '{variable}' no definida", linea=nodo.linea)
        
        objeto = self.variables[variable]
        indice = self.evaluador.evaluar(nodo.hijos[0])
        valor = self.evaluador.evaluar(nodo.hijos[1])
        
        if isinstance(objeto, list):
            if not isinstance(indice, int):
                if hasattr(indice, 'valor') and isinstance(indice.valor, int):
                    indice = indice.valor
                else:
                    raise RuntimeError("Índice de lista debe ser entero", linea=nodo.linea)
            if indice < 0 or indice >= len(objeto):
                raise RuntimeError(f"Índice {indice} fuera de rango para lista de tamaño {len(objeto)}", linea=nodo.linea)
            objeto[indice] = valor
        elif isinstance(objeto, dict):
            objeto[indice] = valor
        else:
            raise RuntimeError(f"No se puede indexar asignación sobre tipo {type(objeto).__name__}", linea=nodo.linea)
    
    def _definir_funcion(self, nodo):
        """Define una función"""
        docstring = getattr(nodo, "docstring", None)
        self.funciones[nodo.valor] = {
            "parametros": [param.valor for param in nodo.hijos[0].hijos],
            "cuerpo": nodo.hijos[1].hijos,
            "docstring": docstring
        }
        
    def _ejecutar_si(self, nodo):
        """Ejecuta una sentencia si"""
        condicion = self.evaluador.evaluar(nodo.hijos[0])
        if condicion:
            for sentencia in nodo.hijos[1].hijos:
                self.interpretar(sentencia)
        else:
            for sentencia in nodo.hijos[2].hijos:
                self.interpretar(sentencia)

    def _ejecutar_intentar(self, nodo):
        """Ejecuta una estructura intentar-capturar-finalmente"""
        bloque_try = nodo.hijos[0]
        bloques_capturar = nodo.hijos[1]
        bloque_finally = nodo.hijos[2]
        
        resultado = None
        
        try:
            for sentencia in bloque_try.hijos:
                self.interpretar(sentencia)
        except (ErrorTipo, ErrorValor, ErrorIndice, ErrorAtributo, 
                ErrorImportacion, ErrorMatematico, RuntimeError) as e:
            error_manejado = False
            
            for capturar in bloques_capturar.hijos:
                tipo_error = capturar.valor
                variable_error = capturar.hijos[0].valor
                bloque_capturar = capturar.hijos[1]
                
                if tipo_error is None or self._error_coincide(e, tipo_error):
                    error_manejado = True
                    
                    cambios = {}
                    if variable_error:
                        cambios[variable_error] = e.mensaje if hasattr(e, 'mensaje') else str(e)
                    revertir = self.ejecutor._aplicar_scope_temporal(cambios)
                    
                    try:
                        for sentencia in bloque_capturar.hijos:
                            self.interpretar(sentencia)
                    finally:
                        revertir()
                    
                    break
            
            if not error_manejado:
                raise
        except LanzarException as e:
            error_manejado = False
            valor_para_variable = str(e.valor)

            for capturar in bloques_capturar.hijos:
                tipo_error = capturar.valor
                variable_error = capturar.hijos[0].valor
                bloque_capturar = capturar.hijos[1]

                if tipo_error is None or self._error_coincide(e, tipo_error):
                    error_manejado = True

                    cambios = {}
                    if variable_error:
                        cambios[variable_error] = valor_para_variable
                    revertir = self.ejecutor._aplicar_scope_temporal(cambios)

                    try:
                        for sentencia in bloque_capturar.hijos:
                            self.interpretar(sentencia)
                    finally:
                        revertir()

                    break

            if not error_manejado:
                raise
        
        finally:
            for sentencia in bloque_finally.hijos:
                self.interpretar(sentencia)
        
        return resultado

    def _error_coincide(self, error, tipo_nombre):
        """Verifica si un error coincide con el tipo esperado"""
        tipos = {
            "ErrorTipo":       ErrorTipo,
            "ErrorValor":      ErrorValor,
            "ErrorIndice":     ErrorIndice,
            "ErrorAtributo":   ErrorAtributo,
            "ErrorImportacion": ErrorImportacion,
            "ErrorMatematico": ErrorMatematico,
            "RuntimeError":    RuntimeError,
        }

        if tipo_nombre in tipos:
            return isinstance(error, tipos[tipo_nombre])

        return False

    def _ejecutar_lanzar(self, nodo):
        """Ejecuta la instrucción lanzar"""
        tipo_error = nodo.hijos[0].valor
        nodo_mensaje = nodo.hijos[1]

        mensaje = self.evaluador.evaluar(nodo_mensaje.hijos[0]) if nodo_mensaje.hijos else ""

        errores_map = {
            "ErrorTipo":       ErrorTipo,
            "ErrorValor":      ErrorValor,
            "ErrorIndice":     ErrorIndice,
            "ErrorAtributo":   ErrorAtributo,
            "ErrorImportacion": ErrorImportacion,
            "ErrorMatematico": ErrorMatematico,
            "RuntimeError":    RuntimeError,
        }

        if tipo_error and tipo_error in errores_map:
            raise errores_map[tipo_error](str(mensaje), linea=nodo.linea)

        if tipo_error:
            raise RuntimeError(f"{tipo_error}: {mensaje}", linea=nodo.linea)

        raise RuntimeError(str(mensaje), linea=nodo.linea)

    def _ejecutar_importar(self, nodo):
        """Ejecuta 'importar modulo [como alias]'"""
        nombre_modulo = nodo.valor
        alias_nodo = nodo.hijos[0] if nodo.hijos else None
        alias = alias_nodo.valor if (alias_nodo and alias_nodo.valor) else nombre_modulo.split(".")[-1]

        ruta_modulo = self._resolver_ruta_modulo(nombre_modulo, nodo.linea)

        if ruta_modulo in self._pila_importando:
            ciclo = " -> ".join(self._pila_importando + [ruta_modulo])
            raise ErrorImportacion(f"Importación circular detectada: {ciclo}", linea=nodo.linea)

        if ruta_modulo not in self._cache_modulos:
            self._pila_importando.append(ruta_modulo)
            try:
                self._cache_modulos[ruta_modulo] = self._cargar_modulo(ruta_modulo, nodo.linea)
            finally:
                self._pila_importando.pop()

        self.variables[alias] = self._cache_modulos[ruta_modulo]

    def _buscar_candidato_en(self, base, partes):
        """Busca 'partes' (nombre_modulo.split('.')) directamente dentro de
        'base', sin asumir ninguna subcarpeta especial (ni 'librerias').
        Soporta tanto un archivo suelto (modulo.wn) como notación de
        paquete (carpeta.modulo -> carpeta/modulo.wn o carpeta/modulo/modulo.wn).
        Retorna la ruta absoluta si la encuentra, o None."""
        if not base:
            return None

        ruta_directa = os.path.join(base, *partes)
        extensiones = [".wn", ".py"] + list(importlib.machinery.EXTENSION_SUFFIXES)
        for ext in extensiones:
            candidato = ruta_directa + ext
            if os.path.exists(candidato):
                return os.path.abspath(candidato)

        if len(partes) > 1:
            ruta_paquete = os.path.join(base, *partes[:-1], partes[-1])
            for ext in extensiones:
                candidato = ruta_paquete + ext
                if os.path.exists(candidato):
                    return os.path.abspath(candidato)

        return None

    def _resolver_ruta_modulo(self, nombre_modulo, linea):
        """Convierte 'carpeta.modulo' en una ruta .wn, .py o extensión nativa.

        Busca en, por orden de prioridad:
        1. Junto al archivo .wn que hace la importación (self.directorio) y
           en el directorio de trabajo actual — igual que Python antepone
           la carpeta del script a sys.path, esto permite tener módulos
           locales al lado del script principal sin pasar por 'librerias/'.
        2. Carpeta 'librerias/' junto al archivo actual
        3. Carpeta 'librerias/' en el directorio de trabajo
        4. Carpeta 'librerias/' junto al ejecutable (.exe)
        """
        partes = nombre_modulo.split(".")

        # 1) Resolución LOCAL, al estilo Python: primero se busca el módulo
        # directamente junto al script (y en el cwd), sin 'librerias/' de
        # por medio. Esto es lo que hacía falta para poder importar
        # módulos locales (p. ej. 'importar utilidades' con
        # utilidades.wn en la misma carpeta que el script principal).
        for base_local in (self.directorio, os.getcwd()):
            encontrado = self._buscar_candidato_en(base_local, partes)
            if encontrado:
                return encontrado

        # Obtener carpeta del ejecutable
        try:
            carpeta_ejecutable = __compiled__.containing_dir
        except NameError:
            carpeta_ejecutable = os.path.dirname(os.path.abspath(sys.argv[0]))

        try:
            carpeta_ejecutable_pyinstaller = os.path.join(os.path.dirname(sys.executable), "_internal\\librerias")
            if os.path.exists(carpeta_ejecutable_pyinstaller):
                carpeta_ejecutable = carpeta_ejecutable_pyinstaller
        except Exception:
            pass
        
        # Bases de búsqueda (orden de prioridad) — comportamiento tipo
        # "librería estándar": todo lo que esté en <base>/librerias/
        bases = [
            self.directorio,                    # Carpeta del archivo .wn actual
            os.getcwd(),                        # Directorio de trabajo actual
            carpeta_ejecutable,
            carpeta_ejecutable_pyinstaller,      # Carpeta donde está el .exe
        ]
        
        # Construir rutas candidatas
        for base in bases:
            if not base:
                continue
                
            # Buscar en: base/librerias/modulo.wn
            ruta_librerias = os.path.join(base, "librerias")
            encontrado = self._buscar_candidato_en(ruta_librerias, partes)
            if encontrado:
                return encontrado
        
        # Mostrar dónde se buscó (para debug)
        ejemplos = [
            f"'{os.path.join(self.directorio, *partes)}.wn' (local)",
            f"'{os.path.join(os.getcwd(), *partes)}.wn' (local, cwd)",
        ]
        for base in bases[:2]:
            if base:
                ejemplos.append(f"'{os.path.join(base, 'librerias', *partes)}.wn'")
        
        raise ErrorImportacion(
            f"No se pudo encontrar el módulo '{nombre_modulo}'. "
            f"Buscado en: {', '.join(ejemplos[:5])}...",
            linea=linea
        )

    def _cargar_modulo(self, ruta, linea):
        """Carga un módulo .wn (sub-intérprete) o una librería nativa (.py/.pyd/.so/.dll)."""
        ext = os.path.splitext(ruta)[1].lower()
        if ext in {".py", ".pyd", ".so", ".dll"} or any(ruta.endswith(suf) for suf in importlib.machinery.EXTENSION_SUFFIXES):
            return self._cargar_modulo_nativo(ruta, linea)
        return self._cargar_modulo_wini(ruta, linea)

    def _cargar_modulo_nativo(self, ruta, linea):
        """Carga una librería nativa (.py, .pyd, .so, .dll) desde cualquier ubicación."""
        # Obtener nombre del módulo desde la ruta
        nombre_mod = os.path.splitext(os.path.basename(ruta))[0]
        directorio_modulo = os.path.dirname(os.path.abspath(ruta))
        sys_path_original = list(sys.path)
        
        # Hacer visible el directorio del módulo nativo para importaciones
        # de módulos hermanos como .pyd/.so o archivos Python adyacentes.
        if directorio_modulo not in sys.path:
            sys.path.insert(0, directorio_modulo)
        
        try:
            spec = importlib.util.spec_from_file_location(nombre_mod, ruta)
            if spec is None or spec.loader is None:
                raise ImportError(f"No se pudo crear un spec para '{ruta}'")
            modulo_py = importlib.util.module_from_spec(spec)
            sys.modules[nombre_mod] = modulo_py
            spec.loader.exec_module(modulo_py)
        except Exception as e:
            raise ErrorImportacion(f"No se pudo cargar la librería nativa '{ruta}': {e}", linea=linea)
        finally:
            sys.path[:] = sys_path_original
        
        # Exponer funciones según convención __func_wlib
        funciones = getattr(modulo_py, "__func_wlib", None)
        if not isinstance(funciones, dict):
            funciones = {
                nombre: valor for nombre, valor in vars(modulo_py).items()
                if callable(valor) and not nombre.startswith("_")
            }
        
        variables = {
            nombre: valor for nombre, valor in vars(modulo_py).items()
            if not nombre.startswith("_") and not callable(valor)
            and not isinstance(valor, type(os))
        }
        
        return {
            "_tipo": "modulo",
            "_ruta": ruta,
            "_nombre": nombre_mod,
            "_nativo": True,
            "funciones": funciones,
            "variables": variables,
        }

    def _cargar_modulo_wini(self, ruta, linea):
        """Ejecuta el archivo .wn del módulo en un sub-intérprete aislado y
        devuelve un diccionario con sus funciones y variables."""
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                codigo = f.read()
        except OSError as e:
            raise ErrorImportacion(f"No se pudo leer el módulo '{ruta}': {e}", linea=linea)

        sub_interprete = Interprete(ruta, _cache_modulos=self._cache_modulos, _pila_importando=self._pila_importando)

        try:
            tokens = lexer(codigo)
            parser = Parser(tokens)
            ast = parser.parse()
            sub_interprete.interpretar(ast)
        except (SintaxisError, RuntimeError, ErrorImportacion) as e:
            mensaje = e.mensaje if hasattr(e, "mensaje") else str(e)
            raise ErrorImportacion(f"Error al importar '{os.path.basename(ruta)}': {mensaje}", linea=linea)

        # Foto de las variables de nivel superior del módulo (incluye los
        # alias creados con 'importar X como alias' dentro del propio
        # módulo, como 'std'). Se adjunta a cada función/método definido en
        # el módulo para que, al ejecutarse desde OTRO intérprete (el que
        # hace 'modulo.funcion(...)'), tenga acceso a ese scope: si no,
        # 'std' (u otras variables del módulo) no existirían en el
        # namespace del llamador y fallaría con "Variable 'std' no definida".
        modulo_vars = dict(sub_interprete.variables)

        funciones_modulo = {k: v for k, v in sub_interprete.funciones.items() if k != "rango"}
        for funcion_def in funciones_modulo.values():
            if isinstance(funcion_def, dict):
                funcion_def["_modulo_variables"] = modulo_vars

        return {
            "_tipo": "modulo",
            "_ruta": ruta,
            "_nombre": os.path.splitext(os.path.basename(ruta))[0],
            "funciones": funciones_modulo,
            "variables": modulo_vars,
        }


    def _rango_nativo(self, *args):
        """Función nativa rango() que devuelve una lista de números"""
        try:
            if len(args) == 1:
                return list(range(int(args[0])))
            elif len(args) == 2:
                return list(range(int(args[0]), int(args[1])))
            elif len(args) == 3:
                return list(range(int(args[0]), int(args[1]), int(args[2])))
            else:
                raise RuntimeError("rango() espera entre 1 y 3 argumentos")
        except ValueError as e:
            raise RuntimeError("Los argumentos de rango() deben ser números")