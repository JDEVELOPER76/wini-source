from exepciones import *
# parser.py
class Nodo:
    """Representa un nodo en el AST, ahora con línea asociada."""
    def __init__(self, tipo, valor=None, hijos=None, linea=None):
        self.tipo = tipo
        self.valor = valor
        self.hijos = hijos or []
        self.linea = linea   # número de línea (1‑based) donde inicia el constructo

    def __repr__(self):
        return f"Nodo({self.tipo}, {self.valor}, {self.hijos}, line={self.linea})"

    def __slot__(self, key):
        """Permite acceder a los atributos como un diccionario."""
        return getattr(self, key)

class Parser:
    def __init__(self, tokens):
        # tokens ahora son tuplas (tipo, valor, linea, columna)
        self.tokens = tokens
        self.posicion = 0

    def token_actual(self):
        if self.posicion < len(self.tokens):
            return self.tokens[self.posicion]
        return None

    def token_siguiente(self):
        self.posicion += 1

    def token_linea(self):
        """Retorna la línea del token actual (o None si no hay token)."""
        t = self.token_actual()
        return t[2] if t else None

    def saltar_nuevas_lineas(self):
        while self.token_actual() and self.token_actual()[0] == "NUEVA_LINEA":
            self.token_siguiente()

    def esperado(self, tipo):
        """Verifica que el token actual sea del tipo esperado.
        Retorna el valor del token y guarda la línea internamente (se puede consultar con self.token_linea)."""
        token = self.token_actual()
        if token and token[0] == tipo:
            valor = token[1]
            self.token_siguiente()
            return valor
        # Lanzar error de sintaxis con línea si es posible
        linea = token[2] if token else "desconocida"
        col = token[3] if token else ""
        raise SintaxisError(f"Se esperaba {tipo}, pero se encontró {token} (línea {linea}, columna {col})", linea=linea)

    def parsear_argumento(self):
        """Parsea un argumento de una llamada: puede ser posicional (una
        expresión normal) o nombrado, con la forma 'identificador = expresion'
        (p.ej. alguna(genial="si")). Se distingue mirando dos tokens hacia
        adelante para no confundirlo con comparaciones ('==') ni con
        expresiones que solo empiezan con un identificador."""
        token = self.token_actual()
        siguiente = self.tokens[self.posicion + 1] if self.posicion + 1 < len(self.tokens) else None
        if (token and token[0] == "IDENTIFICADOR" and
                siguiente and siguiente[0] == "OPERADOR" and siguiente[1] == "="):
            linea = token[2]
            nombre_arg = self.esperado("IDENTIFICADOR")
            self.esperado("OPERADOR")  # consume '='
            valor = self.parsear_expresion()
            return Nodo("ARG_NOMBRADO", nombre_arg, [valor], linea=linea)
        return self.parsear_expresion()

    def _encontrar_corchete_cierre(self, inicio):
        balance = 0
        for i in range(inicio, len(self.tokens)):
            tipo, valor = self.tokens[i][0], self.tokens[i][1]
            if tipo == "CORCHETE":
                if valor == "[":
                    balance += 1
                elif valor == "]":
                    balance -= 1
                    if balance == 0:
                        return i
        raise SintaxisError("Corchete ']' no encontrado", linea=self.token_linea())

    def parse(self):
        sentencias = []
        while self.token_actual():
            if self.token_actual()[0] == "NUEVA_LINEA":
                self.token_siguiente()
                continue
            sentencias.append(self.parsear_sentencia())
        return Nodo("PROGRAMA", hijos=sentencias)

    # ---------- Sentencias ----------
    def parsear_sentencia(self, palabras_parada=None):
        """Parsea una sentencia, permitiendo palabras de parada para contextos específicos"""
        if palabras_parada is None:
            palabras_parada = set()
        self.saltar_nuevas_lineas()

        # Palabra de parada
        if (self.token_actual() and
            self.token_actual()[0] == "PALABRA_CLAVE" and
            self.token_actual()[1] in palabras_parada):
            return None

        # ===== VERIFICACIÓN DIRECTA POR VALOR (MÁS CONFIABLE) =====
        token_actual = self.token_actual()
        if token_actual and token_actual[0] == "PALABRA_CLAVE":
            valor_token = token_actual[1]
            
            # INTENTAR - Verificar por valor
            if valor_token == "intentar":
                return self.parsear_intentar(palabras_parada)
            
            # LANZAR
            if valor_token == "lanzar":
                return self.parsear_lanzar()
            
            # MIENTRAS
            if valor_token == "mientras":
                return self.parsear_mientras()
            
            # PARA
            if valor_token == "para":
                return self.parsear_para()
            
            # ROMPER
            if valor_token == "romper":
                linea = self.token_linea()
                self.esperado("PALABRA_CLAVE")
                return Nodo("ROMPER", linea=linea)
            
            # CONTINUAR
            if valor_token == "continuar":
                linea = self.token_linea()
                self.esperado("PALABRA_CLAVE")
                return Nodo("CONTINUAR", linea=linea)
            
            # RETORNO
            if valor_token == "retornar":
                linea = self.token_linea()
                self.esperado("PALABRA_CLAVE")
                expr = self.parsear_expresion()
                return Nodo("RETORNO", hijos=[expr], linea=linea)
            
            # IMPORTAR
            if valor_token == "importar":
                return self.parsear_importar()

            # FUNCION
            if valor_token == "funcion":
                return self.parsear_funcion()
            
            # SI
            if valor_token == "si":
                return self.parsear_si(palabras_parada)
            
            # ESCRIBIR
            if valor_token == "escribir":
                linea = self.token_linea()
                nombre = self.esperado("PALABRA_CLAVE")
                self.esperado("PARENTESIS")
                argumentos = []
                if self.token_actual() and not (self.token_actual()[0] == "PARENTESIS" and self.token_actual()[1] == ")"):
                    argumentos.append(self.parsear_argumento())
                    while self.token_actual() and self.token_actual()[0] == "COMA":
                        self.esperado("COMA")
                        argumentos.append(self.parsear_argumento())
                self.esperado("PARENTESIS")
                return Nodo("LLAMADA", nombre, argumentos, linea=linea)
            
            # LEER
            if valor_token == "leer":
                linea = self.token_linea()
                nombre = self.esperado("PALABRA_CLAVE")
                self.esperado("PARENTESIS")
                argumentos = []
                if self.token_actual() and not (self.token_actual()[0] == "PARENTESIS" and self.token_actual()[1] == ")"):
                    argumentos.append(self.parsear_argumento())
                    while self.token_actual() and self.token_actual()[0] == "COMA":
                        self.esperado("COMA")
                        argumentos.append(self.parsear_argumento())
                self.esperado("PARENTESIS")
                return Nodo("LLAMADA", nombre, argumentos, linea=linea)

        # Asignaciones (ID = ... , ID[IDX] = ... , ID.ATTR = ...)
        if (self.token_actual() and self.token_actual()[0] == "IDENTIFICADOR"):
            token_siguiente = None
            if self.posicion + 1 < len(self.tokens):
                token_siguiente = self.tokens[self.posicion + 1]

            if (token_siguiente and token_siguiente[0] == "CORCHETE" and token_siguiente[1] == "["):
                idx_cierre = self._encontrar_corchete_cierre(self.posicion + 1)
                if idx_cierre + 1 < len(self.tokens) and self.tokens[idx_cierre + 1][1] == "=":
                    return self.parsear_asignacion()

            if token_siguiente and token_siguiente[1] == "=":
                return self.parsear_asignacion()

        # Si no es asignación, es una expresión suelta
        return self.parsear_expresion()

    def parsear_asignacion(self):
        """Parsea: ID = EXPR | ID[IDX] = EXPR | ID.ATTR = EXPR"""
        linea_id = self.token_linea()
        id_nombre = self.esperado("IDENTIFICADOR")

        # Asignación con índice
        if self.token_actual() and self.token_actual()[0] == "CORCHETE" and self.token_actual()[1] == "[":
            self.esperado("CORCHETE")
            indice = self.parsear_expresion()
            self.esperado("CORCHETE")
            token = self.token_actual()
            if not token or token[1] != "=":
                raise SintaxisError(f"Se esperaba '=' pero se encontró {token}",linea=linea_id)
            self.token_siguiente()
            expr = self.parsear_expresion()
            return Nodo("ASIGNACION_INDEX", id_nombre, [indice, expr], linea=linea_id)

        # Asignación simple
        token = self.token_actual()
        if not token or token[1] != "=":
            raise SintaxisError(f"Se esperaba '=' pero se encontró {token}",linea=linea_id)
        self.token_siguiente()
        expr = self.parsear_expresion()
        return Nodo("ASIGNACION", id_nombre, [expr], linea=linea_id)

    def parsear_funcion(self):
        linea = self.token_linea()
        self.esperado("PALABRA_CLAVE")  # funcion
        nombre_funcion = self.esperado("IDENTIFICADOR")
        self.esperado("PARENTESIS")
        parametros = []
        if self.token_actual() and not (self.token_actual()[0] == "PARENTESIS" and self.token_actual()[1] == ")"):
            parametros.append(self.esperado("IDENTIFICADOR"))
            while self.token_actual() and self.token_actual()[0] == "COMA":
                self.esperado("COMA")
                parametros.append(self.esperado("IDENTIFICADOR"))
        self.esperado("PARENTESIS")
        self.esperado("PUNTOS")
        if not self.token_actual() or self.token_actual()[0] != "NUEVA_LINEA":
            raise SintaxisError("Se esperaba un salto de línea después de ':' en la función",linea=linea)
        
        # Leer indentación del bloque
        indentacion_bloque = self.esperado("NUEVA_LINEA")
        
        # --- Extraer docstring opcional ---
        docstring = None
        # Saltar posibles NUEVA_LINEA adicionales? No, ya consumimos la primera
        # Pero puede haber más espacios? Mejor saltar nuevas líneas al inicio del bloque
        self.saltar_nuevas_lineas()
        token = self.token_actual()
        if token and token[0] == "CADENA_TEXTO":
            # Docstring con cadena literal
            docstring = token[1][1:-1]  # quitar comillas
            self.token_siguiente()
            # Consumir la nueva línea que sigue a la cadena (si existe)
            if self.token_actual() and self.token_actual()[0] == "NUEVA_LINEA":
                self.token_siguiente()
        elif token and token[0] == "COMENTARIO" and token[1].startswith("#@"):
            # Docstring con comentario especial
            docstring = token[1][2:].strip()
            self.token_siguiente()
            # Consumir nueva línea posterior
            if self.token_actual() and self.token_actual()[0] == "NUEVA_LINEA":
                self.token_siguiente()
        
        # Restaurar el estado para leer el cuerpo: ahora el siguiente token debe ser parte del cuerpo
        # El docstring ya fue consumido. Continuar leyendo sentencias hasta que la indentación baje.
        cuerpo = []
        while self.token_actual():
            if self.token_actual()[0] == "NUEVA_LINEA":
                if self.token_actual()[1] < indentacion_bloque:
                    break
                self.token_siguiente()
                continue
            if self.token_actual()[0] == "PALABRA_CLAVE" and self.token_actual()[1] == "fin":
                break
            cuerpo.append(self.parsear_sentencia())
        self.saltar_nuevas_lineas()
        if self.token_actual() and self.token_actual()[0] == "PALABRA_CLAVE" and self.token_actual()[1] == "fin":
            self.esperado("PALABRA_CLAVE")
        
        nodo = Nodo("FUNCION", nombre_funcion, [
            Nodo("PARAMETROS", hijos=[Nodo("PARAM", p, linea=linea) for p in parametros]),
            Nodo("CUERPO", hijos=cuerpo)
        ], linea=linea)
        nodo.docstring = docstring  # adjuntar docstring al nodo
        return nodo

    def parsear_si(self, palabras_parada=None):
        """Parsea un condicional si con sintaxis: si condicion entonces: ... sino: ... fin"""
        if palabras_parada is None:
            palabras_parada = set()
        linea = self.token_linea()
        self.esperado("PALABRA_CLAVE")  # si
        condicion = self.parsear_expresion()
        
        # Verificar que sigue 'entonces'
        if (self.token_actual() and 
            self.token_actual()[0] == "PALABRA_CLAVE" and 
            self.token_actual()[1] == "entonces"):
            self.esperado("PALABRA_CLAVE")  # entonces
        else:
            raise SintaxisError("Se esperaba 'entonces' después de la condición", linea=linea)
        
        self.esperado("PUNTOS")  # :
        
        # Leer indentación
        if not self.token_actual() or self.token_actual()[0] != "NUEVA_LINEA":
            raise SintaxisError("Se esperaba un salto de línea después de ':'", linea=linea)
        
        indentacion_bloque = self.esperado("NUEVA_LINEA")
        
        # Leer bloque SI
        bloque_si = []
        while self.token_actual():
            if self.token_actual()[0] == "NUEVA_LINEA":
                if self.token_actual()[1] < indentacion_bloque:
                    break
                self.token_siguiente()
                continue
            
            if (self.token_actual() and self.token_actual()[0] == "PALABRA_CLAVE" and
                self.token_actual()[1] in ("sino", "fin")):
                break
            
            bloque_si.append(self.parsear_sentencia())
        
        # Leer bloque SINO (opcional)
        bloque_sino = []
        self.saltar_nuevas_lineas()
        if (self.token_actual() and
            self.token_actual()[0] == "PALABRA_CLAVE" and
            self.token_actual()[1] == "sino"):
            self.esperado("PALABRA_CLAVE")  # sino
            self.esperado("PUNTOS")  # :
            
            if not self.token_actual() or self.token_actual()[0] != "NUEVA_LINEA":
                raise SintaxisError("Se esperaba un salto de línea después de ':'", linea=linea)
            
            indentacion_sino = self.esperado("NUEVA_LINEA")
            
            while self.token_actual():
                if self.token_actual()[0] == "NUEVA_LINEA":
                    if self.token_actual()[1] < indentacion_sino:
                        break
                    self.token_siguiente()
                    continue
                
                if (self.token_actual() and self.token_actual()[0] == "PALABRA_CLAVE" and
                    self.token_actual()[1] == "fin"):
                    break
                
                bloque_sino.append(self.parsear_sentencia())
        
        # Consumir 'fin'
        self.saltar_nuevas_lineas()
        if self.token_actual() and self.token_actual()[0] == "PALABRA_CLAVE" and self.token_actual()[1] == "fin":
            self.esperado("PALABRA_CLAVE")
        
        return Nodo("SI", hijos=[
            condicion,
            Nodo("BLOQUE_SI", hijos=bloque_si),
            Nodo("BLOQUE_SINO", hijos=bloque_sino)
        ], linea=linea)

    def parsear_intentar(self, palabras_parada=None):
        """Parsea una estructura intentar-capturar-finalmente"""
        if palabras_parada is None:
            palabras_parada = set()
        
        linea = self.token_linea()
        self.esperado("PALABRA_CLAVE")  # intentar
        self.esperado("PUNTOS")  # :
        
        if not self.token_actual() or self.token_actual()[0] != "NUEVA_LINEA":
            raise SintaxisError("Se esperaba un salto de línea después de ':' en intentar", linea=self.token_linea())
        
        indentacion_bloque = self.esperado("NUEVA_LINEA")
        
        # Palabras que terminan el bloque try
        parada_try = palabras_parada | {"capturar", "finalmente", "fin"}

        # parsear_sentencia llama saltar_nuevas_lineas() y retorna None si el
        # siguiente token no-NL está en parada_try — eso es lo que queremos.
        bloque_try = []
        while self.token_actual():
            token = self.token_actual()

            if token[0] == "NUEVA_LINEA":
                if token[1] < indentacion_bloque:
                    break  # indentación bajó → fin del bloque
                self.token_siguiente()
                continue

            # Verificación directa (por si saltar_nuevas_lineas ya avanzó el cursor)
            if (token[0] == "PALABRA_CLAVE" and
                    token[1] in ("capturar", "finalmente", "fin")):
                break

            sent = self.parsear_sentencia(parada_try)
            if sent is None:
                break
            bloque_try.append(sent)
        
        # Parsear bloques capturar y finally
        bloques_capturar = []
        bloque_finally = None
        
        # IMPORTANTE: Saltar líneas vacías antes de procesar capturar/finally
        self.saltar_nuevas_lineas()
        
        while self.token_actual():
            token = self.token_actual()
            
            if token[0] != "PALABRA_CLAVE":
                break
            
            palabra = token[1]
            
            if palabra == "capturar":
                # Saltar nueva línea antes de capturar si existe
                self.saltar_nuevas_lineas()
                
                linea_capturar = self.token_linea()
                self.esperado("PALABRA_CLAVE")  # capturar
                
                tipo_error = None
                variable_error = None
                
                # Forma con paréntesis: capturar(Tipo) como var:
                if (self.token_actual() and 
                    self.token_actual()[0] == "PARENTESIS" and 
                    self.token_actual()[1] == "("):
                    self.esperado("PARENTESIS")
                    token_tipo = self.token_actual()
                    if token_tipo and token_tipo[0] == "IDENTIFICADOR":
                        tipo_error = self.esperado("IDENTIFICADOR")
                    elif token_tipo and token_tipo[0] == "PALABRA_CLAVE":
                        tipo_error = self.esperado("PALABRA_CLAVE")
                    self.esperado("PARENTESIS")
                
                # Forma sin paréntesis: capturar Tipo como var:
                # También soporta notación con punto: capturar modulo.NombreError como var:
                elif (self.token_actual() and
                      self.token_actual()[0] == "IDENTIFICADOR"):
                    tipo_error = self.esperado("IDENTIFICADOR")
                    if (self.token_actual() and
                            self.token_actual()[0] == "PUNTO"):
                        self.esperado("PUNTO")
                        tipo_error = tipo_error + "." + self.esperado("IDENTIFICADOR")
                
                # Verificar 'como' para variable
                if (self.token_actual() and 
                    self.token_actual()[0] == "PALABRA_CLAVE" and 
                    self.token_actual()[1] == "como"):
                    self.esperado("PALABRA_CLAVE")  # como
                    variable_error = self.esperado("IDENTIFICADOR")
                
                self.esperado("PUNTOS")  # :
                
                if not self.token_actual() or self.token_actual()[0] != "NUEVA_LINEA":
                    raise SintaxisError("Se esperaba un salto de línea después de ':' en capturar", linea=self.token_linea())
                
                indent_capturar = self.esperado("NUEVA_LINEA")
                
                parada_capturar = palabras_parada | {"capturar", "finalmente", "fin"}
                bloque_capturar = []
                while self.token_actual():
                    if self.token_actual()[0] == "NUEVA_LINEA":
                        if self.token_actual()[1] < indent_capturar:
                            break
                        self.token_siguiente()
                        continue
                    if (self.token_actual()[0] == "PALABRA_CLAVE" and
                            self.token_actual()[1] in ("capturar", "finalmente", "fin")):
                        break
                    sent = self.parsear_sentencia(parada_capturar)
                    if sent is None:
                        break
                    bloque_capturar.append(sent)
                
                bloques_capturar.append({
                    "tipo": tipo_error,
                    "variable": variable_error,
                    "bloque": bloque_capturar,
                    "linea": linea_capturar
                })
                
                # Saltar líneas vacías después de capturar
                self.saltar_nuevas_lineas()
            
            elif palabra == "finalmente":
                linea_finally = self.token_linea()
                self.esperado("PALABRA_CLAVE")  # finalmente
                self.esperado("PUNTOS")  # :
                
                if not self.token_actual() or self.token_actual()[0] != "NUEVA_LINEA":
                    raise SintaxisError("Se esperaba un salto de línea después de ':' en finalmente", linea=self.token_linea())
                
                indent_finally = self.esperado("NUEVA_LINEA")
                
                parada_finally = palabras_parada | {"fin"}
                bloque_finally = []
                while self.token_actual():
                    if self.token_actual()[0] == "NUEVA_LINEA":
                        if self.token_actual()[1] < indent_finally:
                            break
                        self.token_siguiente()
                        continue
                    if (self.token_actual()[0] == "PALABRA_CLAVE" and
                            self.token_actual()[1] == "fin"):
                        break
                    sent = self.parsear_sentencia(parada_finally)
                    if sent is None:
                        break
                    bloque_finally.append(sent)
                
                # Saltar líneas vacías después de finally
                self.saltar_nuevas_lineas()
                break  # finally debe ser el último
            
            elif palabra == "fin":
                break
            
            else:
                break
        
        # Consumir el 'fin'
        self.saltar_nuevas_lineas()
        if self.token_actual() and self.token_actual()[0] == "PALABRA_CLAVE" and self.token_actual()[1] == "fin":
            self.esperado("PALABRA_CLAVE")
        
        # Crear nodo CAPTURAR para cada bloque
        nodos_capturar = []
        for capturar_info in bloques_capturar:
            nodo_variable = Nodo("VARIABLE_ERROR", capturar_info["variable"]) if capturar_info["variable"] else Nodo("VARIABLE_ERROR", None)
            nodo_capturar = Nodo("CAPTURAR", 
                                valor=capturar_info["tipo"],
                                hijos=[nodo_variable, Nodo("BLOQUE", hijos=capturar_info["bloque"])],
                                linea=capturar_info["linea"])
            nodos_capturar.append(nodo_capturar)
        
        nodo_finally = Nodo("BLOQUE_FINALLY", hijos=bloque_finally) if bloque_finally else Nodo("BLOQUE_FINALLY", hijos=[])
        
        return Nodo("INTENTAR", 
                    hijos=[
                        Nodo("BLOQUE_TRY", hijos=bloque_try),
                        Nodo("BLOQUES_CAPTURAR", hijos=nodos_capturar),
                        nodo_finally
                    ], 
                    linea=linea)

    def _crear_nodo_capturar(self, capturar_info):
        """Crea un nodo para un bloque capturar"""
        return Nodo("CAPTURAR", 
                    valor=capturar_info["tipo"],
                    hijos=[
                        Nodo("VARIABLE_ERROR", capturar_info["variable"]) if capturar_info["variable"] else Nodo("VARIABLE_ERROR", None),
                        Nodo("BLOQUE", hijos=capturar_info["bloque"])
                    ],
                    linea=capturar_info["linea"])

    def parsear_importar(self):
        """Parsea la instrucción 'importar'

        Sintaxis soportada:
            importar modulo
            importar modulo como alias
            importar carpeta.modulo como alias   # subcarpetas con notación de punto
        """
        linea = self.token_linea()
        self.esperado("PALABRA_CLAVE")  # importar

        nombre_modulo = self.esperado("IDENTIFICADOR")
        while self.token_actual() and self.token_actual()[0] == "PUNTO":
            self.esperado("PUNTO")
            nombre_modulo += "." + self.esperado("IDENTIFICADOR")

        alias = None
        if (self.token_actual() and
                self.token_actual()[0] == "PALABRA_CLAVE" and
                self.token_actual()[1] == "como"):
            self.esperado("PALABRA_CLAVE")  # como
            alias = self.esperado("IDENTIFICADOR")

        nodo_alias = Nodo("ALIAS", alias, linea=linea)
        return Nodo("IMPORTAR", nombre_modulo, hijos=[nodo_alias], linea=linea)

    def parsear_lanzar(self):
        """Parsea la instrucción 'lanzar'

        Sintaxis soportada:
            lanzar(ErrorTipo, "mensaje")          # forma antigua con paréntesis
            lanzar(modulo.NombreError, "mensaje") # forma antigua con módulo
            lanzar ErrorTipo("mensaje")           # forma nueva sin paréntesis externos
            lanzar modulo.NombreError("mensaje")  # forma nueva con módulo
        """
        linea = self.token_linea()
        self.esperado("PALABRA_CLAVE")  # lanzar

        tipo_error = None
        mensaje_expr = None

        token = self.token_actual()

        # ── Forma nueva: lanzar Tipo(...)  o  lanzar modulo.Tipo(...) ──────────
        if token and token[0] == "IDENTIFICADOR":
            tipo_error = self.esperado("IDENTIFICADOR")

            # ¿notación de módulo?  lanzar modulo.NombreError(...)
            if self.token_actual() and self.token_actual()[0] == "PUNTO":
                self.esperado("PUNTO")
                tipo_error = tipo_error + "." + self.esperado("IDENTIFICADOR")

            # Ahora debe venir  (argumento)
            if self.token_actual() and self.token_actual()[0] == "PARENTESIS" and self.token_actual()[1] == "(":
                self.esperado("PARENTESIS")
                if self.token_actual() and not (self.token_actual()[0] == "PARENTESIS" and self.token_actual()[1] == ")"):
                    mensaje_expr = self.parsear_expresion()
                self.esperado("PARENTESIS")

            nodo_tipo = Nodo("TIPO_ERROR", tipo_error)
            nodo_mensaje = Nodo("MENSAJE", hijos=[mensaje_expr] if mensaje_expr else [])
            return Nodo("LANZAR", hijos=[nodo_tipo, nodo_mensaje], linea=linea)

        # ── Forma antigua: lanzar("msg")  o  lanzar(Tipo, "msg") ────────────
        if token and token[0] == "PARENTESIS" and token[1] == "(":
            self.esperado("PARENTESIS")

            token2 = self.token_actual()
            if token2 and token2[0] == "IDENTIFICADOR":
                # peek: si después del identificador hay coma → es (Tipo, msg)
                pos_next = self.posicion + 1
                next_tok = self.tokens[pos_next] if pos_next < len(self.tokens) else None
                if next_tok and next_tok[0] == "COMA":
                    tipo_error = self.esperado("IDENTIFICADOR")
                    self.esperado("COMA")
                    mensaje_expr = self.parsear_expresion()
                else:
                    mensaje_expr = self.parsear_expresion()
            else:
                mensaje_expr = self.parsear_expresion()

            self.esperado("PARENTESIS")

            nodo_tipo = Nodo("TIPO_ERROR", tipo_error)
            nodo_mensaje = Nodo("MENSAJE", hijos=[mensaje_expr] if mensaje_expr else [])
            return Nodo("LANZAR", hijos=[nodo_tipo, nodo_mensaje], linea=linea)

        raise SintaxisError(f"Sintaxis inválida para 'lanzar'", linea=linea)

    def parsear_mientras(self):
        """Parsea un bucle mientras con sintaxis: mientras condicion entonces: ... fin"""
        linea = self.token_linea()
        self.esperado("PALABRA_CLAVE")  # mientras
        
        # ✅ Ya no esperamos PARENTESIS
        condicion = self.parsear_expresion()
        
        # Verificar 'entonces'
        if (self.token_actual() and 
            self.token_actual()[0] == "PALABRA_CLAVE" and 
            self.token_actual()[1] == "entonces"):
            self.esperado("PALABRA_CLAVE")  # entonces
        else:
            raise SintaxisError("Se esperaba 'entonces' después de la condición", linea=linea)
        
        self.esperado("PUNTOS")  # :
        
        if not self.token_actual() or self.token_actual()[0] != "NUEVA_LINEA":
            raise SintaxisError("Se esperaba un salto de línea después de ':'", linea=linea)
        
        indentacion_bloque = self.esperado("NUEVA_LINEA")
        
        bloque = []
        while self.token_actual():
            if self.token_actual()[0] == "NUEVA_LINEA":
                if self.token_actual()[1] < indentacion_bloque:
                    break
                self.token_siguiente()
                continue
            
            if (self.token_actual() and self.token_actual()[0] == "PALABRA_CLAVE" and
                self.token_actual()[1] == "fin"):
                break
            
            bloque.append(self.parsear_sentencia())
        
        self.saltar_nuevas_lineas()
        if self.token_actual() and self.token_actual()[0] == "PALABRA_CLAVE" and self.token_actual()[1] == "fin":
            self.esperado("PALABRA_CLAVE")
        
        return Nodo("MIENTRAS", hijos=[condicion, Nodo("BLOQUE", hijos=bloque)], linea=linea)

# En parser.py, reemplaza el método parsear_para() por este:

    def parsear_para(self):
        """Parsea un bucle para con sintaxis mejorada:
        para variable en expresion:
            # cuerpo
        fin
        """
        linea = self.token_linea()
        
        # 1. Consumir 'para'
        self.esperado("PALABRA_CLAVE")  # para
        
        # 2. Variable
        variable_str = self.esperado("IDENTIFICADOR")
        variable_nodo = Nodo("IDENTIFICADOR", valor=variable_str, linea=linea)
        
        # 3. Consumir 'en'
        token_en = self.token_actual()
        if token_en and token_en[0] == "OPERADOR_LOGICO" and token_en[1] == "en":
            self.token_siguiente()
        else:
            raise SintaxisError(f"Se esperaba 'en', pero se encontró {token_en}", linea=linea)
        
        # 4. Expresión iterable
        expresion_iterable = self.parsear_expresion()
        
        # 5. Consumir ':'
        self.esperado("PUNTOS")
        
        # 6. Verificar nueva línea
        if not self.token_actual() or self.token_actual()[0] != "NUEVA_LINEA":
            raise SintaxisError("Se esperaba un salto de línea después de ':'", linea=linea)
        
        indentacion_bloque = self.esperado("NUEVA_LINEA")
        
        # 7. Recolectar el cuerpo
        sentencias_bloque = []
        while self.token_actual():
            if self.token_actual()[0] == "NUEVA_LINEA":
                if self.token_actual()[1] < indentacion_bloque:
                    break
                self.token_siguiente()
                continue
            
            if (self.token_actual()[0] == "PALABRA_CLAVE" and 
                self.token_actual()[1] == "fin"):
                break
            
            sentencia = self.parsear_sentencia()
            if sentencia:
                sentencias_bloque.append(sentencia)
        
        # 8. Consumir 'fin'
        self.saltar_nuevas_lineas()
        if self.token_actual() and self.token_actual()[0] == "PALABRA_CLAVE" and self.token_actual()[1] == "fin":
            self.token_siguiente()
        else:
            raise SintaxisError("Se esperaba 'fin' para cerrar el bucle para", linea=linea)
        
        bloque_nodo = Nodo("BLOQUE", hijos=sentencias_bloque, linea=linea)
        return Nodo("PARA", hijos=[variable_nodo, expresion_iterable, bloque_nodo], linea=linea)
    # ---------- Expresiones ----------
    def parsear_expresion(self):
        return self.parsear_logico_or()

    def parsear_logico_or(self):
        left = self.parsear_logico_and()
        while (self.token_actual() and self.token_actual()[0] == "OPERADOR_LOGICO" and
               self.token_actual()[1] in ("o", "or")):
            op_linea = self.token_linea()
            op = self.esperado("OPERADOR_LOGICO")
            right = self.parsear_logico_and()
            left = Nodo("LOGICO", op, [left, right], linea=op_linea)
        return left

    def parsear_logico_and(self):
        left = self.parsear_not()
        while (self.token_actual() and self.token_actual()[0] == "OPERADOR_LOGICO" and
               self.token_actual()[1] in ("y", "and")):
            op_linea = self.token_linea()
            op = self.esperado("OPERADOR_LOGICO")
            right = self.parsear_not()
            left = Nodo("LOGICO", op, [left, right], linea=op_linea)
        return left

    def parsear_not(self):
        if (self.token_actual() and self.token_actual()[0] == "OPERADOR_LOGICO" and
            self.token_actual()[1] in ("no", "not")):
            op_linea = self.token_linea()
            op = self.esperado("OPERADOR_LOGICO")
            expr = self.parsear_not()
            return Nodo("LOGICO", op, [expr], linea=op_linea)
        return self.parsear_in()

    def parsear_in(self):
        left = self._parsear_comparacion()
        if (self.token_actual() and self.token_actual()[0] == "OPERADOR_LOGICO" and
            self.token_actual()[1] in ("en", "in")):
            op_linea = self.token_linea()
            op = self.esperado("OPERADOR_LOGICO")
            right = self._parsear_comparacion()
            return Nodo("IN", op, [left, right], linea=op_linea)
        return left

    def _parsear_comparacion(self):
        izq = self.parsear_suma()
        while (self.token_actual() and self.token_actual()[0] == "COMPARADOR"):
            op_linea = self.token_linea()
            op = self.esperado("COMPARADOR")
            der = self.parsear_suma()
            izq = Nodo("BINARIA", op, [izq, der], linea=op_linea)
        return izq

    def parsear_suma(self):
        izq = self.parsear_termino()
        while (self.token_actual() and
               self.token_actual()[0] == "OPERADOR" and
               self.token_actual()[1] in ("+", "-")):
            op_linea = self.token_linea()
            op = self.esperado("OPERADOR")
            der = self.parsear_termino()
            izq = Nodo("BINARIA", op, [izq, der], linea=op_linea)
        return izq

    def parsear_termino(self):
        izq = self.parsear_factor()
        while (self.token_actual() and
               self.token_actual()[0] == "OPERADOR" and
               self.token_actual()[1] in ("*", "/","%")):
            op_linea = self.token_linea()
            op = self.esperado("OPERADOR")
            der = self.parsear_factor()
            izq = Nodo("BINARIA", op, [izq, der], linea=op_linea)
        return izq

    def parsear_factor(self):
        token = self.token_actual()
        if token and token[0] == "OPERADOR" and token[1] in ("-", "+"):
            linea = self.token_linea()
            op = self.esperado("OPERADOR")
            operando = self.parsear_factor()
            if op == "+":
                # El '+' unario no hace nada, se descarta.
                return operando
            return Nodo("UNARIA", op, [operando], linea=linea)

        nodo = self._parsear_atomo()
        return self._parsear_postfijos(nodo)

    def _parsear_postfijos(self, nodo):
        """Encadena .atributo, .metodo(args) y [indice] sobre CUALQUIER expresión
        (variables, llamadas a función, literales, otros encadenamientos, etc.),
        para permitir cosas como leer("...").a_entero() o a.dividir(",").primero()."""
        while True:
            token = self.token_actual()
            if not token:
                break

            if token[0] == "PUNTO":
                linea = nodo.linea
                self.esperado("PUNTO")
                token_atributo = self.token_actual()
                if token_atributo and token_atributo[0] == "IDENTIFICADOR":
                    atributo = self.esperado("IDENTIFICADOR")
                elif token_atributo and token_atributo[0] == "PALABRA_CLAVE":
                    atributo = self.esperado("PALABRA_CLAVE")
                else:
                    raise SintaxisError(f"Se esperaba identificador después de '.', pero encontró {token_atributo}", linea=linea)

                if self.token_actual() and self.token_actual()[0] == "PARENTESIS" and self.token_actual()[1] == "(":
                    self.esperado("PARENTESIS")
                    argumentos = []
                    if self.token_actual() and not (self.token_actual()[0] == "PARENTESIS" and self.token_actual()[1] == ")"):
                        argumentos.append(self.parsear_argumento())
                        while self.token_actual() and self.token_actual()[0] == "COMA":
                            self.esperado("COMA")
                            argumentos.append(self.parsear_argumento())
                    self.esperado("PARENTESIS")
                    nodo = Nodo("LLAMADA_METODO", atributo, [nodo] + argumentos, linea=linea)
                else:
                    nodo = Nodo("ACCESO_ATRIBUTO", atributo, [nodo], linea=linea)

            elif token[0] == "CORCHETE" and token[1] == "[":
                linea = nodo.linea
                self.esperado("CORCHETE")
                indice = self.parsear_expresion()
                self.esperado("CORCHETE")
                nodo = Nodo("INDEXACION", None, [nodo, indice], linea=linea)

            else:
                break

        return nodo

    def _parsear_atomo(self):
        token = self.token_actual()
        linea = token[2] if token else None

        if token[0] == "ENTERO":
            valor = self.esperado("ENTERO")
            return Nodo("ENTERO", valor, linea=linea)
        elif token[0] == "DECIMAL":
            valor = self.esperado("DECIMAL")
            return Nodo("DECIMAL", valor, linea=linea)
        elif token[0] == "CADENA_INTERPOLADA":
            valor = self.esperado("CADENA_INTERPOLADA")
            return Nodo("CADENA_INTERPOLADA", valor[2:-1], linea=linea)
        elif token[0] == "CADENA_TEXTO":
            valor = self.esperado("CADENA_TEXTO")
            return Nodo("CADENA_TEXTO", valor[1:-1], linea=linea)
        elif token[0] == "NINGUNO":
            self.esperado("NINGUNO")
            return Nodo("NINGUNO", None, linea=linea)
        elif token[0] == "BOOLEANO":
            valor = self.esperado("BOOLEANO")
            bool_val = True if valor in ("true", "verdadero") else False
            return Nodo("BOOLEANO", bool_val, linea=linea)
        elif token[0] == "PALABRA_CLAVE" and token[1] == "escribir":
            # Llamada a escribir como expresión (aunque normalmente es sentencia)
            nombre = self.esperado("PALABRA_CLAVE")
            self.esperado("PARENTESIS")
            argumentos = []
            if self.token_actual() and not (self.token_actual()[0] == "PARENTESIS" and self.token_actual()[1] == ")"):
                argumentos.append(self.parsear_argumento())
                while self.token_actual() and self.token_actual()[0] == "COMA":
                    self.esperado("COMA")
                    argumentos.append(self.parsear_argumento())
            self.esperado("PARENTESIS")
            return Nodo("LLAMADA", nombre, argumentos, linea=linea)
        elif token[0] == "PALABRA_CLAVE" and token[1] == "leer":
            nombre = self.esperado("PALABRA_CLAVE")
            self.esperado("PARENTESIS")
            argumentos = []
            if self.token_actual() and not (self.token_actual()[0] == "PARENTESIS" and self.token_actual()[1] == ")"):
                argumentos.append(self.parsear_argumento())
                while self.token_actual() and self.token_actual()[0] == "COMA":
                    self.esperado("COMA")
                    argumentos.append(self.parsear_argumento())
            self.esperado("PARENTESIS")
            return Nodo("LLAMADA", nombre, argumentos, linea=linea)
        elif token[0] == "PALABRA_CLAVE" and token[1] == "tipo":
            nombre = self.esperado("PALABRA_CLAVE")
            self.esperado("PARENTESIS")
            argumentos = []
            if self.token_actual() and not (self.token_actual()[0] == "PARENTESIS" and self.token_actual()[1] == ")"):
                argumentos.append(self.parsear_argumento())
                while self.token_actual() and self.token_actual()[0] == "COMA":
                    self.esperado("COMA")
                    argumentos.append(self.parsear_argumento())
            self.esperado("PARENTESIS")
            return Nodo("LLAMADA", nombre, argumentos, linea=linea)
        elif token[0] == "IDENTIFICADOR":
            valor = self.esperado("IDENTIFICADOR")
            # Llamada a función
            if self.token_actual() and self.token_actual()[0] == "PARENTESIS" and self.token_actual()[1] == "(":
                self.esperado("PARENTESIS")
                argumentos = []
                if self.token_actual() and not (self.token_actual()[0] == "PARENTESIS" and self.token_actual()[1] == ")"):
                    argumentos.append(self.parsear_argumento())
                    while self.token_actual() and self.token_actual()[0] == "COMA":
                        self.esperado("COMA")
                        argumentos.append(self.parsear_argumento())
                self.esperado("PARENTESIS")
                return Nodo("LLAMADA", valor, argumentos, linea=linea)
            else:
                return Nodo("IDENTIFICADOR", valor, linea=linea)
        elif token[0] == "CORCHETE" and token[1] == "[":
            self.esperado("CORCHETE")
            elementos = []
            if self.token_actual() and not (self.token_actual()[0] == "CORCHETE" and self.token_actual()[1] == "]"):
                elementos.append(self.parsear_expresion())
                while self.token_actual() and self.token_actual()[0] == "COMA":
                    self.esperado("COMA")
                    elementos.append(self.parsear_expresion())
            self.esperado("CORCHETE")
            return Nodo("LISTA", hijos=elementos, linea=linea)
        elif token[0] == "LLAVE" and token[1] == "{":
            self.esperado("LLAVE")
            pares = []
            if self.token_actual() and not (self.token_actual()[0] == "LLAVE" and self.token_actual()[1] == "}"):
                clave = self.parsear_expresion()
                self.esperado("PUNTOS")
                valor = self.parsear_expresion()
                pares.append((clave, valor))
                while self.token_actual() and self.token_actual()[0] == "COMA":
                    self.esperado("COMA")
                    clave = self.parsear_expresion()
                    self.esperado("PUNTOS")
                    valor = self.parsear_expresion()
                    pares.append((clave, valor))
            self.esperado("LLAVE")
            hijos = [Nodo("PAR", hijos=[k, v], linea=linea) for k, v in pares]
            return Nodo("DICCIONARIO", hijos=hijos, linea=linea)
        elif token[0] == "PARENTESIS" and token[1] == "(":
            self.esperado("PARENTESIS")
            expr = self.parsear_expresion()
            self.esperado("PARENTESIS")
            return expr
        raise SintaxisError(f"Factor inesperado: {token} (línea {linea})",linea=linea)