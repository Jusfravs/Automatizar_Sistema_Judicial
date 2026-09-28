# Contrato operativo: historial e inferencia con NVIDIA

**Fecha:** 24 de septiembre de 2026
**Estado:** piloto técnico en modo sombra

## Qué está conectado

Cada resultado SQLite conserva su fotografía en `resultados_expediente` y añade
actuaciones con ID estable en `actuaciones_procesales`. La tabla
`ejecuciones_inferencia` guarda una versión del estado determinista; las
propuestas de NVIDIA se guardan en `auditorias_ia` y las discrepancias en
`revisiones_ia`. Una auditoría no modifica el estado oficial.

El reporte profesional añade `HISTORIAL HITOS` (hitos propuestos con evidencia)
y `REVISION IA` (discrepancias). `Reporte` muestra estado de auditoría,
confianza y revisión pendiente. `PARA CARGA` conserva su contrato actual.

## Datos enviados

El contexto se construye localmente con IDs del catálogo, fechas normalizadas,
orden cronológico, tipo documental reconocido y señales jurídicas de la
taxonomía vigente. Un motor temporal consultivo distingue avances candidatos,
menciones históricas y posibles regresiones. La API no recibe número de causa, nombres, cédulas, correos,
texto libre de actuaciones, PDF ni tabla de correspondencias. Los identificadores
`A1`, `A2`, etc. se traducen de vuelta a actuaciones reales solo después de
validar la respuesta. Se descartan respuestas con IDs incompatibles, evidencia
inexistente, confianza inválida o JSON mal formado.

Esta minimización protege datos personales, aunque limita la capacidad del
modelo de resolver matices que solo constan en el texto libre o en adjuntos.
Esos expedientes deben pasar a revisión o a una fase posterior de evidencia
documental con controles adicionales.

## Configuración y ejecución

`config.json` usa `inferencia_ia.modo = "sombra"` y el modelo
`nvidia/nemotron-3-super-120b-a12b`. Sin ese bloque, el ejecutor considera la
IA deshabilitada. La credencial se lee únicamente de `NVIDIA_API_KEY`.

En la misma ventana de PowerShell donde se configuró la clave:

```powershell
cd 'C:\Users\pasante.callcenter\OneDrive - ESPOIR\Escritorio\Automatizar_Sistema_Judicial'
[bool]$env:NVIDIA_API_KEY
& .\.venv\Scripts\python.exe -m scripts.auditar_inferencia_nvidia --config config.json --limite 1
```

La comprobación debe imprimir `True`. No imprima el valor de la variable.
Para auditar nuevos resultados mientras corre el extractor, use otra ventana
para el extractor y mantenga el ejecutor en la ventana que tiene la clave:

```powershell
& .\.venv\Scripts\python.exe -m scripts.auditar_inferencia_nvidia --config config.json --seguir --limite 10 --intervalo 60
```

Se detiene con `Ctrl+C`. Cada lote salta auditorías terminadas con la misma
huella de actuaciones y versión de prompt; las fallidas pueden reintentarse.
`401`, `402` o ausencia de clave abren el circuito y detienen el ejecutor. Los
errores no impiden que la extracción continúe.

Para registrar decisiones humanas, edite únicamente las columnas
`DECISION HUMANA`, `eta_id MANUAL`, `fas_id MANUAL` y `OBSERVACION HUMANA` de
`REVISION IA`. Primero valide el archivo y luego impórtelo:

```powershell
& .\.venv\Scripts\python.exe -m scripts.importar_revision_ia --config config.json --excel 'ruta\reporte_revisado.xlsx' --simular
& .\.venv\Scripts\python.exe -m scripts.importar_revision_ia --config config.json --excel 'ruta\reporte_revisado.xlsx'
```

Se aceptan `ACEPTAR_SISTEMA`, `ACEPTAR_IA`, `CORREGIR_MANUALMENTE` y
`POSPONER`. El importador rechaza auditorías duplicadas u obsoletas,
combinaciones de IDs inválidas y propuestas sin evidencia. En esta fase las
decisiones quedan registradas, pero no reescriben el estado oficial.

La normalización histórica se ejecutó con `--solo-migrar --limite 0` sobre
`data/estado_casos_20260827.db`. El respaldo previo está en
`data/backups/estado_casos_pre_historial_ia_20260923.db`.
PostgreSQL tiene la migración `002_historial_inferencia_ia.sql` y el historial
de sus 1.954 expedientes se normalizó sin reconsultar SATJE. El mismo comando
del auditor usa PostgreSQL cuando `base_de_datos.motor` vale `postgres`; su
esquema ya está preparado.

### Hallazgo del primer piloto (24 de septiembre de 2026)

La conexión real con NVIDIA funcionó: once auditorías del piloto comunicado
terminaron sin error; hay doce registros de la versión inicial en la base.
Sin embargo, los doce se marcaron como correcciones porque los expedientes
históricos guardaban la etapa y fase como etiquetas, sin las columnas de IDs
que inicialmente esperaba el auditor. Por eso el modelo recibió el estado
determinista como vacío. **Esas once propuestas no son evidencia de un fallo
del motor judicial y no deben aprobarse.**

Desde `auditoria-nvidia-2`, el auditor convierte localmente las etiquetas
históricas mediante el catálogo oficial antes de construir el contexto.
La segunda muestra real de doce casos terminó sin errores de API, pero volvió
a marcar los doce como correcciones. Al comparar los IDs con el estado guardado,
cuatro propuestas cambian la fase actual, cuatro cambian solo la última fase
y cuatro dicen `CORREGIR` sin cambiar ningún ID. Por tanto, la versión 2
tampoco supera la puerta de calidad y sus propuestas no deben aprobarse.

`auditoria-nvidia-3` explicita que la última fase es la última **concluida**,
distinta de la fase actual en curso. Rechaza `CORREGIR` sin cambios y
`CONSERVAR` con cambios. Las versiones anteriores permanecen en el registro,
pero quedan fuera de las hojas de revisión vigentes y el importador no permite
aceptarlas. La siguiente prueba debe ser pequeña (`--limite 2`) desde la
ventana que conserva `NVIDIA_API_KEY`; solo después de contrastar esos casos
se ampliará la muestra. El modo continúa siendo `sombra` y no se altera la
clasificación oficial.

## Límites antes del modo controlado

Este piloto no aplica correcciones ni usa un segundo modelo. Faltan el conjunto
de verdad validado por una persona, la validación jurídica del motor temporal,
el arbitraje de dos pases y el piloto de calidad exigidos por el plan maestro.
No active `aplicar_controlado` hasta que
esas puertas estén implementadas y superadas.
