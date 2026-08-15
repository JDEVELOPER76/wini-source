package wini

import (
	"fmt"
	"strconv"
	"strings"
)

// Nodo representa un nodo en el AST
type Nodo struct {
	Tipo  string
	Valor interface{}
	Hijos []*Nodo
	Linea int
}

// NewNodo crea un nuevo nodo
func NewNodo(tipo string, valor interface{}, linea int) *Nodo {
	return &Nodo{
		Tipo:  tipo,
		Valor: valor,
		Linea: linea,
		Hijos: []*Nodo{},
	}
}

// AgregarHijo añade uno o varios hijos al nodo y permite encadenar llamadas
func (n *Nodo) AgregarHijo(hijos ...*Nodo) *Nodo {
	n.Hijos = append(n.Hijos, hijos...)
	return n
}

// Parser implementa el analizador sintáctico
type Parser struct {
	tokens   []Token
	posicion int
}

// NewParser crea un nuevo parser
func NewParser(tokens []Token) *Parser {
	return &Parser{
		tokens:   tokens,
		posicion: 0,
	}
}

// tokenActual retorna el token actual
func (p *Parser) tokenActual() *Token {
	if p.posicion < len(p.tokens) {
		return &p.tokens[p.posicion]
	}
	return nil
}

// tokenSiguiente avanza al siguiente token
func (p *Parser) tokenSiguiente() {
	p.posicion++
}

// tokenLinea retorna la línea del token actual
func (p *Parser) tokenLinea() int {
	t := p.tokenActual()
	if t != nil {
		return t.Linea
	}
	return 0
}

// saltarNuevasLineas salta los tokens NUEVA_LINEA
func (p *Parser) saltarNuevasLineas() {
	for p.tokenActual() != nil && p.tokenActual().Tipo == NUEVA_LINEA {
		p.tokenSiguiente()
	}
}

// primerTokenNoNuevaLinea devuelve el índice del primer token que no sea
// NUEVA_LINEA a partir de 'desde', SIN mover el cursor del parser. Se usa
// para "espiar" si después de un bloque viene una palabra clave de
// continuación (sino/capturar/finalmente) sin consumir de forma permanente
// el salto de línea que marca el fin del bloque: si la palabra clave no
// aparece, ese salto de línea debe quedar intacto para que el bloque que
// contiene a este (funcion/para/mientras/si/intentar) pueda detectar
// correctamente el des-sangrado.
func (p *Parser) primerTokenNoNuevaLinea(desde int) int {
	i := desde
	for i < len(p.tokens) && p.tokens[i].Tipo == NUEVA_LINEA {
		i++
	}
	return i
}

// esperado verifica que el token actual sea del tipo esperado
func (p *Parser) esperado(tipo TipoToken) string {
	token := p.tokenActual()
	if token != nil && token.Tipo == tipo {
		valor := token.Valor
		p.tokenSiguiente()
		return valor
	}
	linea := 0
	if token != nil {
		linea = token.Linea
	}
	panic(&SintaxisError{
		ErrorConLinea: ErrorConLinea{
			Mensaje: fmt.Sprintf("Se esperaba %s, pero se encontró %v", tipo, token),
			Linea:   &linea,
		},
	})
}

// parsearArgumento parsea un argumento de una llamada
func (p *Parser) parsearArgumento() *Nodo {
	token := p.tokenActual()
	if token == nil {
		return p.parsearExpresion()
	}

	siguiente := p.tokenSiguientePeek()
	if token.Tipo == IDENTIFICADOR && siguiente != nil && siguiente.Tipo == OPERADOR_ASIGNACION && siguiente.Valor == "=" {
		linea := token.Linea
		nombreArg := p.esperado(IDENTIFICADOR)
		p.esperado(OPERADOR_ASIGNACION) // consume '='
		valor := p.parsearExpresion()
		return NewNodo("ARG_NOMBRADO", nombreArg, linea).AgregarHijo(valor)
	}
	return p.parsearExpresion()
}

// tokenSiguientePeek mira el siguiente token sin consumirlo
func (p *Parser) tokenSiguientePeek() *Token {
	if p.posicion+1 < len(p.tokens) {
		return &p.tokens[p.posicion+1]
	}
	return nil
}

// encontrarCorcheteCierre encuentra el corchete de cierre
func (p *Parser) encontrarCorcheteCierre(inicio int) int {
	balance := 0
	for i := inicio; i < len(p.tokens); i++ {
		if p.tokens[i].Tipo == CORCHETE {
			switch p.tokens[i].Valor {
			case "[":
				balance++
			case "]":
				balance--
				if balance == 0 {
					return i
				}
			}
		}
	}
	panic(&SintaxisError{
		ErrorConLinea: ErrorConLinea{
			Mensaje: "Corchete ']' no encontrado",
			Linea:   &[]int{p.tokenLinea()}[0],
		},
	})
}

// Parse inicia el análisis sintáctico
func (p *Parser) Parse() *Nodo {
	sentencias := []*Nodo{}
	for p.tokenActual() != nil {
		if p.tokenActual().Tipo == NUEVA_LINEA {
			p.tokenSiguiente()
			continue
		}
		sentencias = append(sentencias, p.parsearSentencia(nil))
	}
	return NewNodo("PROGRAMA", nil, 0).AgregarHijo(sentencias...)
}

func indentacionDeToken(token *Token) int {
	if token == nil || token.Tipo != NUEVA_LINEA {
		return -1
	}
	if token.Valor == "" {
		return 0
	}
	if runas := []rune(token.Valor); len(runas) == 1 {
		return int(runas[0])
	}
	if i, err := strconv.Atoi(token.Valor); err == nil {
		return i
	}
	return -1
}

// parsearSentencia parsea una sentencia
func (p *Parser) parsearSentencia(palabrasParada map[string]bool) *Nodo {
	p.saltarNuevasLineas()

	token := p.tokenActual()
	if token == nil {
		return nil
	}

	// Palabra de parada
	if token.Tipo == PALABRA_CLAVE {
		if palabrasParada != nil && palabrasParada[token.Valor] {
			return nil
		}
		if token.Valor == "capturar" || token.Valor == "finalmente" {
			return nil
		}
	}

	// Si encontramos una NUEVA_LINEA con indentación (cierre de bloque), retornar nil
	if token.Tipo == NUEVA_LINEA {
		return nil
	}

	// === VERIFICACIÓN POR VALOR ===
	if token.Tipo == PALABRA_CLAVE {
		switch token.Valor {
		case "intentar":
			return p.parsearIntentar(palabrasParada)
		case "lanzar":
			return p.parsearLanzar()
		case "mientras":
			return p.parsearMientras()
		case "para":
			return p.parsearPara()
		case "romper":
			linea := p.tokenLinea()
			p.esperado(PALABRA_CLAVE)
			return NewNodo("ROMPER", nil, linea)
		case "continuar":
			linea := p.tokenLinea()
			p.esperado(PALABRA_CLAVE)
			return NewNodo("CONTINUAR", nil, linea)
		case "retornar":
			linea := p.tokenLinea()
			p.esperado(PALABRA_CLAVE)
			expr := p.parsearExpresion()
			return NewNodo("RETORNO", nil, linea).AgregarHijo(expr)
		case "importar":
			return p.parsearImportar()
		case "funcion":
			return p.parsearFuncion()
		case "si":
			return p.parsearSi(palabrasParada)
		case "escribir", "leer":
			linea := p.tokenLinea()
			nombre := p.esperado(PALABRA_CLAVE)
			p.esperado(PARENTESIS)
			argumentos := []*Nodo{}
			if p.tokenActual() != nil && !(p.tokenActual().Tipo == PARENTESIS && p.tokenActual().Valor == ")") {
				argumentos = append(argumentos, p.parsearArgumento())
				for p.tokenActual() != nil && p.tokenActual().Tipo == COMA {
					p.esperado(COMA)
					argumentos = append(argumentos, p.parsearArgumento())
				}
			}
			p.esperado(PARENTESIS)
			return NewNodo("LLAMADA", nombre, linea).AgregarHijo(argumentos...)
		}
	}

	// Asignaciones
	if token.Tipo == IDENTIFICADOR {
		siguiente := p.tokenSiguientePeek()
		if siguiente != nil && siguiente.Tipo == CORCHETE && siguiente.Valor == "[" {
			idxCierre := p.encontrarCorcheteCierre(p.posicion + 1)
			if idxCierre+1 < len(p.tokens) {
				tokenTrasIndice := p.tokens[idxCierre+1]
				if tokenTrasIndice.Valor == "=" {
					return p.parsearAsignacion()
				}
				if tokenTrasIndice.Tipo == OPERADOR_ASIGNACION {
					return p.parsearAsignacionCompuesta()
				}
			}
		}
		if siguiente != nil && siguiente.Valor == "=" {
			return p.parsearAsignacion()
		}
		if siguiente != nil && siguiente.Tipo == OPERADOR_ASIGNACION {
			return p.parsearAsignacionCompuesta()
		}
	}

	// Expresión suelta
	return p.parsearExpresion()
}

// parsearAsignacion parsea una asignación
func (p *Parser) parsearAsignacion() *Nodo {
	lineaID := p.tokenLinea()
	idNombre := p.esperado(IDENTIFICADOR)

	// Asignación con índice
	if p.tokenActual() != nil && p.tokenActual().Tipo == CORCHETE && p.tokenActual().Valor == "[" {
		p.esperado(CORCHETE)
		indice := p.parsearExpresion()
		p.esperado(CORCHETE)
		token := p.tokenActual()
		if token == nil || token.Valor != "=" {
			panic(&SintaxisError{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("Se esperaba '=' pero se encontró %v", token),
					Linea:   &lineaID,
				},
			})
		}
		p.tokenSiguiente()
		expr := p.parsearExpresion()
		return NewNodo("ASIGNACION_INDEX", idNombre, lineaID).AgregarHijo(indice).AgregarHijo(expr)
	}

	// Asignación simple
	token := p.tokenActual()
	if token == nil || token.Valor != "=" {
		panic(&SintaxisError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: fmt.Sprintf("Se esperaba '=' pero se encontró %v", token),
				Linea:   &lineaID,
			},
		})
	}
	p.tokenSiguiente()
	expr := p.parsearExpresion()
	return NewNodo("ASIGNACION", idNombre, lineaID).AgregarHijo(expr)
}

// parsearAsignacionCompuesta parsea 'x += expr', 'x -= expr', etc, y también
// 'x[i] += expr'. Se desazucara (desugar) a una asignación normal cuyo valor
// es una operación binaria: 'x = x + (expr)' / 'x[i] = x[i] + (expr)'.
func (p *Parser) parsearAsignacionCompuesta() *Nodo {
	lineaID := p.tokenLinea()
	idNombre := p.esperado(IDENTIFICADOR)

	// Forma indexada: x[i] += expr
	if p.tokenActual() != nil && p.tokenActual().Tipo == CORCHETE && p.tokenActual().Valor == "[" {
		p.esperado(CORCHETE)
		indice := p.parsearExpresion()
		p.esperado(CORCHETE)

		token := p.tokenActual()
		if token == nil || token.Tipo != OPERADOR_ASIGNACION {
			panic(&SintaxisError{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("Se esperaba un operador de asignación compuesta pero se encontró %v", token),
					Linea:   &lineaID,
				},
			})
		}
		opCompuesto := p.esperado(OPERADOR_ASIGNACION)
		opBase := string(opCompuesto[0])

		expr := p.parsearExpresion()

		valorActual := NewNodo("INDEXACION", nil, lineaID).
			AgregarHijo(NewNodo("IDENTIFICADOR", idNombre, lineaID)).
			AgregarHijo(indice)
		combinado := NewNodo("BINARIA", opBase, lineaID).AgregarHijo(valorActual).AgregarHijo(expr)

		return NewNodo("ASIGNACION_INDEX", idNombre, lineaID).AgregarHijo(indice).AgregarHijo(combinado)
	}

	// Forma simple: x += expr
	token := p.tokenActual()
	if token == nil || token.Tipo != OPERADOR_ASIGNACION {
		panic(&SintaxisError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: fmt.Sprintf("Se esperaba un operador de asignación compuesta pero se encontró %v", token),
				Linea:   &lineaID,
			},
		})
	}
	opCompuesto := p.esperado(OPERADOR_ASIGNACION)
	opBase := string(opCompuesto[0])

	expr := p.parsearExpresion()

	valorActual := NewNodo("IDENTIFICADOR", idNombre, lineaID)
	combinado := NewNodo("BINARIA", opBase, lineaID).AgregarHijo(valorActual).AgregarHijo(expr)

	return NewNodo("ASIGNACION", idNombre, lineaID).AgregarHijo(combinado)
}

// parsearFuncion parsea una función
func (p *Parser) parsearFuncion() *Nodo {
	linea := p.tokenLinea()
	p.esperado(PALABRA_CLAVE) // funcion
	nombreFuncion := p.esperado(IDENTIFICADOR)
	p.esperado(PARENTESIS)

	// parsearParametro parsea un parámetro, con soporte opcional para
	// un valor por defecto: nombre[=expresion]
	parsearParametro := func() *Nodo {
		lineaParam := p.tokenLinea()
		nombreParam := p.esperado(IDENTIFICADOR)
		paramNodo := NewNodo("PARAM", nombreParam, lineaParam)
		if p.tokenActual() != nil && p.tokenActual().Tipo == OPERADOR_ASIGNACION && p.tokenActual().Valor == "=" {
			p.tokenSiguiente() // consumir '='
			valorPredeterminado := p.parsearExpresion()
			paramNodo.AgregarHijo(valorPredeterminado)
		}
		return paramNodo
	}

	parametros := []*Nodo{}
	if p.tokenActual() != nil && !(p.tokenActual().Tipo == PARENTESIS && p.tokenActual().Valor == ")") {
		parametros = append(parametros, parsearParametro())
		for p.tokenActual() != nil && p.tokenActual().Tipo == COMA {
			p.esperado(COMA)
			parametros = append(parametros, parsearParametro())
		}
	}
	p.esperado(PARENTESIS)
	p.esperado(PUNTOS)

	if p.tokenActual() == nil || p.tokenActual().Tipo != NUEVA_LINEA {
		panic(&SintaxisError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: "Se esperaba un salto de línea después de ':' en la función",
				Linea:   &linea,
			},
		})
	}

	indentacionBloque := indentacionDeToken(p.tokenActual())
	if indentacionBloque < 0 {
		panic(&SintaxisError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: "Se esperaba un salto de línea con indentación en la función",
				Linea:   &linea,
			},
		})
	}
	p.esperado(NUEVA_LINEA)

	// Docstring opcional
	p.saltarNuevasLineas()
	token := p.tokenActual()
	if token != nil && token.Tipo == CADENA_TEXTO {
		p.tokenSiguiente()
		if p.tokenActual() != nil && p.tokenActual().Tipo == NUEVA_LINEA {
			p.tokenSiguiente()
		}
	} else if token != nil && token.Tipo == COMENTARIO && strings.HasPrefix(token.Valor, "#@") {
		p.tokenSiguiente()
		if p.tokenActual() != nil && p.tokenActual().Tipo == NUEVA_LINEA {
			p.tokenSiguiente()
		}
	}

	// Cuerpo
	cuerpo := []*Nodo{}
	for p.tokenActual() != nil {
		tok := p.tokenActual()
		if tok.Tipo == NUEVA_LINEA {
			if indentacionDeToken(tok) < indentacionBloque {
				break
			}
			p.tokenSiguiente()
			continue
		}
		sent := p.parsearSentencia(nil)
		if sent == nil {
			break
		}
		cuerpo = append(cuerpo, sent)
	}

	nodo := NewNodo("FUNCION", nombreFuncion, linea)
	nodo.AgregarHijo(NewNodo("PARAMETROS", nil, linea).AgregarHijo(parametros...))
	nodo.AgregarHijo(NewNodo("CUERPO", nil, linea).AgregarHijo(cuerpo...))
	// Adjuntar docstring como metadata (se puede acceder con un campo extra)
	return nodo
}

// parsearSi parsea un condicional si
func (p *Parser) parsearSi(palabrasParada map[string]bool) *Nodo {
	if palabrasParada == nil {
		palabrasParada = make(map[string]bool)
	}
	linea := p.tokenLinea()
	p.esperado(PALABRA_CLAVE) // si
	condicion := p.parsearExpresion()

	p.esperado(PUNTOS)

	if p.tokenActual() == nil || p.tokenActual().Tipo != NUEVA_LINEA {
		panic(&SintaxisError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: "Se esperaba un salto de línea después de ':'",
				Linea:   &linea,
			},
		})
	}

	indentacionBloque := indentacionDeToken(p.tokenActual())
	if indentacionBloque < 0 {
		panic(&SintaxisError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: "Se esperaba un salto de línea con indentación después de ':'",
				Linea:   &linea,
			},
		})
	}
	p.esperado(NUEVA_LINEA)

	// Bloque SI
	bloqueSi := []*Nodo{}
	for p.tokenActual() != nil {
		token := p.tokenActual()
		if token.Tipo == NUEVA_LINEA {
			if indentacionDeToken(token) < indentacionBloque {
				break
			}
			p.tokenSiguiente()
			continue
		}
		if token.Tipo == PALABRA_CLAVE && token.Valor == "sino" {
			break
		}
		sent := p.parsearSentencia(nil)
		if sent == nil {
			break
		}
		bloqueSi = append(bloqueSi, sent)
	}

	// Bloque SINO (opcional). Se "espía" hacia adelante sin consumir de forma
	// permanente los saltos de línea: si lo que sigue no es 'sino', el salto
	// de línea que marca el des-sangrado debe quedar disponible para quien
	// llamó a parsearSi (funcion/para/mientras/otro si/intentar).
	bloqueSino := []*Nodo{}
	idxSiguiente := p.primerTokenNoNuevaLinea(p.posicion)
	if idxSiguiente < len(p.tokens) && p.tokens[idxSiguiente].Tipo == PALABRA_CLAVE && p.tokens[idxSiguiente].Valor == "sino" {
		p.posicion = idxSiguiente
		p.esperado(PALABRA_CLAVE) // sino

		// Soporta tres formas:
		// 1) sino:
		// 2) sino si condicion:
		// 3) sino condicion:
		tokTrasSino := p.tokenActual()
		if tokTrasSino != nil && tokTrasSino.Tipo == PUNTOS {
			p.esperado(PUNTOS)

			if p.tokenActual() == nil || p.tokenActual().Tipo != NUEVA_LINEA {
				panic(&SintaxisError{
					ErrorConLinea: ErrorConLinea{
						Mensaje: "Se esperaba un salto de línea después de ':'",
						Linea:   &linea,
					},
				})
			}

			indentacionSino := indentacionDeToken(p.tokenActual())
			if indentacionSino < 0 {
				panic(&SintaxisError{
					ErrorConLinea: ErrorConLinea{
						Mensaje: "Se esperaba un salto de línea con indentación después de ':'",
						Linea:   &linea,
					},
				})
			}
			p.esperado(NUEVA_LINEA)

			for p.tokenActual() != nil {
				token := p.tokenActual()
				if token.Tipo == NUEVA_LINEA {
					if indentacionDeToken(token) < indentacionSino {
						break
					}
					p.tokenSiguiente()
					continue
				}
				sent := p.parsearSentencia(nil)
				if sent == nil {
					break
				}
				bloqueSino = append(bloqueSino, sent)
			}
		} else {
			if p.tokenActual() != nil && p.tokenActual().Tipo == PALABRA_CLAVE && p.tokenActual().Valor == "si" {
				p.esperado(PALABRA_CLAVE)
			}

			condicionSino := p.parsearExpresion()
			p.esperado(PUNTOS)

			if p.tokenActual() == nil || p.tokenActual().Tipo != NUEVA_LINEA {
				panic(&SintaxisError{
					ErrorConLinea: ErrorConLinea{
						Mensaje: "Se esperaba un salto de línea después de ':'",
						Linea:   &linea,
					},
				})
			}

			indentacionSinoCond := indentacionDeToken(p.tokenActual())
			if indentacionSinoCond < 0 {
				panic(&SintaxisError{
					ErrorConLinea: ErrorConLinea{
						Mensaje: "Se esperaba un salto de línea con indentación después de ':'",
						Linea:   &linea,
					},
				})
			}
			p.esperado(NUEVA_LINEA)

			bloqueSinoCond := []*Nodo{}
			for p.tokenActual() != nil {
				token := p.tokenActual()
				if token.Tipo == NUEVA_LINEA {
					if indentacionDeToken(token) < indentacionSinoCond {
						break
					}
					p.tokenSiguiente()
					continue
				}
				sent := p.parsearSentencia(nil)
				if sent == nil {
					break
				}
				bloqueSinoCond = append(bloqueSinoCond, sent)
			}

			nodoSinoSi := NewNodo("SI", nil, linea).
				AgregarHijo(condicionSino).
				AgregarHijo(NewNodo("BLOQUE_SI", nil, linea).AgregarHijo(bloqueSinoCond...)).
				AgregarHijo(NewNodo("BLOQUE_SINO", nil, linea))
			bloqueSino = append(bloqueSino, nodoSinoSi)
		}
	}

	return NewNodo("SI", nil, linea).
		AgregarHijo(condicion).
		AgregarHijo(NewNodo("BLOQUE_SI", nil, linea).AgregarHijo(bloqueSi...)).
		AgregarHijo(NewNodo("BLOQUE_SINO", nil, linea).AgregarHijo(bloqueSino...))
}

// parsearIntentar parsea una estructura intentar-capturar-finalmente
func (p *Parser) parsearIntentar(palabrasParada map[string]bool) *Nodo {
	if palabrasParada == nil {
		palabrasParada = make(map[string]bool)
	}

	linea := p.tokenLinea()
	p.esperado(PALABRA_CLAVE) // intentar
	p.esperado(PUNTOS)

	if p.tokenActual() == nil || p.tokenActual().Tipo != NUEVA_LINEA {
		panic(&SintaxisError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: "Se esperaba un salto de línea después de ':' en intentar",
				Linea:   &[]int{p.tokenLinea()}[0],
			},
		})
	}

	indentacionBloque := indentacionDeToken(p.tokenActual())
	if indentacionBloque < 0 {
		panic(&SintaxisError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: "Se esperaba un salto de línea con indentación en intentar",
				Linea:   &[]int{p.tokenLinea()}[0],
			},
		})
	}
	p.esperado(NUEVA_LINEA)

	paradaTry := make(map[string]bool)
	for k, v := range palabrasParada {
		paradaTry[k] = v
	}
	paradaTry["capturar"] = true
	paradaTry["finalmente"] = true

	bloqueTry := []*Nodo{}
	for p.tokenActual() != nil {
		token := p.tokenActual()
		if token.Tipo == NUEVA_LINEA {
			if indentacionDeToken(token) < indentacionBloque {
				break
			}
			p.tokenSiguiente()
			continue
		}
		if token.Tipo == PALABRA_CLAVE && (token.Valor == "capturar" || token.Valor == "finalmente") {
			break
		}
		sent := p.parsearSentencia(paradaTry)
		if sent == nil {
			break
		}
		bloqueTry = append(bloqueTry, sent)
	}

	// Parsear bloques capturar y finally. Se "espía" hacia adelante (sin
	// consumir de forma permanente) para saber si lo que sigue es
	// 'capturar'/'finalmente'; si no lo es, dejamos el salto de línea
	// intacto para que el bloque contenedor detecte el des-sangrado.
	bloquesCapturar := []*Nodo{}
	var bloqueFinally []*Nodo

	for {
		idxSiguiente := p.primerTokenNoNuevaLinea(p.posicion)
		if idxSiguiente >= len(p.tokens) {
			break
		}
		token := p.tokens[idxSiguiente]
		if token.Tipo != PALABRA_CLAVE || (token.Valor != "capturar" && token.Valor != "finalmente") {
			break
		}
		p.posicion = idxSiguiente

		switch token.Valor {
		case "capturar":
			lineaCapturar := p.tokenLinea()
			p.esperado(PALABRA_CLAVE) // capturar

			var tipoError string
			var variableError string

			// Forma con paréntesis: capturar(Tipo) como var:
			if p.tokenActual() != nil && p.tokenActual().Tipo == PARENTESIS && p.tokenActual().Valor == "(" {
				p.esperado(PARENTESIS)
				if p.tokenActual() != nil && p.tokenActual().Tipo == IDENTIFICADOR {
					tipoError = p.esperado(IDENTIFICADOR)
				} else if p.tokenActual() != nil && p.tokenActual().Tipo == PALABRA_CLAVE {
					tipoError = p.esperado(PALABRA_CLAVE)
				}
				p.esperado(PARENTESIS)
			} else if p.tokenActual() != nil && p.tokenActual().Tipo == IDENTIFICADOR {
				tipoError = p.esperado(IDENTIFICADOR)
				if p.tokenActual() != nil && p.tokenActual().Tipo == PUNTO {
					p.esperado(PUNTO)
					tipoError = tipoError + "." + p.esperado(IDENTIFICADOR)
				}
			}

			if p.tokenActual() != nil && p.tokenActual().Tipo == PALABRA_CLAVE && p.tokenActual().Valor == "como" {
				p.esperado(PALABRA_CLAVE) // como
				variableError = p.esperado(IDENTIFICADOR)
			}

			p.esperado(PUNTOS)

			if p.tokenActual() == nil || p.tokenActual().Tipo != NUEVA_LINEA {
				panic(&SintaxisError{
					ErrorConLinea: ErrorConLinea{
						Mensaje: "Se esperaba un salto de línea después de ':' en capturar",
						Linea:   &[]int{p.tokenLinea()}[0],
					},
				})
			}

			indentCapturar := indentacionDeToken(p.tokenActual())
			if indentCapturar < 0 {
				panic(&SintaxisError{
					ErrorConLinea: ErrorConLinea{
						Mensaje: "Se esperaba un salto de línea con indentación en capturar",
						Linea:   &[]int{p.tokenLinea()}[0],
					},
				})
			}
			p.esperado(NUEVA_LINEA)

			paradaCapturar := make(map[string]bool)
			for k, v := range palabrasParada {
				paradaCapturar[k] = v
			}
			paradaCapturar["capturar"] = true
			paradaCapturar["finalmente"] = true

			bloqueCapturar := []*Nodo{}
			for p.tokenActual() != nil {
				if p.tokenActual().Tipo == NUEVA_LINEA {
					if indentacionDeToken(p.tokenActual()) < indentCapturar {
						break
					}
					p.tokenSiguiente()
					continue
				}
				if p.tokenActual().Tipo == PALABRA_CLAVE && (p.tokenActual().Valor == "capturar" || p.tokenActual().Valor == "finalmente") {
					break
				}
				sent := p.parsearSentencia(paradaCapturar)
				if sent == nil {
					break
				}
				bloqueCapturar = append(bloqueCapturar, sent)
			}

			nodoCapturar := NewNodo("CAPTURAR", tipoError, lineaCapturar)
			nodoCapturar.AgregarHijo(NewNodo("VARIABLE_ERROR", variableError, lineaCapturar))
			nodoCapturar.AgregarHijo(NewNodo("BLOQUE", nil, lineaCapturar).AgregarHijo(bloqueCapturar...))
			bloquesCapturar = append(bloquesCapturar, nodoCapturar)

		case "finalmente":
			p.esperado(PALABRA_CLAVE) // finalmente
			p.esperado(PUNTOS)

			if p.tokenActual() == nil || p.tokenActual().Tipo != NUEVA_LINEA {
				panic(&SintaxisError{
					ErrorConLinea: ErrorConLinea{
						Mensaje: "Se esperaba un salto de línea después de ':' en finalmente",
						Linea:   &[]int{p.tokenLinea()}[0],
					},
				})
			}

			indentFinally := indentacionDeToken(p.tokenActual())
			if indentFinally < 0 {
				panic(&SintaxisError{
					ErrorConLinea: ErrorConLinea{
						Mensaje: "Se esperaba un salto de línea con indentación en finalmente",
						Linea:   &[]int{p.tokenLinea()}[0],
					},
				})
			}
			p.esperado(NUEVA_LINEA)

			paradaFinally := make(map[string]bool)
			for k, v := range palabrasParada {
				paradaFinally[k] = v
			}

			bloqueFinally = []*Nodo{}
			for p.tokenActual() != nil {
				if p.tokenActual().Tipo == NUEVA_LINEA {
					if indentacionDeToken(p.tokenActual()) < indentFinally {
						break
					}
					p.tokenSiguiente()
					continue
				}
				sent := p.parsearSentencia(paradaFinally)
				if sent == nil {
					break
				}
				bloqueFinally = append(bloqueFinally, sent)
			}
		}

		if token.Valor == "finalmente" {
			break
		}
	}

	nodo := NewNodo("INTENTAR", nil, linea)
	nodo.AgregarHijo(NewNodo("BLOQUE_TRY", nil, linea).AgregarHijo(bloqueTry...))
	nodo.AgregarHijo(NewNodo("BLOQUES_CAPTURAR", nil, linea).AgregarHijo(bloquesCapturar...))
	if len(bloqueFinally) > 0 {
		nodo.AgregarHijo(NewNodo("BLOQUE_FINALLY", nil, linea).AgregarHijo(bloqueFinally...))
	} else {
		nodo.AgregarHijo(NewNodo("BLOQUE_FINALLY", nil, linea))
	}

	return nodo
}

// parsearImportar parsea la instrucción 'importar'
// En parser.go, modificar parsearImportar
func (p *Parser) parsearImportar() *Nodo {
	linea := p.tokenLinea()
	p.esperado(PALABRA_CLAVE) // importar

	var nombreModulo string

	// Soporte para importar con nombre en comillas: importar "os.dll" como os
	token := p.tokenActual()
	if token != nil && (token.Tipo == CADENA_TEXTO || token.Tipo == CADENA_INTERPOLADA) {
		nombreModulo = p.esperado(token.Tipo)
		nombreModulo = strings.Trim(nombreModulo, "\"'") // Quitar comillas
	} else {
		nombreModulo = p.esperado(IDENTIFICADOR)
		for p.tokenActual() != nil && p.tokenActual().Tipo == PUNTO {
			p.esperado(PUNTO)
			nombreModulo += "." + p.esperado(IDENTIFICADOR)
		}
	}

	alias := ""
	if p.tokenActual() != nil && p.tokenActual().Tipo == PALABRA_CLAVE && p.tokenActual().Valor == "como" {
		p.esperado(PALABRA_CLAVE) // como
		alias = p.esperado(IDENTIFICADOR)
	}

	nodo := NewNodo("IMPORTAR", nombreModulo, linea)
	nodo.AgregarHijo(NewNodo("ALIAS", alias, linea))
	return nodo
}

// parsearLanzar parsea la instrucción 'lanzar'
func (p *Parser) parsearLanzar() *Nodo {
	linea := p.tokenLinea()
	p.esperado(PALABRA_CLAVE) // lanzar

	var tipoError string
	var mensajeExpr *Nodo

	token := p.tokenActual()

	// Forma nueva: lanzar Tipo(...) o lanzar modulo.Tipo(...)
	if token != nil && token.Tipo == IDENTIFICADOR {
		tipoError = p.esperado(IDENTIFICADOR)

		if p.tokenActual() != nil && p.tokenActual().Tipo == PUNTO {
			p.esperado(PUNTO)
			tipoError = tipoError + "." + p.esperado(IDENTIFICADOR)
		}

		if p.tokenActual() != nil && p.tokenActual().Tipo == PARENTESIS && p.tokenActual().Valor == "(" {
			p.esperado(PARENTESIS)
			if p.tokenActual() != nil && !(p.tokenActual().Tipo == PARENTESIS && p.tokenActual().Valor == ")") {
				mensajeExpr = p.parsearExpresion()
			}
			p.esperado(PARENTESIS)
		}

		nodo := NewNodo("LANZAR", nil, linea)
		nodo.AgregarHijo(NewNodo("TIPO_ERROR", tipoError, linea))
		if mensajeExpr != nil {
			nodo.AgregarHijo(NewNodo("MENSAJE", nil, linea).AgregarHijo(mensajeExpr))
		} else {
			nodo.AgregarHijo(NewNodo("MENSAJE", nil, linea))
		}
		return nodo
	}

	// Forma antigua: lanzar("msg") o lanzar(Tipo, "msg")
	if token != nil && token.Tipo == PARENTESIS && token.Valor == "(" {
		p.esperado(PARENTESIS)

		token2 := p.tokenActual()
		if token2 != nil && token2.Tipo == IDENTIFICADOR {
			siguiente := p.tokenSiguientePeek()
			if siguiente != nil && siguiente.Tipo == COMA {
				tipoError = p.esperado(IDENTIFICADOR)
				p.esperado(COMA)
				mensajeExpr = p.parsearExpresion()
			} else {
				mensajeExpr = p.parsearExpresion()
			}
		} else {
			mensajeExpr = p.parsearExpresion()
		}

		p.esperado(PARENTESIS)

		nodo := NewNodo("LANZAR", nil, linea)
		nodo.AgregarHijo(NewNodo("TIPO_ERROR", tipoError, linea))
		if mensajeExpr != nil {
			nodo.AgregarHijo(NewNodo("MENSAJE", nil, linea).AgregarHijo(mensajeExpr))
		} else {
			nodo.AgregarHijo(NewNodo("MENSAJE", nil, linea))
		}
		return nodo
	}

	panic(&SintaxisError{
		ErrorConLinea: ErrorConLinea{
			Mensaje: "Sintaxis inválida para 'lanzar'",
			Linea:   &linea,
		},
	})
}

// parsearMientras parsea un bucle mientras
func (p *Parser) parsearMientras() *Nodo {
	linea := p.tokenLinea()
	p.esperado(PALABRA_CLAVE) // mientras

	condicion := p.parsearExpresion()

	p.esperado(PUNTOS)

	if p.tokenActual() == nil || p.tokenActual().Tipo != NUEVA_LINEA {
		panic(&SintaxisError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: "Se esperaba un salto de línea después de ':'",
				Linea:   &linea,
			},
		})
	}

	indentacionBloque := indentacionDeToken(p.tokenActual())
	if indentacionBloque < 0 {
		panic(&SintaxisError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: "Se esperaba un salto de línea con indentación después de ':'",
				Linea:   &linea,
			},
		})
	}
	p.esperado(NUEVA_LINEA)

	bloque := []*Nodo{}
	for p.tokenActual() != nil {
		token := p.tokenActual()
		if token.Tipo == NUEVA_LINEA {
			if indentacionDeToken(token) < indentacionBloque {
				break
			}
			p.tokenSiguiente()
			continue
		}
		sent := p.parsearSentencia(nil)
		if sent == nil {
			break
		}
		bloque = append(bloque, sent)
	}

	return NewNodo("MIENTRAS", nil, linea).
		AgregarHijo(condicion).
		AgregarHijo(NewNodo("BLOQUE", nil, linea).AgregarHijo(bloque...))
}

// parsearPara parsea un bucle para
func (p *Parser) parsearPara() *Nodo {
	linea := p.tokenLinea()

	p.esperado(PALABRA_CLAVE) // para

	variableStr := p.esperado(IDENTIFICADOR)
	variableNodo := NewNodo("IDENTIFICADOR", variableStr, linea)

	// Consumir 'en'
	tokenEn := p.tokenActual()
	if tokenEn != nil && tokenEn.Tipo == OPERADOR_LOGICO && tokenEn.Valor == "en" {
		p.tokenSiguiente()
	} else {
		panic(&SintaxisError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: fmt.Sprintf("Se esperaba 'en', pero se encontró %v", tokenEn),
				Linea:   &linea,
			},
		})
	}

	expresionIterable := p.parsearExpresion()

	p.esperado(PUNTOS)

	if p.tokenActual() == nil || p.tokenActual().Tipo != NUEVA_LINEA {
		panic(&SintaxisError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: "Se esperaba un salto de línea después de ':'",
				Linea:   &linea,
			},
		})
	}

	indentacionBloque := indentacionDeToken(p.tokenActual())
	if indentacionBloque < 0 {
		panic(&SintaxisError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: "Se esperaba un salto de línea con indentación después de ':'",
				Linea:   &linea,
			},
		})
	}
	p.esperado(NUEVA_LINEA)

	sentenciasBloque := []*Nodo{}
	for p.tokenActual() != nil {
		token := p.tokenActual()
		if token.Tipo == NUEVA_LINEA {
			if indentacionDeToken(token) < indentacionBloque {
				break
			}
			p.tokenSiguiente()
			continue
		}
		sentencia := p.parsearSentencia(nil)
		if sentencia == nil {
			break
		}
		sentenciasBloque = append(sentenciasBloque, sentencia)
	}

	bloqueNodo := NewNodo("BLOQUE", nil, linea).AgregarHijo(sentenciasBloque...)
	return NewNodo("PARA", nil, linea).
		AgregarHijo(variableNodo).
		AgregarHijo(expresionIterable).
		AgregarHijo(bloqueNodo)
}

// ========== EXPRESIONES ==========

// parsearExpresion parsea una expresión
func (p *Parser) parsearExpresion() *Nodo {
	return p.parsearLogicoOr()
}

// parsearLogicoOr parsea OR lógico
func (p *Parser) parsearLogicoOr() *Nodo {
	left := p.parsearLogicoAnd()
	for p.tokenActual() != nil && p.tokenActual().Tipo == OPERADOR_LOGICO {
		if p.tokenActual().Valor != "o" && p.tokenActual().Valor != "or" {
			break
		}
		opLinea := p.tokenLinea()
		op := p.esperado(OPERADOR_LOGICO)
		right := p.parsearLogicoAnd()
		left = NewNodo("LOGICO", op, opLinea).AgregarHijo(left).AgregarHijo(right)
	}
	return left
}

// parsearLogicoAnd parsea AND lógico
func (p *Parser) parsearLogicoAnd() *Nodo {
	left := p.parsearNot()
	for p.tokenActual() != nil && p.tokenActual().Tipo == OPERADOR_LOGICO {
		if p.tokenActual().Valor != "y" && p.tokenActual().Valor != "and" {
			break
		}
		opLinea := p.tokenLinea()
		op := p.esperado(OPERADOR_LOGICO)
		right := p.parsearNot()
		left = NewNodo("LOGICO", op, opLinea).AgregarHijo(left).AgregarHijo(right)
	}
	return left
}

// parsearNot parsea NOT lógico
func (p *Parser) parsearNot() *Nodo {
	if p.tokenActual() != nil && p.tokenActual().Tipo == OPERADOR_LOGICO {
		if p.tokenActual().Valor == "no" || p.tokenActual().Valor == "not" {
			opLinea := p.tokenLinea()
			op := p.esperado(OPERADOR_LOGICO)
			expr := p.parsearNot()
			return NewNodo("LOGICO", op, opLinea).AgregarHijo(expr)
		}
	}
	return p.parsearIn()
}

// parsearIn parsea el operador IN
func (p *Parser) parsearIn() *Nodo {
	left := p.parsearComparacion()
	if p.tokenActual() != nil && p.tokenActual().Tipo == OPERADOR_LOGICO {
		if p.tokenActual().Valor == "en" || p.tokenActual().Valor == "in" {
			opLinea := p.tokenLinea()
			op := p.esperado(OPERADOR_LOGICO)
			right := p.parsearComparacion()
			return NewNodo("IN", op, opLinea).AgregarHijo(left).AgregarHijo(right)
		}
	}
	return left
}

// parsearComparacion parsea comparaciones
func (p *Parser) parsearComparacion() *Nodo {
	izq := p.parsearSuma()
	for p.tokenActual() != nil && p.tokenActual().Tipo == COMPARADOR {
		opLinea := p.tokenLinea()
		op := p.esperado(COMPARADOR)
		der := p.parsearSuma()
		izq = NewNodo("BINARIA", op, opLinea).AgregarHijo(izq).AgregarHijo(der)
	}
	return izq
}

// parsearSuma parsea suma y resta
func (p *Parser) parsearSuma() *Nodo {
	izq := p.parsearTermino()
	for p.tokenActual() != nil && p.tokenActual().Tipo == OPERADOR {
		if p.tokenActual().Valor != "+" && p.tokenActual().Valor != "-" {
			break
		}
		opLinea := p.tokenLinea()
		op := p.esperado(OPERADOR)
		der := p.parsearTermino()
		izq = NewNodo("BINARIA", op, opLinea).AgregarHijo(izq).AgregarHijo(der)
	}
	return izq
}

// parsearTermino parsea multiplicación, división y módulo
func (p *Parser) parsearTermino() *Nodo {
	izq := p.parsearFactor()
	for p.tokenActual() != nil && p.tokenActual().Tipo == OPERADOR {
		if p.tokenActual().Valor != "*" && p.tokenActual().Valor != "/" && p.tokenActual().Valor != "%" {
			break
		}
		opLinea := p.tokenLinea()
		op := p.esperado(OPERADOR)
		der := p.parsearFactor()
		izq = NewNodo("BINARIA", op, opLinea).AgregarHijo(izq).AgregarHijo(der)
	}
	return izq
}

// parsearFactor parsea factores (operadores unarios y átomos)
func (p *Parser) parsearFactor() *Nodo {
	token := p.tokenActual()
	if token != nil && token.Tipo == OPERADOR && (token.Valor == "-" || token.Valor == "+") {
		linea := p.tokenLinea()
		op := p.esperado(OPERADOR)
		operando := p.parsearFactor()
		if op == "+" {
			return operando
		}
		return NewNodo("UNARIA", op, linea).AgregarHijo(operando)
	}

	nodo := p.parsearAtomo()
	return p.parsearPostfijos(nodo)
}

// parsearPostfijos parsea postfijos (atributos, índices, llamadas)
func (p *Parser) parsearPostfijos(nodo *Nodo) *Nodo {
	for {
		token := p.tokenActual()
		if token == nil {
			break
		}

		if token.Tipo == PUNTO {
			linea := nodo.Linea
			p.esperado(PUNTO)
			tokenAtributo := p.tokenActual()
			var atributo string
			if tokenAtributo != nil && tokenAtributo.Tipo == IDENTIFICADOR {
				atributo = p.esperado(IDENTIFICADOR)
			} else if tokenAtributo != nil && tokenAtributo.Tipo == PALABRA_CLAVE {
				atributo = p.esperado(PALABRA_CLAVE)
			} else {
				panic(&SintaxisError{
					ErrorConLinea: ErrorConLinea{
						Mensaje: fmt.Sprintf("Se esperaba identificador después de '.', pero encontró %v", tokenAtributo),
						Linea:   &linea,
					},
				})
			}

			if p.tokenActual() != nil && p.tokenActual().Tipo == PARENTESIS && p.tokenActual().Valor == "(" {
				p.esperado(PARENTESIS)
				argumentos := []*Nodo{nodo}
				if p.tokenActual() != nil && !(p.tokenActual().Tipo == PARENTESIS && p.tokenActual().Valor == ")") {
					argumentos = append(argumentos, p.parsearArgumento())
					for p.tokenActual() != nil && p.tokenActual().Tipo == COMA {
						p.esperado(COMA)
						argumentos = append(argumentos, p.parsearArgumento())
					}
				}
				p.esperado(PARENTESIS)
				nodo = NewNodo("LLAMADA_METODO", atributo, linea)
				for _, arg := range argumentos {
					nodo.AgregarHijo(arg)
				}
			} else {
				nodo = NewNodo("ACCESO_ATRIBUTO", atributo, linea).AgregarHijo(nodo)
			}

		} else if token.Tipo == CORCHETE && token.Valor == "[" {
			linea := nodo.Linea
			p.esperado(CORCHETE)
			indice := p.parsearExpresion()
			p.esperado(CORCHETE)
			nodo = NewNodo("INDEXACION", nil, linea).AgregarHijo(nodo).AgregarHijo(indice)

		} else {
			break
		}
	}

	return nodo
}

// parsearAtomo parsea un átomo (literal, variable, etc.)
func (p *Parser) parsearAtomo() *Nodo {
	token := p.tokenActual()
	if token == nil {
		return nil
	}

	linea := token.Linea

	switch token.Tipo {
	case ENTERO:
		valor := p.esperado(ENTERO)
		return NewNodo("ENTERO", valor, linea)

	case DECIMAL:
		valor := p.esperado(DECIMAL)
		return NewNodo("DECIMAL", valor, linea)

	case CADENA_INTERPOLADA:
		valor := p.esperado(CADENA_INTERPOLADA)
		return NewNodo("CADENA_INTERPOLADA", valor[2:len(valor)-1], linea)

	case CADENA_TEXTO:
		valor := p.esperado(CADENA_TEXTO)
		return NewNodo("CADENA_TEXTO", valor[1:len(valor)-1], linea)

	case NINGUNO:
		p.esperado(NINGUNO)
		return NewNodo("NINGUNO", nil, linea)

	case BOOLEANO:
		valor := p.esperado(BOOLEANO)
		boolVal := valor == "true" || valor == "verdadero"
		return NewNodo("BOOLEANO", boolVal, linea)
	case OPERADOR_ASIGNACION:
		p.esperado(OPERADOR_ASIGNACION)
		return NewNodo("OPERADOR_ASIGNACION", nil, linea)

	case PALABRA_CLAVE:
		valor := token.Valor
		// Llamada a función
		if p.tokenSiguientePeek() != nil && p.tokenSiguientePeek().Tipo == PARENTESIS && p.tokenSiguientePeek().Valor == "(" {
			p.esperado(PALABRA_CLAVE)
			p.esperado(PARENTESIS)
			argumentos := []*Nodo{}
			if p.tokenActual() != nil && !(p.tokenActual().Tipo == PARENTESIS && p.tokenActual().Valor == ")") {
				argumentos = append(argumentos, p.parsearArgumento())
				for p.tokenActual() != nil && p.tokenActual().Tipo == COMA {
					p.esperado(COMA)
					argumentos = append(argumentos, p.parsearArgumento())
				}
			}
			p.esperado(PARENTESIS)
			return NewNodo("LLAMADA", valor, linea).AgregarHijo(argumentos...)
		}
		return NewNodo("IDENTIFICADOR", valor, linea)

	case IDENTIFICADOR:
		valor := token.Valor
		// Llamada a función
		if p.tokenSiguientePeek() != nil && p.tokenSiguientePeek().Tipo == PARENTESIS && p.tokenSiguientePeek().Valor == "(" {
			p.esperado(IDENTIFICADOR)
			p.esperado(PARENTESIS)
			argumentos := []*Nodo{}
			if p.tokenActual() != nil && !(p.tokenActual().Tipo == PARENTESIS && p.tokenActual().Valor == ")") {
				argumentos = append(argumentos, p.parsearArgumento())
				for p.tokenActual() != nil && p.tokenActual().Tipo == COMA {
					p.esperado(COMA)
					argumentos = append(argumentos, p.parsearArgumento())
				}
			}
			p.esperado(PARENTESIS)
			return NewNodo("LLAMADA", valor, linea).AgregarHijo(argumentos...)
		}
		p.esperado(IDENTIFICADOR)
		return NewNodo("IDENTIFICADOR", valor, linea)

	case CORCHETE:
		if token.Valor == "[" {
			p.esperado(CORCHETE)
			elementos := []*Nodo{}
			p.saltarNuevasLineas()
			if p.tokenActual() != nil && !(p.tokenActual().Tipo == CORCHETE && p.tokenActual().Valor == "]") {
				for {
					elementos = append(elementos, p.parsearExpresion())
					p.saltarNuevasLineas()

					if p.tokenActual() == nil || p.tokenActual().Tipo != COMA {
						break
					}
					p.esperado(COMA)
					p.saltarNuevasLineas()

					// Soporta coma final antes de ']'.
					if p.tokenActual() != nil && p.tokenActual().Tipo == CORCHETE && p.tokenActual().Valor == "]" {
						break
					}
				}
			}
			p.esperado(CORCHETE)
			return NewNodo("LISTA", nil, linea).AgregarHijo(elementos...)
		}

	case LLAVE:
		if token.Valor == "{" {
			p.esperado(LLAVE)
			pares := []*Nodo{}
			p.saltarNuevasLineas()
			if p.tokenActual() != nil && !(p.tokenActual().Tipo == LLAVE && p.tokenActual().Valor == "}") {
				for {
					clave := p.parsearExpresion()
					p.saltarNuevasLineas()
					p.esperado(PUNTOS)
					p.saltarNuevasLineas()

					valor := p.parsearExpresion()
					par := NewNodo("PAR", nil, linea).AgregarHijo(clave).AgregarHijo(valor)
					pares = append(pares, par)
					p.saltarNuevasLineas()

					if p.tokenActual() == nil || p.tokenActual().Tipo != COMA {
						break
					}
					p.esperado(COMA)
					p.saltarNuevasLineas()

					// Soporta coma final antes de '}'.
					if p.tokenActual() != nil && p.tokenActual().Tipo == LLAVE && p.tokenActual().Valor == "}" {
						break
					}
				}
			}
			p.esperado(LLAVE)
			return NewNodo("DICCIONARIO", nil, linea).AgregarHijo(pares...)
		}

	case PARENTESIS:
		if token.Valor == "(" {
			p.esperado(PARENTESIS)
			expr := p.parsearExpresion()
			p.esperado(PARENTESIS)
			return expr
		}
	}

	panic(&SintaxisError{
		ErrorConLinea: ErrorConLinea{
			Mensaje: fmt.Sprintf("Factor inesperado: %v", token),
			Linea:   &linea,
		},
	})
}
