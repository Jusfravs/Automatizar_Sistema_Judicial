# Contexto de reanudación

Última actualización: 25 de septiembre de 2026, America/Guayaquil.

## Estado comprobado

- config.json, config_quito.json y config_santo_domingo.json permanecen en
  SQLite. La configuración general filtra ESTADO = ACTIVO en todas las
  sucursales y usa data/estado_casos_20260827.db.
- PostgreSQL 18.6 responde en localhost:5432. La base casos_judiciales
  conservó 1.954 expedientes, 2.301 versiones, 172.625 actuaciones y
  418 eventos de auditoría al 24 de septiembre. No se detectaron causas
  ni hashes duplicados.
- casos_judiciales y casos_judiciales_test tienen aplicadas las migraciones
  001 y 002 y pasan la verificación de conexión y esquema.
- La inspección SQLite sin escritura obtuvo 2.339 filas de cola,
  2.301 resultados, 1.954 causas únicas y 0 JSON inválidos.
- El 25 de septiembre la suite general terminó con 291 pruebas y
  4 omitidas; las 4 pruebas de integración PostgreSQL pasaron por
  separado contra casos_judiciales_test.

## Pilotos y criterio de rendimiento

Los grupos distintos de 1, 10 y 50 causas en
outputs/postgres_pilotos_20260925/ terminaron con 1/1, 10/10 y 50/50
PROCESADO, sin errores, en 42, 209 y 644 segundos. Cada etapa generó CSV y
Excel en su carpeta y usó casos_judiciales_test sin auditoría de IA. La
comparación histórica de inferencia dio 57 coincidencias y 4 diferencias
pendientes de revisión de evidencia.

La primera ejecución del benchmark de las mismas diez causas con un trabajador
se canceló por `ARTEFACTOS_ERROR:[WinError 206]` al guardar evidencia bajo una
ruta larga. Se acortó el nombre de carpeta en disco y se añadió una prueba de
ruta profunda. La repetición terminó con 10/10 PROCESADO al primer intento en
269 segundos, CSV de 10 filas, Excel y cero fallidos. Los 13 campos de fase,
etapa y fechas coincidieron con el lote de dos trabajadores, que tardó 209
segundos. La mejora de rendimiento fue 28,7 %, por debajo del objetivo de 50 %.
No reutilice la ejecución cancelada para medir rendimiento.

Diagnóstico posterior, sin nuevas consultas al portal: las diez soluciones de
2Captcha sumaron 118,9 s con un trabajador y 245,3 s con dos; las corridas
fueron en horarios distintos y no permiten atribuir esa diferencia a la
concurrencia. De las cuatro diferencias históricas, una causa no tenía
actuaciones antiguas, dos incorporaron nuevas actuaciones y la cuarta ya
produce la nueva fase al recalcular sus actuaciones antiguas con el motor
actual. La revisión jurídica de esta última sigue pendiente.

La medición emparejada se completó después: las mismas diez causas terminaron
10/10 al primer intento en 291 s con un trabajador y 177 s con dos, sin
errores ni diferencias en 13 campos procesales. La mejora de rendimiento fue
64,4 %, superior al objetivo de 50 % en esa muestra. Los CSV tienen diez
filas, los Excel ambas hojas y no hay fallidos. Los perfiles normales
continúan en SQLite hasta decidir su activación.

POSTGRES_PASSWORD y AUTOCAPTCHA_API_KEY están en la PowerShell del operador,
no en archivos del repositorio. El lanzador .cmd debe invocarse desde esa
misma consola para heredar ambas variables. La sesión de Codex no hereda las
variables cargadas en otra ventana.

La siguiente muestra de NVIDIA NIM y su validación jurídica siguen
separadas de estos pilotos. El auditor de IA no debe intervenir en la
medición de PostgreSQL y Playwright.

## Lote real de 50 para el Excel final nuevo

El Excel fuente de `Downloads` se importó a un CSV nuevo de 2001 filas en
`outputs/excel_final_20260925/`. Las primeras 50 causas únicas se procesaron
en PostgreSQL `casos_judiciales` con dos trabajadores: ejecución
`1d359713-8da2-4597-a1f9-2a7b54ffba5c`, `COMPLETADA`, 50/50 `PROCESADO`,
un intento por causa, 25 por trabajador, 766 s y cero fallidos. El Excel nuevo
`REPORTE_PROCESADO_FINAL_20260925.xlsx` conserva las 2001 filas de `Reporte`
y la hoja `PARA CARGA`. Tres campos procesales de las 50 causas coinciden en
PostgreSQL, CSV y Excel. El archivo fuente no cambió según su SHA-256. El
perfil general `config.json` continúa en SQLite; este lote usó un perfil
PostgreSQL aislado. El lanzador se bloquea si se intenta repetir el mismo lote.

## Estado al 28 de septiembre de 2026

La corrida general terminó y el Excel vigente es
`outputs/excel_final_20260925/REPORTE_PROCESADO_FINAL_20260925_CORREGIDO.xlsx`.
Contiene 2001 filas en `Reporte` y 1951 en `PARA CARGA`. La corrección de fecha
local y título dejó 34 causas para revisión manual; 33 se retiraron de la hoja
de carga. El CSV conserva el historial completo y el Excel anterior tiene
respaldo en la misma carpeta de salida. Microsoft Excel abrió el libro
corregido con las dos tablas intactas. La [Guía PostgreSQL](../03_BASE_DE_DATOS/GUIA_PGADMIN_POSTGRES.md)
contiene las consultas de supervisión y el [Manual de uso](MANUAL_DE_USO.md)
indica el perfil y la ruta actuales.

Las cuatro diferencias de clasificación frente a la fotografía histórica
siguen pendientes de revisión jurídica con sus actuaciones de respaldo.

Las notas anteriores de clasificación y los estados de agosto se conservan
en [el contexto archivado](../05_AVANCES/CONTEXTO_REANUDACION_ANTERIOR_20260924.md).
Son antecedentes y no instrucciones operativas vigentes.
