// main.cpp
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include "lexer.hpp"
#include "parser.hpp"
#include "interprete.hpp"
#include "compilador.hpp"
#include "vm_bytecode.hpp"

static std::string leerArchivo(const std::string& ruta) {
    std::ifstream archivo(ruta);
    if (!archivo) {
        throw std::runtime_error("No se pudo abrir el archivo: " + ruta);
    }
    std::ostringstream ss;
    ss << archivo.rdbuf();
    return ss.str();
}

static std::string cambiarExtension(const std::string& ruta, const std::string& nueva_ext) {
    auto pos = ruta.find_last_of('.');
    std::string base = (pos == std::string::npos) ? ruta : ruta.substr(0, pos);
    return base + nueva_ext;
}

static void mostrarUso(const char* nombre_programa) {
    std::cerr
        << "Uso:\n"
        << "  " << nombre_programa << " archivo.wn\n"
        << "      Interpreta el archivo linea a linea (arbol de sintaxis), sin generar bytecode.\n\n"
        << "  " << nombre_programa << " archivo.wn --compilar [salida.wnc]\n"
        << "      Compila el archivo .wn a bytecode y lo guarda como .wnc\n"
        << "      (si no se indica 'salida.wnc', se usa el mismo nombre con extension .wnc).\n\n"
        << "  " << nombre_programa << " archivo.wnc --correr\n"
        << "      Ejecuta un archivo de bytecode .wnc ya compilado, usando la VM de pila.\n";
}

int main(int argc, char** argv) {
    std::string ruta_archivo;
    std::string ruta_salida;
    bool modo_compilar = false;
    bool modo_correr = false;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--compilar") {
            modo_compilar = true;
        } else if (arg == "--correr") {
            modo_correr = true;
        } else if (ruta_archivo.empty()) {
            ruta_archivo = arg;
        } else if (ruta_salida.empty()) {
            ruta_salida = arg;
        }
    }

    if (modo_compilar && modo_correr) {
        std::cerr << "Error: no se puede usar --compilar y --correr al mismo tiempo." << std::endl;
        return 1;
    }

    if (ruta_archivo.empty()) {
        mostrarUso(argv[0]);
        return 1;
    }

    try {
        if (modo_compilar) {
            // --compilar: genera un archivo .wnc con el bytecode del programa
            std::string codigo = leerArchivo(ruta_archivo);

            Lexer lexer(codigo);
            auto tokens = lexer.analizar();

            Parser parser(tokens);
            auto programa = parser.parse();

            CompiladorBytecode compilador;
            BC::Chunk chunk = compilador.compilar(programa.get());

            std::string salida = ruta_salida.empty()
                ? cambiarExtension(ruta_archivo, ".wnc")
                : ruta_salida;

            BC::guardarChunk(chunk, salida);
            std::cout << "Bytecode generado: " << salida << std::endl;
            return 0;
        }

        if (modo_correr) {
            // --correr: carga un .wnc ya compilado y lo ejecuta con la VM de bytecode
            BC::Chunk chunk = BC::cargarChunk(ruta_archivo);
            VMBytecode vm;
            vm.ejecutar(chunk);
            return 0;
        }

        // Sin opciones: comportamiento por defecto, interpreta el archivo
        // linea a linea recorriendo el arbol de sintaxis (AST).
        std::string codigo = leerArchivo(ruta_archivo);

        Lexer lexer(codigo);
        auto tokens = lexer.analizar();

        Parser parser(tokens);
        auto programa = parser.parse();

        Interprete interprete;
        interprete.ejecutar(programa.get());

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
