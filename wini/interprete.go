package wini

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
)

// Interprete es el intérprete principal del lenguaje wini
type Interprete struct {
	Archivo        string
	Directorio     string
	Variables      map[string]interface{}
	Funciones      map[string]interface{}
	Paquetes       map[string]interface{}
	DefaultPaquete interface{}
	Evaluador      *Evaluador
	Ejecutor       *Ejecutor
	Lexer          *Lexer

	// Cache de módulos ya importados
	cacheModulos   map[string]interface{}
	pilaImportando []string
	dispatch       map[string]func(*Nodo)
}

// NewInterprete crea un nuevo intérprete
func NewInterprete(archivo string, cacheModulos map[string]interface{}, pilaImportando []string) *Interprete {
	if cacheModulos == nil {
		cacheModulos = make(map[string]interface{})
	}
	if pilaImportando == nil {
		pilaImportando = []string{}
	}

	absArchivo, _ := filepath.Abs(archivo)
	directorio := filepath.Dir(absArchivo)

	i := &Interprete{
		Archivo:        absArchivo,
		Directorio:     directorio,
		Variables:      make(map[string]interface{}),
		Funciones:      make(map[string]interface{}),
		Paquetes:       make(map[string]interface{}),
		cacheModulos:   cacheModulos,
		pilaImportando: pilaImportando,
	}

	// Funciones nativas
	i.Funciones["rango"] = i.rangoNativo

	// Crear evaluador y ejecutor
	i.Evaluador = NewEvaluador(i)
	i.Ejecutor = NewEjecutor(i)
	i.Lexer = NewLexer()

	// Tabla de despacho
	i.dispatch = map[string]func(*Nodo){
		"PROGRAMA":         i.intPrograma,
		"MIENTRAS":         i.ejecutarMientras,
		"PARA":             i.ejecutarPara,
		"ROMPER":           i.intRomper,
		"CONTINUAR":        i.intContinuar,
		"ASIGNACION":       i.intAsignacion,
		"ASIGNACION_INDEX": i.ejecutarAsignacionIndex,
		"LLAMADA":          i.intLlamada,
		"LLAMADA_METODO":   i.intLlamadaMetodo,
		"RETORNO":          i.intRetorno,
		"INTENTAR":         i.ejecutarIntentar,
		"LANZAR":           i.ejecutarLanzar,
		"IMPORTAR":         i.ejecutarImportar,
		"FUNCION":          i.definirFuncion,
		"SI":               i.ejecutarSi,
	}

	return i
}

// Ejecutar lee y ejecuta el archivo
func (i *Interprete) Ejecutar() error {
	file, err := os.Open(i.Archivo)
	if err != nil {
		return fmt.Errorf("Error: El archivo '%s' no existe", i.Archivo)
	}
	defer file.Close()

	contenido, err := io.ReadAll(file)
	if err != nil {
		return err
	}

	tokens := i.Lexer.Tokenize(string(contenido))
	parser := NewParser(tokens)
	ast := parser.Parse()
	i.Interpretar(ast)

	return nil
}

// MostrarError muestra un error con información de línea y código
func (i *Interprete) MostrarError(e *ErrorConLinea) {
	fmt.Printf("Error: %s\n", e.Mensaje)
	if e.Linea != nil {
		fmt.Printf("  Línea %d", *e.Linea)
		if e.Columna != nil {
			fmt.Printf(", columna %d", *e.Columna)
		}
		fmt.Println()
		if e.Texto != "" {
			fmt.Printf("  %s\n", e.Texto)
		} else {
			// Intentar leer la línea del archivo
			content, err := os.ReadFile(i.Archivo)
			if err == nil {
				lines := strings.Split(string(content), "\n")
				if *e.Linea >= 1 && *e.Linea <= len(lines) {
					fmt.Printf("  %s\n", lines[*e.Linea-1])
				}
			}
		}
	}
}

// NormalizarIterable convierte cualquier objeto a un iterable estándar
func (i *Interprete) NormalizarIterable(iterable interface{}, linea int) []interface{} {
	if iterable == nil {
		panic(&RuntimeError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: "No se puede iterar sobre 'ninguno'",
				Linea:   &linea,
			},
		})
	}
	switch v := iterable.(type) {
	case []interface{}:
		return v
	case string:
		resultado := make([]interface{}, len(v))
		for idx, r := range v {
			resultado[idx] = string(r)
		}
		return resultado
	case map[string]interface{}:
		resultado := make([]interface{}, 0, len(v))
		for k := range v {
			resultado = append(resultado, k)
		}
		return resultado
	default:
		// Intentar convertir usando reflexión
		val := reflect.ValueOf(iterable)
		if val.Kind() == reflect.Slice || val.Kind() == reflect.Array {
			resultado := make([]interface{}, val.Len())
			for i := 0; i < val.Len(); i++ {
				resultado[i] = val.Index(i).Interface()
			}
			return resultado
		}
		tipoNombre := "ninguno"
		if t := reflect.TypeOf(iterable); t != nil {
			tipoNombre = t.Name()
		}
		panic(&RuntimeError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: fmt.Sprintf("No se puede iterar sobre '%s'", tipoNombre),
				Linea:   &linea,
			},
		})
	}
}

// Interpretar interpreta un nodo del AST
func (i *Interprete) Interpretar(nodo *Nodo) {
	if nodo == nil {
		return
	}
	manejador, ok := i.dispatch[nodo.Tipo]
	if ok {
		manejador(nodo)
	}
}

// ========== MANEJADORES ==========

func (i *Interprete) intPrograma(nodo *Nodo) {
	for _, hijo := range nodo.Hijos {
		i.Interpretar(hijo)
	}
}

func (i *Interprete) intRomper(nodo *Nodo) {
	panic(&RomperException{})
}

func (i *Interprete) intContinuar(nodo *Nodo) {
	panic(&ContinuarException{})
}

func (i *Interprete) intAsignacion(nodo *Nodo) {
	valor := i.Evaluador.Evaluar(nodo.Hijos[0])
	i.Variables[nodo.Valor.(string)] = valor
}

func (i *Interprete) intLlamada(nodo *Nodo) {
	i.Ejecutor.EjecutarFuncion(nodo)
}

func (i *Interprete) intLlamadaMetodo(nodo *Nodo) {
	i.Ejecutor.EjecutarMetodo(nodo)
}

func (i *Interprete) intRetorno(nodo *Nodo) {
	valor := i.Evaluador.Evaluar(nodo.Hijos[0])
	panic(&RetornoException{Valor: valor})
}

// ========== EJECUCIÓN DE ESTRUCTURAS ==========

func (i *Interprete) ejecutarMientras(nodo *Nodo) {
	condicionNodo := nodo.Hijos[0]
	bloqueNodo := nodo.Hijos[1]

	for {
		resultadoCondicion := i.Evaluador.Evaluar(condicionNodo)
		if !EsVerdadero(resultadoCondicion) {
			break
		}

		debeRomper := func() (debeRomper bool) {
			defer func() {
				if r := recover(); r != nil {
					if _, ok := r.(*RomperException); ok {
						debeRomper = true
						return
					}
					if _, ok := r.(*ContinuarException); ok {
						return
					}
					panic(r)
				}
			}()
			for _, sentencia := range bloqueNodo.Hijos {
				i.Interpretar(sentencia)
			}
			return false
		}()

		if debeRomper {
			break
		}
	}
}

func (i *Interprete) ejecutarPara(nodo *Nodo) {
	variableNombre := nodo.Hijos[0].Valor.(string)
	iterableEvaluado := i.Evaluador.Evaluar(nodo.Hijos[1])
	bloqueSentencias := nodo.Hijos[2]

	// Convertir a slice para iterar
	iterable := i.NormalizarIterable(iterableEvaluado, nodo.Linea)

	for _, elemento := range iterable {
		i.Variables[variableNombre] = elemento

		debeRomper := func() (debeRomper bool) {
			defer func() {
				if r := recover(); r != nil {
					if _, ok := r.(*RomperException); ok {
						debeRomper = true
						return
					}
					if _, ok := r.(*ContinuarException); ok {
						return
					}
					panic(r)
				}
			}()
			for _, sentencia := range bloqueSentencias.Hijos {
				i.Interpretar(sentencia)
			}
			return false
		}()

		if debeRomper {
			break
		}
	}
}

func (i *Interprete) ejecutarAsignacionIndex(nodo *Nodo) {
	variable := nodo.Valor.(string)
	if _, ok := i.Variables[variable]; !ok {
		panic(&RuntimeError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: fmt.Sprintf("Variable '%s' no definida", variable),
				Linea:   &nodo.Linea,
			},
		})
	}

	objeto := i.Variables[variable]
	indice := i.Evaluador.Evaluar(nodo.Hijos[0])
	valor := i.Evaluador.Evaluar(nodo.Hijos[1])

	switch obj := objeto.(type) {
	case []interface{}:
		idx, ok := indice.(int)
		if !ok {
			panic(&RuntimeError{
				ErrorConLinea: ErrorConLinea{
					Mensaje: "Índice de lista debe ser entero",
					Linea:   &nodo.Linea,
				},
			})
		}
		if idx < 0 || idx >= len(obj) {
			panic(&RuntimeError{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("Índice %d fuera de rango para lista de tamaño %d", idx, len(obj)),
					Linea:   &nodo.Linea,
				},
			})
		}
		obj[idx] = valor
		i.Variables[variable] = obj

	case map[string]interface{}:
		clave := FormatearTexto(indice)
		obj[clave] = valor
		i.Variables[variable] = obj

	default:
		panic(&RuntimeError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: fmt.Sprintf("No se puede indexar asignación sobre tipo %T", objeto),
				Linea:   &nodo.Linea,
			},
		})
	}
}

func (i *Interprete) definirFuncion(nodo *Nodo) {
	parametros := []string{}
	// predeterminados[idx] contiene el nodo de expresión del valor por
	// defecto del parámetro en esa posición, o nil si no tiene uno.
	predeterminados := []*Nodo{}
	if len(nodo.Hijos) > 0 && nodo.Hijos[0].Tipo == "PARAMETROS" {
		for _, param := range nodo.Hijos[0].Hijos {
			if param.Tipo == "PARAM" {
				parametros = append(parametros, param.Valor.(string))
				if len(param.Hijos) > 0 {
					predeterminados = append(predeterminados, param.Hijos[0])
				} else {
					predeterminados = append(predeterminados, nil)
				}
			}
		}
	}

	cuerpo := []*Nodo{}
	if len(nodo.Hijos) > 1 && nodo.Hijos[1].Tipo == "CUERPO" {
		cuerpo = nodo.Hijos[1].Hijos
	}

	i.Funciones[nodo.Valor.(string)] = map[string]interface{}{
		"parametros":      parametros,
		"predeterminados": predeterminados,
		"cuerpo":          cuerpo,
		"docstring":       "", // En Go no tenemos docstring directamente
	}
}

func (i *Interprete) ejecutarSi(nodo *Nodo) {
	condicion := i.Evaluador.Evaluar(nodo.Hijos[0])
	if EsVerdadero(condicion) {
		if len(nodo.Hijos) > 1 && nodo.Hijos[1].Tipo == "BLOQUE_SI" {
			for _, sentencia := range nodo.Hijos[1].Hijos {
				i.Interpretar(sentencia)
			}
		}
	} else {
		if len(nodo.Hijos) > 2 && nodo.Hijos[2].Tipo == "BLOQUE_SINO" {
			for _, sentencia := range nodo.Hijos[2].Hijos {
				i.Interpretar(sentencia)
			}
		}
	}
}

func (i *Interprete) ejecutarIntentar(nodo *Nodo) {
	bloqueTry := nodo.Hijos[0]
	bloquesCapturar := nodo.Hijos[1]
	bloqueFinally := nodo.Hijos[2]

	var err error
	var lanzarErr *LanzarException

	// Ejecutar el bloque try en un cierre propio: así el recover() solo
	// interrumpe ESE cierre y la función principal puede seguir buscando
	// un bloque 'capturar' que coincida (si el recover estuviera en un
	// defer de esta misma función, al recuperar el pánico la función
	// terminaría de inmediato sin llegar a ese código).
	func() {
		defer func() {
			if r := recover(); r != nil {
				if e, ok := r.(*LanzarException); ok {
					lanzarErr = e
					err = e
				} else if e, ok := r.(error); ok {
					err = e
				} else {
					err = fmt.Errorf("%v", r)
				}
			}
		}()
		for _, sentencia := range bloqueTry.Hijos {
			i.Interpretar(sentencia)
		}
	}()

	// El bloque finally debe ejecutarse siempre al salir, incluso si el
	// bloque capturar (o la ausencia de uno) provoca otro panic
	defer func() {
		for _, sentencia := range bloqueFinally.Hijos {
			i.Interpretar(sentencia)
		}
	}()

	// Si no hubo error, salir
	if err == nil && lanzarErr == nil {
		return
	}

	// Buscar bloque capturar que coincida
	errorManejado := false

	// Determinar el mensaje del error
	mensajeError := ""
	if lanzarErr != nil {
		mensajeError = fmt.Sprintf("%v", lanzarErr.Valor)
	} else if err != nil {
		mensajeError = err.Error()
	}

	for _, capturar := range bloquesCapturar.Hijos {
		tipoError := capturar.Valor
		variableError := ""
		if len(capturar.Hijos) > 0 && capturar.Hijos[0] != nil {
			variableError = capturar.Hijos[0].Valor.(string)
		}
		bloqueCapturar := capturar.Hijos[1]

		if tipoError == nil || tipoError == "" || i.errorCoincide(err, tipoError.(string)) || i.errorCoincideLanzar(lanzarErr, tipoError.(string)) {
			errorManejado = true

			// Aplicar scope temporal con la variable de error
			cambios := make(map[string]interface{})
			if variableError != "" {
				cambios[variableError] = mensajeError
			}
			revertir := i.Ejecutor.AplicarScopeTemporal(cambios)

			func() {
				defer revertir()
				for _, sentencia := range bloqueCapturar.Hijos {
					i.Interpretar(sentencia)
				}
			}()

			break
		}
	}

	if !errorManejado {
		if lanzarErr != nil {
			panic(lanzarErr)
		}
		if err != nil {
			panic(err)
		}
	}
}

func (i *Interprete) errorCoincide(err error, tipoNombre string) bool {
	tipos := map[string]reflect.Type{
		"ErrorTipo":        reflect.TypeOf(&ErrorTipo{}),
		"ErrorValor":       reflect.TypeOf(&ErrorValor{}),
		"ErrorIndice":      reflect.TypeOf(&ErrorIndice{}),
		"ErrorAtributo":    reflect.TypeOf(&ErrorAtributo{}),
		"ErrorImportacion": reflect.TypeOf(&ErrorImportacion{}),
		"ErrorMatematico":  reflect.TypeOf(&ErrorMatematico{}),
		"RuntimeError":     reflect.TypeOf(&RuntimeError{}),
	}

	if tipo, ok := tipos[tipoNombre]; ok {
		return reflect.TypeOf(err) == tipo || reflect.TypeOf(err).AssignableTo(tipo)
	}
	return false
}

func (i *Interprete) errorCoincideLanzar(err *LanzarException, tipoNombre string) bool {
	if err == nil {
		return false
	}
	tipos := map[string]bool{
		"ErrorTipo":        true,
		"ErrorValor":       true,
		"ErrorIndice":      true,
		"ErrorAtributo":    true,
		"ErrorImportacion": true,
		"ErrorMatematico":  true,
		"RuntimeError":     true,
	}
	return tipos[tipoNombre]
}

func (i *Interprete) ejecutarLanzar(nodo *Nodo) {
	tipoError := ""
	if len(nodo.Hijos) > 0 && nodo.Hijos[0] != nil {
		if v, ok := nodo.Hijos[0].Valor.(string); ok {
			tipoError = v
		}
	}

	mensaje := ""
	if len(nodo.Hijos) > 1 && nodo.Hijos[1] != nil && len(nodo.Hijos[1].Hijos) > 0 {
		mensaje = FormatearTexto(i.Evaluador.Evaluar(nodo.Hijos[1].Hijos[0]))
	}

	erroresMap := map[string]func(string) error{
		"ErrorTipo":        func(m string) error { return &ErrorTipo{ErrorConLinea: ErrorConLinea{Mensaje: m}} },
		"ErrorValor":       func(m string) error { return &ErrorValor{ErrorConLinea: ErrorConLinea{Mensaje: m}} },
		"ErrorIndice":      func(m string) error { return &ErrorIndice{ErrorConLinea: ErrorConLinea{Mensaje: m}} },
		"ErrorAtributo":    func(m string) error { return &ErrorAtributo{ErrorConLinea: ErrorConLinea{Mensaje: m}} },
		"ErrorImportacion": func(m string) error { return &ErrorImportacion{ErrorConLinea: ErrorConLinea{Mensaje: m}} },
		"ErrorMatematico":  func(m string) error { return &ErrorMatematico{ErrorConLinea: ErrorConLinea{Mensaje: m}} },
		"RuntimeError":     func(m string) error { return &RuntimeError{ErrorConLinea: ErrorConLinea{Mensaje: m}} },
	}

	if tipoError != "" {
		if fn, ok := erroresMap[tipoError]; ok {
			panic(fn(mensaje))
		}
		panic(&RuntimeError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: fmt.Sprintf("%s: %s", tipoError, mensaje),
				Linea:   &nodo.Linea,
			},
		})
	}

	panic(&RuntimeError{
		ErrorConLinea: ErrorConLinea{
			Mensaje: mensaje,
			Linea:   &nodo.Linea,
		},
	})
}

// ========== IMPORTACIÓN DE MÓDULOS ==========

func (i *Interprete) ejecutarImportar(nodo *Nodo) {
	nombreModulo := nodo.Valor.(string)
	alias := nombreModulo
	if len(nodo.Hijos) > 0 && nodo.Hijos[0] != nil {
		if v, ok := nodo.Hijos[0].Valor.(string); ok && v != "" {
			alias = v
		} else {
			partes := strings.Split(nombreModulo, ".")
			alias = partes[len(partes)-1]
		}
	}

	rutaModulo := i.resolverRutaModulo(nombreModulo, nodo.Linea)

	// Verificar importación circular
	for _, r := range i.pilaImportando {
		if r == rutaModulo {
			ciclo := strings.Join(append(i.pilaImportando, rutaModulo), " -> ")
			panic(&ErrorImportacion{
				ErrorConLinea: ErrorConLinea{
					Mensaje: fmt.Sprintf("Importación circular detectada: %s", ciclo),
					Linea:   &nodo.Linea,
				},
			})
		}
	}

	if _, ok := i.cacheModulos[rutaModulo]; !ok {
		i.pilaImportando = append(i.pilaImportando, rutaModulo)
		i.cacheModulos[rutaModulo] = i.cargarModulo(rutaModulo, nodo.Linea)
		i.pilaImportando = i.pilaImportando[:len(i.pilaImportando)-1]
	}

	i.Variables[alias] = i.cacheModulos[rutaModulo]
}

func (i *Interprete) buscarCandidatoEn(base string, partes []string) string {
	if base == "" {
		return ""
	}

	rutaDirecta := filepath.Join(append([]string{base}, partes...)...)

	// Las rutas entre comillas pueden incluir una extensión (por ejemplo,
	// importar "mi_modulo.dll"). En ese caso no se debe tratar el punto como
	// separador de paquetes ni añadir una segunda extensión.
	if ext := filepath.Ext(rutaDirecta); ext != "" {
		if info, err := os.Stat(rutaDirecta); err == nil && !info.IsDir() {
			abs, _ := filepath.Abs(rutaDirecta)
			return abs
		}
	}

	extensiones := []string{".wn", ".go", ".dll", ".so", ".dylib"}

	for _, ext := range extensiones {
		candidato := rutaDirecta + ext
		if _, err := os.Stat(candidato); err == nil {
			abs, _ := filepath.Abs(candidato)
			return abs
		}
	}

	if len(partes) > 1 {
		rutaPaquete := filepath.Join(append([]string{base}, partes[:len(partes)-1]...)...)
		rutaPaquete = filepath.Join(rutaPaquete, partes[len(partes)-1])
		for _, ext := range extensiones {
			candidato := rutaPaquete + ext
			if _, err := os.Stat(candidato); err == nil {
				abs, _ := filepath.Abs(candidato)
				return abs
			}
		}
	}

	return ""
}

func (i *Interprete) resolverRutaModulo(nombreModulo string, linea int) string {
	partes := strings.Split(nombreModulo, ".")
	// Un nombre con extensión de biblioteca es una ruta de archivo, no un
	// módulo punteado. Así, "os.dll" se busca como os.dll y no como os/dll.
	switch strings.ToLower(filepath.Ext(nombreModulo)) {
	case ".dll", ".so", ".dylib", ".wn", ".go":
		partes = []string{nombreModulo}
	}

	// 1) Resolución LOCAL
	basesLocales := []string{i.Directorio}
	cwd, _ := os.Getwd()
	basesLocales = append(basesLocales, cwd)

	for _, base := range basesLocales {
		if encontrado := i.buscarCandidatoEn(base, partes); encontrado != "" {
			return encontrado
		}
	}

	// 2) Buscar en librerias/
	ejecutable, _ := os.Executable()
	carpetaEjecutable := filepath.Dir(ejecutable)

	bases := []string{
		i.Directorio,
		cwd,
		carpetaEjecutable,
	}

	for _, base := range bases {
		if base == "" {
			continue
		}
		rutaLibrerias := filepath.Join(base, "librerias")
		if encontrado := i.buscarCandidatoEn(rutaLibrerias, partes); encontrado != "" {
			return encontrado
		}
	}

	panic(&ErrorImportacion{
		ErrorConLinea: ErrorConLinea{
			Mensaje: fmt.Sprintf("No se pudo encontrar el módulo '%s'", nombreModulo),
			Linea:   &linea,
		},
	})
}

// En interprete.go, modificar cargarModulo
func (i *Interprete) cargarModulo(ruta string, linea int) interface{} {
	ext := filepath.Ext(ruta)

	// Si es una DLL (Windows), .so (Linux) o .dylib (macOS)
	if ext == ".dll" || ext == ".so" || ext == ".dylib" {
		return i.CargarModuloNativo(ruta, linea)
	}

	if ext == ".go" {
		return i.cargarModuloNativo(ruta, linea)
	}

	return i.cargarModuloWini(ruta, linea)
}

func (i *Interprete) cargarModuloNativo(ruta string, linea int) interface{} {
	nombreMod := strings.TrimSuffix(filepath.Base(ruta), filepath.Ext(ruta))

	// Intentar cargar como paquete Go
	// En una implementación real, aquí se cargaría un .so o .dll
	// Para este ejemplo, simulamos un módulo nativo

	return map[string]interface{}{
		"_tipo":     "modulo",
		"_ruta":     ruta,
		"_nombre":   nombreMod,
		"_nativo":   true,
		"funciones": map[string]interface{}{},
		"variables": map[string]interface{}{},
	}
}

func (i *Interprete) cargarModuloWini(ruta string, linea int) interface{} {
	content, err := os.ReadFile(ruta)
	if err != nil {
		panic(&ErrorImportacion{
			ErrorConLinea: ErrorConLinea{
				Mensaje: fmt.Sprintf("No se pudo leer el módulo '%s': %v", ruta, err),
				Linea:   &linea,
			},
		})
	}

	subInterprete := NewInterprete(ruta, i.cacheModulos, i.pilaImportando)

	// Tokenizar y parsear
	tokens := i.Lexer.Tokenize(string(content))
	parser := NewParser(tokens)
	ast := parser.Parse()

	// Ejecutar el módulo
	defer func() {
		if r := recover(); r != nil {
			if e, ok := r.(*ErrorConLinea); ok {
				panic(&ErrorImportacion{
					ErrorConLinea: ErrorConLinea{
						Mensaje: fmt.Sprintf("Error al importar '%s': %s", filepath.Base(ruta), e.Mensaje),
						Linea:   &linea,
					},
				})
			}
			panic(r)
		}
	}()

	subInterprete.Interpretar(ast)

	// Copiar variables del módulo
	moduloVars := make(map[string]interface{})
	for k, v := range subInterprete.Variables {
		moduloVars[k] = v
	}

	// Copiar funciones del módulo
	funcionesModulo := make(map[string]interface{})
	for k, v := range subInterprete.Funciones {
		if k != "rango" {
			if fnMap, ok := v.(map[string]interface{}); ok {
				// Agregar variables del módulo a la función
				fnMap["_modulo_variables"] = moduloVars
				funcionesModulo[k] = fnMap
			} else {
				funcionesModulo[k] = v
			}
		}
	}

	// Segunda pasada: adjuntar también el conjunto de funciones del módulo a
	// cada función. Así, si una función del módulo llama a otra función
	// definida en el mismo archivo por su nombre simple (sin el prefijo del
	// alias, p. ej. "serializar(...)" en lugar de "json.serializar(...)"),
	// el intérprete puede resolverla igual que lo haría dentro del propio
	// archivo del módulo.
	for _, v := range funcionesModulo {
		if fnMap, ok := v.(map[string]interface{}); ok {
			fnMap["_modulo_funciones"] = funcionesModulo
		}
	}

	return map[string]interface{}{
		"_tipo":     "modulo",
		"_ruta":     ruta,
		"_nombre":   strings.TrimSuffix(filepath.Base(ruta), ".wn"),
		"funciones": funcionesModulo,
		"variables": moduloVars,
	}
}

// ========== FUNCIONES NATIVAS ==========

func (i *Interprete) rangoNativo(args ...interface{}) interface{} {
	if len(args) == 0 {
		panic(&RuntimeError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: "rango() espera entre 1 y 3 argumentos",
			},
		})
	}

	convertir := func(v interface{}) int {
		switch val := v.(type) {
		case int:
			return val
		case float64:
			return int(val)
		case string:
			if n, err := strconv.Atoi(val); err == nil {
				return n
			}
		}
		panic(&RuntimeError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: "Los argumentos de rango() deben ser números",
			},
		})
	}

	resultado := []interface{}{}

	switch len(args) {
	case 1:
		fin := convertir(args[0])
		for i := 0; i < fin; i++ {
			resultado = append(resultado, i)
		}
	case 2:
		inicio := convertir(args[0])
		fin := convertir(args[1])
		for i := inicio; i < fin; i++ {
			resultado = append(resultado, i)
		}
	case 3:
		inicio := convertir(args[0])
		fin := convertir(args[1])
		paso := convertir(args[2])
		if paso == 0 {
			panic(&RuntimeError{
				ErrorConLinea: ErrorConLinea{
					Mensaje: "rango() paso no puede ser cero",
				},
			})
		}
		if paso > 0 {
			for i := inicio; i < fin; i += paso {
				resultado = append(resultado, i)
			}
		} else {
			for i := inicio; i > fin; i += paso {
				resultado = append(resultado, i)
			}
		}
	default:
		panic(&RuntimeError{
			ErrorConLinea: ErrorConLinea{
				Mensaje: "rango() espera entre 1 y 3 argumentos",
			},
		})
	}

	return resultado
}

// ========== FUNCIONES AUXILIARES ==========

// LeerEntrada lee una línea de entrada del usuario
func LeerEntrada() string {
	reader := bufio.NewReader(os.Stdin)
	texto, _ := reader.ReadString('\n')
	return strings.TrimRight(texto, "\r\n")
}

// LeerEntradaConPrompt lee una línea con un prompt
func LeerEntradaConPrompt(prompt string) string {
	fmt.Print(prompt)
	return LeerEntrada()
}
