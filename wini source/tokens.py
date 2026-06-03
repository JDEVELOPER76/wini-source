# tokens.py
TOKENS = [
    # 📝 Comentarios y cadenas
    ("COMENTARIO",         r"#[^\n]*"),
    ("CADENA_INTERPOLADA", r'c"[^"\n]*"|c\'[^\'\n]*\''),
    ("CADENA_TEXTO",       r'"[^"]*"|\'[^\']*\''),
    
    # 🔢 Literales
    ("NINGUNO",    r"\b(nulo)\b"),  # ← NUEVO
    ("BOOLEANO",   r"\b(verdadero|falso)\b"),
    ("DECIMAL",    r"-?\d+\.\d+"),
    ("ENTERO",     r"-?\d+"),
    
# tokens.py

    ("PALABRA_CLAVE", r"\b("
        r"entonces|escribir|sino|si|leer|"
        r"funcion|retornar|tipo|importar|"
        r"paquete|clase|mientras|para|"
        r"romper|continuar|hasta|paso|fin|"
        r"intentar|capturar|finalmente|lanzar|como"
    r")\b"),
    
    # ⚙️ Operadores
    ("OPERADOR_LOGICO", r"\b(y|o|no|en)\b"),
    ("TIPO_DATO",       r"\b(entero|decimal|cadena|booleano|lista)\b"),
    ("COMPARADOR",      r"==|!=|<>|<=|>=|<|>"),
    ("OPERADOR",        r"[+\-*/%=]"),  # ← El % ya está aquí
    
    # 🏷️ Identificadores
    ("IDENTIFICADOR", r"[a-zA-Z_][a-zA-Z0-9_]*"),
    
    # 🔣 Símbolos
    ("PARENTESIS", r"[()]"),
    ("CORCHETE",   r"[\[\]]"),
    ("LLAVE",      r"[{}]"),
    ("COMA",       r","),
    ("PUNTOS",     r":"),
    ("PUNTO",      r"\."),
    
    # ⬜ Espacios (ignorados)
    ("ESPACIO", r"\s+"),
]