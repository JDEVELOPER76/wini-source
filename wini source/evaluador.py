# evaluador.py
"""Evaluación de expresiones en el intérprete wini"""

from exepciones import *
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

def es_verdadero(valor):
    """Convierte cualquier valor a booleano según reglas típicas."""
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return valor != 0
    if isinstance(valor, str):
        return len(valor) > 0
    if isinstance(valor, list):
        return len(valor) > 0
    if isinstance(valor, dict):
        return len(valor) > 0
    if valor is None:
        return False
    if hasattr(valor, '__len__'):
        return len(valor) > 0
    return True

def contiene_interpolacion(texto):
    """Verifica si un texto contiene interpolaciones {}"""
    return "{" in texto and "}" in texto

def interpolar_cadena(texto, evaluar_fragmento_func):
    """Interpola variables en una cadena de texto."""
    resultado = []
    indice = 0
    while indice < len(texto):
        caracter = texto[indice]
        if caracter == "{":
            cierre = texto.find("}", indice + 1)
            if cierre == -1:
                from exepciones import RuntimeError
                raise RuntimeError("Cadena interpolada sin cerrar: falta '}'")
            expresion = texto[indice + 1:cierre].strip()
            if not expresion:
                from exepciones import RuntimeError
                raise RuntimeError("Interpolación vacía dentro de '{}'")
            valor = evaluar_fragmento_func(expresion)
            resultado.append(formatear_texto(valor))
            indice = cierre + 1
        else:
            resultado.append(caracter)
            indice += 1
    return "".join(resultado)

class Evaluador:
    """Encapsula la lógica de evaluación de expresiones"""
    
    def __init__(self, interprete):
        self.interprete = interprete
        # Tabla de despacho: tipo de nodo -> método manejador.
        # Se construye una sola vez para no pagar el costo de recorrer una
        # cadena de if/elif (hasta ~17 comparaciones de string) en CADA
        # nodo evaluado. evaluar() es la función más caliente del intérprete
        # (se llama recursivamente por cada expresión, en cada iteración de
        # cada bucle), así que pasar de O(n) a O(1) por nodo aquí es la
        # optimización de mayor impacto posible.
        self._dispatch = {
            "ENTERO": self._ev_entero,
            "DECIMAL": self._ev_decimal,
            "NINGUNO": self._ev_ninguno,
            "CADENA_TEXTO": self._ev_cadena_texto,
            "CADENA_INTERPOLADA": self._ev_cadena_interpolada,
            "BOOLEANO": self._ev_booleano,
            "LISTA": self._ev_lista,
            "DICCIONARIO": self._ev_diccionario,
            "ACCESO_ATRIBUTO": self._ev_acceso_atributo,
            "LLAMADA": self._ev_llamada,
            "INDEXACION": self._ev_indexacion,
            "LLAMADA_METODO": self._ev_llamada_metodo,
            "IDENTIFICADOR": self._ev_identificador,
            "BINARIA": self._evaluar_binaria,
            "UNARIA": self._ev_unaria,
            "LOGICO": self._evaluar_logica,
            "IN": self._ev_in,
        }
    
    def evaluar_fragmento(self, codigo):
        """Evalúa un fragmento de código (usado para interpolación)"""
        from lexer import lexer
        from parser import Parser
        
        tokens_fragmento = lexer(codigo)
        parser_fragmento = Parser(tokens_fragmento)
        ast_fragmento = parser_fragmento.parse()
        if not ast_fragmento.hijos:
            return ""
        return self.evaluar(ast_fragmento.hijos[0])
    
    def evaluar(self, nodo):
        """Evalúa un nodo del AST y retorna su valor.

        Despacha por diccionario (O(1)) en vez de una cadena de if/elif
        (O(n) en el número de tipos de nodo). Como este método es el más
        invocado de todo el intérprete (una vez por cada subexpresión, en
        cada iteración de cada bucle), este cambio es el que más impacta
        en el rendimiento global."""
        manejador = self._dispatch.get(nodo.tipo)
        if manejador is not None:
            return manejador(nodo)
        return None

    # ---------- Manejadores por tipo de nodo (usados por self._dispatch) ----------

    def _ev_entero(self, nodo):
        return int(nodo.valor)

    def _ev_decimal(self, nodo):
        return float(nodo.valor)

    def _ev_ninguno(self, nodo):
        return None

    def _ev_cadena_texto(self, nodo):
        return self._procesar_escapes(str(nodo.valor))

    def _ev_cadena_interpolada(self, nodo):
        texto_procesado = self._procesar_escapes(nodo.valor)
        return interpolar_cadena(texto_procesado, self.evaluar_fragmento)

    def _ev_booleano(self, nodo):
        return nodo.valor

    def _ev_lista(self, nodo):
        return [self.evaluar(elem) for elem in nodo.hijos]

    def _ev_diccionario(self, nodo):
        resultado = {}
        for par in nodo.hijos:
            clave = self.evaluar(par.hijos[0])
            valor = self.evaluar(par.hijos[1])
            resultado[clave] = valor
        return resultado

    def _ev_acceso_atributo(self, nodo):
        atributo_nombre = nodo.valor
        objeto = self.evaluar(nodo.hijos[0])

        # Si es un módulo
        if isinstance(objeto, dict) and objeto.get("_tipo") == "modulo":
            # Buscar en funciones del módulo
            if atributo_nombre in objeto.get("funciones", {}):
                return objeto["funciones"][atributo_nombre]
            # Buscar en variables del módulo
            if atributo_nombre in objeto.get("variables", {}):
                return objeto["variables"][atributo_nombre]
            raise RuntimeError(f"Módulo no tiene '{atributo_nombre}'", linea=nodo.linea)

        raise RuntimeError(f"El valor de tipo '{type(objeto).__name__}' no tiene atributo '{atributo_nombre}'", linea=nodo.linea)

    def _ev_llamada(self, nodo):
        return self.interprete.ejecutor.ejecutar_funcion(nodo)

    def _ev_indexacion(self, nodo):
        objeto = self.evaluar(nodo.hijos[0])
        indice = self.evaluar(nodo.hijos[1])

        if isinstance(objeto, list):
            if not isinstance(indice, int):
                raise ErrorTipo("Índice de lista debe ser entero", linea=nodo.linea)
            if indice < 0 or indice >= len(objeto):
                raise ErrorIndice(f"Índice {indice} fuera de rango para lista de tamaño {len(objeto)}", linea=nodo.linea)
            return objeto[indice]

        elif isinstance(objeto, dict):
            if indice not in objeto:
                raise ErrorIndice(f"Clave '{indice}' no encontrada en el diccionario", linea=nodo.linea)
            return objeto[indice]

        elif isinstance(objeto, str):
            if not isinstance(indice, int):
                raise ErrorTipo("Índice de cadena debe ser entero", linea=nodo.linea)
            if indice < 0 or indice >= len(objeto):
                raise ErrorIndice(f"Índice {indice} fuera de rango para cadena de tamaño {len(objeto)}", linea=nodo.linea)
            return objeto[indice]

        else:
            raise ErrorTipo(f"No se puede indexar sobre tipo {type(objeto).__name__}", linea=nodo.linea)

    def _ev_llamada_metodo(self, nodo):
        return self.interprete.ejecutor.ejecutar_metodo(nodo)

    def _ev_identificador(self, nodo):
        variables = self.interprete.variables
        if nodo.valor in variables:
            return variables[nodo.valor]
        raise RuntimeError(f"Variable '{nodo.valor}' no definida", linea=nodo.linea)

    def _ev_unaria(self, nodo):
        valor = self.evaluar(nodo.hijos[0])
        try:
            return -valor
        except TypeError:
            raise ErrorTipo(
                f"No se puede aplicar '-' unario sobre tipo {type(valor).__name__}",
                linea=nodo.linea
            )

    def _ev_in(self, nodo):
        izquierda = self.evaluar(nodo.hijos[0])
        derecha = self.evaluar(nodo.hijos[1])
        if isinstance(derecha, list):
            return izquierda in derecha
        elif isinstance(derecha, str):
            return str(izquierda) in derecha
        else:
            raise RuntimeError(f"Operador 'in' no soportado entre {type(izquierda)} y {type(derecha)}", linea=nodo.linea)
    
    def _evaluar_binaria(self, nodo):
        """Evalúa operaciones binarias con manejo de errores"""
        try:
            izq = self.evaluar(nodo.hijos[0])
            der = self.evaluar(nodo.hijos[1])
            op = nodo.valor
        except Exception as e:
            raise RuntimeError(f"Error al evaluar operandos: {e}", linea=nodo.linea)
        
        try:
            if op == "+":
                if isinstance(izq, str) or isinstance(der, str):
                    return str(izq) + str(der)
                return izq + der
                
            elif op == "-":
                return izq - der
            elif op == "*":
                if isinstance(izq, str) and isinstance(der, int):
                    return izq * der
                return izq * der
            elif op == "/":
                if der == 0:
                    raise ErrorMatematico("División por cero", linea=nodo.linea)
                return izq / der
            elif op == "%":
                if der == 0:
                    raise ErrorMatematico("Módulo por cero", linea=nodo.linea)
                return izq % der
            elif op == "==":
                return izq == der
            elif op == "!=":
                return izq != der
            elif op == "<>":
                return izq != der
            elif op == "<":
                return izq < der
            elif op == ">":
                return izq > der
            elif op == "<=":
                return izq <= der
            elif op == ">=":
                return izq >= der
            else:
                raise RuntimeError(f"Operador binario desconocido: {op}", linea=nodo.linea)
        
        except ErrorMatematico:
            raise
        except TypeError as e:
            raise ErrorTipo(f"No se puede aplicar operador '{op}' entre {type(izq).__name__} y {type(der).__name__}", linea=nodo.linea)
        except ZeroDivisionError:
            raise ErrorMatematico("División por cero", linea=nodo.linea)
        except Exception as e:
            raise RuntimeError(f"Error en operación {op}: {e}", linea=nodo.linea)
    
    def _evaluar_logica(self, nodo):
        """Evalúa operaciones lógicas"""
        op = nodo.valor
        if op in ("no",):
            valor = self.evaluar(nodo.hijos[0])
            return not es_verdadero(valor)
        elif op in ("y",):
            izquierda = self.evaluar(nodo.hijos[0])
            if not es_verdadero(izquierda):
                return False
            derecha = self.evaluar(nodo.hijos[1])
            return es_verdadero(derecha)
        elif op in ("o",):
            izquierda = self.evaluar(nodo.hijos[0])
            if es_verdadero(izquierda):
                return True
            derecha = self.evaluar(nodo.hijos[1])
            return es_verdadero(derecha)
        else:
            raise RuntimeError(f"Operador lógico desconocido: {op}", linea=nodo.linea)
    

    def _procesar_escapes(self, texto):
        """Procesa caracteres de escape en cadenas de texto."""
        escapes = {
            '\\n': '\n',
            '\\t': '\t',
            '\\r': '\r',
            '\\\\': '\\',
            '\\"': '"',
            "\\'": "'",
        }
        
        resultado = []
        i = 0
        while i < len(texto):
            if texto[i] == '\\' and i + 1 < len(texto):
                escape = texto[i] + texto[i + 1]
                if escape in escapes:
                    resultado.append(escapes[escape])
                    i += 2
                    continue
            resultado.append(texto[i])
            i += 1
        
        return ''.join(resultado)