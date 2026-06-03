class Clase:
    """Representa una clase en el lenguaje .wn"""
    def __init__(self, nombre, atributos=None, metodos=None, padre=None):
        self.nombre = nombre
        self.atributos = atributos or {}  # {nombre: valor}
        self.metodos = metodos or {}      # {nombre: {parametros: [...], cuerpo: [...], retorno: ...}}
        self.padre = padre                # Referencia a la clase padre
        self.docstring  = None  # Documentación de la clase
    
    def obtener_metodo(self, nombre):
        """Obtiene un método, buscando en la clase y sus padres"""
        if nombre in self.metodos:
            return self.metodos[nombre]
        elif self.padre:
            return self.padre.obtener_metodo(nombre)
        return None
    
    def obtener_atributo_clase(self, nombre):
        """Obtiene un atributo de clase, buscando en la clase y sus padres"""
        if nombre in self.atributos:
            return self.atributos[nombre]
        elif self.padre:
            return self.padre.obtener_atributo_clase(nombre)
        return None
    
    def __repr__(self):
        return f"<Clase '{self.nombre}'>"


class Instancia:
    """Representa una instancia de una clase"""
    def __init__(self, clase):
        self.clase = clase
        self.atributos = {}  # Variables de instancia
    
    def obtener_atributo(self, nombre):
        """Obtiene el valor de un atributo (busca en instancia y clase/padres)"""
        if nombre in self.atributos:
            return self.atributos[nombre]
        # Buscar en la clase y sus padres
        valor = self.clase.obtener_atributo_clase(nombre)
        if valor is not None:
            return valor
        return None
    
    def establecer_atributo(self, nombre, valor):
        """Establece el valor de un atributo"""
        self.atributos[nombre] = valor
    
    def obtener_metodo(self, nombre):
        """Obtiene un método buscando en la clase y sus padres"""
        return self.clase.obtener_metodo(nombre)
    
    def __repr__(self):
        return f"<Instancia de {self.clase.nombre}>"
