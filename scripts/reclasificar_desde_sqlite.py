"""Recalcula fases desde historiales persistidos, sin consultar el portal."""

import argparse
import json
import shutil
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.agente_extractor import MotorInferenciaProcesal
from src.gestor_casos import GestorCasos


CAMPOS_CLASIFICACION = (
    "ETAPA_PROCESAL",
    "FASE_PROCESAL",
    "FECHA INICIAL FASE ACTUAL",
    "ULTIMA ETAPA",
    "ULTIMA FASE",
    "FECHA FIN ULTIMA FASE",
    "ETAPA ACTUAL",
    "FASE ACTUAL",
    "FECHA INICIO FASE ACTUAL",
)

CAMPOS_FECHA = {
    "FECHA INICIAL FASE ACTUAL",
    "FECHA FIN ULTIMA FASE",
    "FECHA INICIO FASE ACTUAL",
}


def _campos_desde_inferencia(inferencia):
    fecha = inferencia.get("FECHA_FIN_ULTIMA_FASE")
    return {
        "ETAPA_PROCESAL": inferencia.get("ULTIMA_ETAPA"),
        "FASE_PROCESAL": inferencia.get("ULTIMA_FASE"),
        "FECHA INICIAL FASE ACTUAL": fecha,
        "ULTIMA ETAPA": inferencia.get("ULTIMA_ETAPA"),
        "ULTIMA FASE": inferencia.get("ULTIMA_FASE"),
        "FECHA FIN ULTIMA FASE": fecha,
        "ETAPA ACTUAL": (
            inferencia.get("ETAPA_ACTUAL")
            or inferencia.get("ULTIMA_ETAPA")
        ),
        "FASE ACTUAL": (
            inferencia.get("FASE_ACTUAL")
            or inferencia.get("ULTIMA_FASE")
        ),
        "FECHA INICIO FASE ACTUAL": fecha,
    }


def _reclasificar_datos(datos):
    actuaciones = datos.get("HISTORIAL_ACTUACIONES") or []
    if not actuaciones:
        return None

    inferencia = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
    if not inferencia or not inferencia.get("ULTIMA_ETAPA"):
        return None

    anteriores = {campo: datos.get(campo) for campo in CAMPOS_CLASIFICACION}
    nuevos = _campos_desde_inferencia(inferencia)
    datos.update(nuevos)

    mensaje = inferencia.get("MENSAJE_ESPECIAL")
    if mensaje:
        datos["COMENTARIO_ULTIMO"] = mensaje

    return anteriores, nuevos


def _fecha_canonica(valor):
    if valor is None or str(valor).strip() == "":
        return None
    texto = str(valor).strip()
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto[:10], formato).date().isoformat()
        except ValueError:
            continue
    return texto


def _campos_equivalentes(anteriores, nuevos):
    for campo in CAMPOS_CLASIFICACION:
        anterior = anteriores.get(campo)
        nuevo = nuevos.get(campo)
        if campo in CAMPOS_FECHA:
            if _fecha_canonica(anterior) != _fecha_canonica(nuevo):
                return False
        elif anterior != nuevo:
            return False
    return True


def _ruta_configurada(config_path, valor):
    ruta = Path(valor)
    if ruta.is_absolute():
        return ruta
    return (config_path.parent / ruta).resolve()


def _respaldar_archivo(ruta, directorio, marca):
    if not ruta.exists():
        return None
    directorio.mkdir(parents=True, exist_ok=True)
    destino = directorio / f"{ruta.stem}_antes_reclasificacion_{marca}{ruta.suffix}"
    shutil.copy2(ruta, destino)
    return destino


def _respaldar_sqlite(conexion, ruta_destino):
    ruta_destino.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(ruta_destino) as respaldo:
        conexion.backup(respaldo)


def _normalizar_causa(valor):
    return "".join(caracter for caracter in str(valor or "").strip() if caracter.isdigit())


def _causas_por_sucursal(repo, sucursal):
    if not sucursal:
        return None
    columna_sucursal = "SUCURSAL"
    if columna_sucursal not in repo.df.columns:
        raise KeyError("COLUMNA_SUCURSAL_AUSENTE")

    mascara = repo.df[columna_sucursal].fillna("").astype(str).str.strip().str.upper().eq(
        str(sucursal).strip().upper()
    )
    filtros = repo.config.get("filtros_activos", {})
    columna_estado = str(filtros.get("columna_estado_judicial", "")).strip().upper()
    estado = str(filtros.get("estado_judicial", "")).strip().upper()
    if columna_estado and estado and columna_estado in repo.df.columns:
        mascara &= repo.df[columna_estado].fillna("").astype(str).str.strip().str.upper().eq(estado)

    return {_normalizar_causa(causa) for causa in repo.df.loc[mascara, "NUMERO_JUICIO"] if _normalizar_causa(causa)}


def reclasificar(ruta_config, aplicar=False, sucursal=None, causas=None):
    config_path = Path(ruta_config).resolve()
    repo = GestorCasos(str(config_path))
    causas_alcance = _causas_por_sucursal(repo, sucursal)
    causas_solicitadas = {
        _normalizar_causa(causa) for causa in (causas or [])
        if _normalizar_causa(causa)
    }
    if causas_solicitadas:
        if causas_alcance is None:
            causas_alcance = causas_solicitadas
        else:
            causas_alcance &= causas_solicitadas
    rutas = repo.config.get("rutas", {})
    ruta_db = _ruta_configurada(
        config_path, rutas.get("archivo_db", "estado_casos.db")
    )

    conexion = sqlite3.connect(ruta_db, timeout=30.0)
    registros = conexion.execute(
        """
        SELECT r.numero_causa, r.datos_json
        FROM resultados_expediente AS r
        INNER JOIN juicios AS j ON j.numero_causa = r.numero_causa
        WHERE j.estado IN ('PROCESADO', 'PARCIAL')
        ORDER BY r.numero_causa
        """
    ).fetchall()

    cambios = []
    actualizaciones = []
    resultados_evaluados = 0
    for causa, datos_json in registros:
        if causas_alcance is not None and _normalizar_causa(causa) not in causas_alcance:
            continue
        resultados_evaluados += 1

        resultado = json.loads(datos_json)
        datos = resultado.get("datos") or {}
        reclasificacion = _reclasificar_datos(datos)
        if reclasificacion is None:
            continue

        anteriores, nuevos = reclasificacion
        if not _campos_equivalentes(anteriores, nuevos):
            cambios.append({
                "causa": causa,
                "fase_anterior": anteriores.get("ULTIMA FASE"),
                "fase_nueva": nuevos.get("ULTIMA FASE"),
                "fecha_anterior": anteriores.get("FECHA FIN ULTIMA FASE"),
                "fecha_nueva": nuevos.get("FECHA FIN ULTIMA FASE"),
            })

        for carpeta in resultado.get("resultados_carpetas") or []:
            datos_carpeta = carpeta.get("datos") or {}
            _reclasificar_datos(datos_carpeta)

        actualizaciones.append((
            json.dumps(resultado, ensure_ascii=False),
            causa,
            nuevos,
        ))

    resumen = {
        "resultados_evaluados": resultados_evaluados,
        "clasificaciones_modificadas": len(cambios),
        "transiciones": dict(Counter(
            f"{c['fase_anterior']} -> {c['fase_nueva']}" for c in cambios
        )),
        "cambios": cambios,
    }
    if sucursal:
        resumen["sucursal"] = str(sucursal).strip().upper()
    if causas_solicitadas:
        resumen["causas_solicitadas"] = sorted(causas_solicitadas)

    if not aplicar:
        conexion.close()
        return resumen

    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    directorio_backup = Path(repo.ruta_final).resolve().parent / "backups"
    _respaldar_sqlite(
        conexion,
        directorio_backup / f"{ruta_db.stem}_antes_reclasificacion_{marca}.db",
    )
    _respaldar_archivo(Path(repo.ruta_csv), directorio_backup, marca)
    _respaldar_archivo(Path(repo.ruta_final), directorio_backup, marca)

    try:
        conexion.execute("BEGIN IMMEDIATE")
        for datos_json, causa, nuevos in actualizaciones:
            conexion.execute(
                """
                UPDATE resultados_expediente
                SET datos_json = ?, actualizado_en = CURRENT_TIMESTAMP
                WHERE numero_causa = ?
                """,
                (datos_json, causa),
            )
            if not repo.actualizar_caso(causa, nuevos):
                raise LookupError(f"CAUSA_NO_ENCONTRADA_EN_CSV:{causa}")

        if not repo.guardar():
            raise RuntimeError("PERSISTENCIA_ERROR:CSV")
        repo.exportar_excel()
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()

    resumen["aplicado"] = True
    resumen["ruta_excel"] = str(Path(repo.ruta_final).resolve())
    resumen["directorio_backups"] = str(directorio_backup.resolve())
    return resumen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--aplicar", action="store_true")
    parser.add_argument("--sucursal")
    parser.add_argument("--causa", action="append", dest="causas")
    argumentos = parser.parse_args()
    print(json.dumps(
        reclasificar(
            argumentos.config,
            aplicar=argumentos.aplicar,
            sucursal=argumentos.sucursal,
            causas=argumentos.causas,
        ),
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
