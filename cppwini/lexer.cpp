// lexer.cpp
#include <iostream>
#include <string>
#include <vector>
#include <unordered_map>
#include <cctype>
#include <optional>
#include "tokens.hpp"

class Lexer {
private:
    std::string codigo_fuente;
    size_t posicion;
    int linea;
    int columna;
    std::vector<Token> tokens;
    
    // Palabras clave del lenguaje
    std::unordered_map<std::string, Token::Tipo> palabras_clave = {
        // Estructuras de control
        {"si", Token::Tipo::PALABRA_CLAVE_IF},
        {"sino", Token::Tipo::PALABRA_CLAVE_ELSE},
        {"mientras", Token::Tipo::PALABRA_CLAVE_WHILE},
        {"para", Token::Tipo::PALABRA_CLAVE_FOR},
        {"en", Token::Tipo::PALABRA_CLAVE_EN},
        
        // Funciones
        {"func", Token::Tipo::PALABRA_CLAVE_FUNCTION},
        {"retornar", Token::Tipo::PALABRA_CLAVE_RETURN},
        {"imprimir", Token::Tipo::PALABRA_CLAVE_PRINT},
        
        // Declaraciones
        {"const", Token::Tipo::PALABRA_CLAVE_CONST},
        
        // Tipos de datos (para lenguaje estático)
        {"entero", Token::Tipo::TIPO_ENTERO},
        {"decimal", Token::Tipo::TIPO_DECIMAL},
        {"cadena", Token::Tipo::TIPO_CADENA},
        {"booleano", Token::Tipo::TIPO_BOOLEANO},
        {"lista", Token::Tipo::TIPO_LISTA},
        {"diccionario", Token::Tipo::TIPO_DICCIONARIO},
        {"nulo", Token::Tipo::TIPO_NULO},
        {"vacio", Token::Tipo::TIPO_VOID},
        
        // Valores literales
        {"verdadero", Token::Tipo::BOOLEANO},
        {"falso", Token::Tipo::BOOLEANO},
        {"nada", Token::Tipo::NULO},
        
        // Operadores lógicos en español
        {"y", Token::Tipo::OPERADOR_Y},
        {"o", Token::Tipo::OPERADOR_O},
        {"no", Token::Tipo::OPERADOR_NO}
    };

    // Mapa para convertir tipo de token a TipoDato
    std::unordered_map<Token::Tipo, TipoDato> tipo_a_dato = {
        {Token::Tipo::TIPO_ENTERO, TipoDato::ENTERO},
        {Token::Tipo::TIPO_DECIMAL, TipoDato::DECIMAL},
        {Token::Tipo::TIPO_CADENA, TipoDato::CADENA},
        {Token::Tipo::TIPO_BOOLEANO, TipoDato::BOOLEANO},
        {Token::Tipo::TIPO_LISTA, TipoDato::LISTA},
        {Token::Tipo::TIPO_DICCIONARIO, TipoDato::DICCIONARIO},
        {Token::Tipo::TIPO_NULO, TipoDato::NULO},
        {Token::Tipo::TIPO_VOID, TipoDato::DESCONOCIDO}
    };

    // Caracteres que son operadores de un solo carácter
    std::unordered_map<char, Token::Tipo> operadores_simples = {
        {'+', Token::Tipo::OPERADOR_MAS},
        {'-', Token::Tipo::OPERADOR_MENOS},
        {'*', Token::Tipo::OPERADOR_MULTIPLICAR},
        {'/', Token::Tipo::OPERADOR_DIVIDIR},
        {'=', Token::Tipo::OPERADOR_ASIGNAR},
        {'<', Token::Tipo::OPERADOR_MENOR_QUE},
        {'>', Token::Tipo::OPERADOR_MAYOR_QUE},
        {'!', Token::Tipo::OPERADOR_NO},
        {'(', Token::Tipo::PARENTESIS_IZQUIERDO},
        {')', Token::Tipo::PARENTESIS_DERECHO},
        {'{', Token::Tipo::LLAVE_IZQUIERDA},
        {'}', Token::Tipo::LLAVE_DERECHA},
        {'[', Token::Tipo::CORCHETE_IZQUIERDO},
        {']', Token::Tipo::CORCHETE_DERECHO},
        {';', Token::Tipo::PUNTO_Y_COMA},
        {',', Token::Tipo::COMA},
        {'.', Token::Tipo::PUNTO},
        {':', Token::Tipo::DOS_PUNTOS}
    };

    // Contexto de análisis (para saber si estamos declarando una variable)
    enum class Contexto {
        NORMAL,
        DECLARACION_VARIABLE,
        DECLARACION_CONSTANTE
    };
    Contexto contexto_actual = Contexto::NORMAL;

public:
    Lexer(const std::string& codigo) 
        : codigo_fuente(codigo), posicion(0), linea(1), columna(1) {}

    std::vector<Token> analizar() {
        while (posicion < codigo_fuente.length()) {
            char caracter_actual = codigo_fuente[posicion];
            
            if (std::isspace(caracter_actual)) {
                manejarEspacio();
            }
            else if (caracter_actual == '/' && posicion + 1 < codigo_fuente.length() && codigo_fuente[posicion + 1] == '/') {
                manejarComentario();
            }
            else if (caracter_actual == '"') {
                manejarCadena();
            }
            else if (std::isdigit(caracter_actual)) {
                manejarNumero();
            }
            else if (std::isalpha(caracter_actual) || caracter_actual == '_') {
                manejarIdentificador();
            }
            else {
                manejarOperadorODelimitador();
            }
        }
        
        // Añadir token de fin de archivo
        tokens.push_back(Token(Token::Tipo::FIN_DE_ARCHIVO, "EOF", linea, columna));
        return tokens;
    }

private:
    void manejarEspacio() {
        char c = codigo_fuente[posicion];
        if (c == '\n') {
            linea++;
            columna = 1;
        } else {
            columna++;
        }
        posicion++;
    }

    void manejarComentario() {
        posicion += 2;
        columna += 2;
        
        while (posicion < codigo_fuente.length() && codigo_fuente[posicion] != '\n') {
            posicion++;
            columna++;
        }
    }

    void manejarCadena() {
        int col_inicio = columna;
        int line_inicio = linea;
        posicion++;
        columna++;
        
        std::string valor_cadena;
        
        while (posicion < codigo_fuente.length() && codigo_fuente[posicion] != '"') {
            if (codigo_fuente[posicion] == '\\') {
                posicion++;
                columna++;
                if (posicion < codigo_fuente.length()) {
                    char escape = codigo_fuente[posicion];
                    switch (escape) {
                        case 'n': valor_cadena += '\n'; break;
                        case 't': valor_cadena += '\t'; break;
                        case '"': valor_cadena += '"'; break;
                        case '\\': valor_cadena += '\\'; break;
                        default: valor_cadena += escape; break;
                    }
                    posicion++;
                    columna++;
                }
            } else {
                if (codigo_fuente[posicion] == '\n') {
                    linea++;
                    columna = 1;
                } else {
                    columna++;
                }
                valor_cadena += codigo_fuente[posicion];
                posicion++;
            }
        }
        
        if (posicion < codigo_fuente.length() && codigo_fuente[posicion] == '"') {
            posicion++;
            columna++;
        }
        
        Token token(Token::Tipo::CADENA, "\"" + valor_cadena + "\"", 
                    line_inicio, col_inicio, valor_cadena);
        token.tipo_dato = TipoDato::CADENA;
        tokens.push_back(token);
    }

    void manejarNumero() {
        int col_inicio = columna;
        int line_inicio = linea;
        std::string numero_str;
        bool es_decimal = false;
        
        while (posicion < codigo_fuente.length() && 
               (std::isdigit(codigo_fuente[posicion]) || codigo_fuente[posicion] == '.')) {
            if (codigo_fuente[posicion] == '.') {
                if (es_decimal) break;
                es_decimal = true;
            }
            numero_str += codigo_fuente[posicion];
            posicion++;
            columna++;
        }
        
        Token token;
        if (es_decimal) {
            double valor = std::stod(numero_str);
            token = Token(Token::Tipo::NUMERO, numero_str, line_inicio, col_inicio, valor);
        } else {
            int valor = std::stoi(numero_str);
            token = Token(Token::Tipo::NUMERO, numero_str, line_inicio, col_inicio, valor);
        }
        tokens.push_back(token);
    }

    void manejarIdentificador() {
        int col_inicio = columna;
        int line_inicio = linea;
        std::string identificador;
        
        while (posicion < codigo_fuente.length() && 
               (std::isalnum(codigo_fuente[posicion]) || codigo_fuente[posicion] == '_')) {
            identificador += codigo_fuente[posicion];
            posicion++;
            columna++;
        }
        
        auto it = palabras_clave.find(identificador);
        if (it != palabras_clave.end()) {
            Token::Tipo tipo_token = it->second;
            
            // Verificar si es un tipo de dato
            if (tipo_token == Token::Tipo::TIPO_ENTERO ||
                tipo_token == Token::Tipo::TIPO_DECIMAL ||
                tipo_token == Token::Tipo::TIPO_CADENA ||
                tipo_token == Token::Tipo::TIPO_BOOLEANO ||
                tipo_token == Token::Tipo::TIPO_LISTA ||
                tipo_token == Token::Tipo::TIPO_DICCIONARIO ||
                tipo_token == Token::Tipo::TIPO_NULO ||
                tipo_token == Token::Tipo::TIPO_VOID) {
                
                TipoDato tipo_dato = tipo_a_dato[tipo_token];
                Token token(tipo_token, tipo_dato, identificador, line_inicio, col_inicio);
                
                // Contexto de declaración (solo const)
                if (contexto_actual == Contexto::DECLARACION_CONSTANTE) {
                    // Estamos en una declaración constante, el siguiente token debe ser un identificador
                }
                
                tokens.push_back(token);
            }
            else if (tipo_token == Token::Tipo::BOOLEANO) {
                bool valor = (identificador == "verdadero");
                Token token(tipo_token, identificador, line_inicio, col_inicio, valor);
                token.tipo_dato = TipoDato::BOOLEANO;
                tokens.push_back(token);
            }
            else if (tipo_token == Token::Tipo::NULO) {
                Token token(tipo_token, identificador, line_inicio, col_inicio);
                token.tipo_dato = TipoDato::NULO;
                tokens.push_back(token);
            }
            else if (tipo_token == Token::Tipo::PALABRA_CLAVE_CONST) {
                contexto_actual = Contexto::DECLARACION_CONSTANTE;
                tokens.push_back(Token(tipo_token, identificador, line_inicio, col_inicio));
            }
            else {
                tokens.push_back(Token(tipo_token, identificador, line_inicio, col_inicio));
            }
        } else {
            // Es un identificador normal
            Token token(Token::Tipo::IDENTIFICADOR, identificador, line_inicio, col_inicio);
            
            // Si estamos en contexto de declaración constante, el identificador es una variable
            if (contexto_actual == Contexto::DECLARACION_CONSTANTE) {
                token.es_constante = true;
                contexto_actual = Contexto::NORMAL;
            }
            
            tokens.push_back(token);
        }
    }

    void manejarOperadorODelimitador() {
        int col_inicio = columna;
        int line_inicio = linea;
        char c = codigo_fuente[posicion];
        
        if (posicion + 1 < codigo_fuente.length()) {
            char siguiente = codigo_fuente[posicion + 1];
            
            if (c == '=' && siguiente == '=') {
                tokens.push_back(Token(Token::Tipo::OPERADOR_IGUAL, "==", 
                                       line_inicio, col_inicio));
                posicion += 2;
                columna += 2;
                return;
            }
            else if (c == '!' && siguiente == '=') {
                tokens.push_back(Token(Token::Tipo::OPERADOR_DIFERENTE, "!=", 
                                       line_inicio, col_inicio));
                posicion += 2;
                columna += 2;
                return;
            }
            else if (c == '&' && siguiente == '&') {
                tokens.push_back(Token(Token::Tipo::OPERADOR_Y, "&&", 
                                       line_inicio, col_inicio));
                posicion += 2;
                columna += 2;
                return;
            }
            else if (c == '|' && siguiente == '|') {
                tokens.push_back(Token(Token::Tipo::OPERADOR_O, "||", 
                                       line_inicio, col_inicio));
                posicion += 2;
                columna += 2;
                return;
            }
            else if (c == '+' && siguiente == '+') {
                tokens.push_back(Token(Token::Tipo::OPERADOR_INCREMENTO, "++", 
                                       line_inicio, col_inicio));
                posicion += 2;
                columna += 2;
                return;
            }
            else if (c == '-' && siguiente == '-') {
                tokens.push_back(Token(Token::Tipo::OPERADOR_DECREMENTO, "--", 
                                       line_inicio, col_inicio));
                posicion += 2;
                columna += 2;
                return;
            }
        }
        
        auto it = operadores_simples.find(c);
        if (it != operadores_simples.end()) {
            tokens.push_back(Token(it->second, std::string(1, c), 
                                   line_inicio, col_inicio));
            posicion++;
            columna++;
        } else {
            tokens.push_back(Token(Token::Tipo::DESCONOCIDO, std::string(1, c), 
                                   line_inicio, col_inicio));
            posicion++;
            columna++;
        }
    }

public:
    void imprimirTokens() {
        for (const auto& token : tokens) {
            std::cout << token << std::endl;
        }
    }
};
