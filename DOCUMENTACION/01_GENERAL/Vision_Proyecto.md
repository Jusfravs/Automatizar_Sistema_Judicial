# Visión General y Arquitectura del Proyecto (e-SATJE)

Este documento detalla el funcionamiento interno, la arquitectura multi-agente, el esquema de persistencia de datos, el ciclo de vida de una causa y el propósito de cada archivo dentro del proyecto de **Automatización del Sistema Judicial (e-SATJE)**.

---

## 1. Visión General del Proyecto
0	
El sistema es una plataforma multi-agente autónoma y de alta resiliencia diseñada para la **consulta, extracción, análisis semántico procesal y consolidación masiva** de juicios y causas legales desde el portal e-SATJE del Consejo de la Judicatura del Ecuador.

El proyecto está diseñado para procesar lotes masivos (ej. 4,017 juicios) garantizando:
1. **Resiliencia ante fallos**: Control transaccional atómico mediante SQLite para evitar duplicados o pérdida de progreso si el proceso se interrumpe.
2. **Arquitectura de Ejecución Dual**:
   - **Ruta Primaria (Rápida - XHR/API)**: Intercepta directamente la respuesta JSON enviada por los servidores del e-SATJE (vía `antigravity_cli` o listeners XHR).
   - **Ruta de Respaldo (RPA / Playwright)**: Si la API falla, automatiza un navegador Chromium headless, navega la interfaz Angular y descarga el HTML para analizarlo offline con `BeautifulSoup4`.
3. **Motor de Inferencia Procesal Autónoma ("Regla del Árbol")**: Clasifica automáticamente el expediente dentro de 6 etapas legales y 17 fases procesales, calculando además los días transcurridos en la fase actual.

---

## 2. ¿Cómo se Guarda la Información? (Persistencia y Almacenamiento)

El sistema utiliza un esquema de almacenamiento multicapa para asegurar que ningún dato se pierda:

```
                  +--------------------------------------------------------+
                  |         EXCEL / CSV FUENTE DE ENTRADA                  |
                  | (data/REPORTE JUICIOS PARA REVISIÓN JULIO.xlsx)       |
                  +---------------------------+----------------------------+
                                              |
                                              v
                  +--------------------------------------------------------+
                  |           BASE DE DATOS RELACIONAL SQLITE              |
                  |                   (estado_casos.db)                    |
                  |  - juicios (cola de estados: PENDIENTE/EN_PROCESO...)   |
                  |  - resultados_expediente (datos JSON estructurados)    |
                  |  - eventos_extraccion (auditoría de errores/rescates)  |
                  +---------------------------+----------------------------+
                                              |
                          +-------------------+-------------------+
                          |                                       |
                          v                                       v
      +---------------------------------------+ +---------------------------------------+
      |        JSON ATÓMICO LOCAL             | |            REPORTES FINALES           |
      |         datos_extraidos.json          | |  - data/reporte_trabajo.csv (CSV)   |
      | (Guardado temporal atómico .tmp->json)| |  - data/REPORTE_PROCESADO_FINAL.xlsx|
      +---------------------------------------+ +---------------------------------------+
```

### Capas de Almacenamiento

1. **Base de Datos SQLite (`estado_casos.db`)**: Es el corazón del estado del sistema. Contiene 3 tablas principales gestionadas en `src/gestor_cola.py`:
   - **`juicios`**: Mantiene la cola de trabajo.
     - `numero_causa` (PK): Código de la causa (ej. `23331-2022-04261`).
     - `estado`: `PENDIENTE`, `EN_PROCESO`, `PROCESADO`, `ERROR`.
     - `ruta_html`: Ubicación del HTML guardado si se usó la ruta de respaldo DOM.
     - `reintentos`: Número de fallos sufridos antes de reintentar.
   - **`resultados_expediente`**: Guarda la información extraída.
     - `numero_causa` (PK / FK).
     - `origen`: `ANTIGRAVITY_XHR` o `DOM_BS4`.
     - `datos_json`: Payload completo con el historial de actuaciones, fechas, etapa y fase procesal.
     - `actualizado_en`: Timestamp automático.
   - **`eventos_extraccion`**: Registra logs de auditoría interna, reconexiones o recuperación de registros huérfanos.

2. **Archivo JSON Intermedio (`datos_extraidos.json`)**:
   - Cada causa procesada con éxito se anexa a este archivo. Para evitar corrupción si el programa se apaga a mitad de escritura, se escribe primero en un archivo `.tmp` mediante `tempfile.mkstemp()` y luego se reemplaza atómicamente con `os.replace()`.

3. **Reporte CSV de Trabajo (`data/reporte_trabajo.csv`)**:
   - Se inicializa clonando la estructura del Excel original. En este archivo se actualizan incrementalmente las columnas procesadas (`ETAPA_PROCESAL`, `FASE_PROCESAL`, `FECHA INICIAL FASE ACTUAL`, `DIAS EN LA FASE ACTUAL`).

4. **Reporte Excel Final (`data/REPORTE_PROCESADO_FINAL.xlsx`)**:
   - Es el entregable final generado por `src/gestor_casos.py` o `src/gestor_estado.py`. Incluye la matriz completa con los días transcurridos calculados en tiempo real contra la fecha de ejecución.

5. **Logs y Archivos de Diagnóstico**:
   - **`ejecucion_produccion.log`**: Log rotativo central de todas las operaciones.
   - **`data/casos_fallidos.txt`**: Lista de juicios que dieron error para facilitar ejecuciones posteriores.

---

## 3. Flujo de Procesamiento Paso a Paso (Ciclo de Vida de un Juicio)

```
1. INICIO/REANUDACIÓN
   └── Carga de config.json y poblamiento de SQLite (INSERT OR IGNORE)
   └── Recuperación de registros huérfanos ('EN_PROCESO' -> 'PENDIENTE')

2. RESERVA ATÓMICA
   └── GestorCola.obtener_siguiente() usa 'BEGIN IMMEDIATE' en SQLite
   └── Marca la causa como 'EN_PROCESO' atómicamente

3. EXTRACCIÓN (Dual Execution)
   ├── Intentar Ruta 1: antigravity_adapter / API XHR JSON
   │    └── Si devuelve datos -> Transición rápida
   └── Fallback Ruta 2: Agente Explorador (Playwright Chromium)
        └── Navega e-SATJE -> Aplica Freno de Ejecución -> Descarga HTML a temp_htmls/

4. ANÁLISIS & INFERENCIA PROCESAL
   └── AgenteExtractor / MotorInferenciaProcesal analiza el Árbol de Actuaciones
   └── Aplica la "Regla del Árbol" y la Taxonomía de 6 Etapas / 17 Fases
   └── Deduce: ETAPA_PROCESAL, FASE_PROCESAL, FECHA_INICIAL_FASE_ACTUAL

5. PERSISTENCIA TRANSACCIONAL
   └── SQLite guarda resultado y pasa estado a 'PROCESADO'
   └── Inyección en datos_extraidos.json y autoguardado en reporte_trabajo.csv
   └── Espera aleatoria (backoff 2-4s) para evitar bloqueos F5 WAF

6. EXPORTACIÓN FINAL
   └── Cálculo automático de 'DIAS EN LA FASE ACTUAL'
   └── Generación de data/REPORTE_PROCESADO_FINAL.xlsx
```

---

## 4. Análisis Detallado de Cada Archivo del Proyecto

### Archivos de la Raíz del Proyecto

* **`main.py`**:
  - Punto de entrada principal interactivo/CLI.
  - Carga los casos desde el CSV configurado, inicializa la cola SQLite y lanza el bot en modo asistido/visible. Soporta recibir un número de juicio por parámetro (ej. `python main.py 23331-2022-04261`) para reanudar desde esa causa.

* **`migracion_db.py`**:
  - Script de inicialización y mantenimiento de la base de datos SQLite.
  - Crea copias de seguridad automáticas con timestamp (`estado_casos.db.backup_YYYYMMDD_HHMMSS`), construye el esquema de tablas e índices y recupera registros interrumpidos.

* **`config.json`**:
  - Archivo de configuración central. Define los filtros activos (Sucursal, Oficina, Estado Judicial), rutas de archivos CSV/Excel, URL del portal e-SATJE e intervalo de autoguardado.

* **`Prompt_correcion_Filtro.txt`**:
  - Prompt maestro y matriz de instrucciones para la clasificación mediante modelos de lenguaje (LLM), detallando la Taxonomía e-SATJE y la Regla del Árbol.

* **[`MODULO_FILTRO_CASOS.md`](../02_MODULOS_Y_CONFIGURACION/MODULO_FILTRO_CASOS.md)**:
  - Especificación técnica y de negocio de las 6 etapas procesales e instrucciones semánticas de deducción procesal.

* **`test_inferencia_casos.py`**:
  - Script interactivo de validación sin conexión a Internet. Contiene 10 casos de prueba con diferentes escenarios de actuaciones legales para verificar que la lógica infiera la etapa procesal correcta.

* **`requirements.txt`**:
  - Lista de dependencias de Python: `playwright`, `beautifulsoup4`, `lxml`, `pandas`, `openpyxl`, `psycopg2-binary` y `PyYAML`.
  - Las pruebas usan `unittest`; `pytest` no es una dependencia requerida en este equipo.

---

### Módulo Principal (`src/`)

* **`main.py`**:
  - Punto de entrada operativo visible. Es el flujo recomendado para lotes supervisados y para la ventana de contingencia de CAPTCHA, limitada a 30 segundos.

* **`src/orquestador.py`** (`Orquestador`):
  - Orquestador del ciclo de trabajo masivo e invisible (*headless*). Controla el bucle continuo de consumo de la cola, la ejecución dual, los reintentos automáticos de errores con *exponential backoff* y la llamada al reporte final.

* **`src/gestor_cola.py`** (`GestorCola`):
  - Administra `estado_casos.db`. Utiliza `BEGIN IMMEDIATE` para garantizar exclusividad transaccional de lectura y reserva de causas entre hilos o procesos.

* **`src/agente_explorador.py`** (`AgenteExplorador`):
  - Motor RPA automatizado con Playwright Chromium. Bloquea la carga de imágenes, CSS y fuentes para maximizar velocidad. Escucha respuestas XHR de la API y, si esta falla, realiza el respaldo descargando el HTML a `temp_htmls/`.

* **`src/agente_extractor.py`** (`AgenteExtractor`, `MotorInferenciaProcesal`, `NavegadorArbolContenido`):
  - Motor de extracción semántica offline. Parsea HTML estructurado mediante `BeautifulSoup` y `lxml`.
  - Implementa la **"Regla del Árbol"**: evalúa el avance según la instancia procesal (Primera Instancia, Segunda Instancia, Casación) y prioriza la actuación relevante más reciente para evitar falsos positivos con palabras clave sueltas.

* **`src/gestor_casos.py`** (`GestorCasos`):
  - Repositorio CRUD para el archivo `reporte_trabajo.csv` y exportación a Excel. Implementa la autoreparación desde el Excel original si el CSV está dañado y calcula los días en la fase actual.

* **`src/gestor_estado.py`** (`GestorEstado`):
  - Convierte los registros JSON extraídos (`datos_extraidos.json`) a un DataFrame de Pandas utilizando `pd.json_normalize()` para generar la tabla procesada final.

* **`src/prompt_procesador.py`**:
  - Formatea prompts dinámicos y realiza la limpieza y validación estricta de JSONs retornados por el modelo de IA. Genera un objeto fallback seguro si el JSON resulta inválido.

* **`src/motor_busqueda_web.py`** (`BotJudicial`):
  - Implementación asistida para navegar en vivo en la interfaz de la Judicatura con bypass anti-automatización para el firewall F5 WAF.

* **`src/antigravity_adapter.py`**:
  - Adaptador de integración con la suite `antigravity_cli`. Permite llamar la extracción directa por red sin abrir el navegador.

* **`src/auditor.py`**:
  - Valida la integridad del lote procesado. Compara el total de filas del CSV contra el valor `total_esperado` (4,017) de `config.json` y revisa que no existan campos clave nulos.

* **`src/limpieza.py`**:
  - Purga la carpeta de archivos HTML temporales (`temp_htmls/`) sin tocar la base de datos `estado_casos.db`.

* **`src/logger_config.py`**:
  - Configura el sistema de logging con salida formateada hacia la consola y el archivo `ejecucion_produccion.log`.

---

### Scripts de Mantenimiento (`scripts/`)

* **`scripts/reset_db.py`**:
  - Recrea una base de datos `estado_casos.db` totalmente limpia desde cero previa creación de backup en la carpeta `backups/`.
* **`scripts/persist_and_advance.py`**:
  - Fuerza la persistencia manual de una causa probada en CSV y SQLite y ejecuta automáticamente la siguiente en cola.
* **`scripts/analyze_api.py`** y **`scripts/analyze_latest_html.py`**:
  - Herramientas de diagnóstico rápido para analizar respuestas JSON e inspeccionar la estructura del último HTML descargado.
* **`scripts/run_bot_api.py`**:
  - Ejecución ligera de prueba para la extracción por red.

---

### Pruebas Automatizadas (`tests/`)

* **`tests/test_clasificacion_arbol.py`**: Pruebas unitarias de las 17 fases y de la jerarquía de ramas del árbol procesal.
* **`tests/test_extraccion_api.py`**: Pruebas de integración con la API REST del e-SATJE.
* **`tests/test_extraccion_integration.py`**: Pruebas de parsing end-to-end con archivos HTML reales.
* **`tests/test_migracion.py`**: Verificación del esquema de base de datos SQLite y recuperaciones.
* **`tests/test_prompt_procesador.py`**: Validación de funciones de formateo y fallback de respuestas JSON.

---

## 5. Taxonomía Legal e Inferencia Procesal (Las 6 Etapas)

El motor clasifica cada juicio dentro de la siguiente jerarquía oficial:

1. **ETAPA 1 PRESENTACION Y CALIFICACION**:
   - `1.1 PRESENTAR DEMANDA` (Ingreso de causa, carátula de juicio)
   - `1.2 COMPLETAR/ACLARAR DEMANDA` (Escritos de aclaración)
   - `1.3 CALIFICACION` (Auto inicial que admite la demanda a trámite)
2. **ETAPA 2 CITACION**:
   - `2.1 CITACION (PERSONA/BOLETA)` (Boletas fijadas o acta de citación personal)
   - `2.2 CITACION POR PRENSA` (Extractos de citación publicados en periódicos)
3. **ETAPA 3 CONTESTACION**:
   - `3.1 CONTESTACION` (Escrito de contestación u oposición de excepciones)
4. **ETAPA 4 AUDIENCIA**:
   - `4.1 FIJACION FECHA AUDIENCIA` (Señalamiento/convocatoria a audiencia preliminar o de juicio)
   - `4.2 AUDIENCIA / ACTA RESUMEN` (Celebración de la audiencia / acta resumen)
   - `4.3 ACUERDO DE MEDIACION` (Acta o convenio de mediación)
5. **ETAPA 5 SENTENCIA**:
   - `5.1 SENTENCIA EMITIDA POR EL JUEZ` (Fallo o resolución oral/escrita)
   - `5.2 APELACION` (Recurso de alzada presentado ante Corte Provincial)
   - `5.3 SENTENCIA EJECUTORIADA` (Razón de ejecutoria; la causa gana firmeza)
6. **ETAPA 6 LIQUIDACION Y EMBARGO**:
   - `6.1 LIQUIDACION PERITO LIQUIDADOR` (Informe de liquidación de capital e intereses)
   - `6.2 MANDAMIENTO DE EJECUCION` (Orden judicial de pago)
   - `6.3 EMBARGO` (Acta de embargo de bienes/vehículos)
   - `6.4 REMATE` (Convocatoria a subasta pública de bienes)
   - `6.5 CONGELAMIENTO DE CUENTAS / CIERRE` (Oficios de la Superintendencia de Bancos o retención de fondos bancarios)
