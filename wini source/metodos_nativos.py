# metodos_nativos.py
"""Registro de métodos nativos para tipos básicos"""

# ============= MÉTODOS PARA LISTAS =============

def lista_agregar(self, elemento):
    """lista.agregar(elemento) -> None"""
    self.append(elemento)
    return None

def lista_eliminar(self, elemento):
    """lista.eliminar(elemento) -> None"""
    try:
        self.remove(elemento)
    except ValueError:
        pass
    return None

def lista_eliminar_en(self, posicion):
    """lista.eliminar_en(posicion) -> elemento_eliminado"""
    try:
        return self.pop(int(posicion))
    except (IndexError, ValueError):
        return None

def lista_eliminar_ultimo(self):
    """lista.eliminar_ultimo() -> elemento_eliminado"""
    return self.pop() if self else None

def lista_insertar(self, posicion, elemento):
    """lista.insertar(posicion, elemento) -> None"""
    try:
        self.insert(int(posicion), elemento)
    except ValueError:
        self.append(elemento)
    return None

def lista_extender(self, otra_lista):
    """lista.extender(otra_lista) -> None"""
    if isinstance(otra_lista, list):
        self.extend(otra_lista)
    elif hasattr(otra_lista, '__iter__'):
        self.extend(list(otra_lista))
    return None

def lista_contiene(self, elemento):
    """lista.contiene(elemento) -> booleano"""
    return elemento in self

def lista_posicion(self, elemento):
    """lista.posicion(elemento) -> entero (o -1 si no existe)"""
    try:
        return self.index(elemento)
    except ValueError:
        return -1

def lista_contar(self, elemento):
    """lista.contar(elemento) -> entero"""
    return self.count(elemento)

def lista_longitud(self):
    """lista.longitud() -> entero"""
    return len(self)

def lista_vacia(self):
    """lista.vacia() -> booleano"""
    return len(self) == 0

def lista_invertir(self):
    """lista.invertir() -> None"""
    self.reverse()
    return None

def lista_ordenar(self):
    """lista.ordenar() -> None"""
    try:
        self.sort()
    except TypeError:
        pass
    return None

def lista_ordenar_desc(self):
    """lista.ordenar_desc() -> None"""
    try:
        self.sort(reverse=True)
    except TypeError:
        pass
    return None

def lista_primero(self):
    """lista.primero() -> elemento o None"""
    return self[0] if self else None

def lista_ultimo(self):
    """lista.ultimo() -> elemento o None"""
    return self[-1] if self else None

def lista_limpiar(self):
    """lista.limpiar() -> None"""
    self.clear()
    return None

def lista_copiar(self):
    """lista.copiar() -> nueva_lista"""
    return self.copy()

def lista_a_texto(self, separador=", "):
    """lista.a_texto(separador) -> cadena"""
    elementos = [str(elem) for elem in self]
    return separador.join(elementos)

def lista_sumar(self):
    """lista.sumar() -> numero (solo elementos numéricos)"""
    total = 0
    for elem in self:
        if isinstance(elem, (int, float)):
            total += elem
        elif hasattr(elem, '__add__') and not isinstance(elem, str):
            try:
                total += elem
            except TypeError:
                pass
    return total

def lista_maximo(self):
    """lista.maximo() -> elemento máximo"""
    if not self:
        return None
    try:
        return max(self)
    except TypeError:
        return None

def lista_minimo(self):
    """lista.minimo() -> elemento mínimo"""
    if not self:
        return None
    try:
        return min(self)
    except TypeError:
        return None

# ============= MÉTODOS PARA CADENAS =============

def cadena_longitud(self):
    """cadena.longitud() -> entero"""
    return len(self)

def cadena_mayuscula(self):
    """cadena.mayuscula() -> nueva_cadena"""
    return self.upper()

def cadena_minuscula(self):
    """cadena.minuscula() -> nueva_cadena"""
    return self.lower()

def cadena_capitalizar(self):
    """cadena.capitalizar() -> nueva_cadena"""
    return self.capitalize() if self else ""

def cadena_titulo(self):
    """cadena.titulo() -> nueva_cadena"""
    return self.title()

def cadena_invertir(self):
    """cadena.invertir() -> nueva_cadena"""
    return self[::-1]

def cadena_contiene(self, subcadena):
    """cadena.contiene(subcadena) -> booleano"""
    return str(subcadena) in self

def cadena_indice(self, subcadena):
    """cadena.indice(subcadena) -> entero (o -1 si no existe)"""
    try:
        return self.index(str(subcadena))
    except ValueError:
        return -1

def cadena_ultimo_indice(self, subcadena):
    """cadena.ultimo_indice(subcadena) -> entero (o -1 si no existe)"""
    try:
        return self.rindex(str(subcadena))
    except ValueError:
        return -1

def cadena_empieza_con(self, prefijo):
    """cadena.empieza_con(prefijo) -> booleano"""
    return self.startswith(str(prefijo))

def cadena_termina_con(self, sufijo):
    """cadena.termina_con(sufijo) -> booleano"""
    return self.endswith(str(sufijo))

def cadena_contar(self, subcadena):
    """cadena.contar(subcadena) -> entero"""
    return self.count(str(subcadena))

def cadena_reemplazar(self, viejo, nuevo):
    """cadena.reemplazar(viejo, nuevo) -> nueva_cadena"""
    return self.replace(str(viejo), str(nuevo))

def cadena_unir(self, lista):
    """cadena.unir(lista) -> nueva_cadena (usa la cadena como separador)"""
    elementos = [str(elem) for elem in lista]
    return self.join(elementos)

def cadena_dividir(self, separador=None):
    """cadena.dividir(separador) -> lista"""
    if separador is None:
        return self.split()
    return self.split(str(separador))

def cadena_recortar(self):
    """cadena.recortar() -> nueva_cadena"""
    return self.strip()

def cadena_recortar_izquierda(self):
    """cadena.recortar_izquierda() -> nueva_cadena"""
    return self.lstrip()

def cadena_recortar_derecha(self):
    """cadena.recortar_derecha() -> nueva_cadena"""
    return self.rstrip()

def cadena_extraer(self, inicio, fin=None):
    """cadena.extraer(inicio, fin) -> nueva_cadena"""
    i = int(inicio) if hasattr(inicio, '__int__') else int(inicio)
    if fin is None:
        return self[i:]
    f = int(fin) if hasattr(fin, '__int__') else int(fin)
    return self[i:f]

def cadena_repetir(self, veces):
    """cadena.repetir(veces) -> nueva_cadena"""
    try:
        n = int(veces) if hasattr(veces, '__int__') else int(veces)
        return self * n
    except (ValueError, TypeError):
        return self

def cadena_a_entero(self):
    """cadena.a_entero() -> entero (o 0 si no puede)"""
    try:
        return int(self)
    except ValueError:
        return "0"

def cadena_a_decimal(self):
    """cadena.a_decimal() -> decimal (o 0.0 si no puede)"""
    try:
        return float(self)
    except ValueError:
        return "0.0"

def cadena_a_lista(self):
    """cadena.a_lista() -> lista_de_caracteres"""
    return list(self)

def cadena_es_numero(self):
    """cadena.es_numero() -> booleano"""
    try:
        float(self)
        return True
    except ValueError:
        return False

def cadena_es_digito(self):
    """cadena.es_digito() -> booleano"""
    return self.isdigit()

def cadena_es_alfabetico(self):
    """cadena.es_alfabetico() -> booleano"""
    return self.isalpha()

def cadena_es_vacia(self):
    """cadena.es_vacia() -> booleano"""
    return len(self) == 0

def cadena_es_palindromo(self):
    """cadena.es_palindromo() -> booleano"""
    texto_limpio = ''.join(c.lower() for c in self if c.isalnum())
    return texto_limpio == texto_limpio[::-1]

def cadena_es_mayuscula(self):
    """cadena.es_mayuscula() -> booleano"""
    return self.isupper()

def cadena_es_minuscula(self):
    """cadena.es_minuscula() -> booleano"""
    return self.islower()

def cadena_a_slug(self):
    """cadena.a_slug() -> nueva_cadena (convierte a minúsculas y reemplaza espacios por guiones)"""
    import re
    slug = self.lower()
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'[^\w\-]', '', slug)
    return slug.strip('-')

def cadena_acortar(self, longitud, sufijo="..."):
    """cadena.acortar(longitud, sufijo?) -> nueva_cadena"""
    try:
        max_len = int(longitud)
        if len(self) <= max_len:
            return self
        return self[:max_len] + sufijo
    except (ValueError, TypeError):
        return self


# ============= MÉTODOS PARA DICCIONARIOS =============

def dicc_obtener(self, clave, defecto=None):
    """dicc.obtener(clave, defecto?) -> valor o defecto"""
    return self.get(clave, defecto)

def dicc_establecer(self, clave, valor):
    """dicc.establecer(clave, valor) -> None"""
    self[clave] = valor
    return None

def dicc_eliminar(self, clave):
    """dicc.eliminar(clave) -> valor eliminado o None"""
    return self.pop(clave, None)

def dicc_contiene(self, clave):
    """dicc.contiene(clave) -> booleano"""
    return clave in self

def dicc_claves(self):
    """dicc.claves() -> lista de claves"""
    return list(self.keys())

def dicc_valores(self):
    """dicc.valores() -> lista de valores"""
    return list(self.values())

def dicc_pares(self):
    """dicc.pares() -> lista de [clave, valor]"""
    return [[k, v] for k, v in self.items()]

def dicc_longitud(self):
    """dicc.longitud() -> entero"""
    return len(self)

def dicc_vacio(self):
    """dicc.vacio() -> booleano"""
    return len(self) == 0

def dicc_limpiar(self):
    """dicc.limpiar() -> None"""
    self.clear()
    return None

def dicc_copiar(self):
    """dicc.copiar() -> nuevo_diccionario"""
    return self.copy()

def dicc_unir(self, otro):
    """dicc.unir(otro) -> None  (agrega pares del otro diccionario)"""
    if isinstance(otro, dict):
        self.update(otro)
    return None

def dicc_pop(self, clave):
    """dicc.sacar(clave) -> valor eliminado o None"""
    return self.pop(clave, None)

def dicc_tiene_clave(self, clave):
    """dicc.tiene_clave(clave) -> booleano (alias de contiene)"""
    return clave in self

def dicc_tiene_valor(self, valor):
    """dicc.tiene_valor(valor) -> booleano"""
    return valor in self.values()

def dicc_a_lista_claves(self):
    """dicc.a_lista_claves() -> lista (alias explícito de claves)"""
    return list(self.keys())

def dicc_a_lista_valores(self):
    """dicc.a_lista_valores() -> lista (alias explícito de valores)"""
    return list(self.values())

def dicc_defecto(self, clave, valor_defecto):
    """dicc.defecto(clave, valor) -> valor existente o inserta defecto y lo retorna"""
    if clave not in self:
        self[clave] = valor_defecto
    return self[clave]

def dicc_incrementar(self, clave, cantidad=1):
    """dicc.incrementar(clave, cantidad?) -> nuevo valor (útil para contadores)"""
    self[clave] = self.get(clave, 0) + cantidad
    return self[clave]

METODOS_DICCIONARIO = {
    "obtener":         dicc_obtener,
    "establecer":      dicc_establecer,
    "eliminar":        dicc_eliminar,
    "contiene":        dicc_contiene,
    "claves":          dicc_claves,
    "valores":         dicc_valores,
    "pares":           dicc_pares,
    "longitud":        dicc_longitud,
    "vacio":           dicc_vacio,
    "limpiar":         dicc_limpiar,
    "copiar":          dicc_copiar,
    "unir":            dicc_unir,
    "sacar":           dicc_pop,
    "tiene_clave":     dicc_tiene_clave,
    "tiene_valor":     dicc_tiene_valor,
    "a_lista_claves":  dicc_a_lista_claves,
    "a_lista_valores": dicc_a_lista_valores,
    "defecto":         dicc_defecto,
    "incrementar":     dicc_incrementar,
}


METODOS_CADENA = {
    "longitud": cadena_longitud,
    "mayuscula": cadena_mayuscula,
    "minuscula": cadena_minuscula,
    "capitalizar": cadena_capitalizar,
    "titulo": cadena_titulo,
    "invertir": cadena_invertir,
    "contiene": cadena_contiene,
    "indice": cadena_indice,
    "ultimo_indice": cadena_ultimo_indice,
    "empieza_con": cadena_empieza_con,
    "termina_con": cadena_termina_con,
    "contar": cadena_contar,
    "reemplazar": cadena_reemplazar,
    "unir": cadena_unir,
    "dividir": cadena_dividir,
    "recortar": cadena_recortar,
    "recortar_izquierda": cadena_recortar_izquierda,
    "recortar_derecha": cadena_recortar_derecha,
    "extraer": cadena_extraer,
    "repetir": cadena_repetir,
    "a_entero": cadena_a_entero,
    "a_decimal": cadena_a_decimal,
    "a_lista": cadena_a_lista,
    "es_numero": cadena_es_numero,
    "es_digito": cadena_es_digito,
    "es_alfabetico": cadena_es_alfabetico,
    "es_vacia": cadena_es_vacia,
    "es_palindromo": cadena_es_palindromo,
    "es_mayuscula": cadena_es_mayuscula,
    "es_minuscula": cadena_es_minuscula,
    "a_slug": cadena_a_slug,
    "acortar": cadena_acortar,
}

METODOS_LISTA = {
    "agregar": lista_agregar,
    "eliminar": lista_eliminar,
    "eliminar_en": lista_eliminar_en,
    "eliminar_ultimo": lista_eliminar_ultimo,
    "insertar": lista_insertar,
    "extender": lista_extender,
    "contiene": lista_contiene,
    "posicion": lista_posicion,
    "contar": lista_contar,
    "longitud": lista_longitud,
    "vacia": lista_vacia,
    "invertir": lista_invertir,
    "ordenar": lista_ordenar,
    "ordenar_desc": lista_ordenar_desc,
    "primero": lista_primero,
    "ultimo": lista_ultimo,
    "limpiar": lista_limpiar,
    "copiar": lista_copiar,
    "a_texto": lista_a_texto,
    "sumar": lista_sumar,
    "maximo": lista_maximo,
    "minimo": lista_minimo,
}