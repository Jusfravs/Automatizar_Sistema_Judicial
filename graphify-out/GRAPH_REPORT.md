# Graph Report - Automatizar_Sistema_Judicial  (2026-10-02)

## Corpus Check
- 136 files · ~122,304 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 2, .cmd 2, .example 1)

## Summary
- 1916 nodes · 3787 edges · 121 communities (89 shown, 29 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 238 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2a27c4a6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- .inferir_estado_procesal
- RetornoBuscadorTests
- BotJudicial
- seleccionar_casos
- Orquestador
- consola.py
- Current e-SATJE operating manual
- Dependencias del proyecto Automatizar_Sistema_Judicial
- ._connection
- ._repo
- AgenteExplorador
- RuntimeError
- MotorInferenciaProcesal
- preparar_reproceso_causas.py
- GestorCasos
- EnlaceFalso
- Proveedor2Captcha
- prompt_procesador.py
- ._capturar_adjuntos_pago_perito
- antigravity_adapter.py
- BotJudicialTransaccional
- ControlFalso
- GestorPostgres
- migrar_supabase_gratis.py
- monitorear_esatje.py
- validar_pertenencia_cartera
- TestMigracionDB
- .test_excepcion_no_controlada_marca_error_y_continua_con_siguiente_causa
- FilaFalsa
- RenovadorLease
- test_navegacion_esatje.py
- Q: Continuar revisando la logica del sistema a partir de las preguntas del grafo, conectando o corrigiendo funciones cuando sea necesario sin tocar la inferencia ni la ubicacion por palabras clave
- enriquecer_datos_procesales
- Plan maestro: historial procesal e inferencia híbrida con NVIDIA NIM
- NavegacionEsatjeTests
- datetime
- TestPoblarCola
- Índice de documentación
- TestRecuperarHuerfanos
- TestRegistrarResultado
- Deterministic navigation state machine
- Contexto de reanudación
- ConfiguracionConcurrencia
- RespaldoCsvTests
- InterfazCMD
- preparar_quito.py
- Plan de depuración modular multiagente
- Q: estas Preguntas sugeridas son errores que el grafo localizo o conoxiones sin logica se ven como posibles errores?
- test_regresiones_quito_29.py
- inicializar_postgres.py
- ProcesadorCaso
- RepositorioColaSQLite
- TestConfiguracionQuito
- RepositorioColaPostgres
- ._segmentar_por_instancia
- normalizar_texto
- main.py
- ._seleccionar_rama_activa
- CoordinadorConcurrente
- reclasificar_desde_sqlite.py
- ._inicializar_csv
- TestExtraccionIntegration
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
- test_concurrencia_postgres.py
- .test_ejecutivo_con_mandamiento_real
- Diagnósticos y correcciones
- Historial cronológico de checkpoints
- Planes técnicos
- Contrato operativo: historial e inferencia con NVIDIA
- Q: perfecto que este caso vamos a agregar a al proyecto este sistema DE IDs mas los defectos que encontraste
- Q: Revisar la logica del sistema a partir de las preguntas sugeridas sin modificar la inferencia procesal
- ExportadorResultadosEjecucion
- Procedural phase filtering taxonomy
- ._crear_respaldo_csv
- e-SATJE project architecture
- .registrar_resultado_transaccional
- _reclasificar_datos
- PostgreSQL y procesamiento concurrente
- PaginaActuacionesApiFalsa
- motor_busqueda_web.py
- SeleccionLotesPostgresTests
- ._causa_para_formulario
- Q: Implementar un Excel final profesional sin alterar la inferencia ni la hoja de carga
- Manual de uso de la consola CMD
- NavegadorArbolContenido
- CaptchaConfiguracionError
- TestReiniciarErrores
- GestorCola
- Estado de pausa de la depuración multiagente
- coordinador_concurrente.py
- Classification from confirmed procedural evidence
- Conservative manual-review guard for untyped attachments
- test_migracion.py
- ejecutar_lote_postgres
- ._decision_con_evidencia
- CaptchaSolucion
- FrenoNavegacionTests
- limpieza.py
- .bloquear_ejecucion
- Equipo de agentes de desarrollo
- .procesar_flujo_judicatura
- PostgreSQL and pgAdmin guide
- PaginaMensajeFalsa
- .test_keyword_en_html_no_sobreescribe_fase_real
- Migración de la base judicial a Supabase Free
- ejecucion.py
- .exportar_excel
- ._extraer_informacion_proceso

## God Nodes (most connected - your core abstractions)
1. `TestClasificacionArbol` - 128 edges
2. `BotJudicial` - 90 edges
3. `BotJudicialTransaccional` - 79 edges
4. `GestorCola` - 57 edges
5. `RepositorioColaPostgres` - 57 edges
6. `GestorCasos` - 54 edges
7. `MotorInferenciaProcesal` - 52 edges
8. `NavegacionEsatjeTests` - 40 edges
9. `InterfazCMD` - 35 edges
10. `normalizar_texto()` - 31 edges

## Surprising Connections (you probably didn't know these)
- `Reglas de inferencia procesal` --semantically_similar_to--> `Clasificación procesal`  [INFERRED] [semantically similar]
  DOCUMENTACION/05_AVANCES/03_Inferencia_y_Excel_Base.md → Prompt_correcion_Filtro.txt
- `Latest material procedural act rule` --semantically_similar_to--> `Classification from confirmed procedural evidence`  [INFERRED] [semantically similar]
  CASOS_PENDIENTES_CORRECCION.md → DOCUMENTACION/01_GENERAL/CONTEXTO_REANUDACION.md
- `_repositorio()` --uses--> `RepositorioColaPostgres`  [INFERRED]
  consola.py → src/repositorio_postgres.py
- `main()` --uses--> `ConfiguracionConcurrencia`  [INFERRED]
  main.py → src/ejecucion.py
- `migrar()` --uses--> `RepositorioColaPostgres`  [INFERRED]
  scripts/backfill_historial_ia_postgres.py → src/repositorio_postgres.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Flujo de clasificación judicial estructurada** — prompt_correcion_filtro_arbol_actuaciones, prompt_correcion_filtro_rama_activa, prompt_correcion_filtro_clasificacion_procesal, prompt_correcion_filtro_salida_json_postgresql [EXTRACTED 1.00]
- **Ecosistema de exportación Excel** — documentacion_05_avances_03_inferencia_y_excel_base_procesar_html_string, documentacion_05_avances_03_inferencia_y_excel_base_exportacion_excel, requirements_openpyxl, requirements_pandas [INFERRED 0.85]
- **Resilient durable judicial-case processing** — documentacion_01_general_readme_processing_pipeline, documentacion_01_general_vision_proyecto_dual_extraction_architecture, documentacion_01_general_vision_proyecto_multilayer_persistence, documentacion_03_planes_plan_correccion_freno_informacion_proceso_durable_folder_result [INFERRED 0.85]
- **Procedural classification from attributable evidence** — casos_pendientes_correccion_material_procedural_act_rule, documentacion_01_general_contexto_reanudacion_confirmed_evidence_classification, documentacion_01_general_vision_proyecto_regla_del_arbol, documentacion_04_diagnosticos_y_correcciones_correccion_fecha_derivada_atomic_classification_evidence [INFERRED 0.95]
- **Safe and auditable e-SATJE navigation flow** — documentacion_03_planes_plan_automatizacion_botones_esatje_navigation_state_machine, documentacion_03_planes_plan_correccion_freno_informacion_proceso_no_navigation_invariant, documentacion_03_planes_plan_solucion_regreso_buscador_no_confirmado_observable_spa_return [INFERRED 0.95]

## Communities (121 total, 29 thin omitted)

### Community 0 - ".inferir_estado_procesal"
Cohesion: 0.03
Nodes (3): Analiza el estado procesal basándose ESTRICTAMENTE en la jerarquía del Árbol de…, Suite de pruebas unitarias para la Regla del Árbol Procesal. Verifica que la…, TestClasificacionArbol

### Community 1 - "RetornoBuscadorTests"
Cohesion: 0.13
Nodes (8): PaginaRetornoFalsa, RetornoBuscadorTests, esperar(), ir_buscador(), esperar(), esperar(), procesar(), volver()

### Community 2 - "BotJudicial"
Cohesion: 0.08
Nodes (14): BotJudicial, _load_extraction_keywords(), Arquitectura Dual: - RUTA PRINCIPAL: Si la API interceptó JSON, procesar…, Ruta Principal: Captura JSON puros de la API Angular de la Judicatura., Navegación jerárquica hacia arriba conservando sesión., Carga una lista de keywords desde rutas conocidas o desde un archivo YAML/TSV…, Confirma que Angular ya mont? el control CAPTCHA en el formulario., Motor RPA Asistido con Arquitectura de Ejecución Dual para e-SATJE: 1. Ruta… (+6 more)

### Community 3 - "seleccionar_casos"
Cohesion: 0.12
Nodes (5): dividir_en_bloques(), Divide un lote largo en sesiones acotadas de navegador., Aplica modos acotados o el inicio legado sin ampliar silenciosamente el lote., seleccionar_casos(), SeleccionEjecucionTests

### Community 4 - "Orquestador"
Cohesion: 0.14
Nodes (10): calcular_dias_fase_actual_df(), GestorEstado, Calcula la columna DIAS EN LA FASE ACTUAL a partir de FECHA INICIAL FASE ACTUAL., Gestor de Estado (Pandas): Procesa y normaliza los resultados extraídos hacia…, Lee el archivo JSON con los datos extraídos por AgenteExtractor, aplana la…, Orquestador, Motor de ejecución central con procesamiento dual: - Intercepción API (Ruta…, Motor de Orquestación Principal Multi-Agente con Arquitectura de Ejecución… (+2 more)

### Community 5 - "consola.py"
Cohesion: 0.07
Nodes (35): ArgumentParser, aplicar_migraciones(), _config_perfil(), construir_parser(), diagnostico(), ejecuciones(), _json(), main() (+27 more)

### Community 6 - "Current e-SATJE operating manual"
Cohesion: 0.19
Nodes (12): Operational resume context, Current e-SATJE operating manual, Regional configuration and data isolation, Visible supervised execution through main.py, Automation system overview, AutoCaptcha configuration, API-first CAPTCHA with bounded human fallback, AutoCaptcha API implementation plan (+4 more)

### Community 7 - "Dependencias del proyecto Automatizar_Sistema_Judicial"
Cohesion: 0.06
Nodes (31): Configuración de palabras clave de extracción, Palabras clave de mandamiento de ejecución, Política de fecha relevant, training_case, Checkpoint 03: Inferencia enriquecida y base de exportación Excel, Compatibilidad retroactiva, Exportación Excel, procesar_html_string() (+23 more)

### Community 8 - "._connection"
Cohesion: 0.10
Nodes (10): Inserta masivamente registros en la tabla juicios con INSERT OR IGNORE para…, Conserva causas PENDIENTE o todavía ausentes de SQLite, respetando el orden., Devuelve una nueva conexión a SQLite con timeout de 30s., Actualiza el estado de una causa y opcionalmente su ruta_html., Gestiona una conexión SQLite con rollback automático ante excepciones., Registra fallos de captura sin cancelar la ruta de respaldo DOM., Retorna un diccionario con el conteo de registros agrupados por estado., Cambia el estado de 'ERROR' a 'PENDIENTE' e incrementa en 1 la columna… (+2 more)

### Community 9 - "._repo"
Cohesion: 0.12
Nodes (5): DespachoMainTests, PreparacionLotePostgresTests, crear_pg(), listar_procesadas(), Contratos de despacho de la CLI sin navegador ni base de datos real.

### Community 10 - "AgenteExplorador"
Cohesion: 0.09
Nodes (14): AgenteExplorador, Convierte el payload nativo a DataFrame y normaliza sus cabeceras de inmediato., Agente Explorador con dos rutas de extracción: - Primaria: captura XHR/fetch…, Listener pasivo: captura sólo respuestas XHR/fetch válidas de la API judicial., Devuelve el DataFrame creado en el listener, sin reprocesar el JSON original., Retorna el payload JSON original, fuente de verdad de la ruta primaria., Expone el motivo de fallo de la captura para la auditoría transaccional., Regresa al buscador utilizando esperas explícitas condicionales. (+6 more)

### Community 11 - "RuntimeError"
Cohesion: 0.16
Nodes (10): RuntimeError, Espera la habilitación asíncrona del botón antes del clic inicial., Pulsa BUSCAR para que el portal monte/despliegue el CAPTCHA., Normaliza el numero de causa para comparar portal y archivo de origen., Busca una causa numérica completa sin aceptar sufijos alfanuméricos., Valida primero la columna de proceso y conserva cualquier sufijo., Indica si el CAPTCHA visible a?n no tiene un token v?lido del operador., Escribe la causa de inmediato y conserva un respaldo para la máscara.… (+2 more)

### Community 12 - "MotorInferenciaProcesal"
Cohesion: 0.06
Nodes (22): MotorInferenciaProcesal, Dada la fase actual encontrada, retorna la siguiente fase y etapa según…, Convierte fechas de actuaciones a un valor comparable sin alterar su formato de…, Devuelve la evidencia fechada m??s reciente de una fase, sin depender del orden…, Vincula la fase de citacion con el acta practicada, no con su mención., Reune la evidencia fechada de una fase en todo el historial disponible., Motor de Inferencia Procesal Autónoma basado en MODULO_FILTRO_CASOS.md y…, Busca la evidencia fechada mas reciente de una fase en todo el historial. (+14 more)

### Community 13 - "preparar_reproceso_causas.py"
Cohesion: 0.05
Nodes (30): _conectar_postgres(), _eliminar_evidencias(), limpiar(), limpiar_comentario_automatico(), _limpiar_lista_fallidos(), _limpiar_postgres(), main(), normalizar_causa() (+22 more)

### Community 14 - "GestorCasos"
Cohesion: 0.16
Nodes (8): GestorCasos, Calcula la columna 'DIAS TRANSCURRIDOS' como la diferencia en días calendario…, Método de retrocompatibilidad que delega en calcular_dias_transcurridos., READ: Obtiene la lista de números de juicio que cumplen con los filtros., Repositorio CRUD de datos para la lectura, actualización y persistencia del…, UPDATE: Inyecta en la fila correspondiente los datos extraídos., Elimina solo registros iguales en todas sus columnas. Un mismo nÃºmero de…, Interpreta fechas del portal, incluidas marcas ISO con zona horaria.

### Community 15 - "EnlaceFalso"
Cohesion: 0.20
Nodes (3): EnlaceFalso, FilaCausaFalsa, PaginaAperturaCausaFalsa

### Community 16 - "Proveedor2Captcha"
Cohesion: 0.09
Nodes (18): CaptchaCredencialError, CaptchaDesafio, CaptchaError, CaptchaProveedorError, CaptchaResolucionTimeout, CaptchaSaldoError, _clave_normalizada(), Proveedor2Captcha (+10 more)

### Community 17 - "prompt_procesador.py"
Cohesion: 0.14
Nodes (14): cargar_plantilla_prompt(), construir_prompt(), _generar_fallback(), limpiar_y_validar_json(), Carga la plantilla de prompt desde el sistema de archivos., Construye el prompt completo reemplazando los marcadores de posición dinámicos…, Limpia cualquier delimitador Markdown de la respuesta del LLM y la parsea como…, Genera un diccionario estructurado de respaldo para no interrumpir el flujo. (+6 more)

### Community 18 - "._capturar_adjuntos_pago_perito"
Cohesion: 0.10
Nodes (8): Devuelve los datos procesados en la vista actual., Transforma API/DOM sin hacer clic ni navegar., Normaliza una fecha SATJE para asociar fila y actuación., Acepta factura o pago que identifique el servicio pericial., Lee los nombres visibles sin descargar documentos de SATJE., Obtiene evidencia de pago en actuaciones posteriores al perito. Solo abre el…, Propaga nombres de archivo a la actuación persistida equivalente., Aplica y deja trazada la inferencia definitiva del alcance indicado.

### Community 19 - "antigravity_adapter.py"
Cohesion: 0.47
Nodes (5): extraer_y_normalizar(), extraer_y_normalizar_dict(), _raise_import_error(), Extrae los datos de la causa desde E-SATJE usando el motor antigravity y…, Retorna el primer registro extraído como dict, o None si no hay datos. Registra…

### Community 20 - "BotJudicialTransaccional"
Cohesion: 0.11
Nodes (7): BotJudicialTransaccional, recorrer(), Flujo e-SATJE con navegación bloqueada durante cada extracción., Espera una capa de carga breve; falla de forma recuperable si persiste., Devuelve una firma durable cuando la API ya entrego las actuaciones. La…, Inspecciona el buscador sin provocar navegación ni modificar la página., Confirma por estado visible dos observaciones estables del buscador SPA.

### Community 22 - "GestorPostgres"
Cohesion: 0.09
Nodes (9): GestorPostgres, Gestor de persistencia relacional nativo en PostgreSQL para casos judiciales,…, Guarda o actualiza un expediente procesado y sus actuaciones individuales en…, ConexionFalsa, CursorFalso, PersistenciaPostgresIdsTests, conexion(), skipUnless (+1 more)

### Community 23 - "migrar_supabase_gratis.py"
Cohesion: 0.10
Nodes (29): HTTPError, activate_common_config(), connect(), copy_value(), import_data(), main(), migrate_schema(), missing_storage_object() (+21 more)

### Community 24 - "monitorear_esatje.py"
Cohesion: 0.18
Nodes (14): cargar_navegacion(), main(), Ejecuta una sola causa en e-SATJE para diagnosticar la navegaci?n visible., cargar_configuracion(), estado_visible(), extraer_eventos(), guardar_evidencia(), instalar_monitor() (+6 more)

### Community 25 - "validar_pertenencia_cartera"
Cohesion: 0.25
Nodes (9): _accion_de_caratula(), _causa_canonica(), _lista_configuracion(), _normalizar(), Validación conservadora de pertenencia de un expediente a una cartera., Extrae una acción solo desde una carátula inequívoca de la causa., Devuelve evidencia de exclusión o ``None`` cuando no hay certeza suficiente. No…, validar_pertenencia_cartera() (+1 more)

### Community 26 - "TestMigracionDB"
Cohesion: 0.12
Nodes (9): Verifica que el esquema de la base de datos es correcto después de la migración., Crea una instancia fresca de GestorCola con una DB temporal., Elimina la DB temporal., Las tres tablas requeridas deben existir tras la inicialización., El método verificar_esquema() debe retornar True con el esquema completo., La tabla juicios debe tener las columnas correctas., La tabla resultados_expediente debe tener las columnas correctas., La tabla eventos_extraccion debe tener las columnas correctas. (+1 more)

### Community 28 - "FilaFalsa"
Cohesion: 0.18
Nodes (4): FilaFalsa, PaginaFilasDivFalsa, PaginaFilasFalsa, Imita la lista Angular real, que no usa filas HTML ``tr``.

### Community 29 - "RenovadorLease"
Cohesion: 0.20
Nodes (4): AbstractContextManager, Renueva un lease mientras Playwright o el CAPTCHA permanecen bloqueados., RenovadorLease, HeartbeatTests

### Community 30 - "test_navegacion_esatje.py"
Cohesion: 0.12
Nodes (4): ColeccionFalsa, PaginaCaptchaFalsa, PaginaCargaGlobalPendienteFalsa, TextoFalso

### Community 31 - "Q: Continuar revisando la logica del sistema a partir de las preguntas del grafo, conectando o corrigiendo funciones cuando sea necesario sin tocar la inferencia ni la ubicacion por palabras clave"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Continuar revisando la logica del sistema a partir de las preguntas del grafo, conectando o corrigiendo funciones cuando sea necesario sin tocar la inferencia ni la ubicacion por palabras clave, Source Nodes

### Community 32 - "enriquecer_datos_procesales"
Cohesion: 0.05
Nodes (72): Exception, ejecutar(), main(), Path, Audita expedientes persistidos con NVIDIA sin alterar su estado oficial.…, main(), migrar(), Path (+64 more)

### Community 33 - "Plan maestro: historial procesal e inferencia híbrida con NVIDIA NIM"
Cohesion: 0.08
Nodes (23): 10. Avance verificado al 24 de septiembre de 2026, 1. Contexto y objetivo, 2. Decisiones confirmadas, 3. Arquitectura objetivo, 4. Subfases de implementación, 5. Interfaces y compatibilidad, 6. Reglas de arbitraje, 7. Pruebas y criterios de aceptación (+15 more)

### Community 34 - "NavegacionEsatjeTests"
Cohesion: 0.12
Nodes (4): BotonFalso, CampoFalso, NavegacionEsatjeTests, PaginaEsperaFalsa

### Community 36 - "datetime"
Cohesion: 0.10
Nodes (22): datetime, exportar(), main(), Path, Exporta todas las filas de PostgreSQL a segmentos privados y verificables. El…, segmento_de_causa(), Menú navegable para usar el sistema judicial desde una terminal Windows., enriquecer_ultima_gestion_judicial() (+14 more)

### Community 37 - "TestPoblarCola"
Cohesion: 0.10
Nodes (5): Poblar con una lista de causas debe insertar registros correctamente., Poblar dos veces con las mismas causas no debe duplicar registros., obtener_siguiente() debe cambiar el estado a EN_PROCESO., Verifica la funcionalidad de poblar y gestionar la cola., TestPoblarCola

### Community 38 - "Índice de documentación"
Cohesion: 0.22
Nodes (10): Configuración de AutoCaptcha, Contexto de reanudación, Convención para documentos nuevos, Índice de documentación, Manual de uso, Módulo de filtro de casos, Molde de nuevos cambios, README de documentación general (+2 more)

### Community 39 - "TestRecuperarHuerfanos"
Cohesion: 0.20
Nodes (5): Verifica la recuperación de registros atrapados en EN_PROCESO., Los registros EN_PROCESO deben volver a PENDIENTE., Sin huérfanos, debe retornar 0., Debe registrar un evento en eventos_extraccion por cada huérfano., TestRecuperarHuerfanos

### Community 40 - "TestRegistrarResultado"
Cohesion: 0.25
Nodes (4): Verifica el registro transaccional de resultados., Registrar un resultado debe cambiar el estado a PROCESADO., El resultado debe persistirse en la tabla resultados_expediente., TestRegistrarResultado

### Community 41 - "Deterministic navigation state machine"
Cohesion: 0.25
Nodes (8): Folder-scoped API and DOM extraction, Deterministic navigation state machine, e-SATJE button automation plan, Durable folder result contract, No-navigation extraction invariant, Transactional extraction brake plan, Observable SPA search return, Unconfirmed search-return fix

### Community 42 - "Contexto de reanudación"
Cohesion: 0.17
Nodes (12): Actualización de inferencia e historial (24 de septiembre), AutoCaptcha, Consistencia de la clasificación y del reporte, Contexto de reanudación, Corrección de clasificación pendiente de vigilar, Escrito posterior con adjunto: alerta conservadora, Estado vigente, Evidencia de contestación (+4 more)

### Community 43 - "ConfiguracionConcurrencia"
Cohesion: 0.24
Nodes (4): ConfiguracionConcurrencia, Any, Parametros validados del coordinador multiproceso., ConfiguracionConcurrenciaTests

### Community 44 - "RespaldoCsvTests"
Cohesion: 0.19
Nodes (3): _gestor_con_csv(), Pruebas de tolerancia a bloqueos temporales del CSV en Windows/OneDrive., RespaldoCsvTests

### Community 46 - "preparar_quito.py"
Cohesion: 0.31
Nodes (11): _cargar_json(), _construir_reporte_regional(), _crear_sqlite_vacio(), main(), _normalizar_columnas(), preparar(), DataFrame, Path (+3 more)

### Community 47 - "Plan de depuración modular multiagente"
Cohesion: 0.11
Nodes (18): Bloqueos descubiertos en la auditoría inicial, Contratos que no pueden cambiar, Criterio de terminación, Interpretación operativa de CRUD, claves y tiempos, Línea base verificada, Objetivo, Oleada 0: inventario y contratos, Oleada 1: pruebas y migraciones (+10 more)

### Community 48 - "Q: estas Preguntas sugeridas son errores que el grafo localizo o conoxiones sin logica se ven como posibles errores?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: estas Preguntas sugeridas son errores que el grafo localizo o conoxiones sin logica se ven como posibles errores?, Source Nodes

### Community 49 - "test_regresiones_quito_29.py"
Cohesion: 0.47
Nodes (4): _fecha_iso(), _normalizar_causa(), skipUnless, TestRegresionesQuito29

### Community 50 - "inicializar_postgres.py"
Cohesion: 0.53
Nodes (5): crear_rol_y_base(), ejecutar_migraciones(), main(), obtener_config_postgres(), Crea la base, el rol de aplicacion y ejecuta migraciones versionadas.

### Community 51 - "ProcesadorCaso"
Cohesion: 0.23
Nodes (6): Resultado independiente de la base de datos y de los reportes., ResultadoCaso, ProcesadorCaso, Any, Mantiene una sesion de navegador acotada y produce resultados puros., ProcesadorCasoTests

### Community 52 - "RepositorioColaSQLite"
Cohesion: 0.07
Nodes (11): Protocol, Reserva atomica devuelta a un trabajador., TrabajoCola, crear_repositorio_cola(), Any, Interfaz de persistencia de ejecuciones y trabajos., Construye el adaptador solicitado sin realizar fallback silencioso., RepositorioCola (+3 more)

### Community 54 - "RepositorioColaPostgres"
Cohesion: 0.05
Nodes (32): aplicar(), main(), Path, Aplica la migración aditiva 002 con el usuario de aplicación PostgreSQL., _entero(), _filas_revision(), importar(), _importar_postgres() (+24 more)

### Community 56 - "normalizar_texto"
Cohesion: 0.10
Nodes (18): _decodificar_entidades_satje(), es_archivo_por_incumplimiento(), es_notificacion(), es_orden_explicita(), es_verificacion_secretarial(), normalizar_texto(), Prioriza la providencia que ordena completar sobre hitos posteriores., Convierte entidades no estandar de SATJE solo para reglas contextuales. (+10 more)

### Community 57 - "main.py"
Cohesion: 0.20
Nodes (11): actualizar_casos_fallidos_piloto(), _ejecutar_lote(), extraer_ruta_config(), guardar_casos_fallidos(), guardar_csv_o_fallar(), main(), motivo_revision_manual_por_formato(), Extrae --config <ruta> sin alterar los modos de seleccion existentes. (+3 more)

### Community 60 - "reclasificar_desde_sqlite.py"
Cohesion: 0.22
Nodes (15): Counter, _aplicar_validacion_pertenencia(), _campos_equivalentes(), _causas_por_sucursal(), _demandados_desde_resultado(), _fecha_canonica(), main(), _normalizar_causa() (+7 more)

### Community 61 - "._inicializar_csv"
Cohesion: 0.25
Nodes (3): Conserva un ID por campo; prioriza el valor no vacio mas reciente., Carga el Excel usando una copia sombra para evitar bloqueos si está abierto en…, CREATE: Genera o combina el CSV de trabajo desde el Excel original.

### Community 62 - "TestExtraccionIntegration"
Cohesion: 0.14
Nodes (8): load_html(), load_json(), Test caso variante 1: Mandamiento en tabla de actuaciones., Test caso variante 2: nombreTipoAccion='EJECUTIVO' con actuaciones de CITACION…, La boleta pendiente inicia citación sin cerrar la calificación previa., El número de intento no acredita la citación del demandado., La negación explícita impide acreditar 2.1; la constancia positiva sí lo…, TestExtraccionIntegration

### Community 63 - "calcular_siguiente_fase"
Cohesion: 0.67
Nodes (3): calcular_siguiente_fase(), REMATE y CONGELAMIENTO como estados finales, ORDEN_FASES

### Community 74 - "test_concurrencia_postgres.py"
Cohesion: 0.36
Nodes (3): FuenteSQLite, MigracionDryRunTests, RepoResultadosFalso

### Community 81 - "Contrato operativo: historial e inferencia con NVIDIA"
Cohesion: 0.33
Nodes (6): Configuración y ejecución, Contrato operativo: historial e inferencia con NVIDIA, Datos enviados, Hallazgo del primer piloto (24 de septiembre de 2026), Límites antes del modo controlado, Qué está conectado

### Community 82 - "Q: perfecto que este caso vamos a agregar a al proyecto este sistema DE IDs mas los defectos que encontraste"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: perfecto que este caso vamos a agregar a al proyecto este sistema DE IDs mas los defectos que encontraste, Source Nodes

### Community 83 - "Q: Revisar la logica del sistema a partir de las preguntas sugeridas sin modificar la inferencia procesal"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Revisar la logica del sistema a partir de las preguntas sugeridas sin modificar la inferencia procesal, Source Nodes

### Community 84 - "ExportadorResultadosEjecucion"
Cohesion: 0.18
Nodes (4): ExportadorResultadosEjecucion, Unico escritor autorizado de los artefactos tabulares., ExportadorUnicoTests, GestorCasosFalso

### Community 85 - "Procedural phase filtering taxonomy"
Cohesion: 0.25
Nodes (8): Procedural phase filtering taxonomy, Six-stage judicial taxonomy, Excel output restructuring requirements, Next procedural phase projection, Approved stabilization and inference action plan, Initial project diagnosis checkpoint, Integration fixture repair, Stabilization and test-suite checkpoint

### Community 86 - "._crear_respaldo_csv"
Cohesion: 0.33
Nodes (3): Reconoce bloqueos habituales de Windows, OneDrive y antivirus., Crea el .bak y tolera bloqueos breves sin omitir la salvaguarda., SAVE: Reemplaza atómicamente el CSV tras crear su respaldo.

### Community 87 - "e-SATJE project architecture"
Cohesion: 0.33
Nodes (6): Excel-to-durable-results processing pipeline, Dual API and DOM extraction architecture, Multilayer durable persistence, e-SATJE project architecture, Regla del Árbol procedural inference, Relational judicial case model

### Community 88 - ".registrar_resultado_transaccional"
Cohesion: 0.20
Nodes (5): Método transaccional atómico: Obtiene la primera causa con estado 'PENDIENTE' y…, Reserva atómicamente una causa concreta antes de procesarla. El flujo normal…, Persiste el resultado del expediente y su estado final en una única transacción…, Indica si un resultado conserva evidencia procesal reutilizable., Abre una conexión en modo autocommit (isolation_level=None) y emite BEGIN…

### Community 89 - "_reclasificar_datos"
Cohesion: 0.24
Nodes (7): _campos_desde_inferencia(), _es_comentario_automatico_obsoleto(), Detecta solo la marca automática exacta que puede quedar obsoleta., Distingue marcas del bot de observaciones redactadas por una persona., _reclasificar_datos(), _reporte_tiene_revision_manual_automatica(), TestReclasificarDesdeSQLite

### Community 90 - "PostgreSQL y procesamiento concurrente"
Cohesion: 0.17
Nodes (11): Comparacion emparejada posterior, Contratos principales, Criterios de aceptacion, Decisiones confirmadas, Estado de activacion, Fases, Migracion esperada, Objetivo (+3 more)

### Community 92 - "motor_busqueda_web.py"
Cohesion: 0.11
Nodes (15): Detección y combinación de múltiples folders, AgenteExtractor, Agente Extractor Semántico y Autónomo (e-SATJE). Analiza el contenido completo…, Procesa el contenido HTML recibido como string, extrayendo las actuaciones, la…, Lee y procesa un archivo HTML desde disco delegando en procesar_html_string., Extrae filas de tabla y contenedores estructurados de actuaciones., Escaneo en profundidad de bloques de texto alternativo., Obtiene la fecha de inicio del expediente. (+7 more)

### Community 93 - "SeleccionLotesPostgresTests"
Cohesion: 0.24
Nodes (3): _ejecutar_lote_postgres(), Prepara un lote y delega la ejecucion a la cola PostgreSQL., SeleccionLotesPostgresTests

### Community 95 - "Q: Implementar un Excel final profesional sin alterar la inferencia ni la hoja de carga"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Implementar un Excel final profesional sin alterar la inferencia ni la hoja de carga, Source Nodes

### Community 96 - "Manual de uso de la consola CMD"
Cohesion: 0.20
Nodes (10): 1. Abrir y recorrer el menú, 2. Preparar un Excel nuevo, 3. Recuperar un lote, 4. Configurar PostgreSQL, 5. Procesar causas, 6. Consultar avance y errores, 7. Problemas frecuentes, Archivos creados (+2 more)

### Community 97 - "NavegadorArbolContenido"
Cohesion: 0.25
Nodes (4): NavegadorArbolContenido, Navegador estructural del árbol procesal y de contenido. Implementa la regla de…, Move Up: Escalada por ausencia hacia un contexto más amplio., Move Down: Profundización por hallazgo hacia sub-fase específica.

### Community 99 - "TestReiniciarErrores"
Cohesion: 0.25
Nodes (4): Verifica la lógica de reintentos de registros con estado ERROR., Los registros en ERROR con reintentos < max deben volver a PENDIENTE., Los registros que ya alcanzaron el máximo de reintentos no deben reiniciarse., TestReiniciarErrores

### Community 100 - "GestorCola"
Cohesion: 0.16
Nodes (7): main(), Script de reset y recreación limpia de la base de datos estado_casos.db. Crea…, GestorCola, Crea las tablas de reserva, resultados y auditoría si no existen., Motor de Estado y Cola de Tareas en SQLite para desacoplar el flujo de…, PersistenciaTransaccionalTests, HistorialPersistidoTests

### Community 101 - "Estado de pausa de la depuración multiagente"
Cohesion: 0.22
Nodes (8): Avance al 01/10/2026, Contrato acordado para retomar, Corte de pausa solicitado por Justin, Estado de pausa de la depuración multiagente, Estado seguro conservado, Hallazgo PostgreSQL pendiente, Secuencia exacta para reanudar, Trabajo pausado

### Community 102 - "coordinador_concurrente.py"
Cohesion: 0.31
Nodes (8): ejecutar_trabajador(), _esperar_turno_inicio(), Coordinacion multiproceso para la cola PostgreSQL., Punto de entrada serializable para ``multiprocessing.spawn``., estado_terminal_para_resultado(), motivo_revision_manual_por_formato(), Procesamiento de una causa sin conocer la persistencia ni los reportes., resultado_es_recuperable()

### Community 103 - "Classification from confirmed procedural evidence"
Cohesion: 0.40
Nodes (5): Latest material procedural act rule, Pending case corrections and reinference, Classification from confirmed procedural evidence, Atomic classification and evidence decision, Derived phase-date correction plan

### Community 104 - "Conservative manual-review guard for untyped attachments"
Cohesion: 0.50
Nodes (4): Conservative manual-review guard for untyped attachments, Bounded PDF and OCR processing, Prioritized document evidence pipeline, Selective PDF attachment reading plan

### Community 105 - "test_migracion.py"
Cohesion: 0.18
Nodes (10): Checkpoint 02: Migración SQLite y Recuperación de Cola, Esquema SQLite, estado_casos.db, Migración SQLite, backup_db(), migrar(), Crea un respaldo de la base de datos antes de migrar., Script de migración y verificación para la base de datos SQLite… (+2 more)

### Community 106 - "ejecutar_lote_postgres"
Cohesion: 0.28
Nodes (6): ejecutar_lote_postgres(), Despacho de lotes judiciales mediante la cola PostgreSQL., Selecciona causas y ejecuta el lote PostgreSQL con sus trabajadores., _causa_comparable(), Selección de causas y división de lotes para los modos públicos de la CLI., Contratos públicos de selección de causas, sin E/S ni navegador.

### Community 109 - "FrenoNavegacionTests"
Cohesion: 0.10
Nodes (3): BotonFalso, FrenoNavegacionTests, PaginaFalsa

### Community 110 - "limpieza.py"
Cohesion: 0.50
Nodes (4): ejecutar_limpieza(), Manejador para forzar eliminación de archivos con atributo de solo lectura en…, Elimina de forma recursiva y segura el directorio temp_htmls/ conservando…, _remove_readonly()

### Community 112 - "Equipo de agentes de desarrollo"
Cohesion: 0.33
Nodes (5): Ejemplo de asignación, Equipo de agentes de desarrollo, Inicio sin daemon, Límites operativos, Método de trabajo

### Community 113 - ".procesar_flujo_judicatura"
Cohesion: 0.20
Nodes (5): Modo Híbrido Asistido con Arquitectura de Ejecución Dual: 1. Prepara búsqueda…, Inicia el navegador Chromium con bypass anti-automatización para F5 WAF y…, Cierra la sesión del navegador., Verifica si la página y el contexto del navegador están activos. Si se cerró el…, Verifica si la sesión del portal sigue activa y el navegador está vivo. Si…

### Community 114 - "PostgreSQL and pgAdmin guide"
Cohesion: 0.33
Nodes (5): Consola para nuevos Excel, PostgreSQL, Un config para los Excel nuevos, Judicial analytical database views, PostgreSQL and pgAdmin guide

### Community 120 - "Migración de la base judicial a Supabase Free"
Cohesion: 0.40
Nodes (4): Ejecutar, Estado y alcance, Límites operativos, Migración de la base judicial a Supabase Free

### Community 121 - "ejecucion.py"
Cohesion: 0.40
Nodes (3): extraer_trabajadores(), Contratos estables para ejecuciones secuenciales y concurrentes., Extrae ``--workers N`` sin interferir con los modos historicos.

### Community 123 - ".exportar_excel"
Cohesion: 0.33
Nodes (4): es_error_visual(), estilizar_hoja(), Aplica el acabado profesional del libro sin modificar sus datos., Genera el reporte, la hoja para Sistemas y las vistas de IA.

### Community 124 - "._extraer_informacion_proceso"
Cohesion: 0.14
Nodes (3): Persiste el estado de cada rechazo/timeout sin alterar la navegación., Guarda evidencia best-effort sin intentar una nueva navegación., Reconoce rechazos explícitos de Angular después de pulsar BUSCAR.

## Knowledge Gaps
- **133 isolated node(s):** `Un config para los Excel nuevos`, `PostgreSQL`, `Inicio sin daemon`, `Método de trabajo`, `Límites operativos` (+128 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 718 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Work-memory lessons

**Preferred sources** — corroborated by past sessions; start here.
- `MotorInferenciaProcesal` (3× useful, score=2.862483507) _(code changed — re-verify)_
- `GestorCola` (3× useful, score=2.79669087) _(code changed — re-verify)_
- `GestorCasos` (2× useful, score=1.931864786) _(code changed — re-verify)_

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BotJudicial` connect `BotJudicial` to `RetornoBuscadorTests`, `RuntimeError`, `MotorInferenciaProcesal`, `Proveedor2Captcha`, `._capturar_adjuntos_pago_perito`, `BotJudicialTransaccional`, `monitorear_esatje.py`, `test_navegacion_esatje.py`, `enriquecer_datos_procesales`, `NavegacionEsatjeTests`, `datetime`, `ProcesadorCaso`, `main.py`, `TestExtraccionIntegration`, `motor_busqueda_web.py`, `._causa_para_formulario`, `NavegadorArbolContenido`, `coordinador_concurrente.py`, `CaptchaSolucion`, `FrenoNavegacionTests`, `.procesar_flujo_judicatura`, `._extraer_informacion_proceso`?**
  _High betweenness centrality (0.209) - this node is a cross-community bridge._
- **Why does `GestorCasos` connect `GestorCasos` to `enriquecer_datos_procesales`, `datetime`, `consola.py`, `GestorCola`, `RespaldoCsvTests`, `preparar_reproceso_causas.py`, `preparar_quito.py`, `InterfazCMD`, `FrenoNavegacionTests`, `SeleccionLotesPostgresTests`, `._crear_respaldo_csv`, `main.py`, `.exportar_excel`, `reclasificar_desde_sqlite.py`, `._inicializar_csv`?**
  _High betweenness centrality (0.139) - this node is a cross-community bridge._
- **Why does `GestorCola` connect `GestorCola` to `enriquecer_datos_procesales`, `TestReiniciarErrores`, `Orquestador`, `TestPoblarCola`, `TestRecuperarHuerfanos`, `._connection`, `test_migracion.py`, `TestRegistrarResultado`, `FrenoNavegacionTests`, `preparar_quito.py`, `.bloquear_ejecucion`, `RepositorioColaSQLite`, `.registrar_resultado_transaccional`, `main.py`, `TestMigracionDB`, `motor_busqueda_web.py`?**
  _High betweenness centrality (0.130) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `TestClasificacionArbol` (e.g. with `AgenteExtractor` and `MotorInferenciaProcesal`) actually correct?**
  _`TestClasificacionArbol` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `BotJudicial` (e.g. with `AgenteExtractor` and `MotorInferenciaProcesal`) actually correct?**
  _`BotJudicial` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `BotJudicialTransaccional` (e.g. with `CaptchaConfiguracionError` and `CaptchaDesafio`) actually correct?**
  _`BotJudicialTransaccional` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 75 inferred relationships involving `RuntimeError` (e.g. with `_ejecutar_lote()` and `guardar_csv_o_fallar()`) actually correct?**
  _`RuntimeError` has 75 INFERRED edges - model-reasoned connections that need verification._