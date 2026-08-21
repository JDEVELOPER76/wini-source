// bytecode.cpp
#include "bytecode.hpp"
#include <fstream>
#include <stdexcept>
#include <ostream>
#include <cstring>

namespace BC {

static const char MAGIC[4] = {'W', 'N', 'C', '1'}; // "WNC1" = Wini bytecode, version 1

std::string nombreOpCode(OpCode op) {
    switch (op) {
        case OpCode::OP_CONST: return "OP_CONST";
        case OpCode::OP_NULO: return "OP_NULO";
        case OpCode::OP_VERDADERO: return "OP_VERDADERO";
        case OpCode::OP_FALSO: return "OP_FALSO";
        case OpCode::OP_POP: return "OP_POP";
        case OpCode::OP_DEFINIR_VAR: return "OP_DEFINIR_VAR";
        case OpCode::OP_OBTENER_VAR: return "OP_OBTENER_VAR";
        case OpCode::OP_ASIGNAR_VAR: return "OP_ASIGNAR_VAR";
        case OpCode::OP_SUMA: return "OP_SUMA";
        case OpCode::OP_RESTA: return "OP_RESTA";
        case OpCode::OP_MUL: return "OP_MUL";
        case OpCode::OP_DIV: return "OP_DIV";
        case OpCode::OP_IGUAL: return "OP_IGUAL";
        case OpCode::OP_DIFERENTE: return "OP_DIFERENTE";
        case OpCode::OP_MENOR: return "OP_MENOR";
        case OpCode::OP_MAYOR: return "OP_MAYOR";
        case OpCode::OP_Y: return "OP_Y";
        case OpCode::OP_O: return "OP_O";
        case OpCode::OP_NEGAR: return "OP_NEGAR";
        case OpCode::OP_NO: return "OP_NO";
        case OpCode::OP_LISTA: return "OP_LISTA";
        case OpCode::OP_DICCIONARIO: return "OP_DICCIONARIO";
        case OpCode::OP_INDEXAR: return "OP_INDEXAR";
        case OpCode::OP_IMPRIMIR: return "OP_IMPRIMIR";
        case OpCode::OP_JUMP: return "OP_JUMP";
        case OpCode::OP_JUMP_IF_FALSE: return "OP_JUMP_IF_FALSE";
        case OpCode::OP_ITER_CREAR: return "OP_ITER_CREAR";
        case OpCode::OP_ITER_SIGUIENTE: return "OP_ITER_SIGUIENTE";
        case OpCode::OP_RANGO: return "OP_RANGO";
        case OpCode::OP_HALT: return "OP_HALT";
    }
    return "OP_DESCONOCIDO";
}

// Cuantos operandos de 4 bytes tiene cada opcode (para desensamblar / saltar).
static int numOperandos(OpCode op) {
    switch (op) {
        case OpCode::OP_CONST:
        case OpCode::OP_OBTENER_VAR:
        case OpCode::OP_ASIGNAR_VAR:
        case OpCode::OP_LISTA:
        case OpCode::OP_DICCIONARIO:
        case OpCode::OP_JUMP:
        case OpCode::OP_JUMP_IF_FALSE:
        case OpCode::OP_ITER_SIGUIENTE:
        case OpCode::OP_RANGO:
            return 1;
        case OpCode::OP_DEFINIR_VAR:
            return 3;
        default:
            return 0;
    }
}

uint32_t Chunk::agregarConstante(const Constante& c) {
    constantes.push_back(c);
    return static_cast<uint32_t>(constantes.size() - 1);
}

void Chunk::emitirByte(uint8_t byte) {
    codigo.push_back(byte);
}

void Chunk::emitirU32(uint32_t valor) {
    codigo.push_back(static_cast<uint8_t>(valor & 0xFF));
    codigo.push_back(static_cast<uint8_t>((valor >> 8) & 0xFF));
    codigo.push_back(static_cast<uint8_t>((valor >> 16) & 0xFF));
    codigo.push_back(static_cast<uint8_t>((valor >> 24) & 0xFF));
}

void Chunk::emitirOp(OpCode op) {
    emitirByte(static_cast<uint8_t>(op));
}

void Chunk::emitirOp(OpCode op, uint32_t operando) {
    emitirByte(static_cast<uint8_t>(op));
    emitirU32(operando);
}

void Chunk::emitirOp(OpCode op, uint32_t op1, uint32_t op2) {
    emitirByte(static_cast<uint8_t>(op));
    emitirU32(op1);
    emitirU32(op2);
}

void Chunk::emitirOp(OpCode op, uint32_t op1, uint32_t op2, uint32_t op3) {
    emitirByte(static_cast<uint8_t>(op));
    emitirU32(op1);
    emitirU32(op2);
    emitirU32(op3);
}

static uint32_t leerU32(const std::vector<uint8_t>& codigo, size_t pos) {
    return static_cast<uint32_t>(codigo[pos]) |
           (static_cast<uint32_t>(codigo[pos + 1]) << 8) |
           (static_cast<uint32_t>(codigo[pos + 2]) << 16) |
           (static_cast<uint32_t>(codigo[pos + 3]) << 24);
}

void Chunk::desensamblar(std::ostream& os) const {
    os << "; Constantes (" << constantes.size() << "):\n";
    for (size_t i = 0; i < constantes.size(); ++i) {
        os << ";   [" << i << "] ";
        std::visit([&os](auto&& val) {
            using T = std::decay_t<decltype(val)>;
            if constexpr (std::is_same_v<T, std::monostate>) os << "nulo";
            else if constexpr (std::is_same_v<T, std::string>) os << "\"" << val << "\"";
            else if constexpr (std::is_same_v<T, bool>) os << (val ? "verdadero" : "falso");
            else os << val;
        }, constantes[i]);
        os << "\n";
    }
    os << "; Instrucciones:\n";
    size_t ip = 0;
    while (ip < codigo.size()) {
        OpCode op = static_cast<OpCode>(codigo[ip]);
        os << ip << ": " << nombreOpCode(op);
        int n = numOperandos(op);
        size_t cursor = ip + 1;
        for (int i = 0; i < n; ++i) {
            uint32_t operando = leerU32(codigo, cursor);
            os << " " << operando;
            cursor += 4;
        }
        os << "\n";
        ip = cursor;
    }
}

void guardarChunk(const Chunk& chunk, const std::string& ruta) {
    std::ofstream out(ruta, std::ios::binary);
    if (!out) throw std::runtime_error("No se pudo crear el archivo de bytecode: " + ruta);

    out.write(MAGIC, 4);

    uint32_t num_constantes = static_cast<uint32_t>(chunk.constantes.size());
    out.write(reinterpret_cast<const char*>(&num_constantes), sizeof(num_constantes));

    for (const auto& c : chunk.constantes) {
        uint8_t tag = static_cast<uint8_t>(c.index());
        out.write(reinterpret_cast<const char*>(&tag), 1);
        switch (tag) {
            case 0: // monostate (nulo)
                break;
            case 1: { // int
                int v = std::get<int>(c);
                out.write(reinterpret_cast<const char*>(&v), sizeof(v));
                break;
            }
            case 2: { // double
                double v = std::get<double>(c);
                out.write(reinterpret_cast<const char*>(&v), sizeof(v));
                break;
            }
            case 3: { // string
                const std::string& s = std::get<std::string>(c);
                uint32_t len = static_cast<uint32_t>(s.size());
                out.write(reinterpret_cast<const char*>(&len), sizeof(len));
                out.write(s.data(), len);
                break;
            }
            case 4: { // bool
                uint8_t v = std::get<bool>(c) ? 1 : 0;
                out.write(reinterpret_cast<const char*>(&v), 1);
                break;
            }
        }
    }

    uint32_t len_codigo = static_cast<uint32_t>(chunk.codigo.size());
    out.write(reinterpret_cast<const char*>(&len_codigo), sizeof(len_codigo));
    if (len_codigo > 0) {
        out.write(reinterpret_cast<const char*>(chunk.codigo.data()), len_codigo);
    }

    if (!out) throw std::runtime_error("Fallo al escribir el archivo de bytecode: " + ruta);
}

Chunk cargarChunk(const std::string& ruta) {
    std::ifstream in(ruta, std::ios::binary);
    if (!in) throw std::runtime_error("No se pudo abrir el archivo de bytecode: " + ruta);

    char magic[4];
    in.read(magic, 4);
    if (!in || std::memcmp(magic, MAGIC, 4) != 0) {
        throw std::runtime_error("Archivo de bytecode invalido o de version incompatible: " + ruta);
    }

    Chunk chunk;

    uint32_t num_constantes = 0;
    in.read(reinterpret_cast<char*>(&num_constantes), sizeof(num_constantes));

    chunk.constantes.reserve(num_constantes);
    for (uint32_t i = 0; i < num_constantes; ++i) {
        uint8_t tag = 0;
        in.read(reinterpret_cast<char*>(&tag), 1);
        switch (tag) {
            case 0:
                chunk.constantes.push_back(std::monostate{});
                break;
            case 1: {
                int v = 0;
                in.read(reinterpret_cast<char*>(&v), sizeof(v));
                chunk.constantes.push_back(v);
                break;
            }
            case 2: {
                double v = 0;
                in.read(reinterpret_cast<char*>(&v), sizeof(v));
                chunk.constantes.push_back(v);
                break;
            }
            case 3: {
                uint32_t len = 0;
                in.read(reinterpret_cast<char*>(&len), sizeof(len));
                std::string s(len, '\0');
                if (len > 0) in.read(&s[0], len);
                chunk.constantes.push_back(s);
                break;
            }
            case 4: {
                uint8_t v = 0;
                in.read(reinterpret_cast<char*>(&v), 1);
                chunk.constantes.push_back(v != 0);
                break;
            }
            default:
                throw std::runtime_error("Etiqueta de constante desconocida en .wnc");
        }
    }

    uint32_t len_codigo = 0;
    in.read(reinterpret_cast<char*>(&len_codigo), sizeof(len_codigo));
    chunk.codigo.resize(len_codigo);
    if (len_codigo > 0) {
        in.read(reinterpret_cast<char*>(chunk.codigo.data()), len_codigo);
    }

    if (!in) throw std::runtime_error("Archivo de bytecode truncado o corrupto: " + ruta);

    return chunk;
}

} // namespace BC
