// modulo_nativo.go
package wini

/*
#include <stdlib.h>
#include "puente_dll_windows.h"
*/
import "C"
import (
	"fmt"
	"math"
	"path/filepath"
	"strings"
	"sync"
	"syscall"
	"unsafe"
)

// WiniValor debe coincidir con WiniValorC en C
type WiniValor struct {
	Tipo    int32
	Padding int32
	Datos   uint64
}

type ModuloNativo struct {
	Nombre    string
	Ruta      string
	DLL       *syscall.DLL
	Funciones map[string]unsafe.Pointer
}

var registroDLL struct {
	sync.Mutex
	modulo *ModuloNativo
}

// leerCadenaDesdePuntero lee una cadena desde un puntero C
func leerCadenaDesdePuntero(ptr uint64) string {
	if ptr == 0 {
		return ""
	}
	cstr := (*C.char)(unsafe.Pointer(uintptr(ptr)))
	return C.GoString(cstr)
}

// winiRegistrarFuncion es llamado por el puente C durante wini_module_init
//
//export winiRegistrarFuncion
func winiRegistrarFuncion(nombre *C.char, funcion unsafe.Pointer) unsafe.Pointer {
	registroDLL.Lock()
	defer registroDLL.Unlock()
	if registroDLL.modulo != nil && nombre != nil && funcion != nil {
		registroDLL.modulo.Funciones[C.GoString(nombre)] = funcion
	}
	return nil
}

// CargarModuloNativo carga una DLL que implementa la API Wini
func (i *Interprete) CargarModuloNativo(ruta string, linea int) interface{} {
	nombre := strings.TrimSuffix(filepath.Base(ruta), filepath.Ext(ruta))
	dll, err := syscall.LoadDLL(ruta)
	if err != nil {
		panic(&ErrorImportacion{ErrorConLinea: ErrorConLinea{
			Mensaje: fmt.Sprintf("No se pudo cargar la DLL '%s': %v", ruta, err),
			Linea:   &linea,
		}})
	}

	inicializador, err := dll.FindProc("wini_module_init")
	if err != nil {
		panic(&ErrorImportacion{ErrorConLinea: ErrorConLinea{
			Mensaje: fmt.Sprintf("La DLL '%s' no implementa la API Wini: falta wini_module_init", ruta),
			Linea:   &linea,
		}})
	}

	modulo := &ModuloNativo{
		Nombre:    nombre,
		Ruta:      ruta,
		DLL:       dll,
		Funciones: make(map[string]unsafe.Pointer),
	}

	registroDLL.Lock()
	registroDLL.modulo = modulo
	registroDLL.Unlock()

	resultado := C.winiLlamarInicializador(unsafe.Pointer(inicializador.Addr()), nil)

	registroDLL.Lock()
	registroDLL.modulo = nil
	registroDLL.Unlock()

	if resultado == 0 {
		panic(&ErrorImportacion{ErrorConLinea: ErrorConLinea{
			Mensaje: fmt.Sprintf("Error al inicializar el módulo '%s'", nombre),
			Linea:   &linea,
		}})
	}

	funciones := make(map[string]interface{}, len(modulo.Funciones))
	for nombreFuncion, puntero := range modulo.Funciones {
		funciones[nombreFuncion] = i.wrapFuncionC(puntero)
	}

	return map[string]interface{}{
		"_tipo":     "modulo",
		"_ruta":     ruta,
		"_nombre":   nombre,
		"_nativo":   true,
		"_dll":      dll,
		"funciones": funciones,
		"variables": make(map[string]interface{}),
	}
}

// wrapFuncionC envuelve una función C para que pueda ser llamada desde Go
func (i *Interprete) wrapFuncionC(puntero unsafe.Pointer) func(...interface{}) interface{} {
	return func(argumentos ...interface{}) interface{} {
		// Convertir argumentos Go a WiniValorC
		cArgumentos := make([]C.WiniValorC, len(argumentos))
		cadenas := make([]unsafe.Pointer, 0)

		for idx, arg := range argumentos {
			cArgumentos[idx] = i.goValorToC(arg, &cadenas)
		}

		// Liberar cadenas al final
		defer func() {
			for _, cstr := range cadenas {
				C.free(cstr)
			}
		}()

		var argsPtr *C.WiniValorC
		if len(cArgumentos) > 0 {
			argsPtr = (*C.WiniValorC)(unsafe.Pointer(&cArgumentos[0]))
		}

		// Llamar a la función C
		resultado := C.winiLlamarFuncion(puntero, argsPtr, C.int32_t(len(cArgumentos)))

		// Convertir resultado de C a Go
		return i.cValorToGo(WiniValor{
			Tipo:    int32(resultado.tipo),
			Padding: int32(resultado._padding),
			Datos:   uint64(resultado.datos),
		})
	}
}

// goValorToC convierte un valor Go a WiniValorC
func (i *Interprete) goValorToC(valor interface{}, cadenas *[]unsafe.Pointer) C.WiniValorC {
	var result C.WiniValorC
	result._padding = 0

	switch v := valor.(type) {
	case nil:
		result.tipo = 0
		result.datos = 0

	case int:
		result.tipo = 1
		result.datos = C.uint64_t(v)

	case int64:
		result.tipo = 1
		result.datos = C.uint64_t(v)

	case float64:
		result.tipo = 2
		result.datos = C.uint64_t(math.Float64bits(v))

	case bool:
		result.tipo = 3
		if v {
			result.datos = 1
		} else {
			result.datos = 0
		}

	case string:
		result.tipo = 4
		cstr := C.CString(v)
		*cadenas = append(*cadenas, unsafe.Pointer(cstr))
		result.datos = C.uint64_t(uintptr(unsafe.Pointer(cstr)))

	case []interface{}:
		result.tipo = 5
		// Crear lista en C
		cElementos := make([]C.WiniValorC, len(v))
		for idx, elem := range v {
			cElementos[idx] = i.goValorToC(elem, cadenas)
		}
		var elementos *C.WiniValorC
		if len(cElementos) > 0 {
			elementos = (*C.WiniValorC)(unsafe.Pointer(&cElementos[0]))
		}
		// winiCrearListaC devuelve un WiniValorC* que contiene la lista.
		listaValor := C.winiCrearListaC(elementos, C.int32_t(len(v)))
		result.datos = C.uint64_t(uintptr(unsafe.Pointer(listaValor)))

	case map[string]interface{}:
		result.tipo = 6
		// Crear diccionario en C
		if len(v) == 0 {
			// Diccionario vacío
			diccValor := C.winiCrearDiccionarioC(nil, nil, 0)
			result.datos = C.uint64_t(uintptr(unsafe.Pointer(diccValor)))
		} else {
			claves := make([]*C.char, 0, len(v))
			valores := make([]C.WiniValorC, 0, len(v))

			for k, val := range v {
				cClave := C.CString(k)
				*cadenas = append(*cadenas, unsafe.Pointer(cClave))
				claves = append(claves, cClave)
				valores = append(valores, i.goValorToC(val, cadenas))
			}

			diccValor := C.winiCrearDiccionarioC(
				(**C.char)(unsafe.Pointer(&claves[0])),
				(*C.WiniValorC)(unsafe.Pointer(&valores[0])),
				C.int32_t(len(v)),
			)
			result.datos = C.uint64_t(uintptr(unsafe.Pointer(diccValor)))
		}

	default:
		// Tipo no soportado, retornar nulo
		result.tipo = 0
		result.datos = 0
	}

	return result
}

// cValorToGo convierte un valor C (WiniValor) a Go
func (i *Interprete) cValorToGo(valor WiniValor) interface{} {
	switch valor.Tipo {
	case 0: // NINGUNO
		return nil

	case 1: // ENTERO
		return int(int64(valor.Datos))

	case 2: // DECIMAL
		return math.Float64frombits(valor.Datos)

	case 3: // BOOLEANO
		return valor.Datos != 0

	case 4: // CADENA
		if valor.Datos == 0 {
			return ""
		}
		return leerCadenaDesdePuntero(valor.Datos)

	case 5: // LISTA
		if valor.Datos == 0 {
			return []interface{}{}
		}
		listaC := (*C.WiniListaC)(unsafe.Pointer(uintptr(valor.Datos)))
		longitud := int(listaC.longitud)
		if longitud <= 0 || listaC.elementos == 0 {
			return []interface{}{}
		}

		resultado := make([]interface{}, longitud)
		// La API de las DLL define elementos como WiniValor[], no como
		// WiniValor*. Tratar cada entrada como puntero desalineaba la lectura
		// y terminaba desreferenciando direcciones invalidas.
		elementosPtr := (*C.WiniValorC)(unsafe.Pointer(uintptr(listaC.elementos)))
		elementosArray := (*[1 << 30]C.WiniValorC)(unsafe.Pointer(elementosPtr))[:longitud:longitud]

		for idx := 0; idx < longitud; idx++ {
			elemC := elementosArray[idx]
			valorElem := WiniValor{
				Tipo:    int32(elemC.tipo),
				Padding: int32(elemC._padding),
				Datos:   uint64(elemC.datos),
			}
			resultado[idx] = i.cValorToGo(valorElem)
		}
		return resultado

	case 6: // DICCIONARIO
		if valor.Datos == 0 {
			return map[string]interface{}{}
		}
		diccC := (*C.WiniDiccionarioC)(unsafe.Pointer(uintptr(valor.Datos)))
		longitud := int(diccC.longitud)
		if longitud <= 0 || diccC.claves == 0 || diccC.valores == 0 {
			return map[string]interface{}{}
		}

		resultado := make(map[string]interface{}, longitud)
		clavesPtr := (**C.char)(unsafe.Pointer(uintptr(diccC.claves)))
		valoresPtr := (*C.WiniValorC)(unsafe.Pointer(uintptr(diccC.valores)))

		clavesArray := (*[1 << 30]*C.char)(unsafe.Pointer(clavesPtr))[:longitud:longitud]
		valoresArray := (*[1 << 30]C.WiniValorC)(unsafe.Pointer(valoresPtr))[:longitud:longitud]

		for idx := 0; idx < longitud; idx++ {
			clave := C.GoString(clavesArray[idx])
			valorC := valoresArray[idx]
			valorElem := WiniValor{
				Tipo:    int32(valorC.tipo),
				Padding: int32(valorC._padding),
				Datos:   uint64(valorC.datos),
			}
			resultado[clave] = i.cValorToGo(valorElem)
		}
		return resultado

	default:
		return nil
	}
}
