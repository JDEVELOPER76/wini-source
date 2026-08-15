# lexer.py
import re
from tokens import TOKENS
from exepciones import SintaxisError

# Precompilar todos los patrones una sola vez (en vez de que re.match()
# los compile/recupere de caché en cada intento) y usarlos con match(str, pos)
# más abajo, para no tener que trocear el string en cada intento fallido.
_TOKENS_COMPILADOS = [(tipo, re.compile(patron)) for tipo, patron in TOKENS]


def _extraer_cadenas_triples(code):
    """Busca cadenas delimitadas por comillas triples (\"\"\" o ''') -incluyendo
    la variante interpolada c\"\"\"...\"\"\" / c'''...'''- y las reemplaza por
    marcadores de una sola línea envueltos en comillas normales. Así el resto
    del lexer (que trabaja línea por línea) no necesita ningún cambio.
    Se conserva el número de saltos de línea internos para no descuadrar la
    numeración de líneas del código que sigue."""
    contenidos = {}
    resultado = []
    i = 0
    n = len(code)
    contador = 0

    while i < n:
        es_c = code[i] == 'c' and code[i + 1:i + 4] in ('"""', "'''")
        es_simple = code[i:i + 3] in ('"""', "'''")

        if es_c or es_simple:
            prefijo = "c" if es_c else ""
            comillas = code[i + 1:i + 4] if es_c else code[i:i + 3]
            inicio_contenido = i + (4 if es_c else 3)

            cierre = code.find(comillas, inicio_contenido)
            if cierre == -1:
                linea = code.count("\n", 0, i) + 1
                raise SintaxisError(f"Cadena triple sin cerrar iniciada en línea {linea}")

            contenido = code[inicio_contenido:cierre]
            marcador = f"\x00T{contador}\x00"
            contenidos[marcador] = contenido
            contador += 1

            resultado.append(prefijo)
            resultado.append('"')
            resultado.append(marcador)
            resultado.append('"')
            resultado.append("\n" * contenido.count("\n"))  # conservar numeración de líneas

            i = cierre + 3
        else:
            resultado.append(code[i])
            i += 1

    return "".join(resultado), contenidos


def _restituir_triple(valor, mapa):
    """Sustituye el marcador de cadena triple por su contenido real dentro
    del valor crudo del token (que aún conserva sus comillas/prefijo 'c')."""
    if isinstance(valor, str) and "\x00T" in valor:
        for marcador, contenido in mapa.items():
            if marcador in valor:
                return valor.replace(marcador, contenido)
    return valor


def lexer(code):
    tokens = []
    # Normalizar saltos de línea
    code = code.replace("\r\n", "\n").replace("\r", "\n")
    # Extraer cadenas triples antes de tokenizar línea por línea
    code, cadenas_triples = _extraer_cadenas_triples(code)
    lines = code.split("\n")
    
    # Recorrer línea por línea
    for line_num, line in enumerate(lines, start=1):
        original_line = line
        # Expandir tabs a 4 espacios
        line = line.expandtabs(4)
        
        # Calcular indentación (espacios al inicio)
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)
        
        # Ignorar líneas vacías o que solo tengan comentario
        if not stripped.strip() or stripped.lstrip().startswith("#"):
            continue
        
        # Token NUEVA_LINEA con valor = indentación
        tokens.append(("NUEVA_LINEA", indent, line_num, 0))
        
        # Tokenizar el contenido (sin indentación)
        content = stripped
        col = indent + 1  # columna donde empieza el contenido (1-based)
        pos = 0
        len_content = len(content)
        while pos < len_content:
            matched = False
            for token_type, regex in _TOKENS_COMPILADOS:
                # match(content, pos) usa un offset interno: no crea un
                # substring nuevo en cada intento como hacía content[pos:]
                m = regex.match(content, pos)
                if m:
                    text = m.group(0)
                    # Ignorar espacios y comentarios
                    if token_type not in ("ESPACIO", "COMENTARIO"):
                        tokens.append((token_type, text, line_num, col))
                    largo = len(text)
                    pos += largo
                    col += largo
                    matched = True
                    break
            if not matched:
                raise SintaxisError(f"Carácter inesperado '{content[pos]}' en línea {line_num}, columna {col}")

    if cadenas_triples:
        tokens = [
            (ttype, _restituir_triple(tvalue, cadenas_triples), tline, tcol)
            for (ttype, tvalue, tline, tcol) in tokens
        ]

    return tokens