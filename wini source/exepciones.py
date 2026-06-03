# exepciones.py
"""Excepciones del intérprete wini"""

class RetornoException(Exception):
    """Excepción para manejar retornos dentro de funciones."""
    def __init__(self, valor):
        self.valor = valor
        super().__init__()

class RomperException(Exception):
    """Excepción para romper bucles."""
    pass

class ContinuarException(Exception):
    """Excepción para continuar en bucles."""
    pass

# === NUEVAS EXCEPCIONES PARA TRY-CATCH ===
class LanzarException(Exception):
    """Excepción para lanzar errores manualmente (lanzar)"""
    def __init__(self, valor, linea=None):
        self.valor = valor
        self.linea = linea
        super().__init__(str(valor))

class ErrorConLinea(Exception):
    """Base para excepciones que tienen línea y columna."""
    def __init__(self, mensaje, linea=None, columna=None, texto=None):
        self.mensaje = mensaje
        self.linea = linea
        self.columna = columna
        self.texto = texto
        super().__init__(mensaje)

    def __str__(self):
        base = self.mensaje
        if self.linea is not None:
            base += f" (línea {self.linea}"
            if self.columna is not None:
                base += f", columna {self.columna}"
            base += ")"
        if self.texto:
            base += f"\n  {self.texto}"
        return base

class SintaxisError(ErrorConLinea):
    """Error de sintaxis con ubicación."""
    pass

class RuntimeError(ErrorConLinea):
    """Error en tiempo de ejecución con ubicación."""
    pass

# Nuevos tipos de error para try-catch
class ErrorTipo(ErrorConLinea):
    """Error de tipo (TypeError)"""
    pass

class ErrorValor(ErrorConLinea):
    """Error de valor (ValueError)"""
    pass

class ErrorIndice(ErrorConLinea):
    """Error de índice (IndexError)"""
    pass

class ErrorAtributo(ErrorConLinea):
    """Error de atributo (AttributeError)"""
    pass

class ErrorImportacion(ErrorConLinea):
    """Error de importación (ImportError)"""
    pass

class ErrorMatematico(ErrorConLinea):
    """Error matemático (ZeroDivisionError, etc)"""
    pass