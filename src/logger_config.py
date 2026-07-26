# src/logger_config.py
import logging
import sys

LOG_FILE = "ejecucion_produccion.log"


def obtener_logger(nombre_modulo):
    """
    Configura y devuelve un logger con salida a archivo local ejecucion_produccion.log
    y consola (StreamHandler) con formato estricto.
    """
    logger = logging.getLogger(nombre_modulo)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # Formato estricto: timestamp, nivel de severidad, módulo de origen, mensaje
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # FileHandler con codificación UTF-8
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        # ConsoleHandler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger
