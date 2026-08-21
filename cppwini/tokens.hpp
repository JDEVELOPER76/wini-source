// token.hpp
#pragma once
#include <string>
#include <iostream>
#include <variant>  // C++17 para guardar diferentes tipos de valores
#include <optional>

// Tipos de datos soportados en el lenguaje
enum class TipoDato {
    ENTERO,
    DECIMAL,
    CADENA,
    BOOLEANO,
    NULO,
    LISTA,
    DICCIONARIO,
    DESCONOCIDO
};

struct Token {
    enum class Tipo {
        // Identificadores y literales
        IDENTIFICADOR,     // variable, funcion, clase
        NUMERO,            // 123, 45.67
        CADENA,            // "hola mundo"
        BOOLEANO,          // true, false
        LISTA,             // [1,2,3]
        DICCIONARIO,       // { "clave": "valor" }
        NULO,              // null
        
        // Palabras clave (keywords)
        PALABRA_CLAVE_IF,
        PALABRA_CLAVE_ELSE,
        PALABRA_CLAVE_WHILE,
        PALABRA_CLAVE_FOR,
        PALABRA_CLAVE_EN,
        PALABRA_CLAVE_FUNCTION,
        PALABRA_CLAVE_RETURN,
        PALABRA_CLAVE_PRINT,
        PALABRA_CLAVE_CONST,
        
        // Tipos de datos (para declaraciones estáticas)
        TIPO_ENTERO,
        TIPO_DECIMAL,
        TIPO_CADENA,
        TIPO_BOOLEANO,
        TIPO_LISTA,
        TIPO_DICCIONARIO,
        TIPO_NULO,
        TIPO_VOID,
        
        // Operadores
        OPERADOR_MAS,        // +
        OPERADOR_MENOS,      // -
        OPERADOR_MULTIPLICAR,// *
        OPERADOR_DIVIDIR,    // /
        OPERADOR_ASIGNAR,    // =
        OPERADOR_IGUAL,      // ==
        OPERADOR_DIFERENTE,  // !=
        OPERADOR_MENOR_QUE,  // <
        OPERADOR_MAYOR_QUE,  // >
        OPERADOR_Y,          // && o "y"
        OPERADOR_O,          // || o "o"
        OPERADOR_NO,         // ! o "no"
        OPERADOR_INCREMENTO, // ++
        OPERADOR_DECREMENTO, // --
        
        // Puntuación/Delimitadores
        PARENTESIS_IZQUIERDO,   // (
        PARENTESIS_DERECHO,     // )
        LLAVE_IZQUIERDA,        // {
        LLAVE_DERECHA,          // }
        CORCHETE_IZQUIERDO,     // [
        CORCHETE_DERECHO,       // ]
        PUNTO_Y_COMA,           // ;
        COMA,                   // ,
        PUNTO,                  // .
        DOS_PUNTOS,             // :
        
        // Especiales
        FIN_DE_ARCHIVO,      // Fin del archivo
        ESPACIO,              // Espacio en blanco
        COMENTARIO,           // Comentario
        DESCONOCIDO          // Para errores
    };
    
    Tipo tipo;               // Tipo del token
    std::string lexema;      // Texto original (ej. "variable123")
    int linea;               // Número de línea para errores
    int columna;             // Columna para errores
    
    // Información de tipo para variables (lenguaje estático)
    TipoDato tipo_dato;
    bool es_constante;
    
    // Valor opcional (para números, cadenas, etc.)
    std::variant<std::monostate, int, double, std::string, bool> valor;
    
    // Constructores
    Token() : tipo(Tipo::DESCONOCIDO), lexema(""), linea(0), columna(0), 
              tipo_dato(TipoDato::DESCONOCIDO), es_constante(false) {}
    
    Token(Tipo t, const std::string& lex, int l, int c) 
        : tipo(t), lexema(lex), linea(l), columna(c),
          tipo_dato(TipoDato::DESCONOCIDO), es_constante(false) {}
    
    Token(Tipo t, const std::string& lex, int l, int c, int num_val) 
        : tipo(t), lexema(lex), linea(l), columna(c), valor(num_val),
          tipo_dato(TipoDato::ENTERO), es_constante(false) {}
    
    Token(Tipo t, const std::string& lex, int l, int c, double num_val) 
        : tipo(t), lexema(lex), linea(l), columna(c), valor(num_val),
          tipo_dato(TipoDato::DECIMAL), es_constante(false) {}
    
    Token(Tipo t, const std::string& lex, int l, int c, const std::string& str_val) 
        : tipo(t), lexema(lex), linea(l), columna(c), valor(str_val),
          tipo_dato(TipoDato::CADENA), es_constante(false) {}
    
    Token(Tipo t, const std::string& lex, int l, int c, bool bool_val) 
        : tipo(t), lexema(lex), linea(l), columna(c), valor(bool_val),
          tipo_dato(TipoDato::BOOLEANO), es_constante(false) {}
    
    // Constructor para tipo de dato
    Token(Tipo t, TipoDato td, const std::string& lex, int l, int c)
        : tipo(t), lexema(lex), linea(l), columna(c),
          tipo_dato(td), es_constante(false) {}
    
    // Método para imprimir el token (debug)
    friend std::ostream& operator<<(std::ostream& os, const Token& token) {
        os << "Token{tipo: " << static_cast<int>(token.tipo) 
           << ", lexema: '" << token.lexema 
           << "', linea: " << token.linea 
           << ", col: " << token.columna;
        
        if (token.tipo_dato != TipoDato::DESCONOCIDO) {
            os << ", tipo_dato: " << static_cast<int>(token.tipo_dato);
        }
        
        if (token.es_constante) {
            os << ", constante: true";
        }
        
        os << "}";
        return os;
    }
};