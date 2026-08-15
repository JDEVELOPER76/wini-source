# tokens.py
"""Definición de los tipos de token y los patrones léxicos del lenguaje Wini."""

from dataclasses import dataclass
from enum import Enum


class TipoToken(str, Enum):
    """Tipos de token que puede producir el lexer.

    Hereda de `str` a propósito: así `TipoToken.ENTERO == "ENTERO"` es
    `True` y el resto del proyecto (parser, evaluador, transpilador...)
    sigue funcionando sin cambios aunque compare `nodo.tipo` contra
    literales de texto como venía haciendo.
    """

    COMENTARIO = "COMENTARIO"
    CADENA_INTERPOLADA = "CADENA_INTERPOLADA"
    CADENA_TEXTO = "CADENA_TEXTO"
    NINGUNO = "NINGUNO"
    BOOLEANO = "BOOLEANO"
    DECIMAL = "DECIMAL"
    ENTERO = "ENTERO"
    PALABRA_CLAVE = "PALABRA_CLAVE"
    OPERADOR_LOGICO = "OPERADOR_LOGICO"
    TIPO_DATO = "TIPO_DATO"
    COMPARADOR = "COMPARADOR"
    OPERADOR = "OPERADOR"
    IDENTIFICADOR = "IDENTIFICADOR"
    PARENTESIS = "PARENTESIS"
    CORCHETE = "CORCHETE"
    LLAVE = "LLAVE"
    COMA = "COMA"
    PUNTOS = "PUNTOS"
    PUNTO = "PUNTO"
    ESPACIO = "ESPACIO"

    def __str__(self):
        # Evita el "TipoToken.ENTERO" que da Enum por defecto en mensajes
        # de error / f-strings; con esto se ve simplemente "ENTERO".
        return self.value


@dataclass(frozen=True, slots=True)
class DefinicionToken:
    """Une un `TipoToken` con el patrón regex que lo reconoce."""

    tipo: TipoToken
    patron: str

    def __iter__(self):
        # Mantiene compatible el desempaquetado `for tipo, patron in TOKENS`
        # que ya usa lexer.py, sin tener que tocarlo.
        yield self.tipo
        yield self.patron

    def __repr__(self):
        return f"DefinicionToken({self.tipo}, {self.patron!r})"


# El orden importa: el lexer prueba los patrones en este mismo orden y usa
# el primero que coincida (por eso, p.ej., las palabras clave van antes
# que IDENTIFICADOR).
TOKENS = [
    # 📝 Comentarios y cadenas
    DefinicionToken(TipoToken.COMENTARIO, r"#[^\n]*"),
    DefinicionToken(TipoToken.CADENA_INTERPOLADA, r'c"[^"\n]*"|c\'[^\'\n]*\''),
    DefinicionToken(TipoToken.CADENA_TEXTO, r'"[^"]*"|\'[^\']*\''),

    # 🔢 Literales
    DefinicionToken(TipoToken.NINGUNO, r"\b(nulo)\b"),
    DefinicionToken(TipoToken.BOOLEANO, r"\b(verdadero|falso)\b"),
    DefinicionToken(TipoToken.DECIMAL, r"\d+\.\d+"),
    DefinicionToken(TipoToken.ENTERO, r"\d+"),  # Solo dígitos, sin signo

    # 🔑 Palabras clave
    DefinicionToken(TipoToken.PALABRA_CLAVE, r"\b("
        r"entonces|escribir|sino|si|leer|"
        r"funcion|retornar|tipo|importar|"
        r"paquete|mientras|para|"
        r"romper|continuar|hasta|paso|fin|"
        r"intentar|capturar|finalmente|lanzar|como"
    r")\b"),

    # ⚙️ Operadores
    DefinicionToken(TipoToken.OPERADOR_LOGICO, r"\b(y|o|no|en)\b"),
    DefinicionToken(TipoToken.TIPO_DATO, r"\b(entero|decimal|cadena|booleano|lista)\b"),
    DefinicionToken(TipoToken.COMPARADOR, r"==|!=|<>|<=|>=|<|>"),
    DefinicionToken(TipoToken.OPERADOR, r"[+\-*/%=]"),  # El - aquí captura el signo menos

    # 🏷️ Identificadores
    DefinicionToken(TipoToken.IDENTIFICADOR, r"[a-zA-Z_][a-zA-Z0-9_]*"),

    # 🔣 Símbolos
    DefinicionToken(TipoToken.PARENTESIS, r"[()]"),
    DefinicionToken(TipoToken.CORCHETE, r"[\[\]]"),
    DefinicionToken(TipoToken.LLAVE, r"[{}]"),
    DefinicionToken(TipoToken.COMA, r","),
    DefinicionToken(TipoToken.PUNTOS, r":"),
    DefinicionToken(TipoToken.PUNTO, r"\."),

    # ⬜ Espacios (ignorados)
    DefinicionToken(TipoToken.ESPACIO, r"\s+"),
]
