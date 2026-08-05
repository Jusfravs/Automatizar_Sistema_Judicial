# src/gestor_casos.py
import os
import sys
import json
import shutil
from datetime import datetime
import pandas as pd
from pandas.errors import EmptyDataError
from src.logger_config import obtener_logger

logger = obtener_logger("GestorCasos")

class GestorCasos:
    """
    Repositorio CRUD de datos para la lectura, actualización y persistencia del reporte.
    """
    def __init__(self, ruta_config="config.json"):
        with open(ruta_config, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        rutas = self.config.get('rutas', {})
        self.ruta_csv = rutas.get('archivo_csv', 'data/reporte_trabajo.csv')
        self.ruta_excel = rutas.get('archivo_origen', 'data/REPORTE JUICIOS PARA REVISIÓN JULIO.xlsx')
        self.ruta_final = rutas.get('archivo_excel_final', 'data/REPORTE_PROCESADO_FINAL.xlsx')
        self.hoja = rutas.get('hoja_lectura', 'migrado')
        self.filtros = self.config.get('filtros_activos', {})

        # Cargar CSV existente si existe y es válido
        if os.path.exists(self.ruta_csv):
            try:
                self.df = pd.read_csv(self.ruta_csv, low_memory=False)
                self.df.columns = self.df.columns.astype(str).str.strip().str.upper()
                if self.df.empty:
                    raise EmptyDataError("CSV vacío")
            except Exception as e:
                logger.warning("No se pudo cargar el CSV existente ('%s'): %s. Regenerando desde Excel...", self.ruta_csv, e)
                self._inicializar_csv(forzar=True)
                self.df = pd.read_csv(self.ruta_csv, low_memory=False)
                self.df.columns = self.df.columns.astype(str).str.strip().str.upper()
        else:
            logger.info("CSV no encontrado. Creando desde Excel original...")
            self._inicializar_csv(forzar=True)
            self.df = pd.read_csv(self.ruta_csv, low_memory=False)
            self.df.columns = self.df.columns.astype(str).str.strip().str.upper()

        # Si faltan columnas esenciales o filas incompletas, sincronizar una sola vez
        if ('SUCURSAL' not in self.df.columns or len(self.df) < 1000) and os.path.exists(self.ruta_excel):
            logger.info("El CSV tiene %s registros. Sincronizando datos con el Excel completo...", len(self.df))
            self._inicializar_csv(forzar=True)
            self.df = pd.read_csv(self.ruta_csv, low_memory=False)
            self.df.columns = self.df.columns.astype(str).str.strip().str.upper()

    def _cargar_excel_robusto(self):
        """Carga el Excel usando una copia sombra para evitar bloqueos si está abierto en Excel, e infiere el header."""
        import subprocess
        excel_path = os.path.abspath(self.ruta_excel)
        temp_path = os.path.abspath(os.path.join(os.path.dirname(self.ruta_excel), "_temp_excel_shadow.xlsx"))
        
        # Copiar con PowerShell para evitar error de bloqueo de archivo exclusivo en Windows
        cmd = f'powershell -Command "Copy-Item \'{excel_path}\' \'{temp_path}\' -Force"'
        subprocess.run(cmd, shell=True, capture_output=True)

        archivo_lectura = temp_path if os.path.exists(temp_path) else self.ruta_excel

        try:
            for h in [0, 1]:
                try:
                    df = pd.read_excel(archivo_lectura, sheet_name=self.hoja, header=h)
                    df.columns = df.columns.astype(str).str.strip().str.upper()
                    if 'SUCURSAL' in df.columns or 'CODIGO_JUICIO' in df.columns:
                        logger.info("Excel cargado correctamente detectando header=%s (%s filas).", h, len(df))
                        return df
                except Exception:
                    continue
            raise ValueError("No se pudo detectar la cabecera correcta en el archivo Excel.")
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def _inicializar_csv(self, forzar=False):
        """CREATE: Genera o combina el CSV de trabajo desde el Excel original."""
        if not os.path.exists(self.ruta_excel):
            return

        if os.path.exists(self.ruta_csv) and not forzar:
            return

        logger.info("Inicializando/sincronizando base de datos CSV desde Excel...")
        df_excel = self._cargar_excel_robusto()

        if os.path.exists(self.ruta_csv):
            try:
                df_existente = pd.read_csv(self.ruta_csv, low_memory=False)
                df_existente.columns = df_existente.columns.astype(str).str.strip().str.upper()
                if 'CODIGO_JUICIO' in df_existente.columns and 'CODIGO_JUICIO' in df_excel.columns:
                    logger.info("Combinando datos existentes del CSV con la base completa del Excel...")
                    df_merged = df_existente.set_index('CODIGO_JUICIO').combine_first(df_excel.set_index('CODIGO_JUICIO')).reset_index()
                    df_merged.to_csv(self.ruta_csv, index=False, encoding='utf-8-sig')
                    return
            except Exception as e:
                logger.warning("No se pudo combinar el CSV existente, se creará uno nuevo: %s", e)

        df_excel.to_csv(self.ruta_csv, index=False, encoding='utf-8-sig')

    def obtener_casos_pendientes(self):
        """READ: Obtiene la lista de números de juicio que cumplen con los filtros."""
        logger.debug("Columnas disponibles: %s", self.df.columns.tolist())
        columna_configurada = str(self.filtros.get('columna_estado_judicial', '')).strip().upper()
        if columna_configurada:
            if columna_configurada not in self.df.columns:
                raise KeyError(
                    f"La columna configurada para estado judicial '{columna_configurada}' no existe en el CSV."
                )
            col_estado = columna_configurada
            logger.info("Usando columna configurada para estado judicial: '%s'.", col_estado)
        elif 'ESTADO' in self.df.columns:
            col_estado = 'ESTADO'
        elif 'ESTADO.1' in self.df.columns:
            col_estado = 'ESTADO.1'
            logger.warning("Se usará la columna de respaldo 'ESTADO.1'.")
        else:
            raise KeyError("No se encontro una columna 'ESTADO' ni 'ESTADO.1' en el CSV.")
        
        mask = pd.Series(True, index=self.df.index)

        suc = str(self.filtros.get('sucursal', '') or '').strip().upper()
        if suc and suc not in ('TODAS', 'TODOS', 'ALL', 'NONE'):
            mask &= (self.df['SUCURSAL'].astype(str).str.strip().str.upper() == suc)

        ofi = str(self.filtros.get('oficina', '') or '').strip().upper()
        if ofi and ofi not in ('TODAS', 'TODOS', 'ALL', 'NONE'):
            mask &= (self.df['OFICINA'].astype(str).str.strip().str.upper() == ofi)

        est = str(self.filtros.get('estado_judicial', '') or '').strip().upper()
        if est and est not in ('TODAS', 'TODOS', 'ALL', 'NONE'):
            mask &= (self.df[col_estado].astype(str).str.strip().str.upper() == est)

        df_filtrado = self.df[mask]

        casos = df_filtrado['NUMERO_JUICIO'].dropna().astype(str).str.strip().tolist()

        # Aplicar punto de partida si fue especificado
        inicio = self.filtros.get('inicio_desde_juicio')
        if inicio:
            inicio_limpio = str(inicio).replace("-", "").strip()
            idx = next((i for i, c in enumerate(casos) if str(c).replace("-", "").strip() == inicio_limpio), None)
            if idx is not None:
                logger.info("Reanudando desde causa '%s' (Caso #%s de %s).", inicio, idx + 1, len(casos))
                casos = casos[idx:]

        return casos

    def actualizar_caso(self, numero_juicio, datos):
        """UPDATE: Inyecta en la fila correspondiente los datos extraídos."""
        numero_juicio_normalizado = str(numero_juicio).strip().upper()
        mask = (
            self.df['NUMERO_JUICIO'].astype(str).str.strip().str.upper()
            == numero_juicio_normalizado
        )
        if mask.any():
            idx = self.df[mask].index[0]
            for col, val in datos.items():
                if val is not None:
                    if col not in self.df.columns:
                        self.df[col] = None
                    self.df.at[idx, col] = val
            return True
        return False

    def guardar(self):
        """SAVE: Persiste los cambios en la base CSV de trabajo. Retorna True en éxito."""
        if os.path.isfile(self.ruta_csv):
            ruta_backup = f"{self.ruta_csv}.bak"
            try:
                shutil.copy2(self.ruta_csv, ruta_backup)
                logger.debug("Respaldo del CSV creado en: %s", ruta_backup)
            except OSError as e:
                logger.error("No se pudo crear respaldo del CSV: %s", e)
                return False

        try:
            self.df.to_csv(self.ruta_csv, index=False, encoding='utf-8-sig')
            return True
        except Exception as e:
            logger.error("No se pudo guardar CSV: %s", e)
            return False

    def exportar_excel(self):
        """EXPORT: Genera el Excel .xlsx consolidado final."""
        # Calcular días en fase actual antes de exportar
        self.calcular_dias_fase_actual()
        logger.info("Exportando informe final a: %s", self.ruta_final)
        self.df.to_excel(self.ruta_final, index=False, sheet_name=self.hoja)
        logger.info("¡Archivo Excel final generado exitosamente!")

    def calcular_dias_fase_actual(self):
        """
        Calcula la columna 'DIAS EN LA FASE ACTUAL' como la diferencia en días calendario
        entre la fecha actual y 'FECHA INICIAL FASE ACTUAL'.
        Soporta formatos dd/mm/yyyy y yyyy-mm-dd.
        """
        col_fecha = 'FECHA INICIAL FASE ACTUAL'
        col_dias = 'DIAS EN LA FASE ACTUAL'

        if col_fecha not in self.df.columns:
            logger.warning("Columna '%s' no encontrada. No se calculará '%s'.", col_fecha, col_dias)
            return

        if col_dias not in self.df.columns:
            self.df[col_dias] = None

        hoy = datetime.now()
        conteo = 0

        for idx, valor in self.df[col_fecha].items():
            if pd.isna(valor) or str(valor).strip() == "":
                continue

            fecha_str = str(valor).strip()
            fecha_parsed = None

            # Intentar formato dd/mm/yyyy (formato del portal e-SATJE)
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                try:
                    fecha_parsed = datetime.strptime(fecha_str, fmt)
                    break
                except ValueError:
                    continue

            if fecha_parsed:
                dias = (hoy - fecha_parsed).days
                self.df.at[idx, col_dias] = max(0, dias)
                conteo += 1

        logger.info("'%s' calculado para %s registros.", col_dias, conteo)

