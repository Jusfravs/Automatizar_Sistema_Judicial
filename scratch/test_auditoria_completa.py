# scratch/test_auditoria_completa.py
import os
import sys
import json

sys.path.insert(0, os.path.abspath("."))

def verificar_todo():
    print("============================================================")
    print("[AUDITORIA COMPLETA] - REVISION DE ESTRUCTURA Y ARCHIVOS")
    print("============================================================")

    archivos_requeridos = [
        # Código Principal y Orquestador
        "main.py",
        "config.json",
        "README.md",
        ".gitignore",
        "requirements.txt",
        
        # Módulos del Sistema Multi-Agente (src/)
        "src/gestor_cola.py",
        "src/agente_explorador.py",
        "src/agente_extractor.py",
        "src/gestor_estado.py",
        "src/gestor_casos.py",
        "src/motor_busqueda_web.py",
        "src/orquestador.py",
        "src/logger_config.py",
        "src/auditor.py",
        "src/limpieza.py",
        
        # Bases de datos y archivos de datos
        "data/REPORTE JUICIOS PARA REVISIÓN JULIO.xlsx",
        "data/reporte_trabajo.csv",
        "estado_casos.db"
    ]

    todos_presentes = True
    print("\n--- 1. VERIFICACIÓN DE ARCHIVOS Y COMPONENTES ---")
    for filepath in archivos_requeridos:
        existe = os.path.exists(filepath)
        simbolo = "[OK]" if existe else "[FALTA]"
        tamanio = f"({os.path.getsize(filepath):,} bytes)" if existe else ""
        print(f"{simbolo} {filepath} {tamanio}")
        if not existe:
            todos_presentes = False

    print("\n--- 2. VERIFICACIÓN DE IMPORTACIÓN DE MÓDULOS ---")
    try:
        from src.gestor_cola import GestorCola
        from src.agente_explorador import AgenteExplorador
        from src.agente_extractor import AgenteExtractor
        from src.gestor_estado import GestorEstado
        from src.gestor_casos import GestorCasos
        from src.motor_busqueda_web import BotJudicial
        from src.orquestador import Orquestador
        from src.logger_config import obtener_logger
        from src.auditor import auditar_csv
        from src.limpieza import ejecutar_limpieza
        print("[OK] Todos los módulos de src/ importan sin errores de sintaxis o dependencias.")
    except Exception as e:
        print(f"[ERROR] Fallo al importar módulos: {e}")
        todos_presentes = False

    print("\n--- 3. VERIFICACIÓN DE CONFIGURACIÓN (config.json) ---")
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config_data = json.load(f)
        print(f"[OK] Archivo config.json cargado correctamente. Secciones: {list(config_data.keys())}")
    except Exception as e:
        print(f"[ERROR] Error al leer config.json: {e}")
        todos_presentes = False

    print("\n--- 4. AUDITORÍA DE DATOS DEL LOTE (4,017 REGISTROS) ---")
    from src.auditor import auditar_csv
    res_auditoria = auditar_csv()

    print("\n============================================================")
    if todos_presentes and res_auditoria:
        print("[OK] TODO EL SISTEMA ESTA 100% COMPLETO, INTEGRADO Y OPERATIVO.")
    else:
        print("[ALERTA] SE DETECTARON INCONSISTENCIAS O ARCHIVOS FALTANTES.")
    print("============================================================")

if __name__ == "__main__":
    verificar_todo()
