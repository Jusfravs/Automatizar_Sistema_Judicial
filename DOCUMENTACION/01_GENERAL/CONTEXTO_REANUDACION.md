# Contexto de reanudación

Última actualización: 26 de agosto de 2026, America/Guayaquil.

## Estado vigente

- Lote activo: **todas las sucursales activas**, mediante `config.json`.
- Excel de origen: `data/REPORTE_JUICIOS_LISTO_PARA_REVISION.xlsx` (4.017 filas).
- Se realizó un reinicio coordinado de la región; los artefactos anteriores se
  preservaron en `backups/reinicio_el_oro_20260826_095002/`.
- La cola actual `estado_casos.db` contiene los lotes visibles del 26 de agosto:
  `PROCESADO=36` y `ERROR=1`. Incluye el lote de 20 y las cuatro causas puntuales
  revisadas; no hay una instancia operativa de `main.py` en ejecución.
- La causa `17230-2015-1663` (Quito, QUITO SUR) terminó en
  `RESULTADOS_TIMEOUT`. El retorno al buscador fue confirmado; es un reintento
  pendiente de navegación, no una falla de AutoCaptcha ni de clasificación.
- El intento inicial ejecutado desde una sesión aislada se respaldó y se retiró
  para no conservar errores de CAPTCHA no verificables.

## Fase operativa y medidas ejecutadas

- `ULTIMA ETAPA` y `ULTIMA FASE` conservan el último hito probado y su fecha
  para auditoría. En cambio, `ETAPA_PROCESAL` y `FASE_PROCESAL` envían la fase
  actual calculada. Así una ejecutoria seguida por liquidación, o un embargo
  seguido por remate, no se transmite como si siguiera en el hito previo.
- Solo un embargo expreso, practicado, trabado o inscrito activa `6.3 EMBARGO`.
  Un secuestro o una aprehensión de vehículo, incluso respaldados por acta,
  son medidas preventivas: se conservan como antecedente y no adelantan la
  fase. Solicitudes, órdenes, designaciones, medidas negadas e improcedentes
  tampoco alteran la clasificación.
- Las medidas de una carpeta `CARATULA SORTEO DE DEPRECATORIOS` no sustituyen
  la fase del expediente principal; sus citaciones sí se conservan como
  evidencia.
- `scripts/reclasificar_desde_sqlite.py --aplicar` respalda SQLite, CSV y
  Excel. Solo elimina filas idénticas en todas las columnas: coincidencias del
  mismo juicio con distinta cartera, usuario o crédito se preservan.

## Lote fuente vigente

`config.json` quedó preparado para el reporte externo
`C:\Users\pasante.callcenter\Downloads\Reporte_jucios SIS 3 27082026 12.40.xlsx`:
hoja `Reporte`, 2.001 filas y filtro `ESTADO = ACTIVO`. Sus resultados se
aislarán en `data/reporte_trabajo_20260827.csv`,
`data/REPORTE_PROCESADO_FINAL_20260827.xlsx`,
`data/estado_casos_20260827.db` y `data/casos_fallidos_20260827.txt`.
El CSV inicial y la base SQLite vacía ya fueron creados; el lote anterior no
fue alterado.

## AutoCaptcha

`config.json` usa `captcha.modo = "api_con_espera_humana_limitada"`. La API key
se lee exclusivamente de `AUTOCAPTCHA_API_KEY`; en este equipo no está persistida
ni se carga desde `.env`. Debe cargarse en la misma PowerShell antes de iniciar
el bot.

No existe modo manual permanente. Si la API falla, `main.py` muestra una ventana
de hasta 30 segundos para resolver el CAPTCHA; al agotarse, deja la causa en
`REVISION MANUAL` y continúa con la siguiente. No ejecutar `src.orquestador`
cuando se quiera aprovechar esa ventana, porque se ejecuta sin interfaz visible.

## Corrección de clasificación pendiente de vigilar

Caso de referencia: `07333-2023-02297`.

- Dos demandados fueron citados personalmente el `10/03/2026`.
- Las devoluciones del deprecatorio de junio de 2026 confirman diligencias, no
  un embargo practicado.
- Resultado esperado: última fase `2.1 CITACION (PERSONA/BOLETA)`, fecha
  `10/03/2026`, etapa/fase actual `CONTESTACION`.

El parche en `src/agente_extractor.py` impide elevar a `6.3 EMBARGO` un
despacho deprecatorio sin acta, traba, ejecución o inscripción explícita.

## Verificación técnica

- La sangría de `tests/test_clasificacion_arbol.py` fue corregida.
- Suite actual: `207` pruebas correctas; `3` omitidas por requerir PostgreSQL.
- La prueba específica del deprecatorio frente a citación cumplida pasa.

## Consistencia de la clasificación y del reporte

Caso de referencia: `07333-2025-00183`.

- La extracción DOM había identificado correctamente `1.3 CALIFICACION` del
  `10/02/2025`, pero la consolidación API+DOM la reemplazaba por `2.2 CITACION
  POR PRENSA` debido a menciones jurídicas del artículo 56, sin una diligencia
  de prensa acreditada.
- `src/agente_extractor.py` ahora exige una providencia, constancia de
  publicación o evidencia documental concreta de la citación por prensa. Una
  referencia normativa, una cita jurisprudencial o una etiqueta genérica de
  "medios de comunicación" ya no basta.
- `src/motor_busqueda_web.py` registra la salida operativa única como
  `[DECISION_FASE_FINAL]`; la inferencia DOM aislada se conserva solo como
  diagnóstico. Así el log no induce a confundir una decisión intermedia con la
  que se persiste.
- El 26/08/2026 se reclasificaron 43 resultados SQLite, con cinco correcciones
  `2.2 CITACION POR PRENSA -> 1.3 CALIFICACION`: `07312-2025-00018`,
  `07333-2021-02395`, `07333-2024-01512`, `07333-2025-00183` y
  `07333-2025-03378`. Los respaldos previos quedaron en `data/backups/` con la
  marca `20260826_130318`.

## Evidencia de contestación

- No basta que una providencia use la palabra "contestación", "excepciones" o
  "allanamiento". La fase `3.1 CONTESTACION` requiere un escrito/acto de la
  parte demandada: contestación presentada, excepciones opuestas, allanamiento
  expreso o una providencia que lo incorpore o califique.
- Los plazos para contestar, la contestación de un registro u otra entidad, las
  menciones normativas y los listados de formas de conclusión no hacen avanzar
  la causa. Las referencias posteriores al auto de calificación tampoco cambian
  la fecha de esa fase.
- Basta la contestación acreditada de **una** persona demandada o procesada;
  no se exige que todas hayan contestado. La evidencia debe identificar la
  contestación de la demanda o la providencia que incorpora el escrito.
- Cuando la providencia incorpora de forma inmediata un `ESCRITO` y se refiere
  al contenido de la contestación, la fecha de `3.1 CONTESTACION` es la del
  escrito presentado, no la fecha de la providencia posterior ni la de una
  razón con un año inconsistente. Esta regla se comprobó con
  `07333-2023-00851`: escrito `07/09/2023`, auto de incorporación
  `25/09/2023`.
- El 27/08/2026 se auditó la base persistida con esta regla y se corrigieron
  cuatro registros; `07331-2025-00234` quedó en `1.3 CALIFICACION`, fecha
  `09/04/2025`, con siguiente fase `2.1 CITACION (PERSONA/BOLETA)`.

## Escrito posterior con adjunto: alerta conservadora

Caso de referencia: `07333-2022-01899`.

- SATJE puede mostrar una actuación genérica `ESCRITO / FePresentacion` con un
  adjunto cuyo contenido no se extrae aún. Ese rótulo no permite afirmar que
  sea una contestación, pero tampoco permite presentar la calificación previa
  como el estado material definitivo de la causa.
- El extractor ahora conserva `TIENE_ADJUNTO` para actuaciones DOM que incluyen
  el control `Ver archivos`. La consolidación API+DOM preserva ese metadato.
- Si un `ESCRITO / FEPRESENTACION` con adjunto es posterior a una fase
  confirmada de calificación o citación, la última fase confirmada se conserva,
  pero `ETAPA ACTUAL` y `FASE ACTUAL` pasan a `REVISION MANUAL`. El reporte
  deja el comentario automático `REVISION DOCUMENTAL: ESCRITO POSTERIOR SIN
  TIPO CONFIRMADO (<fecha>)`.
- La regla no asigna `3.1 CONTESTACION`, no se activa sin adjunto y no abre
  revisión en una causa que ya tiene una fase confirmada de contestación o
  posterior. Es una protección contra certeza falsa, no una lectura de PDFs.
- Los historiales antiguos que no conservaron `TIENE_ADJUNTO` no pueden ser
  marcados retroactivamente con seguridad; deben reprocesarse desde SATJE para
  capturar ese metadato.

## Orden seguro para continuar

1. Abrir una sola PowerShell en la raíz del proyecto.
2. Cargar `AUTOCAPTCHA_API_KEY` sin mostrarla.
3. Ejecutar un piloto visible con `main.py --config config.json --lote 10`.
   Tomará causas activas de cualquier sucursal según el orden del Excel.
4. Verificar reporte, estados SQLite y CAPTCHA antes de ampliar el lote.
5. Respaldar antes de cualquier nuevo reinicio o cambio de configuración.
