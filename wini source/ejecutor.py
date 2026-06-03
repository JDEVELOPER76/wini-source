# ejecutor.py
"""Ejecución de funciones y métodos en el intérprete wini"""

from clases import Clase, Instancia
from exepciones import RuntimeError, RetornoException
from utilidades import formatear_texto


class ClasePython(Clase):
    """Wrapper para clases Python que las hace compatibles con wn"""
    def __init__(self, nombre, clase_python):
        self.nombre = nombre
        self.clase_python = clase_python
        self.padre = None
        self.atributos = {}
        self.metodos = {}
    
    def obtener_metodo(self, nombre):
        """Obtiene un método de la clase Python"""
        if hasattr(self.clase_python, nombre):
            metodo = getattr(self.clase_python, nombre)
            if callable(metodo):
                return metodo
        if nombre in self.metodos:
            return self.metodos[nombre]
        if self.padre:
            return self.padre.obtener_metodo(nombre)
        return None


class InstanciaPython(Instancia):
    """Wrapper para instancias de clases Python"""
    def __init__(self, clase_wn, instancia_python):
        self.clase = clase_wn
        self.instancia_python = instancia_python
        self.atributos = {}
    
    def obtener_atributo(self, nombre):
        if hasattr(self.instancia_python, nombre):
            return getattr(self.instancia_python, nombre)
        if nombre in self.atributos:
            return self.atributos[nombre]
        return None
    
    def establecer_atributo(self, nombre, valor):
        setattr(self.instancia_python, nombre, valor)
    
    def obtener_metodo(self, nombre):
        if hasattr(self.instancia_python, nombre):
            metodo = getattr(self.instancia_python, nombre)
            if callable(metodo):
                return metodo
        return None


class Ejecutor:
    """Encapsula la lógica de ejecución de funciones y métodos"""
    
    def __init__(self, interprete):
        self.interprete = interprete
    
    def ejecutar_funcion(self, nodo):
        """Ejecuta una llamada a función"""
        nombre = nodo.valor
        argumentos = [self.interprete.evaluador.evaluar(arg) for arg in nodo.hijos]
        
        # 🔧 NUEVO: Soporte para modulo.funcion()
        if '.' in nombre:
            partes = nombre.split('.')
            modulo_nombre = '.'.join(partes[:-1])
            funcion_nombre = partes[-1]
            
            # Buscar el módulo
            if modulo_nombre in self.interprete.variables:
                modulo = self.interprete.variables[modulo_nombre]
                if isinstance(modulo, dict) and modulo.get("_tipo") == "modulo":
                    # Buscar en funciones del módulo
                    if funcion_nombre in modulo.get("funciones", {}):
                        funcion = modulo["funciones"][funcion_nombre]
                        if callable(funcion):
                            return funcion(*argumentos)
                        # Función Wini dentro del módulo: ejecutar con el contexto
                        # de variables del módulo (para que vea exepciones, arit_codefuente, etc.)
                        return self._ejecutar_funcion_wini(
                            funcion, argumentos, nodo, funcion_nombre,
                            variables_modulo=modulo["variables"]
                        )
                    
                    # Buscar en clases del módulo (constructor)
                    if funcion_nombre in modulo.get("clases", {}):
                        clase = modulo["clases"][funcion_nombre]
                        return self._ejecutar_constructor_clase(clase, argumentos, nodo)
        
        
        # Llamada a función definida por el usuario
        if nombre in self.interprete.funciones:
            return self._ejecutar_funcion_usuario(nombre, argumentos, nodo)
        
        # Funciones nativas
        return self._ejecutar_funcion_nativa(nombre, argumentos, nodo)

    def _ejecutar_constructor_clase(self, clase, argumentos, nodo):
        instancia = Instancia(clase)
        
        constructor = self._buscar_constructor(clase)
        
        if constructor:
            parametros = constructor["parametros"]
            cuerpo = constructor["cuerpo"]
            
            if len(argumentos) != len(parametros):
                raise RuntimeError(...)
            
            self._ejecutar_cuerpo_metodo(parametros, argumentos, cuerpo, instancia)
        
        return instancia
    
    def _buscar_constructor(self, clase):
        """Busca el constructor en la cadena de herencia"""
        clase_actual = clase
        while clase_actual:
            constructor = clase_actual.obtener_metodo("constructor")
            if constructor:
                return constructor
            clase_actual = clase_actual.padre
        return None
    
    def _ejecutar_funcion_usuario(self, nombre, argumentos, nodo):
        """Ejecuta una función definida por el usuario (Wini o Python)"""
        funcion_def = self.interprete.funciones[nombre]
        return self._ejecutar_funcion_wini(funcion_def, argumentos, nodo, nombre)
    
    def _ejecutar_funcion_wini(self, funcion_def, argumentos, nodo, nombre="<función>", variables_modulo=None):
        """Ejecuta una función Wini dada su definición directamente"""
        # Si es una función importada de Python (callable)
        if callable(funcion_def) and not isinstance(funcion_def, dict):
            try:
                return funcion_def(*argumentos)
            except TypeError as e:
                raise RuntimeError(f"Error al llamar función '{nombre}': {e}", linea=nodo.linea)
        
        # Si es una función definida en Wini (diccionario)
        parametros = funcion_def["parametros"]
        cuerpo = funcion_def["cuerpo"]
        if len(argumentos) != len(parametros):
            raise RuntimeError(
                f"La función '{nombre}' espera {len(parametros)} argumentos, "
                f"pero recibió {len(argumentos)}",
                linea=nodo.linea
            )
        
        variables_backup = self.interprete.variables.copy()
        yo_backup = self.interprete.yo
        
        # Si se proporcionan variables del módulo, crear un contexto de ejecución
        # que tenga acceso al módulo (imports, otras funciones) más los parámetros.
        # Usamos una copia para no contaminar el dict del módulo con vars temporales.
        if variables_modulo is not None:
            contexto = variables_modulo.copy()
            self.interprete.variables = contexto
        
        # Agregar los parámetros al contexto de ejecución
        for param, arg in zip(parametros, argumentos):
            self.interprete.variables[param] = arg
        
        resultado = None
        try:
            for sentencia in cuerpo:
                self.interprete.interpretar(sentencia)
        except RetornoException as e:
            resultado = e.valor
        finally:
            # Restaurar SIEMPRE, incluso si se lanzó una excepción (LanzarException, etc.)
            # Esto es crítico para que el contexto global no quede contaminado con
            # variables del módulo cuando una función lanza una excepción.
            self.interprete.variables = variables_backup
            self.interprete.yo = yo_backup
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
            if isinstance(valor, bool):
                return "booleano"
            elif isinstance(valor, int):
                return "entero"
            elif isinstance(valor, float):
                return "decimal"
            elif isinstance(valor, str):
                return "cadena"
            elif isinstance(valor, list):
                return "lista"
            elif isinstance(valor, dict):
                return "diccionario"
            else:
                return "desconocido"
        else:
            raise RuntimeError(f"Función '{nombre}' no definida", linea=nodo.linea)
    
    def ejecutar_metodo(self, nodo):
        """Ejecuta un método en una instancia: obj.metodo(args)"""
        objeto_nombre = nodo.valor
        metodo_nombre = nodo.hijos[0].valor
        argumentos_nodos = nodo.hijos[1:]
        argumentos = [self.interprete.evaluador.evaluar(arg) for arg in argumentos_nodos]
        
        # Obtener la instancia desde las variables
        if objeto_nombre not in self.interprete.variables:
            raise RuntimeError(f"Variable '{objeto_nombre}' no definida", linea=nodo.linea)
        
        objeto = self.interprete.variables[objeto_nombre]
        
        # 🔧 NUEVO: Soporte para modulo.funcion()
        if isinstance(objeto, dict) and objeto.get("_tipo") == "modulo":
            # Es un módulo, buscar la función
            if metodo_nombre in objeto.get("funciones", {}):
                funcion = objeto["funciones"][metodo_nombre]
                
                # Si es una función callable de Python
                if callable(funcion):
                    return funcion(*argumentos)
                
                # Si es una función Wini (diccionario)
                if isinstance(funcion, dict):
                    return self._ejecutar_funcion_wini(
                        funcion, 
                        argumentos, 
                        nodo, 
                        f"{objeto_nombre}.{metodo_nombre}",
                        variables_modulo=objeto.get("variables", {})  # Pasar variables del módulo
                    )
            
            # Buscar en clases del módulo (constructor)
            if metodo_nombre in objeto.get("clases", {}):
                clase = objeto["clases"][metodo_nombre]
                return self._ejecutar_constructor_clase(clase, argumentos, nodo)
            
            # Buscar en variables del módulo
            if metodo_nombre in objeto.get("variables", {}):
                var = objeto["variables"][metodo_nombre]
                if callable(var):
                    return var(*argumentos)
            
            raise RuntimeError(f"Módulo '{objeto_nombre}' no tiene '{metodo_nombre}'", linea=nodo.linea)
        
        # Verificar que sea una instancia
        if not isinstance(objeto, Instancia):
            raise RuntimeError(f"'{objeto_nombre}' no es una instancia", linea=nodo.linea)
        
        instancia = objeto
        
        # Buscar el método en la cadena de herencia
        metodo = self._buscar_metodo(instancia.clase, metodo_nombre)
        
        if not metodo:
            raise RuntimeError(
                f"'{instancia.clase.nombre}' no tiene método '{metodo_nombre}'",
                linea=nodo.linea
            )
        
        # Si es un método Python callable
        if callable(metodo):
            try:
                return metodo(instancia, *argumentos)
            except TypeError as e:
                raise RuntimeError(f"Error al ejecutar {metodo_nombre}: {e}", linea=nodo.linea)
        
        # Si es un método Wini (diccionario)
        if isinstance(metodo, dict):
            parametros = metodo["parametros"]
            cuerpo = metodo["cuerpo"]
            if len(argumentos) != len(parametros):
                raise RuntimeError(
                    f"El método '{metodo_nombre}' espera {len(parametros)} argumentos, "
                    f"pero recibió {len(argumentos)}",
                    linea=nodo.linea
                )
            return self._ejecutar_cuerpo_metodo(parametros, argumentos, cuerpo, instancia)
        
        raise RuntimeError(f"Método '{metodo_nombre}' no es válido", linea=nodo.linea)
    
    def _buscar_metodo(self, clase, nombre_metodo):
        """Busca un método en la cadena de herencia"""
        clase_actual = clase
        while clase_actual:
            metodo = clase_actual.obtener_metodo(nombre_metodo)
            if metodo:
                return metodo
            clase_actual = clase_actual.padre
        return None
    
    def _ejecutar_cuerpo_metodo(self, parametros, argumentos, cuerpo, instancia):
        """Ejecuta el cuerpo de un método con su contexto"""
        variables_backup = self.interprete.variables.copy()
        yo_backup = self.interprete.yo
        
        # Limpiar variables que podrían interferir
        for param in parametros:
            if param in self.interprete.variables:
                del self.interprete.variables[param]
        
        # Asignar parámetros
        for param, arg in zip(parametros, argumentos):
            self.interprete.variables[param] = arg
        
        # Establecer la instancia actual
        self.interprete.yo = instancia
        self.interprete.variables['yo'] = instancia
        self.interprete.variables['self'] = instancia
        
        resultado = None
        try:
            for sentencia in cuerpo:
                self.interprete.interpretar(sentencia)
        except RetornoException as e:
            resultado = e.valor
        
        # Restaurar contexto
        self.interprete.variables = variables_backup
        self.interprete.yo = yo_backup
        
        return resultado