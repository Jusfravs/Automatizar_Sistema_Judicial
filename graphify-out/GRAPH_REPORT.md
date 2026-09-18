# Graph Report - Automatizar_Sistema_Judicial  (2026-09-18)

## Corpus Check
- 83 files · ~83,489 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 2, .example 1, .cmd 1)

## Summary
- 1268 nodes · 2405 edges · 88 communities (56 shown, 29 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 141 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9c7cb074`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- .inferir_estado_procesal
- RetornoBuscadorTests
- BotJudicial
- ._volver_al_buscador
- reclasificar_desde_sqlite.py
- BotonFalso
- Automation system overview
- Dependencias del proyecto Automatizar_Sistema_Judicial
- GestorCola
- NavegadorArbolContenido
- AgenteExplorador
- RuntimeError
- FrenoNavegacionTests
- preparar_reproceso_causas.py
- GestorCasos
- EnlaceFalso
- Proveedor2Captcha
- prompt_procesador.py
- NavegacionEsatjeTests
- logger_config.py
- MotorInferenciaProcesal
- ._evidencia_pago_perito_posterior
- GestorPostgres
- test_navegacion_esatje.py
- monitorear_esatje.py
- test_migracion.py
- TestMigracionDB
- .test_excepcion_no_controlada_marca_error_y_continua_con_siguiente_causa
- BotJudicialTransaccional
- normalizar_texto
- Q: Continuar revisando la logica del sistema a partir de las preguntas del grafo, conectando o corrigiendo funciones cuando sea necesario sin tocar la inferencia ni la ubicacion por palabras clave
- enriquecer_datos_procesales
- Orquestador
- ._procesar_flujo_autonomo
- ._escrito_pendiente_de_revision_documental
- FilaFalsa
- TestPoblarCola
- Índice de documentación
- TestRecuperarHuerfanos
- ._termino_procesal_presente
- Deterministic navigation state machine
- ._fecha_ordenable
- ._hallazgo_mas_reciente
- ._exclusive_transaction
- PaginaActuacionesApiFalsa
- TestRegistrarResultado
- TestReiniciarErrores
- Q: estas Preguntas sugeridas son errores que el grafo localizo o conoxiones sin logica se ven como posibles errores?
- .procesar_flujo_judicatura
- inicializar_postgres.py
- RespaldoCsvTests
- Path
- TestConfiguracionQuito
- test_regresiones_quito_29.py
- ._segmentar_por_instancia
- limpieza.py
- PaginaMensajeFalsa
- ._seleccionar_rama_activa
- motor_busqueda_web.py
- ._causa_para_formulario
- ResultadoInferencia
- ._crear_respaldo_csv
- calcular_siguiente_fase
- Graphify project policy
- Durable queue recovery workflow
- Cola de extracción
- .test_acta_de_secuestro_preventivo_conserva_calificacion_y_citacion
- .test_control_diario_no_es_citacion_por_prensa_y_fallo_personal_pendiente
- .test_una_sola_contestacion_acreditada_basta_y_usa_escrito_inmediato
- .test_orden_de_certificar_si_hubo_contestacion_no_la_acredita
- .test_escrito_generico_con_adjunto_posterior_marca_revision_documental
- .test_ejecutivo_en_citacion_no_es_mandamiento
- .test_segunda_instancia_activa_clasificacion
- .test_keyword_en_html_no_sobreescribe_fase_real
- .test_ejecutivo_con_mandamiento_real
- Diagnósticos y correcciones
- Historial cronológico de checkpoints
- Planes técnicos
- CaptchaSolucion
- Q: perfecto que este caso vamos a agregar a al proyecto este sistema DE IDs mas los defectos que encontraste
- Q: Revisar la logica del sistema a partir de las preguntas sugeridas sin modificar la inferencia procesal
- .bloquear_ejecucion
- ExportacionSistemasTests
- migrar_sqlite_a_postgres.py
- ._motivo_rechazo_formulario

## God Nodes (most connected - your core abstractions)
1. `TestClasificacionArbol` - 128 edges
2. `BotJudicial` - 81 edges
3. `BotJudicialTransaccional` - 79 edges
4. `GestorCola` - 48 edges
5. `MotorInferenciaProcesal` - 47 edges
6. `NavegacionEsatjeTests` - 40 edges
7. `GestorCasos` - 38 edges
8. `normalizar_texto()` - 29 edges
9. `RetornoBuscadorTests` - 29 edges
10. `AgenteExtractor` - 24 edges

## Surprising Connections (you probably didn't know these)
- `Reglas de inferencia procesal` --semantically_similar_to--> `Clasificación procesal`  [INFERRED] [semantically similar]
  DOCUMENTACION/05_AVANCES/03_Inferencia_y_Excel_Base.md → Prompt_correcion_Filtro.txt
- `Latest material procedural act rule` --semantically_similar_to--> `Classification from confirmed procedural evidence`  [INFERRED] [semantically similar]
  CASOS_PENDIENTES_CORRECCION.md → DOCUMENTACION/01_GENERAL/CONTEXTO_REANUDACION.md
- `_reclasificar_datos()` --uses--> `MotorInferenciaProcesal`  [INFERRED]
  scripts/reclasificar_desde_sqlite.py → src/agente_extractor.py
- `actualizar_todo_quito()` --uses--> `MotorInferenciaProcesal`  [INFERRED]
  scripts/reprocesar_y_exportar_quito.py → src/agente_extractor.py
- `CatalogoProcesalTests` --uses--> `ResultadoInferencia`  [INFERRED]
  tests/test_catalogo_ids.py → src/agente_extractor.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Flujo de clasificación judicial estructurada** — prompt_correcion_filtro_arbol_actuaciones, prompt_correcion_filtro_rama_activa, prompt_correcion_filtro_clasificacion_procesal, prompt_correcion_filtro_salida_json_postgresql [EXTRACTED 1.00]
- **Ecosistema de exportación Excel** — documentacion_05_avances_03_inferencia_y_excel_base_procesar_html_string, documentacion_05_avances_03_inferencia_y_excel_base_exportacion_excel, requirements_openpyxl, requirements_pandas [INFERRED 0.85]
- **Resilient durable judicial-case processing** — documentacion_01_general_readme_processing_pipeline, documentacion_01_general_vision_proyecto_dual_extraction_architecture, documentacion_01_general_vision_proyecto_multilayer_persistence, documentacion_03_planes_plan_correccion_freno_informacion_proceso_durable_folder_result [INFERRED 0.85]
- **Procedural classification from attributable evidence** — casos_pendientes_correccion_material_procedural_act_rule, documentacion_01_general_contexto_reanudacion_confirmed_evidence_classification, documentacion_01_general_vision_proyecto_regla_del_arbol, documentacion_04_diagnosticos_y_correcciones_correccion_fecha_derivada_atomic_classification_evidence [INFERRED 0.95]
- **Safe and auditable e-SATJE navigation flow** — documentacion_03_planes_plan_automatizacion_botones_esatje_navigation_state_machine, documentacion_03_planes_plan_correccion_freno_informacion_proceso_no_navigation_invariant, documentacion_03_planes_plan_solucion_regreso_buscador_no_confirmado_observable_spa_return [INFERRED 0.95]

## Communities (88 total, 29 thin omitted)

### Community 0 - ".inferir_estado_procesal"
Cohesion: 0.03
Nodes (3): Analiza el estado procesal basándose ESTRICTAMENTE en la jerarquía del Árbol de…, Suite de pruebas unitarias para la Regla del Árbol Procesal. Verifica que la…, TestClasificacionArbol

### Community 1 - "RetornoBuscadorTests"
Cohesion: 0.05
Nodes (26): actualizar_casos_fallidos_piloto(), _causa_comparable(), dividir_en_bloques(), _ejecutar_lote(), extraer_ruta_config(), guardar_casos_fallidos(), guardar_csv_o_fallar(), main() (+18 more)

### Community 2 - "BotJudicial"
Cohesion: 0.08
Nodes (16): BotJudicial, Devuelve los datos procesados en la vista actual., Arquitectura Dual: - RUTA PRINCIPAL: Si la API interceptó JSON, procesar…, Ruta Principal: Captura JSON puros de la API Angular de la Judicatura., Navegación jerárquica hacia arriba conservando sesión., Normaliza el numero de causa para comparar portal y archivo de origen., Busca una causa numérica completa sin aceptar sufijos alfanuméricos., Valida primero la columna de proceso y conserva cualquier sufijo. (+8 more)

### Community 3 - "._volver_al_buscador"
Cohesion: 0.14
Nodes (3): Espera una capa de carga breve; falla de forma recuperable si persiste., Inspecciona el buscador sin provocar navegación ni modificar la página., Confirma por estado visible dos observaciones estables del buscador SPA.

### Community 4 - "reclasificar_desde_sqlite.py"
Cohesion: 0.09
Nodes (30): _aplicar_validacion_pertenencia(), _campos_desde_inferencia(), _campos_equivalentes(), _causas_por_sucursal(), _demandados_desde_resultado(), _es_comentario_automatico_obsoleto(), _fecha_canonica(), main() (+22 more)

### Community 5 - "BotonFalso"
Cohesion: 0.12
Nodes (3): BotonFalso, CampoFalso, PaginaEsperaFalsa

### Community 6 - "Automation system overview"
Cohesion: 0.06
Nodes (37): Latest material procedural act rule, Pending case corrections and reinference, Classification from confirmed procedural evidence, Conservative manual-review guard for untyped attachments, Operational resume context, Current e-SATJE operating manual, Regional configuration and data isolation, Visible supervised execution through main.py (+29 more)

### Community 7 - "Dependencias del proyecto Automatizar_Sistema_Judicial"
Cohesion: 0.06
Nodes (31): Configuración de palabras clave de extracción, Palabras clave de mandamiento de ejecución, Política de fecha relevant, training_case, Checkpoint 03: Inferencia enriquecida y base de exportación Excel, Compatibilidad retroactiva, Exportación Excel, procesar_html_string() (+23 more)

### Community 8 - "GestorCola"
Cohesion: 0.09
Nodes (16): main(), Script de reset y recreación limpia de la base de datos estado_casos.db. Crea…, GestorCola, Crea las tablas de reserva, resultados y auditoría si no existen., Motor de Estado y Cola de Tareas en SQLite para desacoplar el flujo de…, Inserta masivamente registros en la tabla juicios con INSERT OR IGNORE para…, Conserva causas PENDIENTE o todavía ausentes de SQLite, respetando el orden., Devuelve una nueva conexión a SQLite con timeout de 30s. (+8 more)

### Community 9 - "NavegadorArbolContenido"
Cohesion: 0.11
Nodes (9): NavegadorArbolContenido, Procesa el contenido HTML recibido como string, extrayendo las actuaciones, la…, Lee y procesa un archivo HTML desde disco delegando en procesar_html_string., Extrae filas de tabla y contenedores estructurados de actuaciones., Escaneo en profundidad de bloques de texto alternativo., Obtiene la fecha de inicio del expediente., Navegador estructural del árbol procesal y de contenido. Implementa la regla de…, Move Up: Escalada por ausencia hacia un contexto más amplio. (+1 more)

### Community 10 - "AgenteExplorador"
Cohesion: 0.09
Nodes (14): AgenteExplorador, Convierte el payload nativo a DataFrame y normaliza sus cabeceras de inmediato., Agente Explorador con dos rutas de extracción: - Primaria: captura XHR/fetch…, Listener pasivo: captura sólo respuestas XHR/fetch válidas de la API judicial., Devuelve el DataFrame creado en el listener, sin reprocesar el JSON original., Retorna el payload JSON original, fuente de verdad de la ruta primaria., Expone el motivo de fallo de la captura para la auditoría transaccional., Regresa al buscador utilizando esperas explícitas condicionales. (+6 more)

### Community 11 - "RuntimeError"
Cohesion: 0.21
Nodes (7): RuntimeError, Espera la habilitación asíncrona del botón antes del clic inicial., Pulsa BUSCAR para que el portal monte/despliegue el CAPTCHA., Indica si el CAPTCHA visible a?n no tiene un token v?lido del operador., Escribe la causa de inmediato y conserva un respaldo para la máscara.…, Espera a que terminen de renderizar actuaciones y controles de archivos., Regresa al formulario y verifica que el ?nico campo de causa est? disponible.

### Community 12 - "FrenoNavegacionTests"
Cohesion: 0.10
Nodes (3): BotonFalso, FrenoNavegacionTests, PaginaFalsa

### Community 13 - "preparar_reproceso_causas.py"
Cohesion: 0.13
Nodes (23): _conectar_postgres(), _eliminar_evidencias(), limpiar(), limpiar_comentario_automatico(), _limpiar_lista_fallidos(), _limpiar_postgres(), main(), normalizar_causa() (+15 more)

### Community 14 - "GestorCasos"
Cohesion: 0.11
Nodes (11): GestorCasos, Carga el Excel usando una copia sombra para evitar bloqueos si está abierto en…, CREATE: Genera o combina el CSV de trabajo desde el Excel original., READ: Obtiene la lista de números de juicio que cumplen con los filtros., Repositorio CRUD de datos para la lectura, actualización y persistencia del…, UPDATE: Inyecta en la fila correspondiente los datos extraídos., Elimina solo registros iguales en todas sus columnas. Un mismo nÃºmero de…, Interpreta fechas del portal, incluidas marcas ISO con zona horaria. (+3 more)

### Community 15 - "EnlaceFalso"
Cohesion: 0.20
Nodes (3): EnlaceFalso, FilaCausaFalsa, PaginaAperturaCausaFalsa

### Community 16 - "Proveedor2Captcha"
Cohesion: 0.09
Nodes (18): CaptchaCredencialError, CaptchaDesafio, CaptchaError, CaptchaProveedorError, CaptchaResolucionTimeout, CaptchaSaldoError, _clave_normalizada(), Proveedor2Captcha (+10 more)

### Community 17 - "prompt_procesador.py"
Cohesion: 0.14
Nodes (14): cargar_plantilla_prompt(), construir_prompt(), _generar_fallback(), limpiar_y_validar_json(), Carga la plantilla de prompt desde el sistema de archivos., Construye el prompt completo reemplazando los marcadores de posición dinámicos…, Limpia cualquier delimitador Markdown de la respuesta del LLM y la parsea como…, Genera un diccionario estructurado de respaldo para no interrumpir el flujo. (+6 more)

### Community 19 - "logger_config.py"
Cohesion: 0.17
Nodes (11): extraer_y_normalizar(), extraer_y_normalizar_dict(), _raise_import_error(), Extrae los datos de la causa desde E-SATJE usando el motor antigravity y…, Retorna el primer registro extraído como dict, o None si no hay datos. Registra…, auditar_csv(), cargar_total_esperado(), Load the expected record total from the project configuration. (+3 more)

### Community 20 - "MotorInferenciaProcesal"
Cohesion: 0.12
Nodes (10): MotorInferenciaProcesal, Motor de Inferencia Procesal Autónoma basado en MODULO_FILTRO_CASOS.md y…, Obtiene el identificador de la persona citada cuando estÃ¡ visible., Exige una coincidencia identificable del demandado en la diligencia., Confirma que cada demandado SATJE fue citado de forma acreditada., Crea una decisi??n at??mica y nunca reutiliza una fecha de otra fase., Evita que un cuaderno deprecatorio altere la fase del principal. API+DOM…, Extrae nÃºmeros de juicio con formato SATJE citados en un documento. (+2 more)

### Community 21 - "._evidencia_pago_perito_posterior"
Cohesion: 0.33
Nodes (3): Normaliza nombres de archivos leídos del listado de SATJE., Identifica una factura o comprobante ligado al servicio pericial., Encuentra evidencia de pago pericial posterior al nombramiento. El nombramiento…

### Community 22 - "GestorPostgres"
Cohesion: 0.10
Nodes (9): GestorPostgres, Gestor de persistencia relacional nativo en PostgreSQL para casos judiciales,…, Guarda o actualiza un expediente procesado y sus actuaciones individuales en…, ConexionFalsa, CursorFalso, PersistenciaPostgresIdsTests, conexion(), skipUnless (+1 more)

### Community 23 - "test_navegacion_esatje.py"
Cohesion: 0.11
Nodes (7): ColeccionFalsa, PaginaCaptchaFalsa, PaginaCargaGlobalPendienteFalsa, PaginaFilasDivFalsa, PaginaFilasFalsa, Imita la lista Angular real, que no usa filas HTML ``tr``., TextoFalso

### Community 24 - "monitorear_esatje.py"
Cohesion: 0.18
Nodes (14): cargar_navegacion(), main(), Ejecuta una sola causa en e-SATJE para diagnosticar la navegaci?n visible., cargar_configuracion(), estado_visible(), extraer_eventos(), guardar_evidencia(), instalar_monitor() (+6 more)

### Community 25 - "test_migracion.py"
Cohesion: 0.18
Nodes (10): Checkpoint 02: Migración SQLite y Recuperación de Cola, Esquema SQLite, estado_casos.db, Migración SQLite, backup_db(), migrar(), Crea un respaldo de la base de datos antes de migrar., Script de migración y verificación para la base de datos SQLite… (+2 more)

### Community 26 - "TestMigracionDB"
Cohesion: 0.12
Nodes (9): Verifica que el esquema de la base de datos es correcto después de la migración., Crea una instancia fresca de GestorCola con una DB temporal., Elimina la DB temporal., Las tres tablas requeridas deben existir tras la inicialización., El método verificar_esquema() debe retornar True con el esquema completo., La tabla juicios debe tener las columnas correctas., La tabla resultados_expediente debe tener las columnas correctas., La tabla eventos_extraccion debe tener las columnas correctas. (+1 more)

### Community 29 - "BotJudicialTransaccional"
Cohesion: 0.11
Nodes (8): BotJudicialTransaccional, recorrer(), Flujo e-SATJE con navegación bloqueada durante cada extracción., Persiste el estado de cada rechazo/timeout sin alterar la navegación., Devuelve una firma durable cuando la API ya entrego las actuaciones. La…, Transforma API/DOM sin hacer clic ni navegar., Guarda evidencia best-effort sin intentar una nueva navegación., CaptchaConfiguracionError

### Community 30 - "normalizar_texto"
Cohesion: 0.11
Nodes (13): es_archivo_por_incumplimiento(), es_notificacion(), es_orden_explicita(), es_verificacion_secretarial(), normalizar_texto(), Prioriza la providencia que ordena completar sobre hitos posteriores., Devuelve los demandados de SATJE con roles procesales removidos., Normaliza texto removiendo tildes, caracteres especiales y convirtiendo a… (+5 more)

### Community 31 - "Q: Continuar revisando la logica del sistema a partir de las preguntas del grafo, conectando o corrigiendo funciones cuando sea necesario sin tocar la inferencia ni la ubicacion por palabras clave"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Continuar revisando la logica del sistema a partir de las preguntas del grafo, conectando o corrigiendo funciones cuando sea necesario sin tocar la inferencia ni la ubicacion por palabras clave, Source Nodes

### Community 32 - "enriquecer_datos_procesales"
Cohesion: 0.22
Nodes (16): Any, actualizar_todo_quito(), canonicalizar_etapa(), canonicalizar_fase(), enriquecer_datos_procesales(), id_etapa(), id_fase(), ids_para_estado() (+8 more)

### Community 33 - "Orquestador"
Cohesion: 0.14
Nodes (10): calcular_dias_fase_actual_df(), GestorEstado, Calcula la columna DIAS EN LA FASE ACTUAL a partir de FECHA INICIAL FASE ACTUAL., Gestor de Estado (Pandas): Procesa y normaliza los resultados extraídos hacia…, Lee el archivo JSON con los datos extraídos por AgenteExtractor, aplana la…, Orquestador, Motor de ejecución central con procesamiento dual: - Intercepción API (Ruta…, Motor de Orquestación Principal Multi-Agente con Arquitectura de Ejecución… (+2 more)

### Community 35 - "._escrito_pendiente_de_revision_documental"
Cohesion: 0.22
Nodes (5): Dada la fase actual encontrada, retorna la siguiente fase y etapa según…, Identifica un escrito cuyo contenido no es visible en SATJE. Un rótulo…, Devuelve el escrito genérico posterior que requiere revisión. La alerta se…, Devuelve el índice numérico de la fase para comparaciones de precedencia., probar_inferencias()

### Community 37 - "TestPoblarCola"
Cohesion: 0.10
Nodes (5): Poblar con una lista de causas debe insertar registros correctamente., Poblar dos veces con las mismas causas no debe duplicar registros., obtener_siguiente() debe cambiar el estado a EN_PROCESO., Verifica la funcionalidad de poblar y gestionar la cola., TestPoblarCola

### Community 38 - "Índice de documentación"
Cohesion: 0.22
Nodes (10): Configuración de AutoCaptcha, Contexto de reanudación, Convención para documentos nuevos, Índice de documentación, Manual de uso, Módulo de filtro de casos, Molde de nuevos cambios, README de documentación general (+2 more)

### Community 39 - "TestRecuperarHuerfanos"
Cohesion: 0.20
Nodes (5): Verifica la recuperación de registros atrapados en EN_PROCESO., Los registros EN_PROCESO deben volver a PENDIENTE., Sin huérfanos, debe retornar 0., Debe registrar un evento en eventos_extraccion por cada huérfano., TestRecuperarHuerfanos

### Community 40 - "._termino_procesal_presente"
Cohesion: 0.33
Nodes (4): _decodificar_entidades_satje(), Convierte entidades no estandar de SATJE solo para reglas contextuales., Evalúa la similitud semántica del texto encontrado con la taxonomía judicial de…, Evita que conectores linguisticos activen fases procesales.

### Community 41 - "Deterministic navigation state machine"
Cohesion: 0.25
Nodes (8): Folder-scoped API and DOM extraction, Deterministic navigation state machine, e-SATJE button automation plan, Durable folder result contract, No-navigation extraction invariant, Transactional extraction brake plan, Observable SPA search return, Unconfirmed search-return fix

### Community 42 - "._fecha_ordenable"
Cohesion: 0.25
Nodes (3): Convierte fechas de actuaciones a un valor comparable sin alterar su formato de…, Obtiene el auto que abre formalmente la fase de remate. ``PUBLICACION Y FECHA…, Ubica el escrito que una providencia vincula con la contestación. La fecha…

### Community 43 - "._hallazgo_mas_reciente"
Cohesion: 0.20
Nodes (5): Devuelve la evidencia fechada m??s reciente de una fase, sin depender del orden…, Vincula la fase de citacion con el acta practicada, no con su mención., Reune la evidencia fechada de una fase en todo el historial disponible., Busca la evidencia fechada mas reciente de una fase en todo el historial., Prioriza el acto de calificacion, no menciones incidentales posteriores.

### Community 44 - "._exclusive_transaction"
Cohesion: 0.20
Nodes (5): Método transaccional atómico: Obtiene la primera causa con estado 'PENDIENTE' y…, Reserva atómicamente una causa concreta antes de procesarla. El flujo normal…, Persiste el resultado del expediente y su estado final en una única transacción…, Indica si un resultado conserva evidencia procesal reutilizable., Abre una conexión en modo autocommit (isolation_level=None) y emite BEGIN…

### Community 46 - "TestRegistrarResultado"
Cohesion: 0.25
Nodes (4): Verifica el registro transaccional de resultados., Registrar un resultado debe cambiar el estado a PROCESADO., El resultado debe persistirse en la tabla resultados_expediente., TestRegistrarResultado

### Community 47 - "TestReiniciarErrores"
Cohesion: 0.25
Nodes (4): Verifica la lógica de reintentos de registros con estado ERROR., Los registros en ERROR con reintentos < max deben volver a PENDIENTE., Los registros que ya alcanzaron el máximo de reintentos no deben reiniciarse., TestReiniciarErrores

### Community 48 - "Q: estas Preguntas sugeridas son errores que el grafo localizo o conoxiones sin logica se ven como posibles errores?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: estas Preguntas sugeridas son errores que el grafo localizo o conoxiones sin logica se ven como posibles errores?, Source Nodes

### Community 49 - ".procesar_flujo_judicatura"
Cohesion: 0.20
Nodes (5): Modo Híbrido Asistido con Arquitectura de Ejecución Dual: 1. Prepara búsqueda…, Inicia el navegador Chromium con bypass anti-automatización para F5 WAF y…, Cierra la sesión del navegador., Verifica si la página y el contexto del navegador están activos. Si se cerró el…, Verifica si la sesión del portal sigue activa y el navegador está vivo. Si…

### Community 50 - "inicializar_postgres.py"
Cohesion: 0.33
Nodes (4): crear_base_de_datos(), inicializar_esquema(), Crea la base de datos si no existe., Crea tablas, índices y vistas analíticas para pgAdmin.

### Community 51 - "RespaldoCsvTests"
Cohesion: 0.19
Nodes (5): _gestor_con_csv(), Pruebas de tolerancia a bloqueos temporales del CSV en Windows/OneDrive., RespaldoCsvTests, leer(), reemplazar()

### Community 52 - "Path"
Cohesion: 0.31
Nodes (11): DataFrame, Path, _cargar_json(), _construir_reporte_regional(), _crear_sqlite_vacio(), main(), _normalizar_columnas(), preparar() (+3 more)

### Community 54 - "test_regresiones_quito_29.py"
Cohesion: 0.47
Nodes (4): _fecha_iso(), _normalizar_causa(), skipUnless, TestRegresionesQuito29

### Community 56 - "limpieza.py"
Cohesion: 0.50
Nodes (4): ejecutar_limpieza(), Manejador para forzar eliminación de archivos con atributo de solo lectura en…, Elimina de forma recursiva y segura el directorio temp_htmls/ conservando…, _remove_readonly()

### Community 59 - "motor_busqueda_web.py"
Cohesion: 0.13
Nodes (17): Detección y combinación de múltiples folders, AgenteExtractor, Agente Extractor Semántico y Autónomo (e-SATJE). Analiza el contenido completo…, _load_extraction_keywords(), Carga una lista de keywords desde rutas conocidas o desde un archivo YAML/TSV…, Pruebas unitarias para validar las reglas de Inferencia Procesal Autónoma…, load_html(), load_json() (+9 more)

### Community 61 - "ResultadoInferencia"
Cohesion: 0.36
Nodes (3): Resultado enriquecido de la inferencia procesal. Compatible con desempaquetado…, ResultadoInferencia, tuple

### Community 62 - "._crear_respaldo_csv"
Cohesion: 0.33
Nodes (3): Reconoce bloqueos habituales de Windows, OneDrive y antivirus., Crea el .bak y tolera bloqueos breves sin omitir la salvaguarda., SAVE: Reemplaza atómicamente el CSV tras crear su respaldo.

### Community 63 - "calcular_siguiente_fase"
Cohesion: 0.67
Nodes (3): calcular_siguiente_fase(), REMATE y CONGELAMIENTO como estados finales, ORDEN_FASES

### Community 82 - "Q: perfecto que este caso vamos a agregar a al proyecto este sistema DE IDs mas los defectos que encontraste"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: perfecto que este caso vamos a agregar a al proyecto este sistema DE IDs mas los defectos que encontraste, Source Nodes

### Community 83 - "Q: Revisar la logica del sistema a partir de las preguntas sugeridas sin modificar la inferencia procesal"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Revisar la logica del sistema a partir de las preguntas sugeridas sin modificar la inferencia procesal, Source Nodes

### Community 86 - "migrar_sqlite_a_postgres.py"
Cohesion: 0.83
Nodes (3): migrar_base_sqlite(), migrar_todo(), obtener_conexion_postgres()

## Knowledge Gaps
- **48 isolated node(s):** `Answer`, `Outcome`, `Source Nodes`, `Answer`, `Outcome` (+43 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 461 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Work-memory lessons

**Preferred sources** — corroborated by past sessions; start here.
- `MotorInferenciaProcesal` (2× useful, score=1.99776437) _(code changed — re-verify)_
- `GestorCola` (2× useful, score=1.99776437) _(code changed — re-verify)_

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BotJudicial` connect `BotJudicial` to `RetornoBuscadorTests`, `._procesar_flujo_autonomo`, `._volver_al_buscador`, `NavegadorArbolContenido`, `RuntimeError`, `FrenoNavegacionTests`, `Proveedor2Captcha`, `.procesar_flujo_judicatura`, `NavegacionEsatjeTests`, `logger_config.py`, `MotorInferenciaProcesal`, `test_navegacion_esatje.py`, `CaptchaSolucion`, `._motivo_rechazo_formulario`, `monitorear_esatje.py`, `motor_busqueda_web.py`, `._causa_para_formulario`, `BotJudicialTransaccional`?**
  _High betweenness centrality (0.232) - this node is a cross-community bridge._
- **Why does `GestorCola` connect `GestorCola` to `RetornoBuscadorTests`, `Orquestador`, `TestPoblarCola`, `TestRecuperarHuerfanos`, `._exclusive_transaction`, `TestRegistrarResultado`, `TestReiniciarErrores`, `logger_config.py`, `Path`, `.bloquear_ejecucion`, `test_migracion.py`, `TestMigracionDB`?**
  _High betweenness centrality (0.151) - this node is a cross-community bridge._
- **Why does `MotorInferenciaProcesal` connect `MotorInferenciaProcesal` to `enriquecer_datos_procesales`, `.inferir_estado_procesal`, `BotJudicial`, `._escrito_pendiente_de_revision_documental`, `reclasificar_desde_sqlite.py`, `._termino_procesal_presente`, `._fecha_ordenable`, `._hallazgo_mas_reciente`, `._evidencia_pago_perito_posterior`, `test_regresiones_quito_29.py`, `._segmentar_por_instancia`, `._seleccionar_rama_activa`, `motor_busqueda_web.py`, `normalizar_texto`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `TestClasificacionArbol` (e.g. with `AgenteExtractor` and `MotorInferenciaProcesal`) actually correct?**
  _`TestClasificacionArbol` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `BotJudicial` (e.g. with `AgenteExtractor` and `MotorInferenciaProcesal`) actually correct?**
  _`BotJudicial` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `BotJudicialTransaccional` (e.g. with `CaptchaConfiguracionError` and `CaptchaDesafio`) actually correct?**
  _`BotJudicialTransaccional` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `GestorCola` (e.g. with `Orquestador` and `PersistenciaTransaccionalTests`) actually correct?**
  _`GestorCola` has 7 INFERRED edges - model-reasoned connections that need verification._