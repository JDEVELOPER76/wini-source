// time.cpp - Módulo para manipulación de tiempo en Wini
#include "winiapi.h"
#include <windows.h>
#include <string>
#include <vector>
#include <ctime>
#include <chrono>
#include <iomanip>
#include <sstream>
#include <algorithm>

#pragma comment(lib, "winmm.lib")

extern "C" {

// ===== DECLARACIONES DE FUNCIONES =====
WiniValor wini_time_now(WiniValor* args, int num_args);
WiniValor wini_time_sleep(WiniValor* args, int num_args);
WiniValor wini_time_format(WiniValor* args, int num_args);
WiniValor wini_time_parse(WiniValor* args, int num_args);
WiniValor wini_time_timestamp(WiniValor* args, int num_args);
WiniValor wini_time_add(WiniValor* args, int num_args);
WiniValor wini_time_diff(WiniValor* args, int num_args);
WiniValor wini_time_date(WiniValor* args, int num_args);
WiniValor wini_time_weekday(WiniValor* args, int num_args);
WiniValor wini_time_days_in_month(WiniValor* args, int num_args);
WiniValor wini_time_is_leap_year(WiniValor* args, int num_args);
WiniValor wini_time_strftime(WiniValor* args, int num_args);
WiniValor wini_time_strptime(WiniValor* args, int num_args);
WiniValor wini_time_timer(WiniValor* args, int num_args);
WiniValor wini_time_perf_counter(WiniValor* args, int num_args);

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

// Obtener tiempo como struct tm
struct tm get_current_tm() {
    time_t now = time(nullptr);
    struct tm tm_struct;
    localtime_s(&tm_struct, &now);
    return tm_struct;
}

// Formatear tiempo con formato personalizado
std::string format_time(const struct tm& tm_struct, const std::string& format) {
    char buffer[256];
    std::string fmt = format;
    
    // Reemplazar placeholders personalizados
    // %Y - año (4 dígitos)
    // %y - año (2 dígitos)
    // %m - mes (2 dígitos)
    // %d - día (2 dígitos)
    // %H - hora (24h, 2 dígitos)
    // %I - hora (12h, 2 dígitos)
    // %M - minuto (2 dígitos)
    // %S - segundo (2 dígitos)
    // %p - AM/PM
    // %A - día de la semana completo
    // %a - día de la semana abreviado
    // %B - mes completo
    // %b - mes abreviado
    // %w - día de la semana (0-6, domingo=0)
    // %j - día del año (1-366)
    // %U - semana del año (0-53)
    // %Z - zona horaria
    
    strftime(buffer, sizeof(buffer), fmt.c_str(), &tm_struct);
    return std::string(buffer);
}

// Parsear tiempo desde string
bool parse_time(const std::string& str, const std::string& format, struct tm& tm_struct) {
    std::string fmt = format;
    // Reemplazar placeholders personalizados por los de strftime
    // Nota: strptime no está disponible en Windows, usamos sscanf manual
    // Para simplificar, usamos un enfoque básico
    
    // Soporte básico para formatos comunes
    if (format == "%Y-%m-%d %H:%M:%S") {
        int year, month, day, hour, min, sec;
        if (sscanf_s(str.c_str(), "%d-%d-%d %d:%d:%d", &year, &month, &day, &hour, &min, &sec) == 6) {
            tm_struct.tm_year = year - 1900;
            tm_struct.tm_mon = month - 1;
            tm_struct.tm_mday = day;
            tm_struct.tm_hour = hour;
            tm_struct.tm_min = min;
            tm_struct.tm_sec = sec;
            return true;
        }
    } else if (format == "%Y-%m-%d") {
        int year, month, day;
        if (sscanf_s(str.c_str(), "%d-%d-%d", &year, &month, &day) == 3) {
            tm_struct.tm_year = year - 1900;
            tm_struct.tm_mon = month - 1;
            tm_struct.tm_mday = day;
            tm_struct.tm_hour = 0;
            tm_struct.tm_min = 0;
            tm_struct.tm_sec = 0;
            return true;
        }
    } else if (format == "%H:%M:%S") {
        int hour, min, sec;
        if (sscanf_s(str.c_str(), "%d:%d:%d", &hour, &min, &sec) == 3) {
            time_t now = time(nullptr);
            localtime_s(&tm_struct, &now);
            tm_struct.tm_hour = hour;
            tm_struct.tm_min = min;
            tm_struct.tm_sec = sec;
            return true;
        }
    } else if (format == "%d/%m/%Y") {
        int day, month, year;
        if (sscanf_s(str.c_str(), "%d/%d/%d", &day, &month, &year) == 3) {
            tm_struct.tm_mday = day;
            tm_struct.tm_mon = month - 1;
            tm_struct.tm_year = year - 1900;
            return true;
        }
    } else if (format == "%m/%d/%Y") {
        int month, day, year;
        if (sscanf_s(str.c_str(), "%d/%d/%d", &month, &day, &year) == 3) {
            tm_struct.tm_mon = month - 1;
            tm_struct.tm_mday = day;
            tm_struct.tm_year = year - 1900;
            return true;
        }
    }
    
    return false;
}

// Calcular timestamp desde struct tm
time_t tm_to_timestamp(const struct tm& tm_struct) {
    struct tm tm_copy = tm_struct;
    return mktime(&tm_copy);
}

// ===== INICIALIZACIÓN DEL MÓDULO =====
WINI_API bool wini_module_init(WiniContexto ctx, void* (*registrar)(const char* nombre, void* fn)) {
    g_contexto = ctx;
    
    // Registrar funciones
    registrar("ahora", (void*)wini_time_now);
    registrar("dormir", (void*)wini_time_sleep);
    registrar("formatear", (void*)wini_time_format);
    registrar("parsear", (void*)wini_time_parse);
    registrar("timestamp", (void*)wini_time_timestamp);
    registrar("sumar", (void*)wini_time_add);
    registrar("diferencia", (void*)wini_time_diff);
    registrar("fecha", (void*)wini_time_date);
    registrar("dia_semana", (void*)wini_time_weekday);
    registrar("dias_mes", (void*)wini_time_days_in_month);
    registrar("es_bisiesto", (void*)wini_time_is_leap_year);
    registrar("strftime", (void*)wini_time_strftime);
    registrar("strptime", (void*)wini_time_strptime);
    registrar("cronometro", (void*)wini_time_timer);
    registrar("contador_perf", (void*)wini_time_perf_counter);
    
    return true;
}

WINI_API void wini_module_cleanup(WiniContexto ctx) {
    g_contexto = nullptr;
}

// ===== IMPLEMENTACIÓN DE FUNCIONES =====

// Obtener tiempo actual como diccionario
WiniValor wini_time_now(WiniValor* args, int num_args) {
    struct tm tm_struct = get_current_tm();
    time_t timestamp = time(nullptr);
    
    // Crear diccionario con información de tiempo
    WiniValor claves[9];
    WiniValor valores[9];
    
    claves[0] = wini_crear_cadena("year");
    valores[0] = wini_crear_entero(tm_struct.tm_year + 1900);
    
    claves[1] = wini_crear_cadena("month");
    valores[1] = wini_crear_entero(tm_struct.tm_mon + 1);
    
    claves[2] = wini_crear_cadena("day");
    valores[2] = wini_crear_entero(tm_struct.tm_mday);
    
    claves[3] = wini_crear_cadena("hour");
    valores[3] = wini_crear_entero(tm_struct.tm_hour);
    
    claves[4] = wini_crear_cadena("minute");
    valores[4] = wini_crear_entero(tm_struct.tm_min);
    
    claves[5] = wini_crear_cadena("second");
    valores[5] = wini_crear_entero(tm_struct.tm_sec);
    
    claves[6] = wini_crear_cadena("weekday");
    valores[6] = wini_crear_entero(tm_struct.tm_wday);
    
    claves[7] = wini_crear_cadena("yearday");
    valores[7] = wini_crear_entero(tm_struct.tm_yday + 1);
    
    claves[8] = wini_crear_cadena("timestamp");
    valores[8] = wini_crear_entero((int64_t)timestamp);
    
    return wini_crear_diccionario(claves, valores, 9);
}

// Dormir por milisegundos
WiniValor wini_time_sleep(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_ENTERO) {
        return wini_crear_booleano(false);
    }
    
    DWORD milliseconds = (DWORD)args[0].entero;
    Sleep(milliseconds);
    return wini_crear_booleano(true);
}

// Formatear tiempo con formato personalizado
WiniValor wini_time_format(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_CADENA || !args[0].cadena) {
        return wini_crear_ninguno();
    }
    
    std::string format = args[0].cadena;
    struct tm tm_struct = get_current_tm();
    
    // Si se proporciona timestamp, usarlo
    if (num_args >= 2 && args[1].tipo == WINI_TIPO_ENTERO) {
        time_t timestamp = (time_t)args[1].entero;
        localtime_s(&tm_struct, &timestamp);
    }
    
    std::string resultado = format_time(tm_struct, format);
    return wini_crear_cadena(resultado.c_str());
}

// Parsear string a timestamp
WiniValor wini_time_parse(WiniValor* args, int num_args) {
    if (num_args < 2 || 
        args[0].tipo != WINI_TIPO_CADENA || !args[0].cadena ||
        args[1].tipo != WINI_TIPO_CADENA || !args[1].cadena) {
        return wini_crear_entero(0);
    }
    
    std::string str = args[0].cadena;
    std::string format = args[1].cadena;
    
    struct tm tm_struct = {0};
    if (parse_time(str, format, tm_struct)) {
        time_t timestamp = tm_to_timestamp(tm_struct);
        return wini_crear_entero((int64_t)timestamp);
    }
    
    return wini_crear_entero(0);
}

// Obtener timestamp actual
WiniValor wini_time_timestamp(WiniValor* args, int num_args) {
    time_t now = time(nullptr);
    return wini_crear_entero((int64_t)now);
}



// Sumar tiempo a una fecha
WiniValor wini_time_add(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_ENTERO) {
        return wini_crear_entero(0);
    }
    
    time_t timestamp = (time_t)args[0].entero;
    
    // Valores por defecto
    int segundos = 0, minutos = 0, horas = 0, dias = 0, meses = 0, años = 0;
    
    // Argumentos: timestamp, segundos, minutos, horas, dias, meses, años
    if (num_args >= 2 && args[1].tipo == WINI_TIPO_ENTERO) {
        segundos = (int)args[1].entero;
    }
    if (num_args >= 3 && args[2].tipo == WINI_TIPO_ENTERO) {
        minutos = (int)args[2].entero;
    }
    if (num_args >= 4 && args[3].tipo == WINI_TIPO_ENTERO) {
        horas = (int)args[3].entero;
    }
    if (num_args >= 5 && args[4].tipo == WINI_TIPO_ENTERO) {
        dias = (int)args[4].entero;
    }
    if (num_args >= 6 && args[5].tipo == WINI_TIPO_ENTERO) {
        meses = (int)args[5].entero;
    }
    if (num_args >= 7 && args[6].tipo == WINI_TIPO_ENTERO) {
        años = (int)args[6].entero;
    }
    
    struct tm tm_struct;
    localtime_s(&tm_struct, &timestamp);
    
    // Sumar años, meses, días, horas, minutos, segundos
    tm_struct.tm_year += años;
    tm_struct.tm_mon += meses;
    tm_struct.tm_mday += dias;
    tm_struct.tm_hour += horas;
    tm_struct.tm_min += minutos;
    tm_struct.tm_sec += segundos;
    
    // Convertir a timestamp (normaliza automáticamente)
    time_t new_timestamp = mktime(&tm_struct);
    
    return wini_crear_entero((int64_t)new_timestamp);
}

// Calcular diferencia entre dos timestamps
WiniValor wini_time_diff(WiniValor* args, int num_args) {
    if (num_args < 2 || 
        args[0].tipo != WINI_TIPO_ENTERO ||
        args[1].tipo != WINI_TIPO_ENTERO) {
        return wini_crear_entero(0);
    }
    
    time_t t1 = (time_t)args[0].entero;
    time_t t2 = (time_t)args[1].entero;
    
    double diff = difftime(t1, t2);
    return wini_crear_decimal(diff);
}

// Obtener fecha como string
WiniValor wini_time_date(WiniValor* args, int num_args) {
    struct tm tm_struct = get_current_tm();
    
    if (num_args >= 1 && args[0].tipo == WINI_TIPO_ENTERO) {
        time_t timestamp = (time_t)args[0].entero;
        localtime_s(&tm_struct, &timestamp);
    }
    
    char buffer[100];
    strftime(buffer, sizeof(buffer), "%Y-%m-%d", &tm_struct);
    return wini_crear_cadena(buffer);
}

// Obtener día de la semana (nombre)
WiniValor wini_time_weekday(WiniValor* args, int num_args) {
    struct tm tm_struct = get_current_tm();
    
    if (num_args >= 1 && args[0].tipo == WINI_TIPO_ENTERO) {
        time_t timestamp = (time_t)args[0].entero;
        localtime_s(&tm_struct, &timestamp);
    }
    
    const char* weekdays[] = {"Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"};
    return wini_crear_cadena(weekdays[tm_struct.tm_wday]);
}

// Días en un mes
WiniValor wini_time_days_in_month(WiniValor* args, int num_args) {
    if (num_args < 2 || 
        args[0].tipo != WINI_TIPO_ENTERO ||
        args[1].tipo != WINI_TIPO_ENTERO) {
        return wini_crear_entero(0);
    }
    
    int year = (int)args[0].entero;
    int month = (int)args[1].entero;
    
    if (month < 1 || month > 12) {
        return wini_crear_entero(0);
    }
    
    bool is_leap = (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
    int days_in_month[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    
    if (month == 2 && is_leap) {
        return wini_crear_entero(29);
    }
    return wini_crear_entero(days_in_month[month - 1]);
}

// Verificar si año es bisiesto
WiniValor wini_time_is_leap_year(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_ENTERO) {
        return wini_crear_booleano(false);
    }
    
    int year = (int)args[0].entero;
    bool is_leap = (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
    return wini_crear_booleano(is_leap);
}

// Strftime - formatear con formato personalizado
WiniValor wini_time_strftime(WiniValor* args, int num_args) {
    if (num_args < 1 || args[0].tipo != WINI_TIPO_CADENA || !args[0].cadena) {
        return wini_crear_ninguno();
    }
    
    std::string format = args[0].cadena;
    struct tm tm_struct = get_current_tm();
    
    if (num_args >= 2 && args[1].tipo == WINI_TIPO_ENTERO) {
        time_t timestamp = (time_t)args[1].entero;
        localtime_s(&tm_struct, &timestamp);
    }
    
    char buffer[512];
    strftime(buffer, sizeof(buffer), format.c_str(), &tm_struct);
    return wini_crear_cadena(buffer);
}

// Strptime - parsear string con formato (versión simplificada)
WiniValor wini_time_strptime(WiniValor* args, int num_args) {
    if (num_args < 2 || 
        args[0].tipo != WINI_TIPO_CADENA || !args[0].cadena ||
        args[1].tipo != WINI_TIPO_CADENA || !args[1].cadena) {
        return wini_crear_entero(0);
    }
    
    std::string str = args[0].cadena;
    std::string format = args[1].cadena;
    
    struct tm tm_struct = {0};
    if (parse_time(str, format, tm_struct)) {
        time_t timestamp = tm_to_timestamp(tm_struct);
        return wini_crear_entero((int64_t)timestamp);
    }
    
    return wini_crear_entero(0);
}

// Cronómetro (devuelve segundos transcurridos desde el inicio)
WiniValor wini_time_timer(WiniValor* args, int num_args) {
    static auto start = std::chrono::high_resolution_clock::now();
    static bool initialized = false;
    
    if (!initialized) {
        start = std::chrono::high_resolution_clock::now();
        initialized = true;
    }
    
    auto now = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(now - start);
    
    return wini_crear_decimal(duration.count() / 1000.0);
}

// Contador de rendimiento (alta precisión)
WiniValor wini_time_perf_counter(WiniValor* args, int num_args) {
    LARGE_INTEGER counter, frequency;
    
    if (!QueryPerformanceFrequency(&frequency)) {
        return wini_crear_decimal(0.0);
    }
    
    QueryPerformanceCounter(&counter);
    double seconds = (double)counter.QuadPart / (double)frequency.QuadPart;
    return wini_crear_decimal(seconds);
}

} // extern "C"