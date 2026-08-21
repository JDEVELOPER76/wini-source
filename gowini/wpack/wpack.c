// wpack.c - Gestor de librerias Wini
// Compilar: gcc -o wpack.exe wpack.c

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>
#include <direct.h>
#include <sys/stat.h>
#include <time.h>

#define MAX_PATH_LEN 1024
#define MAX_CMD_LEN 4096
#define VERSION "1.0.0"

// Colores para la consola
void setColor(int color) {
    HANDLE hConsole = GetStdHandle(STD_OUTPUT_HANDLE);
    SetConsoleTextAttribute(hConsole, color);
}

void printGreen(const char* msg) {
    setColor(10);
    printf("%s", msg);
    setColor(7);
}

void printRed(const char* msg) {
    setColor(12);
    printf("%s", msg);
    setColor(7);
}

void printYellow(const char* msg) {
    setColor(14);
    printf("%s", msg);
    setColor(7);
}

void printBlue(const char* msg) {
    setColor(9);
    printf("%s", msg);
    setColor(7);
}

void printCyan(const char* msg) {
    setColor(11);
    printf("%s", msg);
    setColor(7);
}

// Obtener el nombre del repositorio desde la URL
void getRepoName(const char* url, char* nombre, int maxLen) {
    const char* lastSlash = strrchr(url, '/');
    if (!lastSlash) {
        strncpy(nombre, "repo", maxLen - 1);
        return;
    }
    
    const char* nameStart = lastSlash + 1;
    char temp[MAX_PATH_LEN];
    strncpy(temp, nameStart, MAX_PATH_LEN - 1);
    temp[MAX_PATH_LEN - 1] = '\0';
    
    char* gitExt = strstr(temp, ".git");
    if (gitExt) {
        *gitExt = '\0';
    }
    
    strncpy(nombre, temp, maxLen - 1);
    nombre[maxLen - 1] = '\0';
}

// Verificar si git esta instalado
int gitInstalled() {
    FILE* pipe = popen("git --version 2>nul", "r");
    if (!pipe) return 0;
    
    char buffer[128];
    int found = 0;
    while (fgets(buffer, sizeof(buffer), pipe) != NULL) {
        if (strstr(buffer, "git version") != NULL) {
            found = 1;
            break;
        }
    }
    pclose(pipe);
    return found;
}

// Verificar si un directorio existe
int directoryExists(const char* path) {
    DWORD attrs = GetFileAttributesA(path);
    return (attrs != INVALID_FILE_ATTRIBUTES && (attrs & FILE_ATTRIBUTE_DIRECTORY));
}

// Verificar si un archivo existe
int fileExists(const char* path) {
    DWORD attrs = GetFileAttributesA(path);
    return (attrs != INVALID_FILE_ATTRIBUTES && !(attrs & FILE_ATTRIBUTE_DIRECTORY));
}

// Eliminar directorio recursivamente
void removeDirectory(const char* path) {
    char cmd[MAX_CMD_LEN];
    snprintf(cmd, MAX_CMD_LEN, "rmdir /s /q \"%s\"", path);
    system(cmd);
}

// Crear directorio recursivamente
void createDirRecursive(const char* path) {
    char temp[MAX_PATH_LEN];
    strncpy(temp, path, MAX_PATH_LEN - 1);
    temp[MAX_PATH_LEN - 1] = '\0';
    
    for (char* p = temp + 1; *p; p++) {
        if (*p == '\\' || *p == '/') {
            *p = '\0';
            CreateDirectoryA(temp, NULL);
            *p = '\\';
        }
    }
    CreateDirectoryA(temp, NULL);
}

// Copiar directorio recursivamente con xcopy
int copyDirectory(const char* src, const char* dst) {
    char cmd[MAX_CMD_LEN];
    snprintf(cmd, MAX_CMD_LEN, "xcopy /E /I /Y \"%s\" \"%s\" >nul 2>nul", src, dst);
    return system(cmd) == 0;
}

// Crear archivo .extern con firma en BYTES
void createExternFile(const char* path, const char* url) {
    char externPath[MAX_PATH_LEN];
    snprintf(externPath, MAX_PATH_LEN, "%s\\firma.extern", path);
    
    time_t now = time(NULL);
    struct tm* tm_info = localtime(&now);
    char fecha[64];
    strftime(fecha, sizeof(fecha), "%Y-%m-%d %H:%M:%S", tm_info);
    
    char username[256];
    char computername[256];
    DWORD size = sizeof(username);
    GetUserNameA(username, &size);
    size = sizeof(computername);
    GetComputerNameA(computername, &size);
    
    // Crear firma en bytes (formato binario)
    unsigned char firma[] = {
        0x57, 0x49, 0x4E, 0x49,  // "WINI" magic
        0x01, 0x00, 0x00, 0x00,  // Version 1
        0x45, 0x58, 0x54, 0x45, 0x52, 0x4E, 0x00,  // "EXTERN" + null
    };
    
    // Crear contenido textual de la firma
    char contenido[2048];
    snprintf(contenido, sizeof(contenido),
        "WINILIBRARY\n"
        "SOURCE: %s\n"
        "INSTALLED: %s\n"
        "USER: %s\n"
        "COMPUTER: %s\n"
        "TYPE: EXTERNA\n"
        "VERSION: 1.0\n"
        "-----BEGIN FIRMA-----\n"
        "Esta libreria fue instalada desde internet\n"
        "-----END FIRMA-----\n",
        url, fecha, username, computername);
    
    // Escribir archivo en modo binario
    FILE* f = fopen(externPath, "wb");
    if (f) {
        fwrite(firma, 1, sizeof(firma), f);
        fwrite(contenido, 1, strlen(contenido), f);
        fclose(f);
    }
}

// Verificar si es libreria EXTERNA (tiene .extern)
int isExternLibrary(const char* path) {
    char externPath[MAX_PATH_LEN];
    snprintf(externPath, MAX_PATH_LEN, "%s\\firma.extern", path);
    return fileExists(externPath);
}

// Verificar si es libreria NATIVA (no tiene .extern)
int isNativeLibrary(const char* path) {
    return !isExternLibrary(path);
}

// Obtener directorio de librerias
void getLibreriasDir(char* buffer, int maxLen) {
    char cwd[MAX_PATH_LEN];
    if (_getcwd(cwd, MAX_PATH_LEN) == NULL) {
        strncpy(buffer, ".\\librerias", maxLen - 1);
        return;
    }
    snprintf(buffer, maxLen, "%s\\librerias", cwd);
}

// ========== FUNCIONES PRINCIPALES ==========

// Instalar libreria
int instalarLibreria(const char* url) {
    char repoName[MAX_PATH_LEN] = "";
    char cwd[MAX_PATH_LEN] = "";
    char libreriasPath[MAX_PATH_LEN] = "";
    char repoPath[MAX_PATH_LEN] = "";
    char destPath[MAX_PATH_LEN] = "";
    char cmd[MAX_CMD_LEN] = "";
    int error = 0;
    
    if (_getcwd(cwd, MAX_PATH_LEN) == NULL) {
        printRed("Error: No se pudo obtener el directorio actual\n");
        return 1;
    }
    
    // Verificar Git
    if (!gitInstalled()) {
        printRed("Error: Git no esta instalado\n");
        printf("   Instala Git desde: https://git-scm.com/downloads\n");
        return 1;
    }
    
    getRepoName(url, repoName, MAX_PATH_LEN);
    
    printf("\n");
    printBlue("+--------------------------------------------------------+\n");
    printBlue("|           INSTALADOR DE LIBRERIAS WINI                 |\n");
    printBlue("+--------------------------------------------------------+\n");
    printf("\n");
    printf("Repositorio: %s\n", repoName);
    printf("URL: %s\n", url);
    printf("\n");
    
    // Crear carpeta librerias
    snprintf(libreriasPath, MAX_PATH_LEN, "%s\\librerias", cwd);
    if (!directoryExists(libreriasPath)) {
        printYellow("Creando carpeta 'librerias'...\n");
        if (!CreateDirectoryA(libreriasPath, NULL)) {
            printRed("Error: No se pudo crear la carpeta 'librerias'\n");
            return 1;
        }
    }
    
    // Rutas
    snprintf(repoPath, MAX_PATH_LEN, "%s\\%s", cwd, repoName);
    snprintf(destPath, MAX_PATH_LEN, "%s\\%s", libreriasPath, repoName);
    
    // Verificar si ya esta instalado
    if (directoryExists(destPath)) {
        printYellow("La libreria ya esta instalada\n");
        printf("Ruta: %s\n", destPath);
        
        if (isExternLibrary(destPath)) {
            printCyan("  [EXTERNA - instalada desde internet]\n");
        } else {
            printGreen("  [NATIVA - libreria del sistema]\n");
        }
        return 0;
    }
    
    // Intentar clonar repositorio
    printf("Clonando repositorio...\n");
    snprintf(cmd, MAX_CMD_LEN, "git clone %s \"%s\" 2>nul", url, repoPath);
    
    int result = system(cmd);
    if (result != 0) {
        printRed("Error: No se pudo clonar el repositorio\n");
        printf("   Verifica que la URL sea correcta y que tengas acceso a Internet\n");
        printf("   URL: %s\n", url);
        return 1;
    }
    
    // Verificar que se clono correctamente
    if (!directoryExists(repoPath)) {
        printRed("Error: No se pudo clonar el repositorio\n");
        printRed("   La carpeta no se creo correctamente\n");
        return 1;
    }
    
    printGreen("Repositorio clonado correctamente\n");
    printf("\n");
    
    // Intentar instalar
    printf("Instalando libreria en: %s\n", destPath);
    
    // Si el destino existe, eliminarlo
    if (directoryExists(destPath)) {
        removeDirectory(destPath);
    }
    
    // Crear directorio destino
    createDirRecursive(destPath);
    
    // Copiar directorio
    if (!copyDirectory(repoPath, destPath)) {
        printRed("Error: No se pudo copiar la libreria\n");
        error = 1;
        goto limpiar;
    }
    
    // Crear .extern
    createExternFile(destPath, url);
    
    printGreen("Libreria instalada correctamente\n");
    printf("\n");
    printf("Libreria: %s", repoName);
    printCyan(" [EXTERNA - instalada desde internet]\n");
    printf("Ruta: %s\n", destPath);
    printf("\n");
    printf("Para usarla en Wini:\n");
    printf("  importar \"%s/%s.wn\" como %s\n", repoName, repoName, repoName);
    printf("\n");
    printGreen("Instalacion completada!\n");
    
    // Eliminar repositorio temporal
    if (directoryExists(repoPath)) {
        removeDirectory(repoPath);
    }
    
    return 0;

limpiar:
    // Limpiar en caso de error
    printRed("\nError durante la instalacion. Limpiando...\n");
    
    if (directoryExists(repoPath)) {
        removeDirectory(repoPath);
        printf("  Eliminado repositorio temporal: %s\n", repoPath);
    }
    
    if (directoryExists(destPath)) {
        removeDirectory(destPath);
        printf("  Eliminado instalacion incompleta: %s\n", destPath);
    }
    
    printRed("Instalacion cancelada. No se crearon archivos.\n");
    return 1;
}

// Listar librerias instaladas
int listarLibrerias() {
    char libreriasPath[MAX_PATH_LEN];
    getLibreriasDir(libreriasPath, MAX_PATH_LEN);
    
    if (!directoryExists(libreriasPath)) {
        printYellow("No hay librerias instaladas\n");
        return 0;
    }
    
    printf("\n");
    printBlue("+--------------------------------------------------------+\n");
    printBlue("|           LIBRERIAS INSTALADAS                         |\n");
    printBlue("+--------------------------------------------------------+\n");
    printf("\n");
    
    char searchPath[MAX_PATH_LEN];
    snprintf(searchPath, MAX_PATH_LEN, "%s\\*", libreriasPath);
    
    WIN32_FIND_DATAA findData;
    HANDLE hFind = FindFirstFileA(searchPath, &findData);
    
    if (hFind == INVALID_HANDLE_VALUE) {
        printYellow("No se encontraron librerias\n");
        return 0;
    }
    
    int count = 0;
    do {
        if (findData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
            if (strcmp(findData.cFileName, ".") != 0 && 
                strcmp(findData.cFileName, "..") != 0) {
                
                char libPath[MAX_PATH_LEN];
                snprintf(libPath, MAX_PATH_LEN, "%s\\%s", libreriasPath, findData.cFileName);
                
                printf("  %s", findData.cFileName);
                
                if (isExternLibrary(libPath)) {
                    printCyan(" [EXTERNA - instalada desde internet]\n");
                } else {
                    printGreen(" [NATIVA - libreria del sistema]\n");
                }
                
                count++;
            }
        }
    } while (FindNextFileA(hFind, &findData));
    
    FindClose(hFind);
    
    printf("\n");
    printf("Total: %d librerias\n", count);
    printf("\n");
    printGreen("+--------------------------------------------------------+\n");
    
    return 0;
}

// Desinstalar libreria
int desinstalarLibreria(const char* nombre) {
    char libreriasPath[MAX_PATH_LEN];
    char libPath[MAX_PATH_LEN];
    char msg[MAX_PATH_LEN + 100];
    
    getLibreriasDir(libreriasPath, MAX_PATH_LEN);
    snprintf(libPath, MAX_PATH_LEN, "%s\\%s", libreriasPath, nombre);
    
    if (!directoryExists(libPath)) {
        snprintf(msg, sizeof(msg), "Error: La libreria '%s' no esta instalada\n", nombre);
        printRed(msg);
        return 1;
    }
    
    if (isNativeLibrary(libPath)) {
        printRed("Error: No se puede desinstalar una libreria NATIVA del sistema\n");
        printf("  Solo se pueden desinstalar librerias EXTERNAS (instaladas desde internet)\n");
        return 1;
    }
    
    printf("\n");
    snprintf(msg, sizeof(msg), "Desinstalando libreria EXTERNA: %s\n", nombre);
    printYellow(msg);
    printf("Ruta: %s\n", libPath);
    printf("\n");
    
    removeDirectory(libPath);
    
    if (directoryExists(libPath)) {
        printRed("Error al desinstalar la libreria\n");
        return 1;
    }
    
    printGreen("Libreria desinstalada correctamente\n");
    return 0;
}

// Actualizar todas las librerias (SOLO las EXTERNAS)
int actualizarLibrerias() {
    char libreriasPath[MAX_PATH_LEN];
    getLibreriasDir(libreriasPath, MAX_PATH_LEN);
    
    if (!directoryExists(libreriasPath)) {
        printYellow("No hay librerias para actualizar\n");
        return 0;
    }
    
    printf("\n");
    printBlue("+--------------------------------------------------------+\n");
    printBlue("|           ACTUALIZANDO LIBRERIAS                       |\n");
    printBlue("+--------------------------------------------------------+\n");
    printf("\n");
    
    char searchPath[MAX_PATH_LEN];
    snprintf(searchPath, MAX_PATH_LEN, "%s\\*", libreriasPath);
    
    WIN32_FIND_DATAA findData;
    HANDLE hFind = FindFirstFileA(searchPath, &findData);
    
    if (hFind == INVALID_HANDLE_VALUE) {
        printYellow("No se encontraron librerias\n");
        return 0;
    }
    
    int count = 0;
    do {
        if (findData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
            if (strcmp(findData.cFileName, ".") != 0 && 
                strcmp(findData.cFileName, "..") != 0) {
                
                char libPath[MAX_PATH_LEN];
                snprintf(libPath, MAX_PATH_LEN, "%s\\%s", libreriasPath, findData.cFileName);
                char msg[MAX_PATH_LEN + 100];
                
                if (isExternLibrary(libPath)) {
                    snprintf(msg, sizeof(msg), "Actualizando: %s", findData.cFileName);
                    printf("%s", msg);
                    printCyan(" [EXTERNA]\n");
                    
                    char cmd[MAX_CMD_LEN];
                    snprintf(cmd, MAX_CMD_LEN, "cd /d \"%s\" && git pull", libPath);
                    
                    if (system(cmd) == 0) {
                        printGreen("  Actualizada correctamente\n");
                    } else {
                        printRed("  Error al actualizar\n");
                    }
                    count++;
                } else {
                    snprintf(msg, sizeof(msg), "Saltando: %s", findData.cFileName);
                    printf("%s", msg);
                    printGreen(" [NATIVA - no se puede actualizar]\n");
                }
            }
        }
    } while (FindNextFileA(hFind, &findData));
    
    FindClose(hFind);
    
    printf("\n");
    printf("Total actualizadas: %d\n", count);
    printGreen("Actualizacion completada!\n");
    
    return 0;
}

// Mostrar version
void mostrarVersion() {
    printf("\n");
    printBlue("+--------------------------------------------------------+\n");
    printBlue("|           WPACK - Gestor de librerias Wini             |\n");
    printBlue("+--------------------------------------------------------+\n");
    printf("\n");
    printf("Version: %s\n", VERSION);
    printf("Compilado: %s\n", __DATE__);
    printf("Potencia: C\n");
    printf("\n");
}

// Mostrar ayuda
void mostrarAyuda() {
    printf("\n");
    printBlue("+--------------------------------------------------------+\n");
    printBlue("|           WPACK - Gestor de librerias Wini             |\n");
    printBlue("+--------------------------------------------------------+\n");
    printf("\n");
    printf("USO:\n");
    printf("  wpack --instalar <url>              Instalar libreria EXTERNA desde Git\n");
    printf("  wpack --listar                      Listar librerias instaladas\n");
    printf("  wpack --desinstalar <nombre>        Desinstalar libreria EXTERNA\n");
    printf("  wpack --actualizar                  Actualizar librerias EXTERNAS\n");
    printf("  wpack --version                     Mostrar version\n");
    printf("  wpack --ayuda                       Mostrar esta ayuda\n");
    printf("\n");
    printf("TIPOS DE LIBRERIAS:\n");
    printf("  [EXTERNA] - Instalada desde internet (tiene firma.extern)\n");
    printf("  [NATIVA]  - Libreria del sistema (no se puede desinstalar/actualizar)\n");
    printf("\n");
    printf("EJEMPLOS:\n");
    printf("  wpack --instalar https://github.com/usuario/json.wn\n");
    printf("  wpack --listar\n");
    printf("  wpack --desinstalar json.wn\n");
    printf("  wpack --actualizar\n");
    printf("\n");
}

// ========== MAIN ==========

int main(int argc, char* argv[]) {
    if (argc < 2) {
        mostrarAyuda();
        return 0;
    }
    
    if (strcmp(argv[1], "--ayuda") == 0 || strcmp(argv[1], "-h") == 0) {
        mostrarAyuda();
        return 0;
    }
    
    if (strcmp(argv[1], "--version") == 0 || strcmp(argv[1], "-v") == 0) {
        mostrarVersion();
        return 0;
    }
    
    if (strcmp(argv[1], "--listar") == 0 || strcmp(argv[1], "-l") == 0) {
        return listarLibrerias();
    }
    
    if (strcmp(argv[1], "--actualizar") == 0 || strcmp(argv[1], "-u") == 0) {
        return actualizarLibrerias();
    }
    
    if (strcmp(argv[1], "--desinstalar") == 0 || strcmp(argv[1], "-r") == 0) {
        if (argc < 3) {
            printRed("Error: Especifica el nombre de la libreria\n");
            printf("Uso: wpack --desinstalar <nombre>\n");
            return 1;
        }
        return desinstalarLibreria(argv[2]);
    }
    
    if (strcmp(argv[1], "--instalar") == 0 || strcmp(argv[1], "-i") == 0) {
        if (argc < 3) {
            printRed("Error: Especifica la URL del repositorio\n");
            printf("Uso: wpack --instalar <url>\n");
            printf("Ejemplo: wpack --instalar https://github.com/JDEVELOPER76/wini.git\n");
            return 1;
        }
        return instalarLibreria(argv[2]);
    }
    
    // Si no es un comando reconocido, mostrar ayuda
    printRed("Error: Comando no reconocido\n");
    mostrarAyuda();
    return 1;
}