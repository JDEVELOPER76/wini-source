# ejecutor.py - VERSIÓN SIN IMPORTACIONES
"""Ejecución de funciones y métodos en el intérprete wini - SIN IMPORTACIONES"""

from exepciones import RuntimeError, RetornoException
from metodos_nativos import METODOS_LISTA, METODOS_CADENA, METODOS_DICCIONARIO

def formatear_texto(valor):
    """Convierte valores a texto para escribir e interpolación."""
    if valor is None:
        return "nulo"
    if isinstance(valor, bool):
        return "verdadero" if valor else "falso"
    if isinstance(valor, str):
        return valor
    if isinstance(valor, list):
        elementos_formateados = [formatear_texto(elem) for elem in valor]
        return "[" + ", ".join(elementos_formateados) + "]"
    if isinstance(valor, dict):
        pares = []
        for k, v in valor.items():
            pares.append(f"{formatear_texto(k)}: {formatear_texto(v)}")
        return "{" + ", ".join(pares) + "}"
    return str(valor)



class Ejecutor:
    """Encapsula la lógica de ejecución de funciones y métodos"""
    
    def __init__(self, interprete):
        self.interprete = interprete

    def _normalizar_retorno(self, valor):
        """Convierte retornos Python básicos al formato esperado por Wini."""
        return valor
    
    _SENTINEL = object()
    _CENTINELA_SCOPE = object()

    def _aplicar_scope_temporal(self, cambios):
        """Aplica `cambios` (dict nombre->valor) sobre self.interprete.variables
        y devuelve una función `revertir()` que deja el dict exactamente como
        estaba, pero SOLO tocando las claves modificadas (no copia todo el
        diccionario como antes). Esto evita el costo O(nº total de variables)
        que se pagaba en cada llamada a función/método."""
        variables = self.interprete.variables
        guardado = {}
        for k, v in cambios.items():
            if k not in guardado:
                guardado[k] = variables.get(k, self._CENTINELA_SCOPE)
            variables[k] = v

        def revertir():
            for k, v in guardado.items():
                if v is self._CENTINELA_SCOPE:
                    variables.pop(k, None)
                else:
                    variables[k] = v
        return revertir

    def _ejecutar_metodo_nativo(self, objeto, metodo_nombre, argumentos, nombrados=None, nodo=None):
        """Ejecuta un método nativo sobre un objeto básico (str, list o dict)"""
        nombrados = nombrados or {}
        if isinstance(objeto, list) and metodo_nombre in METODOS_LISTA:
            metodo = METODOS_LISTA[metodo_nombre]
            try:
                return metodo(objeto, *argumentos, **nombrados)
            except TypeError as e:
                raise RuntimeError(f"Error al ejecutar método nativo '{metodo_nombre}' en lista: {e}", linea=nodo.linea)
        
        if isinstance(objeto, str) and metodo_nombre in METODOS_CADENA:
            metodo = METODOS_CADENA[metodo_nombre]
            try:
                return metodo(objeto, *argumentos, **nombrados)
            except TypeError as e:
                raise RuntimeError(f"Error al ejecutar método nativo '{metodo_nombre}' en cadena: {e}", linea=nodo.linea)
        
        # Métodos nativos para diccionarios (excluir módulos)
        if isinstance(objeto, dict) and metodo_nombre in METODOS_DICCIONARIO:
            metodo = METODOS_DICCIONARIO[metodo_nombre]
            try:
                return metodo(objeto, *argumentos, **nombrados)
            except TypeError as e:
                raise RuntimeError(f"Error al ejecutar método nativo '{metodo_nombre}' en diccionario: {e}", linea=nodo.linea)
        
        return self._SENTINEL

    def _evaluar_argumentos(self, nodos):
        """Evalúa los nodos de una lista de argumentos de una llamada,
        separando los posicionales de los nombrados (identificador=valor).
        Retorna (posicionales: list, nombrados: dict)."""
        posicionales = []
        nombrados = {}
        for nodo_arg in nodos:
            if nodo_arg.tipo == "ARG_NOMBRADO":
                nombre_arg = nodo_arg.valor
                if nombre_arg in nombrados:
                    raise RuntimeError(
                        f"El argumento con nombre '{nombre_arg}' está repetido en la llamada",
                        linea=nodo_arg.linea
                    )
                nombrados[nombre_arg] = self.interprete.evaluador.evaluar(nodo_arg.hijos[0])
            else:
                posicionales.append(self.interprete.evaluador.evaluar(nodo_arg))
        return posicionales, nombrados

    def _vincular_parametros(self, parametros, posicionales, nombrados, nodo, contexto="la función"):
        """Empareja argumentos posicionales y con nombre con la lista de
        parámetros declarados (nombres de string). Los parámetros que no
        reciben ningún valor (ni posicional ni con nombre) quedan en None
        (nulo), lo que permite llamadas parciales como alguna(genial="si").
        Retorna la lista de valores en el mismo orden que 'parametros'."""
        if len(posicionales) > len(parametros):
            raise RuntimeError(
                f"{contexto} espera como máximo {len(parametros)} argumentos, "
                f"pero recibió {len(posicionales)} posicionales",
                linea=nodo.linea
            )

        valores = {}
        for nombre_param, valor in zip(parametros, posicionales):
            valores[nombre_param] = valor

        for nombre_arg, valor in nombrados.items():
            if nombre_arg not in parametros:
                raise RuntimeError(
                    f"{contexto} no tiene un parámetro llamado '{nombre_arg}'",
                    linea=nodo.linea
                )
            if nombre_arg in valores:
                raise RuntimeError(
                    f"El parámetro '{nombre_arg}' recibió un valor posicional y con nombre a la vez",
                    linea=nodo.linea
                )
            valores[nombre_arg] = valor

        return [valores.get(p, None) for p in parametros]

    def ejecutar_funcion(self, nodo):
        """Ejecuta una llamada a función"""
        nombre = nodo.valor
        posicionales, nombrados = self._evaluar_argumentos(nodo.hijos)

        # Llamada a función definida por el usuario
        if nombre in self.interprete.funciones:
            return self._ejecutar_funcion_usuario(nombre, posicionales, nombrados, nodo)
        
        # Funciones nativas (no admiten argumentos con nombre)
        if nombrados:
            raise RuntimeError(
                f"La función nativa '{nombre}' no admite argumentos con nombre",
                linea=nodo.linea
            )
        return self._ejecutar_funcion_nativa(nombre, posicionales, nodo)

    def _ejecutar_funcion_usuario(self, nombre, posicionales, nombrados, nodo):
        """Ejecuta una función definida por el usuario"""
        funcion_def = self.interprete.funciones[nombre]
        return self._ejecutar_funcion_wini(funcion_def, posicionales, nodo, nombre, nombrados=nombrados)
    
    def _ejecutar_funcion_wini(self, funcion_def, posicionales, nodo, nombre="<función>", nombrados=None):
        """Ejecuta una función Wini dada su definición"""
        nombrados = nombrados or {}

        # Si es una función nativa Python (callable)
        if callable(funcion_def) and not isinstance(funcion_def, dict):
            try:
                return self._normalizar_retorno(funcion_def(*posicionales, **nombrados))
            except TypeError as e:
                raise RuntimeError(f"Error al llamar función '{nombre}': {e}", linea=nodo.linea)
        
        # Si es una función definida en Wini (diccionario)
        parametros = funcion_def["parametros"]
        cuerpo = funcion_def["cuerpo"]
        argumentos = self._vincular_parametros(
            parametros, posicionales, nombrados, nodo,
            contexto=f"La función '{nombre}'"
        )
        
        # Si la función pertenece a un módulo importado, primero cargamos
        # su scope de nivel de módulo (p.ej. alias creados con
        # 'importar X como alias' dentro de ese módulo, como 'std'). Sin
        # esto, al ejecutar el cuerpo con el namespace del intérprete que
        # LLAMA a la función (no el del módulo donde se definió), esos
        # nombres no existirían y fallaría con "Variable 'std' no definida".
        modulo_variables = funcion_def.get("_modulo_variables")
        cambios = dict(modulo_variables) if modulo_variables else {}
        for param, arg in zip(parametros, argumentos):
            cambios[param] = arg

        revertir = self._aplicar_scope_temporal(cambios)

        resultado = None
        try:
            for sentencia in cuerpo:
                self.interprete.interpretar(sentencia)
        except RetornoException as e:
            resultado = e.valor
        finally:
            revertir()
        return resultado
    
    def _ejecutar_funcion_nativa(self, nombre, argumentos, nodo):
        """Ejecuta funciones nativas del intérprete"""
        if nombre == "escribir":
            for arg in argumentos:
                print(formatear_texto(arg))
            return None
        elif nombre == "leer":
            if len(argumentos) == 0:
                return input()
            elif len(argumentos) == 1:
                print(argumentos[0], end="")
                return input()
            else:
                raise RuntimeError(
                    f"La función 'leer' espera 0 o 1 argumento, "
                    f"pero recibió {len(argumentos)}",
                    linea=nodo.linea
                )
        elif nombre == "tipo":
            if len(argumentos) != 1:
                raise RuntimeError(
                    f"La función 'tipo' espera 1 argumento, "
                    f"pero recibió {len(argumentos)}",
                    linea=nodo.linea
                )
            valor = argumentos[0]
            
            if isinstance(valor, str):
                return "cadena"
            elif isinstance(valor, list):
                return "lista"
            elif isinstance(valor, bool):
                return "booleano"
            elif isinstance(valor, int):
                return "entero"
            elif isinstance(valor, float):
                return "decimal"
            elif isinstance(valor, dict):
                return "diccionario"
            elif valor is None:
                return "ninguno"
            else:
                return type(valor).__name__
        
        return None

    def ejecutar_metodo(self, nodo):
        """Ejecuta un método sobre el resultado de CUALQUIER expresión: obj.metodo(args)
        (obj puede ser una variable, otra llamada, un literal, otro encadenamiento, etc.)"""
        metodo_nombre = nodo.valor
        nodo_objeto = nodo.hijos[0]
        argumentos_nodos = nodo.hijos[1:]
        posicionales, nombrados = self._evaluar_argumentos(argumentos_nodos)

        objeto = self.interprete.evaluador.evaluar(nodo_objeto)

        # Llamadas sobre un módulo importado: modulo.funcion(args)
        if isinstance(objeto, dict) and objeto.get("_tipo") == "modulo":
            return self._ejecutar_llamada_modulo(objeto, metodo_nombre, posicionales, nombrados, nodo)

        # Para tipos básicos (str, list, dict), buscar en métodos nativos
        resultado_nativo = self._ejecutar_metodo_nativo(objeto, metodo_nombre, posicionales, nombrados, nodo)
        if resultado_nativo is not self._SENTINEL:
            return resultado_nativo

        raise RuntimeError(f"No se puede llamar '{metodo_nombre}' sobre un valor de tipo {type(objeto).__name__}", linea=nodo.linea)
    
    def _ejecutar_llamada_modulo(self, modulo, nombre, posicionales, nombrados, nodo):
        """Ejecuta 'modulo.nombre(args)': llama a una función del módulo"""
        funciones = modulo.get("funciones", {})
        if nombre in funciones:
            return self._ejecutar_funcion_wini(funciones[nombre], posicionales, nodo, nombre, nombrados=nombrados)

        raise RuntimeError(
            f"El módulo '{modulo.get('_nombre', '?')}' no tiene función '{nombre}'",
            linea=nodo.linea
        )