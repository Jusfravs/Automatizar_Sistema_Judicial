# Plan maestro: historial procesal e inferencia híbrida con NVIDIA NIM

**Fecha:** 21 de septiembre de 2026
**Estado:** IMPLEMENTACIÓN INICIADA; piloto y validación humana pendientes
**Zona horaria:** America/Guayaquil

## 1. Contexto y objetivo

El sistema judicial conservará el motor actual de reglas como base jurídica y
añadirá una capa temporal, un historial versionado y una auditoría de
inteligencia artificial. La IA no sustituirá directamente las reglas:
verificará sus conclusiones, citará actuaciones concretas y escalará los casos
dudosos.

El problema principal que se busca corregir es la confusión entre una fase
histórica y el estado vigente. Una actuación antigua puede contener palabras
correspondientes a una fase válida, aunque el expediente ya se encuentre una o
dos etapas más adelante. La solución debe reconstruir la secuencia procesal,
identificar el último hito confirmado y distinguirlo del estado operativo
actual.

La base inspeccionada contiene historiales extensos: aproximadamente 91
actuaciones y 12.700 tokens crudos por expediente en promedio. Por esta razón
no se enviará todo el texto a la API. Se construirá una cronología compacta con
recuperación selectiva de evidencia.

## 2. Decisiones confirmadas

- NVIDIA NIM será el proveedor inicial mediante `NVIDIA_API_KEY`.
- `nvidia/nemotron-3-super-120b-a12b` auditará los casos en modo sombra.
- El modelo de escalamiento se seleccionará tras medir discrepancias, límites de cuota y calidad en el piloto; no se presupone un segundo modelo disponible.
- La autoridad será híbrida y controlada.
- La confianza mínima para una corrección automática será `0.97`.
- Los datos personales se seudonimizarán localmente antes de enviarse.
- Se migrarán tanto los expedientes existentes como los futuros.
- El Excel mostrará hitos procesales y una cola de revisión.
- Las actuaciones completas permanecerán en la base de datos.
- La cantidad de 5.000 casos fue una estimación; el diseño será escalable desde
  la base real actual de más de 2.000 expedientes.
- SQLite seguirá siendo la fuente operativa del modo secuencial. PostgreSQL
  será la fuente de verdad obligatoria del modo concurrente y podrá usarse con
  un solo trabajador durante los pilotos.
- Las reglas, moldes, módulos, catálogo de IDs y estructura del árbol procesal
  existentes serán reutilizados y no reemplazados.
- Ninguna regla se modificará automáticamente a partir de una respuesta de IA.

El cliente usa la API Chat Completions compatible con OpenAI de NVIDIA. La
disponibilidad, cuota y precio deben verificarse antes del piloto masivo; no
se codifica un costo fijo:

- Modelo y ejemplo de API: <https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b/deploy>
- Inicio de API: <https://docs.api.nvidia.com/nim/docs/api-quickstart>

## 3. Arquitectura objetivo

```text
Portal e-SATJE
      |
      v
Extracción API + DOM
      |
      v
Historial normalizado de actuaciones
      |
      v
Motor determinista actual y reglas del árbol
      |
      v
Cronología de hitos y estado propuesto
      |
      v
NVIDIA Nemotron 3 Super: auditoría general
      |
      +---- Coincidencia segura ----------> Decisión versionada
      |
      +---- Conflicto o ambigüedad
                    |
                    v
              Segundo pase NVIDIA (modelo por validar)
                    |
                    +---- Evidencia suficiente --> Arbitraje controlado
                    |
                    +---- Duda o riesgo ----------> Revisión humana
```

La ejecución de IA será posterior a la extracción y persistencia. Una caída,
demora o falta de saldo del proveedor no bloqueará la navegación del portal ni
el resultado determinista.

## 4. Subfases de implementación

### Subfase 0. Documentación, Git y línea base

- Preservar los cambios aprobados del Excel profesional en un commit separado.
- No incluir en commits los archivos de `data/`, respaldos ni salidas
  operativas.
- Crear la rama `upgrade/inferencia-hibrida-nvidia` cuando los cambios previos del repositorio estén separados.
- Mantener este documento como fuente principal del plan.
- Crear posteriormente:
  - `DOCUMENTACION/02_MODULOS_Y_CONFIGURACION/CONTRATO_INFERENCIA_HIBRIDA_IA.md`.
  - `DOCUMENTACION/03_BASE_DE_DATOS/MODELO_HISTORIAL_PROCESAL_IA.md`.
- Actualizar `DOCUMENTACION/INDICE.md` y
  `DOCUMENTACION/01_GENERAL/CONTEXTO_REANUDACION.md`.
- Registrar como línea base las 264 pruebas correctas y 3 omitidas.
- Añadir dependencias reproducibles de desarrollo para ejecutar las pruebas sin
  depender del Python global.
- Construir un conjunto de verdad de al menos 120 expedientes: regresiones
  conocidas, fases disponibles, múltiples carpetas, actuaciones antiguas
  engañosas, retrocesos y revisiones documentales. La verdad será validada por
  una persona, no generada por IA.

### Subfase 1. Historial procesal normalizado y versionado

- Añadir migraciones SQLite incrementales, con copia de seguridad,
  verificación de integridad y reversión.
- Normalizar cada actuación con un `actuacion_id` estable derivado de causa,
  carpeta, fecha y hash del contenido.
- Añadir tablas append-only para actuaciones procesales, ejecuciones de
  inferencia, hitos, decisiones, evidencias, auditorías de IA y revisiones
  humanas.
- Mantener `resultados_expediente` como fotografía vigente para compatibilidad.
- Actualizar los consumidores para recuperar el historial mediante un
  repositorio, no leyendo directamente `HISTORIAL_ACTUACIONES` desde el JSON.
- Migrar los historiales existentes por lotes idempotentes.
- Verificar conteos, hashes y causas antes de retirar el historial duplicado
  del JSON.
- Conservar un respaldo intacto y generar la base compactada mediante
  `VACUUM INTO`; reemplazarla únicamente después de superar
  `integrity_check`.
- Replicar posteriormente el esquema en PostgreSQL y utilizarlo como fuente de
  verdad cuando se active el procesamiento concurrente; el modo secuencial
  seguirá pudiendo operar con SQLite.

### Subfase 2. Motor temporal sobre las reglas actuales

- Mantener `MotorInferenciaProcesal`, `ORDEN_FASES`, el catálogo de IDs y las
  reglas especiales como fuentes deterministas.
- No modificar inicialmente palabras clave, niveles de inferencia ni reglas
  jurídicas.
- Exponer los hallazgos por actuación, regla, fase candidata, fecha, carpeta e
  instancia.
- Añadir un grafo separado de transiciones permitidas y excepciones: nulidad,
  revocatoria, reapertura, remisión y cambio de instancia.
- Diferenciar expresamente el último hito confirmado, el estado operativo
  actual, la siguiente fase esperada, una fase histórica y una regresión
  jurídicamente justificada.
- Una mención antigua nunca podrá convertirse en estado actual si existe
  evidencia posterior más avanzada.
- No inventar IDs para fases ausentes del catálogo externo; se conservarán con
  ID nulo y revisión.
- Versionar las reglas utilizadas en cada decisión.
- Los posibles nuevos patrones descubiertos por IA se convertirán en
  propuestas documentadas; nunca modificarán automáticamente las reglas.

### Subfase 3. Privacidad, contexto y cliente NVIDIA

- Implementar un adaptador `ProveedorIA` independiente del proveedor y un
  cliente NVIDIA por HTTPS no streaming.
- Leer la credencial exclusivamente desde `NVIDIA_API_KEY`.
- Sustituir nombres, cédulas, RUC, teléfonos, correos y direcciones por
  marcadores consistentes como `PERSONA_1`.
- No enviar a la API la tabla local de correspondencias.
- Tratar las actuaciones como datos no confiables para prevenir instrucciones
  incrustadas en textos judiciales.
- Construir el contexto con taxonomía, IDs, reglas, clasificación determinista,
  cronología resumida, actuaciones decisivas y metadatos de carpeta e
  instancia.
- Limitar el primer pase a aproximadamente 8.000 tokens y el segundo pase a
  24.000; recuperar más evidencia únicamente cuando sea necesario.
- Usar JSON Schema y validar localmente etiquetas, IDs, fechas, evidencias y
  confianza.
- No guardar el razonamiento interno del modelo; conservar decisión,
  explicación breve, evidencias y consumo.
- Registrar tokens, caché, latencia, modelo, versión del prompt y costo
  estimado.
- Aplicar reintentos con espera progresiva para `429`, `500` y `503`.
- Ante `401` o `402`, abrir un circuito y detener las llamadas sin interrumpir
  el RPA.
- Usar un presupuesto inicial de USD 25 por ejecución. Al alcanzar el límite,
  pausar la IA y dejar los casos pendientes sin perder el resultado
  determinista.

### Subfase 4. Auditoría híbrida y arbitraje

- Ejecutar Nemotron 3 Super sobre todos los expedientes después de persistir la
  extracción.
- Escalar a un segundo pase validado ante discrepancia, baja confianza, aparente
  regresión, varias ramas activas, actuación genérica con adjunto, datos
  faltantes o transición terminal.
- Utilizar este contrato principal de salida:

```json
{
  "schema_version": "1.0",
  "decision": "CONSERVAR|CORREGIR|INSUFICIENTE",
  "ultimo_hito": {
    "eta_id": 14,
    "fas_id": 87,
    "fecha": "2026-09-01"
  },
  "estado_actual": {
    "eta_id": 15,
    "fas_id": 88
  },
  "tipo_transicion": "AVANCE|MANTIENE|REGRESION_JUSTIFICADA",
  "evidencias": ["ACT-..."],
  "reglas_relacionadas": ["regla_..."],
  "confianza": 0.98,
  "motivo": "Explicación breve",
  "datos_faltantes": [],
  "requiere_revision_humana": false
}
```

- Una corrección automática requerirá coincidencia entre dos pases independientes,
  confianza mínima de `0.97`, evidencias existentes, IDs válidos, ausencia de
  información faltante y una transición permitida.
- Regresiones, estados terminales, fases sin ID oficial y decisiones sostenidas
  únicamente por OCR requerirán revisión humana.
- Si la IA falla, conservar el resultado determinista y dejar la auditoría
  pendiente.
- Las decisiones humanas tendrán prioridad. Solo nueva evidencia posterior
  podrá reabrirlas.
- Añadir los modos `deshabilitado`, `sombra`, `revision` y
  `aplicar_controlado`.
- El modo predeterminado será `deshabilitado`.

### Subfase 5. Excel profesional y revisión humana

El libro final mantendrá las hojas actuales y añadirá dos vistas.

#### `Reporte`

- Conservar el formato profesional vigente.
- Añadir al final: estado de auditoría, fuente de la decisión, confianza y
  revisión pendiente.

#### `PARA CARGA`

- Mantener encabezado en la fila 1, estructura, IDs y compatibilidad.
- No incluir columnas internas de IA.

#### `HISTORIAL HITOS`

- Una fila por transición relevante, no por actuación cruda.
- Columnas: causa, actuación, fecha, instancia, carpeta, etapa/fase e IDs,
  condición histórica o vigente, fuente, regla, confianza, evidencia resumida
  y versión.

#### `REVISION IA`

- Una fila por discrepancia pendiente.
- Mostrar clasificación del sistema, propuestas del primer y segundo pase, evidencias,
  motivo, riesgo, confianza y datos faltantes.
- Incluir campos editables `DECISION HUMANA`, IDs manuales y observación.
- Decisiones permitidas: `ACEPTAR_SISTEMA`, `ACEPTAR_IA`,
  `CORREGIR_MANUALMENTE` y `POSPONER`.

También se creará un importador validado de decisiones del Excel. Rechazará
revisiones duplicadas, desactualizadas, sin ID o con combinaciones inválidas.

Las hojas nuevas usarán filtros, tablas, paneles inmovilizados, formatos de
fecha y semáforos coherentes con el reporte profesional existente.

### Subfase 6. Evidencia documental selectiva

- Reutilizar el plan existente de lectura selectiva de adjuntos.
- Consultar PDFs solamente en casos escalados por falta documental.
- Mantener inicialmente 6 adjuntos por causa, 4 por carpeta, 15 MB por archivo
  y 8 páginas de OCR.
- Extraer texto nativo primero y ejecutar OCR únicamente cuando sea necesario.
- Seudonimizar el texto antes de enviarlo al segundo pase de NVIDIA.
- Guardar hash, actuación, página, calidad, extracto y regla asociada.
- Usar la fecha de presentación de SATJE como fecha procesal principal.
- Cachear cada documento por ID y SHA-256.
- Un PDF corrupto, ilegible o ambiguo producirá revisión humana, nunca una fase
  inventada.

### Subfase 7. Migración, piloto y despliegue

1. Ejecutar migración y auditoría sin IA.
2. Ejecutar IA en modo sombra sobre el conjunto de verdad.
3. Ejecutar un piloto de 100 a 200 casos reales sin modificar resultados
   oficiales.
4. Habilitar `revision` y procesar la base existente por lotes reanudables.
5. Resolver una primera muestra mediante la hoja `REVISION IA`.
6. Habilitar `aplicar_controlado` solo al superar las puertas de calidad.
7. Procesar los casos futuros después de cada extracción, de forma asíncrona.
8. Actualizar documentación, Graphify y crear un commit verificable al terminar
   cada subfase.

## 5. Interfaces y compatibilidad

- Nuevos modelos internos: `ActuacionProcesal`, `HitoProcesal`,
  `ContextoAuditoriaIA`, `DecisionIA`, `DecisionFinal` y `RevisionHumana`.
- Nuevas operaciones del repositorio: registrar y consultar actuaciones, crear
  una ejecución, guardar propuestas, aplicar decisiones, resolver revisiones y
  reconstruir el estado oficial.
- `ResultadoInferencia` mantendrá su desempaquetado de tres valores y sus claves
  actuales.
- El sistema actual seguirá funcionando sin API key y con IA deshabilitada.
- Los prompts se construirán desde el catálogo y las reglas vigentes para
  evitar una taxonomía duplicada.
- No se enviarán PDFs, HTML completo, credenciales ni identificadores
  personales a la API.

## 6. Reglas de arbitraje

| Resultado | Acción |
|---|---|
| Reglas y primer pase coinciden | Conservar clasificación y registrar auditoría |
| Primer pase discrepa | Escalar a segundo pase validado |
| Ambos pases coinciden con confianza menor a 0.97 | Revisión humana |
| Ambos pases coinciden con confianza mínima de 0.97 y evidencia válida | Corrección controlada |
| Evidencia inexistente o inventada | Rechazar respuesta de IA |
| Regresión, fase terminal o fase sin ID | Revisión humana obligatoria |
| API no disponible | Conservar reglas y marcar auditoría pendiente |
| Falta PDF determinante | Lectura selectiva o revisión humana |

## 7. Pruebas y criterios de aceptación

- Mantener las 264 pruebas actuales correctas y las 3 omisiones justificadas.
- Probar deduplicación API/DOM, IDs estables, múltiples carpetas, orden
  temporal, fases históricas y regresiones justificadas.
- Verificar que migración y reversión conserven todas las causas y actuaciones.
- Exigir que toda evidencia citada por IA exista realmente.
- Confirmar cero datos personales en payloads, errores y logs mediante pruebas
  adversariales.
- Simular respuestas vacías, JSON inválido, timeout, saldo insuficiente y
  errores `429`, `500` y `503`.
- Verificar que el modo sombra no cambie SQLite, CSV, Excel ni `PARA CARGA`.
- Exigir que toda respuesta sea aceptada completamente por el validador o pase
  a revisión; nunca aceptar parcialmente un JSON.
- Alcanzar al menos 95% de exactitud de fase actual en el conjunto validado y
  no empeorar ninguna fase frente al motor actual.
- Exigir al menos 99% de precisión en las correcciones candidatas a aplicación
  automática.
- Exigir cero avances o regresiones críticas falsos durante el piloto.
- Probar importación de decisiones humanas, revisiones obsoletas e IDs
  inválidos.
- Verificar visualmente todas las hojas, filtros, estilos, inmovilización y
  compatibilidad del Excel.
- Probar interrupción y reanudación sin duplicar llamadas, cargos, actuaciones
  ni decisiones.

## 8. Supuestos y límites

- El motor determinista seguirá siendo una pieza permanente del sistema.
- La IA audita los datos recopilados; no consulta autónomamente el portal.
- SQLite seguirá disponible para operación secuencial y recuperación;
  PostgreSQL será requisito únicamente para ejecutar varios trabajadores.
- El historial completo vivirá en la base; el Excel contendrá hitos y
  revisiones.
- La habilitación automática será posterior al piloto.
- Ninguna corrección será retroactiva sin una decisión versionada.
- Los precios, modelos y políticas se revisarán antes de cada despliegue mayor.
- Las respuestas de IA no se considerarán evidencia judicial por sí mismas.
- Una corrección siempre deberá estar respaldada por actuaciones almacenadas.
- El falso avance procesal se considera más grave que enviar un caso a revisión
  humana.

## 9. Criterio de finalización del upgrade

El upgrade se considerará terminado cuando:

1. Todos los casos existentes tengan historial normalizado y estado
   reconstruible.
2. La IA opere en modo controlado sin bloquear la extracción.
3. Cada decisión pueda explicarse mediante reglas y actuaciones concretas.
4. Las correcciones automáticas cumplan los umbrales de calidad.
5. Los casos ambiguos aparezcan en una cola de revisión clara.
6. El Excel final muestre correctamente el estado actual, los hitos y las
   revisiones.
7. `PARA CARGA` conserve compatibilidad con Sistemas.
8. La migración, el piloto y la suite completa hayan superado sus pruebas.
9. La documentación y el grafo del proyecto estén actualizados.

## 10. Avance verificado al 24 de septiembre de 2026

- Subfase 1, SQLite: esquema aditivo e idempotente conectado a la persistencia;
  migración de 1.878 causas con historial y 171.846 actuaciones únicas. Otras
  32 fotografías no contenían actuaciones. Se conservó un respaldo previo de
  1.910 resultados y ambas bases pasaron `PRAGMA integrity_check`.
- Subfase 1, PostgreSQL: migración `002_historial_inferencia_ia.sql` aplicada.
  De 1.954 expedientes existentes, 1.887 quedaron con historial normalizado
  y 67 carecían de actuaciones. Las 172.625 actuaciones normalizadas igualan
  el conteo de la tabla fuente `actuaciones`; hay 1.887 versiones de inferencia.
  El ejecutor de NVIDIA, las vistas Excel y el importador de revisiones tienen
  ruta PostgreSQL, pendientes de validar con una respuesta real del modelo.
- Subfase 2, diagnóstico: `motor_temporal.py` ordena candidatos de fase,
  menciones históricas, ambigüedades y posibles regresiones usando los términos
  del árbol vigente. Su salida es consultiva y no cambia el motor oficial.
- Subfases 3 y 4, primer pase: cliente NVIDIA NIM por `NVIDIA_API_KEY`, contexto
  limitado a señales jurídicas sin texto libre, validación local de IDs y
  evidencias, reintentos y auditoría reanudable en `sombra`. La ejecución es
  externa al RPA mediante `scripts/auditar_inferencia_nvidia.py`.
- Subfase 5, vistas: el Excel puede incluir `HISTORIAL HITOS` y `REVISION IA`;
  `Reporte` muestra el estado de auditoría. `PARA CARGA` no recibe columnas de IA.
  El importador valida y registra decisiones humanas sin modificar aún la
  clasificación oficial.
- Pruebas nuevas: privacidad del contexto, evidencia inventada, IDs inválidos,
  solicitud simulada, persistencia idempotente, lotes reanudables y Excel.
  La suite general cerró con 286 pruebas correctas y 3 omitidas.

Siguen pendientes la validación jurídica del motor temporal, el conjunto de verdad
revisado por una persona, un segundo pase independiente, el arbitraje
controlado, la aplicación de decisiones humanas al estado oficial, la lectura documental
selectiva, las llamadas reales a NVIDIA y el piloto real de calidad.
El modo `aplicar_controlado` se rechaza explícitamente hasta completar esas
puertas. Los hitos de la hoja son propuestas y no estados oficiales.
