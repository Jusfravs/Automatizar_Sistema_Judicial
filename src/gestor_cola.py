# src/gestor_cola.py
import sqlite3
import pandas as pd
from src.logger_config import obtener_logger

logger = obtener_logger("GestorCola")


class GestorCola:
    """
    Motor de Estado y Cola de Tareas en SQLite para desacoplar el flujo de ejecución.
    """
    def __init__(self, ruta_db="estado_casos.db"):
        self.ruta_db = ruta_db
        self._inicializar_tabla()

    def _get_connection(self):
        """Devuelve una nueva conexión a SQLite con timeout de 30s."""
        return sqlite3.connect(self.ruta_db, timeout=30.0)

    def _inicializar_tabla(self):
        """Crea la tabla juicios si no existe."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS juicios (
                    numero_causa TEXT PRIMARY KEY,
                    estado TEXT DEFAULT 'PENDIENTE',
                    ruta_html TEXT NULL,
                    reintentos INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def poblar_cola(self, df_o_lista):
        """
        Inserta masivamente registros en la tabla juicios con INSERT OR IGNORE
        para evitar duplicar registros existentes.
        Acepta un DataFrame de Pandas o una lista de números de causa.
        """
        if isinstance(df_o_lista, pd.DataFrame):
            col_causa = 'NUMERO_JUICIO' if 'NUMERO_JUICIO' in df_o_lista.columns else df_o_lista.columns[0]
            causas = df_o_lista[col_causa].dropna().astype(str).str.strip().tolist()
        elif isinstance(df_o_lista, (list, tuple)):
            causas = [str(c).strip() for c in df_o_lista if c]
        else:
            raise ValueError("El parámetro 'df_o_lista' debe ser un DataFrame de Pandas o una lista.")

        registros = [(c,) for c in causas if c]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT OR IGNORE INTO juicios (numero_causa, estado, reintentos) VALUES (?, 'PENDIENTE', 0)",
                registros
            )
            conn.commit()
            logger.info(f"Cola poblada/actualizada. Total de causas procesadas en inserción: {len(registros)}")

    def obtener_siguiente(self):
        """
        Método transaccional atómico:
        Obtiene la primera causa con estado 'PENDIENTE' y actualiza su estado a 'EN_PROCESO'.
        Retorna el numero_causa o None si no hay causas pendientes.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT numero_causa FROM juicios WHERE estado = 'PENDIENTE' LIMIT 1")
            row = cursor.fetchone()
            if row:
                numero_causa = row[0]
                cursor.execute(
                    "UPDATE juicios SET estado = 'EN_PROCESO' WHERE numero_causa = ?",
                    (numero_causa,)
                )
                conn.commit()
                return numero_causa
            return None

    def actualizar_estado(self, numero_causa, nuevo_estado, ruta_html=None):
        """
        Actualiza el estado de una causa y opcionalmente su ruta_html.
        """
        causa_str = str(numero_causa).strip()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if ruta_html is not None:
                cursor.execute(
                    "UPDATE juicios SET estado = ?, ruta_html = ? WHERE numero_causa = ?",
                    (nuevo_estado, ruta_html, causa_str)
                )
            else:
                cursor.execute(
                    "UPDATE juicios SET estado = ? WHERE numero_causa = ?",
                    (nuevo_estado, causa_str)
                )
            conn.commit()

    def obtener_estadisticas(self):
        """Retorna un diccionario con el conteo de registros agrupados por estado."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT estado, COUNT(*) FROM juicios GROUP BY estado")
            rows = cursor.fetchall()
            return dict(rows)

    def reiniciar_errores(self, max_reintentos=3):
        """
        Cambia el estado de 'ERROR' a 'PENDIENTE' e incrementa en 1 la columna 'reintentos'
        para todos los registros con reintentos < max_reintentos.
        Retorna la cantidad de filas modificadas.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE juicios
                SET estado = 'PENDIENTE', reintentos = reintentos + 1
                WHERE estado = 'ERROR' AND reintentos < ?
                """,
                (max_reintentos,)
            )
            conn.commit()
            filas_modificadas = cursor.rowcount
            if filas_modificadas > 0:
                logger.info(f"Reiniciados {filas_modificadas} registros de 'ERROR' a 'PENDIENTE'.")
            return filas_modificadas
