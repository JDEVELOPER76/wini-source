// os.cpp - versión mejorada con manejo correcto de WiniValor
#include "winiapi.h"
#include <windows.h>
#include <shlwapi.h>
#include <psapi.h>
#include <string>
#include <vector>
#include <map>
#include <memory>
#include <ctime>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <algorithm>

#pragma comment(lib, "shlwapi.lib")
#pragma comment(lib, "psapi.lib")

extern "C" {

// ===== FUNCIONES DECLARADAS =====
WiniValor wini_cmd(WiniValor* args, int num_args);
WiniValor wini_system(WiniValor* args, int num_args);
WiniValor wini_getenv(WiniValor* args, int num_args);
WiniValor wini_setenv(WiniValor* args, int num_args);
WiniValor wini_list_files(WiniValor* args, int num_args);
WiniValor wini_file_exists(WiniValor* args, int num_args);
WiniValor wini_read_file(WiniValor* args, int num_args);
WiniValor wini_write_file(WiniValor* args, int num_args);
WiniValor wini_append_file(WiniValor* args, int num_args);
WiniValor wini_delete_file(WiniValor* args, int num_args);
WiniValor wini_copy_file(WiniValor* args, int num_args);
WiniValor wini_move_file(WiniValor* args, int num_args);
WiniValor wini_file_info(WiniValor* args, int num_args);
WiniValor wini_create_dir(WiniValor* args, int num_args);
WiniValor wini_delete_dir(WiniValor* args, int num_args);
WiniValor wini_get_cwd(WiniValor* args, int num_args);
WiniValor wini_set_cwd(WiniValor* args, int num_args);
WiniValor wini_get_drives(WiniValor* args, int num_args);
WiniValor wini_get_drive_info(WiniValor* args, int num_args);
WiniValor wini_get_pid(WiniValor* args, int num_args);
WiniValor wini_get_processes(WiniValor* args, int num_args);
WiniValor wini_kill_process(WiniValor* args, int num_args);
WiniValor wini_get_memory_info(WiniValor* args, int num_args);
WiniValor wini_get_cpu_info(WiniValor* args, int num_args);
WiniValor wini_sleep(WiniValor* args, int num_args);
WiniValor wini_get_time(WiniValor* args, int num_args);
WiniValor wini_format_time(WiniValor* args, int num_args);
WiniValor wini_get_username(WiniValor* args, int num_args);
WiniValor wini_get_computer_name(WiniValor* args, int num_args);
WiniValor wini_is_admin(WiniValor* args, int num_args);
WiniValor wini_open_url(WiniValor* args, int num_args);
WiniValor wini_beep(WiniValor* args, int num_args);
WiniValor wini_get_clipboard(WiniValor* args, int num_args);
WiniValor wini_set_clipboard(WiniValor* args, int num_args);

// ===== VARIABLES GLOBALES DEL MÓDULO =====
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

std::string format_file_time(FILETIME ft) {
    SYSTEMTIME st;
    FileTimeToSystemTime(&ft, &st);
    char buffer[100];
    sprintf_s(buffer, sizeof(buffer), "%04d-%02d-%02d %02d:%02d:%02d",
              st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond);
    return std::string(buffer);
}

// ===== INICIALIZACIÓN DEL MÓDULO =====
WINI_API bool wini_module_init(WiniContexto ctx, void* (*registrar)(const char* nombre, void* fn)) {
    g_contexto = ctx;
    
    // Registrar funciones
    registrar("cmd", (void*)wini_cmd);
    registrar("ejecutar", (void*)wini_system);
    registrar("obtener_variable", (void*)wini_getenv);
    registrar("establecer_variable", (void*)wini_setenv);
    registrar("listar_archivos", (void*)wini_list_files);
    registrar("archivo_existe", (void*)wini_file_exists);
    registrar("leer_archivo", (void*)wini_read_file);
    registrar("escribir_archivo", (void*)wini_write_file);
    registrar("anadir_archivo", (void*)wini_append_file);
    registrar("eliminar_archivo", (void*)wini_delete_file);
    registrar("copiar_archivo", (void*)wini_copy_file);
    registrar("mover_archivo", (void*)wini_move_file);
    registrar("info_archivo", (void*)wini_file_info);
    registrar("crear_directorio", (void*)wini_create_dir);
    registrar("eliminar_directorio", (void*)wini_delete_dir);
    registrar("obtener_directorio", (void*)wini_get_cwd);
    registrar("establecer_directorio", (void*)wini_set_cwd);
    registrar("obtener_unidades", (void*)wini_get_drives);
    registrar("info_unidad", (void*)wini_get_drive_info);
    registrar("obtener_pid", (void*)wini_get_pid);
    registrar("obtener_procesos", (void*)wini_get_processes);
    registrar("matar_proceso", (void*)wini_kill_process);
    registrar("info_memoria", (void*)wini_get_memory_info);
    registrar("info_cpu", (void*)wini_get_cpu_info);
    registrar("dormir", (void*)wini_sleep);
    registrar("obtener_tiempo", (void*)wini_get_time);
    registrar("formatear_tiempo", (void*)wini_format_time);
    registrar("obtener_usuario", (void*)wini_get_username);
    registrar("obtener_computadora", (void*)wini_get_computer_name);
    registrar("es_admin", (void*)wini_is_admin);
    registrar("abrir_url", (void*)wini_open_url);
    registrar("beep", (void*)wini_beep);
    registrar("obtener_portapapeles", (void*)wini_get_clipboard);
    registrar("establecer_portapapeles", (void*)wini_set_clipboard);

    
    // Variables del sistema
    char* os_name = getenv("OS");
    wini_set_variable(ctx, "OS_VERSION", wini_crear_cadena(os_name ? os_name : "Windows"));
    
    // Obtener versión de Windows
    OSVERSIONINFOEXW osvi = { sizeof(OSVERSIONINFOEXW) };
    if (GetVersionExW((LPOSVERSIONINFOW)&osvi)) {
        char version[100];
        sprintf_s(version, sizeof(version), "Windows %d.%d (Build %d)", 
                 osvi.dwMajorVersion, osvi.dwMinorVersion, osvi.dwBuildNumber);
        wini_set_variable(ctx, "WINDOWS_VERSION", wini_crear_cadena(version));
    }
    
    // Variables de entorno útiles
    wini_set_variable(ctx, "TEMP", wini_crear_cadena(getenv("TEMP") ? getenv("TEMP") : ""));
    wini_set_variable(ctx, "USERNAME", wini_crear_cadena(getenv("USERNAME") ? getenv("USERNAME") : ""));
    wini_set_variable(ctx, "COMPUTERNAME", wini_crear_cadena(getenv("COMPUTERNAME") ? getenv("COMPUTERNAME") : ""));
    
    return true;
}

WINI_API void wini_module_cleanup(WiniContexto ctx) {
    g_contexto = nullptr;
}

// ===== FUNCIONES DEL MÓDULO =====

// Ejecutar comando del sistema
WiniValor wini_cmd(WiniValor* args, int num_args) {
    WiniValor resultado;
    resultado.tipo = WINI_TIPO_NINGUNO;
    resultado.puntero = nullptr;
    
    if (num_args < 1 || args[0].tipo != WINI_TIPO_CADENA) {
        return resultado;
    }
    
    std::string comando = args[0].cadena ? args[0].cadena : "";
    std::wstring wcomando = string_to_wstring(comando);
    
    SECURITY_ATTRIBUTES sa = { sizeof(SECURITY_ATTRIBUTES), NULL, TRUE };
    HANDLE hReadPipe, hWritePipe;
    if (!CreatePipe(&hReadPipe, &hWritePipe, &sa, 0)) {
        return resultado;
    }
    
    PROCESS_INFORMATION pi = {0};
    STARTUPINFOW si = {0};
    si.cb = sizeof(STARTUPINFOW);
    si.dwFlags = STARTF_USESTDHANDLES;
    si.hStdOutput = hWritePipe;
    si.hStdError = hWritePipe;
    
    std::wstring comandoCompleto = L"cmd /c " + wcomando;
    
    if (!CreateProcessW(NULL, (LPWSTR)comandoCompleto.c_str(), NULL, NULL, TRUE, 
                        0, NULL, NULL, &si, &pi)) {
        CloseHandle(hReadPipe);
        CloseHandle(hWritePipe);
        return resultado;
    }
    
    CloseHandle(hWritePipe);
    WaitForSingleObject(pi.hProcess, INFINITE);
    
    char buffer[4096];
    DWORD bytesRead;
    std::string salida;
    
    while (ReadFile(hReadPipe, buffer, sizeof(buffer) - 1, &bytesRead, NULL) && bytesRead > 0) {
        buffer[bytesRead] = '\0';
        salida += buffer;
    }
    
    // Obtener código de salida
    DWORD exitCode;
    GetExitCodeProcess(pi.hProcess, &exitCode);
    
    CloseHandle(hReadPipe);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    
    // Devolver un diccionario con salida y código de error
    WiniValor claves[2];
    claves[0] = wini_crear_cadena("output");
    claves[1] = wini_crear_cadena("exit_code");
    
    WiniValor valores[2];
    valores[0] = wini_crear_cadena(salida.c_str());
    valores[1] = wini_crear_entero(exitCode);
    
    return wini_crear_diccionario(claves, valores, 2);
}

// Ejecutar comando y mostrar salida en consola
WiniValor wini_system(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_CADENA || !args[0].cadena) {
        return wini_crear_entero(-1);
    }
    
    std::string comando = args[0].cadena;
    int resultado = system(comando.c_str());
    return wini_crear_entero(resultado);
}

// Obtener variable de entorno
WiniValor wini_getenv(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_CADENA) {
        return wini_crear_ninguno();
    }
    
    std::string nombre = args[0].cadena ? args[0].cadena : "";
    std::wstring wnombre = string_to_wstring(nombre);
    
    DWORD size = GetEnvironmentVariableW(wnombre.c_str(), NULL, 0);
    if (size > 0) {
        std::wstring wvalor(size, L'\0');
        GetEnvironmentVariableW(wnombre.c_str(), &wvalor[0], size);
        return wini_crear_cadena(wstring_to_string(wvalor).c_str());
    }
    return wini_crear_ninguno();
}

// Establecer variable de entorno
WiniValor wini_setenv(WiniValor* args, int num_args) {
    if (num_args < 2 || 
        args[0].tipo != WINI_TIPO_CADENA ||
        args[1].tipo != WINI_TIPO_CADENA) {
        return wini_crear_booleano(false);
    }
    
    std::wstring wnombre = string_to_wstring(args[0].cadena ? args[0].cadena : "");
    std::wstring wvalor = string_to_wstring(args[1].cadena ? args[1].cadena : "");
    
    bool exito = SetEnvironmentVariableW(wnombre.c_str(), wvalor.c_str()) == TRUE;
    return wini_crear_booleano(exito);
}

// Listar archivos en un directorio
WiniValor wini_list_files(WiniValor* args, int num_args) {
    std::string ruta = ".";
    if (num_args > 0 && args[0].tipo == WINI_TIPO_CADENA && args[0].cadena) {
        ruta = args[0].cadena;
    }
    
    // Si la ruta es "." o está vacía, usar el directorio actual
    if (ruta == "." || ruta.empty()) {
        char buffer[MAX_PATH];
        DWORD size = GetCurrentDirectoryA(MAX_PATH, buffer);
        if (size > 0) {
            ruta = buffer;
        }
    }
    
    // Asegurar que la ruta termine con backslash
    if (!ruta.empty() && ruta.back() != '\\' && ruta.back() != '/') {
        ruta += "\\";
    }
    
    std::string patron = ruta + "*";
    WIN32_FIND_DATAA findData;
    HANDLE hFind = FindFirstFileA(patron.c_str(), &findData);
    
    std::vector<WiniValor> archivos;
    
    if (hFind != INVALID_HANDLE_VALUE) {
        do {
            if (strcmp(findData.cFileName, ".") != 0 && 
                strcmp(findData.cFileName, "..") != 0) {
                archivos.push_back(wini_crear_cadena(findData.cFileName));
            }
        } while (FindNextFileA(hFind, &findData));
        FindClose(hFind);
    }
    
    if (archivos.empty()) {
        return wini_crear_lista(nullptr, 0);
    }
    
    return wini_crear_lista(archivos.data(), (int)archivos.size());
}

// Verificar si un archivo existe
WiniValor wini_file_exists(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_CADENA || !args[0].cadena) {
        return wini_crear_booleano(false);
    }
    
    DWORD attrs = GetFileAttributesA(args[0].cadena);
    return wini_crear_booleano(attrs != INVALID_FILE_ATTRIBUTES);
}

// Leer archivo
WiniValor wini_read_file(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_CADENA || !args[0].cadena) {
        return wini_crear_ninguno();
    }
    
    std::string ruta = args[0].cadena;
    std::ifstream archivo(ruta, std::ios::binary);
    
    if (!archivo.is_open()) {
        return wini_crear_ninguno();
    }
    
    std::stringstream buffer;
    buffer << archivo.rdbuf();
    archivo.close();
    
    return wini_crear_cadena(buffer.str().c_str());
}

// Escribir archivo


// Escribir archivo (crea el archivo si no existe)
WiniValor wini_write_file(WiniValor* args, int num_args) {
    if (num_args < 2 || 
        args[0].tipo != WINI_TIPO_CADENA || !args[0].cadena) {
        return wini_crear_booleano(false);
    }
    
    std::string ruta = args[0].cadena;
    // Aceptar cualquier tipo de valor como contenido (entero, decimal,
    // booleano, etc.), convirtiéndolo a texto igual que escribir()/las
    // cadenas interpoladas, en vez de fallar en silencio cuando no es
    // exactamente una cadena.
    std::string contenido = wini_valor_a_cadena(args[1]);
    
    // Obtener el directorio actual para rutas relativas
    char cwdBuffer[MAX_PATH];
    std::string rutaCompleta = ruta;
    
    // Si la ruta es relativa (no comienza con C:\, D:\, etc.)
    if (ruta.length() < 3 || ruta[1] != ':') {
        if (GetCurrentDirectoryA(MAX_PATH, cwdBuffer)) {
            std::string cwd = cwdBuffer;
            // Asegurar que termine con backslash
            if (!cwd.empty() && cwd.back() != '\\') {
                cwd += "\\";
            }
            rutaCompleta = cwd + ruta;
        }
    }
    
    // Crear los directorios si no existen
    std::string directorio = rutaCompleta;
    size_t lastSlash = directorio.find_last_of("\\/");
    if (lastSlash != std::string::npos) {
        directorio = directorio.substr(0, lastSlash);
        // Crear directorios recursivamente
        std::string path = "";
        std::stringstream ss(directorio);
        std::string segment;
        while (std::getline(ss, segment, '\\')) {
            if (segment.empty()) {
                // Si el segmento está vacío, podría ser una unidad de disco (C:)
                if (path.empty() && rutaCompleta.length() >= 2 && rutaCompleta[1] == ':') {
                    path = rutaCompleta.substr(0, 3); // C:\
                    continue;
                }
                continue;
            }
            if (path.empty()) {
                // Primer segmento: podría ser "C:" o una carpeta
                if (segment.length() == 2 && segment[1] == ':') {
                    path = segment + "\\";
                } else {
                    path = segment;
                }
            } else {
                // Asegurar que path termine con backslash
                if (path.back() != '\\') {
                    path += "\\";
                }
                path += segment;
            }
            
            // Intentar crear el directorio si no existe
            DWORD attrs = GetFileAttributesA(path.c_str());
            if (attrs == INVALID_FILE_ATTRIBUTES) {
                if (!CreateDirectoryA(path.c_str(), NULL)) {
                    // Si falla, continuar de todos modos (quizás el directorio ya existe)
                }
            }
        }
    }
    
    // Escribir el archivo
    std::ofstream archivo(rutaCompleta, std::ios::binary);
    if (!archivo.is_open()) {
        // Intentar con la ruta original
        archivo.open(ruta, std::ios::binary);
        if (!archivo.is_open()) {
            return wini_crear_booleano(false);
        }
    }
    
    archivo.write(contenido.c_str(), contenido.length());
    archivo.close();
    
    // Verificar que el archivo se creó
    DWORD attrs = GetFileAttributesA(rutaCompleta.c_str());
    return wini_crear_booleano(attrs != INVALID_FILE_ATTRIBUTES);
}

// Añadir al final de un archivo
WiniValor wini_append_file(WiniValor* args, int num_args) {
    if (num_args < 2 || 
        args[0].tipo != WINI_TIPO_CADENA || !args[0].cadena) {
        return wini_crear_booleano(false);
    }
    
    // Aceptar cualquier tipo de valor como contenido, igual que en
    // wini_write_file: se convierte a texto en lugar de exigir cadena.
    std::string contenido = wini_valor_a_cadena(args[1]);
    
    std::string ruta = args[0].cadena;
    std::ofstream archivo(ruta, std::ios::binary | std::ios::app);
    
    if (!archivo.is_open()) {
        return wini_crear_booleano(false);
    }
    
    archivo.write(contenido.c_str(), contenido.size());
    archivo.close();
    
    return wini_crear_booleano(true);
}

// Eliminar archivo
WiniValor wini_delete_file(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_CADENA || !args[0].cadena) {
        return wini_crear_booleano(false);
    }
    
    bool exito = DeleteFileA(args[0].cadena) == TRUE;
    return wini_crear_booleano(exito);
}

// Copiar archivo
WiniValor wini_copy_file(WiniValor* args, int num_args) {
    if (num_args < 2 || 
        args[0].tipo != WINI_TIPO_CADENA || !args[0].cadena ||
        args[1].tipo != WINI_TIPO_CADENA || !args[1].cadena) {
        return wini_crear_booleano(false);
    }
    
    bool exito = CopyFileA(args[0].cadena, args[1].cadena, FALSE) == TRUE;
    return wini_crear_booleano(exito);
}

// Mover archivo
WiniValor wini_move_file(WiniValor* args, int num_args) {
    if (num_args < 2 || 
        args[0].tipo != WINI_TIPO_CADENA || !args[0].cadena ||
        args[1].tipo != WINI_TIPO_CADENA || !args[1].cadena) {
        return wini_crear_booleano(false);
    }
    
    bool exito = MoveFileA(args[0].cadena, args[1].cadena) == TRUE;
    return wini_crear_booleano(exito);
}

// Información de archivo
WiniValor wini_file_info(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_CADENA || !args[0].cadena) {
        return wini_crear_ninguno();
    }
    
    WIN32_FILE_ATTRIBUTE_DATA data;
    if (!GetFileAttributesExA(args[0].cadena, GetFileExInfoStandard, &data)) {
        return wini_crear_ninguno();
    }
    
    WiniValor claves[9];
    WiniValor valores[9];
    
    claves[0] = wini_crear_cadena("exists");
    valores[0] = wini_crear_booleano(true);
    
    claves[1] = wini_crear_cadena("size");
    valores[1] = wini_crear_entero(((int64_t)data.nFileSizeHigh << 32) | data.nFileSizeLow);
    
    claves[2] = wini_crear_cadena("is_directory");
    valores[2] = wini_crear_booleano((data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0);
    
    claves[3] = wini_crear_cadena("is_hidden");
    valores[3] = wini_crear_booleano((data.dwFileAttributes & FILE_ATTRIBUTE_HIDDEN) != 0);
    
    claves[4] = wini_crear_cadena("is_readonly");
    valores[4] = wini_crear_booleano((data.dwFileAttributes & FILE_ATTRIBUTE_READONLY) != 0);
    
    claves[5] = wini_crear_cadena("is_system");
    valores[5] = wini_crear_booleano((data.dwFileAttributes & FILE_ATTRIBUTE_SYSTEM) != 0);
    
    claves[6] = wini_crear_cadena("created");
    valores[6] = wini_crear_cadena(format_file_time(data.ftCreationTime).c_str());
    
    claves[7] = wini_crear_cadena("modified");
    valores[7] = wini_crear_cadena(format_file_time(data.ftLastWriteTime).c_str());
    
    claves[8] = wini_crear_cadena("accessed");
    valores[8] = wini_crear_cadena(format_file_time(data.ftLastAccessTime).c_str());
    
    return wini_crear_diccionario(claves, valores, 9);
}

// Crear directorio
WiniValor wini_create_dir(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_CADENA || !args[0].cadena) {
        return wini_crear_booleano(false);
    }
    
    bool exito = CreateDirectoryA(args[0].cadena, NULL) == TRUE;
    return wini_crear_booleano(exito);
}

// Eliminar directorio
WiniValor wini_delete_dir(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_CADENA || !args[0].cadena) {
        return wini_crear_booleano(false);
    }
    
    bool exito = RemoveDirectoryA(args[0].cadena) == TRUE;
    return wini_crear_booleano(exito);
}

// Obtener directorio actual
WiniValor wini_get_cwd(WiniValor* args, int num_args) {
    char buffer[MAX_PATH];
    DWORD size = GetCurrentDirectoryA(MAX_PATH, buffer);
    if (size > 0) {
        return wini_crear_cadena(buffer);
    }
    return wini_crear_ninguno();
}

// Establecer directorio actual
WiniValor wini_set_cwd(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_CADENA || !args[0].cadena) {
        return wini_crear_booleano(false);
    }
    
    bool exito = SetCurrentDirectoryA(args[0].cadena) == TRUE;
    return wini_crear_booleano(exito);
}

// Obtener unidades de disco
WiniValor wini_get_drives(WiniValor* args, int num_args) {
    DWORD drives = GetLogicalDrives();
    std::vector<WiniValor> unidades;
    
    for (int i = 0; i < 26; i++) {
        if (drives & (1 << i)) {
            char drive[4] = { (char)('A' + i), ':', '\\', '\0' };
            unidades.push_back(wini_crear_cadena(drive));
        }
    }
    
    return wini_crear_lista(unidades.data(), (int)unidades.size());
}

// Información de unidad de disco
WiniValor wini_get_drive_info(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_CADENA || !args[0].cadena) {
        return wini_crear_ninguno();
    }
    
    std::string drive = args[0].cadena;
    if (drive.length() < 2 || drive[1] != ':') {
        return wini_crear_ninguno();
    }
    
    std::string root = drive.substr(0, 3);
    ULARGE_INTEGER freeBytes, totalBytes, totalFreeBytes;
    
    if (!GetDiskFreeSpaceExA(root.c_str(), &freeBytes, &totalBytes, &totalFreeBytes)) {
        return wini_crear_ninguno();
    }
    
    WiniValor claves[4];
    WiniValor valores[4];
    
    claves[0] = wini_crear_cadena("total");
    valores[0] = wini_crear_entero(totalBytes.QuadPart);
    
    claves[1] = wini_crear_cadena("free");
    valores[1] = wini_crear_entero(freeBytes.QuadPart);
    
    claves[2] = wini_crear_cadena("used");
    valores[2] = wini_crear_entero(totalBytes.QuadPart - freeBytes.QuadPart);
    
    claves[3] = wini_crear_cadena("percent_free");
    valores[3] = wini_crear_decimal((double)freeBytes.QuadPart / totalBytes.QuadPart * 100);
    
    return wini_crear_diccionario(claves, valores, 4);
}

// Obtener PID del proceso actual
WiniValor wini_get_pid(WiniValor* args, int num_args) {
    return wini_crear_entero(GetCurrentProcessId());
}

// Obtener lista de procesos
WiniValor wini_get_processes(WiniValor* args, int num_args) {
    DWORD processes[1024], bytesReturned;
    if (!EnumProcesses(processes, sizeof(processes), &bytesReturned)) {
        return wini_crear_lista(nullptr, 0);
    }
    
    DWORD numProcesses = bytesReturned / sizeof(DWORD);
    std::vector<WiniValor> lista;
    
    for (DWORD i = 0; i < numProcesses; i++) {
        HANDLE hProcess = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, 
                                      FALSE, processes[i]);
        if (hProcess) {
            char name[MAX_PATH] = "";
            HMODULE hModule;
            DWORD cbNeeded;
            if (EnumProcessModules(hProcess, &hModule, sizeof(hModule), &cbNeeded)) {
                GetModuleBaseNameA(hProcess, hModule, name, sizeof(name));
            }
            CloseHandle(hProcess);
            
            if (strlen(name) > 0) {
                WiniValor claves[2] = {
                    wini_crear_cadena("pid"),
                    wini_crear_cadena("name")
                };
                WiniValor valores[2] = {
                    wini_crear_entero(processes[i]),
                    wini_crear_cadena(name)
                };
                lista.push_back(wini_crear_diccionario(claves, valores, 2));
            }
        }
    }
    
    return wini_crear_lista(lista.data(), (int)lista.size());
}

// Matar proceso
WiniValor wini_kill_process(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_ENTERO) {
        return wini_crear_booleano(false);
    }
    
    HANDLE hProcess = OpenProcess(PROCESS_TERMINATE, FALSE, (DWORD)args[0].entero);
    if (!hProcess) {
        return wini_crear_booleano(false);
    }
    
    bool exito = TerminateProcess(hProcess, 0) == TRUE;
    CloseHandle(hProcess);
    return wini_crear_booleano(exito);
}

// Información de memoria
WiniValor wini_get_memory_info(WiniValor* args, int num_args) {
    MEMORYSTATUSEX memInfo = { sizeof(MEMORYSTATUSEX) };
    if (!GlobalMemoryStatusEx(&memInfo)) {
        return wini_crear_ninguno();
    }
    
    WiniValor claves[6];
    WiniValor valores[6];
    
    claves[0] = wini_crear_cadena("total");
    valores[0] = wini_crear_entero(memInfo.ullTotalPhys);
    
    claves[1] = wini_crear_cadena("available");
    valores[1] = wini_crear_entero(memInfo.ullAvailPhys);
    
    claves[2] = wini_crear_cadena("used");
    valores[2] = wini_crear_entero(memInfo.ullTotalPhys - memInfo.ullAvailPhys);
    
    claves[3] = wini_crear_cadena("percent_used");
    valores[3] = wini_crear_decimal(memInfo.dwMemoryLoad);
    
    claves[4] = wini_crear_cadena("total_virtual");
    valores[4] = wini_crear_entero(memInfo.ullTotalVirtual);
    
    claves[5] = wini_crear_cadena("available_virtual");
    valores[5] = wini_crear_entero(memInfo.ullAvailVirtual);
    
    return wini_crear_diccionario(claves, valores, 6);
}

// Información de CPU
WiniValor wini_get_cpu_info(WiniValor* args, int num_args) {
    SYSTEM_INFO sysInfo;
    GetSystemInfo(&sysInfo);
    
    WiniValor claves[3];
    WiniValor valores[3];
    
    claves[0] = wini_crear_cadena("cores");
    valores[0] = wini_crear_entero(sysInfo.dwNumberOfProcessors);
    
    claves[1] = wini_crear_cadena("architecture");
    valores[1] = wini_crear_entero(sysInfo.wProcessorArchitecture);
    
    // Carga de CPU (simplificada)
    claves[2] = wini_crear_cadena("usage");
    valores[2] = wini_crear_decimal(0.0);
    
    return wini_crear_diccionario(claves, valores, 3);
}

// Pausa (milisegundos)
WiniValor wini_sleep(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_ENTERO) {
        return wini_crear_ninguno();
    }
    
    Sleep((DWORD)args[0].entero);
    return wini_crear_ninguno();
}

// Obtener tiempo actual
WiniValor wini_get_time(WiniValor* args, int num_args) {
    time_t now = time(nullptr);
    struct tm* timeInfo = localtime(&now);
    if (!timeInfo) {
        return wini_crear_ninguno();
    }
    
    char buffer[100];
    strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", timeInfo);
    
    char date[50], timeStr[50], timestamp[50];
    strftime(date, sizeof(date), "%Y-%m-%d", timeInfo);
    strftime(timeStr, sizeof(timeStr), "%H:%M:%S", timeInfo);
    strftime(timestamp, sizeof(timestamp), "%Y%m%d_%H%M%S", timeInfo);
    
    WiniValor claves[5] = {
        wini_crear_cadena("now"),
        wini_crear_cadena("date"),
        wini_crear_cadena("time"),
        wini_crear_cadena("timestamp"),
        wini_crear_cadena("unix")
    };
    WiniValor valores[5] = {
        wini_crear_cadena(buffer),
        wini_crear_cadena(date),
        wini_crear_cadena(timeStr),
        wini_crear_cadena(timestamp),
        wini_crear_entero((int64_t)now)
    };
    
    return wini_crear_diccionario(claves, valores, 5);
}

// Formatear tiempo
WiniValor wini_format_time(WiniValor* args, int num_args) {
    if (num_args < 2 || 
        args[0].tipo != WINI_TIPO_ENTERO ||
        args[1].tipo != WINI_TIPO_CADENA || !args[1].cadena) {
        return wini_crear_ninguno();
    }
    
    time_t now = (time_t)args[0].entero;
    struct tm* timeInfo = localtime(&now);
    if (!timeInfo) {
        return wini_crear_ninguno();
    }
    
    char buffer[256];
    strftime(buffer, sizeof(buffer), args[1].cadena, timeInfo);
    return wini_crear_cadena(buffer);
}

// Obtener nombre de usuario
WiniValor wini_get_username(WiniValor* args, int num_args) {
    char buffer[256];
    DWORD size = sizeof(buffer);
    if (GetUserNameA(buffer, &size)) {
        return wini_crear_cadena(buffer);
    }
    return wini_crear_ninguno();
}

// Obtener nombre de computadora
WiniValor wini_get_computer_name(WiniValor* args, int num_args) {
    char buffer[MAX_COMPUTERNAME_LENGTH + 1];
    DWORD size = sizeof(buffer);
    if (GetComputerNameA(buffer, &size)) {
        return wini_crear_cadena(buffer);
    }
    return wini_crear_ninguno();
}

// Verificar si es administrador
WiniValor wini_is_admin(WiniValor* args, int num_args) {
    BOOL isAdmin = FALSE;
    SID_IDENTIFIER_AUTHORITY ntAuthority = SECURITY_NT_AUTHORITY;
    PSID adminGroup = nullptr;
    
    if (AllocateAndInitializeSid(&ntAuthority, 2, 
                                 SECURITY_BUILTIN_DOMAIN_RID,
                                 DOMAIN_ALIAS_RID_ADMINS,
                                 0, 0, 0, 0, 0, 0, &adminGroup)) {
        CheckTokenMembership(NULL, adminGroup, &isAdmin);
        FreeSid(adminGroup);
    }
    
    return wini_crear_booleano(isAdmin == TRUE);
}

// Abrir URL
WiniValor wini_open_url(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_CADENA || !args[0].cadena) {
        return wini_crear_booleano(false);
    }
    
    HINSTANCE result = ShellExecuteA(NULL, "open", args[0].cadena, NULL, NULL, SW_SHOWNORMAL);
    INT_PTR resultValue = reinterpret_cast<INT_PTR>(result);
    bool exito = resultValue > 32;
    return wini_crear_booleano(exito);
}

// Beep
WiniValor wini_beep(WiniValor* args, int num_args) {
    DWORD freq = 440, duration = 200;
    
    if (num_args > 0 && args[0].tipo == WINI_TIPO_ENTERO) {
        freq = (DWORD)args[0].entero;
    }
    if (num_args > 1 && args[1].tipo == WINI_TIPO_ENTERO) {
        duration = (DWORD)args[1].entero;
    }
    
    Beep(freq, duration);
    return wini_crear_ninguno();
}

// Obtener portapapeles
WiniValor wini_get_clipboard(WiniValor* args, int num_args) {
    if (!OpenClipboard(NULL)) {
        return wini_crear_ninguno();
    }
    
    HANDLE hData = GetClipboardData(CF_TEXT);
    if (!hData) {
        CloseClipboard();
        return wini_crear_ninguno();
    }
    
    char* text = (char*)GlobalLock(hData);
    WiniValor resultado = wini_crear_ninguno();
    if (text) {
        resultado = wini_crear_cadena(text);
        GlobalUnlock(hData);
    }
    
    CloseClipboard();
    return resultado;
}

// Establecer portapapeles
WiniValor wini_set_clipboard(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_CADENA || !args[0].cadena) {
        return wini_crear_booleano(false);
    }
    
    if (!OpenClipboard(NULL)) {
        return wini_crear_booleano(false);
    }
    
    EmptyClipboard();
    
    size_t len = strlen(args[0].cadena) + 1;
    HGLOBAL hMem = GlobalAlloc(GMEM_MOVEABLE, len);
    if (!hMem) {
        CloseClipboard();
        return wini_crear_booleano(false);
    }
    
    char* text = (char*)GlobalLock(hMem);
    if (text) {
        strcpy_s(text, len, args[0].cadena);
        GlobalUnlock(hMem);
        SetClipboardData(CF_TEXT, hMem);
    }
    
    CloseClipboard();
    return wini_crear_booleano(true);
}

} // extern "C"