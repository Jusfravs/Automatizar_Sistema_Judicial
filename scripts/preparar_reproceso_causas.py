"""Limpia un conjunto explícito de causas para volver a consultarlas en e-SATJE.

Conserva los datos base del reporte, respalda SQLite/CSV/Excel, elimina la
evidencia extraída anterior y devuelve las causas a PENDIENTE.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.gestor_casos import GestorCasos


CAUSAS_QUITO_AUDITADAS = (
    "17230-2016-17734", "17233-2017-00375", "17230-2015-17343",
    "17233-2024-01557", "17230-2016-03164", "17230-2016-05679",
    "17230-2016-04908", "17233-2024-05000", "17233-2020-01411",
    "17307-2014-0329", "17315-2024-00284", "17233-2025-11175",
    "17230-2016-11413", "17233-2022-05783", "17230-2015-15007",
    "17233-2018-03830", "17233-2017-02258", "17233-2022-06854",
    "17233-2024-07607", "17233-2019-00127", "17233-2025-09411",
    "17233-2025-09167", "17230-2015-13845", "17233-2025-06383",
    "17233-2017-00211", "17230-2015-13843", "17233-2025-11170",
    "17233-2025-11354", "17231-2025-00028",
)

CAMPOS_LIMPIAR = (
    "ETAPA_PROCESAL", "FASE_PROCESAL", "FECHA INICIAL FASE ACTUAL",
    "HISTORIAL_ACTUACIONES", "ULTIMA ETAPA", "ULTIMA FASE",
    "FECHA FIN ULTIMA FASE", "ETAPA ACTUAL", "FASE ACTUAL",
    "FECHA INICIO FASE ACTUAL",
)


def limpiar_comentario_automatico(valor):
    """Elimina la marca creada por el bot, sin borrar una nota humana.

    ``main.py`` usa el prefijo ``REVISION MANUAL:`` para errores t\u00e9cnicos.
    Al devolver una causa a PENDIENTE esa marca deja de ser vigente; en
    cambio, cualquier comentario con otro origen se conserva.
    """
    texto = str(valor or "")
    return "" if texto.strip().upper().startswith("REVISION MANUAL:") else texto


def normalizar_causa(valor):
    return "".join(c for c in str(valor or "") if c.isdigit())


def ruta_configurada(config_path, valor):
    ruta = Path(valor)
    return ruta if ruta.is_absolute() else (config_path.parent / ruta).resolve()


def respaldar(ruta, directorio, marca):
    if not ruta.exists():
        raise FileNotFoundError(ruta)
    destino = directorio / f"{ruta.stem}_antes_reproceso_{marca}{ruta.suffix}"
    shutil.copy2(ruta, destino)
    return destino


def verificar_archivos_libres(rutas):
    """Falla antes de tocar SQLite si Excel mantiene un bloqueo exclusivo."""
    for ruta in rutas:
        try:
            with ruta.open("r+b"):
                pass
        except PermissionError as exc:
            raise PermissionError(
                f"ARCHIVO_BLOQUEADO_CIERRE_EXCEL_O_EDITOR:{ruta}"
            ) from exc


def limpiar(config_path, causas):
    config_path = Path(config_path).resolve()
    repo = GestorCasos(str(config_path))
    rutas = repo.config.get("rutas", {})
    ruta_db = ruta_configurada(config_path, rutas.get("archivo_db", "estado_casos.db"))
    ruta_csv = Path(repo.ruta_csv).resolve()
    ruta_excel = Path(repo.ruta_final).resolve()
    causas = tuple(dict.fromkeys(str(c).strip() for c in causas if str(c).strip()))
    causas_norm = {normalizar_causa(c): c for c in causas}

    if len(causas_norm) != len(causas):
        raise ValueError("CAUSAS_DUPLICADAS_O_INVALIDAS")
    directorio = ruta_db.parent / "backups"
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    directorio.mkdir(parents=True, exist_ok=True)
    verificar_archivos_libres((ruta_csv, ruta_excel))

    conexion = sqlite3.connect(ruta_db, timeout=30.0)
    try:
        placeholders = ",".join("?" for _ in causas)
        filas = conexion.execute(
            f"SELECT numero_causa, estado FROM juicios WHERE numero_causa IN ({placeholders})",
            causas,
        ).fetchall()
        encontradas = {normalizar_causa(c): (c, estado) for c, estado in filas}
        faltantes = sorted(set(causas_norm) - set(encontradas))
        if faltantes:
            raise LookupError(f"CAUSAS_AUSENTES_SQLITE:{faltantes}")
        en_proceso = [c for c, estado in encontradas.values() if estado == "EN_PROCESO"]
        if en_proceso:
            raise RuntimeError(f"CAUSAS_EN_PROCESO:{en_proceso}")

        respaldos = [respaldar(ruta_csv, directorio, marca), respaldar(ruta_excel, directorio, marca)]
        respaldo_db = directorio / f"{ruta_db.stem}_antes_reproceso_{marca}.db"
        with sqlite3.connect(respaldo_db) as copia:
            conexion.backup(copia)
        respaldos.append(respaldo_db)

        mascara = repo.df["NUMERO_JUICIO"].map(normalizar_causa)
        indices = repo.df.index[mascara.isin(causas_norm)]
        causas_en_csv = set(mascara.loc[indices])
        faltantes_csv = sorted(set(causas_norm) - causas_en_csv)
        if faltantes_csv:
            raise LookupError(f"CAUSAS_AUSENTES_CSV:{faltantes_csv}")
        # Una misma causa puede figurar en varias filas por créditos o carteras
        # distintas. Se limpia la clasificación en cada fila, preservando sus
        # datos base y comentarios humanos, mientras SQLite se reinicia una vez
        # por número de causa.
        for indice in indices:
            for campo in CAMPOS_LIMPIAR:
                if campo in repo.df.columns:
                    repo.df.at[indice, campo] = ""
            if "COMENTARIO_ULTIMO" in repo.df.columns:
                repo.df.at[indice, "COMENTARIO_ULTIMO"] = (
                    limpiar_comentario_automatico(
                        repo.df.at[indice, "COMENTARIO_ULTIMO"]
                    )
                )

        conexion.execute("BEGIN IMMEDIATE")
        conexion.execute(
            f"DELETE FROM resultados_expediente WHERE numero_causa IN ({placeholders})",
            causas,
        )
        conexion.execute(
            f"UPDATE juicios SET estado='PENDIENTE', reintentos=0, ruta_html=NULL "
            f"WHERE numero_causa IN ({placeholders})",
            causas,
        )
        for causa in causas:
            conexion.execute(
                "INSERT INTO eventos_extraccion (numero_causa, origen, detalle) VALUES (?, ?, ?)",
                (causa, "REPROCESO_PREPARADO", "Evidencia extraida limpiada; causa devuelta a PENDIENTE para nueva consulta."),
            )

        if not repo.guardar():
            raise RuntimeError("PERSISTENCIA_ERROR:CSV")
        repo.exportar_excel()
        conexion.commit()
    except Exception:
        conexion.rollback()
        # Restaurar los reportes si la escritura de formatos falla antes del
        # commit SQLite; los respaldos siguen disponibles para auditoria.
        for respaldo in locals().get("respaldos", []):
            if respaldo.suffix.lower() in {".csv", ".xlsx"}:
                destino = ruta_csv if respaldo.suffix.lower() == ".csv" else ruta_excel
                shutil.copy2(respaldo, destino)
        raise
    finally:
        conexion.close()

    return {
        "causas_limpiadas": len(causas),
        "estado_nuevo": "PENDIENTE",
        "resultados_sqlite_eliminados": len(causas),
        "respaldos": [str(r.resolve()) for r in respaldos],
        "sqlite": str(ruta_db),
        "csv": str(ruta_csv),
        "excel": str(ruta_excel),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--causa", action="append", dest="causas")
    parser.add_argument("--auditoria-quito", action="store_true")
    args = parser.parse_args()
    causas = CAUSAS_QUITO_AUDITADAS if args.auditoria_quito else (args.causas or [])
    if not causas:
        parser.error("indique --auditoria-quito o al menos un --causa")
    print(json.dumps(limpiar(args.config, causas), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
