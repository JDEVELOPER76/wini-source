// launcher.cpp - Launcher dinámico en C++ (VERSIÓN SIMPLIFICADA)
// Compilar: g++ -static -O2 -s -o launcher.exe launcher.cpp

#include <windows.h>
#include <stdio.h>
#include <string>
#include <vector>
#include <fstream>
#include <direct.h>
#include <iostream>
#include <sys/stat.h>

using namespace std;

// ============================================================
// ESTRUCTURA DE DATOS
// ============================================================

struct ArchivoEmbbedido {
    string nombre;
    long long offset;
    long long tamanio;
    bool esTexto;
};

// ============================================================
// FUNCIONES AUXILIARES
// ============================================================

bool directorioExiste(const string& path) {
    struct stat info;
    return stat(path.c_str(), &info) == 0 && (info.st_mode & S_IFDIR);
}

void crearDirectorio(const string& path) {
    if (path.empty()) return;
    if (directorioExiste(path)) return;
    
    string current = "";
    for (char c : path) {
        if (c == '\\' || c == '/') {
            if (!current.empty()) {
                CreateDirectoryA(current.c_str(), NULL);
            }
            current += c;
        } else {
            current += c;
        }
    }
    if (!current.empty()) {
        CreateDirectoryA(current.c_str(), NULL);
    }
}

void escribirArchivo(const string& nombre, const vector<char>& datos) {
    size_t lastSlash = nombre.find_last_of("\\/");
    if (lastSlash != string::npos) {
        crearDirectorio(nombre.substr(0, lastSlash));
    }
    
    ofstream file(nombre, ios::binary);
    if (file.is_open()) {
        file.write(datos.data(), datos.size());
        file.close();
    }
}

bool archivoExiste(const string& nombre) {
    struct stat info;
    return stat(nombre.c_str(), &info) == 0;
}

// ============================================================
// FUNCIÓN PRINCIPAL
// ============================================================

int main() {
    // 1. Obtener path del EXE actual
    char exePath[MAX_PATH];
    GetModuleFileNameA(NULL, exePath, MAX_PATH);
    
    // 2. Obtener el directorio del EXE
    string exeDir(exePath);
    size_t lastSlash = exeDir.find_last_of("\\/");
    if (lastSlash != string::npos) {
        exeDir = exeDir.substr(0, lastSlash + 1);
    }
    
    // 3. Crear variables de entorno
    string exePathStr = string(exePath);
    for (char& c : exePathStr) {
        if (c == '\\') c = '/';
    }
    string envVar = "EXE_PATH=" + exePathStr;
    _putenv(envVar.c_str());
    
    string exeDirStr = exeDir;
    for (char& c : exeDirStr) {
        if (c == '\\') c = '/';
    }
    string envDirVar = "EXE_DIR=" + exeDirStr;
    _putenv(envDirVar.c_str());
    
    // 4. Cambiar al directorio del EXE
    SetCurrentDirectoryA(exeDir.c_str());
    
    // 5. Abrir el EXE para leer datos embebidos
    ifstream exe(exePath, ios::binary);
    if (!exe.is_open()) {
        return 1;
    }
    
    exe.seekg(0, ios::end);
    long long exeSize = exe.tellg();
    exe.seekg(0, ios::beg);
    
    // 6. Buscar marca "WINIDATA"
    const char* marca = "WINIDATA";
    char buffer[8];
    long long posMarca = -1;
    
    long long start = exeSize - 10000;
    if (start < 0) start = 0;
    
    for (long long i = start; i < exeSize - 8; i++) {
        exe.seekg(i);
        exe.read(buffer, 8);
        if (memcmp(buffer, marca, 8) == 0) {
            posMarca = i + 8;
            break;
        }
    }
    
    if (posMarca == -1) {
        exe.close();
        return 1;
    }
    
    // 7. Leer byte de config de consola
    exe.seekg(posMarca);
    unsigned char consolaByte;
    exe.read((char*)&consolaByte, sizeof(unsigned char));
    posMarca += sizeof(unsigned char);
    bool consolaHabilitada = (consolaByte != 0);
    
    // 8. Leer índice
    exe.seekg(posMarca);
    int numArchivos;
    exe.read((char*)&numArchivos, sizeof(int));
    posMarca += sizeof(int);
    
    vector<ArchivoEmbbedido> archivos;
    string archivoPrincipal = "";
    
    for (int i = 0; i < numArchivos; i++) {
        // Leer nombre
        short nombreLen;
        exe.read((char*)&nombreLen, sizeof(short));
        posMarca += sizeof(short);
        
        vector<char> nombreBytes(nombreLen);
        exe.read(nombreBytes.data(), nombreLen);
        posMarca += nombreLen;
        string nombre(nombreBytes.data(), nombreLen);
        
        // Leer tamaño
        long long tamanio;
        exe.read((char*)&tamanio, sizeof(long long));
        posMarca += sizeof(long long);
        
        // Leer offset
        long long offset;
        exe.read((char*)&offset, sizeof(long long));
        posMarca += sizeof(long long);
        
        // Leer si es texto
        bool esTexto;
        exe.read((char*)&esTexto, sizeof(bool));
        posMarca += sizeof(bool);
        
        ArchivoEmbbedido a = {nombre, offset, tamanio, esTexto};
        archivos.push_back(a);
        
        // Guardar el nombre del archivo principal
        if (nombre.find("librerias") == string::npos && 
            nombre != "wini.exe" && 
            (nombre.find(".wn") != string::npos || nombre.find(".wini") != string::npos)) {
            archivoPrincipal = nombre;
        }
    }
    
    // Si no se encontró archivo principal, buscar cualquier .wn
    if (archivoPrincipal.empty()) {
        for (auto& a : archivos) {
            if (a.nombre.find(".wn") != string::npos && a.nombre != "wini.exe") {
                archivoPrincipal = a.nombre;
                break;
            }
        }
    }
    
    // 9. Extraer archivos (SOLO SI NO EXISTEN)
    for (int i = 0; i < (int)archivos.size(); i++) {
        ArchivoEmbbedido& a = archivos[i];
        
        // Saltar archivos que ya existen
        if (archivoExiste(a.nombre)) {
            continue;
        }
        
        // Leer datos
        vector<char> datos(a.tamanio);
        exe.seekg(a.offset);
        exe.read(datos.data(), a.tamanio);
        
        // Escribir archivo
        escribirArchivo(a.nombre, datos);
    }
    
    exe.close();
    
    // 10. Ejecutar wini.exe con el archivo principal
    if (archivoPrincipal.empty()) {
        archivoPrincipal = "main.wn";
    }
    
    // Construir el comando
    string cmd = "wini.exe \"" + archivoPrincipal + "\"";
    
    if (consolaHabilitada) {
        // EJECUTAR EN LA MISMA CONSOLA - Usar system()
        system(cmd.c_str());
    } else {
        // EJECUTAR SIN CONSOLA - Usar CreateProcess con CREATE_NO_WINDOW
        STARTUPINFOA si = { sizeof(si) };
        PROCESS_INFORMATION pi;
        CreateProcessA(NULL, (LPSTR)cmd.c_str(), NULL, NULL, FALSE, 
                       CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
        WaitForSingleObject(pi.hProcess, INFINITE);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }
    
    return 0;
}