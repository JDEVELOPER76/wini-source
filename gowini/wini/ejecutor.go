package wini

import (
	"bufio"
	"fmt"
	"os"
	"reflect"
	"strconv"
	"strings"
)

// Sentinela para indicar que no se encontró un método nativo
var SENTINEL = struct{}{}

// metodosListaMutantes son los métodos de lista cuyo resultado debe
// reescribirse en la variable original, ya que en Wini se comportan
// como mutaciones en sitio (al estilo Python), no como devolver una copia
var metodosListaMutantes = map[string]bool{
	"agregar":         true,
	"eliminar":        true,
	"eliminar_en":     true,
	"eliminar_ultimo": true,
	"insertar":        true,
	"extender":        true,
	"invertir":        true,
	"ordenar":         true,
	"ordenar_desc":    true,
	"limpiar":         true,
}

// Ejecutor encapsula la lógica de ejecución de funciones y métodos
type Ejecutor struct {
	interprete *Interprete
}

// NewEjecutor crea un nuevo ejecutor
func NewEjecutor(interprete *Interprete) *Ejecutor {
	return &Ejecutor{
		interprete: interprete,
	}
}

// NormalizarRetorno convierte retornos Python básicos al formato esperado por Wini
func (e *Ejecutor) NormalizarRetorno(valor interface{}) interface{} {
	return valor
}

// AplicarScopeFuncion aplica un scope temporal aislado para la ejecución de
// una función, a diferencia de AplicarScopeTemporal (usado en bloques
// capturar/finalmente, donde las variables nuevas SÍ deben persistir tras el
// bloque). Aquí se toma una foto completa del estado de variables antes de
// aplicar 'cambios' (parámetros + variables del módulo), y al terminar la
// función se restaura ese estado exacto: cualquier variable local creada
// dentro del cuerpo de la función (p. ej. "espacios = ..." en una función
// recursiva) se descarta, en vez de sobrescribir la misma variable en
// llamadas anidadas o filtrarse hacia quien llamó a la función.
func (e *Ejecutor) AplicarScopeFuncion(cambios map[string]interface{}) func() {
	variables := e.interprete.Variables

	snapshot := make(map[string]interface{}, len(variables))
	for k, v := range variables {
		snapshot[k] = v
	}

	for k, v := range cambios {
		variables[k] = v
	}

	return func() {
		for k := range variables {
			if _, existiaAntes := snapshot[k]; !existiaAntes {
				delete(variables, k)
			}
		}
		for k, v := range snapshot {
			variables[k] = v
		}
	}
}

// AplicarScopeTemporal aplica cambios temporales al scope de variables
func (e *Ejecutor) AplicarScopeTemporal(cambios map[string]interface{}) func() {
	variables := e.interprete.Variables
	guardado := make(map[string]interface{})

	for k, v := range cambios {
		if _, ok := guardado[k]; !ok {
			if val, ok := variables[k]; ok {
				guardado[k] = val
			} else {
				guardado[k] = nil // marca como no existente
			}
		}
		variables[k] = v
	}

	return func() {
		for k, v := range guardado {
			if v == nil {
				delete(variables, k)
			} else {
				variables[k] = v
			}
		}
	}
}

// AplicarFuncionesTemporal aplica cambios temporales al mapa de funciones
// del intérprete, igual que AplicarScopeTemporal pero para funciones. Esto
// permite que, durante la ejecución de una función de un módulo, las demás
// funciones de ese mismo módulo puedan llamarse por su nombre simple.
func (e *Ejecutor) AplicarFuncionesTemporal(cambios map[string]interface{}) func() {
	funciones := e.interprete.Funciones
	guardado := make(map[string]interface{})

	for k, v := range cambios {
		if _, ok := guardado[k]; !ok {
			if val, ok := funciones[k]; ok {
				guardado[k] = val
			} else {
				guardado[k] = nil // marca como no existente
			}
		}
		funciones[k] = v
	}

	return func() {
		for k, v := range guardado {
			if v == nil {
				delete(funciones, k)
			} else {
				funciones[k] = v
			}
		}
	}
}

// EjecutarMetodoNativo ejecuta un método nativo sobre un objeto básico
func (e *Ejecutor) EjecutarMetodoNativo(objeto interface{}, metodoNombre string, argumentos []interface{}, nombrados map[string]interface{}, nodo *Nodo) interface{} {
	if nombrados == nil {
		nombrados = make(map[string]interface{})
	}

	// Métodos de lista
	if lista, ok := objeto.([]interface{}); ok {
		if metodo, ok := MetodosLista[metodoNombre]; ok {
			resultado, err := metodo(lista, argumentos, nombrados)
			if err != nil {
				linea := 0
				if nodo != nil {
					linea = nodo.Linea
				}
				panic(&RuntimeError{
					ErrorConLinea: ErrorConLinea{
						Mensaje: fmt.Sprintf("Error al ejecutar método nativo '%s' en lista: %v", metodoNombre, err),
						Linea:   &linea,
					},
				})
			}
			return resultado
		}
	}

	// Métodos de cadena
	if cadena, ok := objeto.(string); ok {
		if metodo, ok := MetodosCadena[metodoNombre]; ok {
			resultado, err := metodo(cadena, argumentos, nombrados)
			if err != nil {
				linea := 0
				if nodo != nil {
					linea = nodo.Linea
				}
				panic(&RuntimeError{
					ErrorConLinea: ErrorConLinea{
						Mensaje: fmt.Sprintf("Error al ejecutar método nativo '%s' en cadena: %v", metodoNombre, err),
						Linea:   &linea,
					},
				})
			}
			return resultado
		}
	}

	// Métodos de diccionario (excluir módulos)
	if mapa, ok := objeto.(map[string]interface{}); ok {
		// Verificar que no sea un módulo
		if tipo, ok := mapa["_tipo"]; !ok || tipo != "modulo" {
			if metodo, ok := MetodosDiccionario[metodoNombre]; ok {
				resultado, err := metodo(mapa, argumentos, nombrados)
				if err != nil {
					linea := 0
					if nodo != nil {
						linea = nodo.Linea
					}
					panic(&RuntimeError{
						ErrorConLinea: ErrorConLinea{
							Mensaje: fmt.Sprintf("Error al ejecutar método nativo '%s' en diccionario: %v", metodoNombre, err),
							Linea:   &linea,
						},
					})
				}
				return resultado
			}
		}
	}

	// Métodos para booleanos
	if booleano, ok := objeto.(bool); ok {
		if metodo, ok := MetodosBooleano[metodoNombre]; ok {
			resultado, err := metodo(booleano, argumentos, nombrados)
			if err != nil {
				linea := 0
				if nodo != nil {
					linea = nodo.Linea
				}
				panic(&RuntimeError{
					ErrorConLinea: ErrorConLinea{
						Mensaje: fmt.Sprintf("Error al ejecutar método nativo '%s' en booleano: %v", metodoNombre, err),
						Linea:   &linea,
					},
				})
			}
			return resultado
		}
	}

	// Métodos para números (int y float64)
	switch objeto.(type) {
	case int, float64:
		if metodo, ok := MetodosNumero[metodoNombre]; ok {
			resultado, err := metodo(objeto, argumentos, nombrados)
			if err != nil {
				linea := 0
				if nodo != nil {
					linea = nodo.Linea
				}
				panic(&RuntimeError{
					ErrorConLinea: ErrorConLinea{
						Mensaje: fmt.Sprintf("Error al ejecutar método nativo '%s' en número: %v", metodoNombre, err),
						Linea:   &linea,
					},
				})
			}
			return resultado
		}
	}

	return SENTINEL
}

// EvaluarArgumentos evalúa los nodos de una lista de argumentos
func (e *Ejecutor) EvaluarArgumentos(nodos []*Nodo) ([]interface{}, map[string]interface{}) {
	posicionales := []interface{}{}
	nombrados := make(map[string]interface{})

	for _, nodoArg := range nodos {
		if nodoArg.Tipo == "ARG_NOMBRADO" {
			nombreArg := nodoArg.Valor.(string)
			if _, ok := nombrados[nombreArg]; ok {
				panic(&RuntimeError{
					ErrorConLinea: ErrorConLinea{
						Mensaje: fmt.Sprintf("El argumento con nombre '%s' está repetido en la llamada", nombreArg),
						Linea:   &nodoArg.Linea,
					},
				})
			}
			nombrados[nombreArg] = e.interprete.Evaluador.Evaluar(nodoArg.Hijos[0])
		} else {
			posicionales = append(posicionales, e.interprete.Evaluador.Evaluar(nodoArg))
		}
	}

	return posicionales, nombrados
}

// VincularParametros empareja argumentos con parámetros. predeterminados
// contiene, por posición, el nodo de expresión del valor por defecto de
// cada parámetro (o nil si el parámetro no tiene uno); puede pasarse como
// nil si ningún parámetro tiene valores por defecto.
func (e *Ejecutor) VincularParametros(parametros []string, predeterminados []*Nodo, posicionales []interface{}, nombrados map[string]interface{}, nodo *Nodo, contexto string) []interface{} {
	if len(posicionales) > len(parametros) {
		panic(&RuntimeError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: fmt.Sprintf("%s espera como máximo %d argumentos, pero recibió %d posicionales", contexto, len(parametros), len(posicionales)),
				Linea:   &nodo.Linea,
			},
		})
	}

	valores := make(map[string]interface{})
	for i, nombreParam := range parametros {
		if i < len(posicionales) {
			valores[nombreParam] = posicionales[i]
		}
	}

	for nombreArg, valor := range nombrados {
		found := false
		for _, p := range parametros {
			if p == nombreArg {
				found = true
				break
			}
		}
		if !found {
			panic(&RuntimeError{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("%s no tiene un parámetro llamado '%s'", contexto, nombreArg),
					Linea:   &nodo.Linea,
				},
			})
		}
		if _, ok := valores[nombreArg]; ok {
			panic(&RuntimeError{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("El parámetro '%s' recibió un valor posicional y con nombre a la vez", nombreArg),
					Linea:   &nodo.Linea,
				},
			})
		}
		valores[nombreArg] = valor
	}

	resultado := make([]interface{}, len(parametros))
	for i, p := range parametros {
		if val, ok := valores[p]; ok {
			resultado[i] = val
			continue
		}
		// No se proporcionó el argumento: usar el valor por defecto si existe
		if predeterminados != nil && i < len(predeterminados) && predeterminados[i] != nil {
			resultado[i] = e.interprete.Evaluador.Evaluar(predeterminados[i])
			continue
		}
		resultado[i] = nil
	}

	return resultado
}

// EjecutarFuncion ejecuta una llamada a función
func (e *Ejecutor) EjecutarFuncion(nodo *Nodo) interface{} {
	nombre := nodo.Valor.(string)
	posicionales, nombrados := e.EvaluarArgumentos(nodo.Hijos)

	// Llamada a función definida por el usuario o función nativa Go registrada
	if funcionRaw, ok := e.interprete.Funciones[nombre]; ok {
		switch funcion := funcionRaw.(type) {
		case map[string]interface{}:
			return e.EjecutarFuncionUsuario(nombre, posicionales, nombrados, nodo, funcion)
		case func(...interface{}) interface{}:
			if len(nombrados) > 0 {
				panic(&RuntimeError{
					ErrorConLinea: ErrorConLinea{
						Mensaje: fmt.Sprintf("La función nativa '%s' no admite argumentos con nombre", nombre),
						Linea:   &nodo.Linea,
					},
				})
			}
			return e.NormalizarRetorno(funcion(posicionales...))
		}
	}

	// Funciones nativas (no admiten argumentos con nombre)
	if len(nombrados) > 0 {
		panic(&RuntimeError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: fmt.Sprintf("La función nativa '%s' no admite argumentos con nombre", nombre),
				Linea:   &nodo.Linea,
			},
		})
	}
	return e.EjecutarFuncionNativa(nombre, posicionales, nodo)
}

// EjecutarFuncionUsuario ejecuta una función definida por el usuario
func (e *Ejecutor) EjecutarFuncionUsuario(nombre string, posicionales []interface{}, nombrados map[string]interface{}, nodo *Nodo, funcionDef map[string]interface{}) interface{} {
	return e.EjecutarFuncionWini(funcionDef, posicionales, nodo, nombre, nombrados)
}

// EjecutarFuncionWini ejecuta una función Wini dada su definición
func (e *Ejecutor) EjecutarFuncionWini(funcionDef map[string]interface{}, posicionales []interface{}, nodo *Nodo, nombre string, nombrados map[string]interface{}) interface{} {
	if nombrados == nil {
		nombrados = make(map[string]interface{})
	}

	// Si es una función nativa Go (callable)
	if fn, ok := funcionDef["_callable"]; ok {
		if f, ok := fn.(func([]interface{}, map[string]interface{}) interface{}); ok {
			return e.NormalizarRetorno(f(posicionales, nombrados))
		}
	}

	// Si es una función definida en Wini (diccionario)
	parametrosInterfaz := funcionDef["parametros"]
	var parametros []string
	if p, ok := parametrosInterfaz.([]string); ok {
		parametros = p
	} else if p, ok := parametrosInterfaz.([]interface{}); ok {
		parametros = make([]string, len(p))
		for i, v := range p {
			if s, ok := v.(string); ok {
				parametros[i] = s
			}
		}
	}

	cuerpo := funcionDef["cuerpo"]
	var cuerpoNodos []*Nodo
	if c, ok := cuerpo.([]*Nodo); ok {
		cuerpoNodos = c
	} else if c, ok := cuerpo.(*Nodo); ok && c.Tipo == "CUERPO" {
		cuerpoNodos = c.Hijos
	}

	var predeterminados []*Nodo
	if pd, ok := funcionDef["predeterminados"].([]*Nodo); ok {
		predeterminados = pd
	}

	argumentos := e.VincularParametros(
		parametros, predeterminados, posicionales, nombrados, nodo,
		fmt.Sprintf("La función '%s'", nombre),
	)

	// Scope del módulo
	cambios := make(map[string]interface{})
	if moduloVariables, ok := funcionDef["_modulo_variables"].(map[string]interface{}); ok {
		for k, v := range moduloVariables {
			cambios[k] = v
		}
	}
	for i, param := range parametros {
		if i < len(argumentos) {
			cambios[param] = argumentos[i]
		}
	}

	revertir := e.AplicarScopeFuncion(cambios)
	defer revertir()

	// Si la función pertenece a un módulo, exponer temporalmente las demás
	// funciones de ese módulo por su nombre simple, para que puedan
	// llamarse entre sí como en su archivo de origen.
	if funcionesModulo, ok := funcionDef["_modulo_funciones"].(map[string]interface{}); ok {
		revertirFunciones := e.AplicarFuncionesTemporal(funcionesModulo)
		defer revertirFunciones()
	}

	var resultado interface{}
	var retornoErr *RetornoException

	func() {
		defer func() {
			if r := recover(); r != nil {
				if re, ok := r.(*RetornoException); ok {
					retornoErr = re
				} else {
					panic(r)
				}
			}
		}()
		for _, sentencia := range cuerpoNodos {
			e.interprete.Interpretar(sentencia)
		}
	}()

	if retornoErr != nil {
		resultado = retornoErr.Valor
	}

	return resultado
}

// NombreTipoWini devuelve el nombre del tipo Wini de un valor Go, tal como
// lo usan las funciones 'tipo' y los mensajes de error de conversión.
func (e *Ejecutor) NombreTipoWini(valor interface{}) string {
	switch v := valor.(type) {
	case string:
		return "cadena"
	case []interface{}:
		return "lista"
	case bool:
		return "booleano"
	case int:
		return "entero"
	case float64:
		return "decimal"
	case map[string]interface{}:
		return "diccionario"
	default:
		if v == nil {
			return "ninguno"
		}
		return reflect.TypeOf(v).Name()
	}
}

// ConvertirAEntero implementa la función global entero(x), al estilo de
// Python: panic con ErrorTipo/ErrorValor si la conversión no es posible.
func (e *Ejecutor) ConvertirAEntero(valor interface{}, nodo *Nodo) interface{} {
	switch v := valor.(type) {
	case int:
		return v
	case float64:
		return int(v)
	case bool:
		if v {
			return 1
		}
		return 0
	case string:
		texto := strings.TrimSpace(v)
		if n, err := strconv.Atoi(texto); err == nil {
			return n
		}
		if f, err := strconv.ParseFloat(texto, 64); err == nil {
			return int(f)
		}
		panic(&ErrorValor{ErrorConLinea: ErrorConLinea{
			Mensaje: fmt.Sprintf("no se puede convertir '%s' a entero", v),
			Linea:   &nodo.Linea,
		}})
	default:
		panic(&ErrorTipo{ErrorConLinea: ErrorConLinea{
			Mensaje: fmt.Sprintf("no se puede convertir un valor de tipo '%s' a entero", e.NombreTipoWini(valor)),
			Linea:   &nodo.Linea,
		}})
	}
}

// ConvertirADecimal implementa la función global decimal(x).
func (e *Ejecutor) ConvertirADecimal(valor interface{}, nodo *Nodo) interface{} {
	switch v := valor.(type) {
	case float64:
		return v
	case int:
		return float64(v)
	case bool:
		if v {
			return 1.0
		}
		return 0.0
	case string:
		texto := strings.TrimSpace(v)
		if f, err := strconv.ParseFloat(texto, 64); err == nil {
			return f
		}
		panic(&ErrorValor{ErrorConLinea: ErrorConLinea{
			Mensaje: fmt.Sprintf("no se puede convertir '%s' a decimal", v),
			Linea:   &nodo.Linea,
		}})
	default:
		panic(&ErrorTipo{ErrorConLinea: ErrorConLinea{
			Mensaje: fmt.Sprintf("no se puede convertir un valor de tipo '%s' a decimal", e.NombreTipoWini(valor)),
			Linea:   &nodo.Linea,
		}})
	}
}

// ConvertirALista implementa la función global lista(x). Cadenas se separan
// en caracteres y diccionarios se convierten en la lista de sus claves,
// igual que list() en Python.
func (e *Ejecutor) ConvertirALista(valor interface{}, nodo *Nodo) interface{} {
	switch v := valor.(type) {
	case []interface{}:
		resultado := make([]interface{}, len(v))
		copy(resultado, v)
		return resultado
	case string:
		resultado := make([]interface{}, 0, len(v))
		for _, r := range v {
			resultado = append(resultado, string(r))
		}
		return resultado
	case map[string]interface{}:
		resultado := make([]interface{}, 0, len(v))
		for k := range v {
			resultado = append(resultado, k)
		}
		return resultado
	default:
		panic(&ErrorTipo{ErrorConLinea: ErrorConLinea{
			Mensaje: fmt.Sprintf("no se puede convertir un valor de tipo '%s' a lista", e.NombreTipoWini(valor)),
			Linea:   &nodo.Linea,
		}})
	}
}

// ConvertirADiccionario implementa la función global diccionario(x). Acepta
// diccionarios (se copian) y listas de pares [clave, valor].
func (e *Ejecutor) ConvertirADiccionario(valor interface{}, nodo *Nodo) interface{} {
	switch v := valor.(type) {
	case map[string]interface{}:
		resultado := make(map[string]interface{}, len(v))
		for k, val := range v {
			resultado[k] = val
		}
		return resultado
	case []interface{}:
		resultado := make(map[string]interface{}, len(v))
		for _, elem := range v {
			par, ok := elem.([]interface{})
			if !ok || len(par) != 2 {
				panic(&ErrorValor{ErrorConLinea: ErrorConLinea{
					Mensaje: "diccionario() requiere una lista de pares [clave, valor]",
					Linea:   &nodo.Linea,
				}})
			}
			clave := fmt.Sprintf("%v", par[0])
			resultado[clave] = par[1]
		}
		return resultado
	default:
		panic(&ErrorTipo{ErrorConLinea: ErrorConLinea{
			Mensaje: fmt.Sprintf("no se puede convertir un valor de tipo '%s' a diccionario", e.NombreTipoWini(valor)),
			Linea:   &nodo.Linea,
		}})
	}
}

// ConvertirABooleano implementa la función global booleano(x). Al igual que
// bool() en Python, nunca falla: evalúa la "verdad" del valor.
func (e *Ejecutor) ConvertirABooleano(valor interface{}) interface{} {
	switch v := valor.(type) {
	case nil:
		return false
	case bool:
		return v
	case int:
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

// EjecutarFuncionNativa ejecuta funciones nativas del intérprete
func (e *Ejecutor) EjecutarFuncionNativa(nombre string, argumentos []interface{}, nodo *Nodo) interface{} {
	switch nombre {
	case "escribir":
		for _, arg := range argumentos {
			fmt.Print(FormatearTexto(arg))
		}
		fmt.Println()
		return nil

	case "leer":
		if len(argumentos) == 0 {
			reader := bufio.NewReader(os.Stdin)
			texto, _ := reader.ReadString('\n')
			return strings.TrimRight(texto, "\r\n")
		} else if len(argumentos) == 1 {
			fmt.Print(argumentos[0])
			reader := bufio.NewReader(os.Stdin)
			texto, _ := reader.ReadString('\n')
			return strings.TrimRight(texto, "\r\n")
		} else {
			panic(&RuntimeError{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("La función 'leer' espera 0 o 1 argumento, pero recibió %d", len(argumentos)),
					Linea:   &nodo.Linea,
				},
			})
		}

	case "tipo":
		if len(argumentos) != 1 {
			panic(&RuntimeError{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("La función 'tipo' espera 1 argumento, pero recibió %d", len(argumentos)),
					Linea:   &nodo.Linea,
				},
			})
		}
		return e.NombreTipoWini(argumentos[0])

	case "cadena":
		if len(argumentos) != 1 {
			panic(&RuntimeError{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("La función 'cadena' espera 1 argumento, pero recibió %d", len(argumentos)),
					Linea:   &nodo.Linea,
				},
			})
		}
		return FormatearTexto(argumentos[0])

	case "entero":
		if len(argumentos) != 1 {
			panic(&RuntimeError{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("La función 'entero' espera 1 argumento, pero recibió %d", len(argumentos)),
					Linea:   &nodo.Linea,
				},
			})
		}
		return e.ConvertirAEntero(argumentos[0], nodo)

	case "decimal":
		if len(argumentos) != 1 {
			panic(&RuntimeError{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("La función 'decimal' espera 1 argumento, pero recibió %d", len(argumentos)),
					Linea:   &nodo.Linea,
				},
			})
		}
		return e.ConvertirADecimal(argumentos[0], nodo)

	case "lista":
		if len(argumentos) != 1 {
			panic(&RuntimeError{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("La función 'lista' espera 1 argumento, pero recibió %d", len(argumentos)),
					Linea:   &nodo.Linea,
				},
			})
		}
		return e.ConvertirALista(argumentos[0], nodo)

	case "diccionario":
		if len(argumentos) != 1 {
			panic(&RuntimeError{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("La función 'diccionario' espera 1 argumento, pero recibió %d", len(argumentos)),
					Linea:   &nodo.Linea,
				},
			})
		}
		return e.ConvertirADiccionario(argumentos[0], nodo)

	case "booleano":
		if len(argumentos) != 1 {
			panic(&RuntimeError{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("La función 'booleano' espera 1 argumento, pero recibió %d", len(argumentos)),
					Linea:   &nodo.Linea,
				},
			})
		}
		return e.ConvertirABooleano(argumentos[0])

	case "longitud":
		if len(argumentos) != 1 {
			panic(&RuntimeError{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("La función 'longitud' espera 1 argumento, pero recibió %d", len(argumentos)),
					Linea:   &nodo.Linea,
				},
			})
		}
		switch v := argumentos[0].(type) {
		case string:
			return len(v)
		case []interface{}:
			return len(v)
		case map[string]interface{}:
			return len(v)
		default:
			panic(&RuntimeError{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("La función 'longitud' no admite valores de tipo %T", argumentos[0]),
					Linea:   &nodo.Linea,
				},
			})
		}

	default:
		panic(&RuntimeError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: fmt.Sprintf("La función '%s' no está definida", nombre),
				Linea:   &nodo.Linea,
			},
		})
	}
}

// EjecutarMetodo ejecuta un método sobre un objeto
func (e *Ejecutor) EjecutarMetodo(nodo *Nodo) interface{} {
	metodoNombre := nodo.Valor.(string)
	if len(nodo.Hijos) == 0 {
		panic(&RuntimeError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: fmt.Sprintf("Método '%s' sin objeto", metodoNombre),
				Linea:   &nodo.Linea,
			},
		})
	}

	nodoObjeto := nodo.Hijos[0]
	argumentosNodos := []*Nodo{}
	if len(nodo.Hijos) > 1 {
		argumentosNodos = nodo.Hijos[1:]
	}

	posicionales, nombrados := e.EvaluarArgumentos(argumentosNodos)
	objeto := e.interprete.Evaluador.Evaluar(nodoObjeto)

	// Llamadas sobre un módulo importado: modulo.funcion(args)
	if mapa, ok := objeto.(map[string]interface{}); ok {
		if tipo, ok := mapa["_tipo"].(string); ok && tipo == "modulo" {
			return e.EjecutarLlamadaModulo(mapa, metodoNombre, posicionales, nombrados, nodo)
		}
	}

	// Para tipos básicos (str, list, dict), buscar en métodos nativos
	resultadoNativo := e.EjecutarMetodoNativo(objeto, metodoNombre, posicionales, nombrados, nodo)
	if resultadoNativo != SENTINEL {
		// Las listas son slices de Go: append/ordenar/etc. pueden devolver un
		// slice nuevo que no comparte memoria con el original, así que hay
		// que reescribir la variable para que el método se sienta "mutante"
		// (igual que en Python). Los diccionarios son mapas y ya mutan en sitio.
		if _, esLista := objeto.([]interface{}); esLista && metodosListaMutantes[metodoNombre] {
			if nodoObjeto.Tipo == "IDENTIFICADOR" {
				if nuevaLista, ok := resultadoNativo.([]interface{}); ok {
					e.interprete.Variables[nodoObjeto.Valor.(string)] = nuevaLista
				}
			}
		}
		return resultadoNativo
	}

	panic(&RuntimeError{
		ErrorConLinea: ErrorConLinea{
			Mensaje: fmt.Sprintf("No se puede llamar '%s' sobre un valor de tipo %T", metodoNombre, objeto),
			Linea:   &nodo.Linea,
		},
	})
}

// EjecutarLlamadaModulo ejecuta 'modulo.nombre(args)'
func (e *Ejecutor) EjecutarLlamadaModulo(modulo map[string]interface{}, nombre string, posicionales []interface{}, nombrados map[string]interface{}, nodo *Nodo) interface{} {
	funciones, ok := modulo["funciones"].(map[string]interface{})
	if !ok {
		funciones = make(map[string]interface{})
	}

	if funcion, ok := funciones[nombre]; ok {
		if fnMap, ok := funcion.(map[string]interface{}); ok {
			return e.EjecutarFuncionWini(fnMap, posicionales, nodo, nombre, nombrados)
		}
		if fnNativa, ok := funcion.(func(...interface{}) interface{}); ok {
			if len(nombrados) > 0 {
				panic(&RuntimeError{ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("La función nativa '%s.%s' no admite argumentos con nombre", modulo["_nombre"], nombre),
					Linea:   &nodo.Linea,
				}})
			}
			return fnNativa(posicionales...)
		}
	}

	nombreModulo := "?"
	if n, ok := modulo["_nombre"].(string); ok {
		nombreModulo = n
	}

	panic(&RuntimeError{
		ErrorConLinea: ErrorConLinea{
			Mensaje: fmt.Sprintf("El módulo '%s' no tiene función '%s'", nombreModulo, nombre),
			Linea:   &nodo.Linea,
		},
	})
}
