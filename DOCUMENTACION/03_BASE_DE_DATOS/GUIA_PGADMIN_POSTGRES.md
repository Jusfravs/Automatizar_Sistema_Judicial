# Guía de Uso: Base de Datos PostgreSQL y pgAdmin 4

Esta guía explica cómo conectar **pgAdmin 4** a la base de datos `casos_judiciales`, explorar las tablas relacionales y consultar las vistas analíticas preparadas para la gestión de expedientes.

---

## 1. Parámetros de Conexión en pgAdmin 4

Abre **pgAdmin 4** desde tu menú de inicio de Windows y crea una nueva conexión con estos datos:

| Parámetro | Valor |
| :--- | :--- |
| **Host name / address** | `localhost` |
| **Port** | `5432` |
| **Maintenance database** | `casos_judiciales` |
| **Username** | `postgres` |
| **Password** | *(Vacío o la configurada en tu instalación local)* |

---

## 2. Estructura de la Base de Datos

En el panel izquierdo de pgAdmin 4, navega hasta:
`Servers > PostgreSQL 18 > Databases > casos_judiciales > Schemas > public`

### Tablas Principales (`Tables`):
- **`expedientes`**: Tabla central con los 3,743 expedientes de Santo Domingo y 128 de Quito. Contiene:
  - `numero_causa`, `ciudad`, `estado`, `ultima_etapa`, `ultima_fase`, `fecha_fin_ultima_fase`
  - `actor`, `demandado`, `tipo_accion`, `fecha_inicio_juicio`, `total_actuaciones`
  - `datos_json` (campo `JSONB` indexado con GIN para búsquedas profundas).
- **`actuaciones`**: Registro cronológico de todas las más de 30,000 providencias y diligencias indexadas por causa.
- **`eventos_auditoria`**: Registro histórico de eventos y extracciones.

---

## 3. Vistas Analíticas Preconfiguradas (`Views`)

Puedes hacer clic derecho sobre cualquiera de estas vistas en pgAdmin 4 y seleccionar **View/Edit Data > All Rows**:

1. **`v_resumen_fases`**:
   Dashboard agregado de cuántos expedientes se encuentran en cada etapa y fase procesal, con su porcentaje relativo.
   ```sql
   SELECT * FROM v_resumen_fases;
   ```

2. **`v_casos_revision_manual`**:
   Expedientes derivados a mediación o con acuerdos que requieren supervisión humana.
   ```sql
   SELECT * FROM v_casos_revision_manual;
   ```

3. **`v_reporte_ejecutivo`**:
   Reporte tabular unificado listo para exportar a CSV/Excel desde pgAdmin.
   ```sql
   SELECT * FROM v_reporte_ejecutivo WHERE ciudad = 'QUITO';
   ```

4. **`v_cola_pendientes`**:
   Cola de expedientes pendientes o con errores para monitorear el progreso del extractor.
   ```sql
   SELECT * FROM v_cola_pendientes;
   ```

---

## 4. Consultas SQL Útiles para el Día a Día

### Ver los expedientes de Quito en Citación / Calificación:
```sql
SELECT numero_causa, actor, demandado, ultima_fase, fecha_fin_ultima_fase
FROM expedientes
WHERE ciudad = 'QUITO' AND ultima_fase = '1.3 CALIFICACION'
ORDER BY numero_causa;
```

### Consultar las actuaciones de un caso específico:
```sql
SELECT orden, fecha, tipo_actuacion, detalle
FROM actuaciones
WHERE numero_causa = '17230-2016-17734'
ORDER BY orden ASC;
```

### Búsqueda por nombre de demandado:
```sql
SELECT numero_causa, ciudad, demandado, ultima_fase, fecha_fin_ultima_fase
FROM expedientes
WHERE demandado ILIKE '%Perez%'
ORDER BY actualizado_en DESC;
```

---

## 5. Scripts de Mantenimiento

- **Reinicializar o actualizar esquema:**
  ```powershell
  py scripts/inicializar_postgres.py
  ```
- **Re-migrar o sincronizar SQLite hacia PostgreSQL:**
  ```powershell
  py scripts/migrar_sqlite_a_postgres.py
  ```
