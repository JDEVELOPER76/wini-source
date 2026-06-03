# evaluador.py
"""Evaluación de expresiones en el intérprete wini"""

from clases import Instancia
from exepciones import *
from utilidades import es_verdadero, interpolar_cadena, contiene_interpolacion, formatear_texto


class Evaluador:
    """Encapsula la lógica de evaluación de expresiones"""
    
    def __init__(self, interprete):
        self.interprete = interprete
    
    def evaluar_fragmento(self, codigo):
        """Evalúa un fragmento de código (usado para interpolación)"""
        from lexer import lexer
        from parser import Parser
        
        tokens_fragmento = lexer(codigo)
        parser_fragmento = Parser(tokens_fragmento)
        ast_fragmento = parser_fragmento.parse()
        if not ast_fragmento.hijos:
            return ""
        return self.evaluar(ast_fragmento.hijos[0])
    
    def evaluar(self, nodo):
        """Evalúa un nodo del AST y retorna su valor"""
        
        if nodo.tipo == "ENTERO":
            return int(nodo.valor)
        
        elif nodo.tipo == "DECIMAL":
            return float(nodo.valor)
        
        elif nodo.tipo == "NINGUNO":
            return None
        
        elif nodo.tipo == "CADENA_TEXTO":
            texto = str(nodo.valor)
            return texto

        elif nodo.tipo == "CADENA_INTERPOLADA":
            return interpolar_cadena(nodo.valor, self.evaluar_fragmento)
        
        elif nodo.tipo == "BOOLEANO":
            return nodo.valor
        
        elif nodo.tipo == "LISTA":
            elementos = [self.evaluar(elem) for elem in nodo.hijos]
            return elementos
        
        elif nodo.tipo == "DICCIONARIO":
            resultado = {}
            for par in nodo.hijos:
                clave = self.evaluar(par.hijos[0])
                valor = self.evaluar(par.hijos[1])
                resultado[clave] = valor
            return resultado
        
        elif nodo.tipo == "INDEXACION":
            if nodo.valor not in self.interprete.variables:
                raise RuntimeError(f"Variable '{nodo.valor}' no definida", linea=nodo.linea)
            objeto = self.interprete.variables[nodo.valor]
            indice = self.evaluar(nodo.hijos[0])
            if isinstance(objeto, list):
                if not isinstance(indice, int):
                    raise RuntimeError("Índice de lista debe ser entero", linea=nodo.linea)
                if indice < 0 or indice >= len(objeto):
                    raise RuntimeError(f"Índice {indice} fuera de rango para lista de tamaño {len(objeto)}", linea=nodo.linea)
                return objeto[indice]
            elif isinstance(objeto, dict):
                return objeto[indice]
            else:
                raise RuntimeError(f"'{nodo.valor}' no es una lista ni un diccionario", linea=nodo.linea)
        
        elif nodo.tipo == "ACCESO_ATRIBUTO":
            objeto_nombre = nodo.valor
            atributo_nombre = nodo.hijos[0].valor
            
            # Verificar si es un módulo
            if objeto_nombre in self.interprete.variables:
                objeto = self.interprete.variables[objeto_nombre]
                
                # Si es un módulo
                if isinstance(objeto, dict) and objeto.get("_tipo") == "modulo":
                    # Buscar en funciones del módulo
                    if atributo_nombre in objeto.get("funciones", {}):
                        return objeto["funciones"][atributo_nombre]
                    # Buscar en clases del módulo
                    if atributo_nombre in objeto.get("clases", {}):
                        return objeto["clases"][atributo_nombre]
                    # Buscar en variables del módulo
                    if atributo_nombre in objeto.get("variables", {}):
                        return objeto["variables"][atributo_nombre]
                    raise RuntimeError(f"Módulo '{objeto_nombre}' no tiene '{atributo_nombre}'", linea=nodo.linea)
                
                # Para instancias normales
                if isinstance(objeto, Instancia):
                    return objeto.obtener_atributo(atributo_nombre)
            
            if objeto_nombre == "yo" and self.interprete.yo:
                return self.interprete.yo.obtener_atributo(atributo_nombre)
            
            raise RuntimeError(f"'{objeto_nombre}' no tiene atributo '{atributo_nombre}'", linea=nodo.linea)
        
        elif nodo.tipo == "LLAMADA":
            return self.interprete.ejecutor.ejecutar_funcion(nodo)
        
        elif nodo.tipo == "LLAMADA_METODO":
            return self.interprete.ejecutor.ejecutar_metodo(nodo)
        
        elif nodo.tipo == "IDENTIFICADOR":
            if nodo.valor in self.interprete.variables:
                return self.interprete.variables[nodo.valor]
            raise RuntimeError(f"Variable '{nodo.valor}' no definida", linea=nodo.linea)
        
        elif nodo.tipo == "BINARIA":
            return self._evaluar_binaria(nodo)
        
        elif nodo.tipo == "LOGICO":
            return self._evaluar_logica(nodo)

        elif nodo.tipo == "IN":
            izquierda = self.evaluar(nodo.hijos[0])
            derecha = self.evaluar(nodo.hijos[1])
            if isinstance(derecha, list):
                return izquierda in derecha
            elif isinstance(derecha, str):
                return str(izquierda) in derecha
            else:
                raise RuntimeError(f"Operador 'in' no soportado entre {type(izquierda)} y {type(derecha)}", linea=nodo.linea)
        
        return None
    
    def _evaluar_binaria(self, nodo):
        """Evalúa operaciones binarias con manejo de errores"""
        try:
            izq = self.evaluar(nodo.hijos[0])
            der = self.evaluar(nodo.hijos[1])
            op = nodo.valor
        except Exception as e:
            raise RuntimeError(f"Error al evaluar operandos: {e}", linea=nodo.linea)
        
        try:
            if op == "+":
                if isinstance(izq, str) or isinstance(der, str):
                    return str(izq) + str(der)
                return izq + der
            elif op == "-":
                return izq - der
            elif op == "*":
                return izq * der
            elif op == "/":
                if der == 0:
                    raise ErrorMatematico("División por cero", linea=nodo.linea)
                return izq / der
            elif op == "%":
                if der == 0:
                    raise ErrorMatematico("Módulo por cero", linea=nodo.linea)
                return izq % der
            elif op == "==":
                return izq == der
            elif op == "!=":
                return izq != der
            elif op == "<>":
                return izq != der
            elif op == "<":
                return izq < der
            elif op == ">":
                return izq > der
            elif op == "<=":
                return izq <= der
            elif op == ">=":
                return izq >= der
            else:
                raise RuntimeError(f"Operador binario desconocido: {op}", linea=nodo.linea)
        
        except ErrorMatematico:
            raise
        except TypeError as e:
            raise ErrorTipo(f"No se puede aplicar operador '{op}' entre {type(izq).__name__} y {type(der).__name__}", linea=nodo.linea)
        except ZeroDivisionError:
            raise ErrorMatematico("División por cero", linea=nodo.linea)
        except Exception as e:
            raise RuntimeError(f"Error en operación {op}: {e}", linea=nodo.linea)
    
    def _evaluar_logica(self, nodo):
        """Evalúa operaciones lógicas"""
        op = nodo.valor
        if op in ("no",):
            valor = self.evaluar(nodo.hijos[0])
            return not es_verdadero(valor)
        elif op in ("y",):
            izquierda = self.evaluar(nodo.hijos[0])
            if not es_verdadero(izquierda):
                return False
            derecha = self.evaluar(nodo.hijos[1])
            return es_verdadero(derecha)
        elif op in ("o",):
            izquierda = self.evaluar(nodo.hijos[0])
            if es_verdadero(izquierda):
                return True
            derecha = self.evaluar(nodo.hijos[1])
            return es_verdadero(derecha)
        else:
            raise RuntimeError(f"Operador lógico desconocido: {op}", linea=nodo.linea)
