# scripts/inicializar_postgres.py
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def obtener_config_postgres():
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
        "dbname": os.getenv("POSTGRES_DB", "casos_judiciales"),
    }

def crear_base_de_datos(config):
    """Crea la base de datos si no existe."""
    target_db = config["dbname"]
    conn = psycopg2.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        dbname="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
    existe = cursor.fetchone()
    if not existe:
        cursor.execute(f'CREATE DATABASE "{target_db}" WITH ENCODING "UTF8";')
        print(f"[OK] Base de datos '{target_db}' creada exitosamente.")
    else:
        print(f"[INFO] Base de datos '{target_db}' ya existe.")
    
    cursor.close()
    conn.close()

def inicializar_esquema(config):
    """Crea tablas, índices y vistas analíticas para pgAdmin."""
    conn = psycopg2.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        dbname=config["dbname"]
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    print("[INFO] Creando tablas, índices y vistas analíticas...")

    # 1. Tabla expedientes / juicios
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expedientes (
        numero_causa VARCHAR(60) PRIMARY KEY,
        ciudad VARCHAR(100) DEFAULT 'QUITO',
        estado VARCHAR(50) DEFAULT 'PENDIENTE',
        ultima_etapa VARCHAR(150),
        ultima_fase VARCHAR(150),
        fecha_fin_ultima_fase VARCHAR(50),
        etapa_actual VARCHAR(150),
        fase_actual VARCHAR(150),
        fecha_inicio_fase_actual VARCHAR(50),
        mensaje_especial VARCHAR(255),
        actor TEXT,
        demandado TEXT,
        tipo_accion TEXT,
        fecha_inicio_juicio VARCHAR(50),
        total_actuaciones INT DEFAULT 0,
        origen VARCHAR(100) DEFAULT 'ESATJE_TRANSACCIONAL',
        ruta_html TEXT,
        reintentos INT DEFAULT 0,
        datos_json JSONB,
        creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Tabla actuaciones individuales
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS actuaciones (
        id BIGSERIAL PRIMARY KEY,
        numero_causa VARCHAR(60) REFERENCES expedientes(numero_causa) ON DELETE CASCADE,
        fecha VARCHAR(50),
        tipo_actuacion TEXT,
        detalle TEXT,
        instancia VARCHAR(100),
        orden INT,
        creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Tabla eventos de auditoría
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS eventos_auditoria (
        id BIGSERIAL PRIMARY KEY,
        numero_causa VARCHAR(60),
        tipo_evento VARCHAR(100) NOT NULL,
        origen VARCHAR(100),
        detalle TEXT,
        creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. Índices
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_expedientes_estado ON expedientes(estado);
    CREATE INDEX IF NOT EXISTS idx_expedientes_ultima_fase ON expedientes(ultima_fase);
    CREATE INDEX IF NOT EXISTS idx_expedientes_ciudad ON expedientes(ciudad);
    CREATE INDEX IF NOT EXISTS idx_expedientes_datos_gin ON expedientes USING GIN (datos_json);
    CREATE INDEX IF NOT EXISTS idx_actuaciones_causa ON actuaciones(numero_causa);
    CREATE INDEX IF NOT EXISTS idx_actuaciones_orden ON actuaciones(numero_causa, orden);
    CREATE INDEX IF NOT EXISTS idx_eventos_causa ON eventos_auditoria(numero_causa);
    CREATE INDEX IF NOT EXISTS idx_eventos_fecha ON eventos_auditoria(creado_en);
    """)

    # 5. Vistas analíticas para pgAdmin 4
    cursor.execute("""
    CREATE OR REPLACE VIEW v_resumen_fases AS
    SELECT 
        COALESCE(ultima_etapa, 'SIN PROCESAR') AS etapa,
        COALESCE(ultima_fase, 'SIN PROCESAR') AS fase,
        COUNT(*) AS total_casos,
        ROUND(COUNT(*) * 100.0 / NULLIF((SELECT COUNT(*) FROM expedientes WHERE estado = 'PROCESADO'), 0), 2) AS porcentaje
    FROM expedientes
    WHERE estado = 'PROCESADO'
    GROUP BY ultima_etapa, ultima_fase
    ORDER BY total_casos DESC;
    """)

    cursor.execute("""
    CREATE OR REPLACE VIEW v_casos_revision_manual AS
    SELECT 
        numero_causa,
        ciudad,
        ultima_fase,
        fecha_fin_ultima_fase,
        mensaje_especial,
        actor,
        demandado,
        total_actuaciones,
        actualizado_en
    FROM expedientes
    WHERE mensaje_especial = 'REVISION MANUAL' 
       OR fase_actual = 'REVISION MANUAL'
       OR ultima_fase = '4.3 ACUERDO DE MEDIACION'
    ORDER BY actualizado_en DESC;
    """)

    cursor.execute("""
    CREATE OR REPLACE VIEW v_reporte_ejecutivo AS
    SELECT 
        numero_causa,
        ciudad,
        actor,
        demandado,
        tipo_accion,
        fecha_inicio_juicio,
        ultima_etapa,
        ultima_fase,
        fecha_fin_ultima_fase,
        etapa_actual,
        fase_actual,
        fecha_inicio_fase_actual,
        mensaje_especial,
        total_actuaciones,
        estado,
        actualizado_en
    FROM expedientes
    ORDER BY numero_causa;
    """)

    cursor.execute("""
    CREATE OR REPLACE VIEW v_cola_pendientes AS
    SELECT 
        numero_causa,
        ciudad,
        estado,
        reintentos,
        origen,
        actualizado_en
    FROM expedientes
    WHERE estado IN ('PENDIENTE', 'ERROR', 'PARCIAL')
    ORDER BY reintentos ASC, actualizado_en ASC;
    """)

    cursor.close()
    conn.close()
    print("[OK] Tablas, índices y vistas analíticas creados con éxito en PostgreSQL.")

if __name__ == "__main__":
    cfg = obtener_config_postgres()
    crear_base_de_datos(cfg)
    inicializar_esquema(cfg)
