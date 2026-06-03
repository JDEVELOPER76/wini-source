# lexer.py
import re
from tokens import TOKENS
from exepciones import SintaxisError

def lexer(code):
    tokens = []
    # Normalizar saltos de línea
    code = code.replace("\r\n", "\n").replace("\r", "\n")
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
        while pos < len(content):
            matched = False
            for token_type, pattern in TOKENS:
                regex = re.match(pattern, content[pos:])
                if regex:
                    text = regex.group(0)
                    # Ignorar espacios y comentarios
                    if token_type not in ("ESPACIO", "COMENTARIO"):
                        tokens.append((token_type, text, line_num, col))
                    pos += len(text)
                    col += len(text)
                    matched = True
                    break
            if not matched:
                raise SintaxisError(f"Carácter inesperado '{content[pos]}' en línea {line_num}, columna {col}")
    
    return tokens