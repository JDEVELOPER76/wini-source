// winiapi_impl.cpp
#include "winiapi.h"
#include <cstdlib>
#include <cstring>
#include <string>
#include <unordered_map>
#include <vector>

//g++ -shared -o os.dll os.cpp winiapi.cpp -I.. -lshlwapi -lpsapi -luser32 -lshell32 -D WINI_EXPORTS -std=c++17


// Contexto global para el módulo
static WiniContexto g_contexto = nullptr;

// Implementación de funciones de creación de valores
WINI_API WiniValor wini_crear_entero(int64_t valor) {
    WiniValor v;
    v.tipo = WINI_TIPO_ENTERO;
    v.entero = valor;
    return v;
}

WINI_API WiniValor wini_crear_decimal(double valor) {
    WiniValor v;
    v.tipo = WINI_TIPO_DECIMAL;
    v.decimal = valor;
    return v;
}

WINI_API WiniValor wini_crear_booleano(bool valor) {
    WiniValor v;
    v.tipo = WINI_TIPO_BOOLEANO;
    v.booleano = valor;
    return v;
}

WINI_API WiniValor wini_crear_cadena(const char* valor) {
    WiniValor v;
    v.tipo = WINI_TIPO_CADENA;
    if (valor) {
        char* copia = (char*)malloc(strlen(valor) + 1);
        strcpy(copia, valor);
        v.cadena = copia;
    } else {
        v.cadena = nullptr;
    }
    return v;
}

static char* copiar_cadena(const char* valor) {
    if (!valor) return nullptr;
    size_t len = strlen(valor);
    char* copia = (char*)malloc(len + 1);
    if (copia) {
        memcpy(copia, valor, len + 1);
    }
    return copia;
}

WINI_API WiniValor wini_crear_lista(WiniValor* elementos, int longitud) {
    WiniValor v;
    v.tipo = WINI_TIPO_LISTA;
    WiniListaC* lista = (WiniListaC*)malloc(sizeof(WiniListaC));
    lista->longitud = longitud;
    lista->elementos = nullptr;
    if (longitud > 0 && elementos) {
        lista->elementos = (WiniValor*)malloc(sizeof(WiniValor) * (size_t)longitud);
        for (int i = 0; i < longitud; i++) {
            lista->elementos[i] = elementos[i];
        }
    }
    v.puntero = lista;
    return v;
}

WINI_API WiniValor wini_crear_diccionario(WiniValor* claves, WiniValor* valores, int longitud) {
    WiniValor v;
    v.tipo = WINI_TIPO_DICCIONARIO;
    WiniDiccionarioC* dicc = (WiniDiccionarioC*)malloc(sizeof(WiniDiccionarioC));
    dicc->longitud = longitud;
    dicc->claves = nullptr;
    dicc->valores = nullptr;
    if (longitud > 0 && claves && valores) {
        dicc->claves = (char**)malloc(sizeof(char*) * (size_t)longitud);
        dicc->valores = (WiniValor*)malloc(sizeof(WiniValor) * (size_t)longitud);
        for (int i = 0; i < longitud; i++) {
            const char* clave = wini_valor_a_cadena(claves[i]);
            dicc->claves[i] = copiar_cadena(clave);
            dicc->valores[i] = valores[i];
        }
    }
    v.puntero = dicc;
    return v;
}

WINI_API WiniValor wini_crear_ninguno(void) {
    WiniValor v;
    v.tipo = WINI_TIPO_NINGUNO;
    v.puntero = nullptr;
    return v;
}

WINI_API void wini_free_string(char* str) {
    if (str) free(str);
}

WINI_API void wini_free_valor(WiniValor valor) {
    switch (valor.tipo) {
    case WINI_TIPO_CADENA:
        if (valor.cadena) free(valor.cadena);
        break;
    case WINI_TIPO_LISTA:
        if (valor.puntero) {
            WiniListaC* lista = (WiniListaC*)valor.puntero;
            if (lista->elementos) free(lista->elementos);
            free(lista);
        }
        break;
    case WINI_TIPO_DICCIONARIO:
        if (valor.puntero) {
            WiniDiccionarioC* dicc = (WiniDiccionarioC*)valor.puntero;
            if (dicc->claves) {
                for (int i = 0; i < dicc->longitud; i++) {
                    if (dicc->claves[i]) free(dicc->claves[i]);
                }
                free(dicc->claves);
            }
            if (dicc->valores) free(dicc->valores);
            free(dicc);
        }
        break;
    default:
        break;
    }
}

WINI_API const char* wini_valor_a_cadena(WiniValor valor) {
    static thread_local std::string buffer;
    switch (valor.tipo) {
    case WINI_TIPO_NINGUNO:   buffer = "nulo"; break;
    case WINI_TIPO_ENTERO:    buffer = std::to_string(valor.entero); break;
    case WINI_TIPO_DECIMAL:   buffer = std::to_string(valor.decimal); break;
    case WINI_TIPO_BOOLEANO:  buffer = valor.booleano ? "verdadero" : "falso"; break;
    case WINI_TIPO_CADENA:    buffer = valor.cadena ? valor.cadena : ""; break;
    default:                  buffer = "<objeto>";
    }
    return buffer.c_str();
}

// Implementación de funciones de contexto
WINI_API void wini_set_variable(WiniContexto ctx, const char* nombre, WiniValor valor) {
    // En una DLL, las variables se almacenan en el contexto del intérprete
    // Esta función debería ser proporcionada por el intérprete en tiempo de ejecución
    // Como fallback, guardamos en un mapa global
    static std::unordered_map<std::string, WiniValor> variables_globales;
    variables_globales[nombre] = valor;
}

WINI_API WiniValor wini_get_variable(WiniContexto ctx, const char* nombre) {
    static std::unordered_map<std::string, WiniValor> variables_globales;
    auto it = variables_globales.find(nombre);
    if (it != variables_globales.end()) {
        return it->second;
    }
    return wini_crear_ninguno();
}

WINI_API void* wini_get_funcion_nativa(WiniContexto ctx, const char* nombre) {
    return nullptr;
}

WINI_API void wini_registrar_funcion(WiniContexto ctx, const char* nombre, void* fn) {
    // Registro de funciones - implementación simple
}

WINI_API WiniValor wini_evaluar(WiniContexto ctx, const char* expresion) {
    return wini_crear_ninguno();
}

// Funciones de acceso a listas y diccionarios
WINI_API int wini_lista_longitud(WiniValor lista) {
    if (lista.tipo != WINI_TIPO_LISTA || !lista.puntero) return 0;
    std::vector<WiniValor>* vec = (std::vector<WiniValor>*)lista.puntero;
    return (int)vec->size();
}

WINI_API WiniValor wini_lista_obtener(WiniValor lista, int indice) {
    if (lista.tipo != WINI_TIPO_LISTA || !lista.puntero) {
        return wini_crear_ninguno();
    }
    std::vector<WiniValor>* vec = (std::vector<WiniValor>*)lista.puntero;
    if (indice < 0 || indice >= (int)vec->size()) {
        return wini_crear_ninguno();
    }
    return (*vec)[indice];
}

WINI_API void wini_lista_establecer(WiniValor lista, int indice, WiniValor valor) {
    if (lista.tipo != WINI_TIPO_LISTA || !lista.puntero) return;
    std::vector<WiniValor>* vec = (std::vector<WiniValor>*)lista.puntero;
    if (indice >= 0 && indice < (int)vec->size()) {
        (*vec)[indice] = valor;
    }
}

WINI_API int wini_diccionario_longitud(WiniValor dicc) {
    if (dicc.tipo != WINI_TIPO_DICCIONARIO || !dicc.puntero) return 0;
    std::unordered_map<std::string, WiniValor>* map = (std::unordered_map<std::string, WiniValor>*)dicc.puntero;
    return (int)map->size();
}

WINI_API WiniValor wini_diccionario_obtener(WiniValor dicc, const char* clave) {
    if (dicc.tipo != WINI_TIPO_DICCIONARIO || !dicc.puntero || !clave) {
        return wini_crear_ninguno();
    }
    std::unordered_map<std::string, WiniValor>* map = (std::unordered_map<std::string, WiniValor>*)dicc.puntero;
    auto it = map->find(clave);
    if (it != map->end()) {
        return it->second;
    }
    return wini_crear_ninguno();
}

WINI_API void wini_diccionario_establecer(WiniValor dicc, const char* clave, WiniValor valor) {
    if (dicc.tipo != WINI_TIPO_DICCIONARIO || !dicc.puntero || !clave) return;
    std::unordered_map<std::string, WiniValor>* map = (std::unordered_map<std::string, WiniValor>*)dicc.puntero;
    (*map)[clave] = valor;
}