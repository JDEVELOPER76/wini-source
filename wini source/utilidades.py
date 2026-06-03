# utilidades.py
"""Funciones auxiliares para el intérprete wini"""

from clases import Instancia



def formatear_texto(valor):
    """Convierte valores wn a texto para escribir e interpolación."""
    if valor is None:  # ← NUEVO
        return "nulo"
    if isinstance(valor, bool):
        return "verdadero" if valor else "falso"
    if isinstance(valor, list):
        elementos_formateados = [formatear_texto(elem) for elem in valor]
        return "[" + ", ".join(elementos_formateados) + "]"
    if isinstance(valor, dict):
        pares = []
        for k, v in valor.items():
            pares.append(f"{formatear_texto(k)}: {formatear_texto(v)}")
        return "{" + ", ".join(pares) + "}"
    if isinstance(valor, Instancia):
        return f"<Instancia de {valor.clase.nombre}>"
    return str(valor)

def contiene_interpolacion(texto):
    """Verifica si un texto contiene interpolaciones {}"""
    return "{" in texto and "}" in texto


def interpolar_cadena(texto, evaluar_fragmento_func):
    """Interpola variables en una cadena de texto.
    
    Args:
        texto: La cadena a interpolar
        evaluar_fragmento_func: Función que evalúa fragmentos de código
    """
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
    return True
