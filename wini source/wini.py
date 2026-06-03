import argparse
import subprocess
import os
from interprete import Interprete
import sys

VERSION = "1.0.0"


class InstaladorWini:
    def __init__(self):
        self.ruta_librerias = os.path.join(self._obtener_ruta_base(), 'librerias')
        self.registro = os.path.join(self._obtener_ruta_base(), 'instaladas.txt')
        self.asegurar_directorios()



    def _obtener_ruta_base(self):
        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)

        return os.path.dirname(os.path.abspath(__file__))
    
    def asegurar_directorios(self):
        os.makedirs(self.ruta_librerias, exist_ok=True)
        os.makedirs(os.path.dirname(self.registro), exist_ok=True)
    
    def obtener_nombre_repo(self, url):
        nombre = url.split('/')[-1]
        if nombre.endswith('.git'):
            nombre = nombre[:-4]
        return nombre
    
    def instalar(self, url):
        nombre = self.obtener_nombre_repo(url)
        ruta_destino = os.path.join(self.ruta_librerias, nombre)
        
        if os.path.exists(ruta_destino):
            return f"⚠️ La librería '{nombre}' ya está instalada"
        
        print(f"📦 Instalando {nombre}...")
        try:
            subprocess.run(["git", "clone", url, ruta_destino], check=True, capture_output=True)
            
            # Guardar en registro
            with open(self.registro, 'a', encoding='utf-8') as f:
                f.write(f"{nombre}|{url}\n")
            
            return f"✅ Librería '{nombre}' instalada correctamente"
        except subprocess.CalledProcessError as e:
            return f"❌ Error al instalar: {e.stderr.decode() if e.stderr else 'Desconocido'}"
    
    def actualizar(self, nombre):
        ruta = os.path.join(self.ruta_librerias, nombre)
        if not os.path.exists(ruta):
            return f"❌ Librería '{nombre}' no encontrada"
        
        print(f"🔄 Actualizando {nombre}...")
        try:
            subprocess.run(["git", "-C", ruta, "pull"], check=True, capture_output=True)
            return f"✅ Librería '{nombre}' actualizada"
        except subprocess.CalledProcessError as e:
            return f"❌ Error: {e.stderr.decode() if e.stderr else 'Desconocido'}"
    
    def eliminar(self, nombre):
        ruta = os.path.join(self.ruta_librerias, nombre)
        if not os.path.exists(ruta):
            return f"❌ Librería '{nombre}' no encontrada"
        
        print(f"🗑️ Eliminando {nombre}...")
        try:
            import shutil
            shutil.rmtree(ruta)
            
            # Eliminar del registro
            if os.path.exists(self.registro):
                with open(self.registro, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                with open(self.registro, 'w', encoding='utf-8') as f:
                    for line in lines:
                        if not line.startswith(f"{nombre}|"):
                            f.write(line)
            
            return f"✅ Librería '{nombre}' eliminada"
        except Exception as e:
            return f"❌ Error: {e}"
    
    def listar(self):
        if not os.path.exists(self.ruta_librerias):
            return "📭 No hay librerías instaladas"
        
        librerias = [d for d in os.listdir(self.ruta_librerias) 
                    if os.path.isdir(os.path.join(self.ruta_librerias, d))]
        
        if not librerias:
            return "📭 No hay librerías instaladas"
        
        resultado = "\n📚 Librerías Wini instaladas:\n"
        resultado += "═" * 40 + "\n"
        for lib in sorted(librerias):
            ruta = os.path.join(self.ruta_librerias, lib)
            # Contar archivos .wipy/.wn
            archivos = []
            for root, dirs, files in os.walk(ruta):
                for f in files:
                    if f.endswith(('.wn', '.wipy')):
                        archivos.append(f)
            
            resultado += f"  📦 {lib}\n"
            resultado += f"     📄 {len(archivos)} módulo(s)\n"
        resultado += "═" * 40
        return resultado


def main():
    parser = argparse.ArgumentParser(
        prog="wini",
        description="Lenguaje de programación Wini",
        epilog="Ejemplos:\n  wini programa.wn\n  wini instala https://github.com/usuario/lib.git\n  wini actualiza lib\n  wini elimina lib\n  wini lista\n  wini --version",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"Wini {VERSION}"
    )

    parser.add_argument(
        "comando",
        nargs="?",
        help="Archivo .wn o comando: instala, actualiza, elimina, lista"
    )

    parser.add_argument(
        "argumento",
        nargs="?",
        help="URL para instalar o nombre de librería para actualizar/eliminar"
    )

    args = parser.parse_args()

    if not args.comando:
        parser.print_help()
        return

    instalador = InstaladorWini()

    # Comandos del instalador
    if args.comando == "instala":
        if not args.argumento:
            print("❌ Uso: wini instala <url>")
            return
        print(instalador.instalar(args.argumento))
        return

    elif args.comando == "actualiza":
        if not args.argumento:
            print("❌ Uso: wini actualiza <nombre>")
            return
        print(instalador.actualizar(args.argumento))
        return

    elif args.comando == "elimina":
        if not args.argumento:
            print("❌ Uso: wini elimina <nombre>")
            return
        print(instalador.eliminar(args.argumento))
        return

    elif args.comando == "lista":
        print(instalador.listar())
        return

    # Si no es comando, debe ser archivo .wn
    if not args.comando.endswith(".wn"):
        print(f"❌ Error: '{args.comando}' no es un comando válido ni archivo .wn")
        print("\nComandos disponibles:")
        print("  wini instala <url>     - Instalar librería")
        print("  wini actualiza <nombre> - Actualizar librería")
        print("  wini elimina <nombre>  - Eliminar librería")
        print("  wini lista             - Listar librerías")
        print("  wini <archivo.wn>      - Ejecutar programa")
        return

    # Ejecutar archivo .wn
    if not os.path.exists(args.comando):
        print(f"❌ Error: Archivo '{args.comando}' no encontrado")
        return

    interprete = Interprete(args.comando)
    interprete.ejecutar()


if __name__ == "__main__":
    main()