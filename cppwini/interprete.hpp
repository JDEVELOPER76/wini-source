// interprete.hpp
#pragma once
#include <string>
#include <unordered_map>
#include <variant>
#include <stdexcept>
#include <sstream>
#include <iostream>
#include <memory>
#include <vector>
#include <cmath>
#include "ast.hpp"
#include "valores.hpp"

class Interprete {
private:
    struct Variable {
        Valor valor;
        TipoDato tipo;
        bool es_constante;
    };

    std::unordered_map<std::string, Variable> entorno;

    Valor evaluarBinaria(AST::ExpresionBinaria* expr) {
        // Asignacion: x = expr
        if (expr->operador == AST::ExpresionBinaria::Operador::ASIGNACION) {
            auto* var = dynamic_cast<AST::ExpresionVariable*>(expr->izquierda.get());
            if (!var) throw std::runtime_error("Lado izquierdo de '=' invalido");
            auto it = entorno.find(var->nombre);
            if (it == entorno.end())
                throw std::runtime_error("Variable no declarada: " + var->nombre);
            if (it->second.es_constante)
                throw std::runtime_error("No se puede reasignar la constante: " + var->nombre);
            Valor nuevo = evaluar(expr->derecha.get());
            it->second.valor = nuevo;
            return nuevo;
        }

        Valor izq = evaluar(expr->izquierda.get());
        Valor der = evaluar(expr->derecha.get());

        using Op = AST::ExpresionBinaria::Operador;

        // Concatenacion si alguno de los dos lados es cadena y el operador es SUMA
        if (expr->operador == Op::SUMA &&
            (std::holds_alternative<std::string>(izq) || std::holds_alternative<std::string>(der))) {
            return valorATexto(izq) + valorATexto(der);
        }

        switch (expr->operador) {
            case Op::SUMA: {
                if (std::holds_alternative<int>(izq) && std::holds_alternative<int>(der))
                    return std::get<int>(izq) + std::get<int>(der);
                return aDouble(izq) + aDouble(der);
            }
            case Op::RESTA: {
                if (std::holds_alternative<int>(izq) && std::holds_alternative<int>(der))
                    return std::get<int>(izq) - std::get<int>(der);
                return aDouble(izq) - aDouble(der);
            }
            case Op::MULTIPLICACION: {
                if (std::holds_alternative<int>(izq) && std::holds_alternative<int>(der))
                    return std::get<int>(izq) * std::get<int>(der);
                return aDouble(izq) * aDouble(der);
            }
            case Op::DIVISION: {
                double d = aDouble(der);
                if (d == 0) throw std::runtime_error("Division entre cero");
                return aDouble(izq) / d;
            }
            case Op::IGUAL:
                if (esNumerico(izq) && esNumerico(der)) return aDouble(izq) == aDouble(der);
                return valorATexto(izq) == valorATexto(der);
            case Op::DIFERENTE:
                if (esNumerico(izq) && esNumerico(der)) return aDouble(izq) != aDouble(der);
                return valorATexto(izq) != valorATexto(der);
            case Op::MENOR_QUE:
                return aDouble(izq) < aDouble(der);
            case Op::MAYOR_QUE:
                return aDouble(izq) > aDouble(der);
            case Op::Y:
                return aBool(izq) && aBool(der);
            case Op::O:
                return aBool(izq) || aBool(der);
            default:
                throw std::runtime_error("Operador binario no soportado");
        }
    }

    Valor evaluarUnaria(AST::ExpresionUnaria* expr) {
        Valor v = evaluar(expr->operando.get());
        if (expr->operador == AST::ExpresionUnaria::Operador::NEGATIVO) {
            if (std::holds_alternative<int>(v)) return -std::get<int>(v);
            return -aDouble(v);
        }
        // NO
        return !aBool(v);
    }

public:
    Valor evaluar(AST::Expresion* expr) {
        if (!expr) return std::monostate{};
        if (auto* llamada = dynamic_cast<AST::ExpresionLlamada*>(expr)) {
            if (llamada->nombre_funcion == "rango" || llamada->nombre_funcion == "range") {
                if (llamada->argumentos.size() == 1) {
                    auto fin = evaluar(llamada->argumentos[0].get());
                    if (!std::holds_alternative<int>(fin)) {
                        throw std::runtime_error("rango() espera un entero");
                    }
                    auto resultado = std::make_shared<ListaValor>();
                    for (int i = 0; i < std::get<int>(fin); ++i) {
                        resultado->elementos.push_back(i);
                    }
                    return resultado;
                }
                if (llamada->argumentos.size() == 2) {
                    auto inicio = evaluar(llamada->argumentos[0].get());
                    auto fin = evaluar(llamada->argumentos[1].get());
                    if (!std::holds_alternative<int>(inicio) || !std::holds_alternative<int>(fin)) {
                        throw std::runtime_error("rango() espera enteros");
                    }
                    auto resultado = std::make_shared<ListaValor>();
                    for (int i = std::get<int>(inicio); i < std::get<int>(fin); ++i) {
                        resultado->elementos.push_back(i);
                    }
                    return resultado;
                }
                throw std::runtime_error("rango() acepta 1 o 2 argumentos");
            }
            throw std::runtime_error("La funcion '" + llamada->nombre_funcion + "' no esta implementada");
        }
        if (auto* lit = dynamic_cast<AST::ExpresionLiteral*>(expr)) {
            return std::visit([](auto&& val) -> Valor { return val; }, lit->valor);
        }
        if (auto* var = dynamic_cast<AST::ExpresionVariable*>(expr)) {
            auto it = entorno.find(var->nombre);
            if (it == entorno.end())
                throw std::runtime_error("Variable no declarada: " + var->nombre);
            return it->second.valor;
        }
        if (auto* bin = dynamic_cast<AST::ExpresionBinaria*>(expr)) {
            return evaluarBinaria(bin);
        }
        if (auto* un = dynamic_cast<AST::ExpresionUnaria*>(expr)) {
            return evaluarUnaria(un);
        }
        if (auto* lista = dynamic_cast<AST::ExpresionLista*>(expr)) {
            auto resultado = std::make_shared<ListaValor>();
            for (const auto& elemento : lista->elementos) {
                resultado->elementos.push_back(evaluar(elemento.get()));
            }
            return resultado;
        }
        if (auto* dicc = dynamic_cast<AST::ExpresionDiccionario*>(expr)) {
            auto resultado = std::make_shared<DiccionarioValor>();
            for (const auto& par : dicc->pares) {
                Valor clave_val = evaluar(par.first.get());
                std::string clave = std::holds_alternative<std::string>(clave_val)
                    ? std::get<std::string>(clave_val)
                    : valorATexto(clave_val);
                resultado->asignar(clave, evaluar(par.second.get()));
            }
            return resultado;
        }
        if (auto* acceso = dynamic_cast<AST::ExpresionAccesoLista*>(expr)) {
            Valor contenedor = evaluar(acceso->lista.get());

            if (std::holds_alternative<std::shared_ptr<DiccionarioValor>>(contenedor)) {
                Valor valor_clave = evaluar(acceso->indice.get());
                std::string clave = std::holds_alternative<std::string>(valor_clave)
                    ? std::get<std::string>(valor_clave)
                    : valorATexto(valor_clave);
                auto dicc = std::get<std::shared_ptr<DiccionarioValor>>(contenedor);
                Valor* encontrado = dicc->buscar(clave);
                if (!encontrado)
                    throw std::runtime_error("Clave no encontrada en el diccionario: " + clave);
                return *encontrado;
            }

            if (!std::holds_alternative<std::shared_ptr<ListaValor>>(contenedor))
                throw std::runtime_error("Se esperaba una lista o diccionario para acceder por indice");
            Valor valor_indice = evaluar(acceso->indice.get());
            if (!std::holds_alternative<int>(valor_indice))
                throw std::runtime_error("El indice de una lista debe ser entero");
            int indice = std::get<int>(valor_indice);
            const auto& elementos = std::get<std::shared_ptr<ListaValor>>(contenedor)->elementos;
            if (indice < 0 || static_cast<size_t>(indice) >= elementos.size())
                throw std::runtime_error("Indice de lista fuera de rango");
            return elementos[indice];
        }
        throw std::runtime_error("Tipo de expresion no soportado por el interprete");
    }

    void ejecutar(AST::Sentencia* sent) {
        if (auto* decl = dynamic_cast<AST::DeclaracionVariable*>(sent)) {
            Valor valor = std::monostate{};
            if (decl->valor_inicial) {
                valor = evaluar(decl->valor_inicial.get());
            }
            entorno[decl->nombre] = Variable{valor, decl->tipo, decl->es_constante};
            return;
        }
        if (auto* impr = dynamic_cast<AST::SentenciaPrint*>(sent)) {
            Valor valor = evaluar(impr->expresion.get());
            std::cout << valorATexto(valor) << std::endl;
            return;
        }
        if (auto* for_en = dynamic_cast<AST::SentenciaForEn*>(sent)) {
            Valor iterable = evaluar(for_en->iterable.get());

            if (std::holds_alternative<std::shared_ptr<ListaValor>>(iterable)) {
                auto lista = std::get<std::shared_ptr<ListaValor>>(iterable);
                for (const auto& elemento : lista->elementos) {
                    entorno[for_en->nombre_variable] = Variable{elemento, TipoDato::DESCONOCIDO, false};
                    for (const auto& cuerpo_sent : for_en->cuerpo) {
                        ejecutar(cuerpo_sent.get());
                    }
                }
                return;
            }

            if (std::holds_alternative<std::shared_ptr<DiccionarioValor>>(iterable)) {
                auto dicc = std::get<std::shared_ptr<DiccionarioValor>>(iterable);
                for (const auto& par : dicc->elementos) {
                    entorno[for_en->nombre_variable] = Variable{par.second, TipoDato::DESCONOCIDO, false};
                    for (const auto& cuerpo_sent : for_en->cuerpo) {
                        ejecutar(cuerpo_sent.get());
                    }
                }
                return;
            }

            if (std::holds_alternative<int>(iterable)) {
                int limite = std::get<int>(iterable);
                for (int i = 0; i < limite; ++i) {
                    entorno[for_en->nombre_variable] = Variable{int(i), TipoDato::DESCONOCIDO, false};
                    for (const auto& cuerpo_sent : for_en->cuerpo) {
                        ejecutar(cuerpo_sent.get());
                    }
                }
                return;
            }

            if (std::holds_alternative<double>(iterable)) {
                double limite = std::get<double>(iterable);
                for (int i = 0; i < static_cast<int>(limite); ++i) {
                    entorno[for_en->nombre_variable] = Variable{int(i), TipoDato::DESCONOCIDO, false};
                    for (const auto& cuerpo_sent : for_en->cuerpo) {
                        ejecutar(cuerpo_sent.get());
                    }
                }
                return;
            }

            throw std::runtime_error("El iterador del bucle 'para ... en ...' debe ser una lista, diccionario o un rango numerico");
        }
        throw std::runtime_error("Tipo de sentencia no soportado por el interprete");
    }

    void ejecutar(AST::Programa* programa) {
        for (auto& sent : programa->sentencias) {
            ejecutar(sent.get());
        }
    }
};
