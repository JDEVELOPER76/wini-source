# ============================================================
#  RUNTIME GENERADO POR wn2py — NO EDITAR A MANO
#  Reproduce las semánticas especiales del intérprete Wini
#  necesarias para que el código transpilado se comporte igual.
# ============================================================

from types import SimpleNamespace as _wn_ns

# Caché de módulos importados con 'importar ... [como ...]': evita volver a
# ejecutar el mismo archivo .wn dos veces si se importa desde más de un
# lugar (mismo comportamiento que el intérprete). Las funciones de carga
# '_wn_cargar_modulo_N()' generadas por el transpilador consultan y llenan
# este diccionario.
_wn_modulos_cache = {}


# ---------- Excepciones (mismos nombres que exepciones.py) ----------
class ErrorTipo(Exception):
    pass

class ErrorValor(Exception):
    pass

class ErrorIndice(Exception):
    pass

class ErrorAtributo(Exception):
    pass

class ErrorImportacion(Exception):
    pass

class ErrorMatematico(ArithmeticError):
    pass

class WiniRuntimeError(Exception):
    """Equivalente al RuntimeError propio de Wini (no confundir con el builtin)."""
    pass


_MAPA_ERRORES = {
    "ErrorTipo": ErrorTipo,
    "ErrorValor": ErrorValor,
    "ErrorIndice": ErrorIndice,
    "ErrorAtributo": ErrorAtributo,
    "ErrorImportacion": ErrorImportacion,
    "ErrorMatematico": ErrorMatematico,
    "RuntimeError": WiniRuntimeError,
}


def _wn_lanzar(tipo_nombre, mensaje):
    """Implementa la sentencia 'lanzar'."""
    cls = _MAPA_ERRORES.get(tipo_nombre, WiniRuntimeError if tipo_nombre else WiniRuntimeError)
    if tipo_nombre and tipo_nombre not in _MAPA_ERRORES:
        # Tipo desconocido -> mensaje con prefijo, como el intérprete original
        raise WiniRuntimeError(f"{tipo_nombre}: {mensaje}")
    raise cls(str(mensaje))


# ---------- Formateo de valores (equivalente a utilidades.formatear_texto) ----------
def _wn_fmt(valor):
    if valor is None:
        return "nulo"
    if isinstance(valor, bool):
        return "verdadero" if valor else "falso"
    if isinstance(valor, str):
        return valor
    if isinstance(valor, list):
        return "[" + ", ".join(_wn_fmt(e) for e in valor) + "]"
    if isinstance(valor, dict):
        return "{" + ", ".join(f"{_wn_fmt(k)}: {_wn_fmt(v)}" for k, v in valor.items()) + "}"
    if hasattr(valor, "__class__") and not isinstance(valor, (int, float)):
        # Objeto sin representación de texto propia (p.ej. proveniente de
        # una librería nativa importada) -> usar su str() por defecto
        try:
            return str(valor)
        except Exception:
            return f"<objeto de tipo {valor.__class__.__name__}>"
    return str(valor)


def _wn_verdadero(valor):
    """Equivalente a utilidades.es_verdadero (regla de truthiness de Wini)."""
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return valor != 0
    if valor is None:
        return False
    if hasattr(valor, "__len__"):
        return len(valor) > 0
    return True


# ---------- Funciones nativas de Wini ----------
def escribir(*args):
    for arg in args:
        print(_wn_fmt(arg))
    return None


def leer(prompt=None):
    if prompt is None:
        return input()
    print(prompt, end="")
    return input()


def tipo(valor):
    if isinstance(valor, str):
        return "cadena"
    if isinstance(valor, list):
        return "lista"
    if isinstance(valor, bool):
        return "booleano"
    if isinstance(valor, int):
        return "entero"
    if isinstance(valor, float):
        return "decimal"
    if isinstance(valor, dict):
        return "diccionario"
    if valor is None:
        return "ninguno"
    return valor.__class__.__name__


def rango(*args):
    try:
        if len(args) == 1:
            return list(range(int(args[0])))
        elif len(args) == 2:
            return list(range(int(args[0]), int(args[1])))
        elif len(args) == 3:
            return list(range(int(args[0]), int(args[1]), int(args[2])))
        else:
            raise WiniRuntimeError("rango() espera entre 1 y 3 argumentos")
    except ValueError:
        raise WiniRuntimeError("Los argumentos de rango() deben ser números")


# ---------- Operadores con semántica de Wini ----------
def _wn_add(a, b):
    if isinstance(a, str) or isinstance(b, str):
        return str(a) + str(b)
    return a + b


def _wn_div(a, b):
    if b == 0:
        raise ErrorMatematico("División por cero")
    return a / b


def _wn_mod(a, b):
    if b == 0:
        raise ErrorMatematico("Módulo por cero")
    return a % b


def _wn_in(izq, der):
    if isinstance(der, list):
        return izq in der
    if isinstance(der, str):
        return str(izq) in der
    raise ErrorTipo(f"Operador 'in' no soportado entre {type(izq).__name__} y {type(der).__name__}")


def _wn_iter(iterable):
    """Equivalente a Interprete._normalizar_iterable: normaliza cualquier iterable de 'para'."""
    if isinstance(iterable, str):
        return list(iterable)
    if isinstance(iterable, (list, tuple, range)):
        return list(iterable)
    if isinstance(iterable, dict):
        return list(iterable.keys())
    try:
        return list(iterable)
    except TypeError:
        raise ErrorTipo(f"No se puede iterar sobre '{type(iterable).__name__}'")


def _wn_getitem(obj, indice):
    if isinstance(obj, list):
        if not isinstance(indice, int):
            raise ErrorTipo("Índice de lista debe ser entero")
        if indice < 0 or indice >= len(obj):
            raise ErrorIndice(f"Índice {indice} fuera de rango para lista de tamaño {len(obj)}")
        return obj[indice]
    if isinstance(obj, dict):
        if indice not in obj:
            raise ErrorIndice(f"Clave '{indice}' no encontrada en el diccionario")
        return obj[indice]
    if isinstance(obj, str):
        if not isinstance(indice, int):
            raise ErrorTipo("Índice de cadena debe ser entero")
        if indice < 0 or indice >= len(obj):
            raise ErrorIndice(f"Índice {indice} fuera de rango para cadena de tamaño {len(obj)}")
        return obj[indice]
    raise ErrorTipo(f"No se puede indexar sobre tipo {type(obj).__name__}")


def _wn_setitem(obj, indice, valor):
    if isinstance(obj, list):
        if not isinstance(indice, int):
            raise ErrorTipo("Índice de lista debe ser entero")
        if indice < 0 or indice >= len(obj):
            raise ErrorIndice(f"Índice {indice} fuera de rango para lista de tamaño {len(obj)}")
        obj[indice] = valor
    elif isinstance(obj, dict):
        obj[indice] = valor
    else:
        raise ErrorTipo(f"No se puede indexar asignación sobre tipo {type(obj).__name__}")
    return valor


# ---------- Métodos nativos en español (listas / cadenas / diccionarios) ----------
# Copiados 1:1 de metodos_nativos.py: funciones que reciben el objeto como
# primer argumento (no son métodos "bound"), por eso encajan directamente
# en el despachador _wn_metodo de abajo.

def _l_agregar(self, elemento):
    self.append(elemento); return None
def _l_eliminar(self, elemento):
    try: self.remove(elemento)
    except ValueError: pass
    return None
def _l_eliminar_en(self, posicion):
    try: return self.pop(int(posicion))
    except (IndexError, ValueError): return None
def _l_eliminar_ultimo(self):
    return self.pop() if self else None
def _l_insertar(self, posicion, elemento):
    try: self.insert(int(posicion), elemento)
    except ValueError: self.append(elemento)
    return None
def _l_extender(self, otra):
    if isinstance(otra, list): self.extend(otra)
    elif hasattr(otra, "__iter__"): self.extend(list(otra))
    return None
def _l_contiene(self, elemento): return elemento in self
def _l_posicion(self, elemento):
    try: return self.index(elemento)
    except ValueError: return -1
def _l_contar(self, elemento): return self.count(elemento)
def _l_longitud(self): return len(self)
def _l_vacia(self): return len(self) == 0
def _l_invertir(self): self.reverse(); return None
def _l_ordenar(self):
    try: self.sort()
    except TypeError: pass
    return None
def _l_ordenar_desc(self):
    try: self.sort(reverse=True)
    except TypeError: pass
    return None
def _l_primero(self): return self[0] if self else None
def _l_ultimo(self): return self[-1] if self else None
def _l_limpiar(self): self.clear(); return None
def _l_copiar(self): return self.copy()
def _l_a_texto(self, separador=", "): return separador.join(str(e) for e in self)
def _l_sumar(self):
    total = 0
    for e in self:
        if isinstance(e, (int, float)): total += e
    return total
def _l_maximo(self):
    try: return max(self) if self else None
    except TypeError: return None
def _l_minimo(self):
    try: return min(self) if self else None
    except TypeError: return None

METODOS_LISTA = {
    "agregar": _l_agregar, "eliminar": _l_eliminar, "eliminar_en": _l_eliminar_en,
    "eliminar_ultimo": _l_eliminar_ultimo, "insertar": _l_insertar, "extender": _l_extender,
    "contiene": _l_contiene, "posicion": _l_posicion, "contar": _l_contar,
    "longitud": _l_longitud, "vacia": _l_vacia, "invertir": _l_invertir,
    "ordenar": _l_ordenar, "ordenar_desc": _l_ordenar_desc, "primero": _l_primero,
    "ultimo": _l_ultimo, "limpiar": _l_limpiar, "copiar": _l_copiar,
    "a_texto": _l_a_texto, "sumar": _l_sumar, "maximo": _l_maximo, "minimo": _l_minimo,
}


def _c_longitud(self): return len(self)
def _c_mayuscula(self): return self.upper()
def _c_minuscula(self): return self.lower()
def _c_capitalizar(self): return self.capitalize() if self else ""
def _c_titulo(self): return self.title()
def _c_invertir(self): return self[::-1]
def _c_contiene(self, sub): return str(sub) in self
def _c_indice(self, sub):
    try: return self.index(str(sub))
    except ValueError: return -1
def _c_ultimo_indice(self, sub):
    try: return self.rindex(str(sub))
    except ValueError: return -1
def _c_empieza_con(self, p): return self.startswith(str(p))
def _c_termina_con(self, s): return self.endswith(str(s))
def _c_contar(self, sub): return self.count(str(sub))
def _c_reemplazar(self, viejo, nuevo): return self.replace(str(viejo), str(nuevo))
def _c_unir(self, lista): return self.join(str(e) for e in lista)
def _c_dividir(self, separador=None):
    return self.split() if separador is None else self.split(str(separador))
def _c_recortar(self): return self.strip()
def _c_recortar_izquierda(self): return self.lstrip()
def _c_recortar_derecha(self): return self.rstrip()
def _c_extraer(self, inicio, fin=None):
    return self[int(inicio):] if fin is None else self[int(inicio):int(fin)]
def _c_repetir(self, veces):
    try: return self * int(veces)
    except (ValueError, TypeError): return self
def _c_a_entero(self):
    try: return int(self)
    except ValueError: return "0"
def _c_a_decimal(self):
    try: return float(self)
    except ValueError: return "0.0"
def _c_a_lista(self): return list(self)
def _c_es_numero(self):
    try: float(self); return True
    except ValueError: return False
def _c_es_digito(self): return self.isdigit()
def _c_es_alfabetico(self): return self.isalpha()
def _c_es_vacia(self): return len(self) == 0
def _c_es_palindromo(self):
    t = "".join(c.lower() for c in self if c.isalnum())
    return t == t[::-1]
def _c_es_mayuscula(self): return self.isupper()
def _c_es_minuscula(self): return self.islower()
def _c_a_slug(self):
    import re
    s = re.sub(r"[^\w\-]", "", re.sub(r"\s+", "-", self.lower()))
    return s.strip("-")
def _c_acortar(self, longitud, sufijo="..."):
    try:
        n = int(longitud)
        return self if len(self) <= n else self[:n] + sufijo
    except (ValueError, TypeError): return self

METODOS_CADENA = {
    "longitud": _c_longitud, "mayuscula": _c_mayuscula, "minuscula": _c_minuscula,
    "capitalizar": _c_capitalizar, "titulo": _c_titulo, "invertir": _c_invertir,
    "contiene": _c_contiene, "indice": _c_indice, "ultimo_indice": _c_ultimo_indice,
    "empieza_con": _c_empieza_con, "termina_con": _c_termina_con, "contar": _c_contar,
    "reemplazar": _c_reemplazar, "unir": _c_unir, "dividir": _c_dividir,
    "recortar": _c_recortar, "recortar_izquierda": _c_recortar_izquierda,
    "recortar_derecha": _c_recortar_derecha, "extraer": _c_extraer, "repetir": _c_repetir,
    "a_entero": _c_a_entero, "a_decimal": _c_a_decimal, "a_lista": _c_a_lista,
    "es_numero": _c_es_numero, "es_digito": _c_es_digito, "es_alfabetico": _c_es_alfabetico,
    "es_vacia": _c_es_vacia, "es_palindromo": _c_es_palindromo, "es_mayuscula": _c_es_mayuscula,
    "es_minuscula": _c_es_minuscula, "a_slug": _c_a_slug, "acortar": _c_acortar,
}


def _d_obtener(self, clave, defecto=None): return self.get(clave, defecto)
def _d_establecer(self, clave, valor): self[clave] = valor; return None
def _d_eliminar(self, clave): return self.pop(clave, None)
def _d_contiene(self, clave): return clave in self
def _d_claves(self): return list(self.keys())
def _d_valores(self): return list(self.values())
def _d_pares(self): return [[k, v] for k, v in self.items()]
def _d_longitud(self): return len(self)
def _d_vacio(self): return len(self) == 0
def _d_limpiar(self): self.clear(); return None
def _d_copiar(self): return self.copy()
def _d_unir(self, otro):
    if isinstance(otro, dict): self.update(otro)
    return None
def _d_sacar(self, clave): return self.pop(clave, None)
def _d_tiene_clave(self, clave): return clave in self
def _d_tiene_valor(self, valor): return valor in self.values()
def _d_a_lista_claves(self): return list(self.keys())
def _d_a_lista_valores(self): return list(self.values())
def _d_defecto(self, clave, valor_defecto):
    if clave not in self: self[clave] = valor_defecto
    return self[clave]
def _d_incrementar(self, clave, cantidad=1):
    self[clave] = self.get(clave, 0) + cantidad
    return self[clave]

METODOS_DICCIONARIO = {
    "obtener": _d_obtener, "establecer": _d_establecer, "eliminar": _d_eliminar,
    "contiene": _d_contiene, "claves": _d_claves, "valores": _d_valores,
    "pares": _d_pares, "longitud": _d_longitud, "vacio": _d_vacio,
    "limpiar": _d_limpiar, "copiar": _d_copiar, "unir": _d_unir, "sacar": _d_sacar,
    "tiene_clave": _d_tiene_clave, "tiene_valor": _d_tiene_valor,
    "a_lista_claves": _d_a_lista_claves, "a_lista_valores": _d_a_lista_valores,
    "defecto": _d_defecto, "incrementar": _d_incrementar,
}


def _wn_metodo(obj, nombre, *args, **kwargs):
    """Despachador de llamadas 'obj.metodo(args)':
    primero intenta métodos nativos en español (listas/cadenas/diccionarios,
    igual que ejecutor.py), y si no aplica, cae a un método real del objeto
    (por ejemplo, de un objeto proveniente de una librería nativa
    importada). Admite argumentos con nombre (kwargs), igual que el
    intérprete."""
    if isinstance(obj, list) and nombre in METODOS_LISTA:
        return METODOS_LISTA[nombre](obj, *args, **kwargs)
    if isinstance(obj, str) and nombre in METODOS_CADENA:
        return METODOS_CADENA[nombre](obj, *args, **kwargs)
    if isinstance(obj, dict) and nombre in METODOS_DICCIONARIO:
        return METODOS_DICCIONARIO[nombre](obj, *args, **kwargs)
    metodo = getattr(obj, nombre, None)
    if callable(metodo):
        return metodo(*args, **kwargs)
    raise ErrorAtributo(f"'{type(obj).__name__}' no tiene método '{nombre}'")