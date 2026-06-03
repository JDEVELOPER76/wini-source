# interprete.py
"""Intérprete principal para el lenguaje wini"""

import os 
import sys
from lexer import lexer
from parser import Parser
from clases import Clase, Instancia
from exepciones import *
from evaluador import Evaluador
from ejecutor import Ejecutor
from importador import Importador


class Interprete:
    """Intérprete principal del lenguaje wini"""

    def __init__(self, archivo):
        self.archivo = os.path.abspath(archivo)
        self.directorio = os.path.dirname(self.archivo)
        self.variables = {}
        
        # 🔥 REGISTRAR AQUÍ: Agregamos la función nativa al diccionario de funciones
        self.funciones = {
            "rango": self._rango_nativo
        }
        
        self.clases = {}
        self.paquetes = {}
        self.default_paquete = None
        self.yo = None
        
        # Crear evaluador, ejecutor e importador
        self.evaluador = Evaluador(self)
        self.ejecutor = Ejecutor(self)
        self.importador = Importador(self)  # ← Ahora Importador maneja todo
    
    
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

    def interpretar(self, nodo):
        """Interpreta un nodo del AST"""
        
        if nodo.tipo == "PROGRAMA":
            for hijo in nodo.hijos:
                self.interpretar(hijo)
        
        elif nodo.tipo == "MIENTRAS":
            self._ejecutar_mientras(nodo)
        
        elif nodo.tipo == "PARA":
            self._ejecutar_para(nodo)
        
        elif nodo.tipo == "ROMPER":
            raise RomperException()
        
        elif nodo.tipo == "CONTINUAR":
            raise ContinuarException()
        
        elif nodo.tipo == "ASIGNACION":
            valor = self.evaluador.evaluar(nodo.hijos[0])
            self.variables[nodo.valor] = valor
        
        elif nodo.tipo == "ASIGNACION_ATRIBUTO":
            self._ejecutar_asignacion_atributo(nodo)
        
        elif nodo.tipo == "ASIGNACION_INDEX":
            self._ejecutar_asignacion_index(nodo)
        
        elif nodo.tipo == "LLAMADA":
            return self.ejecutor.ejecutar_funcion(nodo)
        
        elif nodo.tipo == "LLAMADA_METODO":
            return self.ejecutor.ejecutar_metodo(nodo)
        
        elif nodo.tipo == "RETORNO":
            valor = self.evaluador.evaluar(nodo.hijos[0])
            raise RetornoException(valor)
        elif nodo.tipo == "INTENTAR":
            self._ejecutar_intentar(nodo)
        
        elif nodo.tipo == "LANZAR":
            self._ejecutar_lanzar(nodo)

        elif nodo.tipo == "IMPORTAR":
            nombre_modulo = self.evaluador.evaluar(nodo.hijos[0])
            self.importador.importar_modulo(nombre_modulo)
            
        elif nodo.tipo == "PAQUETE":
            self._registrar_paquete(nodo)
        
        elif nodo.tipo == "CLASE":
            self._definir_clase(nodo)
        
        elif nodo.tipo == "FUNCION":
            self._definir_funcion(nodo)
        
        elif nodo.tipo == "SI":
            self._ejecutar_si(nodo)
    
    # ------------------- Métodos auxiliares para interpretación -------------------
    
    def _ejecutar_mientras(self, nodo):
        """Ejecuta un bucle mientras en Python puro"""
        condicion_nodo = nodo.hijos[0]
        bloque_nodo = nodo.hijos[1]
        
        while True:
            # 1. Evaluar la condición en cada iteración
            resultado_condicion = self.evaluador.evaluar(condicion_nodo)
            
            # Si la condición ya no se cumple, salimos del bucle
            if not resultado_condicion:
                break
                
            # 2. Ejecutar el cuerpo del bucle
            try:
                for sentencia in bloque_nodo.hijos:
                    self.interpretar(sentencia)
            except RomperException:
                break  # Detiene el 'mientras' por completo
            except ContinuarException:
                continue  # Salta directo a la siguiente evaluación de la condición
    
    def _ejecutar_para(self, nodo):
        """Ejecuta un bucle para usando la nueva sintaxis unificada de Wini"""
        # nodo.hijos[0] es el Nodo("IDENTIFICADOR"), extraemos su string con .valor
        variable = nodo.hijos[0].valor 
        valor_anterior = self.variables.get(variable)
        
        # Evaluamos el iterable (la lista de rango() o una variable)
        iterable = self.evaluador.evaluar(nodo.hijos[1])
        bloque = nodo.hijos[2] # El nodo BLOQUE
        
        if isinstance(iterable, dict):
            iterable = list(iterable.keys())
            
        if not isinstance(iterable, (list, str)):
            raise RuntimeError(f"El objeto no es iterable en el bucle para")

        # Ejecución del bucle en Python puro
        for elemento in iterable:
            self.variables[variable] = elemento
            try:
                # bloque.hijos contiene la lista de sentencias que guardamos en el parser
                for sentencia in bloque.hijos:
                    self.interpretar(sentencia)
            except RomperException:
                break
            except ContinuarException:
                continue
                
        if valor_anterior is not None:
            self.variables[variable] = valor_anterior
        else:
            self.variables.pop(variable, None)
    
    def _ejecutar_asignacion_atributo(self, nodo):
        """Ejecuta una asignación de atributo"""
        objeto_nombre = nodo.valor
        atributo_nombre = nodo.hijos[0].valor
        valor = self.evaluador.evaluar(nodo.hijos[1])
        
        if objeto_nombre == "yo" and self.yo:
            self.yo.establecer_atributo(atributo_nombre, valor)
        elif objeto_nombre in self.variables:
            objeto = self.variables[objeto_nombre]
            if isinstance(objeto, Instancia):
                objeto.establecer_atributo(atributo_nombre, valor)
            else:
                raise RuntimeError(f"'{objeto_nombre}' no es una instancia", linea=nodo.linea)
        else:
            raise RuntimeError(f"Variable '{objeto_nombre}' no definida", linea=nodo.linea)
    
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
                raise RuntimeError("Índice de lista debe ser entero", linea=nodo.linea)
            if indice < 0 or indice >= len(objeto):
                raise RuntimeError(f"Índice {indice} fuera de rango para lista de tamaño {len(objeto)}", linea=nodo.linea)
            objeto[indice] = valor
        elif isinstance(objeto, dict):
            objeto[indice] = valor
        else:
            raise RuntimeError(f"No se puede indexar asignación sobre tipo {type(objeto)}", linea=nodo.linea)
    
    def _registrar_paquete(self, nodo):
        """Registra un paquete"""
        nombre = self.evaluador.evaluar(nodo.hijos[0])
        carpeta = None
        if len(nodo.hijos) > 1 and nodo.hijos[1] is not None:
            carpeta = self.evaluador.evaluar(nodo.hijos[1])
        
        if carpeta:
            ruta = os.path.normpath(os.path.join(self.directorio, carpeta))
        else:
            # Buscar en las rutas estándar
            ruta = None
            for base in self.importador.rutas_busqueda:
                posible = os.path.join(base, nombre)
                if os.path.isdir(posible):
                    ruta = posible
                    break
            
            if ruta is None:
                # Crear ruta por defecto en librerias local
                ruta = os.path.join(self.directorio, "librerias", nombre)
        
        self.paquetes[nombre] = ruta
        self.default_paquete = nombre
        
        # Agregar a las rutas de búsqueda del importador
        self.importador.agregar_ruta_busqueda(ruta, prioridad=True)
    
    def _definir_clase(self, nodo):
        """Define una clase, almacenando también su docstring si existe"""
        nombre_padre = nodo.hijos[0].valor
        clase_padre = None
        if nombre_padre:
            if nombre_padre not in self.clases:
                raise RuntimeError(f"Clase padre '{nombre_padre}' no definida", linea=nodo.linea)
            clase_padre = self.clases[nombre_padre]
        
        metodos = {}
        for metodo_nodo in nodo.hijos[1].hijos:
            nombre_metodo = metodo_nodo.valor
            parametros = [param.valor for param in metodo_nodo.hijos[0].hijos]
            cuerpo = metodo_nodo.hijos[1].hijos
            metodos[nombre_metodo] = {
                "parametros": parametros,
                "cuerpo": cuerpo,
                "docstring": getattr(metodo_nodo, "docstring", None)  # docstring de cada método
            }
        
        clase = Clase(nodo.valor, {}, metodos, padre=clase_padre)
        clase.docstring = getattr(nodo, "docstring", None)  # docstring de la clase
        self.clases[nodo.valor] = clase
    
    def _definir_funcion(self, nodo):
        """Define una función, almacenando también su docstring si existe"""
        docstring = getattr(nodo, "docstring", None)
        self.funciones[nodo.valor] = {
            "parametros": [param.valor for param in nodo.hijos[0].hijos],
            "cuerpo": nodo.hijos[1].hijos,
            "docstring": docstring   # <-- nuevo campo
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
        
        # Ejecutar bloque try
        try:
            for sentencia in bloque_try.hijos:
                self.interpretar(sentencia)
        except (ErrorTipo, ErrorValor, ErrorIndice, ErrorAtributo, 
                ErrorImportacion, ErrorMatematico, RuntimeError) as e:
            error_manejado = False
            
            for capturar in bloques_capturar.hijos:
                tipo_error = capturar.valor  # Tipo esperado (o None)
                variable_error = capturar.hijos[0].valor  # Variable donde guardar
                bloque_capturar = capturar.hijos[1]
                
                # Verificar si este bloque maneja el error
                if tipo_error is None or self._error_coincide(e, tipo_error):
                    error_manejado = True
                    
                    variables_backup = self.variables.copy()
                    yo_backup = self.yo
                    
                    if variable_error:
                        # Guardar el mensaje del error en la variable
                        self.variables[variable_error] = e.mensaje if hasattr(e, 'mensaje') else str(e)
                    
                    try:
                        for sentencia in bloque_capturar.hijos:
                            self.interpretar(sentencia)
                    finally:
                        self.variables = variables_backup
                        self.yo = yo_backup
                    
                    break
            
            if not error_manejado:
                raise
        except LanzarException as e:
            error_manejado = False

            # Extraer el mensaje para asignarlo a la variable del capturar.
            # Si el valor es una Instancia wini, exponemos el objeto completo
            # para que el usuario pueda hacer err.mensaje, err.tipo, etc.
            if isinstance(e.valor, Instancia):
                valor_para_variable = e.valor
            else:
                valor_para_variable = str(e.valor)

            for capturar in bloques_capturar.hijos:
                tipo_error    = capturar.valor
                variable_error = capturar.hijos[0].valor
                bloque_capturar = capturar.hijos[1]

                # Coincide si: sin tipo (atrapa todo) O el tipo coincide
                if tipo_error is None or self._error_coincide(e, tipo_error):
                    error_manejado = True

                    variables_backup = self.variables.copy()
                    yo_backup = self.yo

                    if variable_error:
                        self.variables[variable_error] = valor_para_variable

                    try:
                        for sentencia in bloque_capturar.hijos:
                            self.interpretar(sentencia)
                    finally:
                        self.variables = variables_backup
                        self.yo = yo_backup

                    break

            if not error_manejado:
                raise
        
        finally:
            # Ejecutar bloque finally siempre
            for sentencia in bloque_finally.hijos:
                self.interpretar(sentencia)
        
        return resultado

    def _error_coincide(self, error, tipo_nombre):
        """Verifica si un error coincide con el tipo esperado.
        
        tipo_nombre puede ser "Clase" o "modulo.Clase".
        """
        tipos = {
            "ErrorTipo":       ErrorTipo,
            "ErrorValor":      ErrorValor,
            "ErrorIndice":     ErrorIndice,
            "ErrorAtributo":   ErrorAtributo,
            "ErrorImportacion":ErrorImportacion,
            "ErrorMatematico": ErrorMatematico,
            "RuntimeError":    RuntimeError,
        }

        # Error nativo
        if tipo_nombre in tipos:
            return isinstance(error, tipos[tipo_nombre])

        # Resolver el nombre de clase (soporta "modulo.Clase")
        nombre_clase = tipo_nombre
        if "." in tipo_nombre:
            partes = tipo_nombre.split(".", 1)
            nombre_clase = partes[1]  # solo el nombre de la clase para comparar

        # Error personalizado wini: LanzarException cuyo valor es una Instancia
        if isinstance(error, LanzarException) and isinstance(error.valor, Instancia):
            instancia = error.valor
            clase_actual = instancia.clase
            # Recorre la jerarquía de herencia
            while clase_actual is not None:
                if clase_actual.nombre == nombre_clase:
                    return True
                clase_actual = clase_actual.padre
        return False

    def _ejecutar_lanzar(self, nodo):
        """Ejecuta la instrucción lanzar usando excepciones Python"""
        tipo_error = nodo.hijos[0].valor
        nodo_mensaje = nodo.hijos[1]

        mensaje = self.evaluador.evaluar(nodo_mensaje.hijos[0]) if nodo_mensaje.hijos else ""

        # Errores nativos del intérprete
        errores_map = {
            "ErrorTipo":       ErrorTipo,
            "ErrorValor":      ErrorValor,
            "ErrorIndice":     ErrorIndice,
            "ErrorAtributo":   ErrorAtributo,
            "ErrorImportacion":ErrorImportacion,
            "ErrorMatematico": ErrorMatematico,
            "RuntimeError":    RuntimeError,
        }

        if tipo_error and tipo_error in errores_map:
            raise errores_map[tipo_error](str(mensaje), linea=nodo.linea)

        # Resolver clase: puede ser "Clase" o "modulo.Clase"
        clase = None
        nombre_clase = tipo_error

        if tipo_error and "." in tipo_error:
            # Notación modulo.Clase
            partes = tipo_error.split(".", 1)
            modulo_nombre, clase_nombre = partes
            if modulo_nombre in self.variables:
                modulo = self.variables[modulo_nombre]
                if isinstance(modulo, dict) and modulo.get("_tipo") == "modulo":
                    clase = modulo.get("clases", {}).get(clase_nombre)
                    nombre_clase = clase_nombre
        elif tipo_error and tipo_error in self.clases:
            clase = self.clases[tipo_error]

        if clase:
            instancia = Instancia(clase)
            instancia.atributos["mensaje"] = str(mensaje)
            instancia.atributos["tipo"]    = nombre_clase
            raise LanzarException(instancia, linea=nodo.linea)

        elif tipo_error:
            # Tipo desconocido → RuntimeError con prefijo
            raise RuntimeError(f"{tipo_error}: {mensaje}", linea=nodo.linea)

        else:
            # Sin tipo → RuntimeError genérico
            raise RuntimeError(str(mensaje), linea=nodo.linea)

    def _convertir_error_a_valor(self, error):
        """Convierte una excepción Python a un valor que puede usarse en Wini"""
        # Crear objeto error en Wini
        # Por ahora, retornar el mensaje como string
        if hasattr(error, 'mensaje'):
            return error.mensaje
        elif hasattr(error, 'message'):
            return error.message
        else:
            return str(error)
    
    def _rango_nativo(self, *args):
        try:
            """Función nativa rango() que devuelve una lista de números"""
            # Soporta: rango(fin), rango(inicio, fin) o rango(inicio, fin, paso)
            if len(args) == 1:
                return list(range(int(args[0])))
            elif len(args) == 2:
                return list(range(int(args[0]), int(args[1])))
            elif len(args) == 3:
                return list(range(int(args[0]), int(args[1]), int(args[2])))
            else:
                raise RuntimeError("rango() espera entre 1 y 3 argumentos")
        except ValueError as e:
            raise RuntimeError(f"Los Argumentos de rango() deben ser numeros")