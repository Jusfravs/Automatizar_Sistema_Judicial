# PostgreSQL y pgAdmin 4 — guía operativa

Actualizado: 25 de septiembre de 2026 (America/Guayaquil).

PostgreSQL 18.6 está instalado en localhost:5432. Existen las bases
casos_judiciales y casos_judiciales_test. Ambas tienen las migraciones
001_concurrencia_base.sql y 002_historial_inferencia_ia.sql, comprobadas el
24 de septiembre. Los perfiles normales siguen en SQLite.

## 1. Consola y credenciales

Use PowerShell y el mismo proceso para cargar claves y ejecutar el bot. Si
partió de CMD, escriba powershell -NoExit. Una variable $env: establecida en
una PowerShell hija no regresa a CMD ni aparece en otra ventana.

El bot usa POSTGRES_HOST (localhost), POSTGRES_PORT (5432),
POSTGRES_USER (judicial_app) y POSTGRES_PASSWORD. Cada configuración PostgreSQL
fija nombre_db, por lo que POSTGRES_DB no sustituye la base indicada allí.
La contraseña administrativa solo se necesita para crear rol, base o migraciones
con scripts/inicializar_postgres.py; no se necesita para los pilotos.

Cargue las claves con Read-Host -AsSecureString según el Manual de uso. Verifique
solo su presencia:

~~~powershell
[bool]$env:POSTGRES_PASSWORD
[bool]$env:AUTOCAPTCHA_API_KEY
~~~

No guarde valores reales en config.json, .env, comandos visibles ni reportes.

## 2. Estado y estructura

La base casos_judiciales conserva la migración histórica: 1.954 expedientes,
2.301 versiones, 172.625 actuaciones y 418 eventos de auditoría al
24 de septiembre. No se detectaron duplicados de causa ni de hash de fuente.
casos_judiciales_test tiene el esquema completo y se usa para las pruebas y
los pilotos aislados.

Tablas principales: ejecuciones, cola_trabajo, resultados_ejecucion,
expedientes, actuaciones y eventos_auditoria. La migración 002 añade
actuaciones_procesales, ejecuciones_inferencia, auditorias_ia,
revisiones_ia e hitos_procesales.

Para registrar la conexión en pgAdmin:

| Campo | Valor |
|---|---|
| Host | localhost |
| Puerto | 5432 |
| Base de mantenimiento | casos_judiciales_test para el piloto |
| Usuario | judicial_app |
| Contraseña | Credencial local de la sesión |

Consultas de supervisión:

~~~sql
SELECT * FROM v_estado_ejecuciones ORDER BY creado_en DESC;
SELECT * FROM v_trabajadores_activos;
SELECT * FROM v_cola_trabajo WHERE estado IN ('ERROR_FINAL', 'REVISION');
SELECT * FROM v_resumen_fases;
~~~

## 3. Verificación sin modificar datos de producción

Desde la raíz del proyecto:

~~~powershell
$python = (Get-Command python).Source
& $python scripts/migrar_sqlite_a_postgres.py
~~~

Sin --apply, ese script solo inspecciona las tres fuentes SQLite. La revisión
del 24 de septiembre obtuvo 2.339 filas de cola, 2.301 resultados, 1.954
causas únicas y 0 JSON inválidos. No vuelva a importar por rutina.

Las pruebas de integración escriben y limpian una causa de prueba, por lo que
deben apuntar exclusivamente a casos_judiciales_test:

~~~powershell
$dbAnterior = $env:POSTGRES_DB
$integracionAnterior = $env:RUN_POSTGRES_INTEGRATION
try {
    $env:POSTGRES_DB = 'casos_judiciales_test'
    $env:RUN_POSTGRES_INTEGRATION = '1'
    & $python -m unittest tests.test_postgres_integracion -v
}
finally {
    $env:POSTGRES_DB = $dbAnterior
    $env:RUN_POSTGRES_INTEGRATION = $integracionAnterior
}
~~~

La suite del 24 de septiembre pasó 4 pruebas de integración, incluida la
validación del esquema completo. El servicio y la conexión por sí solos no
demuestran que el portal, CAPTCHA y los dos trabajadores funcionen.

## 4. Pilotos reales

Use los lanzadores preparados en outputs/postgres_pilotos_20260925/ según el
Manual de uso. Cada uno apunta explícitamente a casos_judiciales_test, usa
un CSV y un Excel propios y desactiva las vistas de IA. El orden es una causa
con un trabajador, diez con dos y cincuenta con dos. Los tres lotes aún
requieren resultado real del portal antes de considerar terminada la fase.

Mantenga el navegador visible. Si falla 2Captcha, la ventana humana dura
como máximo 30 segundos. Si el esquema o la conexión fallan, el coordinador
se detiene antes de abrir Chromium y no cambia silenciosamente a SQLite.

Una nueva invocación crea una ejecución nueva. Consulte primero las vistas y
el archivo ejecucion_produccion.log de la etapa. No borre trabajos o expedientes
de la base de pruebas mientras un trabajador conserve un lease.

## 5. Inicialización excepcional

Solo en una instalación nueva, o si una migración falta y se ha revisado
previamente el estado, use la credencial administrativa y ejecute:

~~~powershell
& $python scripts/inicializar_postgres.py
& $python scripts/inicializar_postgres.py --dbname casos_judiciales_test
~~~

El inicializador crea rol y base si faltan, aplica SQL versionado y comprueba
los hashes de migraciones existentes. No es un paso previo de cada piloto.
El comando scripts/migrar_sqlite_a_postgres.py --apply escribe en la base
indicada por POSTGRES_DB y se reserva para una migración autorizada.

Para volver a la operación secuencial, cierre o cancele la ejecución
PostgreSQL, compruebe que v_trabajadores_activos esté vacío y use los perfiles
SQLite normales. No copie manualmente filas PostgreSQL sobre SQLite.
