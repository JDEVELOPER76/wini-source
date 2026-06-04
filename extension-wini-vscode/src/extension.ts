import * as path from "path";
import * as fs from "fs";
import * as os from "os";
import { workspace, ExtensionContext, window, languages, CompletionItem, CompletionItemKind, SnippetString, MarkdownString, Hover, Position, TextDocument } from "vscode";

// ============================================================================
// PALABRAS CLAVE
// ============================================================================
const KEYWORDS: string[] = [
    "si", "sino", "entonces", "fin",
    "mientras", "para", "romper", "continuar",
    "funcion", "retornar", "clase",
    "importar", "paquete",
    "intentar", "capturar", "finalmente", "lanzar", "como",
    "verdadero", "falso", "nulo",
    "yo", "self"
];

// ============================================================================
// FUNCIONES NATIVAS
// ============================================================================
const NATIVE_FUNCTIONS: { name: string; signature: string; doc: string }[] = [
    { name: "escribir", signature: "escribir(valor)", doc: "Imprime un valor en la consola" },
    { name: "leer", signature: "leer(prompt?)", doc: "Lee una línea de entrada" },
    { name: "tipo", signature: "tipo(valor) -> cadena", doc: "Retorna el tipo del valor" },
    { name: "rango", signature: "rango(fin) | rango(inicio, fin) | rango(inicio, fin, paso)", doc: "Genera una lista de números" }
];

// ============================================================================
// SNIPPETS
// ============================================================================
const SNIPPETS: { [key: string]: { snippet: string; description: string } } = {
    "si": { snippet: "si ${1:condicion} entonces:\n\t${2:# codigo}\nfin", description: "Estructura condicional" },
    "sino": { snippet: "si ${1:condicion} entonces:\n\t${2:# verdadero}\nsino:\n\t${3:# falso}\nfin", description: "Condicional con sino" },
    "mientras": { snippet: "mientras ${1:condicion}:\n\t${2:# codigo}\nfin", description: "Bucle mientras" },
    "para": { snippet: "para ${1:variable} en ${2:lista}:\n\t${3:# codigo}\nfin", description: "Bucle para" },
    "funcion": { snippet: "funcion ${1:nombre}(${2:parametros}):\n\t${3:# codigo}\n\tretornar ${4:valor}\nfin", description: "Definir función" },
    "clase": { snippet: "clase ${1:Nombre}:\n\tfuncion constructor(${2:parametros}):\n\t\t${3:# codigo}\n\tfin\nfin", description: "Definir clase" },
    "importar": { snippet: 'importar("${1:modulo}")', description: "Importar módulo" },
    "paquete": { snippet: 'paquete("${1:nombre}")', description: "Registrar paquete" },
    "intentar": { snippet: "intentar:\n\t${1:# codigo}\ncapturar ${2:Tipo} como ${3:error}:\n\t${4:# manejo}\nfinalmente:\n\t${5:# limpieza}\nfin", description: "Manejo de excepciones" },
    "lanzar": { snippet: 'lanzar ${1:Tipo}("${2:mensaje}")', description: "Lanzar excepción" },
    "retornar": { snippet: "retornar ${1:valor}", description: "Retornar valor" },
    "romper": { snippet: "romper", description: "Salir del bucle" },
    "continuar": { snippet: "continuar", description: "Siguiente iteración" }
};

// ============================================================================
// DOCUMENTACIÓN
// ============================================================================
const HOVER_DOCS: { [key: string]: string } = {
    "escribir": "```wini\nescribir(valor)\n```\nImprime un valor en consola",
    "leer": "```wini\nleer()\nleer(\"Mensaje: \")\n```\nLee entrada del usuario",
    "tipo": "```wini\ntipo(valor) -> cadena\n```\nRetorna el tipo del valor",
    "rango": "```wini\nrango(5) -> [0,1,2,3,4]\nrango(2,5) -> [2,3,4]\n```",
    "si": "```wini\nsi condicion entonces:\n    # codigo\nfin\n```",
    "funcion": "```wini\nfuncion nombre(params):\n    # codigo\n    retornar valor\nfin\n```",
    "clase": "```wini\nclase Nombre:\n    funcion constructor(params):\n        yo.atributo = params\n    fin\nfin\n```",
    "importar": '```wini\nimportar("modulo")\n```\nImporta un módulo .wn o .wipy',
    "paquete": '```wini\npaquete("nombre")\n```\nRegistra una carpeta como paquete',
    "verdadero": "Valor booleano verdadero",
    "falso": "Valor booleano falso",
    "nulo": "Valor nulo",
    "yo": "Referencia a la instancia actual",
    "self": "Sinónimo de 'yo'"
};

// ============================================================================
// INTERFACES
// ============================================================================
interface ModuleExports {
    functions: string[];
    classes: string[];
    variables: string[];
}

// ============================================================================
// RUTAS DINÁMICAS
// ============================================================================
function getGlobalLibreriasPath(): string {
    // Obtener el nombre de usuario actual
    const username = os.userInfo().username;
    
    // Posibles rutas donde puede estar instalado Wini
    const possiblePaths = [
        path.join("C:", "Users", username, "AppData", "Local", "Programs", "wini", "librerias"),
        path.join("C:", "Users", username, "AppData", "Local", "wini", "librerias"),
        path.join(os.homedir(), "AppData", "Local", "Programs", "wini", "librerias"),
        path.join(os.homedir(), ".wini", "librerias"),
        // Ruta alternativa por si el usuario es diferente
        path.join("C:", "Users", "herob", "AppData", "Local", "Programs", "wini", "librerias"),
    ];
    
    for (const p of possiblePaths) {
        if (fs.existsSync(p)) {
            console.log(`[Wini] Librerías encontradas en: ${p}`);
            return p;
        }
    }
    
    console.log(`[Wini] No se encontraron librerías en las rutas buscadas`);
    return "";
}

// Cache
let globalPackages: string[] = [];
let moduleContentsCache: Map<string, ModuleExports> = new Map();
let globalLibreriasPath: string = "";

// ============================================================================
// ESCANEO GLOBAL
// ============================================================================
function scanGlobalPackages(): string[] {
    if (globalPackages.length > 0) return globalPackages;
    
    if (!globalLibreriasPath) {
        globalLibreriasPath = getGlobalLibreriasPath();
    }
    
    if (!globalLibreriasPath || !fs.existsSync(globalLibreriasPath)) {
        console.log(`[Wini] No existe: ${globalLibreriasPath}`);
        return [];
    }
    
    try {
        const items = fs.readdirSync(globalLibreriasPath);
        globalPackages = items.filter(item => {
            const itemPath = path.join(globalLibreriasPath, item);
            return fs.statSync(itemPath).isDirectory() && !item.startsWith('_') && !item.startsWith('.');
        });
        console.log(`[Wini] Paquetes globales: ${globalPackages.join(", ")}`);
    } catch (error) {
        console.error("[Wini] Error escaneando paquetes:", error);
    }
    
    return globalPackages;
}

// ============================================================================
// PARSER DE ARCHIVOS
// ============================================================================
function parseModuleFile(filePath: string): ModuleExports {
    const cacheKey = filePath;
    if (moduleContentsCache.has(cacheKey)) {
        return moduleContentsCache.get(cacheKey)!;
    }
    
    const result: ModuleExports = { functions: [], classes: [], variables: [] };
    
    if (!fs.existsSync(filePath)) {
        moduleContentsCache.set(cacheKey, result);
        return result;
    }
    
    try {
        const content = fs.readFileSync(filePath, 'utf-8');
        const lines = content.split('\n');
        
        for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('#')) continue;
            
            // Variables: nombre = valor
            const varMatch = trimmed.match(/^(\w+)\s*=/);
            if (varMatch && !varMatch[1].startsWith('_') && !KEYWORDS.includes(varMatch[1])) {
                if (!result.variables.includes(varMatch[1])) {
                    result.variables.push(varMatch[1]);
                }
            }
            
            // Funciones en .wn: funcion nombre(params):
            const funcMatchWN = trimmed.match(/^funcion\s+(\w+)\s*\(([^)]*)\)/);
            if (funcMatchWN && !funcMatchWN[1].startsWith('_')) {
                if (!result.functions.includes(funcMatchWN[1])) {
                    result.functions.push(funcMatchWN[1]);
                }
            }
            
            // Funciones en .wipy: def nombre(params):
            const funcMatchPy = trimmed.match(/^def\s+(\w+)\s*\(([^)]*)\)/);
            if (funcMatchPy && !funcMatchPy[1].startsWith('_')) {
                if (!result.functions.includes(funcMatchPy[1])) {
                    result.functions.push(funcMatchPy[1]);
                }
            }
            
            // Clases: clase Nombre
            const classMatch = trimmed.match(/^clase\s+(\w+)/);
            if (classMatch && !classMatch[1].startsWith('_')) {
                if (!result.classes.includes(classMatch[1])) {
                    result.classes.push(classMatch[1]);
                }
            }
        }
        
        console.log(`[Wini] Parseado: ${path.basename(filePath)} - Funciones: ${result.functions.length}, Clases: ${result.classes.length}`);
    } catch (error) {
        console.error(`[Wini] Error leyendo ${filePath}:`, error);
    }
    
    moduleContentsCache.set(cacheKey, result);
    return result;
}

// ============================================================================
// BUSCAR MÓDULOS LOCALES (archivos sueltos)
// ============================================================================
function findLocalModules(workspacePath: string): Map<string, string> {
    const modules = new Map<string, string>();
    
    if (!workspacePath || !fs.existsSync(workspacePath)) {
        return modules;
    }
    
    try {
        const files = fs.readdirSync(workspacePath);
        for (const file of files) {
            if (file.endsWith('.wn') || file.endsWith('.wipy')) {
                const moduleName = file.replace(/\.(wn|wipy)$/, '');
                modules.set(moduleName, path.join(workspacePath, file));
            }
        }
    } catch (error) {
        console.error("[Wini] Error buscando módulos locales:", error);
    }
    
    return modules;
}

// ============================================================================
// BUSCAR MÓDULOS DENTRO DE UN PAQUETE
// ============================================================================
function findModulesInPackage(packagePath: string): Map<string, string> {
    const modules = new Map<string, string>();
    
    if (!packagePath || !fs.existsSync(packagePath)) {
        return modules;
    }
    
    try {
        const files = fs.readdirSync(packagePath);
        for (const file of files) {
            if (file.endsWith('.wn') || file.endsWith('.wipy')) {
                const moduleName = file.replace(/\.(wn|wipy)$/, '');
                modules.set(moduleName, path.join(packagePath, file));
            }
        }
    } catch (error) {
        console.error(`[Wini] Error buscando módulos en ${packagePath}:`, error);
    }
    
    return modules;
}

// ============================================================================
// OBTENER RUTA DEL PAQUETE GLOBAL
// ============================================================================
function getGlobalPackagePath(packageName: string): string {
    if (!globalLibreriasPath) {
        globalLibreriasPath = getGlobalLibreriasPath();
    }
    return path.join(globalLibreriasPath, packageName);
}

// ============================================================================
// OBTENER RUTA DEL PAQUETE LOCAL
// ============================================================================
function getLocalPackagePath(workspacePath: string, packageName: string): string {
    const possiblePaths = [
        path.join(workspacePath, "librerias", packageName),
        path.join(workspacePath, packageName)
    ];
    
    for (const p of possiblePaths) {
        if (p && fs.existsSync(p) && fs.statSync(p).isDirectory()) {
            return p;
        }
    }
    
    return "";
}

// ============================================================================
// ANALIZAR DOCUMENTO ACTUAL
// ============================================================================
function analyzeDocument(text: string): { packages: string[], imports: string[] } {
    const packages: string[] = [];
    const imports: string[] = [];
    
    // paquete("nombre")
    const pkgRegex = /paquete\s*\(\s*["']([^"']+)["']\s*\)/g;
    let match: RegExpExecArray | null;
    while ((match = pkgRegex.exec(text)) !== null) {
        if (!packages.includes(match[1])) packages.push(match[1]);
    }
    
    // importar("nombre")
    const impRegex = /importar\s*\(\s*["']([^"']+)["']\s*\)/g;
    while ((match = impRegex.exec(text)) !== null) {
        if (!imports.includes(match[1])) imports.push(match[1]);
    }
    
    return { packages, imports };
}

// ============================================================================
// VARIABLES LOCALES DEL DOCUMENTO
// ============================================================================
function getLocalVariables(text: string): string[] {
    const variables: string[] = [];
    const lines = text.split('\n');
    
    for (const line of lines) {
        const trimmed = line.trim();
        const match = trimmed.match(/^(\w+)\s*=/);
        if (match && !match[1].startsWith('_') && !KEYWORDS.includes(match[1])) {
            if (!variables.includes(match[1])) variables.push(match[1]);
        }
    }
    
    return variables;
}

// Función mejorada para capturar funciones con sus parámetros completos
function getLocalFunctions(text: string): Map<string, { params: string, body: string, line: number }> {
    const functions = new Map<string, { params: string, body: string, line: number }>();
    const lines = text.split('\n');
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        // Capturar todo lo que está dentro de los paréntesis: funcion nombre(param1, param2, ...)
        const match = line.match(/^funcion\s+(\w+)\s*\(([^)]*)\)/);
        if (match && !match[1].startsWith('_')) {
            const funcName = match[1];
            const params = match[2].trim(); // Esto captura todo: "a, b, c" o "nombre, edad"
            functions.set(funcName, { params: params, body: "", line: i });
        }
    }
    
    return functions;
}

function getLocalClasses(text: string): string[] {
    const classes: string[] = [];
    const lines = text.split('\n');
    
    for (const line of lines) {
        const trimmed = line.trim();
        const match = trimmed.match(/^clase\s+(\w+)/);
        if (match && !match[1].startsWith('_')) {
            if (!classes.includes(match[1])) classes.push(match[1]);
        }
    }
    
    return classes;
}

// ============================================================================
// PROVEEDOR DE AUTOCOMPLETADO
// ============================================================================
const completionProvider = languages.registerCompletionItemProvider(
    "wini",
    {
        provideCompletionItems(document, position) {
            const text = document.getText();
            const line = document.lineAt(position.line).text;
            const linePrefix = line.substring(0, position.character);
            
            const workspacePath = workspace.workspaceFolders?.[0]?.uri.fsPath || path.dirname(document.uri.fsPath);
            
            const completions: CompletionItem[] = [];
            
            // ===== CASO 1: Dentro de paquete("...") =====
            const pkgInProgress = linePrefix.match(/paquete\s*\(\s*["']([^"']*)$/);
            if (pkgInProgress) {
                const prefix = pkgInProgress[1];
                
                // Paquetes globales
                const globalPkgs = scanGlobalPackages();
                for (const pkg of globalPkgs) {
                    if (pkg.startsWith(prefix)) {
                        const item = new CompletionItem(pkg, CompletionItemKind.Module);
                        item.detail = "Paquete global";
                        item.insertText = pkg;
                        completions.push(item);
                    }
                }
                
                // Paquetes locales (carpetas dentro de librerias/)
                const libreriasPath = path.join(workspacePath, "librerias");
                if (fs.existsSync(libreriasPath)) {
                    try {
                        const items = fs.readdirSync(libreriasPath);
                        for (const item of items) {
                            const itemPath = path.join(libreriasPath, item);
                            if (fs.statSync(itemPath).isDirectory() && item.startsWith(prefix)) {
                                const pkgItem = new CompletionItem(item, CompletionItemKind.Folder);
                                pkgItem.detail = "Paquete local";
                                pkgItem.insertText = item;
                                completions.push(pkgItem);
                            }
                        }
                    } catch (error) {
                        console.error("[Wini] Error leyendo librerias local:", error);
                    }
                }
                
                return completions;
            }
            
            // ===== CASO 2: Dentro de importar("...") =====
            const impInProgress = linePrefix.match(/importar\s*\(\s*["']([^"']*)$/);
            if (impInProgress) {
                const prefix = impInProgress[1];
                const { packages } = analyzeDocument(text);
                
                // Módulos locales (archivos sueltos)
                const localModules = findLocalModules(workspacePath);
                for (const [modName] of localModules) {
                    if (modName.startsWith(prefix)) {
                        const item = new CompletionItem(modName, CompletionItemKind.File);
                        item.detail = "Módulo local (archivo suelto)";
                        item.insertText = modName;
                        completions.push(item);
                    }
                }
                
                // Módulos dentro de paquetes registrados
                for (const pkg of packages) {
                    // Paquete global
                    const globalPkgPath = getGlobalPackagePath(pkg);
                    if (fs.existsSync(globalPkgPath)) {
                        const modules = findModulesInPackage(globalPkgPath);
                        for (const [modName] of modules) {
                            if (modName.startsWith(prefix)) {
                                const item = new CompletionItem(modName, CompletionItemKind.Module);
                                item.detail = `Módulo en paquete global '${pkg}'`;
                                item.insertText = modName;
                                completions.push(item);
                            }
                        }
                    }
                    
                    // Paquete local
                    const localPkgPath = getLocalPackagePath(workspacePath, pkg);
                    if (localPkgPath && fs.existsSync(localPkgPath)) {
                        const modules = findModulesInPackage(localPkgPath);
                        for (const [modName] of modules) {
                            if (modName.startsWith(prefix)) {
                                const item = new CompletionItem(modName, CompletionItemKind.Module);
                                item.detail = `Módulo en paquete local '${pkg}'`;
                                item.insertText = modName;
                                completions.push(item);
                            }
                        }
                    }
                }
                
                return completions;
            }
            
            // ===== CASO 3: Acceso a módulo: modulo. =====
            const dotInProgress = linePrefix.match(/(\w+)\.([\w_]*)$/);
            if (dotInProgress) {
                const moduleName = dotInProgress[1];
                const prefix = dotInProgress[2];
                const { packages, imports } = analyzeDocument(text);
                
                if (imports.includes(moduleName)) {
                    let found = false;
                    
                    // Buscar en módulos locales (archivos sueltos)
                    const localModules = findLocalModules(workspacePath);
                    if (localModules.has(moduleName)) {
                        const modulePath = localModules.get(moduleName)!;
                        const exports = parseModuleFile(modulePath);
                        
                        for (const func of exports.functions) {
                            if (func.startsWith(prefix)) {
                                const item = new CompletionItem(func, CompletionItemKind.Function);
                                item.detail = `Función de ${moduleName}`;
                                item.insertText = func;
                                completions.push(item);
                            }
                        }
                        
                        for (const cls of exports.classes) {
                            if (cls.startsWith(prefix)) {
                                const item = new CompletionItem(cls, CompletionItemKind.Class);
                                item.detail = `Clase de ${moduleName}`;
                                item.insertText = cls;
                                completions.push(item);
                            }
                        }
                        
                        for (const varName of exports.variables) {
                            if (varName.startsWith(prefix)) {
                                const item = new CompletionItem(varName, CompletionItemKind.Variable);
                                item.detail = `Variable de ${moduleName}`;
                                item.insertText = varName;
                                completions.push(item);
                            }
                        }
                        
                        found = true;
                    }
                    
                    // Buscar en paquetes
                    if (!found) {
                        for (const pkg of packages) {
                            // Paquete global
                            const globalPkgPath = getGlobalPackagePath(pkg);
                            const globalModules = findModulesInPackage(globalPkgPath);
                            if (globalModules.has(moduleName)) {
                                const modulePath = globalModules.get(moduleName)!;
                                const exports = parseModuleFile(modulePath);
                                
                                for (const func of exports.functions) {
                                    if (func.startsWith(prefix)) {
                                        const item = new CompletionItem(func, CompletionItemKind.Function);
                                        item.detail = `Función de ${moduleName}`;
                                        item.insertText = func;
                                        completions.push(item);
                                    }
                                }
                                
                                for (const cls of exports.classes) {
                                    if (cls.startsWith(prefix)) {
                                        const item = new CompletionItem(cls, CompletionItemKind.Class);
                                        item.detail = `Clase de ${moduleName}`;
                                        item.insertText = cls;
                                        completions.push(item);
                                    }
                                }
                                found = true;
                                break;
                            }
                            
                            // Paquete local
                            const localPkgPath = getLocalPackagePath(workspacePath, pkg);
                            const localModulesInPkg = findModulesInPackage(localPkgPath);
                            if (localModulesInPkg.has(moduleName)) {
                                const modulePath = localModulesInPkg.get(moduleName)!;
                                const exports = parseModuleFile(modulePath);
                                
                                for (const func of exports.functions) {
                                    if (func.startsWith(prefix)) {
                                        const item = new CompletionItem(func, CompletionItemKind.Function);
                                        item.detail = `Función de ${moduleName}`;
                                        item.insertText = func;
                                        completions.push(item);
                                    }
                                }
                                found = true;
                                break;
                            }
                        }
                    }
                }
                
                return completions;
            }
            
            // ===== CASO 4: Autocompletado normal =====
            const prefixMatch = linePrefix.match(/[\w_]+$/);
            const prefix = prefixMatch ? prefixMatch[0] : "";
            
            // Palabras clave con snippets
            for (const kw of KEYWORDS) {
                if (kw.startsWith(prefix)) {
                    const item = new CompletionItem(kw, CompletionItemKind.Keyword);
                    if (SNIPPETS[kw]) {
                        item.insertText = new SnippetString(SNIPPETS[kw].snippet);
                        item.detail = SNIPPETS[kw].description;
                    }
                    completions.push(item);
                }
            }
            
            // Funciones nativas
            for (const fn of NATIVE_FUNCTIONS) {
                if (fn.name.startsWith(prefix)) {
                    const item = new CompletionItem(fn.name, CompletionItemKind.Function);
                    item.detail = fn.signature;
                    item.documentation = new MarkdownString(fn.doc);
                    completions.push(item);
                }
            }
            
            // Variables locales
            const localVars = getLocalVariables(text);
            for (const varName of localVars) {
                if (varName.startsWith(prefix) && !completions.some(c => c.label === varName)) {
                    const item = new CompletionItem(varName, CompletionItemKind.Variable);
                    item.detail = "Variable local";
                    completions.push(item);
                }
            }
            
            // Funciones locales con sus parámetros completos
            const localFuncs = getLocalFunctions(text);
            for (const [funcName, info] of localFuncs) {
                if (funcName.startsWith(prefix) && !completions.some(c => c.label === funcName)) {
                    const item = new CompletionItem(funcName, CompletionItemKind.Function);
                    // Mostrar todos los parámetros: funcion nombre(a, b, c)
                    item.detail = `función ${funcName}(${info.params})`;
                    item.insertText = new SnippetString(`${funcName}(${info.params})`);
                    completions.push(item);
                }
            }
            
            // Clases locales
            const localClasses = getLocalClasses(text);
            for (const clsName of localClasses) {
                if (clsName.startsWith(prefix) && !completions.some(c => c.label === clsName)) {
                    const item = new CompletionItem(clsName, CompletionItemKind.Class);
                    item.detail = "Clase local";
                    completions.push(item);
                }
            }
            
            // Módulos locales (archivos sueltos para importar)
            const localModules = findLocalModules(workspacePath);
            for (const [modName] of localModules) {
                if (modName.startsWith(prefix) && !completions.some(c => c.label === modName)) {
                    const item = new CompletionItem(modName, CompletionItemKind.File);
                    item.detail = "Módulo local (archivo suelto)";
                    item.insertText = modName;
                    completions.push(item);
                }
            }
            
            return completions;
        }
    },
    ".", "(", "\"", "'", " "
);

// ============================================================================
// PROVEEDOR DE HOVER
// ============================================================================
const hoverProvider = languages.registerHoverProvider("wini", {
    provideHover(document: TextDocument, position: Position): Hover | null {
        const line = document.lineAt(position.line).text;
        const col = position.character;
        
        let start = col;
        while (start > 0 && line[start-1].match(/[\w_]/)) start--;
        let end = col;
        while (end < line.length && line[end].match(/[\w_]/)) end++;
        
        const word = line.substring(start, end);
        
        if (word && HOVER_DOCS[word]) {
            return new Hover(new MarkdownString(HOVER_DOCS[word]));
        }
        
        const text = document.getText();
        
        const localFuncs = getLocalFunctions(text);
        if (localFuncs.has(word)) {
            const info = localFuncs.get(word)!;
            return new Hover(new MarkdownString(`**Función local**\n\n\`${word}(${info.params})\``));
        }
        
        const localVars = getLocalVariables(text);
        if (localVars.includes(word)) {
            return new Hover(new MarkdownString(`**Variable local**\n\n\`${word}\``));
        }
        
        const localClasses = getLocalClasses(text);
        if (localClasses.includes(word)) {
            return new Hover(new MarkdownString(`**Clase local**\n\n\`clase ${word}\``));
        }
        
        return null;
    }
});

// ============================================================================
// ACTIVACIÓN
// ============================================================================
export function activate(context: ExtensionContext) {
    console.log("[Wini] Activando extensión...");
    
    // Inicializar ruta global
    globalLibreriasPath = getGlobalLibreriasPath();
    scanGlobalPackages();
    
    context.subscriptions.push(completionProvider);
    context.subscriptions.push(hoverProvider);
    
    window.showInformationMessage("Wini Language Support activado");
    console.log("[Wini] Extensión activada");
    console.log(`[Wini] Ruta de librerías: ${globalLibreriasPath}`);
}

export function deactivate() {
    console.log("[Wini] Extensión desactivada");
}