package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"runtime/debug"
	"wini/wini"
)

const Version = "2.3.0"

// ejecutarArchivo ejecuta un archivo .wn usando el intérprete tradicional
func ejecutarArchivo(archivo string, mostrarTraceback bool) bool {
	if _, err := os.Stat(archivo); os.IsNotExist(err) {
		fmt.Printf("Error: Archivo '%s' no encontrado\n", archivo)
		return false
	}

	defer func() {
		if r := recover(); r != nil {
			fmt.Printf("Error al ejecutar: %v\n", r)
			if mostrarTraceback {
				fmt.Printf("%s\n", debug.Stack())
			}
		}
	}()

	interprete := wini.NewInterprete(archivo, nil, nil)
	if err := interprete.Ejecutar(); err != nil {
		fmt.Printf("Error al ejecutar: %v\n", err)
		return false
	}
	return true
}

func main() {
	// Configurar flags
	version := flag.Bool("version", false, "Mostrar versión")
	versionShort := flag.Bool("v", false, "Mostrar versión (corto)")
	traceback := flag.Bool("traceback", false, "Mostrar traceback completo")
	tracebackShort := flag.Bool("t", false, "Mostrar traceback completo (corto)")

	flag.Usage = func() {
		fmt.Printf(`Wini %s - Lenguaje de programación Wini - Intérprete

Uso: wini [opciones] <archivo.wn>

Opciones:
  -v, --version      Mostrar versión
  -t, --traceback    Mostrar traceback completo

Ejemplos:
  wini programa.wn              # Ejecutar con intérprete
  wini --version                # Mostrar versión

╔════════════════════════════════════════════════════════════════════╗
║  COMANDOS:                                                         ║
╠════════════════════════════════════════════════════════════════════╣
║  wini programa.wn              # Ejecutar con intérprete           ║
║  wini --version                # Mostrar versión                   ║
║  wpack --version               # Gestor de paquetes                ║
╚════════════════════════════════════════════════════════════════════╝
`, Version)
	}

	flag.Parse()

	// Verificar versión
	if *version || *versionShort {
		fmt.Printf("Wini %s\n", Version)
		return
	}

	// Obtener archivo
	args := flag.Args()
	if len(args) == 0 {
		flag.Usage()
		os.Exit(1)
	}

	archivo := args[0]

	// Verificar extensión .wn
	if filepath.Ext(archivo) != ".wn" {
		if _, err := os.Stat(archivo + ".wn"); err == nil {
			archivo = archivo + ".wn"
		} else {
			fmt.Printf("Error: '%s' no es un archivo .wn\n", args[0])
			os.Exit(1)
		}
	}

	if _, err := os.Stat(archivo); os.IsNotExist(err) {
		fmt.Printf("Error: Archivo '%s' no encontrado\n", archivo)
		os.Exit(1)
	}

	mostrarTraceback := *traceback || *tracebackShort

	// Modo interpretación
	if !ejecutarArchivo(archivo, mostrarTraceback) {
		os.Exit(1)
	}
}
