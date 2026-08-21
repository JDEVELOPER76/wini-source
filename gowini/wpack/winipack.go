// winipack.go - Empaquetador de Wini (VERSIÓN SIMPLIFICADA)
// Compilar: go build -ldflags="-s -w" -o winipack.exe winipack.go

package main

import (
	"encoding/binary"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

type ArchivoEmbbedido struct {
	Nombre  string
	Offset  int64
	Tamanio int64
	EsTexto bool
}

func main() {
	var (
		principalFile = flag.String("principal", "main.wn", "Archivo principal .wn")
		outputFile    = flag.String("output", "", "Nombre del ejecutable de salida")
		nombreExe     = flag.String("nombre_exe", "", "Nombre personalizado del ejecutable")
		archivoFlag   = flag.String("archivo", "", "Archivo adicional para empaquetar")
		carpetaFlag   = flag.String("carpeta", "", "Carpeta adicional para empaquetar")
		help          = flag.Bool("help", false, "Mostrar ayuda")
	)

	flag.Parse()

	if *help {
		fmt.Println("=== WINIPACK - Empaquetador de Wini ===")
		fmt.Println("")
		fmt.Println("Uso: winipack [opciones]")
		fmt.Println("")
		fmt.Println("Opciones:")
		fmt.Println("  --principal <archivo.wn>   Archivo principal .wn")
		fmt.Println("  --output <nombre>          Nombre del ejecutable de salida")
		fmt.Println("  --nombre_exe <nombre>      Nombre personalizado del ejecutable")
		fmt.Println("  --archivo <archivo>        Agregar un archivo adicional")
		fmt.Println("  --carpeta <carpeta>        Agregar una carpeta completa")
		fmt.Println("  --consola_h                Consola habilitada (default)")
		fmt.Println("  --consola_d                Consola deshabilitada")
		fmt.Println("  --help                     Mostrar esta ayuda")
		return
	}

	archivoWn := *principalFile
	var archivosAdicionales []string
	var carpetasAdicionales []string
	consolaHabilitada := true

	// Parseo manual de flags para soportar múltiples archivos
	for i := 1; i < len(os.Args); i++ {
		arg := os.Args[i]
		if arg == "--archivo" && i+1 < len(os.Args) {
			archivosAdicionales = append(archivosAdicionales, os.Args[i+1])
			i++
		} else if arg == "--carpeta" && i+1 < len(os.Args) {
			carpetasAdicionales = append(carpetasAdicionales, os.Args[i+1])
			i++
		} else if arg == "--output" && i+1 < len(os.Args) {
			outputFile = &os.Args[i+1]
			i++
		} else if arg == "--nombre_exe" && i+1 < len(os.Args) {
			nombreExe = &os.Args[i+1]
			i++
		} else if arg == "--principal" && i+1 < len(os.Args) {
			archivoWn = os.Args[i+1]
			i++
		} else if arg == "--consola_h" {
			consolaHabilitada = true
		} else if arg == "--consola_d" {
			consolaHabilitada = false
		}
	}

	if *archivoFlag != "" {
		archivosAdicionales = append(archivosAdicionales, *archivoFlag)
	}
	if *carpetaFlag != "" {
		carpetasAdicionales = append(carpetasAdicionales, *carpetaFlag)
	}

	var nombreSalida string
	if *nombreExe != "" {
		nombreSalida = *nombreExe
	} else if *outputFile != "" {
		nombreSalida = *outputFile
	} else {
		nombreBase := strings.TrimSuffix(filepath.Base(archivoWn), filepath.Ext(archivoWn))
		nombreSalida = nombreBase + ".exe"
	}

	fmt.Println("=== WINIPACK - Empaquetador de Wini ===")
	fmt.Printf("Empaquetando: %s\n", archivoWn)
	fmt.Printf("Salida: %s\n", nombreSalida)
	fmt.Printf("Consola: %s\n\n", map[bool]string{true: "habilitada", false: "deshabilitada"}[consolaHabilitada])

	// Verificar archivos necesarios
	if _, err := os.Stat("launcher.exe"); os.IsNotExist(err) {
		fmt.Println("Error: launcher.exe no encontrado")
		fmt.Println("Compila: g++ -static -O2 -s -o launcher.exe launcher.cpp")
		os.Exit(1)
	}
	if _, err := os.Stat("wini.exe"); os.IsNotExist(err) {
		fmt.Println("Error: wini.exe no encontrado")
		os.Exit(1)
	}
	if _, err := os.Stat(archivoWn); os.IsNotExist(err) {
		fmt.Printf("Error: %s no encontrado\n", archivoWn)
		os.Exit(1)
	}

	// Leer archivos
	fmt.Println("Leyendo archivos...")
	launcherData, _ := os.ReadFile("launcher.exe")
	fmt.Printf("  OK launcher.exe (%d bytes)\n", len(launcherData))

	winiData, _ := os.ReadFile("wini.exe")
	fmt.Printf("  OK wini.exe (%d bytes)\n", len(winiData))

	appData, _ := os.ReadFile(archivoWn)
	fmt.Printf("  OK %s (%d bytes)\n", archivoWn, len(appData))

	var archivos []ArchivoEmbbedido
	archivos = append(archivos, ArchivoEmbbedido{
		Nombre:  "wini.exe",
		Offset:  0,
		Tamanio: int64(len(winiData)),
		EsTexto: false,
	})
	archivos = append(archivos, ArchivoEmbbedido{
		Nombre:  archivoWn,
		Offset:  0,
		Tamanio: int64(len(appData)),
		EsTexto: true,
	})

	// Leer librerias
	if _, err := os.Stat("librerias"); err == nil {
		fmt.Println("  Leyendo librerias...")
		filepath.Walk("librerias", func(path string, info os.FileInfo, err error) error {
			if err != nil || info.IsDir() {
				return err
			}
			relPath := strings.ReplaceAll(path, "\\", "/")
			data, _ := os.ReadFile(path)
			archivos = append(archivos, ArchivoEmbbedido{
				Nombre:  relPath,
				Offset:  0,
				Tamanio: int64(len(data)),
				EsTexto: strings.HasSuffix(relPath, ".wn") || strings.HasSuffix(relPath, ".txt"),
			})
			fmt.Printf("    OK %s (%d bytes)\n", relPath, len(data))
			return nil
		})
	}

	// Leer archivos adicionales
	for _, archivo := range archivosAdicionales {
		if _, err := os.Stat(archivo); os.IsNotExist(err) {
			fmt.Printf("Advertencia: %s no encontrado\n", archivo)
			continue
		}
		data, _ := os.ReadFile(archivo)
		nombre := filepath.Base(archivo)
		archivos = append(archivos, ArchivoEmbbedido{
			Nombre:  nombre,
			Offset:  0,
			Tamanio: int64(len(data)),
			EsTexto: strings.HasSuffix(nombre, ".wn") || strings.HasSuffix(nombre, ".txt"),
		})
		fmt.Printf("  OK %s (%d bytes)\n", nombre, len(data))
	}

	// Leer carpetas adicionales
	for _, carpeta := range carpetasAdicionales {
		if _, err := os.Stat(carpeta); os.IsNotExist(err) {
			fmt.Printf("Advertencia: %s no encontrada\n", carpeta)
			continue
		}
		fmt.Printf("  Leyendo carpeta: %s\n", carpeta)
		filepath.Walk(carpeta, func(path string, info os.FileInfo, err error) error {
			if err != nil || info.IsDir() {
				return err
			}
			relPath := strings.ReplaceAll(path, "\\", "/")
			data, _ := os.ReadFile(path)
			archivos = append(archivos, ArchivoEmbbedido{
				Nombre:  relPath,
				Offset:  0,
				Tamanio: int64(len(data)),
				EsTexto: strings.HasSuffix(relPath, ".txt") || strings.HasSuffix(relPath, ".wn"),
			})
			fmt.Printf("    OK %s (%d bytes)\n", relPath, len(data))
			return nil
		})
	}

	fmt.Printf("\nArchivos totales: %d\n", len(archivos))
	fmt.Println("Generando ejecutable...")

	// Escribir ejecutable
	out, _ := os.Create(nombreSalida)
	defer out.Close()

	out.Write(launcherData)

	offsets := make([]int64, len(archivos))
	fmt.Println("  Escribiendo datos...")
	for i, arch := range archivos {
		var data []byte
		switch arch.Nombre {
		case "wini.exe":
			data = winiData
		default:
			if arch.Nombre == archivoWn {
				data = appData
			} else if strings.HasPrefix(arch.Nombre, "librerias/") {
				path := strings.ReplaceAll(arch.Nombre, "/", "\\")
				data, _ = os.ReadFile(path)
			} else {
				data, _ = os.ReadFile(arch.Nombre)
			}
		}
		if len(data) == 0 {
			continue
		}
		offset, _ := out.Seek(0, io.SeekCurrent)
		offsets[i] = offset
		out.Write(data)
	}

	// Escribir índice
	fmt.Println("  Escribiendo índice...")
	marca := []byte("WINIDATA")
	out.Write(marca)

	// Configuración de consola
	binary.Write(out, binary.LittleEndian, byte(map[bool]int{true: 1, false: 0}[consolaHabilitada]))
	binary.Write(out, binary.LittleEndian, int32(len(archivos)))

	for i, arch := range archivos {
		nombreBytes := []byte(arch.Nombre)
		binary.Write(out, binary.LittleEndian, int16(len(nombreBytes)))
		out.Write(nombreBytes)
		binary.Write(out, binary.LittleEndian, arch.Tamanio)
		binary.Write(out, binary.LittleEndian, offsets[i])
		esTexto := byte(0)
		if arch.EsTexto || strings.HasSuffix(arch.Nombre, ".wn") {
			esTexto = 1
		}
		binary.Write(out, binary.LittleEndian, esTexto)
		fmt.Printf("    OK %s (offset: %d, tamaño: %d)\n", arch.Nombre, offsets[i], arch.Tamanio)
	}

	fmt.Printf("\n✅ %s generado correctamente!\n", nombreSalida)
	info, _ := os.Stat(nombreSalida)
	fmt.Printf("📦 Tamaño: %.2f MB\n", float64(info.Size())/(1024*1024))
	fmt.Printf("\n🚀 Para ejecutar: .\\%s\n", nombreSalida)
}
