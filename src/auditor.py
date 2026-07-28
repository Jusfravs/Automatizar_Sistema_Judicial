# src/auditor.py
import json
import os
import sys
import pandas as pd
from src.logger_config import obtener_logger

logger = obtener_logger("Auditor")

RUTA_CSV_FINAL = os.path.join("data", "reporte_trabajo.csv")
RUTA_CONFIG = "config.json"


def cargar_total_esperado(ruta_config=RUTA_CONFIG):
    """Load the expected record total from the project configuration."""
    try:
        with open(ruta_config, "r", encoding="utf-8") as archivo_config:
            config = json.load(archivo_config)

        if not isinstance(config, dict):
            raise TypeError("The configuration root must be an object.")

        auditoria = config.get("auditoria", {})
        sistema = config.get("sistema", {})
        if not isinstance(auditoria, dict) or not isinstance(sistema, dict):
            raise TypeError("Configuration sections must be objects.")

        valores_configurados = (
            auditoria.get("total_esperado"),
            sistema.get("total_esperado"),
            config.get("total_esperado"),
        )
        total_esperado = next(
            (valor for valor in valores_configurados if valor is not None),
            None,
        )
        if total_esperado is None:
            logger.warning(
                "Missing 'total_esperado' in %s; count validation will be skipped.",
                ruta_config,
            )
            return None

        total_esperado = int(total_esperado)
        if total_esperado < 0:
            raise ValueError("The expected total cannot be negative.")
        return total_esperado
    except (OSError, json.JSONDecodeError, TypeError, ValueError, AttributeError) as e:
        logger.warning("Could not read 'total_esperado' from %s: %s", ruta_config, e)
        return None


TOTAL_ESPERADO = cargar_total_esperado()

def auditar_csv(ruta_csv=RUTA_CSV_FINAL, total_esperado=TOTAL_ESPERADO):
    """
    Carga el archivo CSV final y ejecuta validaciones de conteo e integridad de columnas críticas.
    """
    print("=" * 60)
    print("[AUDITOR] - VALIDACIÓN DE INTEGRIDAD DEL LOTE PROCESADO")
    print("=" * 60)
    
    if not os.path.exists(ruta_csv):
        mensaje_err = f"El archivo CSV final no existe en la ruta: {ruta_csv}"
        print(f"[ERROR] {mensaje_err}")
        logger.error(mensaje_err)
        return False

    try:
        df = pd.read_csv(ruta_csv, low_memory=False)
        df.columns = [str(c).strip() for c in df.columns]
        
        total_filas = len(df)
        if total_esperado is None:
            print(f"[*] Filas procesadas en CSV: {total_filas} / Registros esperados: no configurado")
        else:
            print(f"[*] Filas procesadas en CSV: {total_filas} / Registros esperados: {total_esperado}")
        logger.info(f"Total registros leídos: {total_filas}")

        if total_esperado is None:
            print("[ADVERTENCIA] No se valido el conteo porque falta 'total_esperado' en config.json.")
        elif total_filas < total_esperado:
            print(f"[ALERTA] El número de filas ({total_filas}) es inferior a los {total_esperado} registros esperados.")
            logger.warning(f"Filas incompletas: {total_filas}/{total_esperado}")
        elif total_filas == total_esperado:
            print(f"[OK] Coincidencia exacta con los {total_esperado} registros esperados.")

        # Identificación de columna de causa
        col_causa = None
        for col in ['NUMERO_JUICIO', 'numero_causa', 'CAUSA', 'JUICIO']:
            if col in df.columns:
                col_causa = col
                break

        if col_causa:
            nulos_causa = df[col_causa].isnull().sum()
            print(f"[*] Campo '{col_causa}': {total_filas - nulos_causa} válidos | {nulos_causa} nulos.")
            if nulos_causa > 0:
                print(f"[ALERTA CRÍTICA] Existen {nulos_causa} registros con número de causa nulo/vacío.")
                logger.warning(f"Valores nulos detectados en '{col_causa}': {nulos_causa}")
        else:
            print("[ALERTA] No se encontró una columna explícita de número de causa/juicio en el CSV.")

        # Verificación de fechas o campos extraídos
        cols_fechas = [c for c in df.columns if 'FECHA' in c.upper() or 'ETAPA' in c.upper()]
        if cols_fechas:
            print("[*] Resumen de columnas de datos procesados:")
            for cf in cols_fechas:
                completos = df[cf].notnull().sum()
                porcentaje = round(completos / total_filas * 100, 1) if total_filas else 0.0
                print(f"  - {cf}: {completos} registros procesados ({porcentaje}%)")

        print("=" * 60)
        print("[OK] Auditoría completada.")
        print("=" * 60)
        return True

    except Exception as e:
        mensaje_exc = f"Excepción durante la auditoría del CSV: {e}"
        print(f"[ERROR] {mensaje_exc}")
        logger.error(mensaje_exc)
        return False

if __name__ == "__main__":
    auditar_csv()
