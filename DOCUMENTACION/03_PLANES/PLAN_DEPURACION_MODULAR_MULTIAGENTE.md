# Plan de depuración modular multiagente

## Objetivo

Reducir la complejidad acumulada del sistema judicial sin cambiar su comportamiento observable, preservando la navegación ESATJE, la inferencia procesal, la concurrencia PostgreSQL y la exportación Excel.

El trabajo se ejecutará mediante `codex --no-daemon`, con un máximo de tres agentes activos por oleada. Solo habrá un responsable por archivo. Los agentes de diagnóstico entregarán evidencia; `desarrollador` modificará producción y `qa_automatizado` modificará pruebas.

## Línea base verificada

- Fecha: 29 de septiembre de 2026.
- Prueba de humo `codex --no-daemon`: los siete perfiles respondieron `OK`.
- Suite completa: `302` pruebas aprobadas, `5` omitidas, `39.105 s`.
- Comando base: `python -m unittest discover -s tests`.
- Archivos de mayor tamaño observados:
  - `src/motor_busqueda_web.py`: 3.631 líneas.
  - `src/agente_extractor.py`: 2.764 líneas.
  - `tests/test_clasificacion_arbol.py`: 2.252 líneas.
  - `src/gestor_casos.py`: 1.007 líneas.
  - `tests/test_navegacion_esatje.py`: 806 líneas.
  - `tests/test_regreso_buscador.py`: 733 líneas.
  - `src/repositorio_postgres.py`: 667 líneas.
  - `main.py`: 632 líneas.

El tamaño orienta el orden de revisión, pero no justifica por sí solo una división. Cada extracción debe formar una responsabilidad coherente y conservar contratos verificables.

## Bloqueos descubiertos en la auditoría inicial

1. `unittest` no descubre siete pruebas escritas como funciones en `tests/test_extraccion_integration.py` y `tests/test_trazabilidad_decision_final.py`. Un arnés temporal ejecutó esas siete: tres pasan y cuatro fallan. Antes de refactorizar el extractor hay que convertirlas al marco elegido y decidir, con evidencia del dominio, si sus expectativas son vigentes.
2. Los cuatro fallos ocultos afectan mandamiento, boleta de citación, conservación de calificación y una variante DOM de mandamiento. No deben corregirse dentro de un movimiento estructural de código.
3. `migrations/postgres/002_historial_inferencia_ia.sql` crea cinco tablas dependientes de `expedientes` sin borrado en cascada, mientras `scripts/preparar_reproceso_causas.py` elimina directamente expedientes. Esa operación puede fallar cuando una causa ya tiene historial IA.
4. Las integraciones PostgreSQL están omitidas sin variables explícitas. Las migraciones deben probarse sobre una instancia efímera antes de modificar el esquema operativo.
5. Hay archivos operativos versionados en `data/`, `backups/` y artefactos de pruebas. Se requiere inventario de datos y estrategia de saneamiento separada; no se eliminarán masivamente durante la refactorización.
6. Se observaron capturas de excepciones amplias y silenciosas. Cada una se revisará dentro del módulo correspondiente para registrar, propagar o documentar el respaldo correcto.

## Reglas de seguridad para la refactorización

1. No mezclar cambios funcionales con movimientos de código.
2. No borrar código por apariencia. Antes de eliminarlo se deben revisar referencias, rutas dinámicas, pruebas y puntos de entrada.
3. No conservar bloques obsoletos comentados. Git mantiene el historial; los comentarios explican motivos, invariantes o restricciones externas.
4. No ejecutar causas reales, migraciones ni escrituras operativas como parte de las pruebas unitarias.
5. No incluir `AUTOCAPTCHA_API_KEY`, `NVIDIA_API_KEY`, `POSTGRES_PASSWORD`, datos personales ni expedientes reales en prompts, fixtures, logs o commits.
6. Ante evidencia judicial ambigua, conservar el dato original y marcar revisión manual.
7. Cada cambio debe poder revertirse con un commit pequeño e independiente.

## Contratos que no pueden cambiar

- Formato y normalización de `CODIGO_JUICIO`.
- Estados y transiciones de la cola PostgreSQL.
- Reclamo atómico de causas y protección contra procesamiento duplicado.
- Reintentos, revisión manual y continuidad después de errores.
- Selección de la última actuación judicial, su título y su fecha procesal.
- Reglas de inferencia de fase y etapa.
- Columnas, tipos, filtros, tablas y apertura válida del Excel final.
- Variables de entorno y ausencia de secretos persistidos.
- Comandos públicos de `main.py` usados por operación.

## Interpretación operativa de CRUD, claves y tiempos

La capa de persistencia se organizará por operaciones del dominio:

- Crear o importar causas de forma idempotente.
- Leer pendientes, estado, historial y evidencia.
- Reclamar una causa mediante una operación atómica.
- Completar, fallar, reintentar o enviar a revisión manual con transición válida.
- Liberar reclamos vencidos con trazabilidad.

No se expondrá un CRUD genérico que permita estados inválidos. Las claves serán identificadores del dominio, restricciones únicas e identificadores de idempotencia. Las claves secretas seguirán únicamente en variables de entorno.

Los tiempos se medirán por etapa: carga, CAPTCHA, navegación, extracción, inferencia, persistencia y exportación. Las comparaciones usarán el mismo conjunto sintético y la mediana de tres ejecuciones; no se optimizará una etapa sin evidencia.

## Oleadas de trabajo

### Oleada 0: inventario y contratos

Agentes simultáneos: `arquitecto`, `qa_automatizado`, `revisor_seguridad`.

Entregables:

- Mapa de módulos, entradas, salidas y dependencias.
- Matriz entre contratos y pruebas existentes.
- Registro priorizado de complejidad, duplicación, excepciones silenciosas y riesgos de secretos.
- Lista de cambios que requieren prueba de caracterización antes de tocar producción.

Puerta de salida: línea base verde y alcance del primer cambio limitado a una responsabilidad.

### Oleada 1: pruebas y migraciones

Agentes simultáneos: `postgres_concurrencia`, `desarrollador`, `qa_automatizado`.

Alcance:

- Convertir las siete pruebas no descubiertas a `unittest` o adoptar `pytest` formalmente.
- Resolver por separado los cuatro fallos de clasificación ocultos antes de mover el extractor.
- Separar fixtures, constructores y dobles repetidos sin alterar aserciones.
- Dividir archivos de pruebas por comportamiento cuando puedan ejecutarse de forma independiente.
- Revisar migraciones por orden, repetibilidad, restricciones, índices y recuperación ante ejecución parcial.
- Formalizar los contratos de importación y transición PostgreSQL.
- Definir y probar la política de borrado de expedientes con historial IA.

Puertas de salida:

- Las siete pruebas adicionales son descubiertas automáticamente y no hay fallos ocultos.
- Pruebas de migración desde una base vacía y desde el estado anterior.
- Reaplicar una migración no destruye datos ni duplica objetos.
- Preparar un reproceso no viola claves foráneas ni elimina trazabilidad por accidente.
- Selección, reclamo y finalización concurrente mantienen exclusión e idempotencia.
- Suite focal y suite completa verdes.

### Oleada 2: `main.py` y composición

Agentes simultáneos: `arquitecto`, `desarrollador`, `qa_automatizado`.

Alcance:

- Mantener en `main.py` el análisis de argumentos y la composición de servicios.
- Extraer selección de casos, configuración de ejecución, coordinación y resumen final hacia módulos con contratos explícitos.
- Conservar los comandos actuales y sus códigos de salida.

Puertas de salida:

- Pruebas de caracterización de argumentos, perfiles, `--solo`, `--lote`, exclusiones, continuación y trabajadores.
- Ninguna dependencia circular nueva.
- Los mensajes operativos esenciales y estados finales siguen disponibles.

### Oleada 3: núcleo de navegación y extracción

Agentes simultáneos: `navegacion_judicial`, `desarrollador`, `qa_automatizado`.

Alcance:

- Dividir `motor_busqueda_web.py` por sesión, búsqueda, CAPTCHA, navegación de carpetas, extracción de artefactos y retorno seguro.
- Dividir `agente_extractor.py` por normalización, cronología, reglas, inferencia y consolidación.
- Revisar cada `except`, `pass` y respaldo silencioso para registrar, propagar o documentar la decisión correcta.

Puertas de salida:

- Navegación bloqueada impide acciones posteriores.
- Los errores de una carpeta no contaminan otra causa.
- Los artefactos usan rutas acotadas y válidas en Windows.
- La inferencia conserva fecha, actuación de respaldo, regla y alcance.
- Pruebas de retorno al buscador, freno transaccional y clasificación verdes.

### Oleada 4: Excel y gestión de casos

Agentes simultáneos: `excel_procesal`, `desarrollador`, `qa_automatizado`.

Alcance:

- Separar lectura, normalización, combinación, cálculo y escritura en `gestor_casos.py`.
- Centralizar la selección de la última gestión judicial.
- Validar rangos de tabla, filtros, celdas combinadas, anchos, formatos y fechas.

Puertas de salida:

- Excel abre sin reparación de contenido.
- Las celdas visibles conservan su contenido y formato.
- `ESTADO ULTIMA GESTION JUDICIAL` contiene el título y no el cuerpo completo.
- La fecha procede de la actuación seleccionada y no de la fecha de consulta.
- Prueba específica del caso de regresión mediante datos anonimizados o sintéticos.

### Oleada 5: scripts y herramientas operativas

Agentes simultáneos: `arquitecto`, `desarrollador`, `revisor_seguridad`.

Alcance:

- Convertir scripts repetidos en funciones reutilizables con una interfaz de línea de comandos uniforme.
- Separar lectura, validación, planificación, ejecución y reporte.
- Añadir modo de simulación a operaciones que cambian datos cuando sea aplicable.
- Documentar entradas, salidas, variables de entorno y recuperación ante fallos.

Puertas de salida:

- `--help` funciona sin conectar servicios externos.
- Las operaciones peligrosas validan destino y precondiciones.
- Ningún secreto se imprime o persiste.
- Las herramientas reutilizan repositorios y contratos de producción en lugar de duplicarlos.

### Oleada 6: integración y limpieza final

Agentes simultáneos: `revisor_seguridad`, `arquitecto`, `qa_automatizado`.

Entregables:

- Revisión del diff acumulado y dependencias.
- Confirmación de código muerto eliminado con evidencia.
- Verificación de documentación y comandos operativos.
- Informe de pruebas y tiempos antes/después.

Puerta de salida: ninguna observación crítica o alta abierta; suite completa verde; revisión manual de un Excel sintético; piloto real separado y autorizado.

## Puertas obligatorias por cambio

1. `python -m compileall main.py src scripts tests`
2. Pruebas focales del contrato modificado.
3. `python -m unittest discover -s tests`
4. `git diff --check`
5. Revisión del diff por `revisor_seguridad`.
6. Confirmación de que no se agregaron secretos, expedientes ni artefactos operativos.
7. Medición antes/después si se tocó una ruta de rendimiento.
8. Cero pruebas válidas fuera del mecanismo de descubrimiento automático.

Las pruebas que requieren navegador visible, API externa o PostgreSQL real se ejecutan como integración explícita después de superar las puertas locales.

## Organización de ramas y archivos

- Una rama o worktree por cambio independiente.
- `desarrollador`: archivos de producción asignados.
- `qa_automatizado`: pruebas y fixtures asignados.
- Especialistas y revisores: lectura, diagnóstico y aceptación.
- Si dos cambios necesitan el mismo archivo, se ejecutan en serie.
- Cada commit incluye una sola intención: caracterización, extracción, corrección o documentación.

## Criterio de terminación

La depuración termina cuando cada responsabilidad principal tiene un dueño claro, los puntos de entrada siguen siendo compatibles, los contratos están cubiertos por pruebas, el código muerto comprobado fue eliminado, los tiempos están medidos y el sistema puede completar un piloto autorizado sin regresiones en PostgreSQL, navegación ni Excel.
