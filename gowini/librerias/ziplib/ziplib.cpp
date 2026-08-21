
// Definir constantes de encriptación si no están definidas
#ifndef ZIP_EM_TRADITIONAL
    #define ZIP_EM_TRADITIONAL 1
#endif

#ifndef ZIP_EM_AES_128
    #define ZIP_EM_AES_128 2
#endif

#ifndef ZIP_EM_AES_192
    #define ZIP_EM_AES_192 3
#endif

#ifndef ZIP_EM_AES_256
    #define ZIP_EM_AES_256 4
#endif

// ziplib.cpp - Módulo ZIP completo para Wini
#include "winiapi.h"
#include <zip.h>
#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <windows.h>

//C:\msys64\ucrt64\bin\g++.exe -shared -o zip.dll ziplib.cpp winiapi.cpp -I"C:\msys64\ucrt64\include" -L"C:\msys64\ucrt64\lib" -lzip -lz -static-libgcc -static-libstdc++ -O2 -DWINI_EXPORTS   

// ===== DECLARACIONES DE FUNCIONES =====
extern "C" {
    WiniValor wini_zip_create(WiniValor* args, int num_args);
    WiniValor wini_zip_add_file(WiniValor* args, int num_args);
    WiniValor wini_zip_extract(WiniValor* args, int num_args);
    WiniValor wini_zip_list(WiniValor* args, int num_args);
    WiniValor wini_zip_delete(WiniValor* args, int num_args);
    WiniValor wini_zip_rename(WiniValor* args, int num_args);
    WiniValor wini_zip_add_dir(WiniValor* args, int num_args);
    WiniValor wini_zip_add_from_memory(WiniValor* args, int num_args);
    WiniValor wini_zip_file_info(WiniValor* args, int num_args);
    WiniValor wini_zip_set_comment(WiniValor* args, int num_args);
    WiniValor wini_zip_get_comment(WiniValor* args, int num_args);
    WiniValor wini_zip_add_directory(WiniValor* args, int num_args);
    WiniValor wini_zip_set_password(WiniValor* args, int num_args);
    WiniValor wini_zip_extract_with_password(WiniValor* args, int num_args);
    WiniValor wini_zip_add_encrypted(WiniValor* args, int num_args);
    WiniValor wini_zip_count(WiniValor* args, int num_args);
    WiniValor wini_zip_contains(WiniValor* args, int num_args);
}

// ===== VARIABLES GLOBALES =====
static WiniContexto g_contexto = nullptr;

// ===== FUNCIONES DE UTILIDAD =====
std::string wstring_to_string(const std::wstring& wstr) {
    if (wstr.empty()) return "";
    int size_needed = WideCharToMultiByte(CP_UTF8, 0, wstr.c_str(), (int)wstr.length(), 
                                          NULL, 0, NULL, NULL);
    std::string str(size_needed, 0);
    WideCharToMultiByte(CP_UTF8, 0, wstr.c_str(), (int)wstr.length(), 
                        &str[0], size_needed, NULL, NULL);
    return str;
}

std::wstring string_to_wstring(const std::string& str) {
    if (str.empty()) return L"";
    int size_needed = MultiByteToWideChar(CP_UTF8, 0, str.c_str(), (int)str.length(), NULL, 0);
    std::wstring wstr(size_needed, 0);
    MultiByteToWideChar(CP_UTF8, 0, str.c_str(), (int)str.length(), &wstr[0], size_needed);
    return wstr;
}

bool crear_directorios(const std::string& ruta) {
    std::string path = "";
    std::stringstream ss(ruta);
    std::string segmento;
    std::vector<std::string> segmentos;
    
    while (std::getline(ss, segmento, '\\')) {
        if (segmento.empty()) continue;
        segmentos.push_back(segmento);
    }
    
    for (size_t i = 0; i < segmentos.size(); i++) {
        if (i == 0 && segmentos[i].length() == 2 && segmentos[i][1] == ':') {
            path = segmentos[i] + "\\";
        } else {
            if (path.empty()) {
                path = segmentos[i];
            } else {
                path += "\\" + segmentos[i];
            }
            CreateDirectoryA(path.c_str(), NULL);
        }
    }
    return true;
}

// ===== INICIALIZACIÓN DEL MÓDULO =====
extern "C" {
    WINI_API bool wini_module_init(WiniContexto ctx, void* (*registrar)(const char* nombre, void* fn)) {
        g_contexto = ctx;
        
        registrar("crear", (void*)wini_zip_create);
        registrar("agregar", (void*)wini_zip_add_file);
        registrar("extraer", (void*)wini_zip_extract);
        registrar("listar", (void*)wini_zip_list);
        registrar("eliminar", (void*)wini_zip_delete);
        registrar("renombrar", (void*)wini_zip_rename);
        registrar("agregar_directorio", (void*)wini_zip_add_dir);
        registrar("agregar_desde_memoria", (void*)wini_zip_add_from_memory);
        registrar("info_archivo", (void*)wini_zip_file_info);
        registrar("establecer_comentario", (void*)wini_zip_set_comment);
        registrar("obtener_comentario", (void*)wini_zip_get_comment);
        registrar("agregar_carpeta", (void*)wini_zip_add_directory);
        registrar("establecer_password", (void*)wini_zip_set_password);
        registrar("extraer_con_password", (void*)wini_zip_extract_with_password);
        registrar("agregar_encriptado", (void*)wini_zip_add_encrypted);
        registrar("contar", (void*)wini_zip_count);
        registrar("contiene", (void*)wini_zip_contains);
        
        return true;
    }
    
    WINI_API void wini_module_cleanup(WiniContexto ctx) {
        g_contexto = nullptr;
    }
}

// ===== IMPLEMENTACIÓN DE FUNCIONES BÁSICAS =====

WiniValor wini_zip_create(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_CADENA) {
        return wini_crear_booleano(false);
    }
    
    std::string nombre_zip = args[0].cadena ? args[0].cadena : "";
    int error = 0;
    zip_t* archivo = zip_open(nombre_zip.c_str(), ZIP_CREATE | ZIP_TRUNCATE, &error);
    
    if (!archivo) {
        return wini_crear_booleano(false);
    }
    
    zip_close(archivo);
    return wini_crear_booleano(true);
}

WiniValor wini_zip_add_file(WiniValor* args, int num_args) {
    if (num_args < 2 || 
        args[0].tipo != WINI_TIPO_CADENA ||
        args[1].tipo != WINI_TIPO_CADENA) {
        return wini_crear_booleano(false);
    }
    
    std::string nombre_zip = args[0].cadena ? args[0].cadena : "";
    std::string archivo_origen = args[1].cadena ? args[1].cadena : "";
    
    int error = 0;
    zip_t* archivo = zip_open(nombre_zip.c_str(), ZIP_CREATE, &error);
    if (!archivo) return wini_crear_booleano(false);
    
    zip_source_t* source = zip_source_file(archivo, archivo_origen.c_str(), 0, 0);
    if (!source) {
        zip_close(archivo);
        return wini_crear_booleano(false);
    }
    
    std::string nombre_interno = archivo_origen;
    size_t pos = nombre_interno.find_last_of("\\/");
    if (pos != std::string::npos) {
        nombre_interno = nombre_interno.substr(pos + 1);
    }
    
    int64_t idx = zip_file_add(archivo, nombre_interno.c_str(), source, ZIP_FL_OVERWRITE);
    if (idx < 0) {
        zip_source_free(source);
        zip_close(archivo);
        return wini_crear_booleano(false);
    }
    
    zip_close(archivo);
    return wini_crear_booleano(true);
}

WiniValor wini_zip_extract(WiniValor* args, int num_args) {
    if (num_args < 2 ||
        args[0].tipo != WINI_TIPO_CADENA ||
        args[1].tipo != WINI_TIPO_CADENA) {
        return wini_crear_booleano(false);
    }
    
    std::string nombre_zip = args[0].cadena ? args[0].cadena : "";
    std::string destino = args[1].cadena ? args[1].cadena : "";
    
    int error = 0;
    zip_t* archivo = zip_open(nombre_zip.c_str(), ZIP_RDONLY, &error);
    if (!archivo) return wini_crear_booleano(false);
    
    zip_int64_t num_entries = zip_get_num_entries(archivo, 0);
    bool exito = true;
    
    for (zip_int64_t i = 0; i < num_entries; i++) {
        const char* nombre = zip_get_name(archivo, i, 0);
        if (!nombre) continue;
        
        std::string ruta_salida = destino + "\\" + nombre;
        size_t pos = ruta_salida.find_last_of("\\/");
        if (pos != std::string::npos) {
            std::string dir = ruta_salida.substr(0, pos);
            crear_directorios(dir);
        }
        
        zip_file_t* file = zip_fopen_index(archivo, i, 0);
        if (!file) {
            exito = false;
            continue;
        }
        
        std::ofstream out(ruta_salida, std::ios::binary);
        if (!out.is_open()) {
            zip_fclose(file);
            exito = false;
            continue;
        }
        
        char buffer[8192];
        zip_int64_t bytes;
        while ((bytes = zip_fread(file, buffer, sizeof(buffer))) > 0) {
            out.write(buffer, bytes);
        }
        
        out.close();
        zip_fclose(file);
    }
    
    zip_close(archivo);
    return wini_crear_booleano(exito);
}

WiniValor wini_zip_list(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_CADENA) {
        return wini_crear_lista(nullptr, 0);
    }
    
    std::string nombre_zip = args[0].cadena ? args[0].cadena : "";
    int error = 0;
    zip_t* archivo = zip_open(nombre_zip.c_str(), ZIP_RDONLY, &error);
    if (!archivo) return wini_crear_lista(nullptr, 0);
    
    std::vector<WiniValor> archivos;
    zip_int64_t num_entries = zip_get_num_entries(archivo, 0);
    
    for (zip_int64_t i = 0; i < num_entries; i++) {
        const char* nombre = zip_get_name(archivo, i, 0);
        if (nombre) {
            struct zip_stat st;
            zip_stat_init(&st);
            zip_stat(archivo, nombre, 0, &st);
            
            WiniValor claves[3];
            WiniValor valores[3];
            
            claves[0] = wini_crear_cadena("nombre");
            valores[0] = wini_crear_cadena(nombre);
            
            claves[1] = wini_crear_cadena("volumen");
            valores[1] = wini_crear_entero(st.size);
            
            claves[2] = wini_crear_cadena("comprimido");
            valores[2] = wini_crear_entero(st.comp_size);
            
            archivos.push_back(wini_crear_diccionario(claves, valores, 3));
        }
    }
    
    zip_close(archivo);
    return wini_crear_lista(archivos.data(), (int)archivos.size());
}

// ===== FUNCIONES AVANZADAS =====

WiniValor wini_zip_delete(WiniValor* args, int num_args) {
    if (num_args < 2 || 
        args[0].tipo != WINI_TIPO_CADENA ||
        args[1].tipo != WINI_TIPO_CADENA) {
        return wini_crear_booleano(false);
    }
    
    std::string nombre_zip = args[0].cadena;
    std::string archivo_a_eliminar = args[1].cadena;
    
    int error = 0;
    zip_t* archivo = zip_open(nombre_zip.c_str(), ZIP_CREATE, &error);
    if (!archivo) return wini_crear_booleano(false);
    
    zip_int64_t idx = zip_name_locate(archivo, archivo_a_eliminar.c_str(), 0);
    if (idx < 0) {
        zip_close(archivo);
        return wini_crear_booleano(false);
    }
    
    int resultado = zip_delete(archivo, idx);
    zip_close(archivo);
    return wini_crear_booleano(resultado == 0);
}

WiniValor wini_zip_rename(WiniValor* args, int num_args) {
    if (num_args < 3 ||
        args[0].tipo != WINI_TIPO_CADENA ||
        args[1].tipo != WINI_TIPO_CADENA ||
        args[2].tipo != WINI_TIPO_CADENA) {
        return wini_crear_booleano(false);
    }
    
    std::string nombre_zip = args[0].cadena;
    std::string nombre_viejo = args[1].cadena;
    std::string nombre_nuevo = args[2].cadena;
    
    int error = 0;
    zip_t* archivo = zip_open(nombre_zip.c_str(), ZIP_CREATE, &error);
    if (!archivo) return wini_crear_booleano(false);
    
    zip_int64_t idx = zip_name_locate(archivo, nombre_viejo.c_str(), 0);
    if (idx < 0) {
        zip_close(archivo);
        return wini_crear_booleano(false);
    }
    
    int resultado = zip_file_rename(archivo, idx, nombre_nuevo.c_str(), ZIP_FL_OVERWRITE);
    zip_close(archivo);
    return wini_crear_booleano(resultado == 0);
}

WiniValor wini_zip_add_dir(WiniValor* args, int num_args) {
    if (num_args < 2 ||
        args[0].tipo != WINI_TIPO_CADENA ||
        args[1].tipo != WINI_TIPO_CADENA) {
        return wini_crear_booleano(false);
    }
    
    std::string nombre_zip = args[0].cadena;
    std::string nombre_dir = args[1].cadena;
    
    if (nombre_dir.back() != '/') nombre_dir += '/';
    
    int error = 0;
    zip_t* archivo = zip_open(nombre_zip.c_str(), ZIP_CREATE, &error);
    if (!archivo) return wini_crear_booleano(false);
    
    int resultado = zip_dir_add(archivo, nombre_dir.c_str(), ZIP_FL_OVERWRITE);
    zip_close(archivo);
    return wini_crear_booleano(resultado >= 0);
}

WiniValor wini_zip_add_from_memory(WiniValor* args, int num_args) {
    if (num_args < 3 ||
        args[0].tipo != WINI_TIPO_CADENA ||
        args[1].tipo != WINI_TIPO_CADENA ||
        args[2].tipo != WINI_TIPO_CADENA) {
        return wini_crear_booleano(false);
    }
    
    std::string nombre_zip = args[0].cadena;
    std::string nombre_interno = args[1].cadena;
    std::string contenido = args[2].cadena;
    
    int error = 0;
    zip_t* archivo = zip_open(nombre_zip.c_str(), ZIP_CREATE, &error);
    if (!archivo) return wini_crear_booleano(false);
    
    zip_source_t* source = zip_source_buffer(archivo, 
                                             contenido.c_str(), 
                                             contenido.length(), 
                                             0);
    if (!source) {
        zip_close(archivo);
        return wini_crear_booleano(false);
    }
    
    zip_int64_t idx = zip_file_add(archivo, nombre_interno.c_str(), source, ZIP_FL_OVERWRITE);
    if (idx < 0) {
        zip_source_free(source);
        zip_close(archivo);
        return wini_crear_booleano(false);
    }
    
    zip_close(archivo);
    return wini_crear_booleano(true);
}

WiniValor wini_zip_file_info(WiniValor* args, int num_args) {
    if (num_args < 2 ||
        args[0].tipo != WINI_TIPO_CADENA ||
        args[1].tipo != WINI_TIPO_CADENA) {
        return wini_crear_ninguno();
    }
    
    std::string nombre_zip = args[0].cadena;
    std::string archivo_buscar = args[1].cadena;
    
    int error = 0;
    zip_t* archivo = zip_open(nombre_zip.c_str(), ZIP_RDONLY, &error);
    if (!archivo) return wini_crear_ninguno();
    
    struct zip_stat st;
    zip_stat_init(&st);
    
    if (zip_stat(archivo, archivo_buscar.c_str(), 0, &st) != 0) {
        zip_close(archivo);
        return wini_crear_ninguno();
    }
    
    WiniValor claves[8];
    WiniValor valores[8];
    int idx = 0;
    
    claves[idx] = wini_crear_cadena("nombre");
    valores[idx] = wini_crear_cadena(zip_get_name(archivo, st.index, 0));
    idx++;
    
    claves[idx] = wini_crear_cadena("volumen");
    valores[idx] = wini_crear_entero(st.size);
    idx++;
    
    claves[idx] = wini_crear_cadena("comprimido");
    valores[idx] = wini_crear_entero(st.comp_size);
    idx++;
    
    claves[idx] = wini_crear_cadena("metodo_compresion");
    valores[idx] = wini_crear_entero(st.comp_method);
    idx++;
    
    claves[idx] = wini_crear_cadena("crc32");
    valores[idx] = wini_crear_entero(st.crc);
    idx++;
    
    claves[idx] = wini_crear_cadena("modificado");
    valores[idx] = wini_crear_entero(st.mtime);
    idx++;
    
    claves[idx] = wini_crear_cadena("indice");
    valores[idx] = wini_crear_entero(st.index);
    idx++;
    
    zip_close(archivo);
    return wini_crear_diccionario(claves, valores, idx);
}

WiniValor wini_zip_set_comment(WiniValor* args, int num_args) {
    if (num_args < 2 ||
        args[0].tipo != WINI_TIPO_CADENA ||
        args[1].tipo != WINI_TIPO_CADENA) {
        return wini_crear_booleano(false);
    }
    
    std::string nombre_zip = args[0].cadena;
    std::string comentario = args[1].cadena;
    
    int error = 0;
    zip_t* archivo = zip_open(nombre_zip.c_str(), ZIP_CREATE, &error);
    if (!archivo) return wini_crear_booleano(false);
    
    int resultado = zip_set_archive_comment(archivo, comentario.c_str(), (zip_uint16_t)comentario.length());
    zip_close(archivo);
    return wini_crear_booleano(resultado == 0);
}

WiniValor wini_zip_get_comment(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_CADENA) {
        return wini_crear_ninguno();
    }
    
    std::string nombre_zip = args[0].cadena;
    
    int error = 0;
    zip_t* archivo = zip_open(nombre_zip.c_str(), ZIP_RDONLY, &error);
    if (!archivo) return wini_crear_ninguno();
    
    int len = 0;  // ← Cambiado de zip_uint16_t a int
    const char* comentario = zip_get_archive_comment(archivo, &len, 0);
    
    WiniValor resultado;
    if (comentario && len > 0) {
        resultado = wini_crear_cadena(std::string(comentario, len).c_str());
    } else {
        resultado = wini_crear_ninguno();
    }
    
    zip_close(archivo);
    return resultado;
}

WiniValor wini_zip_add_directory(WiniValor* args, int num_args) {
    if (num_args < 2 ||
        args[0].tipo != WINI_TIPO_CADENA ||
        args[1].tipo != WINI_TIPO_CADENA) {
        return wini_crear_booleano(false);
    }
    
    std::string nombre_zip = args[0].cadena;
    std::string directorio = args[1].cadena;
    
    int error = 0;
    zip_t* archivo = zip_open(nombre_zip.c_str(), ZIP_CREATE, &error);
    if (!archivo) return wini_crear_booleano(false);
    
    std::string patron = directorio + "\\*";
    WIN32_FIND_DATAA findData;
    HANDLE hFind = FindFirstFileA(patron.c_str(), &findData);
    
    if (hFind == INVALID_HANDLE_VALUE) {
        zip_close(archivo);
        return wini_crear_booleano(false);
    }
    
    bool exito = true;
    do {
        if (strcmp(findData.cFileName, ".") == 0 || 
            strcmp(findData.cFileName, "..") == 0) continue;
        
        std::string ruta_completa = directorio + "\\" + findData.cFileName;
        
        zip_source_t* source = zip_source_file(archivo, ruta_completa.c_str(), 0, 0);
        if (!source) {
            exito = false;
            continue;
        }
        
        zip_int64_t idx = zip_file_add(archivo, findData.cFileName, source, ZIP_FL_OVERWRITE);
        if (idx < 0) {
            zip_source_free(source);
            exito = false;
        }
    } while (FindNextFileA(hFind, &findData));
    
    FindClose(hFind);
    zip_close(archivo);
    return wini_crear_booleano(exito);
}

// ===== FUNCIONES CON CONTRASEÑA =====

WiniValor wini_zip_set_password(WiniValor* args, int num_args) {
    if (num_args < 2 ||
        args[0].tipo != WINI_TIPO_CADENA ||
        args[1].tipo != WINI_TIPO_CADENA) {
        return wini_crear_booleano(false);
    }
    
    std::string nombre_zip = args[0].cadena;
    std::string password = args[1].cadena;
    
    int error = 0;
    zip_t* archivo = zip_open(nombre_zip.c_str(), ZIP_CREATE, &error);
    if (!archivo) return wini_crear_booleano(false);
    
    int resultado = zip_set_default_password(archivo, password.c_str());
    zip_close(archivo);
    return wini_crear_booleano(resultado == 0);
}

WiniValor wini_zip_add_encrypted(WiniValor* args, int num_args) {
    if (num_args < 3 ||
        args[0].tipo != WINI_TIPO_CADENA ||
        args[1].tipo != WINI_TIPO_CADENA ||
        args[2].tipo != WINI_TIPO_CADENA) {
        return wini_crear_booleano(false);
    }
    
    std::string nombre_zip = args[0].cadena;
    std::string archivo_origen = args[1].cadena;
    std::string password = args[2].cadena;
    
    int error = 0;
    zip_t* archivo = zip_open(nombre_zip.c_str(), ZIP_CREATE, &error);
    if (!archivo) return wini_crear_booleano(false);
    
    zip_set_default_password(archivo, password.c_str());
    
    zip_source_t* source = zip_source_file(archivo, archivo_origen.c_str(), 0, 0);
    if (!source) {
        zip_close(archivo);
        return wini_crear_booleano(false);
    }
    
    std::string nombre_interno = archivo_origen;
    size_t pos = nombre_interno.find_last_of("\\/");
    if (pos != std::string::npos) {
        nombre_interno = nombre_interno.substr(pos + 1);
    }
    
    // Cambiar ZIP_FL_ENC_AES_256 por ZIP_EM_AES_256
    // Si no funciona, usar 0 (encriptación tradicional)
    zip_int64_t idx = zip_file_add(archivo, nombre_interno.c_str(), source, ZIP_FL_OVERWRITE);
    if (idx < 0) {
        zip_source_free(source);
        zip_close(archivo);
        return wini_crear_booleano(false);
    }
    
    // Intentar establecer encriptación AES-256
    int enc_result = zip_file_set_encryption(archivo, idx, ZIP_EM_AES_256, password.c_str());
    if (enc_result < 0) {
        // Si falla, intentar con encriptación tradicional
        zip_file_set_encryption(archivo, idx, ZIP_EM_TRADITIONAL, password.c_str());
    }
    
    zip_close(archivo);
    return wini_crear_booleano(true);
}

WiniValor wini_zip_extract_with_password(WiniValor* args, int num_args) {
    if (num_args < 3 ||
        args[0].tipo != WINI_TIPO_CADENA ||
        args[1].tipo != WINI_TIPO_CADENA ||
        args[2].tipo != WINI_TIPO_CADENA) {
        return wini_crear_booleano(false);
    }
    
    std::string nombre_zip = args[0].cadena;
    std::string destino = args[1].cadena;
    std::string password = args[2].cadena;
    
    int error = 0;
    zip_t* archivo = zip_open(nombre_zip.c_str(), ZIP_RDONLY, &error);
    if (!archivo) return wini_crear_booleano(false);
    
    // Establecer contraseña para extraer
    zip_set_default_password(archivo, password.c_str());
    
    zip_int64_t num_entries = zip_get_num_entries(archivo, 0);
    bool exito = true;
    
    for (zip_int64_t i = 0; i < num_entries; i++) {
        const char* nombre = zip_get_name(archivo, i, 0);
        if (!nombre) continue;
        
        std::string ruta_salida = destino + "\\" + nombre;
        size_t pos = ruta_salida.find_last_of("\\/");
        if (pos != std::string::npos) {
            std::string dir = ruta_salida.substr(0, pos);
            crear_directorios(dir);
        }
        
        // Abrir con contraseña
        zip_file_t* file = zip_fopen_index_encrypted(archivo, i, 0, password.c_str());
        if (!file) {
            exito = false;
            continue;
        }
        
        std::ofstream out(ruta_salida, std::ios::binary);
        if (!out.is_open()) {
            zip_fclose(file);
            exito = false;
            continue;
        }
        
        char buffer[8192];
        zip_int64_t bytes;
        while ((bytes = zip_fread(file, buffer, sizeof(buffer))) > 0) {
            out.write(buffer, bytes);
        }
        
        out.close();
        zip_fclose(file);
    }
    
    zip_close(archivo);
    return wini_crear_booleano(exito);
}

// ===== FUNCIONES ÚTILES ADICIONALES =====

WiniValor wini_zip_count(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_CADENA) {
        return wini_crear_entero(0);
    }
    
    std::string nombre_zip = args[0].cadena;
    int error = 0;
    zip_t* archivo = zip_open(nombre_zip.c_str(), ZIP_RDONLY, &error);
    if (!archivo) return wini_crear_entero(0);
    
    zip_int64_t num_entries = zip_get_num_entries(archivo, 0);
    zip_close(archivo);
    return wini_crear_entero(num_entries);
}

WiniValor wini_zip_contains(WiniValor* args, int num_args) {
    if (num_args < 2 ||
        args[0].tipo != WINI_TIPO_CADENA ||
        args[1].tipo != WINI_TIPO_CADENA) {
        return wini_crear_booleano(false);
    }
    
    std::string nombre_zip = args[0].cadena;
    std::string archivo_buscar = args[1].cadena;
    
    int error = 0;
    zip_t* archivo = zip_open(nombre_zip.c_str(), ZIP_RDONLY, &error);
    if (!archivo) return wini_crear_booleano(false);
    
    zip_int64_t idx = zip_name_locate(archivo, archivo_buscar.c_str(), 0);
    zip_close(archivo);
    return wini_crear_booleano(idx >= 0);
}