// vm_bytecode.hpp
// Maquina virtual de pila (stack-based) que ejecuta un BC::Chunk,
// ya sea leido de un archivo .wnc o generado en memoria por
// CompiladorBytecode. Produce el mismo comportamiento observable
// que Interprete (interprete.hpp), pero ejecutando bytecode.
#pragma once
#include <string>
#include <vector>
#include <unordered_map>
#include "bytecode.hpp"
#include "valores.hpp"

class VMBytecode {
public:
    void ejecutar(const BC::Chunk& chunk);

private:
    struct Variable {
        Valor valor;
        bool es_constante;
    };

    // Estado de iteracion para el bucle 'para ... en ...'. Se apila una
    // por cada bucle activo (soporta bucles anidados) y avanza con
    // OP_ITER_SIGUIENTE hasta agotarse.
    struct Iterador {
        enum class Tipo { LISTA, DICCIONARIO, RANGO } tipo;
        std::shared_ptr<ListaValor> lista;
        std::shared_ptr<DiccionarioValor> diccionario;
        size_t indice = 0;
        int rango_actual = 0;
        int rango_limite = 0;
    };

    std::vector<Valor> pila;
    std::vector<Iterador> pila_iteradores;
    std::unordered_map<std::string, Variable> entorno;

    Valor pop();
    void push(const Valor& v);
    const std::string& nombreConstante(const BC::Chunk& chunk, uint32_t idx);
};
