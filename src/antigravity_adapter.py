import asyncio
import os
import sys
from pathlib import Path

ANTIGRAVITY_ROOT = Path(
    os.environ.get("ANTIGRAVITY_CLI_PATH", "C:/Users/HP/OneDrive/Desktop/antigravity_cli")
).resolve()

if not ANTIGRAVITY_ROOT.exists():
    # Intento ruta relativa si ambos proyectos son hermanos en el mismo directorio padre.
    posible_root = Path(__file__).resolve().parents[1].parent / "antigravity_cli"
    if posible_root.exists():
        ANTIGRAVITY_ROOT = posible_root.resolve()

ANTIGRAVITY_AVAILABLE = False
ANTIGRAVITY_IMPORT_ERROR = None

if ANTIGRAVITY_ROOT.exists():
    if str(ANTIGRAVITY_ROOT) not in sys.path:
        sys.path.insert(0, str(ANTIGRAVITY_ROOT))

    try:
        from skills import extraer_via_red, normalizar_columnas
        ANTIGRAVITY_AVAILABLE = True
    except ImportError as exc:
        ANTIGRAVITY_IMPORT_ERROR = exc
else:
    ANTIGRAVITY_IMPORT_ERROR = ImportError(
        "No se encontró la carpeta antigravity_cli. Configure ANTIGRAVITY_CLI_PATH o verifique la ruta absoluta."
    )


def _raise_import_error():
    if ANTIGRAVITY_IMPORT_ERROR is not None:
        raise ANTIGRAVITY_IMPORT_ERROR


def extraer_y_normalizar(numero_juicio: str, timeout_ms: int = 15000):
    """Extrae los datos de la causa desde E-SATJE usando el motor antigravity y normaliza el DataFrame."""
    if not numero_juicio:
        return None

    if not ANTIGRAVITY_AVAILABLE:
        _raise_import_error()

    try:
        df = asyncio.run(extraer_via_red(numero_juicio, timeout_ms=timeout_ms))
        if df is None or df.empty:
            return None

        df_normalizado = normalizar_columnas(df)
        return df_normalizado
    except Exception:
        return None


def extraer_y_normalizar_dict(numero_juicio: str, timeout_ms: int = 15000):
    """Retorna el primer registro extraído como dict, o None si no hay datos."""
    try:
        df = extraer_y_normalizar(numero_juicio, timeout_ms=timeout_ms)
    except Exception:
        return None

    if df is None or df.empty:
        return None

    records = df.to_dict(orient="records")
    return records[0] if records else None
