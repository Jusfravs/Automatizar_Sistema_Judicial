# Estado de pausa de la depuración multiagente

Fecha de pausa: 30 de septiembre de 2026.

## Estado seguro conservado

- Los siete perfiles personalizados están definidos en `.codex/agents/`.
- Los siete perfiles respondieron `OK` en una prueba real con `codex --no-daemon`.
- `ABRIR_CODEX_CASOS_JUDICIALES.cmd` inicia Codex con `--no-daemon`.
- El límite continúa en tres agentes simultáneos por oleada.
- El plan completo está en `PLAN_DEPURACION_MODULAR_MULTIAGENTE.md`.
- La línea base estable previa a la oleada es `302` pruebas, con `5` integraciones PostgreSQL omitidas de forma controlada.

## Trabajo pausado

La primera oleada descubrió siete pruebas que `unittest` no ejecutaba. Un intento inicial convirtió esas pruebas y corrigió cuatro resultados, alcanzando `309` pruebas verdes. La revisión independiente rechazó el parche por dos problemas de contrato:

1. `FASE_PROCESAL` y `ETAPA_PROCESAL` deben seguir siendo alias de `FASE ACTUAL` y `ETAPA ACTUAL`; el intento los cambió al último hito acreditado.
2. `BOLETA DE CITACION AL/A LA DEMANDADO/A` sin `NOTIFICADA`, `REALIZADA`, `ENTREGADA` o `FIJADA` representa una diligencia pendiente, no una citación cumplida.

El parche rechazado se preservó únicamente como referencia en `PAUSA_DEPURACION_20260930.patch`. No debe aplicarse completo. Los cinco archivos de producción y pruebas fueron restaurados a la versión estable para evitar que una corrida operativa use esa semántica incorrecta. Los artefactos de Graphify regenerados durante la oleada también fueron restaurados.

## Contrato acordado para retomar

- `ULTIMA ETAPA` y `ULTIMA FASE`: último hito acreditado y cumplido.
- `ETAPA ACTUAL` y `FASE ACTUAL`: estado operativo vigente o siguiente paso.
- `ETAPA_PROCESAL == ETAPA ACTUAL`.
- `FASE_PROCESAL == FASE ACTUAL`.
- Una boleta aislada conserva `ULTIMA FASE = 1.3 CALIFICACION` y mantiene `FASE ACTUAL = 2.1 CITACION`.
- La fecha de una actuación pendiente puede fechar el inicio de la fase actual, pero no debe inventar una fecha de culminación del último hito.

## Hallazgo PostgreSQL pendiente

`scripts/preparar_reproceso_causas.py` intenta borrar `expedientes`, pero las cinco tablas de historial IA de la migración `002` lo referencian sin cascada. Además, SQLite puede confirmarse antes de que PostgreSQL termine, dejando ambos almacenes desalineados si PostgreSQL falla.

La política acordada es conservar el expediente, reiniciar su fotografía a `PENDIENTE`, borrar únicamente las actuaciones vigentes que deben reconstruirse y preservar todo el historial y auditoría. La corrección debe probarse primero sobre PostgreSQL efímero; no se ha modificado la base operativa.

## Secuencia exacta para reanudar

1. Leer este documento y `PLAN_DEPURACION_MODULAR_MULTIAGENTE.md`.
2. Hacer descubribles las siete pruebas sin cambiar todavía sus expectativas de dominio.
3. Ajustar las pruebas al contrato acordado: último hito separado de fase actual.
4. Implementar el tratamiento de boleta pendiente sin marcar citación cumplida.
5. Ejecutar pruebas focales, `python -m unittest discover -s tests` y revisión independiente.
6. Corregir el reproceso PostgreSQL con pruebas efímeras antes de continuar con `main.py`.

No hay agentes trabajando al quedar registrada esta pausa.

## Avance al 01/10/2026

- Las siete pruebas antes ocultas ya son descubiertas por `unittest`. La inferencia distingue el ultimo hito acreditado de la fase operativa; boletas pendientes, repetidas o `NO NOTIFICADA` no acreditan citacion, y una boleta `NOTIFICADA` si puede hacerlo.
- `preparar_reproceso_causas.py` conserva `expedientes`, las cinco tablas IA y la auditoria; limpia la fotografia procesal, la ultima gestion y los cuatro IDs, y borra solo `actuaciones` legadas. Si PostgreSQL falla despues del commit SQLite, restaura SQLite, CSV y Excel desde respaldos.
- La prueba de integracion se ejecuto contra `casos_judiciales_test` con esquema unico. Las migraciones 001/002 se aplicaron y reaplicaron sobre datos sinteticos sin perder ni duplicar historial; el reproceso respeto las claves foraneas. Se verifico que quedaron cero esquemas temporales. La base operativa no se uso para esta prueba.
- La suite completa, `compileall` y `git diff --check` pasaron con la integracion aislada activada.
- Oleada 2 iniciada: la seleccion pura se extrajo de `main.py` a `src/seleccion_ejecucion.py`, con compatibilidad de importacion y 15 pruebas nuevas. La revision independiente no encontro regresiones.
- Pendiente: extraer el despacho PostgreSQL y luego la ejecucion secuencial de `main.py`. El script de reproceso debe usarse sin workers ni lotes activos hasta implantar exclusion compartida con la cola. Persiste la ventana de fallo entre los commits SQLite y PostgreSQL; no existe transaccion distribuida.

### Corte de pausa solicitado por Justin

- El despacho PostgreSQL se extrajo a `src/ejecucion_postgres.py`; `main.py` mantiene `_ejecutar_lote_postgres` como wrapper compatible y las dependencias siguen cargandose de forma diferida.
- `tests/test_despacho_postgres_main.py` agrega 9 pruebas de despacho. La revision independiente no encontro regresiones en el cuerpo trasladado ni en los puntos de parche.
- Ultima puerta ejecutada: `python -m unittest discover -s tests -q` con `TEST_POSTGRES_DSN` apuntando a `casos_judiciales_test`: **341 pruebas, OK, 5 omitidas**. Se comprobaron `compileall`, `git diff --check` y cero esquemas `qa_reproceso_%` restantes.
- Proxima tarea al retomar: revisar `git status`, ejecutar la suite despues de cualquier nuevo cambio y continuar la oleada 2 con la ejecucion secuencial SQLite. No lanzar casos reales ni reprocesos antes de revisar la limitacion de concurrencia indicada arriba.
