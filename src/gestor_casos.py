# src/gestor_casos.py
import os
import sys
import json
import shutil
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

        self._inicializar_csv()

        try:
            self.df = pd.read_csv(self.ruta_csv, low_memory=False)
            if self.df.empty:
                raise EmptyDataError("El archivo CSV está completamente vacío.")
        except EmptyDataError:
            logger.critical(
                "El archivo CSV está vacío o corrupto. "
                "Intentando autoreparar desde el Excel original..."
            )
            if os.path.exists(self.ruta_csv):
                try:
                    os.remove(self.ruta_csv)
                except Exception:
                    pass
            self._inicializar_csv()
            try:
                self.df = pd.read_csv(self.ruta_csv, low_memory=False)
            except Exception:
                logger.critical("No se pudo restaurar la base de datos CSV. Verifique el Excel de origen.")
                sys.exit(1)
        except FileNotFoundError:
            logger.critical("No se encontró el CSV en '%s'. Creando desde Excel...", self.ruta_csv)
            self._inicializar_csv()
            try:
                self.df = pd.read_csv(self.ruta_csv, low_memory=False)
            except Exception:
                logger.critical("No se pudo crear la base de datos CSV en '%s'.", self.ruta_csv)
                sys.exit(1)
        except Exception as e:
            logger.critical("Error inesperado al cargar la base de datos CSV: %s", e)
            sys.exit(1)

        # Normalizar cabeceras (limpia espacios y fuerza mayúsculas)
        self.df.columns = self.df.columns.astype(str).str.strip().str.upper()

        if 'SUCURSAL' not in self.df.columns and os.path.exists(self.ruta_excel):
            logger.warning("'SUCURSAL' no encontrada en CSV. Regenerando CSV desde Excel...")
            if os.path.exists(self.ruta_csv):
                try:
                    os.remove(self.ruta_csv)
                except Exception:
                    pass
            self._inicializar_csv()
            self.df = pd.read_csv(self.ruta_csv, low_memory=False)
            self.df.columns = self.df.columns.astype(str).str.strip().str.upper()

    def _inicializar_csv(self):
        """CREATE: Genera el CSV de trabajo desde el Excel original si no existe."""
        if not os.path.exists(self.ruta_csv) and os.path.exists(self.ruta_excel):
            logger.info("Inicializando base de datos CSV desde Excel...")
            df_excel = pd.read_excel(self.ruta_excel, sheet_name=self.hoja, header=0)
            df_excel.columns = df_excel.columns.astype(str).str.strip().str.upper()
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
        
        suc = str(self.filtros.get('sucursal', '')).strip().upper()
        ofi = str(self.filtros.get('oficina', '')).strip().upper()
        est = str(self.filtros.get('estado_judicial', '')).strip().upper()

        df_filtrado = self.df[
            (self.df['SUCURSAL'].astype(str).str.strip().str.upper() == suc) &
            (self.df['OFICINA'].astype(str).str.strip().str.upper() == ofi) &
            (self.df[col_estado].astype(str).str.strip().str.upper() == est)
        ]

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
        logger.info("Exportando informe final a: %s", self.ruta_final)
        self.df.to_excel(self.ruta_final, index=False, sheet_name=self.hoja)
        logger.info("¡Archivo Excel final generado exitosamente!")
