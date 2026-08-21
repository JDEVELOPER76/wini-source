// ast.hpp
#pragma once
#include <string>
#include <vector>
#include <memory>
#include <variant>
#include "tokens.hpp"

namespace AST {

// Nodos base
struct Nodo {
    virtual ~Nodo() = default;
};

struct Sentencia : Nodo {
    // Clase base para sentencias
};

// ---------------------------------------------------------
// Expresiones (definidas primero: las sentencias las usan)
// ---------------------------------------------------------
struct Expresion : Nodo {
    virtual TipoDato getTipo() const = 0;
};

struct ExpresionLiteral : Expresion {
    std::variant<int, double, std::string, bool> valor;
    TipoDato tipo;

    TipoDato getTipo() const override { return tipo; }
};

// [expresion, expresion, ...]
struct ExpresionLista : Expresion {
    std::vector<std::unique_ptr<Expresion>> elementos;

    TipoDato getTipo() const override { return TipoDato::LISTA; }
};

// { clave: valor, clave: valor, ... }
struct ExpresionDiccionario : Expresion {
    std::vector<std::pair<std::unique_ptr<Expresion>, std::unique_ptr<Expresion>>> pares;

    TipoDato getTipo() const override { return TipoDato::DICCIONARIO; }
};

struct ExpresionVariable : Expresion {
    std::string nombre;
    TipoDato tipo;

    TipoDato getTipo() const override { return tipo; }
};

struct ExpresionBinaria : Expresion {
    enum class Operador {
        SUMA, RESTA, MULTIPLICACION, DIVISION,
        IGUAL, DIFERENTE, MENOR_QUE, MAYOR_QUE,
        Y, O,
        ASIGNACION
    };

    Operador operador;
    std::unique_ptr<Expresion> izquierda;
    std::unique_ptr<Expresion> derecha;
    TipoDato tipo_resultado;

    TipoDato getTipo() const override { return tipo_resultado; }
};

struct ExpresionUnaria : Expresion {
    enum class Operador {
        NEGATIVO, NO
    };

    Operador operador;
    std::unique_ptr<Expresion> operando;
    TipoDato tipo_resultado;

    TipoDato getTipo() const override { return tipo_resultado; }
};

struct ExpresionLlamada : Expresion {
    std::string nombre_funcion;
    std::vector<std::unique_ptr<Expresion>> argumentos;
    TipoDato tipo_retorno;

    TipoDato getTipo() const override { return tipo_retorno; }
};

// lista[indice]
struct ExpresionAccesoLista : Expresion {
    std::unique_ptr<Expresion> lista;
    std::unique_ptr<Expresion> indice;
    TipoDato tipo_elemento = TipoDato::DESCONOCIDO;

    TipoDato getTipo() const override { return tipo_elemento; }
};

// ---------------------------------------------------------
// Sentencias
// ---------------------------------------------------------

// Declaraciones
struct DeclaracionVariable : Sentencia {
    std::string nombre;
    TipoDato tipo;
    bool es_constante;
    std::unique_ptr<Expresion> valor_inicial; // puede ser nullptr
};

struct DeclaracionFuncion : Sentencia {
    std::string nombre;
    TipoDato tipo_retorno;
    std::vector<std::pair<std::string, TipoDato>> parametros;
    std::vector<std::unique_ptr<Sentencia>> cuerpo;
};

// print(expresion);
struct SentenciaPrint : Sentencia {
    std::unique_ptr<Expresion> expresion;
};

// Estructuras de control
struct SentenciaIf : Sentencia {
    std::unique_ptr<Expresion> condicion;
    std::vector<std::unique_ptr<Sentencia>> cuerpo;
    std::vector<std::unique_ptr<Sentencia>> cuerpo_sino;
};

struct SentenciaWhile : Sentencia {
    std::unique_ptr<Expresion> condicion;
    std::vector<std::unique_ptr<Sentencia>> cuerpo;
};

struct SentenciaFor : Sentencia {
    std::unique_ptr<DeclaracionVariable> inicializacion;
    std::unique_ptr<Expresion> condicion;
    std::unique_ptr<Expresion> incremento;
    std::vector<std::unique_ptr<Sentencia>> cuerpo;
};

struct SentenciaForEn : Sentencia {
    std::string nombre_variable;
    std::unique_ptr<Expresion> iterable;
    std::vector<std::unique_ptr<Sentencia>> cuerpo;
};

struct Programa : Nodo {
    std::vector<std::unique_ptr<Sentencia>> sentencias;
};

} // namespace AST
