// puente_dll_windows.h
#ifndef PUENTE_DLL_WINDOWS_H
#define PUENTE_DLL_WINDOWS_H

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

// Estructura de valor Wini para el puente
typedef struct {
    int32_t tipo;       // 0=nulo, 1=entero, 2=decimal, 3=booleano, 4=cadena, 5=lista, 6=diccionario
    int32_t _padding;   // Padding para alinear a 8 bytes
    uint64_t datos;     // Datos según el tipo
} WiniValorC;

// Estructura para listas
typedef struct {
    int32_t longitud;
    int32_t _padding;
    uint64_t elementos; // puntero a array de WiniValorC*
} WiniListaC;

// Estructura para diccionarios
typedef struct {
    int32_t longitud;
    int32_t _padding;
    uint64_t claves;    // puntero a array de char*
    uint64_t valores;   // puntero a array de WiniValorC
} WiniDiccionarioC;

// Funciones de puente (implementadas en C)
int winiLlamarInicializador(void* inicializador, void* contexto);
WiniValorC winiLlamarFuncion(void* funcion, WiniValorC* argumentos, int32_t cantidad);

// Funciones de utilidad (implementadas en C)
char* winiStringToC(const char* str);
void winiFreeString(char* str);
WiniValorC* winiCrearListaC(WiniValorC* elementos, int32_t longitud);
WiniValorC* winiCrearDiccionarioC(char** claves, WiniValorC* valores, int32_t longitud);
void winiLiberarListaC(WiniListaC* lista);
void winiLiberarDiccionarioC(WiniDiccionarioC* dicc);

#ifdef __cplusplus
}
#endif

#endif // PUENTE_DLL_WINDOWS_H