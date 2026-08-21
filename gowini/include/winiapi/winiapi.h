#ifndef WINI_API_H
#define WINI_API_H

#ifdef _WIN32
    #ifdef WINI_EXPORTS
        #define WINI_API __declspec(dllexport)
    #else
        #define WINI_API __declspec(dllimport)
    #endif
#else
    #define WINI_API __attribute__((visibility("default")))
#endif

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// Tipos de valores Wini
typedef enum {
    WINI_TIPO_NINGUNO = 0,
    WINI_TIPO_ENTERO = 1,
    WINI_TIPO_DECIMAL = 2,
    WINI_TIPO_BOOLEANO = 3,
    WINI_TIPO_CADENA = 4,
    WINI_TIPO_LISTA = 5,
    WINI_TIPO_DICCIONARIO = 6,
    WINI_TIPO_FUNCION = 7,
    WINI_TIPO_ERROR = -1
} WiniTipo;

// Estructura de valor Wini
typedef struct {
    WiniTipo tipo;
    union {
        int64_t entero;
        double decimal;
        uint8_t booleano;   // ← CAMBIADO DE bool a uint8_t
        char* cadena;
        void* puntero;
    };
} WiniValor;

typedef struct {
    int32_t longitud;
    WiniValor* elementos;
} WiniListaC;

typedef struct {
    int32_t longitud;
    char** claves;
    WiniValor* valores;
} WiniDiccionarioC;

// Contexto del intérprete (opaco)
typedef void* WiniContexto;

// ===== FUNCIONES QUE EL MÓDULO NATIVO DEBE EXPORTAR =====

// Inicialización del módulo
WINI_API bool wini_module_init(WiniContexto ctx, void* (*funcion_registrar)(const char* nombre, void* fn));

// Limpieza del módulo
WINI_API void wini_module_cleanup(WiniContexto ctx);

// ===== FUNCIONES QUE EL INTÉRPRETE PROPORCIONA AL MÓDULO =====

// Obtener una variable del intérprete
WINI_API WiniValor wini_get_variable(WiniContexto ctx, const char* nombre);

// Establecer una variable en el intérprete
WINI_API void wini_set_variable(WiniContexto ctx, const char* nombre, WiniValor valor);

// Obtener una función nativa
WINI_API void* wini_get_funcion_nativa(WiniContexto ctx, const char* nombre);

// Registrar una función nativa
WINI_API void wini_registrar_funcion(WiniContexto ctx, const char* nombre, void* fn);

// Evaluar una expresión
WINI_API WiniValor wini_evaluar(WiniContexto ctx, const char* expresion);

// Crear valores
WINI_API WiniValor wini_crear_entero(int64_t valor);
WINI_API WiniValor wini_crear_decimal(double valor);
WINI_API WiniValor wini_crear_booleano(bool valor);
WINI_API WiniValor wini_crear_cadena(const char* valor);
WINI_API WiniValor wini_crear_lista(WiniValor* elementos, int longitud);
WINI_API WiniValor wini_crear_diccionario(WiniValor* claves, WiniValor* valores, int longitud);
WINI_API WiniValor wini_crear_ninguno(void);

// Liberar memoria
WINI_API void wini_free_string(char* str);
WINI_API void wini_free_valor(WiniValor valor);

// Acceso a listas y diccionarios
WINI_API int wini_lista_longitud(WiniValor lista);
WINI_API WiniValor wini_lista_obtener(WiniValor lista, int indice);
WINI_API void wini_lista_establecer(WiniValor lista, int indice, WiniValor valor);

WINI_API int wini_diccionario_longitud(WiniValor dicc);
WINI_API WiniValor wini_diccionario_obtener(WiniValor dicc, const char* clave);
WINI_API void wini_diccionario_establecer(WiniValor dicc, const char* clave, WiniValor valor);

// Conversión
WINI_API const char* wini_valor_a_cadena(WiniValor valor);

#ifdef __cplusplus
}
#endif

#endif // WINI_API_H