// compilador.hpp
// Recorre el AST (el mismo que usa el interprete de arbol) y emite
// bytecode equivalente en un BC::Chunk, listo para guardarse en un
// archivo .wnc o ejecutarse directamente con VMBytecode.
#pragma once
#include "ast.hpp"
#include "bytecode.hpp"

class CompiladorBytecode {
public:
    BC::Chunk compilar(AST::Programa* programa);

private:
    BC::Chunk chunk;

    uint32_t constanteNombre(const std::string& nombre);

    void compilarSentencia(AST::Sentencia* sent);
    void compilarDeclaracionVariable(AST::DeclaracionVariable* decl);
    void compilarImprimir(AST::SentenciaPrint* sent);
    void compilarForEn(AST::SentenciaForEn* sent);

    void compilarExpresion(AST::Expresion* expr);

    // Reescribe el operando (4 bytes, little-endian) de un salto ya
    // emitido, una vez que se conoce su destino real.
    void patchSalto(size_t pos_operando, uint32_t destino);
};
