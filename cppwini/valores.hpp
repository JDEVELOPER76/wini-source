// valores.hpp
// Tipos de valores en tiempo de ejecucion, compartidos entre el
// interprete de arbol de sintaxis (interprete.hpp) y la maquina
// virtual de bytecode (vm_bytecode.hpp), para no duplicar la logica.
#pragma once
#include <variant>
#include <vector>
#include <string>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <type_traits>

struct ListaValor;
struct DiccionarioValor;

// Valor en tiempo de ejecucion (monostate = nulo)
using Valor = std::variant<std::monostate, int, double, std::string, bool,
                            std::shared_ptr<ListaValor>, std::shared_ptr<DiccionarioValor>>;

struct ListaValor {
    std::vector<Valor> elementos;
};

struct DiccionarioValor {
    std::vector<std::pair<std::string, Valor>> elementos; // preserva orden de insercion

    Valor* buscar(const std::string& clave) {
        for (auto& par : elementos) {
            if (par.first == clave) return &par.second;
        }
        return nullptr;
    }

    void asignar(const std::string& clave, const Valor& valor) {
        for (auto& par : elementos) {
            if (par.first == clave) { par.second = valor; return; }
        }
        elementos.emplace_back(clave, valor);
    }
};

inline std::string valorATexto(const Valor& v) {
    std::ostringstream os;
    std::visit([&os](auto&& val) {
        using T = std::decay_t<decltype(val)>;
        if constexpr (std::is_same_v<T, std::monostate>) {
            os << "nulo";
        } else if constexpr (std::is_same_v<T, bool>) {
            os << (val ? "verdadero" : "falso");
        } else if constexpr (std::is_same_v<T, std::shared_ptr<ListaValor>>) {
            os << "[";
            for (size_t i = 0; i < val->elementos.size(); ++i) {
                if (i != 0) os << ", ";
                os << valorATexto(val->elementos[i]);
            }
            os << "]";
        } else if constexpr (std::is_same_v<T, std::shared_ptr<DiccionarioValor>>) {
            os << "{";
            for (size_t i = 0; i < val->elementos.size(); ++i) {
                if (i != 0) os << ", ";
                os << "\"" << val->elementos[i].first << "\": "
                   << valorATexto(val->elementos[i].second);
            }
            os << "}";
        } else {
            os << val;
        }
    }, v);
    return os.str();
}

inline double aDouble(const Valor& v) {
    if (std::holds_alternative<int>(v)) return std::get<int>(v);
    if (std::holds_alternative<double>(v)) return std::get<double>(v);
    throw std::runtime_error("Se esperaba un valor numerico");
}

inline bool esNumerico(const Valor& v) {
    return std::holds_alternative<int>(v) || std::holds_alternative<double>(v);
}

inline bool aBool(const Valor& v) {
    if (std::holds_alternative<bool>(v)) return std::get<bool>(v);
    throw std::runtime_error("Se esperaba un valor booleano");
}
