# src/gestor_estado.py
import json
import os
import pandas as pd
from src.logger_config import obtener_logger

logger = obtener_logger("GestorEstado")


class GestorEstado:
    """
    Gestor de Estado (Pandas): Procesa y normaliza los resultados extraídos
    hacia su formato tabular final (.csv y .xlsx).
    """
    def __init__(self):
        pass

    def generar_reporte_final(self, ruta_json="datos_extraidos.json", ruta_salida_csv="data/reporte_trabajo_final.csv"):
        """
        Lee el archivo JSON con los datos extraídos por AgenteExtractor,
        aplana la estructura usando pd.json_normalize, limpia nulos
        y exporta la tabla final a CSV (y Excel opcional) en UTF-8.
        """
        logger.info(f"Compilando reporte final desde: {ruta_json}")
        if not os.path.exists(ruta_json):
            logger.error(f"No existe el archivo de resultados: {ruta_json}")
            return None

        try:
            with open(ruta_json, "r", encoding="utf-8") as f:
                datos = json.load(f)

            if not datos:
                logger.warning("El archivo JSON está vacío. No hay datos para procesar.")
                return None

            # Aplanar estructura JSON
            df = pd.json_normalize(datos)

            # Reordenar columnas clave si existen
            columnas_deseadas = [
                "NUMERO_JUICIO",
                "FECHA INICIO JUICIO",
                "FECHA INICIAL FASE ACTUAL",
                "ETAPA_PROCESAL",
                "FASE_PROCESAL",
                "HISTORIAL_ACTUACIONES"
            ]

            # Mantener columnas existentes
            columnas_presentes = [col for col in columnas_deseadas if col in df.columns]
            otras_columnas = [col for col in df.columns if col not in columnas_presentes]
            df = df[columnas_presentes + otras_columnas]

            # Limpiar valores nulos
            df = df.fillna("")

            # Convertir listas/diccionarios anidados a strings para exportación limpia en CSV
            if "HISTORIAL_ACTUACIONES" in df.columns:
                df["HISTORIAL_ACTUACIONES"] = df["HISTORIAL_ACTUACIONES"].apply(
                    lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else str(x)
                )

            # Crear directorio de salida si no existe
            dir_salida = os.path.dirname(ruta_salida_csv)
            if dir_salida:
                os.makedirs(dir_salida, exist_ok=True)

            # Exportar a CSV UTF-8 sin índice
            df.to_csv(ruta_salida_csv, index=False, encoding="utf-8")
            logger.info(f"Reporte final generado exitosamente en CSV: {ruta_salida_csv} ({len(df)} registros)")

            return df

        except Exception as e:
            logger.error(f"Fallo al generar reporte final: {e}")
            return None
