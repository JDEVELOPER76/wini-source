// vm_bytecode.cpp
#include "vm_bytecode.hpp"
#include <stdexcept>
#include <iostream>

using BC::OpCode;

static uint32_t leerU32(const std::vector<uint8_t>& codigo, size_t pos) {
    return static_cast<uint32_t>(codigo[pos]) |
           (static_cast<uint32_t>(codigo[pos + 1]) << 8) |
           (static_cast<uint32_t>(codigo[pos + 2]) << 16) |
           (static_cast<uint32_t>(codigo[pos + 3]) << 24);
}

Valor VMBytecode::pop() {
    if (pila.empty()) throw std::runtime_error("VM: pila vacia (underflow)");
    Valor v = pila.back();
    pila.pop_back();
    return v;
}

void VMBytecode::push(const Valor& v) {
    pila.push_back(v);
}

const std::string& VMBytecode::nombreConstante(const BC::Chunk& chunk, uint32_t idx) {
    if (idx >= chunk.constantes.size())
        throw std::runtime_error("VM: indice de constante fuera de rango");
    if (!std::holds_alternative<std::string>(chunk.constantes[idx]))
        throw std::runtime_error("VM: se esperaba una constante de tipo cadena (nombre)");
    return std::get<std::string>(chunk.constantes[idx]);
}

void VMBytecode::ejecutar(const BC::Chunk& chunk) {
    const auto& codigo = chunk.codigo;
    size_t ip = 0;

    auto constanteComoValor = [&](uint32_t idx) -> Valor {
        if (idx >= chunk.constantes.size())
            throw std::runtime_error("VM: indice de constante fuera de rango");
        const BC::Constante& c = chunk.constantes[idx];
        return std::visit([](auto&& val) -> Valor { return val; }, c);
    };

    while (ip < codigo.size()) {
        OpCode op = static_cast<OpCode>(codigo[ip]);
        ip += 1;

        switch (op) {
            case OpCode::OP_CONST: {
                uint32_t idx = leerU32(codigo, ip); ip += 4;
                push(constanteComoValor(idx));
                break;
            }
            case OpCode::OP_NULO:
                push(std::monostate{});
                break;
            case OpCode::OP_VERDADERO:
                push(true);
                break;
            case OpCode::OP_FALSO:
                push(false);
                break;
            case OpCode::OP_POP:
                pop();
                break;

            case OpCode::OP_DEFINIR_VAR: {
                uint32_t idx_nombre = leerU32(codigo, ip); ip += 4;
                /* tipo (no usado en tiempo de ejecucion) */ leerU32(codigo, ip); ip += 4;
                uint32_t es_const = leerU32(codigo, ip); ip += 4;
                const std::string& nombre = nombreConstante(chunk, idx_nombre);
                Valor valor = pop();
                entorno[nombre] = Variable{valor, es_const != 0};
                break;
            }
            case OpCode::OP_OBTENER_VAR: {
                uint32_t idx_nombre = leerU32(codigo, ip); ip += 4;
                const std::string& nombre = nombreConstante(chunk, idx_nombre);
                auto it = entorno.find(nombre);
                if (it == entorno.end())
                    throw std::runtime_error("Variable no declarada: " + nombre);
                push(it->second.valor);
                break;
            }
            case OpCode::OP_ASIGNAR_VAR: {
                uint32_t idx_nombre = leerU32(codigo, ip); ip += 4;
                const std::string& nombre = nombreConstante(chunk, idx_nombre);
                auto it = entorno.find(nombre);
                if (it == entorno.end())
                    throw std::runtime_error("Variable no declarada: " + nombre);
                if (it->second.es_constante)
                    throw std::runtime_error("No se puede reasignar la constante: " + nombre);
                Valor v = pop();
                it->second.valor = v;
                push(v);
                break;
            }

            case OpCode::OP_SUMA: {
                Valor der = pop();
                Valor izq = pop();
                if (std::holds_alternative<std::string>(izq) || std::holds_alternative<std::string>(der)) {
                    push(valorATexto(izq) + valorATexto(der));
                } else if (std::holds_alternative<int>(izq) && std::holds_alternative<int>(der)) {
                    push(std::get<int>(izq) + std::get<int>(der));
                } else {
                    push(aDouble(izq) + aDouble(der));
                }
                break;
            }
            case OpCode::OP_RESTA: {
                Valor der = pop(); Valor izq = pop();
                if (std::holds_alternative<int>(izq) && std::holds_alternative<int>(der))
                    push(std::get<int>(izq) - std::get<int>(der));
                else
                    push(aDouble(izq) - aDouble(der));
                break;
            }
            case OpCode::OP_MUL: {
                Valor der = pop(); Valor izq = pop();
                if (std::holds_alternative<int>(izq) && std::holds_alternative<int>(der))
                    push(std::get<int>(izq) * std::get<int>(der));
                else
                    push(aDouble(izq) * aDouble(der));
                break;
            }
            case OpCode::OP_DIV: {
                Valor der = pop(); Valor izq = pop();
                double d = aDouble(der);
                if (d == 0) throw std::runtime_error("Division entre cero");
                push(aDouble(izq) / d);
                break;
            }
            case OpCode::OP_IGUAL: {
                Valor der = pop(); Valor izq = pop();
                if (esNumerico(izq) && esNumerico(der)) push(aDouble(izq) == aDouble(der));
                else push(valorATexto(izq) == valorATexto(der));
                break;
            }
            case OpCode::OP_DIFERENTE: {
                Valor der = pop(); Valor izq = pop();
                if (esNumerico(izq) && esNumerico(der)) push(aDouble(izq) != aDouble(der));
                else push(valorATexto(izq) != valorATexto(der));
                break;
            }
            case OpCode::OP_MENOR: {
                Valor der = pop(); Valor izq = pop();
                push(aDouble(izq) < aDouble(der));
                break;
            }
            case OpCode::OP_MAYOR: {
                Valor der = pop(); Valor izq = pop();
                push(aDouble(izq) > aDouble(der));
                break;
            }
            case OpCode::OP_Y: {
                Valor der = pop(); Valor izq = pop();
                push(aBool(izq) && aBool(der));
                break;
            }
            case OpCode::OP_O: {
                Valor der = pop(); Valor izq = pop();
                push(aBool(izq) || aBool(der));
                break;
            }
            case OpCode::OP_NEGAR: {
                Valor v = pop();
                if (std::holds_alternative<int>(v)) push(-std::get<int>(v));
                else push(-aDouble(v));
                break;
            }
            case OpCode::OP_NO: {
                Valor v = pop();
                push(!aBool(v));
                break;
            }

            case OpCode::OP_LISTA: {
                uint32_t n = leerU32(codigo, ip); ip += 4;
                auto lista = std::make_shared<ListaValor>();
                lista->elementos.resize(n);
                for (uint32_t i = 0; i < n; ++i) {
                    lista->elementos[n - 1 - i] = pop();
                }
                push(lista);
                break;
            }
            case OpCode::OP_DICCIONARIO: {
                uint32_t n = leerU32(codigo, ip); ip += 4;
                std::vector<std::pair<Valor, Valor>> pares(n);
                for (uint32_t i = 0; i < n; ++i) {
                    Valor valor = pop();
                    Valor clave = pop();
                    pares[n - 1 - i] = {clave, valor};
                }
                auto dicc = std::make_shared<DiccionarioValor>();
                for (auto& par : pares) {
                    std::string clave = std::holds_alternative<std::string>(par.first)
                        ? std::get<std::string>(par.first) : valorATexto(par.first);
                    dicc->asignar(clave, par.second);
                }
                push(dicc);
                break;
            }
            case OpCode::OP_INDEXAR: {
                Valor indice = pop();
                Valor contenedor = pop();
                if (std::holds_alternative<std::shared_ptr<DiccionarioValor>>(contenedor)) {
                    std::string clave = std::holds_alternative<std::string>(indice)
                        ? std::get<std::string>(indice) : valorATexto(indice);
                    auto dicc = std::get<std::shared_ptr<DiccionarioValor>>(contenedor);
                    Valor* encontrado = dicc->buscar(clave);
                    if (!encontrado) throw std::runtime_error("Clave no encontrada en el diccionario: " + clave);
                    push(*encontrado);
                } else if (std::holds_alternative<std::shared_ptr<ListaValor>>(contenedor)) {
                    if (!std::holds_alternative<int>(indice))
                        throw std::runtime_error("El indice de una lista debe ser entero");
                    int i = std::get<int>(indice);
                    const auto& elementos = std::get<std::shared_ptr<ListaValor>>(contenedor)->elementos;
                    if (i < 0 || static_cast<size_t>(i) >= elementos.size())
                        throw std::runtime_error("Indice de lista fuera de rango");
                    push(elementos[i]);
                } else {
                    throw std::runtime_error("Se esperaba una lista o diccionario para acceder por indice");
                }
                break;
            }

            case OpCode::OP_IMPRIMIR: {
                Valor v = pop();
                std::cout << valorATexto(v) << std::endl;
                break;
            }

            case OpCode::OP_JUMP: {
                uint32_t destino = leerU32(codigo, ip);
                ip = destino;
                break;
            }
            case OpCode::OP_JUMP_IF_FALSE: {
                uint32_t destino = leerU32(codigo, ip); ip += 4;
                Valor cond = pop();
                if (!aBool(cond)) ip = destino;
                break;
            }

            case OpCode::OP_ITER_CREAR: {
                Valor v = pop();
                VMBytecode::Iterador it;
                if (std::holds_alternative<std::shared_ptr<ListaValor>>(v)) {
                    it.tipo = VMBytecode::Iterador::Tipo::LISTA;
                    it.lista = std::get<std::shared_ptr<ListaValor>>(v);
                } else if (std::holds_alternative<std::shared_ptr<DiccionarioValor>>(v)) {
                    it.tipo = VMBytecode::Iterador::Tipo::DICCIONARIO;
                    it.diccionario = std::get<std::shared_ptr<DiccionarioValor>>(v);
                } else if (std::holds_alternative<int>(v)) {
                    it.tipo = VMBytecode::Iterador::Tipo::RANGO;
                    it.rango_limite = std::get<int>(v);
                } else if (std::holds_alternative<double>(v)) {
                    it.tipo = VMBytecode::Iterador::Tipo::RANGO;
                    it.rango_limite = static_cast<int>(std::get<double>(v));
                } else {
                    throw std::runtime_error(
                        "El iterador del bucle 'para ... en ...' debe ser una lista, "
                        "diccionario o un rango numerico");
                }
                pila_iteradores.push_back(std::move(it));
                break;
            }
            case OpCode::OP_ITER_SIGUIENTE: {
                uint32_t destino = leerU32(codigo, ip); ip += 4;
                if (pila_iteradores.empty())
                    throw std::runtime_error("VM: pila de iteradores vacia");
                VMBytecode::Iterador& it = pila_iteradores.back();

                bool hay_siguiente = false;
                Valor valor_siguiente;
                switch (it.tipo) {
                    case VMBytecode::Iterador::Tipo::LISTA:
                        if (it.indice < it.lista->elementos.size()) {
                            valor_siguiente = it.lista->elementos[it.indice++];
                            hay_siguiente = true;
                        }
                        break;
                    case VMBytecode::Iterador::Tipo::DICCIONARIO:
                        if (it.indice < it.diccionario->elementos.size()) {
                            valor_siguiente = it.diccionario->elementos[it.indice++].second;
                            hay_siguiente = true;
                        }
                        break;
                    case VMBytecode::Iterador::Tipo::RANGO:
                        if (it.rango_actual < it.rango_limite) {
                            valor_siguiente = it.rango_actual++;
                            hay_siguiente = true;
                        }
                        break;
                }

                if (hay_siguiente) {
                    push(valor_siguiente);
                } else {
                    pila_iteradores.pop_back();
                    ip = destino;
                }
                break;
            }

            case OpCode::OP_RANGO: {
                uint32_t n_args = leerU32(codigo, ip); ip += 4;
                int inicio = 0;
                int fin;
                if (n_args == 1) {
                    Valor v_fin = pop();
                    if (!std::holds_alternative<int>(v_fin))
                        throw std::runtime_error("rango() espera un entero");
                    fin = std::get<int>(v_fin);
                } else if (n_args == 2) {
                    Valor v_fin = pop();
                    Valor v_inicio = pop();
                    if (!std::holds_alternative<int>(v_inicio) || !std::holds_alternative<int>(v_fin))
                        throw std::runtime_error("rango() espera enteros");
                    inicio = std::get<int>(v_inicio);
                    fin = std::get<int>(v_fin);
                } else {
                    throw std::runtime_error("rango() acepta 1 o 2 argumentos");
                }
                auto resultado = std::make_shared<ListaValor>();
                for (int i = inicio; i < fin; ++i) resultado->elementos.push_back(i);
                push(resultado);
                break;
            }

            case OpCode::OP_HALT:
                return;

            default:
                throw std::runtime_error("VM: opcode desconocido");
        }
    }
}
