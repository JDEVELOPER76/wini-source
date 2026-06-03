# wini_bridge.py
"""
API de bridging entre Python y Wini.

Para exponer funciones o clases Python a Wini, crea un archivo .wipy
y usa el decorador @exportar o la clase PythonAPI.

Ejemplo de archivo  matematica.wbridge
─────────────────────────────────────
    from wpython import PythonAPI
    import math

    modulo = PythonAPI("matematica")

    @modulo.funcion
    def raiz(n):
        return math.sqrt(n)

    @modulo.funcion
    def potencia(base, exp):
        return base ** exp

    @modulo.constante("PI", math.pi)
    @modulo.constante("E", math.e)

─────────────────────────────────────
Desde Wini:
    importar("matematica")
    escribir(matematica.raiz(16))   # → 4.0
    escribir(matematica.PI)         # → 3.14159...
"""

from functools import wraps


class PythonAPI:
    """Define un módulo puente que controla exactamente qué se expone a Wini."""

    def __init__(self, nombre):
        self.nombre = nombre
        self._funciones = {}
        self._clases = {}
        self._variables = {}

    # ── Decoradores ──────────────────────────────────────────────────────────

    def funcion(self, fn=None, *, nombre=None):
        """
        Expone una función Python a Wini.

        Uso:
            @modulo.funcion
            def suma(a, b): ...

            @modulo.funcion(nombre="sumar")
            def _suma_interna(a, b): ...
        """
        if fn is None:
            # Llamado con argumento: @modulo.funcion(nombre="...")
            def decorator(f):
                n = nombre or f.__name__
                self._funciones[n] = f
                return f
            return decorator
        # Llamado sin argumento: @modulo.funcion
        self._funciones[fn.__name__] = fn
        return fn

    def clase(self, cls=None, *, nombre=None):
        """
        Expone una clase Python a Wini.

        Uso:
            @modulo.clase
            class MiClase: ...
        """
        if cls is None:
            def decorator(c):
                n = nombre or c.__name__
                self._clases[n] = c
                return c
            return decorator
        self._clases[cls.__name__] = cls
        return cls

    def constante(self, nombre_var, valor):
        """
        Expone una constante a Wini.

        Uso:
            modulo.constante("PI", 3.14159)
        """
        self._variables[nombre_var] = valor
        return self  # permite encadenar

    # ── Conversión al formato interno de Wini ────────────────────────────────

    def _a_modulo_wini(self, ruta=None):
        """Convierte este puente al dict interno que usa el importador de Wini."""
        from ejecutor import ClasePython  # importación diferida para evitar ciclos

        clases_wini = {
            nombre: ClasePython(nombre, cls)
            for nombre, cls in self._clases.items()
        }

        return {
            "_tipo": "modulo",
            "nombre": self.nombre,
            "ruta": ruta,
            "variables": dict(self._variables),
            "funciones": dict(self._funciones),
            "clases": clases_wini,
        }