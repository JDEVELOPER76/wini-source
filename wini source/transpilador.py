# transpilador.py
"""Trasquilador (transpilador) de Wini (.wn) a Python (.py).

Uso:
    python wn2py.py entrada.wn [-o salida.py]

Estrategia:
    1. Reutiliza el lexer y el parser reales de Wini para obtener el AST
       (Nodo) exactamente como lo vería el intérprete.
    2. Recorre ese AST generando código Python línea por línea.
    3. Antepone un pequeño "runtime" (runtime_shim.py) que reproduce las
       semánticas propias de Wini que no tienen equivalente directo en
       Python (escribir/leer/tipo, métodos nativos en español sobre
       listas/cadenas/diccionarios, formateo de valores, errores con
       nombres en español, etc.)

Limitaciones conocidas (se marcan con comentarios TODO en la salida):
    - 'paquete' (namespaces de paquete estilo .wipy) no se traduce
      automáticamente: requiere adaptación manual.
    - 'importar modulo [como alias]' SÍ se traduce: el módulo referenciado
      (otro archivo .wn, resuelto junto al archivo de entrada) se
      re-transpila recursivamente y se incrusta en el mismo .py de salida
      como una función de carga que devuelve un namespace (SimpleNamespace)
      con sus funciones/variables. El resultado sigue siendo un
      único archivo .py autocontenido. Se detectan importaciones
      circulares en tiempo de transpilación (error, no recursión infinita).
    - 'lanzar TipoDesconocido("msg")' con un tipo de error no reconocido
      (que no sea uno de los tipos incorporados) se traduce a una
      excepción genérica con el nombre como prefijo del mensaje.
    - La restauración de la variable de 'para' al valor que tenía antes
      del bucle (shadowing) no se reproduce; en Python la variable queda
      con el último valor iterado, como es habitual en el lenguaje.
"""

import os
import re
import sys
from parser import Parser
from lexer import lexer
from exepciones import SintaxisError


def _directorio_ejecutable():
    """Carpeta donde vive el .exe (o el script) real. Ver interprete.py."""
    try:
        return __compiled__.containing_dir
    except NameError:
        pass
    try:
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    except Exception:
        return os.getcwd()


INDENT = "    "


def _es_identificador(nombre):
    return isinstance(nombre, str) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", nombre)


class ErrorTranspilacion(Exception):
    pass


class Transpilador:
    def __init__(self, ruta_archivo=None):
        self.avisos = []  # limitaciones encontradas, para reportar al usuario

        # ---- Soporte de 'importar modulo [como alias]' ----
        # Directorio base para resolver imports relativos al archivo actual
        # (cambia temporalmente mientras se transpila un módulo importado,
        # para que SUS imports se resuelvan relativos a SU propia ubicación).
        self.directorio = os.path.dirname(os.path.abspath(ruta_archivo)) if ruta_archivo else None
        self.directorio_ejecutable = _directorio_ejecutable()
        self._modulos_generados = {}  # ruta_absoluta -> nombre_funcion_carga
        self._modulos_orden = []      # bloques de código (listas de líneas), en orden de generación
        self._pila_importando = []    # rutas en proceso de transpilación (detección de ciclos)

    # ------------------------------------------------------------------
    # Punto de entrada
    # ------------------------------------------------------------------
    def transpilar_codigo(self, codigo_wn):
        tokens = lexer(codigo_wn)
        ast = Parser(tokens).parse()
        cuerpo = self._gen_bloque(ast.hijos, 0)
        return "\n".join(cuerpo) if cuerpo else "pass"

    # ------------------------------------------------------------------
    # Utilidades de generación
    # ------------------------------------------------------------------
    def _ln(self, indent, texto):
        return f"{INDENT * indent}{texto}"

    def _gen_bloque(self, sentencias, indent):
        lineas = []
        for s in sentencias:
            lineas.extend(self._gen_stmt(s, indent))
        if not lineas:
            lineas = [self._ln(indent, "pass")]
        return lineas

    def _nombre(self, ident):
        return ident

    def _py_string_literal(self, texto_decodificado):
        """Genera un literal Python triple-comillas seguro a partir de texto ya
        decodificado (con saltos de línea, tabs, etc. reales)."""
        escapado = texto_decodificado.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
        return f'"""{escapado}"""'

    def _decodificar_escapes(self, texto):
        escapes = {
            "\\n": "\n", "\\t": "\t", "\\r": "\r",
            "\\\\": "\\", "\\\"": '"', "\\'": "'",
        }
        resultado = []
        i = 0
        while i < len(texto):
            if texto[i] == "\\" and i + 1 < len(texto):
                par = texto[i:i + 2]
                if par in escapes:
                    resultado.append(escapes[par])
                    i += 2
                    continue
            resultado.append(texto[i])
            i += 1
        return "".join(resultado)

    # ------------------------------------------------------------------
    # Sentencias
    # ------------------------------------------------------------------
    def _gen_stmt(self, nodo, indent):
        tipo = nodo.tipo

        if tipo == "FUNCION":
            return self._gen_funcion(nodo, indent)

        if tipo == "SI":
            return self._gen_si(nodo, indent)

        if tipo == "MIENTRAS":
            cond = self._gen_expr(nodo.hijos[0])
            cabecera = [self._ln(indent, f"while {cond}:")]
            return cabecera + self._gen_bloque(nodo.hijos[1].hijos, indent + 1)

        if tipo == "PARA":
            var = self._nombre(nodo.hijos[0].valor)
            iterable = self._gen_expr(nodo.hijos[1])
            cabecera = [self._ln(indent, f"for {var} in _wn_iter({iterable}):")]
            return cabecera + self._gen_bloque(nodo.hijos[2].hijos, indent + 1)

        if tipo == "ROMPER":
            return [self._ln(indent, "break")]

        if tipo == "CONTINUAR":
            return [self._ln(indent, "continue")]

        if tipo == "RETORNO":
            expr = self._gen_expr(nodo.hijos[0]) if nodo.hijos else "None"
            return [self._ln(indent, f"return {expr}")]

        if tipo == "ASIGNACION":
            expr = self._gen_expr(nodo.hijos[0])
            return [self._ln(indent, f"{self._nombre(nodo.valor)} = {expr}")]

        if tipo == "ASIGNACION_INDEX":
            obj = self._nombre(nodo.valor)
            idx = self._gen_expr(nodo.hijos[0])
            expr = self._gen_expr(nodo.hijos[1])
            return [self._ln(indent, f"_wn_setitem({obj}, {idx}, {expr})")]

        if tipo in ("LLAMADA", "LLAMADA_METODO"):
            return [self._ln(indent, self._gen_expr(nodo))]

        if tipo == "INTENTAR":
            return self._gen_intentar(nodo, indent)

        if tipo == "LANZAR":
            tipo_error = nodo.hijos[0].valor
            nodo_msj = nodo.hijos[1]
            msj = self._gen_expr(nodo_msj.hijos[0]) if nodo_msj.hijos else '""'
            tipo_lit = f'"{tipo_error}"' if tipo_error else "None"
            return [self._ln(indent, f"_wn_lanzar({tipo_lit}, {msj})")]

        if tipo == "IMPORTAR":
            return self._gen_importar(nodo, indent)

        if tipo == "PAQUETE":
            self.avisos.append(
                f"Línea {nodo.linea}: 'paquete' no se tradujo automáticamente "
                f"(sistema de paquetes de Wini); revisa e impórtalo manualmente."
            )
            return [self._ln(indent, f"# TODO: paquete(...) no soportado automáticamente por wn2py (línea {nodo.linea})")]

        # Cualquier otra cosa que llegue aquí como sentencia suelta: tratarla como expresión
        return [self._ln(indent, self._gen_expr(nodo))]

    def _gen_funcion(self, nodo, indent):
        nombre = nodo.valor
        params_nodos = nodo.hijos[0].hijos
        params = [self._nombre(p.valor) for p in params_nodos]
        # Cada parámetro recibe un valor por defecto 'None' en la firma de
        # Python generada, igual que hace el intérprete: así se admiten
        # llamadas parciales/con nombre como alguna(genial="si").
        params_con_defecto = [f"{p}=None" for p in params]
        cuerpo = nodo.hijos[1].hijos
        docstring = getattr(nodo, "docstring", None)

        cabecera = [self._ln(indent, f"def {nombre}({', '.join(params_con_defecto)}):")]
        cuerpo_lineas = []
        if docstring:
            cuerpo_lineas.append(self._ln(indent + 1, self._py_string_literal(docstring)))
        cuerpo_lineas.extend(self._gen_bloque(cuerpo, indent + 1))
        return cabecera + cuerpo_lineas

    def _gen_si(self, nodo, indent):
        cond = self._gen_expr(nodo.hijos[0])
        bloque_si = nodo.hijos[1].hijos
        bloque_sino = nodo.hijos[2].hijos

        lineas = [self._ln(indent, f"if {cond}:")]
        lineas.extend(self._gen_bloque(bloque_si, indent + 1))
        if bloque_sino:
            lineas.append(self._ln(indent, "else:"))
            lineas.extend(self._gen_bloque(bloque_sino, indent + 1))
        return lineas

    _MAPA_TIPOS_ERROR = {
        "ErrorTipo", "ErrorValor", "ErrorIndice", "ErrorAtributo",
        "ErrorImportacion", "ErrorMatematico", "RuntimeError",
    }

    # ------------------------------------------------------------------
    # 'importar modulo [como alias]'
    # ------------------------------------------------------------------
    def _gen_importar(self, nodo, indent):
        nombre_modulo = nodo.valor
        alias_nodo = nodo.hijos[0] if nodo.hijos else None
        alias = (self._nombre(alias_nodo.valor) if (alias_nodo and alias_nodo.valor)
                 else nombre_modulo.split(".")[-1])

        ruta = self._resolver_ruta_modulo(nombre_modulo, nodo.linea)
        nombre_funcion = self._transpilar_modulo(ruta, nodo.linea)
        return [self._ln(indent, f"{alias} = {nombre_funcion}()")]

    def _resolver_ruta_modulo(self, nombre_modulo, linea):
        """Convierte 'carpeta.modulo' en una ruta .wn (o .py).
        Busca en directorio actual y en carpeta 'librerias/'."""
        partes = nombre_modulo.split(".")
        base = self.directorio if self.directorio else os.getcwd()

        raices = (base, os.getcwd(), self.directorio_ejecutable)
        candidatos = []
        
        # Módulo local
        for raiz in raices:
            candidatos.append(os.path.join(raiz, *partes) + ".wn")
            candidatos.append(os.path.join(raiz, *partes) + ".py")
        
        # En librerias/
        for raiz in raices:
            ruta_lib = os.path.join(raiz, "librerias")
            candidatos.append(os.path.join(ruta_lib, *partes) + ".wn")
            candidatos.append(os.path.join(ruta_lib, *partes) + ".py")
        
        # Caso especial: módulo dentro de carpeta con mismo nombre
        if len(partes) > 0:
            ultimo = partes[-1]
            for raiz in raices:
                ruta_lib = os.path.join(raiz, "librerias")
                ruta_carpeta = os.path.join(ruta_lib, *partes[:-1], ultimo)
                candidatos.append(os.path.join(ruta_carpeta, ultimo) + ".wn")
                candidatos.append(os.path.join(ruta_carpeta, ultimo) + ".py")
        
        for candidato in candidatos:
            if os.path.exists(candidato):
                return os.path.abspath(candidato)
        
        raise ErrorTranspilacion(
            f"No se pudo encontrar el módulo '{nombre_modulo}' "
            f"(buscado en librerias/ y directorio actual) (línea {linea})"
        )

    def _transpilar_modulo(self, ruta, linea):
        """Registra (una sola vez, con caché) el módulo de 'ruta' como una
        función de carga '_wn_cargar_modulo_N' incrustada en el .py final.
        Despacha entre módulo Wini (.wn, se re-transpila recursivamente) y
        librería nativa (.py, se incrusta y ejecuta tal cual). Devuelve el
        nombre de esa función."""
        if ruta in self._modulos_generados:
            return self._modulos_generados[ruta]

        if ruta.endswith(".py"):
            return self._transpilar_modulo_nativo(ruta, linea)
        return self._transpilar_modulo_wini(ruta, linea)

    def _transpilar_modulo_nativo(self, ruta, linea):
        """Incrusta una librería nativa Python (.py) en el .py final: su
        código fuente se guarda como texto y se ejecuta con exec() dentro de
        la función de carga, así el resultado sigue siendo un único archivo
        autocontenido (no depende de que ese .py exista en disco en tiempo
        de ejecución). Convención (igual que stdlib.py):
            - Si el archivo define '__func_wlib' ({"nombre_wini": fn, ...}),
              esas son las funciones expuestas al código Wini.
            - Si no, se exponen automáticamente las funciones/callables
              públicas del archivo (sin '_' inicial).
        """
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                codigo_fuente = f.read()
        except OSError as e:
            raise ErrorTranspilacion(f"No se pudo leer la librería nativa '{ruta}': {e} (línea {linea})")

        nombre_funcion = f"_wn_cargar_modulo_{len(self._modulos_generados)}"
        self._modulos_generados[ruta] = nombre_funcion

        clave = repr(ruta)
        literal_fuente = self._py_string_literal(codigo_fuente)

        lineas = [f"def {nombre_funcion}():"]
        lineas.append(self._ln(1, f"if {clave} in _wn_modulos_cache:"))
        lineas.append(self._ln(2, f"return _wn_modulos_cache[{clave}]"))
        lineas.append(self._ln(1, f"_wn_fuente_nativa = {literal_fuente}"))
        lineas.append(self._ln(1, "_wn_ns_nativo = {}"))
        lineas.append(self._ln(1, "import os"))
        lineas.append(self._ln(1, "import sys"))
        lineas.append(self._ln(1, f"_wn_directorio_modulo = os.path.dirname(os.path.abspath({clave}))"))
        lineas.append(self._ln(1, "_wn_sys_path_original = list(sys.path)"))
        lineas.append(self._ln(1, "if _wn_directorio_modulo not in sys.path:"))
        lineas.append(self._ln(2, "sys.path.insert(0, _wn_directorio_modulo)"))
        lineas.append(self._ln(1, "try:"))
        lineas.append(self._ln(2, f"exec(compile(_wn_fuente_nativa, {clave}, 'exec'), _wn_ns_nativo)"))
        lineas.append(self._ln(1, "finally:"))
        lineas.append(self._ln(2, "sys.path[:] = _wn_sys_path_original"))
        lineas.append(self._ln(1, "_wn_funcs = _wn_ns_nativo.get('__func_wlib')"))
        lineas.append(self._ln(1, "if not isinstance(_wn_funcs, dict):"))
        lineas.append(self._ln(2, "_wn_funcs = {k: v for k, v in _wn_ns_nativo.items() if callable(v) and not k.startswith('_')}"))
        lineas.append(self._ln(1, "_wn_mod = _wn_ns(**_wn_funcs)"))
        lineas.append(self._ln(1, f"_wn_modulos_cache[{clave}] = _wn_mod"))
        lineas.append(self._ln(1, "return _wn_mod"))

        self._modulos_orden.append(lineas)
        return nombre_funcion

    def _transpilar_modulo_wini(self, ruta, linea):
        """Transpila (una sola vez, con caché) el archivo .wn de 'ruta' y lo
        registra como una función de carga '_wn_cargar_modulo_N' que se
        incrusta en el .py final. Devuelve el nombre de esa función."""
        if ruta in self._pila_importando:
            ciclo = " -> ".join(self._pila_importando + [ruta])
            raise ErrorTranspilacion(f"Importación circular detectada: {ciclo} (línea {linea})")

        try:
            with open(ruta, "r", encoding="utf-8") as f:
                codigo = f.read()
        except OSError as e:
            raise ErrorTranspilacion(f"No se pudo leer el módulo '{ruta}': {e} (línea {linea})")

        nombre_funcion = f"_wn_cargar_modulo_{len(self._modulos_generados)}"
        self._modulos_generados[ruta] = nombre_funcion

        self._pila_importando.append(ruta)
        directorio_anterior = self.directorio
        self.directorio = os.path.dirname(ruta)
        try:
            tokens = lexer(codigo)
            ast = Parser(tokens).parse()
            bloque = self._gen_cuerpo_modulo(ast.hijos, nombre_funcion, ruta)
            self._modulos_orden.append(bloque)
        except SintaxisError as e:
            raise ErrorTranspilacion(f"Error de sintaxis al importar '{os.path.basename(ruta)}': {e}")
        finally:
            self._pila_importando.pop()
            self.directorio = directorio_anterior

        return nombre_funcion

    def _gen_cuerpo_modulo(self, hijos, nombre_funcion, ruta):
        """Genera:
            def _wn_cargar_modulo_N():
                if <ruta> in _wn_modulos_cache: return _wn_modulos_cache[<ruta>]
                ...cuerpo del módulo (funciones, variables, imports)...
                _wn_mod = _wn_ns(nombre1=nombre1, nombre2=nombre2, ...)
                _wn_modulos_cache[<ruta>] = _wn_mod
                return _wn_mod
        El caché evita re-ejecutar el módulo si se importa más de una vez
        (mismo comportamiento que el intérprete)."""
        clave = repr(ruta)
        lineas = [f"def {nombre_funcion}():"]
        lineas.append(self._ln(1, f"if {clave} in _wn_modulos_cache:"))
        lineas.append(self._ln(2, f"return _wn_modulos_cache[{clave}]"))
        lineas.extend(self._gen_bloque(hijos, 1))

        nombres = self._nombres_nivel_superior(hijos)
        asignaciones_ns = ", ".join(f"{n}={n}" for n in nombres)
        lineas.append(self._ln(1, f"_wn_mod = _wn_ns({asignaciones_ns})"))
        lineas.append(self._ln(1, f"_wn_modulos_cache[{clave}] = _wn_mod"))
        lineas.append(self._ln(1, "return _wn_mod"))
        return lineas

    def _nombres_nivel_superior(self, hijos):
        """Nombres definidos directamente en el nivel superior de un módulo
        (funciones, variables, alias de sub-imports): son los que se
        exponen en el namespace devuelto por la función de carga."""
        nombres = []
        for nodo in hijos:
            if nodo.tipo == "FUNCION":
                nombres.append(self._nombre(nodo.valor))
            elif nodo.tipo == "ASIGNACION":
                nombres.append(self._nombre(nodo.valor))
            elif nodo.tipo == "IMPORTAR":
                alias_nodo = nodo.hijos[0] if nodo.hijos else None
                alias = (alias_nodo.valor if (alias_nodo and alias_nodo.valor)
                          else nodo.valor.split(".")[-1])
                nombres.append(self._nombre(alias))

        vistos = set()
        resultado = []
        for n in nombres:
            if n not in vistos:
                vistos.add(n)
                resultado.append(n)
        return resultado

    def _gen_intentar(self, nodo, indent):
        bloque_try = nodo.hijos[0].hijos
        bloques_capturar = nodo.hijos[1].hijos
        bloque_finally = nodo.hijos[2].hijos

        lineas = [self._ln(indent, "try:")]
        lineas.extend(self._gen_bloque(bloque_try, indent + 1))

        if not bloques_capturar:
            # try sin capturar sólo tiene sentido si hay finally
            if bloque_finally:
                lineas.append(self._ln(indent, "finally:"))
                lineas.extend(self._gen_bloque(bloque_finally, indent + 1))
            return lineas

        for cap in bloques_capturar:
            tipo_error = cap.valor  # string o None
            var_nodo = cap.hijos[0]
            variable = var_nodo.valor
            bloque_cap = cap.hijos[1].hijos

            if tipo_error is None:
                cls_py = "Exception"
            elif tipo_error in self._MAPA_TIPOS_ERROR:
                cls_py = "WiniRuntimeError" if tipo_error == "RuntimeError" else tipo_error
            else:
                # Tipo de error no reconocido (no es uno de los tipos
                # incorporados ni pertenece a un módulo): no se traduce a
                # una excepción Python real -> se captura como Exception
                # y se avisa.
                self.avisos.append(
                    f"Línea {cap.linea}: 'capturar {tipo_error}' usa un tipo de error "
                    f"no reconocido; se generó 'except Exception' como aproximación."
                )
                cls_py = "Exception"

            tmp = "_exc"
            lineas.append(self._ln(indent, f"except {cls_py} as {tmp}:"))
            cuerpo_cap = []
            if variable:
                cuerpo_cap.append(self._ln(indent + 1, f"{self._nombre(variable)} = str({tmp})"))
            cuerpo_cap.extend(self._gen_bloque(bloque_cap, indent + 1))
            lineas.extend(cuerpo_cap)

        if bloque_finally:
            lineas.append(self._ln(indent, "finally:"))
            lineas.extend(self._gen_bloque(bloque_finally, indent + 1))

        return lineas

    # ------------------------------------------------------------------
    # Expresiones
    # ------------------------------------------------------------------
    _OPS_DIRECTOS = {
        "==": "==", "!=": "!=", "<>": "!=", "<": "<", ">": ">", "<=": "<=", ">=": ">=",
        "-": "-", "*": "*",
    }

    def _gen_expr(self, nodo):
        tipo = nodo.tipo

        if tipo == "ENTERO":
            return str(int(nodo.valor))
        if tipo == "DECIMAL":
            return str(float(nodo.valor))
        if tipo == "NINGUNO":
            return "None"
        if tipo == "BOOLEANO":
            return "True" if nodo.valor else "False"

        if tipo == "CADENA_TEXTO":
            texto = self._decodificar_escapes(str(nodo.valor))
            return self._py_string_literal(texto)

        if tipo == "CADENA_INTERPOLADA":
            return self._gen_interpolada(nodo)

        if tipo == "LISTA":
            elems = ", ".join(self._gen_expr(e) for e in nodo.hijos)
            return f"[{elems}]"

        if tipo == "DICCIONARIO":
            pares = []
            for par in nodo.hijos:
                k = self._gen_expr(par.hijos[0])
                v = self._gen_expr(par.hijos[1])
                pares.append(f"{k}: {v}")
            return "{" + ", ".join(pares) + "}"

        if tipo == "IDENTIFICADOR":
            return self._nombre(nodo.valor)

        if tipo == "ACCESO_ATRIBUTO":
            obj = self._gen_expr(nodo.hijos[0])
            attr = nodo.valor
            return f"{obj}.{attr}"

        if tipo == "INDEXACION":
            obj = self._gen_expr(nodo.hijos[0])
            idx = self._gen_expr(nodo.hijos[1])
            return f"_wn_getitem({obj}, {idx})"

        if tipo == "LLAMADA":
            return self._gen_llamada(nodo)

        if tipo == "LLAMADA_METODO":
            obj = self._gen_expr(nodo.hijos[0])
            metodo = nodo.valor
            args = ", ".join(self._gen_expr(a) for a in nodo.hijos[1:])
            sep = ", " if args else ""
            return f'_wn_metodo({obj}, "{metodo}"{sep}{args})'

        if tipo == "BINARIA":
            return self._gen_binaria(nodo)

        if tipo == "UNARIA":
            operando = self._gen_expr(nodo.hijos[0])
            return f"(-{operando})"

        if tipo == "LOGICO":
            return self._gen_logica(nodo)

        if tipo == "IN":
            izq = self._gen_expr(nodo.hijos[0])
            der = self._gen_expr(nodo.hijos[1])
            return f"_wn_in({izq}, {der})"

        if tipo == "ARG_NOMBRADO":
            # Solo válido dentro de una lista de argumentos de una llamada;
            # se traduce directamente a la sintaxis de kwargs de Python.
            valor = self._gen_expr(nodo.hijos[0])
            return f"{self._nombre(nodo.valor)}={valor}"

        raise ErrorTranspilacion(f"Nodo de expresión no soportado: {tipo} (línea {nodo.linea})")

    def _gen_llamada(self, nodo):
        nombre = nodo.valor
        args = ", ".join(self._gen_expr(a) for a in nodo.hijos)
        return f"{nombre}({args})"

    def _gen_binaria(self, nodo):
        op = nodo.valor
        izq = self._gen_expr(nodo.hijos[0])
        der = self._gen_expr(nodo.hijos[1])

        if op == "+":
            return f"_wn_add({izq}, {der})"
        if op == "/":
            return f"_wn_div({izq}, {der})"
        if op == "%":
            return f"_wn_mod({izq}, {der})"
        if op in self._OPS_DIRECTOS:
            return f"({izq} {self._OPS_DIRECTOS[op]} {der})"
        raise ErrorTranspilacion(f"Operador binario no soportado: {op} (línea {nodo.linea})")

    def _gen_logica(self, nodo):
        op = nodo.valor
        if op in ("no", "not"):
            expr = self._gen_expr(nodo.hijos[0])
            return f"(not _wn_verdadero({expr}))"
        izq = self._gen_expr(nodo.hijos[0])
        der = self._gen_expr(nodo.hijos[1])
        if op in ("y", "and"):
            return f"(_wn_verdadero({izq}) and _wn_verdadero({der}))"
        if op in ("o", "or"):
            return f"(_wn_verdadero({izq}) or _wn_verdadero({der}))"
        raise ErrorTranspilacion(f"Operador lógico no soportado: {op} (línea {nodo.linea})")

    def _gen_interpolada(self, nodo):
        texto = self._decodificar_escapes(nodo.valor)
        partes = []  # lista de ("lit", texto) o ("expr", codigo_python)
        i = 0
        buffer_lit = []
        while i < len(texto):
            c = texto[i]
            if c == "{":
                cierre = texto.find("}", i + 1)
                if cierre == -1:
                    raise ErrorTranspilacion(f"Cadena interpolada sin cerrar (línea {nodo.linea})")
                expr_src = texto[i + 1:cierre].strip()
                if buffer_lit:
                    partes.append(("lit", "".join(buffer_lit)))
                    buffer_lit = []
                if not expr_src:
                    raise ErrorTranspilacion(f"Interpolación vacía dentro de '{{}}' (línea {nodo.linea})")
                sub_tokens = lexer(expr_src)
                sub_ast = Parser(sub_tokens).parse()
                if not sub_ast.hijos:
                    codigo_py = "None"
                else:
                    codigo_py = self._gen_expr(sub_ast.hijos[0])
                partes.append(("expr", codigo_py))
                i = cierre + 1
            else:
                buffer_lit.append(c)
                i += 1
        if buffer_lit:
            partes.append(("lit", "".join(buffer_lit)))

        cuerpo_fstring = []
        for kind, valor in partes:
            if kind == "lit":
                escapado = (
                    valor.replace("\\", "\\\\")
                    .replace('"""', '\\"\\"\\"')
                    .replace("{", "{{")
                    .replace("}", "}}")
                )
                cuerpo_fstring.append(escapado)
            else:
                cuerpo_fstring.append("{_wn_fmt(" + valor + ")}")

        contenido = "".join(cuerpo_fstring)
        return f'f"""{contenido}"""'


def transpilar(codigo_wn, ruta_archivo=None):
    """Transpila código fuente Wini a código fuente Python (string).

    ruta_archivo: ruta del archivo .wn de entrada (permite resolver
    'importar modulo [como alias]' relativos a su ubicación). Si se omite,
    los 'importar' se resuelven relativos al directorio de trabajo actual.

    Retorna (codigo_python, lista_de_avisos)."""
    t = Transpilador(ruta_archivo)
    cuerpo_principal = t.transpilar_codigo(codigo_wn)

    partes = ["\n".join(bloque) for bloque in t._modulos_orden]
    partes.append(cuerpo_principal)

    codigo_final = "\n\n".join(partes)
    return codigo_final, t.avisos