// bytecode.hpp
// Formato de bytecode de Wini (extension de archivo: .wnc)
//
// Un Chunk contiene:
//   - un arreglo de constantes (literales usados por el programa: numeros,
//     cadenas, booleanos, nulo; los nombres de variable tambien se guardan
//     aqui como constantes de tipo cadena y se referencian por indice)
//   - un flujo de bytes con las instrucciones
//
// Codificacion de instrucciones:
//   [1 byte  OpCode] [N operandos de 4 bytes (uint32, little-endian)]
// El numero de operandos depende del opcode (ver tabla en BYTECODE.md).
#pragma once
#include <cstdint>
#include <string>
#include <vector>
#include <variant>
#include <iosfwd>

namespace BC {

enum class OpCode : uint8_t {
    OP_CONST = 0,        // [idx_const]              push constantes[idx]
    OP_NULO,              //                          push nulo
    OP_VERDADERO,         //                          push verdadero
    OP_FALSO,              //                          push falso
    OP_POP,                //                          pop (descarta el tope)

    OP_DEFINIR_VAR,       // [idx_nombre, tipo, es_const]  pop valor, define variable
    OP_OBTENER_VAR,       // [idx_nombre]              push valor de la variable
    OP_ASIGNAR_VAR,       // [idx_nombre]              pop valor, reasigna variable (no la desapila)

    OP_SUMA, OP_RESTA, OP_MUL, OP_DIV,          // pop b, pop a, push a OP b
    OP_IGUAL, OP_DIFERENTE, OP_MENOR, OP_MAYOR, // pop b, pop a, push (a OP b)
    OP_Y, OP_O,                                  // logicos
    OP_NEGAR, OP_NO,                             // unarios: pop a, push OP a

    OP_LISTA,             // [n]  pop n valores, push lista
    OP_DICCIONARIO,       // [n]  pop 2n valores (clave,valor)*n, push diccionario
    OP_INDEXAR,            //                          pop indice, pop contenedor, push valor

    OP_IMPRIMIR,           //                          pop valor, lo imprime

    OP_JUMP,               // [destino]                ip = destino
    OP_JUMP_IF_FALSE,      // [destino]                pop cond; si es falso, ip = destino

    OP_ITER_CREAR,         //                          pop valor (lista/diccionario/entero/decimal),
                            //                          crea un iterador y lo apila en la pila de iteradores
    OP_ITER_SIGUIENTE,     // [destino]                si el iterador del tope tiene siguiente valor, lo
                            //                          push en la pila de valores; si no, desapila el
                            //                          iterador y salta a 'destino' (fin del bucle)

    OP_RANGO,               // [n_args]  pop n_args (1 o 2) valores enteros
                            //           (n_args==1: fin; n_args==2: inicio, fin)
                            //           push una lista [inicio..fin)

    OP_HALT                //                          detiene la VM
};

std::string nombreOpCode(OpCode op);

// Constante embebida en el bytecode (literal). No incluye listas/diccionarios:
// esos se construyen en tiempo de ejecucion con OP_LISTA / OP_DICCIONARIO.
using Constante = std::variant<std::monostate, int, double, std::string, bool>;

struct Chunk {
    std::vector<uint8_t> codigo;
    std::vector<Constante> constantes;

    uint32_t agregarConstante(const Constante& c);

    void emitirByte(uint8_t byte);
    void emitirU32(uint32_t valor);

    void emitirOp(OpCode op);
    void emitirOp(OpCode op, uint32_t operando);
    void emitirOp(OpCode op, uint32_t op1, uint32_t op2);
    void emitirOp(OpCode op, uint32_t op1, uint32_t op2, uint32_t op3);

    // Vuelca una representacion legible del bytecode (para depuracion).
    void desensamblar(std::ostream& os) const;
};

// Guarda/carga un Chunk en formato binario .wnc
void guardarChunk(const Chunk& chunk, const std::string& ruta);
Chunk cargarChunk(const std::string& ruta);

} // namespace BC
