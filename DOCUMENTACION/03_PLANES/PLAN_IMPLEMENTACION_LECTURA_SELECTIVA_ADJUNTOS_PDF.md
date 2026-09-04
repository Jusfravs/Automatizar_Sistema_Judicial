# Plan de implementación: lectura selectiva de adjuntos PDF

## Estado

- Fecha: 27 de agosto de 2026.
- Estado: propuesta para evaluación; no implementado.
- Alcance: añadir evidencia procedente de PDFs de e-SATJE sin sustituir el clasificador actual ni descargar todos los documentos.

## Motivo y diagnóstico

El caso `07333-2022-01899` muestra el vacío actual. La actuación del
`16/12/2022 16:08` aparece como `ESCRITO / FePresentacion`; su PDF dice de
forma expresa que se da contestación a la demanda. Sin embargo, el flujo actual
solo lee la actuación visible en DOM/API y cuenta los controles `Ver archivos`;
no descarga ni interpreta el adjunto. Por ello puede conservar `1.3
CALIFICACION` aun existiendo una contestación real.

La solución no puede ser leer todo: hay causas con muchos escritos y la mayor
parte no cambia la fase procesal.

## Objetivo e invariantes

Objetivo: incorporar una capa de evidencia documental que seleccione y lea
solo PDFs con una posibilidad razonable de cambiar la fase o la fecha de una
fase, y que entregue esa evidencia al `MotorInferenciaProcesal` existente.

Invariantes obligatorios:

1. El resultado actual se mantiene cuando no se lee ningún PDF.
2. Un PDF solo cambia una fase con evidencia afirmativa, atribuible y auditable.
3. La fecha procesal es la fecha de la actuación de presentación en SATJE, no la fecha de firma impresa en el PDF.
4. Cada causa tiene límites explícitos de documentos, tamaño, tiempo y OCR.
5. Ante duda, fallo o límite agotado, no se inventa una fase: se conserva el resultado y se crea una revisión manual.
6. Un adjunto ya validado queda en caché y no se relee en ejecuciones futuras.
7. La nueva lectura no puede alterar la navegación, CAPTCHA ni persistencia actual sin pasar por validaciones.

## Flujo propuesto

```text
Actuaciones DOM/API
  -> índice liviano de adjuntos
  -> puntaje de prioridad
  -> descarga con la sesión autenticada actual
  -> texto nativo del PDF
  -> OCR solo si no hay texto suficiente
  -> evidencia estructurada y atribuida
  -> MotorInferenciaProcesal existente
  -> decisión, auditoría o revisión manual
```

La capa documental produce evidencias; no decide una fase por su cuenta.

## Selección para evitar saturación

### Índice sin descargar

Antes de descargar, guardar por cada adjunto: causa, carpeta, actuación,
fecha/hora, título y tipo visibles, número de adjuntos, nombre/tamaño/MIME/ID
si SATJE los expone, y posición cronológica respecto de la fase consolidada.

### Prioridad determinista

| Señal | Prioridad |
|---|---|
| Título explícito: contestación, excepciones, allanamiento, embargo, sentencia, remate o citación | Muy alta |
| `Escrito / FePresentacion` dentro de una ventana procesal abierta | Alta |
| Escrito posterior a calificación sin contestación confirmada | Alta |
| Documento que puede corregir la última fase o su fecha | Alta |
| Oficio, razón o providencia ya explicada por DOM/API | Media o baja |
| Documento anterior a evidencia posterior concluyente | Baja |
| Repetido, ya procesado o fuera de la ventana útil | No descargar |

Un escrito genérico nunca se considera contestación solo por su nombre. Pero
sí es candidato cuando su fecha y la etapa actual permiten que contenga una
respuesta de la parte demandada. Así se cubre `07333-2022-01899` sin escanear
todos los archivos.

### Presupuesto y parada

Propuesta inicial, configurable después del piloto:

```json
{
  "adjuntos_pdf": {
    "habilitado": false,
    "modo": "observacion",
    "max_adjuntos_por_causa": 6,
    "max_adjuntos_por_carpeta": 4,
    "max_bytes_por_adjunto": 15728640,
    "timeout_descarga_ms": 20000,
    "timeout_ocr_ms": 30000,
    "max_paginas_ocr": 8,
    "confianza_minima_para_aplicar": 0.90
  }
}
```

Se deja de seleccionar cuando se encuentra evidencia concluyente, se alcanza el
presupuesto, los documentos restantes no pueden cambiar la decisión o la sesión
no permite una lectura segura. Si quedan candidatos útiles por leer al llegar al
límite, registrar `REVISION_MANUAL_ADJUNTOS_PENDIENTES` con su lista priorizada.

### Niveles de lectura

1. Metadatos: no descargar, solo indexar y priorizar.
2. Texto nativo: descargar únicamente el candidato y extraer texto directo.
3. OCR dirigido: solo si el PDF es escaneado o el texto es insuficiente.
4. Revisión manual: si hay ambigüedad, baja calidad o presupuesto agotado.

No se ejecuta OCR masivo ni se usa OCR de baja calidad para forzar una fase.

## Descarga y extracción técnica

### Descubrimiento previo

Antes de implementar el lote se debe confirmar en una causa piloto cómo opera
`Ver archivos`: endpoint o URL, método, cookies/sesión, redirecciones, visor o
blob, tipo de respuesta y vínculo entre adjunto, actuación y carpeta.

La descarga debe usar la sesión autenticada de Playwright. No se deben usar
solicitudes externas sin cookies ni clics que desordenen la navegación de la
causa.

### Seguridad de archivo

Validar código HTTP, MIME, cabecera `%PDF`, tamaño, páginas y hash SHA-256.
Rechazar HTML de error, archivos corruptos, protegidos o que superen los límites
y registrar la causa de rechazo sin detener el lote.

### Adaptadores

Separar responsabilidades:

```text
LectorPDFNativo -> texto, páginas y calidad
LectorOCR       -> texto, páginas, idioma y calidad
AnalizadorPDF   -> hallazgos con página, extracto y regla
```

El OCR debe usar español, ser opcional y respetar límites de tamaño, páginas y
tiempo.

## Contrato de evidencia

Cada hallazgo que pueda afectar una decisión debe contener:

```python
{
    "fuente": "PDF_ADJUNTO",
    "causa": "07333-2022-01899",
    "actuacion_id": "<id>",
    "fecha_presentacion": "2022-12-16T16:08:00",
    "documento_id": "<id o URL normalizada>",
    "sha256": "<hash>",
    "pagina": 1,
    "tipo_hallazgo": "CONTESTACION",
    "extracto": "... doy contestación a la demanda ...",
    "regla": "contestacion_explicita_presentada",
    "confianza": 0.98,
    "calidad_texto": 0.99,
    "atribucion": "DEMANDADO_CONFIRMADO"
}
```

Para cambiar una fase se exige: expresión procesal afirmativa, vínculo con la
causa y actuación, atribución compatible con la parte requerida, calidad de
texto suficiente y una regla explícita. Menciones aisladas, plazos para
contestar, citas legales, escritos del actor o comunicaciones de terceros no
son prueba de contestación del demandado.

## Fechas y conflictos

Orden de autoridad:

1. PDF explícito, atribuible y de alta calidad.
2. Actuación judicial explícita de DOM/API.
3. Inferencia estructural actual.
4. Texto ambiguo, que solo añade una advertencia.

Al usar evidencia PDF se publicará la fecha de la actuación SATJE. Las fechas
del documento se conservarán como auxiliares. Si dos evidencias válidas chocan,
registrar `CONFLICTO_EVIDENCIA_PDF` y enviar a revisión, salvo que exista una
regla procesal de precedencia inequívoca.

## Persistencia, caché y privacidad

Usar como clave de caché `documento_id + hash`; si no hay ID estable, usar causa,
carpeta, fecha, URL normalizada, nombre/tamaño y hash. El resultado reutiliza
texto y hallazgos ya validados.

Por defecto almacenar metadatos, hash, texto normalizado necesario y extractos.
Conservar PDFs completos solo si una política explícita de auditoría lo exige.
Separar esos artefactos de CSV/Excel. SQLite guarda las evidencias; los reportes
solo resumen fuente, actuación, regla, confianza y estado de revisión.

## Modos de operación

| Modo | Comportamiento |
|---|---|
| `deshabilitado` | Conserva el funcionamiento actual. |
| `observacion` | Lee candidatos y registra diferencias, sin modificar resultados oficiales. |
| `revision` | Crea sugerencias y una cola de revisión, sin sobrescritura automática. |
| `aplicar` | Usa evidencia de alta confianza en la decisión final. |

Después de desarrollar la función, el valor inicial debe ser `observacion`.
Nunca se habilitará `aplicar` por defecto ni en un lote masivo inicial.

## Validación y despliegue

### Muestra mínima

- `07333-2022-01899`: escrito genérico que sí contiene contestación explícita.
- Escritos del actor que mencionan contestación pero no cuentan como respuesta.
- Providencias que conceden plazo para contestar.
- Documentos de terceros o instituciones.
- PDF nativo, PDF escaneado, PDF ilegible y causa con muchos adjuntos.
- Causa sin adjuntos.

Las fixtures se sanitizarán para no conservar datos personales innecesarios.

### Pruebas automatizadas

1. Priorización correcta de `Escrito / FePresentacion` posterior a calificación.
2. Presupuesto respetado y revisión creada al quedar candidatos relevantes.
3. Contestación explícita detectada con fecha de actuación correcta.
4. Un plazo, una mención del actor o un documento de tercero no generan contestación.
5. OCR solo con texto insuficiente, dentro de límites, y nunca aplica con baja calidad.
6. Caché evita la segunda descarga.
7. Errores de descarga o PDF no válido no derriban el lote.
8. El modo `deshabilitado` conserva los resultados existentes.
9. La regresión de navegación, CAPTCHA, inferencia, SQLite, CSV y Excel es satisfactoria.

### Puertas de avance

1. Piloto técnico: una causa, un adjunto y confirmación del mecanismo de descarga.
2. Piloto en observación: 10 a 20 causas revisadas manualmente.
3. Medir falsos positivos, falsos negativos, PDFs por causa, uso de OCR, duración y revisiones pendientes.
4. Activar `revision` solo si la trazabilidad es completa y no hay falsos positivos críticos.
5. Autorizar un piloto limitado en `aplicar` únicamente mediante decisión explícita posterior.

Un falso positivo que avance una etapa es más grave que enviar una causa a
revisión manual; por ello la métrica global de acierto no es suficiente.

## Criterios de aceptación

1. `07333-2022-01899` se sugiere como contestación con fecha `16/12/2022` y evidencia auditable.
2. Casos sin PDFs o sin candidatos conservan su resultado actual.
3. Los documentos irrelevantes no se descargan fuera del presupuesto.
4. Todo cambio por PDF incluye documento, página, extracto, regla, calidad y fecha de actuación.
5. PDF ambiguo, corrupto o pendiente por límite genera revisión, no una fase inventada.
6. La caché evita reprocesamiento.
7. Ninguna ejecución en observación modifica CSV, Excel ni SQLite oficiales.
8. La suite completa del proyecto y el piloto validado superan la regresión antes de habilitar `aplicar`.

## Orden futuro de implementación

1. Confirmar técnicamente el mecanismo de `Ver archivos` en una sola causa piloto.
2. Implementar índice, prioridad, presupuesto, parada y logs sin aplicar cambios.
3. Añadir descarga autenticada, validación de PDF y caché.
4. Añadir extracción nativa y luego OCR dirigido.
5. Integrar evidencias de alta confianza con el motor, inicialmente en observación.
6. Crear fixtures, pruebas y ejecutar regresión completa.
7. Comparar el piloto con revisión humana y decidir si se ajustan reglas, se usa solo revisión o se autoriza aplicación limitada.

## Decisiones prohibidas

- No descargar todos los adjuntos de cada causa.
- No convertir cada `Escrito / FePresentacion` en contestación.
- No usar una palabra aislada del PDF como decisión procesal.
- No usar la fecha impresa del PDF como fecha procesal principal.
- No ejecutar OCR sin límites.
- No sobrescribir datos oficiales desde el primer piloto.
- No almacenar masivamente PDFs sensibles sin política de retención.

Este diseño aumenta cobertura donde SATJE usa títulos genéricos, pero mantiene
la inferencia actual como base y evita que la lectura de adjuntos se convierta
en un cuello de botella.
