import Editor from "@monaco-editor/react";
import { useRef, useEffect, useState, useCallback } from "react";
import TerminalPanel from "./TerminalPanel";
import DialogModal from "./DialogModal";


// ───────────────────────── Helpers de archivos ─────────────────────────

const IGNORED_ENTRIES = new Set(["node_modules", ".git", ".DS_Store"]);

const EXT_COLORS = {
  wn: "#a225a7",
  js: "#F0DB4F",
  jsx: "#61DAFB",
  ts: "#3178C6",
  tsx: "#3178C6",
  json: "#CBCB41",
  css: "#42A5F5",
  html: "#E44D26",
  md: "#89b4fa",
  py: "#FFD43B",
  go: "#00ADD8",
  dll: "#6C7086",
  so: "#FF6B6B",
  dylib: "#A6E3A1",
};

const EXT_LANGUAGE = {
  wn: "wini",
  js: "javascript",
  jsx: "javascript",
  ts: "typescript",
  tsx: "typescript",
  json: "json",
  css: "css",
  html: "html",
  md: "markdown",
  py: "python",
  go: "go",
};

function getExt(name) {
  const i = name.lastIndexOf(".");
  return i === -1 ? "" : name.slice(i + 1).toLowerCase();
}

function getFileColor(name) {
  return EXT_COLORS[getExt(name)] || "#6C7086";
}

function getMonacoLanguage(name) {
  return EXT_LANGUAGE[getExt(name)] || "plaintext";
}

// Analiza el texto de un archivo .wn y extrae todas las declaraciones "importar",
// soportando ambas sintaxis del lenguaje:
//   importar modulo como mod        -> .wn local, sin comillas, "como" opcional
//   importar "carpeta/mod.dll" como mod -> librería externa, comillas + "como" obligatorio
function parseImportStatements(text) {
  const regex = /importar\s+(?:"([^"]+)"|'([^']+)'|([a-zA-Z_]\w*(?:[\\/][\w.-]+)*))(?:\s+como\s+([a-zA-Z_]\w*))?/g;
  const results = [];
  let m;
  while ((m = regex.exec(text)) !== null) {
    const importPath = m[1] ?? m[2] ?? m[3];
    if (!importPath) continue;
    const isQuoted = m[1] !== undefined || m[2] !== undefined;
    const moduleName = importPath.split(/[\\/]/).pop().replace(/\.[^.]+$/, "");
    const alias = m[4] || moduleName;
    results.push({ importPath, alias, isQuoted, moduleName });
  }
  return results;
}

// ───────────────────────── Iconos SVG ─────────────────────────

function ChevronIcon({ open }) {
  return (
    <svg width="10" height="10" viewBox="0 0 16 16" style={{
      transform: open ? "rotate(90deg)" : "rotate(0deg)",
      transition: "transform 0.1s ease",
      flexShrink: 0,
    }}>
      <path d="M5 3l6 5-6 5V3z" fill="#9399b2" />
    </svg>
  );
}

function FolderIcon({ open }) {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" style={{ flexShrink: 0 }}>
      <path
        d={open
          ? "M1.5 3.5h4l1.2 1.4H14a.5.5 0 01.5.5v.6H2.3l-.8 6.9-1-.1z"
          : "M1.5 3h4l1.2 1.4H14a.5.5 0 01.5.5v8.6a.5.5 0 01-.5.5h-12a.5.5 0 01-.5-.5V3z"}
        fill="#89b4fa"
      />
    </svg>
  );
}

function FileIcon({ name }) {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" style={{ flexShrink: 0 }}>
      <path d="M3 1.5h6.5L13 5v9.5a.5.5 0 01-.5.5h-9a.5.5 0 01-.5-.5v-12a.5.5 0 01.5-.5z"
        fill="#3a3a4a" stroke={getFileColor(name)} strokeWidth="1" />
      <path d="M9.5 1.5V5H13z" fill={getFileColor(name)} opacity="0.6" />
    </svg>
  );
}

function OpenFolderIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9399b2" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
      <line x1="12" y1="11" x2="12" y2="17" />
      <line x1="9" y1="14" x2="15" y2="14" />
    </svg>
  );
}

function EmptyDocIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#6C7086" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.5 }}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  );
}

function SaveIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function DiskIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
      <polyline points="17 21 17 13 7 13 7 21" />
      <polyline points="7 3 7 8 15 8" />
    </svg>
  );
}

function CloseXIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function DirtyDotIcon() {
  return (
    <svg width="8" height="8" viewBox="0 0 8 8">
      <circle cx="4" cy="4" r="3" fill="#CDD6F4" />
    </svg>
  );
}

function NewFileIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="12" y1="12" x2="12" y2="18" />
      <line x1="9" y1="15" x2="15" y2="15" />
    </svg>
  );
}

function NewFolderIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
      <line x1="12" y1="10" x2="12" y2="16" />
      <line x1="9" y1="13" x2="15" y2="13" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      <line x1="10" y1="11" x2="10" y2="17" />
      <line x1="14" y1="11" x2="14" y2="17" />
    </svg>
  );
}

function TerminalIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4 17 10 11 4 5" />
      <line x1="12" y1="19" x2="20" y2="19" />
    </svg>
  );
}

function RenameIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5z" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function PasteIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
    </svg>
  );
}

function ModulesIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2L2 7l10 5 10-5-10-5z" />
      <path d="M2 17l10 5 10-5" />
      <path d="M2 12l10 5 10-5" />
    </svg>
  );
}

function AppDataIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
      <line x1="12" y1="11" x2="12" y2="17" />
      <line x1="9" y1="14" x2="15" y2="14" />
    </svg>
  );
}

// ───────────────────────── Sistema de módulos y librerías ─────────────────────────

// Extensiones soportadas para módulos
const MODULE_EXTENSIONS = [".wn", ".go", ".dll", ".so", ".dylib"];
const EXPORT_EXTENSION = ".exp";
// Extensiones que son binarias: no se pueden decodificar como texto sin corromperlas.
// Se muestran en el árbol y se pueden ver como referencia, pero no se editan/guardan
// desde el editor de texto.
const BINARY_EXTENSIONS = new Set([
  "dll", "so", "dylib", "exe", "o", "obj", "bin", "node", "wasm", "class", "pyc", "a", "lib"
]);

function App() {
  const editorRef = useRef(null);
  const monacoRef = useRef(null);
  const disposablesRef = useRef([]);
  const setupDoneRef = useRef(false);
  const modelsRef = useRef(new Map());
  const binaryFilesRef = useRef(new Set());
  const fallbackInputRef = useRef(null);
  const saveActiveFileRef = useRef(() => {});

  // Refs "espejo" del estado: setupMonaco() se ejecuta una sola vez (setupDoneRef),
  // así que los proveedores de Monaco quedarían con clausuras desactualizadas si
  // leyeran el estado directamente. Estas refs se mantienen sincronizadas en cada
  // render para que la sugerencia de "importar" siempre vea las librerías/módulos
  // recién escaneados.
  const nodesByPathRef = useRef({});
  const activeFilePathRef = useRef(null);
  const libraryModulesRef = useRef({});
  const localModulesRef = useRef({});

  const supportsFSAccess = typeof window !== "undefined" && "showDirectoryPicker" in window;

  const [rootPath, setRootPath] = useState(null);
  const [nodesByPath, setNodesByPath] = useState({});
  const [expandedPaths, setExpandedPaths] = useState(() => new Set());
  const [openFiles, setOpenFiles] = useState([]);
  const [activeFilePath, setActiveFilePath] = useState(null);
  const [readOnlyMode, setReadOnlyMode] = useState(false);
  const [themeApplied, setThemeApplied] = useState(false);
  const [contextMenu, setContextMenu] = useState(null);
  const [selectedPath, setSelectedPath] = useState(null);
  const [dragOverPath, setDragOverPath] = useState(null);
  const draggedPathRef = useRef(null);
  const [terminalOpen, setTerminalOpen] = useState(false);
  const [terminalHeight, setTerminalHeight] = useState(260);
  const terminalResizeRef = useRef(null);
  const [dialog, setDialog] = useState(null);
  const [clipboard, setClipboard] = useState(null);
  
  // Estados para módulos y librerías
  const [localModules, setLocalModules] = useState({});
  const [libraryModules, setLibraryModules] = useState({});
  const [libraryPaths, setLibraryPaths] = useState([]);
  const [isScanningLibraries, setIsScanningLibraries] = useState(false);
  const [showModulesPanel, setShowModulesPanel] = useState(false);
  const [moduleExportsCache, setModuleExportsCache] = useState({});

  // Mantiene sincronizadas las refs que usa el proveedor de autocompletado de Monaco.
  useEffect(() => {
    nodesByPathRef.current = nodesByPath;
    activeFilePathRef.current = activeFilePath;
    libraryModulesRef.current = libraryModules;
    localModulesRef.current = localModules;
  });

  const showAlert = useCallback((message, title = "Aviso") => new Promise((resolve) => {
    setDialog({ type: "alert", title, message, resolve: () => { setDialog(null); resolve(); } });
  }), []);

  const showConfirm = useCallback((message, title = "Confirmar", options = {}) => new Promise((resolve) => {
    setDialog({
      type: "confirm", title, message, danger: options.danger, confirmLabel: options.confirmLabel,
      resolve: (val) => { setDialog(null); resolve(val); },
    });
  }), []);

  const showPrompt = useCallback((message, defaultValue = "", title = "Ingresar nombre") => new Promise((resolve) => {
    setDialog({
      type: "prompt", title, message, defaultValue,
      resolve: (val) => { setDialog(null); resolve(val); },
    });
  }), []);

  const palabrasClave = [
    "sino", "si", "funcion", "retornar",
    "importar", "paquete", "mientras", "para", "romper",
    "continuar", "intentar", "capturar",
    "finalmente", "lanzar", "como"
  ];

  const funcionesNativas = ["escribir", "leer", "tipo", "rango"];
  const constantes = ["verdadero", "falso", "nulo", "en", "o", "y"];

  const metodos = {
    lista: [
      "agregar", "eliminar", "eliminar_en", "eliminar_ultimo", "insertar",
      "extender", "contiene", "posicion", "contar", "longitud", "vacia",
      "invertir", "ordenar", "ordenar_desc", "primero", "ultimo", "limpiar",
      "copiar", "a_texto", "sumar", "maximo", "minimo"
    ],
    cadena: [
      "longitud", "mayuscula", "minuscula", "capitalizar", "titulo",
      "invertir", "contiene", "indice", "ultimo_indice", "empieza_con",
      "termina_con", "contar", "reemplazar", "unir", "dividir", "recortar",
      "recortar_izquierda", "recortar_derecha", "extraer", "repetir",
      "a_entero", "a_decimal", "a_lista", "es_numero", "es_digito",
      "es_alfabetico", "es_vacia", "es_palindromo", "es_mayuscula",
      "es_minuscula", "a_slug", "acortar"
    ],
    diccionario: [
      "obtener", "establecer", "eliminar", "contiene", "claves",
      "valores", "pares", "longitud", "vacio", "limpiar", "copiar",
      "unir", "sacar", "tiene_clave", "tiene_valor", "a_lista_claves",
      "a_lista_valores", "defecto", "incrementar"
    ]
  };

  // ─────────────────────── Sistema de Importación ───────────────────────

  // Resolver ruta de importación
  const resolveImportPath = useCallback((importPath, currentFilePath) => {
    const path = importPath.replace(/^["']|["']$/g, '').trim();
    
    // Si es una ruta relativa
    if (path.startsWith('./') || path.startsWith('../')) {
      const currentDir = currentFilePath.substring(0, currentFilePath.lastIndexOf('/'));
      const parts = currentDir.split('/');
      const importParts = path.split('/');
      
      for (const part of importParts) {
        if (part === '..') {
          parts.pop();
        } else if (part !== '.') {
          parts.push(part);
        }
      }
      return parts.join('/');
    }
    
    // Si es una ruta absoluta
    if (path.startsWith('/')) {
      return path.substring(1);
    }
    
    // Buscar en módulos locales
    const firstPart = path.split('/')[0];
    if (localModules[firstPart]) {
      return path;
    }
    
    // Buscar en librerías
    for (const libPath of libraryPaths) {
      const fullPath = `${libPath}/${path}`;
      if (nodesByPath[fullPath] || nodesByPath[`${fullPath}.wn`] || 
          MODULE_EXTENSIONS.some(ext => nodesByPath[`${fullPath}${ext}`])) {
        return fullPath;
      }
    }
    
    return path;
  }, [localModules, libraryPaths, nodesByPath]);

  // Encontrar archivo .exp
  const findExpFile = useCallback(async (modulePath) => {
    const dirPath = modulePath.substring(0, modulePath.lastIndexOf('/'));
    const dirNode = nodesByPath[dirPath];
    
    if (!dirNode || dirNode.kind !== 'directory') return null;
    
    for (const childPath of (dirNode.childrenPaths || [])) {
      const child = nodesByPath[childPath];
      if (child?.kind === 'file' && child.name.endsWith('.exp')) {
        return child;
      }
    }
    
    // Buscar en la raíz si no hay .exp en la carpeta
    if (rootPath) {
      const rootNode = nodesByPath[rootPath];
      if (rootNode) {
        for (const childPath of (rootNode.childrenPaths || [])) {
          const child = nodesByPath[childPath];
          if (child?.kind === 'file' && child.name.endsWith('.exp')) {
            return child;
          }
        }
      }
    }
    
    return null;
  }, [nodesByPath, rootPath]);

  // Analizar archivo .wn para extraer funciones y variables
  const analyzeWnFile = useCallback(async (filePath) => {
    const node = nodesByPath[filePath];
    if (!node || node.kind !== 'file') return { functions: [], variables: [] };
    
    try {
      const file = await node.handle.getFile();
      const text = await file.text();
      const lines = text.split('\n');
      const functions = [];
      const variables = [];
      
      lines.forEach((line, index) => {
        const trimmed = line.trim();
        
        // Buscar funciones: "funcion nombre("
        const funcMatch = trimmed.match(/^funcion\s+([a-zA-Z_]\w*)\s*\(/);
        if (funcMatch) {
          functions.push({
            name: funcMatch[1],
            line: index + 1,
            type: 'function'
          });
        }
        
        // Buscar variables: "var nombre = valor" o "nombre = valor"
        const varMatch = trimmed.match(/^(?:var\s+)?([a-zA-Z_]\w*)\s*[:=]\s*(.+)$/);
        if (varMatch) {
          variables.push({
            name: varMatch[1],
            value: varMatch[2].trim(),
            line: index + 1,
            type: 'variable'
          });
        }
      });
      
      return { functions, variables };
    } catch (error) {
      console.warn(`Error al analizar ${filePath}:`, error);
      return { functions: [], variables: [] };
    }
  }, [nodesByPath]);

  // Cargar exportaciones de un módulo
  const loadModuleExports = useCallback(async (modulePath, moduleName) => {
    // Verificar caché
    const cacheKey = `${modulePath}`;
    if (moduleExportsCache[cacheKey]) {
      return moduleExportsCache[cacheKey];
    }
    
    const exports = [];
    
    // 1. Buscar archivo .exp
    const expFile = await findExpFile(modulePath);
    if (expFile) {
      try {
        const file = await expFile.handle.getFile();
        const text = await file.text();
        const lines = text.split('\n');
        
        lines.forEach(line => {
          const trimmed = line.trim();
          // Buscar "func nombre"
          const funcMatch = trimmed.match(/^func\s+([a-zA-Z_]\w*)/);
          if (funcMatch) {
            exports.push({
              name: funcMatch[1],
              type: 'function',
              source: '.exp'
            });
          }
        });
      } catch (error) {
        console.warn(`Error al leer .exp para ${moduleName}:`, error);
      }
    }
    
    // 2. Si es un archivo .wn, analizarlo directamente
    const node = nodesByPath[modulePath];
    if (node?.kind === 'file' && node.name.endsWith('.wn')) {
      const analysis = await analyzeWnFile(modulePath);
      
      analysis.functions.forEach(fn => {
        if (!exports.some(e => e.name === fn.name && e.type === 'function')) {
          exports.push({
            name: fn.name,
            type: 'function',
            source: '.wn',
            line: fn.line
          });
        }
      });
      
      analysis.variables.forEach(v => {
        if (!exports.some(e => e.name === v.name)) {
          exports.push({
            name: v.name,
            type: 'variable',
            source: '.wn',
            value: v.value,
            line: v.line
          });
        }
      });
    }
    
    // Guardar en caché
    setModuleExportsCache(prev => ({ ...prev, [cacheKey]: exports }));
    
    return exports;
  }, [findExpFile, analyzeWnFile, nodesByPath, moduleExportsCache]);

  // Importar un módulo
  const importModule = useCallback(async (importPath, currentFilePath) => {
    const resolvedPath = resolveImportPath(importPath, currentFilePath);
    
    let moduleNode = null;
    let moduleName = '';
    
    // Verificar si es una ruta con extensión
    if (MODULE_EXTENSIONS.some(ext => resolvedPath.endsWith(ext))) {
      moduleNode = nodesByPath[resolvedPath];
      moduleName = resolvedPath.split('/').pop().replace(/\.[^.]+$/, '');
    } else {
      for (const ext of MODULE_EXTENSIONS) {
        const testPath = `${resolvedPath}${ext}`;
        if (nodesByPath[testPath]) {
          moduleNode = nodesByPath[testPath];
          moduleName = resolvedPath.split('/').pop();
          break;
        }
      }
    }
    
    if (!moduleNode) {
      console.warn(`Módulo no encontrado: ${importPath}`);
      return null;
    }
    
    const exports = await loadModuleExports(moduleNode.path, moduleName);
    
    return {
      name: moduleName,
      path: moduleNode.path,
      node: moduleNode,
      exports: exports
    };
  }, [resolveImportPath, nodesByPath, loadModuleExports]);

  // ─────────────────────── Funciones de módulos y librerías ───────────────────────

  // Escanear módulos locales
  const scanLocalModules = useCallback(async () => {
    if (!rootPath) return {};
    
    const modules = {};
    
    const scanDirectory = async (path) => {
      const node = nodesByPath[path];
      if (!node) return;
      
      if (node.kind === "directory") {
        if (node.name.toLowerCase() === "librerias") return;
        
        for (const childPath of (node.childrenPaths || [])) {
          await scanDirectory(childPath);
        }
      } else if (node.kind === "file") {
        const ext = getExt(node.name);
        if (ext === "wn") {
          const moduleName = node.name.replace(".wn", "");
          const analysis = await analyzeWnFile(node.path);
          modules[moduleName] = {
            path: node.path,
            name: node.name,
            extension: ".wn",
            isLocal: true,
            functions: analysis.functions,
            variables: analysis.variables,
            exports: [...analysis.functions, ...analysis.variables]
          };
        }
      }
    };
    
    await scanDirectory(rootPath);
    return modules;
  }, [rootPath, nodesByPath, analyzeWnFile]);

  // Escanear carpeta de librería
  // Analiza una sola carpeta de librería (busca su .exp opcional y sus módulos)
  // leyendo directamente desde el FileSystemDirectoryHandle, sin depender de
  // childrenPaths (que en el árbol lateral se cargan de forma perezosa al expandir).
  const scanOneLibraryDir = useCallback(async (dirHandle, dirPath, namePrefix) => {
    const modules = {};
    const exportFunctions = [];
    const moduleEntries = [];

    for await (const [name, entryHandle] of dirHandle.entries()) {
      if (IGNORED_ENTRIES.has(name) || entryHandle.kind !== "file") continue;
      const ext = `.${getExt(name)}`;
      if (ext === EXPORT_EXTENSION) {
        try {
          const file = await entryHandle.getFile();
          const text = await file.text();
          text.split("\n").forEach(line => {
            const trimmed = line.trim();
            const funcMatch = trimmed.match(/^func\s+([a-zA-Z_]\w*)/);
            if (funcMatch) {
              exportFunctions.push({ name: funcMatch[1], type: "function", source: ".exp" });
            }
          });
        } catch (error) {
          console.warn(`Error al leer .exp: ${name}`, error);
        }
      } else if (MODULE_EXTENSIONS.includes(ext)) {
        moduleEntries.push({ name, handle: entryHandle, ext });
      }
    }

    for (const { name, handle, ext } of moduleEntries) {
      const baseName = name.replace(ext, "");
      const exports = [...exportFunctions];

      if (ext === ".wn") {
        try {
          const file = await handle.getFile();
          const text = await file.text();
          text.split("\n").forEach((line, index) => {
            const trimmed = line.trim();
            const funcMatch = trimmed.match(/^funcion\s+([a-zA-Z_]\w*)\s*\(/);
            if (funcMatch && !exports.some(e => e.name === funcMatch[1])) {
              exports.push({ name: funcMatch[1], line: index + 1, type: "function", source: ".wn" });
            }
            const varMatch = trimmed.match(/^(?:var\s+)?([a-zA-Z_]\w*)\s*[:=]\s*(.+)$/);
            if (varMatch && !exports.some(e => e.name === varMatch[1])) {
              exports.push({ name: varMatch[1], value: varMatch[2].trim(), line: index + 1, type: "variable", source: ".wn" });
            }
          });
        } catch (error) {
          console.warn(`Error al analizar ${name}:`, error);
        }
      }

      const relativeName = namePrefix ? `${namePrefix}/${name}` : name;
      const key = namePrefix ? `${namePrefix}/${baseName}` : baseName;
      modules[key] = {
        path: `${dirPath}/${name}`,
        name: relativeName, // ruta relativa a "librerias", ej: "sistema/os.dll"
        extension: ext,
        exports,
      };
    }

    return modules;
  }, []);

  // Escanea una carpeta "librerias" completa: soporta tanto archivos sueltos
  // directamente dentro de ella, como el caso normal -> una subcarpeta por
  // cada librería (ej: librerias/sistema/os.dll + librerias/sistema/os.exp).
  const scanLibraryFolder = useCallback(async (libraryPath) => {
    const libraryNode = nodesByPath[libraryPath];
    if (!libraryNode || libraryNode.kind !== "directory" || !libraryNode.handle) return null;

    const modules = {};

    // 1) Archivos sueltos directamente dentro de "librerias" (compatibilidad hacia atrás)
    Object.assign(modules, await scanOneLibraryDir(libraryNode.handle, libraryPath, ""));

    // 2) Subcarpetas: cada una es una librería propia
    for await (const [name, entryHandle] of libraryNode.handle.entries()) {
      if (IGNORED_ENTRIES.has(name) || entryHandle.kind !== "directory") continue;
      const subDirPath = `${libraryPath}/${name}`;
      Object.assign(modules, await scanOneLibraryDir(entryHandle, subDirPath, name));
    }

    return modules;
  }, [nodesByPath, scanOneLibraryDir]);

  // Encontrar carpetas "libreria"
  const findLibraryFolders = useCallback(async () => {
    if (!rootPath) return [];
    
    const folders = [];
    const rootNode = nodesByPath[rootPath];
    if (!rootNode) return folders;
    
    for (const childPath of (rootNode.childrenPaths || [])) {
      const child = nodesByPath[childPath];
      if (child?.kind === "directory" && child.name.toLowerCase() === "librerias") {
        folders.push(childPath);
      }
    }
    
    return folders;
  }, [rootPath, nodesByPath]);

  // Escanear todos los módulos
  const scanAllModules = useCallback(async () => {
    if (!rootPath || isScanningLibraries) return;
    
    setIsScanningLibraries(true);
    
    try {
      const local = await scanLocalModules();
      setLocalModules(local);
      
      const libraries = await findLibraryFolders();
      setLibraryPaths(libraries);
      
      const allLibraryModules = {};
      for (const libPath of libraries) {
        const modules = await scanLibraryFolder(libPath);
        if (modules) {
          Object.assign(allLibraryModules, modules);
        }
      }
      setLibraryModules(allLibraryModules);
      
    } catch (error) {
      console.error("Error al escanear módulos:", error);
    } finally {
      setIsScanningLibraries(false);
    }
  }, [rootPath, scanLocalModules, findLibraryFolders, scanLibraryFolder, isScanningLibraries]);

  // Buscar librerías en AppData
  const findLibraryInAppData = useCallback(async () => {
    if (!supportsFSAccess) {
      await showAlert("Tu navegador no soporta acceso completo al sistema de archivos.\nUsa Chrome o Edge para esta función.");
      return;
    }
    
    try {
      const handle = await window.showDirectoryPicker({
        mode: "readwrite",
      });
      
      let libraryFound = false;
      for await (const [name, entry] of handle.entries()) {
        if (name.toLowerCase() === "librerias" && entry.kind === "directory") {
          libraryFound = true;
          
          const libPath = `librerias_${Date.now()}`;
          
          setNodesByPath(prev => ({
            ...prev,
            [libPath]: {
              name: `📚 ${handle.name}`,
              kind: "directory",
              path: libPath,
              handle: entry,
              parentPath: rootPath,
              childrenPaths: [],
            }
          }));
          
          setLibraryPaths(prev => [...prev, libPath]);
          
          // Un solo nivel para la barra lateral: las subcarpetas (cada librería,
          // ej. "sistema") quedan con childrenPaths: null y se cargan solas al
          // expandirlas, igual que el resto del árbol de archivos.
          const children = [];
          for await (const [childName, childHandle] of entry.entries()) {
            if (IGNORED_ENTRIES.has(childName)) continue;
            const childPath = `${libPath}/${childName}`;
            children.push(childPath);
            setNodesByPath(prev => ({
              ...prev,
              [childPath]: {
                name: childName,
                kind: childHandle.kind,
                path: childPath,
                handle: childHandle,
                parentPath: libPath,
                childrenPaths: childHandle.kind === "directory" ? null : undefined,
              }
            }));
          }
          setNodesByPath(prev => ({
            ...prev,
            [libPath]: { ...prev[libPath], childrenPaths: children }
          }));
          
          // El escaneo de módulos lee directamente desde los handles del sistema
          // de archivos (recursivo, 2 niveles), así que no depende de que el
          // usuario haya expandido las subcarpetas en la barra lateral.
          const modules = await scanLibraryFolder(libPath);
          if (modules) {
            setLibraryModules(prev => ({ ...prev, ...modules }));
          }
          
          setExpandedPaths(prev => new Set(prev).add(libPath));
          
          await showAlert(`Librería encontrada en: ${handle.name}\nSe cargaron ${Object.keys(modules || {}).length} módulos.`);
          break;
        }
      }
      
      if (!libraryFound) {
        await showAlert("No se encontró una carpeta 'librerias' en la ubicación seleccionada.");
      }
      
    } catch (error) {
      if (error?.name !== "AbortError") {
        console.error("Error al buscar librería:", error);
        await showAlert("No se pudo acceder a la carpeta seleccionada.");
      }
    }
  }, [supportsFSAccess, rootPath, scanLibraryFolder, showAlert]);

  // Escanear módulos al abrir carpeta
  useEffect(() => {
    if (rootPath) {
      scanAllModules();
    }
  }, [rootPath, scanAllModules]);

  // ─────────────────────── Tema y Monaco ───────────────────────

  const applyTheme = useCallback(() => {
    if (monacoRef.current) {
      try {
        monacoRef.current.editor.setTheme("customTheme");
        setThemeApplied(true);
        return true;
      } catch (e) {
        console.warn("Error applying theme:", e);
        return false;
      }
    }
    return false;
  }, []);

  const setupMonaco = () => {
    const monaco = window.monaco;

    monaco.languages.register({ id: "wini" });

    monaco.languages.setMonarchTokensProvider("wini", {
      keywords: palabrasClave,
      nativeFunctions: funcionesNativas,
      constants: constantes,
      operators: [
        "+", "-", "*", "/", "%", "=", "==", "!=", "<", ">",
        "<=", ">=", "&&", "||", "!", "++", "--", ":=", "->"
      ],

      tokenizer: {
        root: [
          [/#.*$/, "comment"],
          [/"([^"\\]|\\.)*$/, "string"],
          [/'([^'\\]|\\.)*$/, "string"],
          [/"/, "string", "@string_double"],
          [/'/, "string", "@string_single"],
          [/`/, "string", "@string_backtick"],
          [/\b\d+\.\d+\b/, "number"],
          [/\b\d+\b/, "number"],
          [/\b0x[0-9a-fA-F]+\b/, "number"],
          [/\b0b[01]+\b/, "number"],
          [new RegExp(`\\b(?:${palabrasClave.join('|')})\\b`), "keyword"],
          [new RegExp(`\\b(?:${funcionesNativas.join('|')})\\b(?=\\s*\\()`), "native-function"],
          [new RegExp(`\\b(?:${constantes.join('|')})\\b`), "constant"],
          [/\b\w+(?=\s*\()/, "function"],
          [/\b[a-zA-Z_]\w*\b/, "variable"],
          [/[+\-*/%=!<>]=?/, "operator"],
          [/[&|]&&?/, "operator"],
          [/[:]=?/, "operator"],
          [/[~^]/, "operator"],
          [/[{}()\[\]]/, "delimiter"],
          [/[;,.]/, "delimiter"],
        ],
        string_double: [
          [/[^"\\]+/, "string"],
          [/\\./, "string"],
          [/"/, "string", "@pop"],
        ],
        string_single: [
          [/[^'\\]+/, "string"],
          [/\\./, "string"],
          [/'/, "string", "@pop"],
        ],
        string_backtick: [
          [/[^`]+/, "string"],
          [/`/, "string", "@pop"],
        ],
      },
    });

    monaco.editor.defineTheme("customTheme", {
      base: "vs-dark",
      inherit: true,
      rules: [
        { token: "keyword", foreground: "#a225a7" },
        { token: "native-function", foreground: "#d1e428" },
        { token: "function", foreground: "#d1e428" },
        { token: "string", foreground: "#51CF66" },
        { token: "comment", foreground: "#2f8136" },
        { token: "number", foreground: "#FFA94D" },
        { token: "variable", foreground: "#229094" },
        { token: "operator", foreground: "#FF6B6B" },
        { token: "constant", foreground: "#2a27cc" },
        { token: "delimiter", foreground: "#D4BFFF" },
      ],
      colors: {
        "editor.background": "#1E1E2E",
        "editor.foreground": "#CDD6F4",
        "editor.lineHighlightBackground": "#313244",
        "editor.selectionBackground": "#45475A",
        "editorCursor.foreground": "#F5E0DC",
        "editorIndentGuide.background": "#313244",
        "editorLineNumber.foreground": "#6C7086",
        "editorLineNumber.activeForeground": "#CDD6F4",
      }
    });

    // Proveedor de símbolos
    const symbolProviderDisposable = monaco.languages.registerDocumentSymbolProvider("wini", {
      provideDocumentSymbols: (model) => {
        const symbols = [];
        const lines = model.getLinesContent();

        lines.forEach((line, index) => {
          const trimmed = line.trim();

          const varMatch = trimmed.match(/^([a-zA-Z_]\w*)\s*[:=]/);
          if (varMatch) {
            symbols.push({
              name: varMatch[1],
              kind: monaco.languages.SymbolKind.Variable,
              range: {
                startLineNumber: index + 1,
                endLineNumber: index + 1,
                startColumn: trimmed.indexOf(varMatch[1]) + 1,
                endColumn: trimmed.indexOf(varMatch[1]) + varMatch[1].length + 1
              },
              selectionRange: {
                startLineNumber: index + 1,
                endLineNumber: index + 1,
                startColumn: trimmed.indexOf(varMatch[1]) + 1,
                endColumn: trimmed.indexOf(varMatch[1]) + varMatch[1].length + 1
              }
            });
          }

          const funcMatch = trimmed.match(/^funcion\s+([a-zA-Z_]\w*)\s*\(/);
          if (funcMatch) {
            symbols.push({
              name: funcMatch[1],
              kind: monaco.languages.SymbolKind.Function,
              range: {
                startLineNumber: index + 1,
                endLineNumber: index + 1,
                startColumn: trimmed.indexOf(funcMatch[1]) + 1,
                endColumn: trimmed.indexOf(funcMatch[1]) + funcMatch[1].length + 1
              },
              selectionRange: {
                startLineNumber: index + 1,
                endLineNumber: index + 1,
                startColumn: trimmed.indexOf(funcMatch[1]) + 1,
                endColumn: trimmed.indexOf(funcMatch[1]) + funcMatch[1].length + 1
              }
            });
          }
        });

        return symbols;
      }
    });

    const detectarTipoVariable = (model, varName) => {
      const lines = model.getLinesContent();

      for (let line of lines) {
        const match = line.match(new RegExp(`^\\s*${varName}\\s*[:=]\\s*(.+)$`));
        if (match) {
          const valor = match[1].trim();

          if (valor.startsWith('"') || valor.startsWith("'") || valor.startsWith("`")) {
            return "cadena";
          } else if (valor.startsWith('[')) {
            return "lista";
          } else if (valor.startsWith('{')) {
            return "diccionario";
          } else if (valor === "verdadero" || valor === "falso" || valor === "nulo") {
            return "constante";
          } else if (/^\d+$/.test(valor) || /^\d+\.\d+$/.test(valor)) {
            return "numero";
          }
        }
      }
      return null;
    };

    // Proveedor de autocompletado principal
    const completionProviderDisposable = monaco.languages.registerCompletionItemProvider("wini", {
      triggerCharacters: [
        "a","b","c","d","e","f","g","h","i","j","k","l","m",
        "n","o","p","q","r","s","t","u","v","w","x","y","z",
        "A","B","C","D","E","F","G","H","I","J","K","L","M",
        "N","O","P","Q","R","S","T","U","V","W","X","Y","Z",
        "_", ".", '"', "'", "/"
      ],

      provideCompletionItems: (model, position, context) => {
        const lineContent = model.getLineContent(position.lineNumber);
        const textBeforeCursor = lineContent.substring(0, position.column - 1);
        const fullText = model.getValue();

        const wordMatch = textBeforeCursor.match(/[a-zA-Z_]\w*$/);
        const currentWord = wordMatch ? wordMatch[0] : "";

        const dotMatch = textBeforeCursor.match(/([a-zA-Z_]\w*)\.$/);
        const isAfterDot = !!dotMatch;
        const variableName = dotMatch ? dotMatch[1] : null;

        // IMPORTACIÓN: Buscar patrones de importación.
        // El lenguaje soporta dos sintaxis:
        //   importar modulo como mod              -> módulo local .wn, sin comillas, "como" opcional
        //   importar "carpeta/modulo.dll" como mod -> librería externa, comillas + "como" obligatorio
        const currentLibraryModules = libraryModulesRef.current || {};
        const currentLocalModules = localModulesRef.current || {};

        // 1) Está escribiendo el alias justo después de "como"
        const aliasQuotedMatch = textBeforeCursor.match(/importar\s+["']([^"']+)["']\s+como\s+([a-zA-Z_]\w*)?$/);
        const aliasUnquotedMatch = !aliasQuotedMatch
          ? textBeforeCursor.match(/importar\s+([a-zA-Z_]\w*)\s+como\s+([a-zA-Z_]\w*)?$/)
          : null;
        const aliasMatch = aliasQuotedMatch || aliasUnquotedMatch;

        if (aliasMatch) {
          const importPath = aliasMatch[1];
          const partialAlias = aliasMatch[2] || "";
          const defaultAlias = importPath.split(/[\\/]/).pop().replace(/\.[^.]+$/, "");
          const suggestions = [];
          if (defaultAlias && defaultAlias.toLowerCase().includes(partialAlias.toLowerCase())) {
            suggestions.push({
              label: defaultAlias,
              kind: monaco.languages.CompletionItemKind.Variable,
              insertText: defaultAlias,
              detail: "Alias sugerido",
              documentation: { value: `Nombre del módulo importado: **${importPath}**` },
              sortText: "0" + defaultAlias,
              range: {
                startLineNumber: position.lineNumber,
                endLineNumber: position.lineNumber,
                startColumn: position.column - partialAlias.length,
                endColumn: position.column,
              }
            });
          }
          return { suggestions };
        }

        // 2) Está escribiendo la ruta entre comillas -> librerías externas (carpeta "librerias")
        const importQuotedPathMatch = textBeforeCursor.match(/importar\s+["']([^"']*)$/);
        // 3) Está escribiendo el nombre sin comillas -> módulos locales .wn
        const importBarePathMatch = !importQuotedPathMatch
          ? textBeforeCursor.match(/importar\s+([a-zA-Z_]\w*)$/)
          : null;

        if (importQuotedPathMatch || importBarePathMatch) {
          const suggestions = [];
          const isQuoted = !!importQuotedPathMatch;
          const currentPath = isQuoted ? importQuotedPathMatch[1] : importBarePathMatch[1];

          if (isQuoted) {
            // Sugerir módulos de librería (requieren comillas + "como")
            Object.keys(currentLibraryModules).forEach(name => {
              const mod = currentLibraryModules[name];
              if (!mod) return;
              if (name.toLowerCase().includes(currentPath.toLowerCase()) ||
                  mod.name.toLowerCase().includes(currentPath.toLowerCase()) || !currentPath) {
                suggestions.push({
                  label: mod.name,
                  kind: monaco.languages.CompletionItemKind.Module,
                  insertText: mod.name,
                  detail: `📚 Librería (${mod.extension})`,
                  documentation: {
                    value: `Módulo: **${name}**\n` +
                           `Tipo: ${mod.extension}\n` +
                           `Uso: importar "${mod.name}" como <alias>\n` +
                           `Funciones: ${mod.exports.filter(e => e.type === 'function').map(e => e.name).join(", ") || "Ninguna"}`
                  },
                  sortText: "1" + name,
                  range: {
                    startLineNumber: position.lineNumber,
                    endLineNumber: position.lineNumber,
                    startColumn: position.column - currentPath.length,
                    endColumn: position.column,
                  }
                });
              }
            });
          } else {
            // Sugerir módulos locales .wn (sin comillas, "como" opcional)
            Object.keys(currentLocalModules).forEach(name => {
              const mod = currentLocalModules[name];
              if (!mod) return;
              if (name.toLowerCase().includes(currentPath.toLowerCase()) || !currentPath) {
                suggestions.push({
                  label: name,
                  kind: monaco.languages.CompletionItemKind.Module,
                  insertText: name,
                  detail: `📁 Local (.wn)`,
                  documentation: {
                    value: `Módulo: **${name}**\n` +
                           `Uso: importar ${name}  (o  importar ${name} como <alias>)\n` +
                           `Funciones: ${mod.functions.map(f => f.name).join(", ") || "Ninguna"}\n` +
                           `Variables: ${mod.variables.map(v => v.name).join(", ") || "Ninguna"}`
                  },
                  sortText: "0" + name,
                  range: {
                    startLineNumber: position.lineNumber,
                    endLineNumber: position.lineNumber,
                    startColumn: position.column - currentPath.length,
                    endColumn: position.column,
                  }
                });
              }
            });
          }

          return { suggestions };
        }

        // Autocompletado después de un punto
        if (isAfterDot && variableName) {
          const suggestions = [];
          
          // Verificar tipos nativos
          const tipo = detectarTipoVariable(model, variableName);
          if (tipo && metodos[tipo]) {
            metodos[tipo].forEach(metodo => {
              suggestions.push({
                label: metodo,
                kind: monaco.languages.CompletionItemKind.Method,
                insertText: `${metodo}()`,
                detail: `Método de ${tipo}`,
                documentation: { value: `Método para **${tipo}**: ${metodo}` },
                sortText: "0" + metodo,
                range: {
                  startLineNumber: position.lineNumber,
                  endLineNumber: position.lineNumber,
                  startColumn: position.column,
                  endColumn: position.column,
                }
              });
            });
          }
          
          // Buscar en módulos importados (soporta "importar mod" y "importar \"ruta\" como mod")
          const importedStatements = parseImportStatements(fullText);
          if (importedStatements.length) {
            importedStatements.forEach(({ moduleName, alias }) => {
              if (alias === variableName) {
                // Buscar en librerías
                if (currentLibraryModules[moduleName]) {
                  const mod = currentLibraryModules[moduleName];
                  mod.exports.forEach(exp => {
                    suggestions.push({
                      label: exp.name,
                      kind: exp.type === 'function' ? 
                        monaco.languages.CompletionItemKind.Function : 
                        monaco.languages.CompletionItemKind.Variable,
                      insertText: exp.name,
                      detail: `Exportado de ${moduleName}`,
                      documentation: { 
                        value: `${exp.type === 'function' ? 'Función' : 'Variable'} exportada de **${moduleName}**\n` +
                               `Fuente: ${exp.source}`
                      },
                      sortText: "1" + exp.name,
                      range: {
                        startLineNumber: position.lineNumber,
                        endLineNumber: position.lineNumber,
                        startColumn: position.column,
                        endColumn: position.column,
                      }
                    });
                  });
                }
                
                // Buscar en locales
                if (currentLocalModules[moduleName]) {
                  const mod = currentLocalModules[moduleName];
                  mod.exports.forEach(exp => {
                    suggestions.push({
                      label: exp.name,
                      kind: exp.type === 'function' ?
                        monaco.languages.CompletionItemKind.Function :
                        monaco.languages.CompletionItemKind.Variable,
                      insertText: exp.name,
                      detail: `Exportado de ${moduleName}`,
                      documentation: {
                        value: `${exp.type === 'function' ? 'Función' : 'Variable'} exportada de **${moduleName}**\n` +
                               `Línea: ${exp.line}`
                      },
                      sortText: "0" + exp.name,
                      range: {
                        startLineNumber: position.lineNumber,
                        endLineNumber: position.lineNumber,
                        startColumn: position.column,
                        endColumn: position.column,
                      }
                    });
                  });
                }
              }
            });
          }
          
          return { suggestions };
        }

        if (!currentWord && context.triggerKind !== monaco.languages.CompletionTriggerKind.Invoke) {
          return { suggestions: [] };
        }

        const suggestions = [];

        // Palabras clave
        palabrasClave.forEach(palabra => {
          suggestions.push({
            label: palabra,
            kind: monaco.languages.CompletionItemKind.Keyword,
            insertText: palabra,
            detail: "Palabra clave",
            documentation: { value: `Palabra reservada: **${palabra}**` },
            sortText: "3" + palabra,
            range: {
              startLineNumber: position.lineNumber,
              endLineNumber: position.lineNumber,
              startColumn: position.column - currentWord.length,
              endColumn: position.column,
            }
          });
        });

        // Funciones nativas
        funcionesNativas.forEach(fn => {
          suggestions.push({
            label: fn,
            kind: monaco.languages.CompletionItemKind.Function,
            insertText: `${fn}()`,
            detail: "Función incorporada",
            documentation: { value: `Función incorporada: **${fn}()**` },
            sortText: "4" + fn,
            range: {
              startLineNumber: position.lineNumber,
              endLineNumber: position.lineNumber,
              startColumn: position.column - currentWord.length,
              endColumn: position.column,
            }
          });
        });

        // Constantes
        constantes.forEach(constante => {
          suggestions.push({
            label: constante,
            kind: monaco.languages.CompletionItemKind.Constant,
            insertText: constante,
            detail: "Constante",
            documentation: { value: `Constante: **${constante}**` },
            sortText: "5" + constante,
            range: {
              startLineNumber: position.lineNumber,
              endLineNumber: position.lineNumber,
              startColumn: position.column - currentWord.length,
              endColumn: position.column,
            }
          });
        });

        // Módulos importados (soporta "importar mod" y "importar \"ruta\" como mod")
        parseImportStatements(fullText).forEach(({ moduleName, alias }) => {
          // Buscar el módulo
          const mod = currentLibraryModules[moduleName] || currentLocalModules[moduleName];
          if (mod) {
            // Agregar el alias del módulo
            if (alias.toLowerCase().includes(currentWord.toLowerCase()) || !currentWord) {
              suggestions.push({
                label: alias,
                kind: monaco.languages.CompletionItemKind.Module,
                insertText: alias,
                detail: `Módulo importado: ${moduleName}`,
                documentation: {
                  value: `Módulo: **${moduleName}**\n` +
                         `Alias: ${alias}\n` +
                         `Funciones: ${mod.exports.filter(e => e.type === 'function').map(e => e.name).join(", ") || "Ninguna"}`
                },
                sortText: "2" + alias,
                range: {
                  startLineNumber: position.lineNumber,
                  endLineNumber: position.lineNumber,
                  startColumn: position.column - currentWord.length,
                  endColumn: position.column,
                }
              });
            }
          }
        });

        // Variables y funciones del usuario
        const lines = model.getLinesContent();
        const userVariables = new Map();
        const userFunctions = new Map();

        lines.forEach((line, index) => {
          const trimmed = line.trim();

          const varMatch = trimmed.match(/^([a-zA-Z_]\w*)\s*[:=]/);
          if (varMatch) {
            const varName = varMatch[1];
            const tipo = detectarTipoVariable(model, varName);
            userVariables.set(varName, {
              name: varName,
              line: index + 1,
              tipo: tipo || "variable"
            });
          }

          const funcMatch = trimmed.match(/^funcion\s+([a-zA-Z_]\w*)\s*\(/);
          if (funcMatch) {
            const funcName = funcMatch[1];
            userFunctions.set(funcName, {
              name: funcName,
              line: index + 1
            });
          }
        });

        userVariables.forEach((varInfo, varName) => {
          if (varName.toLowerCase().includes(currentWord.toLowerCase()) || !currentWord) {
            suggestions.push({
              label: varName,
              kind: monaco.languages.CompletionItemKind.Variable,
              insertText: varName,
              detail: `${varInfo.tipo} (línea ${varInfo.line})`,
              documentation: { value: `Variable: **${varName}** (${varInfo.tipo})` },
              sortText: "6" + varName,
              range: {
                startLineNumber: position.lineNumber,
                endLineNumber: position.lineNumber,
                startColumn: position.column - currentWord.length,
                endColumn: position.column,
              }
            });
          }
        });

        userFunctions.forEach((funcInfo, funcName) => {
          if (funcName.toLowerCase().includes(currentWord.toLowerCase()) || !currentWord) {
            suggestions.push({
              label: funcName,
              kind: monaco.languages.CompletionItemKind.Function,
              insertText: `${funcName}()`,
              detail: `Función (línea ${funcInfo.line})`,
              documentation: { value: `Función: **${funcName}()**` },
              sortText: "6" + funcName,
              range: {
                startLineNumber: position.lineNumber,
                endLineNumber: position.lineNumber,
                startColumn: position.column - currentWord.length,
                endColumn: position.column,
              }
            });
          }
        });

        const seenLabels = new Set();
        const uniqueSuggestions = [];

        suggestions.forEach(suggestion => {
          const key = `${suggestion.label}-${suggestion.kind}`;
          if (!seenLabels.has(key)) {
            seenLabels.add(key);
            uniqueSuggestions.push(suggestion);
          }
        });

        return { suggestions: uniqueSuggestions };
      }
    });

    disposablesRef.current.push(symbolProviderDisposable, completionProviderDisposable);
    
    monaco.editor.setTheme("customTheme");
    setThemeApplied(true);
  };

  useEffect(() => {
    const checkMonaco = () => {
      if (window.monaco && !setupDoneRef.current) {
        setupDoneRef.current = true;
        setupMonaco();
        return true;
      }
      return !!window.monaco;
    };

    let interval;
    if (!checkMonaco()) {
      interval = setInterval(() => {
        if (checkMonaco()) {
          clearInterval(interval);
        }
      }, 100);
    }

    return () => {
      if (interval) clearInterval(interval);
      disposablesRef.current.forEach((d) => d?.dispose?.());
      disposablesRef.current = [];
      setupDoneRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (monacoRef.current && !themeApplied) {
      applyTheme();
    }
  }, [themeApplied, applyTheme]);

  // ─────────────────────── EXPLORADOR DE ARCHIVOS ───────────────────────

  const loadChildren = useCallback(async (path, nodeParam) => {
    setNodesByPath((current) => {
      const node = nodeParam || current[path];
      if (!node || node.kind !== "directory") return current;
      return current;
    });

    const node = nodeParam || nodesByPath[path];
    if (!node || node.kind !== "directory" || !node.handle?.entries) return;

    const entries = [];
    for await (const [name, entryHandle] of node.handle.entries()) {
      if (IGNORED_ENTRIES.has(name)) continue;
      entries.push({ name, entryHandle });
    }
    entries.sort((a, b) => {
      const aDir = a.entryHandle.kind === "directory";
      const bDir = b.entryHandle.kind === "directory";
      if (aDir !== bDir) return aDir ? -1 : 1;
      return a.name.localeCompare(b.name, "es");
    });

    const childPaths = [];
    const newNodes = {};
    entries.forEach(({ name, entryHandle }) => {
      const childPath = `${path}/${name}`;
      childPaths.push(childPath);
      newNodes[childPath] = {
        name,
        kind: entryHandle.kind,
        path: childPath,
        handle: entryHandle,
        parentPath: path,
        childrenPaths: entryHandle.kind === "directory" ? null : undefined,
      };
    });

    setNodesByPath((prev) => ({
      ...prev,
      ...newNodes,
      [path]: { ...prev[path], childrenPaths: childPaths },
    }));
  }, [nodesByPath]);

  const toggleFolder = useCallback((path) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
    const node = nodesByPath[path];
    if (node && node.childrenPaths === null) {
      loadChildren(path, node);
    }
  }, [nodesByPath, loadChildren]);

  const switchToModel = useCallback((path) => {
    const model = modelsRef.current.get(path);
    if (model && editorRef.current) {
      editorRef.current.setModel(model);
    }
  }, []);

  const markDirty = useCallback((path) => {
    setOpenFiles((prev) => prev.map((f) => (f.path === path && !f.dirty ? { ...f, dirty: true } : f)));
  }, []);

  const ensureModelLoaded = useCallback(async (path, node) => {
    const monaco = monacoRef.current;
    if (!monaco) return;
    if (modelsRef.current.has(path)) {
      switchToModel(path);
      return;
    }
    const file = await node.handle.getFile();
    const ext = getExt(node.name);
    const isBinary = BINARY_EXTENSIONS.has(ext);

    let text;
    let lang;
    if (isBinary) {
      // No decodificamos binarios como texto: eso los corrompe y muestra caracteres
      // ilegibles. Mostramos una vista informativa en su lugar y bloqueamos el guardado.
      binaryFilesRef.current.add(path);
      const kb = (file.size / 1024).toFixed(1);
      text =
        `// Archivo binario (.${ext}) — no se puede previsualizar ni editar como texto.\n` +
        `// Nombre: ${node.name}\n` +
        `// Tamaño: ${kb} KB\n` +
        `//\n` +
        `// Este archivo aparece en el árbol y puede usarse en "importar" normalmente;\n` +
        `// esta pestaña es solo informativa y no se guarda si la modificás.`;
      lang = "plaintext";
    } else {
      binaryFilesRef.current.delete(path);
      text = await file.text();
      lang = getMonacoLanguage(node.name);
    }

    const uri = monaco.Uri.parse(`file:///${path}`);
    let model = monaco.editor.getModel(uri);
    if (!model) {
      model = monaco.editor.createModel(text, lang, uri);
      model.onDidChangeContent(() => markDirty(path));
    }
    modelsRef.current.set(path, model);
    switchToModel(path);
  }, [markDirty, switchToModel]);

  const openFile = useCallback((path) => {
    const node = nodesByPath[path];
    if (!node || node.kind !== "file") return;
    setActiveFilePath(path);
    setOpenFiles((prev) => (prev.some((f) => f.path === path) ? prev : [...prev, { path, name: node.name, dirty: false }]));
    ensureModelLoaded(path, node);
  }, [nodesByPath, ensureModelLoaded]);

  const closeFile = useCallback((path, e) => {
    e.stopPropagation();
    setOpenFiles((prev) => {
      const idx = prev.findIndex((f) => f.path === path);
      const next = prev.filter((f) => f.path !== path);
      setActiveFilePath((current) => {
        if (current !== path) return current;
        const nextActive = next[idx] || next[idx - 1] || null;
        if (nextActive) switchToModel(nextActive.path);
        else editorRef.current?.setModel(null);
        return nextActive ? nextActive.path : null;
      });
      return next;
    });
  }, [switchToModel]);

  const saveActiveFile = useCallback(async () => {
    if (!activeFilePath) return;
    const node = nodesByPath[activeFilePath];
    const model = modelsRef.current.get(activeFilePath);
    if (!node || !model) return;
    if (binaryFilesRef.current.has(activeFilePath)) {
      await showAlert("Este archivo es binario y se muestra solo como referencia: no se puede guardar desde el editor de texto.");
      return;
    }
    if (!node.handle.createWritable) {
      await showAlert(
        "No se puede guardar directamente en disco: tu navegador no soporta acceso completo al sistema de archivos."
      );
      return;
    }
    try {
      const writable = await node.handle.createWritable();
      await writable.write(model.getValue());
      await writable.close();
      setOpenFiles((prev) => prev.map((f) => (f.path === activeFilePath ? { ...f, dirty: false } : f)));
    } catch (err) {
      console.error(err);
      await showAlert("No se pudo guardar el archivo: " + (err?.message || "permiso denegado."));
    }
  }, [activeFilePath, nodesByPath, showAlert]);

  useEffect(() => {
    saveActiveFileRef.current = saveActiveFile;
  }, [saveActiveFile]);

  // ─────────────────────── CREAR / ELIMINAR ARCHIVOS ───────────────────────

  const createEntry = useCallback(async (parentPath, kind) => {
    const parentNode = nodesByPath[parentPath];
    if (!parentNode || !parentNode.handle?.getFileHandle) {
      await showAlert("No se puede crear archivos aquí: esta carpeta se abrió en modo solo lectura.");
      return;
    }
    const name = await showPrompt(
      kind === "file" ? "Nombre del nuevo archivo:" : "Nombre de la nueva carpeta:",
      "",
      kind === "file" ? "Nuevo archivo" : "Nueva carpeta"
    );
    if (!name || !name.trim()) return;
    const cleanName = name.trim();

    try {
      const newHandle = kind === "file"
        ? await parentNode.handle.getFileHandle(cleanName, { create: true })
        : await parentNode.handle.getDirectoryHandle(cleanName, { create: true });

      const childPath = `${parentPath}/${cleanName}`;
      const newNode = {
        name: cleanName,
        kind,
        path: childPath,
        handle: newHandle,
        parentPath,
        childrenPaths: kind === "directory" ? [] : undefined,
      };

      setNodesByPath((prev) => {
        const parent = prev[parentPath];
        const currentChildren = parent.childrenPaths || [];
        if (currentChildren.includes(childPath)) {
          return { ...prev, [childPath]: newNode };
        }
        const merged = [...currentChildren, childPath].sort((a, b) => {
          const na = a === childPath ? newNode : prev[a];
          const nb = b === childPath ? newNode : prev[b];
          const aDir = na.kind === "directory";
          const bDir = nb.kind === "directory";
          if (aDir !== bDir) return aDir ? -1 : 1;
          return na.name.localeCompare(nb.name, "es");
        });
        return { ...prev, [childPath]: newNode, [parentPath]: { ...parent, childrenPaths: merged } };
      });
      setExpandedPaths((prev) => new Set(prev).add(parentPath));

      if (kind === "file") {
        setActiveFilePath(childPath);
        setOpenFiles((prev) => (prev.some((f) => f.path === childPath) ? prev : [...prev, { path: childPath, name: cleanName, dirty: false }]));
        ensureModelLoaded(childPath, newNode);
      }

      if (kind === "file" && cleanName.endsWith(".wn")) {
        setTimeout(() => scanAllModules(), 500);
      } else if (kind === "directory" && cleanName.toLowerCase() === "libreria") {
        setTimeout(() => scanAllModules(), 500);
      }

    } catch (err) {
      console.error(err);
      if (err?.name === "TypeMismatchError") {
        await showAlert("Ya existe una carpeta o archivo con ese nombre pero de otro tipo.");
      } else {
        await showAlert("No se pudo crear: " + (err?.message || "error desconocido."));
      }
    }
  }, [nodesByPath, ensureModelLoaded, showAlert, showPrompt, scanAllModules]);

  const deleteEntry = useCallback(async (path) => {
    const node = nodesByPath[path];
    if (!node || !node.parentPath) return;
    const parentNode = nodesByPath[node.parentPath];
    if (!parentNode?.handle?.removeEntry) {
      await showAlert("No se puede eliminar aquí: esta carpeta se abrió en modo solo lectura.");
      return;
    }
    const label = node.kind === "directory" ? "la carpeta" : "el archivo";
    const confirmed = await showConfirm(
      `¿Eliminar ${label} "${node.name}"? Esta acción no se puede deshacer.`,
      "Eliminar",
      { danger: true, confirmLabel: "Eliminar" }
    );
    if (!confirmed) return;

    try {
      await parentNode.handle.removeEntry(node.name, { recursive: node.kind === "directory" });

      const toRemove = new Set();
      const collect = (p) => {
        toRemove.add(p);
        const n = nodesByPath[p];
        if (n?.childrenPaths) n.childrenPaths.forEach(collect);
      };
      collect(path);

      toRemove.forEach((p) => {
        const m = modelsRef.current.get(p);
        if (m) {
          m.dispose();
          modelsRef.current.delete(p);
        }
      });

      setOpenFiles((prev) => {
        const next = prev.filter((f) => !toRemove.has(f.path));
        setActiveFilePath((current) => {
          if (!toRemove.has(current)) return current;
          const nextActive = next[0];
          if (nextActive) switchToModel(nextActive.path);
          else editorRef.current?.setModel(null);
          return nextActive ? nextActive.path : null;
        });
        return next;
      });

      setNodesByPath((prev) => {
        const next = { ...prev };
        toRemove.forEach((p) => delete next[p]);
        if (next[node.parentPath]) {
          next[node.parentPath] = {
            ...next[node.parentPath],
            childrenPaths: next[node.parentPath].childrenPaths.filter((cp) => cp !== path),
          };
        }
        return next;
      });

      setTimeout(() => scanAllModules(), 500);

    } catch (err) {
      console.error(err);
      await showAlert("No se pudo eliminar: " + (err?.message || "error desconocido."));
    }
  }, [nodesByPath, switchToModel, showAlert, showConfirm, scanAllModules]);

  const getCreateTargetPath = useCallback(() => {
    if (!selectedPath) return rootPath;
    const node = nodesByPath[selectedPath];
    if (!node) return rootPath;
    if (node.kind === "directory") return selectedPath;
    return node.parentPath || rootPath;
  }, [selectedPath, nodesByPath, rootPath]);

  const copyHandleInto = useCallback(async (sourceHandle, destDirHandle, name) => {
    if (sourceHandle.kind === "file") {
      const file = await sourceHandle.getFile();
      const content = await file.arrayBuffer();
      const newFileHandle = await destDirHandle.getFileHandle(name, { create: true });
      const writable = await newFileHandle.createWritable();
      await writable.write(content);
      await writable.close();
      return newFileHandle;
    }
    const newDirHandle = await destDirHandle.getDirectoryHandle(name, { create: true });
    for await (const [childName, childHandle] of sourceHandle.entries()) {
      if (IGNORED_ENTRIES.has(childName)) continue;
      await copyHandleInto(childHandle, newDirHandle, childName);
    }
    return newDirHandle;
  }, []);

  const moveEntry = useCallback(async (sourcePath, targetDirPath, desiredName) => {
    if (!sourcePath || !targetDirPath) return;

    const sourceNode = nodesByPath[sourcePath];
    const targetNode = nodesByPath[targetDirPath];
    if (!sourceNode || !targetNode || targetNode.kind !== "directory") return;
    if (!sourceNode.parentPath) return;

    const finalName = (desiredName && desiredName.trim()) || sourceNode.name;
    const samePlace = sourceNode.parentPath === targetDirPath && finalName === sourceNode.name;
    if (samePlace) return;

    if (sourceNode.kind === "directory") {
      let p = targetDirPath;
      while (p) {
        if (p === sourcePath) {
          await showAlert("No puedes mover una carpeta dentro de sí misma.");
          return;
        }
        p = nodesByPath[p]?.parentPath || null;
      }
    }

    const parentNode = nodesByPath[sourceNode.parentPath];
    if (!parentNode?.handle?.removeEntry) {
      await showAlert("No se puede mover: esta carpeta se abrió en modo solo lectura.");
      return;
    }
    if (!targetNode.handle?.getDirectoryHandle) {
      await showAlert("No se puede mover a esta carpeta en modo solo lectura.");
      return;
    }

    try {
      let existsAlready = false;
      try {
        if (sourceNode.kind === "file") await targetNode.handle.getFileHandle(finalName);
        else await targetNode.handle.getDirectoryHandle(finalName);
        existsAlready = true;
      } catch {
        // no existe
      }
      if (existsAlready) {
        const confirmed = await showConfirm(
          `Ya existe "${finalName}" en el destino. ¿Reemplazar?`,
          "Reemplazar",
          { danger: true, confirmLabel: "Reemplazar" }
        );
        if (!confirmed) return;
      }

      if (typeof sourceNode.handle.move === "function") {
        await sourceNode.handle.move(targetNode.handle, finalName);
      } else {
        await copyHandleInto(sourceNode.handle, targetNode.handle, finalName);
        await parentNode.handle.removeEntry(sourceNode.name, { recursive: sourceNode.kind === "directory" });
      }

      const affected = new Set();
      const collect = (p) => {
        affected.add(p);
        const n = nodesByPath[p];
        if (n?.childrenPaths) n.childrenPaths.forEach(collect);
      };
      collect(sourcePath);

      affected.forEach((p) => {
        const m = modelsRef.current.get(p);
        if (m) {
          m.dispose();
          modelsRef.current.delete(p);
        }
      });
      setOpenFiles((prev) => {
        const next = prev.filter((f) => !affected.has(f.path));
        setActiveFilePath((current) => (affected.has(current) ? (next[0]?.path || null) : current));
        return next;
      });

      setNodesByPath((prev) => {
        const next = { ...prev };
        affected.forEach((p) => delete next[p]);
        if (next[sourceNode.parentPath]) {
          next[sourceNode.parentPath] = {
            ...next[sourceNode.parentPath],
            childrenPaths: next[sourceNode.parentPath].childrenPaths.filter((cp) => cp !== sourcePath),
          };
        }
        return next;
      });
      setExpandedPaths((prev) => new Set(prev).add(targetDirPath));
      await loadChildren(targetDirPath, { ...targetNode });
      if (sourceNode.parentPath !== targetDirPath) {
        await loadChildren(sourceNode.parentPath, { ...parentNode });
      }
      setSelectedPath(`${targetDirPath}/${finalName}`);
      
      setTimeout(() => scanAllModules(), 500);
      
    } catch (err) {
      console.error(err);
      await showAlert("No se pudo mover: " + (err?.message || "error desconocido."));
    }
  }, [nodesByPath, copyHandleInto, loadChildren, showAlert, showConfirm, scanAllModules]);

  const renameEntry = useCallback(async (path) => {
    const node = nodesByPath[path];
    if (!node || !node.parentPath) {
      await showAlert("No se puede renombrar la carpeta raíz.");
      return;
    }
    const parentNode = nodesByPath[node.parentPath];
    if (!parentNode?.handle?.removeEntry) {
      await showAlert("No se puede renombrar aquí: esta carpeta se abrió en modo solo lectura.");
      return;
    }
    const newName = await showPrompt("Nuevo nombre:", node.name, "Renombrar");
    if (!newName || !newName.trim() || newName.trim() === node.name) return;
    await moveEntry(path, node.parentPath, newName.trim());
  }, [nodesByPath, moveEntry, showAlert, showPrompt]);

  const copyEntryToClipboard = useCallback((path) => {
    const node = nodesByPath[path];
    if (!node || !node.parentPath) return;
    setClipboard({ path });
  }, [nodesByPath]);

  const pasteEntry = useCallback(async (targetDirPath) => {
    if (!clipboard) return;
    const sourceNode = nodesByPath[clipboard.path];
    const targetNode = nodesByPath[targetDirPath];
    if (!sourceNode) {
      await showAlert("El elemento copiado ya no existe.");
      setClipboard(null);
      return;
    }
    if (!targetNode || targetNode.kind !== "directory") return;
    if (!targetNode.handle?.getDirectoryHandle) {
      await showAlert("No se puede pegar aquí: esta carpeta se abrió en modo solo lectura.");
      return;
    }

    const existsInTarget = async (name) => {
      try {
        if (sourceNode.kind === "file") await targetNode.handle.getFileHandle(name);
        else await targetNode.handle.getDirectoryHandle(name);
        return true;
      } catch {
        return false;
      }
    };

    let finalName = sourceNode.name;
    if (await existsInTarget(finalName)) {
      const dot = sourceNode.kind === "file" ? sourceNode.name.lastIndexOf(".") : -1;
      const base = dot > 0 ? sourceNode.name.slice(0, dot) : sourceNode.name;
      const ext = dot > 0 ? sourceNode.name.slice(dot) : "";
      let candidate = `${base} copia${ext}`;
      let i = 2;
      while (await existsInTarget(candidate)) {
        candidate = `${base} copia ${i}${ext}`;
        i++;
      }
      finalName = candidate;
    }

    try {
      await copyHandleInto(sourceNode.handle, targetNode.handle, finalName);
      setExpandedPaths((prev) => new Set(prev).add(targetDirPath));
      await loadChildren(targetDirPath, { ...targetNode });
      setSelectedPath(`${targetDirPath}/${finalName}`);
      
      setTimeout(() => scanAllModules(), 500);
      
    } catch (err) {
      console.error(err);
      await showAlert("No se pudo pegar: " + (err?.message || "error desconocido."));
    }
  }, [clipboard, nodesByPath, copyHandleInto, loadChildren, showAlert, scanAllModules]);

  useEffect(() => {
    const onKeyDown = (e) => {
      if (dialog) return;
      if (document.activeElement?.closest?.(".monaco-editor")) return;
      if (!selectedPath) return;

      const mod = e.ctrlKey || e.metaKey;

      if (e.key === "F2") {
        e.preventDefault();
        renameEntry(selectedPath);
      } else if (mod && e.key.toLowerCase() === "c") {
        const node = nodesByPath[selectedPath];
        if (node?.parentPath) {
          e.preventDefault();
          copyEntryToClipboard(selectedPath);
        }
      } else if (mod && e.key.toLowerCase() === "v" && clipboard) {
        e.preventDefault();
        pasteEntry(getCreateTargetPath());
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [dialog, selectedPath, nodesByPath, clipboard, renameEntry, copyEntryToClipboard, pasteEntry, getCreateTargetPath]);

  const startTerminalResize = useCallback((e) => {
    e.preventDefault();
    const startY = e.clientY;
    const startHeight = terminalHeight;
    terminalResizeRef.current = { startY, startHeight };

    const onMove = (moveEvent) => {
      const { startY: sy, startHeight: sh } = terminalResizeRef.current;
      const delta = sy - moveEvent.clientY;
      const next = Math.min(Math.max(sh + delta, 120), window.innerHeight - 160);
      setTerminalHeight(next);
    };
    const onUp = () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [terminalHeight]);

  useEffect(() => {
    if (!contextMenu) return;
    const close = () => setContextMenu(null);
    const onKeyDown = (e) => { if (e.key === "Escape") close(); };
    window.addEventListener("click", close);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [contextMenu]);

  const openFolder = useCallback(async () => {
    if (supportsFSAccess) {
      try {
        const handle = await window.showDirectoryPicker({ mode: "readwrite" });
        const rootNode = {
          name: handle.name, kind: "directory", path: handle.name,
          handle, parentPath: null, childrenPaths: null,
        };
        setNodesByPath({ [handle.name]: rootNode });
        setExpandedPaths(new Set([handle.name]));
        setRootPath(handle.name);
        setReadOnlyMode(false);
        await loadChildren(handle.name, rootNode);
        setTimeout(() => scanAllModules(), 1000);
      } catch (err) {
        if (err?.name !== "AbortError") console.error(err);
      }
    } else {
      fallbackInputRef.current?.click();
    }
  }, [supportsFSAccess, loadChildren, scanAllModules]);

  const handleFallbackInput = useCallback((e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    const nodes = {};
    let root = null;

    files.forEach((file) => {
      const parts = file.webkitRelativePath.split("/");
      if (parts.some((p) => IGNORED_ENTRIES.has(p))) return;
      if (!root) root = parts[0];

      let accPath = "";
      parts.forEach((part, i) => {
        const parentPath = accPath;
        accPath = accPath ? `${accPath}/${part}` : part;
        const isFile = i === parts.length - 1;

        if (!nodes[accPath]) {
          nodes[accPath] = {
            name: part,
            kind: isFile ? "file" : "directory",
            path: accPath,
            parentPath: parentPath || null,
            childrenPaths: isFile ? undefined : [],
            handle: isFile
              ? { kind: "file", getFile: async () => file }
              : { kind: "directory" },
          };
        }
        if (parentPath && nodes[parentPath] && !nodes[parentPath].childrenPaths.includes(accPath)) {
          nodes[parentPath].childrenPaths.push(accPath);
        }
      });
    });

    Object.values(nodes).forEach((n) => {
      if (n.kind === "directory") {
        n.childrenPaths.sort((a, b) => {
          const aDir = nodes[a].kind === "directory";
          const bDir = nodes[b].kind === "directory";
          if (aDir !== bDir) return aDir ? -1 : 1;
          return nodes[a].name.localeCompare(nodes[b].name, "es");
        });
      }
    });

    setNodesByPath(nodes);
    setExpandedPaths(new Set([root]));
    setRootPath(root);
    setReadOnlyMode(true);
    e.target.value = "";
    
    setTimeout(() => scanAllModules(), 1000);
  }, [scanAllModules]);

  useEffect(() => {
    if (activeFilePath) switchToModel(activeFilePath);
  }, [activeFilePath, switchToModel]);

  const handleEditorDidMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;
    
    monaco.editor.setTheme("customTheme");
    setThemeApplied(true);
    
    setTimeout(() => {
      monaco.editor.setTheme("customTheme");
    }, 100);
    
    editor.onDidFocusEditorWidget(() => {
      setTimeout(() => {
        monaco.editor.setTheme("customTheme");
      }, 10);
    });

    editor.updateOptions({
      autoClosingBrackets: "always",
      autoClosingQuotes: "always",
      autoClosingDelete: "always",
      autoClosingOvertype: "always",
      autoIndent: "full",
      formatOnPaste: true,
      formatOnType: true,

      suggest: {
        showKeywords: true,
        showFunctions: true,
        showVariables: true,
        showSnippets: false,
        showClasses: true,
        showModules: true,
        snippetsPreventQuickSuggestions: false,
        preview: true,
        filterGraceful: true,
        localityBonus: true,
        shareWordSuggestionsPool: false,
        insertMode: "insert",
        showWords: false,
      },

      quickSuggestions: {
        other: true,
        comments: false,
        strings: true // necesario para que autocompleten las rutas dentro de importar "..."
      },

      acceptSuggestionOnEnter: "on",
      acceptSuggestionOnCommitCharacter: true,
      parameterHints: { enabled: true },
      hover: { enabled: true },
      contextmenu: true,
      suggestSelection: "first",
      suggestIcons: true,
      suggestFilterGraceful: true,
      suggestLocalityBonus: true,
      suggestShowInlineDetails: true,
      suggestMaxVisibleSuggestions: 12,
    });

    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Space, () => {
      editor.trigger("keyboard", "editor.action.triggerSuggest", {});
    });

    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      saveActiveFileRef.current();
    });

    editor.onKeyDown((e) => {
      if (e.keyCode !== monaco.KeyCode.Enter) return;

      const position = editor.getPosition();
      const model = editor.getModel();
      const lineContent = model.getLineContent(position.lineNumber);
      const beforeCursor = lineContent.slice(0, position.column - 1);
      const afterCursor = lineContent.slice(position.column - 1);
      const charBefore = beforeCursor.slice(-1);
      const charAfter = afterCursor.slice(0, 1);
      const lineIndent = lineContent.match(/^\s*/)[0] || "";

      const isInsideEmptyBlock =
        (charBefore === "{" && charAfter === "}") ||
        (charBefore === "[" && charAfter === "]");

      const isOpeningBlockAtCursor =
        /[{[]\s*$/.test(beforeCursor) &&
        !afterCursor.trimStart().startsWith("}") &&
        !afterCursor.trimStart().startsWith("]");

      if (isInsideEmptyBlock || isOpeningBlockAtCursor) {
        e.preventDefault();
        e.stopPropagation();

        const indent = lineIndent;
        const newIndent = indent + "    ";
        const insertText = `\n${newIndent}\n${indent}`;

        editor.executeEdits("expand-brackets", [{
          range: {
            startLineNumber: position.lineNumber,
            endLineNumber: position.lineNumber,
            startColumn: position.column,
            endColumn: position.column,
          },
          text: insertText,
          forceMoveMarkers: true,
        }]);

        editor.setPosition({
          lineNumber: position.lineNumber + 1,
          column: newIndent.length + 1,
        });
      }
    });

    editor.onDidType((text) => {
      if (text === '"' || text === "'" || text === "`" || text === "(") {
        const position = editor.getPosition();
        const lineContent = editor.getModel().getLineContent(position.lineNumber);

        const closingMap = {
          '"': '"',
          "'": "'",
          "`": "`",
          "(": ")"
        };

        const closingChar = closingMap[text];
        const charAfter = lineContent[position.column - 1] || "";

        if (charAfter !== closingChar) {
          editor.executeEdits("auto-close", [{
            range: {
              startLineNumber: position.lineNumber,
              endLineNumber: position.lineNumber,
              startColumn: position.column,
              endColumn: position.column
            },
            text: closingChar,
            forceMoveMarkers: true
          }]);

          editor.setPosition({
            lineNumber: position.lineNumber,
            column: position.column
          });
        }
      }

      if (text === "{" || text === "[") {
        const position = editor.getPosition();
        const lineContent = editor.getModel().getLineContent(position.lineNumber);

        const closingMap = {
          "{": "}",
          "[": "]"
        };

        const closingChar = closingMap[text];
        const charAfter = lineContent[position.column - 1] || "";

        if (charAfter !== closingChar) {
          editor.executeEdits("auto-close-bracket", [{
            range: {
              startLineNumber: position.lineNumber,
              endLineNumber: position.lineNumber,
              startColumn: position.column,
              endColumn: position.column
            },
            text: closingChar,
            forceMoveMarkers: true
          }]);

          editor.setPosition({
            lineNumber: position.lineNumber,
            column: position.column
          });
        }
      }

      if (text === ":") {
        setTimeout(() => {
          const position = editor.getPosition();
          const lineContent = editor.getModel().getLineContent(position.lineNumber);

          if (lineContent.trim().endsWith(":")) {
            const indent = lineContent.match(/^\s*/)[0] || "";
            const newIndent = indent + "    ";

            editor.executeEdits("auto-indent", [{
              range: {
                startLineNumber: position.lineNumber,
                endLineNumber: position.lineNumber,
                startColumn: position.column,
                endColumn: position.column
              },
              text: `\n${newIndent}`,
              forceMoveMarkers: true
            }]);

            editor.setPosition({
              lineNumber: position.lineNumber + 1,
              column: newIndent.length + 1
            });
          }
        }, 10);
      }

      if (/[a-zA-Z_]/.test(text)) {
        editor.trigger("keyboard", "editor.action.triggerSuggest", {});
      }
    });
  };

  // ─────────────────────── PANEL DE MÓDULOS ───────────────────────

  function ModulesPanel() {
    const totalModules = Object.keys(localModules).length + Object.keys(libraryModules).length;
    
    if (!rootPath) return null;
    
    return (
      <div style={{ 
        borderTop: "1px solid #313244", 
        padding: "8px 12px",
        marginTop: "auto",
        background: "#181825",
      }}>
        <div 
          onClick={() => setShowModulesPanel(!showModulesPanel)}
          style={{
            display: "flex", 
            alignItems: "center", 
            justifyContent: "space-between",
            cursor: "pointer",
            color: "#9399b2",
            fontSize: 11,
            letterSpacing: "0.08em",
            fontWeight: 600,
            padding: "4px 0",
          }}
        >
          <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <ModulesIcon />
            MÓDULOS {totalModules > 0 && `(${totalModules})`}
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <button
              onClick={(e) => {
                e.stopPropagation();
                findLibraryInAppData();
              }}
              style={{
                background: "transparent",
                border: "none",
                color: "#9399b2",
                cursor: "pointer",
                padding: 2,
                borderRadius: 3,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              title="Buscar librerías en AppData\Local\Programs"
              onMouseEnter={(e) => e.currentTarget.style.background = "#313244"}
              onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
            >
              <AppDataIcon />
            </button>
            <ChevronIcon open={showModulesPanel} />
          </div>
        </div>
        
        {showModulesPanel && (
          <div style={{ marginTop: 6, fontSize: 12, maxHeight: "200px", overflowY: "auto" }}>
            {/* Módulos locales */}
            {Object.keys(localModules).length > 0 && (
              <div style={{ marginBottom: 6 }}>
                <span style={{ color: "#89b4fa", fontSize: 10, opacity: 0.7 }}>LOCALES</span>
                {Object.keys(localModules).map(name => {
                  const mod = localModules[name];
                  const funcs = mod.functions || [];
                  const vars = mod.variables || [];
                  return (
                    <div key={name} style={{ 
                      padding: "2px 0", 
                      color: "#CDD6F4",
                      display: "flex",
                      alignItems: "center",
                      gap: 4,
                    }}>
                      <FileIcon name={`${name}.wn`} />
                      <span>{name}</span>
                      <span style={{ fontSize: 10, color: "#6C7086", marginLeft: "auto" }}>
                        {funcs.length} func{funcs.length !== 1 ? "s" : ""}
                        {vars.length > 0 && `, ${vars.length} var${vars.length !== 1 ? "s" : ""}`}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
            
            {/* Módulos de librería */}
            {Object.keys(libraryModules).length > 0 && (
              <div>
                <span style={{ color: "#f38ba8", fontSize: 10, opacity: 0.7 }}>LIBRERÍA</span>
                {Object.keys(libraryModules).map(name => {
                  const mod = libraryModules[name];
                  const extDisplay = mod.extension.replace(".", "").toUpperCase();
                  const funcs = mod.exports.filter(e => e.type === 'function') || [];
                  const vars = mod.exports.filter(e => e.type === 'variable') || [];
                  const colors = {
                    ".wn": "#a225a7",
                    ".go": "#00ADD8",
                    ".dll": "#6C7086",
                    ".so": "#FF6B6B",
                    ".dylib": "#A6E3A1",
                  };
                  return (
                    <div key={name} style={{ 
                      padding: "2px 0", 
                      color: "#CDD6F4",
                      display: "flex",
                      alignItems: "center",
                      gap: 4,
                    }}>
                      <span style={{ 
                        display: "inline-block",
                        width: 18,
                        height: 18,
                        borderRadius: 2,
                        background: colors[mod.extension] || "#6C7086",
                        fontSize: 7,
                        color: "#1E1E2E",
                        textAlign: "center",
                        lineHeight: "18px",
                        fontWeight: "bold",
                        flexShrink: 0,
                      }}>
                        {extDisplay.slice(0, 3)}
                      </span>
                      <span>{name}</span>
                      <span style={{ fontSize: 10, color: "#6C7086", marginLeft: "auto" }}>
                        {funcs.length} func{funcs.length !== 1 ? "s" : ""}
                        {vars.length > 0 && `, ${vars.length} var${vars.length !== 1 ? "s" : ""}`}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
            
            {totalModules === 0 && (
              <div style={{ color: "#6C7086", fontSize: 11, padding: "4px 0" }}>
                No se encontraron módulos
                {supportsFSAccess && (
                  <div style={{ marginTop: 4 }}>
                    <button
                      onClick={findLibraryInAppData}
                      style={{
                        background: "#313244",
                        color: "#CDD6F4",
                        border: "1px solid #45475A",
                        borderRadius: 3,
                        padding: "3px 8px",
                        fontSize: 11,
                        cursor: "pointer",
                      }}
                    >
                      Buscar en AppData
                    </button>
                  </div>
                )}
              </div>
            )}
            
            {isScanningLibraries && (
              <div style={{ color: "#6C7086", fontSize: 11, padding: "4px 0" }}>
                Escaneando módulos...
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  // ─────────────────────── RENDER DEL ÁRBOL ───────────────────────

  const renderTree = (path, depth) => {
    const node = nodesByPath[path];
    if (!node) return null;
    const isExpanded = expandedPaths.has(path);
    const isActive = path === activeFilePath;

    const isDropTarget = dragOverPath === path;
    const isSelected = selectedPath === path;

    if (node.kind === "directory") {
      return (
        <div key={path}>
          <div
            draggable
            onDragStart={(e) => {
              e.stopPropagation();
              draggedPathRef.current = path;
              e.dataTransfer.effectAllowed = "move";
              e.dataTransfer.setData("text/plain", path);
            }}
            onDragOver={(e) => {
              if (!draggedPathRef.current || draggedPathRef.current === path) return;
              e.preventDefault();
              e.stopPropagation();
              e.dataTransfer.dropEffect = "move";
              if (dragOverPath !== path) setDragOverPath(path);
            }}
            onDragLeave={(e) => {
              e.stopPropagation();
              setDragOverPath((current) => (current === path ? null : current));
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.stopPropagation();
              const dragged = draggedPathRef.current || e.dataTransfer.getData("text/plain");
              draggedPathRef.current = null;
              setDragOverPath(null);
              if (dragged) moveEntry(dragged, path);
            }}
            onDragEnd={() => { draggedPathRef.current = null; setDragOverPath(null); }}
            onClick={() => { setSelectedPath(path); toggleFolder(path); }}
            onContextMenu={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setSelectedPath(path);
              setContextMenu({ x: e.clientX, y: e.clientY, path });
            }}
            style={{
              display: "flex", alignItems: "center", gap: 4,
              padding: "3px 8px", paddingLeft: 8 + depth * 14,
              cursor: "pointer", userSelect: "none",
              color: "#CDD6F4", fontSize: 13, whiteSpace: "nowrap",
              background: isDropTarget ? "#39456b" : (isSelected ? "#2a2a3d" : "transparent"),
              outline: isDropTarget ? "1px dashed #89b4fa" : "none",
              outlineOffset: -1,
            }}
            onMouseEnter={(e) => { if (!isDropTarget) e.currentTarget.style.background = "#26263a"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = isDropTarget ? "#39456b" : (isSelected ? "#2a2a3d" : "transparent"); }}
          >
            <ChevronIcon open={isExpanded} />
            <FolderIcon open={isExpanded} />
            <span>{node.name}</span>
          </div>
          {isExpanded && node.childrenPaths && node.childrenPaths.map((cp) => renderTree(cp, depth + 1))}
        </div>
      );
    }

    return (
      <div
        key={path}
        draggable
        onDragStart={(e) => {
          e.stopPropagation();
          draggedPathRef.current = path;
          e.dataTransfer.effectAllowed = "move";
          e.dataTransfer.setData("text/plain", path);
        }}
        onDragEnd={() => { draggedPathRef.current = null; setDragOverPath(null); }}
        onClick={() => { setSelectedPath(path); openFile(path); }}
        onContextMenu={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setSelectedPath(path);
          setContextMenu({ x: e.clientX, y: e.clientY, path });
        }}
        style={{
          display: "flex", alignItems: "center", gap: 6,
          padding: "3px 8px", paddingLeft: 8 + depth * 14 + 14,
          cursor: "pointer", userSelect: "none",
          background: isActive ? "#37374a" : (isSelected ? "#2a2a3d" : "transparent"),
          borderLeft: isActive ? "2px solid #89b4fa" : "2px solid transparent",
          color: isActive ? "#ffffff" : "#CDD6F4", fontSize: 13, whiteSpace: "nowrap",
        }}
        onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = "#26263a"; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = isActive ? "#37374a" : (isSelected ? "#2a2a3d" : "transparent"); }}
      >
        <FileIcon name={node.name} />
        <span>{node.name}</span>
      </div>
    );
  };

  return (
    <div style={{ width: "100vw", height: "100vh", display: "flex", flexDirection: "column" }}>
      <DialogModal dialog={dialog} />
      <input
        ref={fallbackInputRef}
        type="file"
        webkitdirectory=""
        directory=""
        multiple
        style={{ display: "none" }}
        onChange={handleFallbackInput}
      />

      <div style={{
        background: "#181825",
        padding: "8px 16px",
        color: "#CDD6F4",
        borderBottom: "1px solid #313244",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        fontSize: 13,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#89b4fa" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="16 18 22 12 16 6" />
            <polyline points="8 6 2 12 8 18" />
          </svg>
          <span style={{ fontWeight: 600, letterSpacing: "0.02em" }}>Editor Wini</span>
          <span style={{ color: "#6C7086", fontSize: 12, marginLeft: 4 }}>—Enginedvp</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 12, opacity: 0.7 }}>
          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="6 9 12 15 18 9" />
            </svg>
            Ctrl+Space
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <DiskIcon />
            Ctrl+S
          </span>
          {readOnlyMode && (
            <span style={{ 
              background: "#313244", 
              padding: "2px 8px", 
              borderRadius: 3,
              fontSize: 11,
              color: "#F38BA8"
            }}>
              Solo lectura
            </span>
          )}
          <button
            onClick={() => setTerminalOpen((v) => !v)}
            title="Alternar terminal"
            style={{
              background: terminalOpen ? "#313244" : "transparent",
              border: "1px solid #45475A", color: "#CDD6F4",
              cursor: "pointer", fontSize: 11, padding: "3px 8px",
              borderRadius: 3, display: "flex", alignItems: "center", gap: 5,
            }}
          >
            <TerminalIcon /> Terminal
          </button>
        </div>
      </div>

      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        <div style={{
          width: 240, flexShrink: 0,
          background: "#181825",
          borderRight: "1px solid #313244",
          display: "flex", flexDirection: "column",
          overflow: "hidden",
        }}>
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "10px 14px 6px",
            color: "#9399b2", fontSize: 11, letterSpacing: "0.08em", fontWeight: 600,
          }}>
            <span>EXPLORADOR</span>
            <div style={{ display: "flex", alignItems: "center", gap: 2 }}>
              {rootPath && (
                <>
                  <button
                    onClick={() => createEntry(getCreateTargetPath(), "file")}
                    title="Nuevo archivo (en la carpeta seleccionada)"
                    style={{
                      background: "transparent", border: "none", color: "#9399b2",
                      cursor: "pointer", padding: 4, borderRadius: 3,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      transition: "background 0.15s ease",
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = "#313244"}
                    onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                  >
                    <NewFileIcon />
                  </button>
                  <button
                    onClick={() => createEntry(getCreateTargetPath(), "directory")}
                    title="Nueva carpeta (en la carpeta seleccionada)"
                    style={{
                      background: "transparent", border: "none", color: "#9399b2",
                      cursor: "pointer", padding: 4, borderRadius: 3,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      transition: "background 0.15s ease",
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = "#313244"}
                    onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                  >
                    <NewFolderIcon />
                  </button>
                </>
              )}
              <button
                onClick={openFolder}
                title="Abrir carpeta"
                style={{
                  background: "transparent", border: "none", color: "#9399b2",
                  cursor: "pointer", fontSize: 14, lineHeight: 1, padding: 4,
                  borderRadius: 3,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  transition: "background 0.15s ease",
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = "#313244"}
                onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
              >
                <OpenFolderIcon />
              </button>
            </div>
          </div>

          {contextMenu && nodesByPath[contextMenu.path] && (
            <div
              onClick={(e) => e.stopPropagation()}
              style={{
                position: "fixed", top: contextMenu.y, left: contextMenu.x,
                background: "#26263a", border: "1px solid #45475A", borderRadius: 4,
                boxShadow: "0 4px 12px rgba(0,0,0,0.4)", zIndex: 1000,
                minWidth: 170, padding: "4px 0", fontSize: 13,
              }}
            >
              {nodesByPath[contextMenu.path].kind === "directory" && (
                <>
                  <div
                    onClick={() => { createEntry(contextMenu.path, "file"); setContextMenu(null); }}
                    style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 12px", cursor: "pointer", color: "#CDD6F4" }}
                    onMouseEnter={(e) => e.currentTarget.style.background = "#313244"}
                    onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                  >
                    <NewFileIcon /> Nuevo archivo
                  </div>
                  <div
                    onClick={() => { createEntry(contextMenu.path, "directory"); setContextMenu(null); }}
                    style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 12px", cursor: "pointer", color: "#CDD6F4" }}
                    onMouseEnter={(e) => e.currentTarget.style.background = "#313244"}
                    onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                  >
                    <NewFolderIcon /> Nueva carpeta
                  </div>
                  {clipboard && (
                    <div
                      onClick={() => { pasteEntry(contextMenu.path); setContextMenu(null); }}
                      style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 12px", cursor: "pointer", color: "#CDD6F4" }}
                      onMouseEnter={(e) => e.currentTarget.style.background = "#313244"}
                      onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                    >
                      <PasteIcon /> Pegar
                    </div>
                  )}
                </>
              )}
              {nodesByPath[contextMenu.path].parentPath && (
                <>
                  <div style={{ height: 1, background: "#45475A", margin: "4px 0" }} />
                  <div
                    onClick={() => { copyEntryToClipboard(contextMenu.path); setContextMenu(null); }}
                    style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 12px", cursor: "pointer", color: "#CDD6F4" }}
                    onMouseEnter={(e) => e.currentTarget.style.background = "#313244"}
                    onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                  >
                    <CopyIcon /> Copiar
                  </div>
                  <div
                    onClick={() => { renameEntry(contextMenu.path); setContextMenu(null); }}
                    style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 12px", cursor: "pointer", color: "#CDD6F4" }}
                    onMouseEnter={(e) => e.currentTarget.style.background = "#313244"}
                    onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                  >
                    <RenameIcon /> Renombrar
                  </div>
                  <div style={{ height: 1, background: "#45475A", margin: "4px 0" }} />
                  <div
                    onClick={() => { deleteEntry(contextMenu.path); setContextMenu(null); }}
                    style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 12px", cursor: "pointer", color: "#F38BA8" }}
                    onMouseEnter={(e) => e.currentTarget.style.background = "#313244"}
                    onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                  >
                    <TrashIcon /> Eliminar
                  </div>
                </>
              )}
            </div>
          )}

          <div
            style={{
              flex: 1, overflowY: "auto", paddingBottom: 12,
              background: dragOverPath === "__ROOT__" ? "#232338" : "transparent",
            }}
            onClick={() => setSelectedPath(rootPath)}
            onDragOver={(e) => {
              if (!draggedPathRef.current || !rootPath) return;
              e.preventDefault();
              if (dragOverPath !== "__ROOT__") setDragOverPath("__ROOT__");
            }}
            onDragLeave={() => setDragOverPath((current) => (current === "__ROOT__" ? null : current))}
            onDrop={(e) => {
              e.preventDefault();
              const dragged = draggedPathRef.current || e.dataTransfer.getData("text/plain");
              draggedPathRef.current = null;
              setDragOverPath(null);
              if (dragged && rootPath) moveEntry(dragged, rootPath);
            }}
          >
            {rootPath ? (
              renderTree(rootPath, 0)
            ) : (
              <div style={{ padding: "16px 14px", color: "#9399b2", fontSize: 12.5 }}>
                <div style={{ display: "flex", justifyContent: "center", marginBottom: 12 }}>
                  <EmptyDocIcon />
                </div>
                <p style={{ margin: "0 0 12px", textAlign: "center", lineHeight: 1.5 }}>
                  No has abierto ninguna carpeta.
                </p>
                <button
                  onClick={openFolder}
                  style={{
                    width: "100%", padding: "8px 10px",
                    background: "#313244", color: "#CDD6F4",
                    border: "1px solid #45475A", borderRadius: 4,
                    cursor: "pointer", fontSize: 12.5,
                    display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                    transition: "background 0.15s ease, border-color 0.15s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "#45475A";
                    e.currentTarget.style.borderColor = "#585B70";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "#313244";
                    e.currentTarget.style.borderColor = "#45475A";
                  }}
                >
                  <OpenFolderIcon />
                  Abrir Carpeta
                </button>
                {!supportsFSAccess && (
                  <p style={{ margin: "10px 0 0", fontSize: 11, opacity: 0.7, lineHeight: 1.4 }}>
                    Tu navegador no soporta acceso completo al sistema de archivos: podrás ver y editar los archivos, pero no guardarlos directamente en disco.
                  </p>
                )}
              </div>
            )}
          </div>

          <ModulesPanel />
        </div>

        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
          {openFiles.length > 0 && (
            <div style={{
              display: "flex", background: "#181825",
              borderBottom: "1px solid #313244", overflowX: "auto", flexShrink: 0,
            }}>
              {openFiles.map((f) => {
                const isActive = f.path === activeFilePath;
                return (
                  <div
                    key={f.path}
                    onClick={() => setActiveFilePath(f.path)}
                    style={{
                      display: "flex", alignItems: "center", gap: 6,
                      padding: "7px 8px 7px 12px",
                      background: isActive ? "#1E1E2E" : "transparent",
                      borderRight: "1px solid #313244",
                      borderTop: isActive ? "2px solid #89b4fa" : "2px solid transparent",
                      color: isActive ? "#ffffff" : "#9399b2",
                      fontSize: 13, cursor: "pointer", whiteSpace: "nowrap", flexShrink: 0,
                      transition: "background 0.1s ease",
                    }}
                  >
                    <FileIcon name={f.name} />
                    <span>{f.name}</span>
                    {f.dirty && (
                      <span style={{ marginLeft: 2, display: "flex", alignItems: "center" }}>
                        <DirtyDotIcon />
                      </span>
                    )}
                    <span
                      onClick={(e) => closeFile(f.path, e)}
                      style={{
                        marginLeft: 4, opacity: 0.5, fontSize: 14, lineHeight: 1,
                        padding: "2px 4px", borderRadius: 3,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        transition: "background 0.1s ease, opacity 0.1s ease",
                      }}
                      onMouseEnter={(e) => { 
                        e.currentTarget.style.background = "#45475A"; 
                        e.currentTarget.style.opacity = 1; 
                      }}
                      onMouseLeave={(e) => { 
                        e.currentTarget.style.background = "transparent"; 
                        e.currentTarget.style.opacity = 0.5; 
                      }}
                    >
                      <CloseXIcon />
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          <div style={{ flex: 1, minHeight: 0, position: "relative", background: "#1E1E2E" }}>
            {openFiles.length === 0 && (
              <div style={{
                position: "absolute", inset: 0, display: "flex",
                flexDirection: "column",
                alignItems: "center", justifyContent: "center",
                color: "#6C7086", fontSize: 13, pointerEvents: "none",
                background: "#1E1E2E", zIndex: 1,
                gap: 16,
              }}>
                <EmptyDocIcon />
                <span>Abre una carpeta y selecciona un archivo para editarlo</span>
              </div>
            )}
            <Editor
              height="100%"
              defaultLanguage="wini"
              theme="customTheme"
              onMount={handleEditorDidMount}
              options={{
                fontSize: 14,
                fontFamily: "Fira Code, 'Cascadia Code', Consolas, monospace",
                fontLigatures: true,
                minimap: { enabled: true },
                automaticLayout: true,
                lineNumbers: "on",
                renderWhitespace: "selection",
                bracketPairColorization: { enabled: true },
                readOnly: false,
                backgroundColor: "#1E1E2E",
              }}
            />
          </div>

          {terminalOpen && (
            <TerminalPanel
              height={terminalHeight}
              onResizeStart={startTerminalResize}
              onClose={() => setTerminalOpen(false)}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default App;