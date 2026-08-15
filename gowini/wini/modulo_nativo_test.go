package wini

import (
	"reflect"
	"testing"
	"unsafe"
)

func TestParserIntentarCapturar(t *testing.T) {
	codigo := "intentar:\n    a = 1\ncapturar(ErrorTipo) como e:\n    escribir(e)\nfinalmente:\n    escribir(\"fin\")\n"
	parser := NewParser(NewLexer().Tokenize(codigo))
	ast := parser.Parse()
	if ast == nil {
		t.Fatal("el AST no debe ser nil")
	}
	if ast.Tipo != "PROGRAMA" {
		t.Fatalf("se esperaba PROGRAMA, se obtuvo %s", ast.Tipo)
	}
}

type WiniDiccionarioPrueba struct {
	Longitud int32
	_        [4]byte
	Claves   uintptr
	Valores  uintptr
}

type WiniListaPrueba struct {
	Longitud  int32
	_         [4]byte
	Elementos uintptr
}

func TestAccesoAtributoEnMapa(t *testing.T) {
	interprete := NewInterprete("", nil, nil)
	interprete.Variables["info"] = map[string]interface{}{
		"size":   123,
		"exists": true,
	}

	evaluador := NewEvaluador(interprete)
	nodo := &Nodo{
		Tipo:  "ACCESO_ATRIBUTO",
		Valor: "size",
		Hijos: []*Nodo{{
			Tipo:  "IDENTIFICADOR",
			Valor: "info",
		}},
	}

	got := evaluador.Evaluar(nodo)
	if got != 123 {
		t.Fatalf("se esperaba 123, se obtuvo %#v", got)
	}
}

func TestCValorToGoDiccionario(t *testing.T) {
	claveSize := []byte("size\x00")
	claveExists := []byte("exists\x00")
	claves := []uintptr{uintptr(unsafe.Pointer(&claveSize[0])), uintptr(unsafe.Pointer(&claveExists[0]))}
	valores := []WiniValor{{Tipo: 1, Datos: 123}, {Tipo: 3, Datos: 1}}
	dicc := &WiniDiccionarioPrueba{
		Longitud: 2,
		Claves:   uintptr(unsafe.Pointer(&claves[0])),
		Valores:  uintptr(unsafe.Pointer(&valores[0])),
	}

	resultado := (&Interprete{}).cValorToGo(WiniValor{Tipo: 6, Datos: uint64(uintptr(unsafe.Pointer(dicc)))})
	mapa, ok := resultado.(map[string]interface{})
	if !ok {
		t.Fatalf("se esperaba un diccionario, se obtuvo %T", resultado)
	}
	if got := mapa["size"]; got != 123 {
		t.Fatalf("size esperado 123, obtenido %#v", got)
	}
	if got := mapa["exists"]; got != true {
		t.Fatalf("exists esperado true, obtenido %#v", got)
	}
}

func TestCValorToGoLista(t *testing.T) {
	elementos := []WiniValor{
		{Tipo: 1, Datos: 42},
		{Tipo: 3, Datos: 1},
	}
	lista := &WiniListaPrueba{
		Longitud:  int32(len(elementos)),
		Elementos: uintptr(unsafe.Pointer(&elementos[0])),
	}

	resultado := (&Interprete{}).cValorToGo(WiniValor{Tipo: 5, Datos: uint64(uintptr(unsafe.Pointer(lista)))})
	valores, ok := resultado.([]interface{})
	if !ok {
		t.Fatalf("se esperaba una lista, se obtuvo %T", resultado)
	}
	if got, want := valores, []interface{}{42, true}; !reflect.DeepEqual(got, want) {
		t.Fatalf("lista esperada %#v, obtenida %#v", want, got)
	}
}

func TestAsignacionCompuestaSumaYResta(t *testing.T) {
	codigo := "numero = 10\nnumero += 5\nnumero -= 3\nelementos = [1]\nelementos[0] += 4\nelementos[0] -= 2\n"
	ast := NewParser(NewLexer().Tokenize(codigo)).Parse()
	interprete := NewInterprete("", nil, nil)
	interprete.Interpretar(ast)

	if got := interprete.Variables["numero"]; !valoresIguales(got, 12) {
		t.Fatalf("numero esperado 12, obtenido %#v", got)
	}
	lista, ok := interprete.Variables["elementos"].([]interface{})
	if !ok {
		t.Fatalf("se esperaba una lista, se obtuvo %T", interprete.Variables["elementos"])
	}
	if got := lista[0]; !valoresIguales(got, 3) {
		t.Fatalf("elemento esperado 3, obtenido %#v", got)
	}
}
