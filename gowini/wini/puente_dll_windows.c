// puente_dll_windows.c
#include "puente_dll_windows.h"
#include <stdlib.h>
#include <string.h>

// Declarar que winiRegistrarFuncion será proporcionada por Go
// Esta función es exportada por el programa Go con //export winiRegistrarFuncion
extern void* winiRegistrarFuncion(char* nombre, void* funcion);

typedef int (*WiniInicializador)(void *contexto, void *(*registrar)(const char *, void *));
typedef WiniValorC (*WiniFuncion)(WiniValorC *argumentos, int32_t cantidad);

static void *registrarFuncionPuente(const char *nombre, void *funcion) {
    return winiRegistrarFuncion((char *)nombre, funcion);
}

int winiLlamarInicializador(void *inicializador, void *contexto) {
    if (!inicializador) return 0;
    return ((WiniInicializador)inicializador)(contexto, registrarFuncionPuente);
}

WiniValorC winiLlamarFuncion(void *funcion, WiniValorC *argumentos, int32_t cantidad) {
    if (!funcion) {
        WiniValorC resultado = {0, 0, 0};
        return resultado;
    }
    return ((WiniFuncion)funcion)(argumentos, cantidad);
}

// Funciones de utilidad
char* winiStringToC(const char* str) {
    if (!str) return NULL;
    size_t len = strlen(str) + 1;
    char* copy = (char*)malloc(len);
    if (copy) {
        memcpy(copy, str, len);
    }
    return copy;
}

void winiFreeString(char* str) {
    if (str) free(str);
}

WiniValorC* winiCrearListaC(WiniValorC* elementos, int32_t longitud) {
    WiniValorC* valor = (WiniValorC*)malloc(sizeof(WiniValorC));
    valor->tipo = 5;
    valor->_padding = 0;
    
    WiniListaC* lista = (WiniListaC*)malloc(sizeof(WiniListaC));
    lista->longitud = longitud;
    lista->_padding = 0;
    
    if (longitud > 0 && elementos) {
        uint64_t* elementosArray = (uint64_t*)malloc(sizeof(uint64_t) * longitud);
        for (int i = 0; i < longitud; i++) {
            WiniValorC* elem = (WiniValorC*)malloc(sizeof(WiniValorC));
            elem->tipo = elementos[i].tipo;
            elem->_padding = 0;
            elem->datos = elementos[i].datos;
            elementosArray[i] = (uint64_t)(uintptr_t)elem;
        }
        lista->elementos = (uint64_t)(uintptr_t)elementosArray;
    } else {
        lista->elementos = 0;
    }
    
    valor->datos = (uint64_t)(uintptr_t)lista;
    return valor;
}

WiniValorC* winiCrearDiccionarioC(char** claves, WiniValorC* valores, int32_t longitud) {
    WiniValorC* valor = (WiniValorC*)malloc(sizeof(WiniValorC));
    valor->tipo = 6;
    valor->_padding = 0;
    
    WiniDiccionarioC* dicc = (WiniDiccionarioC*)malloc(sizeof(WiniDiccionarioC));
    dicc->longitud = longitud;
    dicc->_padding = 0;
    
    if (longitud > 0 && claves && valores) {
        char** clavesArray = (char**)malloc(sizeof(char*) * longitud);
        for (int i = 0; i < longitud; i++) {
            if (claves[i]) {
                clavesArray[i] = winiStringToC(claves[i]);
            } else {
                clavesArray[i] = NULL;
            }
        }
        dicc->claves = (uint64_t)(uintptr_t)clavesArray;
        
        WiniValorC* valoresArray = (WiniValorC*)malloc(sizeof(WiniValorC) * longitud);
        for (int i = 0; i < longitud; i++) {
            valoresArray[i].tipo = valores[i].tipo;
            valoresArray[i]._padding = 0;
            valoresArray[i].datos = valores[i].datos;
        }
        dicc->valores = (uint64_t)(uintptr_t)valoresArray;
    } else {
        dicc->claves = 0;
        dicc->valores = 0;
    }
    
    valor->datos = (uint64_t)(uintptr_t)dicc;
    return valor;
}

void winiLiberarListaC(WiniListaC* lista) {
    if (!lista) return;
    if (lista->elementos) {
        uint64_t* elementos = (uint64_t*)(uintptr_t)lista->elementos;
        for (int i = 0; i < lista->longitud; i++) {
            WiniValorC* elem = (WiniValorC*)(uintptr_t)elementos[i];
            if (elem) {
                if (elem->tipo == 4 && elem->datos) {
                    free((char*)(uintptr_t)elem->datos);
                }
                free(elem);
            }
        }
        free(elementos);
    }
    free(lista);
}

void winiLiberarDiccionarioC(WiniDiccionarioC* dicc) {
    if (!dicc) return;
    if (dicc->claves) {
        char** claves = (char**)(uintptr_t)dicc->claves;
        for (int i = 0; i < dicc->longitud; i++) {
            if (claves[i]) free(claves[i]);
        }
        free(claves);
    }
    if (dicc->valores) {
        WiniValorC* valores = (WiniValorC*)(uintptr_t)dicc->valores;
        for (int i = 0; i < dicc->longitud; i++) {
            if (valores[i].tipo == 4 && valores[i].datos) {
                free((char*)(uintptr_t)valores[i].datos);
            }
        }
        free(valores);
    }
    free(dicc);
}