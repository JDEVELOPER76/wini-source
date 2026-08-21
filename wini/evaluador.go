package wini

import (
	"fmt"
	"strconv"
	"strings"
)

// Evaluador encapsula la lógica de evaluación de expresiones
type Evaluador struct {
	interprete *Interprete // Referencia al intérprete principal
	dispatch   map[string]func(*Nodo) interface{}
}

// NewEvaluador crea un nuevo evaluador
func NewEvaluador(interprete *Interprete) *Evaluador {
	e := &Evaluador{
		interprete: interprete,
		dispatch:   make(map[string]func(*Nodo) interface{}),
	}
	e.initDispatch()
	return e
}

// initDispatch inicializa el mapa de despacho
func (e *Evaluador) initDispatch() {
	e.dispatch["ENTERO"] = e.evEntero
	e.dispatch["DECIMAL"] = e.evDecimal
	e.dispatch["NINGUNO"] = e.evNinguno
	e.dispatch["CADENA_TEXTO"] = e.evCadenaTexto
	e.dispatch["CADENA_INTERPOLADA"] = e.evCadenaInterpolada
	e.dispatch["BOOLEANO"] = e.evBooleano
	e.dispatch["LISTA"] = e.evLista
	e.dispatch["DICCIONARIO"] = e.evDiccionario
	e.dispatch["ACCESO_ATRIBUTO"] = e.evAccesoAtributo
	e.dispatch["LLAMADA"] = e.evLlamada
	e.dispatch["INDEXACION"] = e.evIndexacion
	e.dispatch["LLAMADA_METODO"] = e.evLlamadaMetodo
	e.dispatch["IDENTIFICADOR"] = e.evIdentificador
	e.dispatch["BINARIA"] = e.evaluarBinaria
	e.dispatch["UNARIA"] = e.evUnaria
	e.dispatch["LOGICO"] = e.evaluarLogica
	e.dispatch["IN"] = e.evIn
}

// Evaluar evalúa un nodo del AST y retorna su valor
func (e *Evaluador) Evaluar(nodo *Nodo) interface{} {
	if nodo == nil {
		return nil
	}

	manejador, ok := e.dispatch[nodo.Tipo]
	if !ok {
		return nil
	}
	return manejador(nodo)
}

// FormatearTexto convierte valores a texto para escribir e interpolación
func FormatearTexto(valor interface{}) string {
	if valor == nil {
		return "nulo"
	}

	switch v := valor.(type) {
	case bool:
		if v {
			return "verdadero"
		}
		return "falso"
	case string:
		return v
	case []interface{}:
		elementos := make([]string, len(v))
		for i, elem := range v {
			elementos[i] = FormatearTexto(elem)
		}
		return "[" + strings.Join(elementos, ", ") + "]"
	case map[string]interface{}:
		pares := make([]string, 0, len(v))
		for k, val := range v {
			pares = append(pares, fmt.Sprintf("%s: %s", FormatearTexto(k), FormatearTexto(val)))
		}
		return "{" + strings.Join(pares, ", ") + "}"
	case int, int64, float64:
		return fmt.Sprintf("%v", v)
	default:
		return fmt.Sprintf("%v", v)
	}
}

// EsVerdadero convierte cualquier valor a booleano según reglas típicas
func EsVerdadero(valor interface{}) bool {
	if valor == nil {
		return false
	}

	switch v := valor.(type) {
	case bool:
		return v
	case int:
		return v != 0
	case int64:
		return v != 0
	case float64:
		return v != 0
	case string:
		return len(v) > 0
	case []interface{}:
		return len(v) > 0
	case map[string]interface{}:
		return len(v) > 0
	default:
		return true
	}
}

// ContieneInterpolacion verifica si un texto contiene interpolaciones {}
func ContieneInterpolacion(texto string) bool {
	return strings.Contains(texto, "{") && strings.Contains(texto, "}")
}

// InterpolarCadena interpola variables en una cadena de texto
func (e *Evaluador) InterpolarCadena(texto string, evaluarFragmentoFunc func(string) interface{}) string {
	var resultado strings.Builder
	indice := 0

	for indice < len(texto) {
		caracter := texto[indice]
		if caracter == '{' {
			cierre := strings.Index(texto[indice+1:], "}")
			if cierre == -1 {
				linea := 0
				panic(&RuntimeError{
					ErrorConLinea: ErrorConLinea{
						Mensaje: "Cadena interpolada sin cerrar: falta '}'",
						Linea:   &linea,
					},
				})
			}
			cierre += indice + 1
			expresion := strings.TrimSpace(texto[indice+1 : cierre])
			if expresion == "" {
				linea := 0
				panic(&RuntimeError{
					ErrorConLinea: ErrorConLinea{
						Mensaje: "Interpolación vacía dentro de '{}'",
						Linea:   &linea,
					},
				})
			}
			valor := evaluarFragmentoFunc(expresion)
			resultado.WriteString(FormatearTexto(valor))
			indice = cierre + 1
		} else {
			resultado.WriteByte(caracter)
			indice++
		}
	}
	return resultado.String()
}

// EvaluarFragmento evalúa un fragmento de código (usado para interpolación)
func (e *Evaluador) EvaluarFragmento(codigo string) interface{} {
	lexer := NewLexer()
	tokens := lexer.Tokenize(codigo)
	parser := NewParser(tokens)
	ast := parser.Parse()
	if ast == nil || len(ast.Hijos) == 0 {
		return ""
	}
	return e.Evaluar(ast.Hijos[0])
}

// ========== Manejadores por tipo de nodo ==========

func (e *Evaluador) evEntero(nodo *Nodo) interface{} {
	val, _ := strconv.Atoi(nodo.Valor.(string))
	return val
}

func (e *Evaluador) evDecimal(nodo *Nodo) interface{} {
	val, _ := strconv.ParseFloat(nodo.Valor.(string), 64)
	return val
}

func (e *Evaluador) evNinguno(nodo *Nodo) interface{} {
	return nil
}

func (e *Evaluador) evCadenaTexto(nodo *Nodo) interface{} {
	return e.procesarEscapes(nodo.Valor.(string))
}

func (e *Evaluador) evCadenaInterpolada(nodo *Nodo) interface{} {
	textoProcesado := e.procesarEscapes(nodo.Valor.(string))
	return e.InterpolarCadena(textoProcesado, e.EvaluarFragmento)
}

func (e *Evaluador) evBooleano(nodo *Nodo) interface{} {
	return nodo.Valor
}

func (e *Evaluador) evLista(nodo *Nodo) interface{} {
	resultado := make([]interface{}, len(nodo.Hijos))
	for i, elem := range nodo.Hijos {
		resultado[i] = e.Evaluar(elem)
	}
	return resultado
}

func (e *Evaluador) evDiccionario(nodo *Nodo) interface{} {
	resultado := make(map[string]interface{})
	for _, par := range nodo.Hijos {
		if len(par.Hijos) >= 2 {
			clave := e.Evaluar(par.Hijos[0])
			valor := e.Evaluar(par.Hijos[1])
			// Convertir clave a string para usar como key en el mapa
			resultado[FormatearTexto(clave)] = valor
		}
	}
	return resultado
}

func (e *Evaluador) evAccesoAtributo(nodo *Nodo) interface{} {
	atributoNombre := nodo.Valor.(string)
	objeto := e.Evaluar(nodo.Hijos[0])

	if mapa, ok := objeto.(map[string]interface{}); ok {
		if valor, ok := mapa[atributoNombre]; ok {
			return valor
		}

		if tipo, ok := mapa["_tipo"].(string); ok && tipo == "modulo" {
			if funciones, ok := mapa["funciones"].(map[string]interface{}); ok {
				if fn, ok := funciones[atributoNombre]; ok {
					return fn
				}
			}
			if variables, ok := mapa["variables"].(map[string]interface{}); ok {
				if val, ok := variables[atributoNombre]; ok {
					return val
				}
			}
			linea := 0
			panic(&RuntimeError{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("Módulo no tiene '%s'", atributoNombre),
					Linea:   &linea,
				},
			})
		}
	}

	linea := 0
	panic(&RuntimeError{
		ErrorConLinea: ErrorConLinea{
			Mensaje: fmt.Sprintf("El valor de tipo '%T' no tiene atributo '%s'", objeto, atributoNombre),
			Linea:   &linea,
		},
	})
}

func (e *Evaluador) evLlamada(nodo *Nodo) interface{} {
	return e.interprete.Ejecutor.EjecutarFuncion(nodo)
}

func (e *Evaluador) evIndexacion(nodo *Nodo) interface{} {
	objeto := e.Evaluar(nodo.Hijos[0])
	indice := e.Evaluar(nodo.Hijos[1])
	linea := nodo.Linea

	switch obj := objeto.(type) {
	case []interface{}:
		idx, ok := indice.(int)
		if !ok {
			panic(&ErrorTipo{
				ErrorConLinea: ErrorConLinea{
					Mensaje: "Índice de lista debe ser entero",
					Linea:   &linea,
				},
			})
		}
		if idx < 0 || idx >= len(obj) {
			panic(&ErrorIndice{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("Índice %d fuera de rango para lista de tamaño %d", idx, len(obj)),
					Linea:   &linea,
				},
			})
		}
		return obj[idx]

	case map[string]interface{}:
		clave := FormatearTexto(indice)
		if val, ok := obj[clave]; ok {
			return val
		}
		panic(&ErrorIndice{
			ErrorConLinea: ErrorConLinea{
				Mensaje: fmt.Sprintf("Clave '%s' no encontrada en el diccionario", clave),
				Linea:   &linea,
			},
		})

	case string:
		idx, ok := indice.(int)
		if !ok {
			panic(&ErrorTipo{
				ErrorConLinea: ErrorConLinea{
					Mensaje: "Índice de cadena debe ser entero",
					Linea:   &linea,
				},
			})
		}
		if idx < 0 || idx >= len(obj) {
			panic(&ErrorIndice{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("Índice %d fuera de rango para cadena de tamaño %d", idx, len(obj)),
					Linea:   &linea,
				},
			})
		}
		return string(obj[idx])

	default:
		panic(&ErrorTipo{
			ErrorConLinea: ErrorConLinea{
				Mensaje: fmt.Sprintf("No se puede indexar sobre tipo %T", objeto),
				Linea:   &linea,
			},
		})
	}
}

func (e *Evaluador) evLlamadaMetodo(nodo *Nodo) interface{} {
	return e.interprete.Ejecutor.EjecutarMetodo(nodo)
}

func (e *Evaluador) evIdentificador(nodo *Nodo) interface{} {
	if val, ok := e.interprete.Variables[nodo.Valor.(string)]; ok {
		return val
	}
	linea := nodo.Linea
	panic(&RuntimeError{
		ErrorConLinea: ErrorConLinea{
			Mensaje: fmt.Sprintf("Variable '%s' no definida", nodo.Valor),
			Linea:   &linea,
		},
	})
}

func (e *Evaluador) evUnaria(nodo *Nodo) interface{} {
	valor := e.Evaluar(nodo.Hijos[0])
	linea := nodo.Linea

	switch v := valor.(type) {
	case int:
		return -v
	case int64:
		return -v
	case float64:
		return -v
	default:
		panic(&ErrorTipo{
			ErrorConLinea: ErrorConLinea{
				Mensaje: fmt.Sprintf("No se puede aplicar '-' unario sobre tipo %T", valor),
				Linea:   &linea,
			},
		})
	}
}

func (e *Evaluador) evIn(nodo *Nodo) interface{} {
	izquierda := e.Evaluar(nodo.Hijos[0])
	derecha := e.Evaluar(nodo.Hijos[1])
	linea := nodo.Linea

	switch d := derecha.(type) {
	case []interface{}:
		for _, elem := range d {
			if elem == izquierda {
				return true
			}
		}
		return false
	case string:
		return strings.Contains(d, FormatearTexto(izquierda))
	default:
		panic(&RuntimeError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: fmt.Sprintf("Operador 'in' no soportado entre %T y %T", izquierda, derecha),
				Linea:   &linea,
			},
		})
	}
}

func (e *Evaluador) evaluarBinaria(nodo *Nodo) interface{} {
	linea := nodo.Linea

	var izq, der interface{}
	var err error

	// Evaluar operandos con recuperación de pánico
	func() {
		defer func() {
			if r := recover(); r != nil {
				if e, ok := r.(error); ok {
					err = e
				} else {
					err = fmt.Errorf("%v", r)
				}
			}
		}()
		izq = e.Evaluar(nodo.Hijos[0])
		der = e.Evaluar(nodo.Hijos[1])
	}()

	if err != nil {
		panic(&RuntimeError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: fmt.Sprintf("Error al evaluar operandos: %v", err),
				Linea:   &linea,
			},
		})
	}

	op := nodo.Valor

	// Función auxiliar para manejar pánicos en operaciones
	defer func() {
		if r := recover(); r != nil {
			if _, ok := r.(*ErrorMatematico); ok {
				panic(r)
			}
			if _, ok := r.(*ErrorTipo); ok {
				panic(r)
			}
			panic(&RuntimeError{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("Error en operación %s: %v", op, r),
					Linea:   &linea,
				},
			})
		}
	}()

	// Convertir tipos para operaciones numéricas
	izqFloat, izqIsFloat := toFloat64(izq)
	derFloat, derIsFloat := toFloat64(der)
	izqInt, _ := toInt64(izq)
	derInt, _ := toInt64(der)

	switch op {
	case "+":
		// Concatenación de strings
		if _, ok := izq.(string); ok {
			return fmt.Sprintf("%v%v", izq, der)
		}
		if _, ok := der.(string); ok {
			return fmt.Sprintf("%v%v", izq, der)
		}
		// Suma numérica
		if izqIsFloat || derIsFloat {
			return izqFloat + derFloat
		}
		return int(izqInt + derInt)

	case "-":
		if izqIsFloat || derIsFloat {
			return izqFloat - derFloat
		}
		return int(izqInt - derInt)

	case "*":
		if izqIsFloat || derIsFloat {
			return izqFloat * derFloat
		}
		return int(izqInt * derInt)

	case "/":
		if derIsFloat && derFloat == 0 {
			panic(&ErrorMatematico{
				ErrorConLinea: ErrorConLinea{
					Mensaje: "División por cero",
					Linea:   &linea,
				},
			})
		}
		if !derIsFloat && derInt == 0 {
			panic(&ErrorMatematico{
				ErrorConLinea: ErrorConLinea{
					Mensaje: "División por cero",
					Linea:   &linea,
				},
			})
		}
		if izqIsFloat || derIsFloat {
			return izqFloat / derFloat
		}
		return float64(izqInt) / float64(derInt)

	case "%":
		if derInt == 0 {
			panic(&ErrorMatematico{
				ErrorConLinea: ErrorConLinea{
					Mensaje: "Módulo por cero",
					Linea:   &linea,
				},
			})
		}
		if izqIsFloat || derIsFloat {
			return int(izqFloat) % int(derFloat)
		}
		return int(izqInt % derInt)

	case "==":
		return valoresIguales(izq, der)
	case "!=", "<>":
		return !valoresIguales(izq, der)
	case "<":
		if izqIsFloat || derIsFloat {
			return izqFloat < derFloat
		}
		return izqInt < derInt
	case ">":
		if izqIsFloat || derIsFloat {
			return izqFloat > derFloat
		}
		return izqInt > derInt
	case "<=":
		if izqIsFloat || derIsFloat {
			return izqFloat <= derFloat
		}
		return izqInt <= derInt
	case ">=":
		if izqIsFloat || derIsFloat {
			return izqFloat >= derFloat
		}
		return izqInt >= derInt

	default:
		panic(&RuntimeError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: fmt.Sprintf("Operador binario desconocido: %s", op),
				Linea:   &linea,
			},
		})
	}
}

func (e *Evaluador) evaluarLogica(nodo *Nodo) interface{} {
	op := nodo.Valor
	linea := nodo.Linea

	switch op {
	case "no":
		valor := e.Evaluar(nodo.Hijos[0])
		return !EsVerdadero(valor)

	case "y":
		izquierda := e.Evaluar(nodo.Hijos[0])
		if !EsVerdadero(izquierda) {
			return false
		}
		derecha := e.Evaluar(nodo.Hijos[1])
		return EsVerdadero(derecha)

	case "o":
		izquierda := e.Evaluar(nodo.Hijos[0])
		if EsVerdadero(izquierda) {
			return true
		}
		derecha := e.Evaluar(nodo.Hijos[1])
		return EsVerdadero(derecha)

	default:
		panic(&RuntimeError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: fmt.Sprintf("Operador lógico desconocido: %s", op),
				Linea:   &linea,
			},
		})
	}
}

func (e *Evaluador) procesarEscapes(texto string) string {
	escapes := map[string]string{
		"\\n":  "\n",
		"\\t":  "\t",
		"\\r":  "\r",
		"\\\\": "\\",
		"\\\"": "\"",
		"\\'":  "'",
	}

	var resultado strings.Builder
	i := 0
	for i < len(texto) {
		if texto[i] == '\\' && i+1 < len(texto) {
			escape := texto[i : i+2]
			if val, ok := escapes[escape]; ok {
				resultado.WriteString(val)
				i += 2
				continue
			}
		}
		resultado.WriteByte(texto[i])
		i++
	}
	return resultado.String()
}

// ========== Funciones auxiliares ==========

func toFloat64(val interface{}) (float64, bool) {
	switch v := val.(type) {
	case int:
		return float64(v), true
	case int64:
		return float64(v), true
	case float64:
		return v, true
	default:
		return 0, false
	}
}

func toInt64(val interface{}) (int64, bool) {
	switch v := val.(type) {
	case int:
		return int64(v), true
	case int64:
		return v, true
	case float64:
		return int64(v), true
	default:
		return 0, false
	}
}

// valoresIguales compara dos valores para '==' tratando los números de forma
// coherente sin importar si son int, int64 o float64 internamente
func valoresIguales(a, b interface{}) bool {
	aFloat, aEsNum := toFloat64(a)
	bFloat, bEsNum := toFloat64(b)
	if aEsNum && bEsNum {
		return aFloat == bFloat
	}
	return a == b
}
