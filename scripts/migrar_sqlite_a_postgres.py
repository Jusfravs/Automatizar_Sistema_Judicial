# scripts/migrar_sqlite_a_postgres.py
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import sqlite3
import json
import psycopg2
from psycopg2.extras import execute_values, Json
from pathlib import Path

def obtener_conexion_postgres():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        dbname=os.getenv("POSTGRES_DB", "casos_judiciales"),
    )

def migrar_base_sqlite(ruta_sqlite, ciudad_default="QUITO"):
    if not Path(ruta_sqlite).exists():
        print(f"[WARN] Archivo SQLite no encontrado: {ruta_sqlite}")
        return 0

    print(f"\n[INFO] Iniciando migración desde: {ruta_sqlite} (Ciudad: {ciudad_default})...")
    conn_sq = sqlite3.connect(ruta_sqlite)
    conn_pg = obtener_conexion_postgres()
    conn_pg.autocommit = False
    cur_pg = conn_pg.cursor()

    # 1. Leer tabla juicios
    juicios_map = {}
    try:
        rows_juicios = conn_sq.execute("SELECT numero_causa, estado, ruta_html, reintentos FROM juicios").fetchall()
        for causa, est, r_html, reint in rows_juicios:
            juicios_map[causa] = {
                "estado": est or "PENDIENTE",
                "ruta_html": r_html,
                "reintentos": reint or 0
            }
    except Exception as e:
        print(f"[WARN] No se pudo leer tabla juicios de {ruta_sqlite}: {e}")

    # 2. Leer resultados_expediente
    rows_resultados = []
    try:
        rows_resultados = conn_sq.execute("SELECT numero_causa, origen, datos_json, ruta_html, actualizado_en FROM resultados_expediente").fetchall()
    except Exception as e:
        print(f"[WARN] No se pudo leer resultados_expediente de {ruta_sqlite}: {e}")

    expedientes_insert = []
    actuaciones_insert = []
    causas_procesadas = set()

    for causa, origen, datos_json_raw, r_html, act_en in rows_resultados:
        causas_procesadas.add(causa)
        info_juicio = juicios_map.get(causa, {"estado": "PROCESADO", "reintentos": 0, "ruta_html": r_html})
        
        data = {}
        try:
            data = json.loads(datos_json_raw)
        except Exception:
            data = {}

        datos_extraidos = data.get("datos") or {}
        actuaciones = datos_extraidos.get("HISTORIAL_ACTUACIONES") or []

        # Extraer campos de primer nivel
        ultima_etapa = datos_extraidos.get("ULTIMA ETAPA") or datos_extraidos.get("ETAPA_PROCESAL")
        ultima_fase = datos_extraidos.get("ULTIMA FASE") or datos_extraidos.get("FASE_ACTUAL")
        fecha_fin = datos_extraidos.get("FECHA FIN ULTIMA FASE") or datos_extraidos.get("FECHA_FIN_ETAPA") or datos_extraidos.get("FECHA INICIAL FASE ACTUAL")
        etapa_act = datos_extraidos.get("ETAPA ACTUAL") or datos_extraidos.get("SIGUIENTE_ETAPA")
        fase_act = datos_extraidos.get("FASE ACTUAL") or datos_extraidos.get("SIGUIENTE_FASE")
        fecha_inicio_act = datos_extraidos.get("FECHA INICIO FASE ACTUAL") or fecha_fin
        msg_esp = datos_extraidos.get("COMENTARIO_ULTIMO") or datos_extraidos.get("MENSAJE_ESPECIAL")
        
        actor = datos_extraidos.get("ACTOR") or datos_extraidos.get("DEMANDANTE")
        demandado = datos_extraidos.get("DEMANDADO")
        tipo_accion = datos_extraidos.get("ACCION/INFRACCION") or datos_extraidos.get("TIPO_ACCION")
        fecha_inicio_j = datos_extraidos.get("FECHA INICIO JUICIO") or datos_extraidos.get("FECHA_INGRESO")
        
        estado_final = (
            "EXCLUIDO_NO_CORRESPONDE"
            if data.get("estado") == "EXCLUIDO_NO_CORRESPONDE"
            else "PROCESADO"
            if (data.get("estado") == "COMPLETADO" or ultima_fase)
            else info_juicio["estado"]
        )

        expedientes_insert.append((
            causa,
            ciudad_default,
            estado_final,
            ultima_etapa,
            ultima_fase,
            str(fecha_fin) if fecha_fin else None,
            etapa_act,
            fase_act,
            str(fecha_inicio_act) if fecha_inicio_act else None,
            msg_esp,
            actor,
            demandado,
            tipo_accion,
            str(fecha_inicio_j) if fecha_inicio_j else None,
            len(actuaciones),
            origen or "ESATJE_TRANSACCIONAL",
            r_html or info_juicio.get("ruta_html"),
            info_juicio.get("reintentos", 0),
            Json(data)
        ))

        # Actuaciones individuales
        for idx, act in enumerate(actuaciones):
            actuaciones_insert.append((
                causa,
                str(act.get("fecha") or ""),
                act.get("actuacion") or act.get("tipo") or "",
                act.get("detalle") or "",
                act.get("instancia") or "PRIMERA INSTANCIA",
                idx + 1
            ))

    # Añadir causas que estaban en cola juicios pero no en resultados (PENDIENTES)
    for causa, info_j in juicios_map.items():
        if causa not in causas_procesadas:
            expedientes_insert.append((
                causa,
                ciudad_default,
                info_j["estado"],
                None, None, None, None, None, None, None,
                None, None, None, None,
                0,
                "COLA_INICIAL",
                info_j.get("ruta_html"),
                info_j.get("reintentos", 0),
                Json({})
            ))

    # Insertar expedientes con UPSERT en PostgreSQL
    if expedientes_insert:
        upsert_query = """
        INSERT INTO expedientes (
            numero_causa, ciudad, estado, ultima_etapa, ultima_fase,
            fecha_fin_ultima_fase, etapa_actual, fase_actual, fecha_inicio_fase_actual,
            mensaje_especial, actor, demandado, tipo_accion, fecha_inicio_juicio,
            total_actuaciones, origen, ruta_html, reintentos, datos_json
        ) VALUES %s
        ON CONFLICT (numero_causa) DO UPDATE SET
            ciudad = EXCLUDED.ciudad,
            estado = EXCLUDED.estado,
            ultima_etapa = EXCLUDED.ultima_etapa,
            ultima_fase = EXCLUDED.ultima_fase,
            fecha_fin_ultima_fase = EXCLUDED.fecha_fin_ultima_fase,
            etapa_actual = EXCLUDED.etapa_actual,
            fase_actual = EXCLUDED.fase_actual,
            fecha_inicio_fase_actual = EXCLUDED.fecha_inicio_fase_actual,
            mensaje_especial = EXCLUDED.mensaje_especial,
            actor = EXCLUDED.actor,
            demandado = EXCLUDED.demandado,
            tipo_accion = EXCLUDED.tipo_accion,
            fecha_inicio_juicio = EXCLUDED.fecha_inicio_juicio,
            total_actuaciones = EXCLUDED.total_actuaciones,
            origen = EXCLUDED.origen,
            ruta_html = EXCLUDED.ruta_html,
            reintentos = EXCLUDED.reintentos,
            datos_json = EXCLUDED.datos_json,
            actualizado_en = CURRENT_TIMESTAMP;
        """
        execute_values(cur_pg, upsert_query, expedientes_insert)
        conn_pg.commit()
        print(f"[OK] {len(expedientes_insert)} expedientes sincronizados y confirmados en PostgreSQL.")

    # Insertar actuaciones individuales
    if actuaciones_insert:
        causas_list = list(causas_procesadas)
        cur_pg.execute("DELETE FROM actuaciones WHERE numero_causa = ANY(%s)", (causas_list,))
        
        insert_act_query = """
        INSERT INTO actuaciones (
            numero_causa, fecha, tipo_actuacion, detalle, instancia, orden
        ) VALUES %s
        """
        execute_values(cur_pg, insert_act_query, actuaciones_insert)
        conn_pg.commit()
        print(f"[OK] {len(actuaciones_insert)} actuaciones individuales indexadas y confirmadas en PostgreSQL.")

    # 3. Migrar eventos de auditoría si existen
    try:
        rows_eventos = conn_sq.execute("SELECT numero_causa, origen, detalle, creado_en FROM eventos_extraccion").fetchall()
        if rows_eventos:
            insert_eventos_query = """
            INSERT INTO eventos_auditoria (numero_causa, origen, detalle, creado_en)
            VALUES %s
            """
            execute_values(cur_pg, insert_eventos_query, rows_eventos)
            conn_pg.commit()
            print(f"[OK] {len(rows_eventos)} eventos de auditoría migrados.")
    except Exception as e:
        conn_pg.rollback()
        print(f"[INFO] No se migraron eventos de auditoría antiguos: {e}")

    cur_pg.close()
    conn_pg.close()
    conn_sq.close()
    return len(expedientes_insert)

def migrar_todo():
    print("=" * 70)
    print("MIGRACIÓN INTEGRAL DE SQLITE A POSTGRESQL (CASOS JUDICIALES)")
    print("=" * 70)

    # 1. Migrar Quito (dataset principal corregido)
    db_quito = "data/quito/estado_casos_quito.db"
    migrar_base_sqlite(db_quito, ciudad_default="QUITO")

    # 2. Migrar General / Santo Domingo si existe
    db_general = "estado_casos.db"
    if Path(db_general).exists():
        migrar_base_sqlite(db_general, ciudad_default="SANTO DOMINGO")

    print("\n" + "=" * 70)
    print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE EN POSTGRESQL.")
    print("=" * 70)

if __name__ == "__main__":
    migrar_todo()
