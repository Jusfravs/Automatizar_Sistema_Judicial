# src/auditor.py
import os
import sys
import pandas as pd
from src.logger_config import obtener_logger

logger = obtener_logger("Auditor")

RUTA_CSV_FINAL = os.path.join("data", "reporte_trabajo.csv")
TOTAL_ESPERADO = 4017

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
        print(f"[*] Filas procesadas en CSV: {total_filas} / Registros esperados: {total_esperado}")
        logger.info(f"Total registros leídos: {total_filas}")

        if total_filas < total_esperado:
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
                print(f"  - {cf}: {completos} registros procesados ({round(completos/total_filas*100, 1)}%)")

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
