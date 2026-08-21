// compilador.cpp
#include "compilador.hpp"
#include <stdexcept>

uint32_t CompiladorBytecode::constanteNombre(const std::string& nombre) {
    return chunk.agregarConstante(BC::Constante(nombre));
}

BC::Chunk CompiladorBytecode::compilar(AST::Programa* programa) {
    chunk = BC::Chunk();
    for (auto& sent : programa->sentencias) {
        compilarSentencia(sent.get());
    }
    chunk.emitirOp(BC::OpCode::OP_HALT);
    return chunk;
}

void CompiladorBytecode::compilarSentencia(AST::Sentencia* sent) {
    if (auto* decl = dynamic_cast<AST::DeclaracionVariable*>(sent)) {
        compilarDeclaracionVariable(decl);
        return;
    }
    if (auto* impr = dynamic_cast<AST::SentenciaPrint*>(sent)) {
        compilarImprimir(impr);
        return;
    }
    if (auto* for_en = dynamic_cast<AST::SentenciaForEn*>(sent)) {
        compilarForEn(for_en);
        return;
    }
    throw std::runtime_error("El compilador de bytecode aun no soporta este tipo de sentencia");
}

void CompiladorBytecode::compilarDeclaracionVariable(AST::DeclaracionVariable* decl) {
    if (decl->valor_inicial) {
        compilarExpresion(decl->valor_inicial.get());
    } else {
        chunk.emitirOp(BC::OpCode::OP_NULO);
    }

    uint32_t idx_nombre = constanteNombre(decl->nombre);
    uint32_t tipo = static_cast<uint32_t>(decl->tipo);
    uint32_t es_const = decl->es_constante ? 1u : 0u;
    chunk.emitirOp(BC::OpCode::OP_DEFINIR_VAR, idx_nombre, tipo, es_const);
}

void CompiladorBytecode::compilarImprimir(AST::SentenciaPrint* sent) {
    compilarExpresion(sent->expresion.get());
    chunk.emitirOp(BC::OpCode::OP_IMPRIMIR);
}

void CompiladorBytecode::patchSalto(size_t pos_operando, uint32_t destino) {
    chunk.codigo[pos_operando]     = static_cast<uint8_t>(destino & 0xFF);
    chunk.codigo[pos_operando + 1] = static_cast<uint8_t>((destino >> 8) & 0xFF);
    chunk.codigo[pos_operando + 2] = static_cast<uint8_t>((destino >> 16) & 0xFF);
    chunk.codigo[pos_operando + 3] = static_cast<uint8_t>((destino >> 24) & 0xFF);
}

void CompiladorBytecode::compilarForEn(AST::SentenciaForEn* sent) {
    // iterable -> OP_ITER_CREAR
    compilarExpresion(sent->iterable.get());
    chunk.emitirOp(BC::OpCode::OP_ITER_CREAR);

    // inicio del bucle: intenta obtener el siguiente valor
    uint32_t inicio_loop = static_cast<uint32_t>(chunk.codigo.size());
    size_t pos_operando_salto = chunk.codigo.size() + 1; // +1 salta el byte del opcode
    chunk.emitirOp(BC::OpCode::OP_ITER_SIGUIENTE, 0); // destino se parchea despues

    // define/actualiza la variable del bucle con el valor obtenido
    uint32_t idx_nombre = constanteNombre(sent->nombre_variable);
    chunk.emitirOp(BC::OpCode::OP_DEFINIR_VAR, idx_nombre,
                   static_cast<uint32_t>(TipoDato::DESCONOCIDO), 0u);

    for (auto& cuerpo_sent : sent->cuerpo) {
        compilarSentencia(cuerpo_sent.get());
    }

    chunk.emitirOp(BC::OpCode::OP_JUMP, inicio_loop);

    uint32_t destino_fin = static_cast<uint32_t>(chunk.codigo.size());
    patchSalto(pos_operando_salto, destino_fin);
}

void CompiladorBytecode::compilarExpresion(AST::Expresion* expr) {
    if (auto* lit = dynamic_cast<AST::ExpresionLiteral*>(expr)) {
        switch (lit->tipo) {
            case TipoDato::ENTERO:
                chunk.emitirOp(BC::OpCode::OP_CONST,
                    chunk.agregarConstante(BC::Constante(std::get<int>(lit->valor))));
                return;
            case TipoDato::DECIMAL:
                chunk.emitirOp(BC::OpCode::OP_CONST,
                    chunk.agregarConstante(BC::Constante(std::get<double>(lit->valor))));
                return;
            case TipoDato::CADENA:
                chunk.emitirOp(BC::OpCode::OP_CONST,
                    chunk.agregarConstante(BC::Constante(std::get<std::string>(lit->valor))));
                return;
            case TipoDato::BOOLEANO:
                chunk.emitirOp(std::get<bool>(lit->valor) ? BC::OpCode::OP_VERDADERO
                                                            : BC::OpCode::OP_FALSO);
                return;
            case TipoDato::NULO:
            default:
                chunk.emitirOp(BC::OpCode::OP_NULO);
                return;
        }
    }

    if (auto* var = dynamic_cast<AST::ExpresionVariable*>(expr)) {
        chunk.emitirOp(BC::OpCode::OP_OBTENER_VAR, constanteNombre(var->nombre));
        return;
    }

    if (auto* bin = dynamic_cast<AST::ExpresionBinaria*>(expr)) {
        using Op = AST::ExpresionBinaria::Operador;

        if (bin->operador == Op::ASIGNACION) {
            auto* var = dynamic_cast<AST::ExpresionVariable*>(bin->izquierda.get());
            if (!var) throw std::runtime_error("Lado izquierdo de '=' invalido en el compilador");
            compilarExpresion(bin->derecha.get());
            chunk.emitirOp(BC::OpCode::OP_ASIGNAR_VAR, constanteNombre(var->nombre));
            return;
        }

        compilarExpresion(bin->izquierda.get());
        compilarExpresion(bin->derecha.get());

        switch (bin->operador) {
            case Op::SUMA: chunk.emitirOp(BC::OpCode::OP_SUMA); break;
            case Op::RESTA: chunk.emitirOp(BC::OpCode::OP_RESTA); break;
            case Op::MULTIPLICACION: chunk.emitirOp(BC::OpCode::OP_MUL); break;
            case Op::DIVISION: chunk.emitirOp(BC::OpCode::OP_DIV); break;
            case Op::IGUAL: chunk.emitirOp(BC::OpCode::OP_IGUAL); break;
            case Op::DIFERENTE: chunk.emitirOp(BC::OpCode::OP_DIFERENTE); break;
            case Op::MENOR_QUE: chunk.emitirOp(BC::OpCode::OP_MENOR); break;
            case Op::MAYOR_QUE: chunk.emitirOp(BC::OpCode::OP_MAYOR); break;
            case Op::Y: chunk.emitirOp(BC::OpCode::OP_Y); break;
            case Op::O: chunk.emitirOp(BC::OpCode::OP_O); break;
            default:
                throw std::runtime_error("Operador binario no soportado por el compilador");
        }
        return;
    }

    if (auto* un = dynamic_cast<AST::ExpresionUnaria*>(expr)) {
        compilarExpresion(un->operando.get());
        if (un->operador == AST::ExpresionUnaria::Operador::NEGATIVO) {
            chunk.emitirOp(BC::OpCode::OP_NEGAR);
        } else {
            chunk.emitirOp(BC::OpCode::OP_NO);
        }
        return;
    }

    if (auto* lista = dynamic_cast<AST::ExpresionLista*>(expr)) {
        for (auto& el : lista->elementos) compilarExpresion(el.get());
        chunk.emitirOp(BC::OpCode::OP_LISTA, static_cast<uint32_t>(lista->elementos.size()));
        return;
    }

    if (auto* dicc = dynamic_cast<AST::ExpresionDiccionario*>(expr)) {
        for (auto& par : dicc->pares) {
            compilarExpresion(par.first.get());
            compilarExpresion(par.second.get());
        }
        chunk.emitirOp(BC::OpCode::OP_DICCIONARIO, static_cast<uint32_t>(dicc->pares.size()));
        return;
    }

    if (auto* acceso = dynamic_cast<AST::ExpresionAccesoLista*>(expr)) {
        compilarExpresion(acceso->lista.get());
        compilarExpresion(acceso->indice.get());
        chunk.emitirOp(BC::OpCode::OP_INDEXAR);
        return;
    }

    if (auto* llamada = dynamic_cast<AST::ExpresionLlamada*>(expr)) {
        if (llamada->nombre_funcion == "rango" || llamada->nombre_funcion == "range") {
            if (llamada->argumentos.size() == 1) {
                compilarExpresion(llamada->argumentos[0].get());
                chunk.emitirOp(BC::OpCode::OP_RANGO, 1u);
                return;
            }
            if (llamada->argumentos.size() == 2) {
                compilarExpresion(llamada->argumentos[0].get());
                compilarExpresion(llamada->argumentos[1].get());
                chunk.emitirOp(BC::OpCode::OP_RANGO, 2u);
                return;
            }
            throw std::runtime_error("rango() acepta 1 o 2 argumentos");
        }
        throw std::runtime_error(
            "El compilador de bytecode aun no soporta llamadas a la funcion '" +
            llamada->nombre_funcion + "'");
    }

    throw std::runtime_error("Tipo de expresion no soportado por el compilador de bytecode");
}
