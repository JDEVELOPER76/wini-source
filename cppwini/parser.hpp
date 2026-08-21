// parser.hpp
#pragma once
#include <vector>
#include <memory>
#include "lexer.hpp"
#include "ast.hpp"  // Árbol de sintaxis abstracta

class Parser {
private:
    std::vector<Token> tokens;
    size_t posicion;
    Token token_actual;

    // Métodos de parsing
    void siguienteToken();
    bool coincidir(Token::Tipo tipo);
    bool esperar(Token::Tipo tipo, const std::string& mensaje_error);

    // Reglas gramaticales
    std::unique_ptr<AST::Programa> parsePrograma();
    std::unique_ptr<AST::Sentencia> parseSentencia();
    std::unique_ptr<AST::DeclaracionVariable> parseDeclaracionVariable();
    std::unique_ptr<AST::Sentencia> parseImprimir();
    std::unique_ptr<AST::Sentencia> parseForEn();
    std::vector<std::unique_ptr<AST::Sentencia>> parseBloque();
    std::unique_ptr<AST::Expresion> parseExpresion();
    std::unique_ptr<AST::Expresion> parseExpresionLogica();
    std::unique_ptr<AST::Expresion> parseExpresionComparacion();
    std::unique_ptr<AST::Expresion> parseExpresionAritmetica();
    std::unique_ptr<AST::Expresion> parseExpresionUnaria();
    std::unique_ptr<AST::Expresion> parseFactor();
    std::unique_ptr<AST::Expresion> parseListaLiteral();
    std::unique_ptr<AST::Expresion> parseDiccionarioLiteral();

public:
    Parser(const std::vector<Token>& tokens);
    std::unique_ptr<AST::Programa> parse();
};
