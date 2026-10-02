-- Los campos voluminosos de las filas históricas viven en un bucket privado.
ALTER TABLE expedientes ADD COLUMN IF NOT EXISTS archivo_segmento TEXT;
ALTER TABLE resultados_ejecucion ADD COLUMN IF NOT EXISTS archivo_segmento TEXT;
ALTER TABLE actuaciones ADD COLUMN IF NOT EXISTS archivo_segmento TEXT;
ALTER TABLE actuaciones_procesales ADD COLUMN IF NOT EXISTS archivo_segmento TEXT;

CREATE TABLE IF NOT EXISTS archivo_historico_objetos (
    nombre TEXT PRIMARY KEY,
    sha256 CHAR(64) NOT NULL,
    bytes BIGINT NOT NULL CHECK (bytes >= 0),
    filas BIGINT NOT NULL CHECK (filas >= 0),
    registrado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- El sistema usa psycopg2; los datos judiciales no se publican por Data API.
DO $$
DECLARE
    objeto TEXT;
BEGIN
    FOREACH objeto IN ARRAY ARRAY[
        'ejecuciones', 'expedientes', 'cola_trabajo', 'resultados_ejecucion',
        'actuaciones', 'eventos_auditoria', 'actuaciones_procesales',
        'ejecuciones_inferencia', 'auditorias_ia', 'revisiones_ia',
        'hitos_procesales', 'schema_migrations', 'archivo_historico_objetos'
    ] LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', objeto);
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated, service_role', objeto);
    END LOOP;
    FOREACH objeto IN ARRAY ARRAY[
        'v_estado_ejecuciones', 'v_cola_trabajo', 'v_trabajadores_activos',
        'v_resumen_fases', 'v_casos_revision_manual', 'v_reporte_ejecutivo'
    ] LOOP
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated, service_role', objeto);
    END LOOP;
END $$;
