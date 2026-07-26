# src/orquestador.py
import json
import os
import random
import time
import pandas as pd

from src.gestor_cola import GestorCola
from src.agente_explorador import AgenteExplorador
from src.agente_extractor import AgenteExtractor


class Orquestador:
    """
    Motor de Orquestación Principal Multi-Agente.
    Coordina la cola de tareas SQLite (GestorCola), la descarga web Playwright (AgenteExplorador)
    y el análisis de datos HTML offline (AgenteExtractor).
    """
    def __init__(self, ruta_db="estado_casos.db", dir_temp="temp_htmls", ruta_json="datos_extraidos.json", modo_visible=True):
        self.ruta_json = ruta_json
        self.gestor_cola = GestorCola(ruta_db=ruta_db)
        self.agente_explorador = AgenteExplorador(dir_temp=dir_temp, modo_visible=modo_visible)
        self.agente_extractor = AgenteExtractor()

    def cargar_datos_iniciales(self, ruta_origen):
        """
        Lee el archivo fuente (CSV o Excel) con los registros de causas
        e inyecta los datos en la base de datos SQLite mediante GestorCola.
        """
        print(f"[*] Cargando datos iniciales desde: {ruta_origen}")
        if not os.path.exists(ruta_origen):
            print(f"[ERROR ORQUESTADOR] No se encontró el archivo fuente: {ruta_origen}")
            return False

        try:
            if ruta_origen.endswith(".csv"):
                df = pd.read_csv(ruta_origen, low_memory=False)
            elif ruta_origen.endswith((".xlsx", ".xls")):
                df = pd.read_excel(ruta_origen)
            else:
                raise ValueError("Formato de archivo no soportado. Debe ser .csv o .xlsx")

            self.gestor_cola.poblar_cola(df)
            print("[+] Datos iniciales poblados con éxito en la cola SQLite.")
            return True
        except Exception as e:
            print(f"[ERROR ORQUESTADOR] Error al cargar datos iniciales: {e}")
            return False

    def guardar_resultado_json(self, registro_datos):
        """
        Anexa el diccionario de datos extraídos al archivo local datos_extraidos.json.
        """
        resultados = []
        if os.path.exists(self.ruta_json):
            try:
                with open(self.ruta_json, "r", encoding="utf-8") as f:
                    resultados = json.load(f)
            except Exception:
                resultados = []

        resultados.append(registro_datos)

        with open(self.ruta_json, "w", encoding="utf-8") as f:
            json.dump(resultados, f, ensure_ascii=False, indent=2)

    def iniciar_procesamiento(self, limite_lote=None):
        """
        Motor de ejecución central: consume causas pendientes de la cola,
        descarga el HTML vía AgenteExplorador, analiza datos vía AgenteExtractor,
        actualiza SQLite y guarda resultados en JSON.
        """
        print("\n🚀 [ORQUESTADOR] Iniciando motor de ejecución multi-agente...")
        procesados_lote = 0

        try:
            while True:
                if limite_lote is not None and procesados_lote >= limite_lote:
                    print(f"[*] Límite de lote alcanzado ({limite_lote} registros). Deteniendo orquestación.")
                    break

                # 1. Obtener siguiente causa pendiente
                numero_causa = self.gestor_cola.obtener_siguiente()
                if not numero_causa:
                    print("[+] No hay causas pendientes en la cola. Procesamiento finalizado.")
                    break

                print("==================================================")
                print(f"[*] Procesando causa #{procesados_lote + 1}: {numero_causa}")

                # 2. Descargar HTML pasivo vía AgenteExplorador
                ruta_html = self.agente_explorador.descargar_html_juicio(numero_causa)

                # 3. Validar resultado de descarga
                if not ruta_html or not os.path.exists(ruta_html):
                    print(f"[!] Fallo en la descarga de la causa {numero_causa}. Registrando 'ERROR'.")
                    self.gestor_cola.actualizar_estado(numero_causa, "ERROR")
                    time.sleep(random.uniform(2.0, 4.0))
                    continue

                # 4. Procesar HTML offline vía AgenteExtractor
                datos_extraidos = self.agente_extractor.procesar_archivo_html(ruta_html)
                datos_extraidos["NUMERO_JUICIO"] = numero_causa

                # 5. Guardar resultado en JSON local
                self.guardar_resultado_json(datos_extraidos)

                # 6. Marcar causa como PROCESADO en SQLite
                self.gestor_cola.actualizar_estado(numero_causa, "PROCESADO", ruta_html=ruta_html)
                print(f"[✅] Causa {numero_causa} procesada y guardada con éxito.")

                procesados_lote += 1

                # 7. Retraso obligatorio entre 2 y 4 segundos contra estrangulamiento de red
                retraso = random.uniform(2.0, 4.0)
                print(f"[*] Esperando {retraso:.2f}s para evitar rate-limiting...")
                time.sleep(retraso)

        except KeyboardInterrupt:
            print("\n[!] Ejecución interrumpida por el usuario.")
        finally:
            self.agente_explorador.cerrar()
            print("[*] Orquestador finalizado.")


def cargar_datos_iniciales(ruta_origen):
    """Función de conveniencia para poblar la cola desde un script exterior."""
    gestor = GestorCola()
    if ruta_origen.endswith(".csv"):
        df = pd.read_csv(ruta_origen, low_memory=False)
    else:
        df = pd.read_excel(ruta_origen)
    gestor.poblar_cola(df)


if __name__ == "__main__":
    import sys
    print("=== MOTOR ORQUESTADOR MULTI-AGENTE (E-SATJE) ===")
    
    # Determinar ruta del archivo fuente por defecto o argumento
    ruta_fuente = "data/reporte_trabajo.csv"
    if not os.path.exists(ruta_fuente):
        if os.path.exists("REPORTE JUICIOS PARA REVISIÓN JULIO.xlsx"):
            ruta_fuente = "REPORTE JUICIOS PARA REVISIÓN JULIO.xlsx"

    orquestador = Orquestador(modo_visible=False)
    
    # Cargar datos en SQLite si la cola está vacía
    stats = orquestador.gestor_cola.obtener_estadisticas()
    if not stats or stats.get("PENDIENTE", 0) == 0:
        orquestador.cargar_datos_iniciales(ruta_fuente)

    # Iniciar procesamiento
    limite = int(sys.argv[1]) if len(sys.argv) > 1 else None
    orquestador.iniciar_procesamiento(limite_lote=limite)
