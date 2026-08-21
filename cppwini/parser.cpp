// parser.cpp
#include "parser.hpp"
#include <stdexcept>

static bool esTokenDeTipo(Token::Tipo t);

Parser::Parser(const std::vector<Token>& tokens_)
    : tokens(tokens_), posicion(0) {
    token_actual = tokens.empty() ? Token() : tokens[0];
}

void Parser::siguienteToken() {
    if (posicion + 1 < tokens.size()) {
        posicion++;
        token_actual = tokens[posicion];
    } else {
        token_actual = Token(Token::Tipo::FIN_DE_ARCHIVO, "EOF",
                              token_actual.linea, token_actual.columna);
    }
}

bool Parser::coincidir(Token::Tipo tipo) {
    if (token_actual.tipo == tipo) {
        siguienteToken();
        return true;
    }
    return false;
}

bool Parser::esperar(Token::Tipo tipo, const std::string& mensaje_error) {
    if (token_actual.tipo == tipo) {
        siguienteToken();
        return true;
    }
    throw std::runtime_error(
        "Error de sintaxis (linea " + std::to_string(token_actual.linea) +
        ", col " + std::to_string(token_actual.columna) + "): " +
        mensaje_error + " -- token encontrado: '" + token_actual.lexema + "'");
}

std::unique_ptr<AST::Programa> Parser::parse() {
    return parsePrograma();
}

std::unique_ptr<AST::Programa> Parser::parsePrograma() {
    auto programa = std::make_unique<AST::Programa>();
    while (token_actual.tipo != Token::Tipo::FIN_DE_ARCHIVO) {
        programa->sentencias.push_back(parseSentencia());
    }
    return programa;
}

std::unique_ptr<AST::Sentencia> Parser::parseSentencia() {
    if (token_actual.tipo == Token::Tipo::PALABRA_CLAVE_CONST ||
        esTokenDeTipo(token_actual.tipo)) {
        return parseDeclaracionVariable();
    }
    if (token_actual.tipo == Token::Tipo::PALABRA_CLAVE_PRINT) {
        return parseImprimir();
    }
    if (token_actual.tipo == Token::Tipo::PALABRA_CLAVE_FOR) {
        return parseForEn();
    }

    throw std::runtime_error(
        "Error de sintaxis (linea " + std::to_string(token_actual.linea) +
        "): sentencia no reconocida -- token: '" + token_actual.lexema + "'");
}

static bool esTokenDeTipo(Token::Tipo t) {
    switch (t) {
        case Token::Tipo::TIPO_ENTERO:
        case Token::Tipo::TIPO_DECIMAL:
        case Token::Tipo::TIPO_CADENA:
        case Token::Tipo::TIPO_BOOLEANO:
        case Token::Tipo::TIPO_LISTA:
        case Token::Tipo::TIPO_DICCIONARIO:
        case Token::Tipo::TIPO_NULO:
        case Token::Tipo::TIPO_VOID:
            return true;
        default:
            return false;
    }
}

std::unique_ptr<AST::DeclaracionVariable> Parser::parseDeclaracionVariable() {
    bool es_constante = false;
    if (token_actual.tipo == Token::Tipo::PALABRA_CLAVE_CONST) {
        es_constante = true;
        siguienteToken();
    }

    if (!esTokenDeTipo(token_actual.tipo)) {
        throw std::runtime_error(
            "Error de sintaxis (linea " + std::to_string(token_actual.linea) +
            ", col " + std::to_string(token_actual.columna) + "): se esperaba un tipo de dato");
    }
    TipoDato tipo = token_actual.tipo_dato;
    siguienteToken();

    std::string nombre = token_actual.lexema;
    esperar(Token::Tipo::IDENTIFICADOR, "se esperaba el nombre de la variable");

    auto decl = std::make_unique<AST::DeclaracionVariable>();
    decl->nombre = nombre;
    decl->tipo = tipo;
    decl->es_constante = es_constante;

    if (coincidir(Token::Tipo::OPERADOR_ASIGNAR)) {
        decl->valor_inicial = parseExpresion();
    }

    esperar(Token::Tipo::PUNTO_Y_COMA, "se esperaba ';' al final de la declaracion");
    return decl;
}

std::unique_ptr<AST::Sentencia> Parser::parseImprimir() {
    esperar(Token::Tipo::PALABRA_CLAVE_PRINT, "se esperaba 'imprimir'");
    esperar(Token::Tipo::PARENTESIS_IZQUIERDO, "se esperaba '(' despues de 'imprimir'");

    auto sent = std::make_unique<AST::SentenciaPrint>();
    sent->expresion = parseExpresion();

    esperar(Token::Tipo::PARENTESIS_DERECHO, "se esperaba ')' despues de la expresion");
    esperar(Token::Tipo::PUNTO_Y_COMA, "se esperaba ';' despues de imprimir(...)");
    return sent;
}

std::unique_ptr<AST::Sentencia> Parser::parseForEn() {
    esperar(Token::Tipo::PALABRA_CLAVE_FOR, "se esperaba 'para'");

    std::string nombre_variable = token_actual.lexema;
    esperar(Token::Tipo::IDENTIFICADOR, "se esperaba el nombre de la variable del bucle");

    esperar(Token::Tipo::PALABRA_CLAVE_EN, "se esperaba 'en' en la sintaxis del bucle");

    auto sent = std::make_unique<AST::SentenciaForEn>();
    sent->nombre_variable = nombre_variable;
    sent->iterable = parseExpresion();
    sent->cuerpo = parseBloque();
    return sent;
}

std::vector<std::unique_ptr<AST::Sentencia>> Parser::parseBloque() {
    esperar(Token::Tipo::LLAVE_IZQUIERDA, "se esperaba '{' para iniciar el cuerpo del bucle");

    std::vector<std::unique_ptr<AST::Sentencia>> cuerpo;
    while (token_actual.tipo != Token::Tipo::LLAVE_DERECHA &&
           token_actual.tipo != Token::Tipo::FIN_DE_ARCHIVO) {
        cuerpo.push_back(parseSentencia());
    }

    esperar(Token::Tipo::LLAVE_DERECHA, "se esperaba '}' para cerrar el cuerpo del bucle");
    return cuerpo;
}

std::unique_ptr<AST::Expresion> Parser::parseExpresion() {
    return parseExpresionLogica();
}

std::unique_ptr<AST::Expresion> Parser::parseExpresionLogica() {
    auto izquierda = parseExpresionComparacion();

    while (token_actual.tipo == Token::Tipo::OPERADOR_Y ||
           token_actual.tipo == Token::Tipo::OPERADOR_O) {
        auto op = (token_actual.tipo == Token::Tipo::OPERADOR_Y)
                      ? AST::ExpresionBinaria::Operador::Y
                      : AST::ExpresionBinaria::Operador::O;
        siguienteToken();
        auto derecha = parseExpresionComparacion();

        auto bin = std::make_unique<AST::ExpresionBinaria>();
        bin->operador = op;
        bin->izquierda = std::move(izquierda);
        bin->derecha = std::move(derecha);
        bin->tipo_resultado = TipoDato::BOOLEANO;
        izquierda = std::move(bin);
    }
    return izquierda;
}

std::unique_ptr<AST::Expresion> Parser::parseExpresionComparacion() {
    auto izquierda = parseExpresionAritmetica();

    while (token_actual.tipo == Token::Tipo::OPERADOR_IGUAL ||
           token_actual.tipo == Token::Tipo::OPERADOR_DIFERENTE ||
           token_actual.tipo == Token::Tipo::OPERADOR_MENOR_QUE ||
           token_actual.tipo == Token::Tipo::OPERADOR_MAYOR_QUE) {
        AST::ExpresionBinaria::Operador op;
        switch (token_actual.tipo) {
            case Token::Tipo::OPERADOR_IGUAL: op = AST::ExpresionBinaria::Operador::IGUAL; break;
            case Token::Tipo::OPERADOR_DIFERENTE: op = AST::ExpresionBinaria::Operador::DIFERENTE; break;
            case Token::Tipo::OPERADOR_MENOR_QUE: op = AST::ExpresionBinaria::Operador::MENOR_QUE; break;
            default: op = AST::ExpresionBinaria::Operador::MAYOR_QUE; break;
        }
        siguienteToken();
        auto derecha = parseExpresionAritmetica();

        auto bin = std::make_unique<AST::ExpresionBinaria>();
        bin->operador = op;
        bin->izquierda = std::move(izquierda);
        bin->derecha = std::move(derecha);
        bin->tipo_resultado = TipoDato::BOOLEANO;
        izquierda = std::move(bin);
    }
    return izquierda;
}

std::unique_ptr<AST::Expresion> Parser::parseExpresionAritmetica() {
    auto izquierda = parseExpresionUnaria();

    while (token_actual.tipo == Token::Tipo::OPERADOR_MAS ||
           token_actual.tipo == Token::Tipo::OPERADOR_MENOS ||
           token_actual.tipo == Token::Tipo::OPERADOR_MULTIPLICAR ||
           token_actual.tipo == Token::Tipo::OPERADOR_DIVIDIR) {
        AST::ExpresionBinaria::Operador op;
        switch (token_actual.tipo) {
            case Token::Tipo::OPERADOR_MAS: op = AST::ExpresionBinaria::Operador::SUMA; break;
            case Token::Tipo::OPERADOR_MENOS: op = AST::ExpresionBinaria::Operador::RESTA; break;
            case Token::Tipo::OPERADOR_MULTIPLICAR: op = AST::ExpresionBinaria::Operador::MULTIPLICACION; break;
            default: op = AST::ExpresionBinaria::Operador::DIVISION; break;
        }
        siguienteToken();
        auto derecha = parseExpresionUnaria();

        auto bin = std::make_unique<AST::ExpresionBinaria>();
        bin->operador = op;
        bin->izquierda = std::move(izquierda);
        bin->derecha = std::move(derecha);
        bin->tipo_resultado = izquierda ? izquierda->getTipo() : TipoDato::DESCONOCIDO;
        // el tipo real se resuelve en tiempo de ejecucion (string+string, int+int, etc.)
        izquierda = std::move(bin);
    }
    return izquierda;
}

std::unique_ptr<AST::Expresion> Parser::parseExpresionUnaria() {
    if (token_actual.tipo == Token::Tipo::OPERADOR_MENOS ||
        token_actual.tipo == Token::Tipo::OPERADOR_NO) {
        auto op = (token_actual.tipo == Token::Tipo::OPERADOR_MENOS)
                      ? AST::ExpresionUnaria::Operador::NEGATIVO
                      : AST::ExpresionUnaria::Operador::NO;
        siguienteToken();
        auto operando = parseExpresionUnaria();

        auto un = std::make_unique<AST::ExpresionUnaria>();
        un->operador = op;
        un->tipo_resultado = operando->getTipo();
        un->operando = std::move(operando);
        return un;
    }
    return parseFactor();
}

std::unique_ptr<AST::Expresion> Parser::parseFactor() {
    std::unique_ptr<AST::Expresion> expresion;

    if (token_actual.tipo == Token::Tipo::NUMERO) {
        auto lit = std::make_unique<AST::ExpresionLiteral>();
        if (token_actual.tipo_dato == TipoDato::DECIMAL) {
            lit->valor = std::get<double>(token_actual.valor);
            lit->tipo = TipoDato::DECIMAL;
        } else {
            lit->valor = std::get<int>(token_actual.valor);
            lit->tipo = TipoDato::ENTERO;
        }
        siguienteToken();
        expresion = std::move(lit);
    }
    else if (token_actual.tipo == Token::Tipo::CADENA) {
        auto lit = std::make_unique<AST::ExpresionLiteral>();
        lit->valor = std::get<std::string>(token_actual.valor);
        lit->tipo = TipoDato::CADENA;
        siguienteToken();
        expresion = std::move(lit);
    }
    else if (token_actual.tipo == Token::Tipo::BOOLEANO) {
        auto lit = std::make_unique<AST::ExpresionLiteral>();
        lit->valor = std::get<bool>(token_actual.valor);
        lit->tipo = TipoDato::BOOLEANO;
        siguienteToken();
        expresion = std::move(lit);
    }
    else if (token_actual.tipo == Token::Tipo::NULO) {
        auto lit = std::make_unique<AST::ExpresionLiteral>();
        lit->tipo = TipoDato::NULO;
        siguienteToken();
        expresion = std::move(lit);
    }
    else if (token_actual.tipo == Token::Tipo::CORCHETE_IZQUIERDO) {
        expresion = parseListaLiteral();
    }
    else if (token_actual.tipo == Token::Tipo::LLAVE_IZQUIERDA) {
        expresion = parseDiccionarioLiteral();
    }
    else if (token_actual.tipo == Token::Tipo::IDENTIFICADOR) {
        std::string nombre = token_actual.lexema;
        siguienteToken();

        // Llamada a funcion: identificador(args...)
        if (token_actual.tipo == Token::Tipo::PARENTESIS_IZQUIERDO) {
            siguienteToken();
            auto llamada = std::make_unique<AST::ExpresionLlamada>();
            llamada->nombre_funcion = nombre;
            if (token_actual.tipo != Token::Tipo::PARENTESIS_DERECHO) {
                llamada->argumentos.push_back(parseExpresion());
                while (coincidir(Token::Tipo::COMA)) {
                    llamada->argumentos.push_back(parseExpresion());
                }
            }
            esperar(Token::Tipo::PARENTESIS_DERECHO, "se esperaba ')' en la llamada a funcion");
            expresion = std::move(llamada);
        } else {
            auto var = std::make_unique<AST::ExpresionVariable>();
            var->nombre = nombre;
            var->tipo = TipoDato::DESCONOCIDO; // se resuelve en tiempo de ejecucion
            expresion = std::move(var);
        }
    }
    else if (coincidir(Token::Tipo::PARENTESIS_IZQUIERDO)) {
        auto expr = parseExpresion();
        esperar(Token::Tipo::PARENTESIS_DERECHO, "se esperaba ')'");
        expresion = std::move(expr);
    }
    else {
        throw std::runtime_error(
            "Error de sintaxis (linea " + std::to_string(token_actual.linea) +
            "): expresion no valida -- token: '" + token_actual.lexema + "'");
    }

    while (coincidir(Token::Tipo::CORCHETE_IZQUIERDO)) {
        auto acceso = std::make_unique<AST::ExpresionAccesoLista>();
        acceso->lista = std::move(expresion);
        acceso->indice = parseExpresion();
        esperar(Token::Tipo::CORCHETE_DERECHO, "se esperaba ']' despues del indice");
        expresion = std::move(acceso);
    }
    return expresion;
}

std::unique_ptr<AST::Expresion> Parser::parseListaLiteral() {
    esperar(Token::Tipo::CORCHETE_IZQUIERDO, "se esperaba '['");
    auto lista = std::make_unique<AST::ExpresionLista>();

    if (token_actual.tipo != Token::Tipo::CORCHETE_DERECHO) {
        lista->elementos.push_back(parseExpresion());
        while (coincidir(Token::Tipo::COMA)) {
            lista->elementos.push_back(parseExpresion());
        }
    }
    esperar(Token::Tipo::CORCHETE_DERECHO, "se esperaba ']' al final de la lista");
    return lista;
}

std::unique_ptr<AST::Expresion> Parser::parseDiccionarioLiteral() {
    esperar(Token::Tipo::LLAVE_IZQUIERDA, "se esperaba '{'");
    auto dicc = std::make_unique<AST::ExpresionDiccionario>();

    if (token_actual.tipo != Token::Tipo::LLAVE_DERECHA) {
        auto clave = parseExpresion();
        esperar(Token::Tipo::DOS_PUNTOS, "se esperaba ':' despues de la clave del diccionario");
        auto valor = parseExpresion();
        dicc->pares.emplace_back(std::move(clave), std::move(valor));

        while (coincidir(Token::Tipo::COMA)) {
            auto clave2 = parseExpresion();
            esperar(Token::Tipo::DOS_PUNTOS, "se esperaba ':' despues de la clave del diccionario");
            auto valor2 = parseExpresion();
            dicc->pares.emplace_back(std::move(clave2), std::move(valor2));
        }
    }
    esperar(Token::Tipo::LLAVE_DERECHA, "se esperaba '}' al final del diccionario");
    return dicc;
}
