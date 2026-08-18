# Plan de implementación definitivo: freno transaccional en Información del proceso

## 0. Estado y propósito del documento

- Versión del plan: 2.0.
- Fecha de contraste: 7 de agosto de 2026.
- Estado: listo para implementación.
- Este documento sustituye la versión anterior del plan.
- Esta fase solo define el parche. No autoriza todavía la ejecución masiva ni la lectura automática de adjuntos.

El plan fue contrastado con el código actual de `src/motor_busqueda_web.py`, `main.py`, `src/logger_config.py`, `src/gestor_cola.py`, las pruebas existentes, los scripts de diagnóstico y los artefactos reales `monitoreo_23331202202089_004`, `005` y `006`.

## 1. Objetivo e invariante principal

Corregir el flujo automático de `BotJudicial` para que cada llegada válida a `/actuaciones` active una transacción de extracción durante la cual no pueda ocurrir ninguna navegación.

Invariante no negociable:

> Desde que se valida `INFORMACION_PROCESO_LISTA` hasta que existe un resultado de carpeta durable —completo, parcial registrado o error registrado— no se permite ningún clic, `go_back()`, `goto()`, apertura de carpeta, retorno ni cambio de causa.

El bloqueo cubre:

1. estabilización final de la pantalla;
2. cierre de la ventana de captura API;
3. captura DOM e iframes;
4. normalización de actuaciones;
5. inferencia por carpeta;
6. guardado de artefactos y manifiesto de resultado;
7. emisión del evento terminal de carpeta.

La persistencia final de la causa en CSV y SQLite ocurre después de consolidar todas sus carpetas, pero siempre antes de comenzar la siguiente causa.

## 2. Diagnóstico confirmado contra el código actual

### 2.1. El flujo salta prematuramente de `/movimientos` a `/actuaciones`

En la rama donde los resultados están en `/causas`, `_abrir_detalle_causa()` realiza dos clics seguidos:

1. abre `/movimientos`;
2. localiza globalmente `Ver detalle del proceso judicial` y abre `/actuaciones`.

Después, `_esperar_datos_generales()` acepta la pantalla porque el texto **Datos generales** también está presente dentro de `/actuaciones`. Como resultado, el descubrimiento posterior se ejecuta en la pantalla equivocada.

Corrección obligatoria: sustituir esta responsabilidad por `_abrir_movimientos_causa()`, que debe terminar exclusivamente en `/movimientos`. La apertura de `/actuaciones` se hará después de descubrir y validar una carpeta procesal concreta.

### 2.2. Los selectores actuales confunden carpetas con adjuntos

`_boton_carpeta_en_fila()` incluye explícitamente:

```text
[mattooltip='Ver archivos']
[role='link'][aria-label*='archivo' i]
```

También acepta cualquier accionable cuyo texto contenga `ARCHIVO`. Al ejecutarse dentro de `/actuaciones`, `_descriptores_carpetas_actuaciones()` puede interpretar los adjuntos como carpetas procesales.

Los artefactos reales confirman que:

- en `/movimientos`, la estructura relevante es `.lista-movimientos-causa`;
- una dependencia está representada por `.movimiento-individual`;
- cada incidente o carpeta accionable está en `.lista-movimiento-individual`;
- el enlace válido contiene `href=".../actuaciones"` y el icono tiene `mattooltip="Ver detalle del proceso judicial"`;
- en `/actuaciones`, los adjuntos son elementos `role="link"` con `mattooltip="Ver archivos"` y aparecen muchas veces.

Corrección obligatoria: eliminar el selector genérico compartido. Las carpetas procesales y los adjuntos tendrán detectores separados y mutuamente excluyentes.

### 2.3. La espera actual no identifica de forma exclusiva las pantallas

`_esperar_datos_generales()` no exige `/movimientos`. `_esperar_actuaciones()` acepta cualquiera de varias frases sin exigir `/actuaciones`, causa coincidente ni estabilidad. `_esperar_pantalla_final_estable()` requiere al menos un botón `Ver archivos`, por lo que una carpeta legítima sin adjuntos nunca podría considerarse estable.

Corrección obligatoria: implementar detectores de pantalla puros que combinen ruta URL exacta, encabezados, causa, contenedores exclusivos, ausencia de carga y firma estable. La cantidad de botones `Ver archivos` solo será una métrica diagnóstica; nunca una precondición de éxito.

### 2.4. La extracción actual puede hacer clic

La ruta DOM de `_ejecutar_extraccion_detalles()` espera una respuesta y, si no llega, intenta pulsar pestañas de actuaciones. Incluso usa `page.evaluate()` para buscar texto y ejecutar `click()`.

Corrección obligatoria: la nueva rutina de extracción será de solo lectura. No podrá recibir ni invocar capacidades de navegación. Se eliminarán de ella todos los clics, incluyendo el clic por JavaScript.

### 2.5. No existe un bloqueo real

El código actual registra estados mediante `_cambiar_estado_navegacion()`, pero no existe una barrera que impida un clic. Un estado de log no es un mecanismo de exclusión.

Corrección obligatoria: todas las operaciones de navegación pasarán por una única puerta que consulte un bloqueo con contexto. Durante las pruebas, cualquier intento será registrado y fallará con `NAVEGACION_BLOQUEADA`.

### 2.6. La captura API no está suficientemente delimitada

El listener actual acumula respuestas en una lista global. `_procesar_todas_las_carpetas()` toma un índice antes del clic, pero los paquetes no tienen secuencia, instante, tipo de recurso ni identidad de carpeta. Además, la ruta API puede retornar antes de guardar HTML y otros artefactos.

Corrección obligatoria: abrir una ventana de captura antes del clic de carpeta, cerrarla después de la estabilidad, correlacionar sus paquetes y guardar artefactos tanto para API como para DOM.

### 2.7. Existe un retorno duplicado

`_procesar_todas_las_carpetas()` intenta volver a Datos generales después de cada carpeta. Al terminar, `_procesar_flujo_autonomo()` vuelve a llamar `_volver_a_datos_generales()` antes de regresar al buscador.

Corrección obligatoria: cada carpeta hará un único retorno `/actuaciones -> /movimientos`; terminado el ciclo, la causa hará un único retorno `/movimientos -> buscador`.

### 2.8. El contrato con `main.py` y SQLite no distingue bien los resultados

Actualmente `main.py` interpreta un booleano y, ante `True`, trata el caso como exitoso. `GestorCola.registrar_resultado_transaccional()` marca siempre `PROCESADO`, aunque los datos puedan contener `ESTADO_NAVEGACION="PARCIAL"`. Un fallo de SQLite se limita a una advertencia y el lote puede avanzar.

Corrección obligatoria: devolver un resultado estructurado, persistir el estado real y no iniciar otra causa si la persistencia final de la actual no quedó confirmada.

### 2.9. Las pruebas abren el log de producción al importar módulos

`src/logger_config.py` crea `ejecucion_produccion.log` desde `obtener_logger()`, y los módulos crean sus loggers durante la importación. Por ello una prueba puede escribir en el mismo archivo que una ejecución real.

Corrección obligatoria: separar la configuración de handlers de la obtención del logger. Solo los puntos de entrada de producción habilitarán el archivo de producción.

## 3. Alcance exacto del parche

### 3.1. Archivos que deben cambiar

- `src/motor_busqueda_web.py`: flujo, detectores, bloqueo, captura API, extracción por carpeta, consolidación y retorno.
- `main.py`: consumo del resultado estructurado, persistencia por estado y freno antes de la siguiente causa.
- `src/logger_config.py`: configuración explícita y log por entorno.
- `src/gestor_cola.py`: persistencia de estado final `PROCESADO`, `PARCIAL`, `SIN_RESULTADOS` o `ERROR` sin forzar siempre `PROCESADO`.
- `config.json`: parámetros explícitos de estabilidad y quietud API.
- `tests/test_navegacion_esatje.py`: pruebas unitarias del flujo y del bloqueo.
- `tests/test_extraccion_integration.py` o un archivo nuevo específico: integración de extracción por carpeta y consolidación.
- `tests/conftest.py`: aislamiento del logging cuando se ejecuta con pytest.
- `scripts/diagnosticar_esatje.py`: mostrar el nuevo resultado estructurado.
- `scripts/monitorear_esatje.py`: configurar un log diagnóstico independiente, si se conserva el script.

### 3.2. Archivos que solo deben cambiar si una prueba demuestra necesidad

- `src/agente_extractor.py`: debe mantenerse como transformador de contenido e inferencia, sin asumir navegación. Solo se modifica si hace falta aceptar metadatos ya extraídos o corregir el contrato de datos.
- `src/gestor_casos.py`: preferir usar su interfaz actual. Solo se modifica si resulta imprescindible para confirmar la escritura por causa.

### 3.3. Fuera de alcance

- Clic o lectura automática de `Ver archivos`.
- Descarga de adjuntos.
- Rediseño del motor de inferencia procesal.
- Cambios funcionales en `AgenteExplorador` o `src/orquestador.py`.
- Ejecución masiva antes de superar el piloto.

`AgenteExplorador` pertenece al flujo alternativo de `orquestador.py`; no forma parte del grafo ejecutado por `main.py`. No se mezclará ese flujo con este parche. Si posteriormente se desea aplicar la misma máquina de navegación al orquestador, será un cambio separado.

## 4. Terminología y fronteras

- **Resultado de búsqueda**: registro que representa la causa solicitada.
- **Movimientos**: pantalla `/movimientos` que contiene Datos generales y la lista de dependencias/incidentes.
- **Dependencia**: contenedor `.movimiento-individual` con dependencia jurisdiccional y ciudad.
- **Carpeta procesal**: fila hija `.lista-movimiento-individual` que posee un único enlace validado a `/actuaciones`.
- **Información del proceso**: pantalla `/actuaciones` con la información y actuaciones de una carpeta procesal.
- **Adjunto**: control `Ver archivos` asociado a una actuación; nunca es carpeta procesal.
- **Resultado durable de carpeta**: manifiesto JSON escrito correctamente, acompañado por los artefactos disponibles, que declara `COMPLETA`, `PARCIAL_REGISTRADA` o `ERROR_REGISTRADO`.
- **Persistencia final de causa**: actualización confirmada del repositorio de trabajo y SQLite antes de iterar a la siguiente causa.

## 5. Flujo funcional definitivo

```text
BUSCADOR
  -> preparar causa y CAPTCHA
  -> BUSCAR exactamente una vez por intento
  -> validar resultado único
  -> abrir únicamente el vínculo de movimientos de la causa
  -> /movimientos
  -> esperar ausencia de carga y firma estable
  -> descubrir todos los descriptores de carpeta

  -> por cada descriptor pendiente:
       abrir ventana de captura API
       volver a localizar la carpeta
       hacer un único clic en su enlace /actuaciones
       validar /actuaciones y la causa
       activar bloqueo de navegación
       esperar estabilidad y quietud API
       cerrar y correlacionar ventana API
       capturar API + DOM + iframes
       extraer e inferir una sola vez
       persistir artefactos y manifiesto de carpeta
       emitir resultado terminal de carpeta
       liberar bloqueo
       volver una sola vez a /movimientos
       revalidar causa y reconstruir locators

  -> consolidar todas las carpetas
  -> inferir resultado final de causa
  -> volver una sola vez al buscador
  -> devolver resultado estructurado
  -> main.py persiste CSV/SQLite según el estado
  -> solo entonces comenzar la siguiente causa
```

## 6. Máquina de estados

### 6.1. Estados operativos

Implementar valores constantes o un `Enum`; no usar cadenas libres dispersas.

```text
PREPARAR_BUSCADOR
CAUSA_ESCRITA
ESPERAR_FIN_CAPTCHA
BUSQUEDA_HABILITADA
BUSQUEDA_ENVIADA
RESULTADOS_LISTOS
ABRIENDO_MOVIMIENTOS
MOVIMIENTOS_CARGANDO
MOVIMIENTOS_LISTOS
CARPETAS_DESCUBIERTAS
ABRIENDO_INFORMACION_PROCESO
INFORMACION_PROCESO_CARGANDO
INFORMACION_PROCESO_LISTA
EXTRACCION_EN_PROGRESO
RETORNANDO_A_MOVIMIENTOS
CONSOLIDACION_EN_PROGRESO
RETORNANDO_AL_BUSCADOR
CAUSA_COMPLETADA
CAUSA_PARCIAL
CAUSA_SIN_RESULTADOS
CAUSA_ERROR
```

El bloqueo es una condición ortogonal y no reemplaza al estado operativo. Se audita con eventos `NAVEGACION_BLOQUEADA` y `NAVEGACION_REANUDADA`.

### 6.2. Transiciones permitidas relevantes

| Estado origen | Estado destino | Condición |
|---|---|---|
| `RESULTADOS_LISTOS` | `ABRIENDO_MOVIMIENTOS` | resultado y causa validados |
| `ABRIENDO_MOVIMIENTOS` | `MOVIMIENTOS_CARGANDO` | clic único ejecutado |
| `MOVIMIENTOS_CARGANDO` | `MOVIMIENTOS_LISTOS` | URL, causa, carga y firma válidas |
| `MOVIMIENTOS_LISTOS` | `CARPETAS_DESCUBIERTAS` | descriptores inmutables creados |
| `CARPETAS_DESCUBIERTAS` | `ABRIENDO_INFORMACION_PROCESO` | descriptor pendiente relocalizado |
| `ABRIENDO_INFORMACION_PROCESO` | `INFORMACION_PROCESO_CARGANDO` | clic único ejecutado |
| `INFORMACION_PROCESO_CARGANDO` | `INFORMACION_PROCESO_LISTA` | URL, causa y pantalla validadas |
| `INFORMACION_PROCESO_LISTA` | `EXTRACCION_EN_PROGRESO` | bloqueo activo |
| `EXTRACCION_EN_PROGRESO` | `RETORNANDO_A_MOVIMIENTOS` | resultado de carpeta durable y bloqueo liberado |
| `RETORNANDO_A_MOVIMIENTOS` | `MOVIMIENTOS_LISTOS` | retorno único y pantalla revalidada |
| `MOVIMIENTOS_LISTOS` | `CONSOLIDACION_EN_PROGRESO` | no quedan descriptores pendientes |
| `CONSOLIDACION_EN_PROGRESO` | `RETORNANDO_AL_BUSCADOR` | consolidado construido |

Una transición no listada debe fallar con un error controlado y generar evidencia. `_cambiar_estado_navegacion()` validará el estado actual en vez de aceptar un `anterior` declarado por el llamador.

### 6.3. Errores estructurados

```text
RESULTADOS_TIMEOUT
RESULTADO_AMBIGUO
MOVIMIENTOS_TIMEOUT
MOVIMIENTOS_CAUSA_INCONSISTENTE
CARPETA_PROCESAL_AUSENTE
CARPETA_PROCESAL_AMBIGUA
CARPETA_NO_RELOCALIZABLE
INFORMACION_PROCESO_TIMEOUT
INFORMACION_PROCESO_CAUSA_INCONSISTENTE
PANTALLA_ACTUACIONES_NO_ESTABLE
NAVEGACION_BLOQUEADA
EXTRACCION_ERROR
ARTEFACTOS_ERROR
RETORNO_ERROR
CONSOLIDACION_ERROR
PERSISTENCIA_ERROR
```

## 7. Bloqueo central de navegación

### 7.1. Contexto del bloqueo

El controlador mantendrá un objeto de bloqueo, no solo un booleano:

```python
{
    "activo": True,
    "token": "<uuid o intento_id:clave_carpeta>",
    "motivo": "EXTRACCION_INFORMACION_PROCESO",
    "causa": "23331202202089",
    "clave_carpeta": "...",
    "url_inicio": ".../actuaciones",
    "inicio_monotonic": 123.45,
}
```

### 7.2. Única puerta de navegación

Crear wrappers centrales para:

```text
_click_navegacion(locator, contexto)
_go_back_navegacion(contexto)
_goto_navegacion(url, contexto)
```

Antes de actuar, los tres llamarán `_asegurar_navegacion_permitida()`. No quedarán llamadas directas a `click()`, `go_back()` o `goto()` dentro del flujo autónomo, salvo las internas de estos wrappers y las acciones iniciales de apertura del navegador claramente excluidas del ciclo.

El desbloqueo no es una excepción genérica al guard. Debe realizarse mediante `_finalizar_bloqueo(token, resultado_durable)` y verificar:

- que el token coincide;
- que la causa y la carpeta siguen siendo las esperadas;
- que existe un manifiesto de resultado escrito correctamente;
- que el resultado terminal es permitido.

### 7.3. Uso de `finally`

`finally` debe intentar cerrar la transacción, pero no puede desbloquear incondicionalmente.

```python
resultado_durable = None
token = bloquear(...)
try:
    resultado = extraer_inferir_y_guardar(...)
    resultado_durable = resultado.manifiesto_confirmado
except Exception as exc:
    resultado_durable = guardar_error_y_evidencia(exc)
finally:
    if resultado_durable:
        finalizar_bloqueo(token, resultado_durable)
```

Si tampoco puede guardarse el error, el estado será `ARTEFACTOS_ERROR`, no se intentará retornar ni continuar y el lote deberá detenerse.

## 8. Detectores exclusivos de pantalla

Los detectores deben ser funciones de lectura sin efectos laterales. Deben devolver un diagnóstico con cada señal evaluada, no solo `True` o `False`.

### 8.1. Resultados

Condiciones:

- vista o ruta compatible con resultados;
- una única coincidencia de causa canónica;
- vínculo de movimientos localizado dentro del resultado validado;
- en `/causas`, `aria-label` del vínculo contiene la causa canónica.

Acción permitida: un único clic en el vínculo validado.

### 8.2. `/movimientos`

Condiciones obligatorias:

- el `path` de la URL es exactamente `/movimientos`, permitiendo query o fragmento;
- no hay overlay, spinner, barra de progreso ni texto visible `Buscando...`;
- aparece el encabezado **Datos generales**;
- **Número de proceso** coincide con la causa canónica;
- existe `.lista-movimientos-causa` con la cabecera **Actuaciones Judiciales**;
- el conjunto de dependencias e incidentes permanece estable durante las comprobaciones configuradas.

Selectores prioritarios basados en evidencia real:

```text
.lista-movimientos-causa
.movimiento-individual
.lista-movimiento-individual
a[href*='/actuaciones']
[mattooltip='Ver detalle del proceso judicial']
```

No usar un selector global `.first`. Un resultado con cero incidentes produce `CARPETA_PROCESAL_AUSENTE`; uno o varios incidentes son válidos.

### 8.3. `/actuaciones`

Condiciones obligatorias:

- el `path` es exactamente `/actuaciones`;
- aparece el encabezado **Información del proceso**;
- el número de proceso coincide con la causa;
- existe al menos un control exclusivo de la vista, como `Exportar PDF`, `Ampliar todo` o `Contraer todo`;
- no hay overlay visible;
- la sección de actuaciones alcanzó estabilidad o existe una respuesta API terminal válida;
- una pantalla sin adjuntos sigue siendo válida.

Acciones permitidas: leer red ya capturada, DOM, frames y atributos.

Acciones prohibidas: cualquier clic, incluso `Ampliar todo`, pestañas, texto encontrado mediante JavaScript, `Ver archivos`, `Cerrar` o `Regresar`.

## 9. Espera y firma de estabilidad

### 9.1. Parámetros configurables

Añadir a `navegacion`:

```json
{
  "sondeo_estabilidad_ms": 250,
  "comprobaciones_estables": 3,
  "quietud_api_ms": 750,
  "movimientos_timeout_ms": 30000,
  "pantalla_final_timeout_ms": 30000
}
```

Los valores se podrán ajustar con evidencia, pero las pruebas no dependerán de esperas reales.

### 9.2. Firma de `/movimientos`

La firma contendrá:

- causa canónica;
- número de dependencias visibles;
- número total de incidentes visibles;
- por cada incidente: texto normalizado, fecha, número de incidente y destino del enlace;
- estado de carga.

La firma debe repetirse `comprobaciones_estables` veces. Un cambio reinicia el contador.

### 9.3. Firma de `/actuaciones`

La firma contendrá:

- causa canónica;
- cantidad de nodos de actuaciones;
- cantidad de fechas detectadas;
- longitud del texto normalizado de la sección de actuaciones;
- primer y último identificador o texto normalizado de actuación;
- cantidad de `Ver archivos`, solo para diagnóstico;
- última secuencia API de la ventana;
- estado de carga.

Se considera estable cuando la firma se repite y además transcurre `quietud_api_ms` sin una nueva respuesta API relevante. Si la API declara explícitamente una lista vacía o la UI presenta un estado vacío, la estabilidad con cero actuaciones es válida.

No se usará `networkidle` como única condición, porque una SPA puede mantener actividad de red ajena al expediente.

## 10. Descriptores de carpeta procesal

### 10.1. Descubrimiento

El descubrimiento se ejecuta una sola vez al entrar establemente a `/movimientos`, pero la fila se vuelve a localizar antes de cada clic.

Por cada `.movimiento-individual`:

1. leer dependencia jurisdiccional y ciudad del contenedor padre;
2. recorrer cada `.lista-movimiento-individual` visible;
3. exigir exactamente un `a[href*='/actuaciones']` accionable dentro de esa fila hija;
4. construir un descriptor inmutable;
5. no conservar locators de Playwright.

### 10.2. Campos requeridos

```python
{
    "causa": "23331202202089",
    "dependencia": "Unidad Judicial ...",
    "ciudad": "Santo Domingo",
    "numero_incidente": "1",
    "fecha_ingreso": "14/06/2022 15:52",
    "actores": "...",
    "demandados": "...",
    "texto_normalizado": "...",
    "href_actuaciones": ".../actuaciones",
    "id_api": None,
    "clave_carpeta": "...",
}
```

### 10.3. Clave estable y colisiones

Prioridad para `clave_carpeta`:

1. identificador API de proceso/incidente, si existe;
2. causa + dependencia normalizada + número de incidente + fecha de ingreso;
3. hash SHA-256 corto del texto normalizado como complemento, nunca como único dato humano.

El índice visual no forma parte principal de la identidad; solo se conserva para diagnóstico. Dos descriptores con la misma clave provocan `CARPETA_PROCESAL_AMBIGUA` antes de hacer clic.

### 10.4. Relocalización

La relocalización reconstruye dependencias e incidentes y busca la misma clave. Debe producir exactamente una coincidencia. Si Angular cambió el DOM pero los datos son equivalentes, la clave debe seguir funcionando.

## 11. Ventana y correlación de captura API

### 11.1. Registro de respuestas

Cada paquete capturado deberá incluir:

```python
{
    "secuencia": 42,
    "capturado_monotonic": 123.45,
    "url": "...",
    "status": 200,
    "resource_type": "xhr",
    "payload": {...},
}
```

Filtrar desde el listener los recursos estáticos y conservar únicamente JSON de endpoints judiciales relevantes.

### 11.2. Ventana por carpeta

Orden obligatorio:

```text
marcar secuencia inicial
-> relocalizar carpeta
-> clic único
-> validar /actuaciones
-> bloquear navegación
-> esperar pantalla estable y quietud API
-> marcar secuencia final
-> correlacionar paquetes [inicio, fin]
```

La correlación priorizará identificadores de causa y carpeta presentes en payload o URL. Un paquete sin identificador solo podrá atribuirse si:

- pertenece a un endpoint de actuaciones;
- cayó dentro de la ventana exclusiva;
- no se ejecutó otra navegación en esa ventana;
- no contiene un identificador incompatible.

Los paquetes dudosos se guardan como evidencia, pero no se usan como fuente primaria sin dejar una advertencia estructurada.

## 12. Operación bloqueante de extracción

Crear un único punto de entrada:

```python
_extraer_informacion_proceso(causa, descriptor, ventana_api)
```

Responsabilidades exactas:

1. comprobar nuevamente `/actuaciones`, causa y descriptor;
2. activar el bloqueo;
3. esperar estabilidad y cerrar la ventana API;
4. capturar HTML principal y frames legibles;
5. capturar screenshot y diagnóstico de pantalla;
6. normalizar paquetes API correlacionados;
7. llamar exactamente una vez al procesamiento de contenido de esa carpeta;
8. realizar inferencia por carpeta;
9. adjuntar dependencia, ciudad, incidente y clave a cada actuación;
10. crear el resultado estructurado de carpeta;
11. guardar los artefactos y el manifiesto atómicamente;
12. emitir `EXTRACCION_COMPLETA`, `EXTRACCION_PARCIAL_REGISTRADA` o `EXTRACCION_ERROR_REGISTRADO`;
13. liberar el bloqueo solo con el manifiesto confirmado;
14. devolver el resultado sin navegar.

`_ejecutar_extraccion_detalles()` se convertirá en una función de transformación sin clics. La selección API/DOM debe seguir estas reglas:

- API utilizable: procesar API y conservar DOM como evidencia; no retornar antes de guardar artefactos.
- API parcial o dudosa: combinar de manera determinista con DOM, deduplicando por identidad de actuación.
- API inutilizable: usar DOM y registrar el motivo del respaldo.
- inferencia fallida con actuaciones obtenidas: conservar actuaciones y declarar `PARCIAL_REGISTRADA`.
- extracción sin actuaciones pero con estado vacío confirmado: resultado completo vacío, no error automático.

## 13. Artefactos e idempotencia

### 13.1. Estructura

Usar una carpeta por intento y carpeta procesal:

```text
data/temp_htmls/<causa>/<intento_id>/<clave_carpeta>/
  page.html
  frame_001.html
  api.json
  screen.png
  diagnostic.json
  result.json
```

No reutilizar `<causa>.html` para varias carpetas, porque actualmente se sobrescribe.

### 13.2. Escritura durable

`result.json` es el marcador terminal. Se escribe en un archivo temporal del mismo directorio y se publica mediante reemplazo atómico. El bloqueo no se libera si el marcador no existe o no puede releerse.

El manifiesto incluye:

- versión de esquema;
- causa, intento y clave de carpeta;
- estado terminal;
- firma de pantalla;
- secuencias API inicial y final;
- fuente utilizada `API`, `DOM` o `API+DOM`;
- cantidades extraídas;
- inferencia;
- advertencias y errores;
- rutas y hashes de artefactos;
- tiempos de inicio, fin y duración.

### 13.3. Garantía de una sola extracción

Dentro de un intento, mantener un conjunto `claves_extraidas`. Una clave solo puede entrar una vez a `_extraer_informacion_proceso()`.

Entre reintentos o reinicios no se promete ejecución física exactamente una vez. Se garantiza idempotencia lógica: la misma causa, carpeta e intento no duplica el resultado, y la persistencia final usa actualización por clave. Los criterios de aceptación usarán la frase “exactamente una vez por carpeta y por intento”.

## 14. Resultado de carpeta y consolidado de causa

### 14.1. Estados de carpeta

```text
COMPLETA
PARCIAL_REGISTRADA
ERROR_REGISTRADO
```

- `COMPLETA`: captura, normalización, inferencia aplicable y artefactos confirmados.
- `PARCIAL_REGISTRADA`: existe evidencia útil, pero falló o quedó incompleta una parte no destructiva, como inferencia o una fuente secundaria.
- `ERROR_REGISTRADO`: no existe información útil normalizada, pero el error y la evidencia quedaron guardados.

### 14.2. Consolidación

Después de procesar todas las carpetas:

- enriquecer cada actuación con su origen antes de deduplicar;
- deduplicar solo dentro de la misma carpeta, salvo que exista un identificador API global confiable;
- conservar `ORIGEN_CARPETA`, dependencia, ciudad, incidente y `ORIGEN_DATA`;
- ejecutar una inferencia final de causa con todas las actuaciones;
- conservar también la inferencia individual de cada carpeta;
- no permitir que un resultado vacío de una carpeta sobrescriba datos válidos de otra.

Estado final de causa:

| Condición | Estado |
|---|---|
| Todas las carpetas `COMPLETA` | `COMPLETADO` |
| Al menos una carpeta útil y alguna parcial/error | `PARCIAL` |
| Todas las carpetas con error registrado | `EXTRACCION_ERROR` |
| No existe resultado de búsqueda | `SIN_RESULTADOS` |
| Falla antes de obtener carpetas o no puede retornar | `ERROR_NAVEGACION` |

## 15. Retorno, continuación y reintentos

### 15.1. Retorno a `/movimientos`

Solo después de liberar correctamente el bloqueo:

1. confirmar que la pantalla actual es `/actuaciones` de la causa;
2. usar un único control `Regresar` validado;
3. esperar URL `/movimientos`;
4. si el control no existe o falla sin transición, permitir un único `go_back()` como respaldo;
5. ejecutar `_esperar_movimientos_listos(causa)`;
6. reconstruir los locators a partir de los descriptores;
7. continuar con la siguiente clave pendiente.

No usar `Cerrar` como equivalente de `Regresar` sin evidencia de que produce `/movimientos`.

### 15.2. Retorno al buscador

Cuando no quedan carpetas pendientes:

1. consolidar la causa;
2. desde `/movimientos`, ejecutar una única estrategia de retorno;
3. validar el campo único de búsqueda;
4. devolver el resultado estructurado.

Eliminar la llamada duplicada a `_volver_a_datos_generales()` del flujo externo.

### 15.3. Política de reintentos por fase

- Antes de abrir una carpeta: puede repetirse la búsqueda completa según `max_reintentos_transicion`.
- Después de abrir una carpeta pero antes de crear resultado durable: registrar el error; no repetir ciegamente el clic.
- Después de persistir una carpeta: nunca reiniciar toda la causa dentro del mismo intento. Volver a `/movimientos` y continuar solo con claves pendientes.
- Si no se puede retornar después de una carpeta: terminar la causa como `ERROR_NAVEGACION` o `PARCIAL`, según los resultados ya durables; no comenzar otra causa con la página en estado desconocido.
- Un `KeyboardInterrupt` detiene el lote y realiza solo guardado de evidencia de mejor esfuerzo; nunca navega durante la interrupción.

## 16. Contrato entre `BotJudicial`, `main.py` y persistencia

### 16.1. Retorno público

`procesar_flujo_judicatura()` devolverá un diccionario estructurado; `main.py` no evaluará su truthiness.

```python
{
    "causa": "23331202202089",
    "estado": "COMPLETADO | PARCIAL | SIN_RESULTADOS | EXTRACCION_ERROR | ERROR_NAVEGACION",
    "regreso_confirmado": True,
    "datos": {...},
    "carpetas_descubiertas": 2,
    "carpetas_completas": 1,
    "carpetas_parciales": 1,
    "carpetas_error": 0,
    "resultados_carpetas": [...],
    "errores": [...],
    "artefactos": [...],
}
```

`extraer_detalles_juicio()` puede conservarse temporalmente como adaptador de compatibilidad, pero `main.py` dejará de depender del patrón booleano + lectura destructiva posterior.

### 16.2. Persistencia en `main.py`

Orden obligatorio por causa:

1. recibir y validar el resultado estructurado;
2. para `COMPLETADO` o `PARCIAL`, actualizar los datos disponibles en el repositorio de trabajo;
3. confirmar `repo.guardar()` para que no sea solo una modificación en memoria;
4. persistir resultado y estado en SQLite de forma idempotente;
5. para `SIN_RESULTADOS` o errores, registrar evento y estado correspondiente;
6. solo tras confirmar el paso aplicable, incrementar contadores y avanzar.

`GestorCola.registrar_resultado_transaccional()` aceptará un `estado_final` validado. Mapeo:

```text
COMPLETADO       -> PROCESADO
PARCIAL          -> PARCIAL
SIN_RESULTADOS   -> SIN_RESULTADOS
EXTRACCION_ERROR -> ERROR
ERROR_NAVEGACION -> ERROR
```

Si falla la persistencia final en CSV o SQLite, el lote se detiene con `PERSISTENCIA_ERROR`. No se registra éxito ni se inicia la causa siguiente. Una reejecución será segura porque SQLite usa `ON CONFLICT` y los artefactos de carpeta son idempotentes.

## 17. Logging y auditoría

### 17.1. Configuración

`obtener_logger()` solo devolverá el logger; no debe decidir por sí mismo el archivo de salida durante la importación.

Crear una configuración explícita, por ejemplo:

```python
configurar_logging(ruta_archivo, consola=True)
```

- `main.py`: `ejecucion_produccion.log`.
- pruebas: archivo temporal o ningún `FileHandler`.
- diagnóstico: `diagnostico_esatje.log` o ruta suministrada.
- evitar handlers duplicados al reconfigurar.

### 17.2. Eventos mínimos

```text
MOVIMIENTOS_CARGANDO
MOVIMIENTOS_LISTOS
CARPETAS_DESCUBIERTAS
ABRIENDO_INFORMACION_PROCESO
INFORMACION_PROCESO_LISTA
NAVEGACION_BLOQUEADA
EXTRACCION_EN_PROGRESO
EXTRACCION_COMPLETA | EXTRACCION_PARCIAL_REGISTRADA | EXTRACCION_ERROR_REGISTRADO
NAVEGACION_REANUDADA
RETORNANDO_A_MOVIMIENTOS
CONSOLIDACION_EN_PROGRESO
RETORNANDO_AL_BUSCADOR
CAUSA_COMPLETADA | CAUSA_PARCIAL | CAUSA_ERROR
```

Todo evento incluirá `causa`, `intento_id`, estado anterior/siguiente, URL y timestamp. Los eventos de carpeta incluirán `clave_carpeta`, secuencias API, firma, cantidades, fuente, rutas de artefactos y duración.

Los intentos de navegación rechazados durante el bloqueo también se registrarán con operación, selector o destino y contexto del bloqueo.

## 18. Plan de pruebas

### 18.1. Fixtures

Crear fixtures sanitizados derivados de los artefactos reales:

```text
tests/fixtures/esatje/movimientos_cargando.html
tests/fixtures/esatje/movimientos_una_carpeta.html
tests/fixtures/esatje/movimientos_varias_carpetas.html
tests/fixtures/esatje/actuaciones_con_adjuntos.html
tests/fixtures/esatje/actuaciones_sin_adjuntos.html
tests/fixtures/esatje/actuaciones_vacia_confirmada.html
```

No guardar datos personales innecesarios en las fixtures; conservar solo la estructura relevante.

### 18.2. Resultados y `/movimientos`

1. La URL cambia a `/movimientos`, pero `Buscando...` sigue visible: cero clics y cero descubrimientos.
2. Al desaparecer la carga y estabilizarse la firma: descubrir todos los incidentes.
3. Validar dependencia padre y fila hija por separado.
4. Varias dependencias y varios incidentes: una carpeta por enlace hijo, sin ambigüedad global.
5. Angular reconstruye el DOM: relocalización por clave, no por locator antiguo.
6. Dos claves iguales: error antes del clic.
7. Cero carpetas: `CARPETA_PROCESAL_AUSENTE`.
8. La rama `/causas` se detiene en `/movimientos` y no hace el segundo clic prematuro.

### 18.3. Freno de navegación

1. `/actuaciones` válida activa el bloqueo antes de extraer.
2. Cada wrapper rechaza clic, `go_back()` y `goto()` mientras está bloqueado.
3. La prueba mantiene un registro global de intentos y confirma cero navegaciones exitosas.
4. Ningún `Ver archivos` recibe clic.
5. Ningún clic por `page.evaluate()` existe en la ruta de extracción.
6. `_ejecutar_extraccion_detalles()` se invoca exactamente una vez por clave y por intento.
7. Un timeout sin manifiesto durable no libera el bloqueo ni retorna.
8. Un error correctamente guardado libera el bloqueo y permite el retorno controlado.

### 18.4. Estabilidad y API

1. Encabezado presente pero filas cambiando: no extraer.
2. Firma estable pero API aún activa: no extraer.
3. API quieta y firma estable: extraer.
4. Cero `Ver archivos`: la pantalla puede ser válida.
5. Paquete de otra causa dentro de la lista global: descartarlo.
6. Paquete dentro de la ventana sin identidad y sin conflicto: aceptarlo con advertencia.
7. Paquete dudoso: guardarlo, pero no usarlo como fuente primaria.
8. Ruta API exitosa: también se guardan HTML, screenshot y manifiesto.

### 18.5. Extracción, error y retorno

1. Extracción completa: manifiesto, desbloqueo y un retorno.
2. Inferencia fallida con actuaciones: resultado parcial conservado.
3. Error total con evidencia guardada: `ERROR_REGISTRADO`, desbloqueo y retorno.
4. Error al guardar evidencia: detenerse sin navegar.
5. Retorno por botón exitoso: no ejecutar `go_back()`.
6. Botón ausente: un único `go_back()` y validación estricta.
7. Fallo de retorno: no procesar otra carpeta ni causa.
8. Final del ciclo: no existe un segundo retorno a Datos generales.

### 18.6. Consolidación y persistencia

1. Varias carpetas conservan origen por actuación.
2. Duplicados iguales en carpetas diferentes no pierden el origen.
3. Todas completas: `COMPLETADO` y SQLite `PROCESADO`.
4. Alguna parcial/error con evidencia útil: `PARCIAL` y SQLite `PARCIAL`.
5. Todas fallidas: `EXTRACCION_ERROR` y SQLite `ERROR`.
6. Fallo de `repo.guardar()` o SQLite: `PERSISTENCIA_ERROR`, lote detenido.
7. `main.py` no comienza otra causa hasta confirmar la persistencia de la actual.

### 18.7. Logging

1. Importar módulos durante pruebas no crea ni modifica `ejecucion_produccion.log`.
2. Ejecutar pytest no cambia tamaño ni fecha del log de producción.
3. Producción crea el handler una sola vez.
4. Diagnóstico escribe en un destino distinto.

### 18.8. Regresión

Ejecutar toda la suite existente, incluyendo clasificación, fechas derivadas, API, migración y extracción. No corregir fallos ajenos ocultándolos o debilitando aserciones.

## 19. Criterios de aceptación del parche

La implementación estará completa únicamente cuando:

1. La apertura del resultado termina en `/movimientos`; no salta automáticamente a `/actuaciones`.
2. No se buscan carpetas mientras exista una señal visible de carga.
3. Las carpetas se descubren en `.lista-movimientos-causa`, distinguiendo dependencia e incidente.
4. Se procesan una o varias carpetas sin selector global `.first`; cero carpetas produce error explícito.
5. `Ver archivos` nunca participa en el descubrimiento ni recibe clic.
6. La llegada validada a `/actuaciones` activa el bloqueo antes de extraer.
7. Toda navegación pasa por el guard central.
8. La extracción no contiene clics ni navegación directa o por JavaScript.
9. La estabilidad no depende de que existan adjuntos.
10. La ventana API queda delimitada y auditable por carpeta.
11. Cada carpeta se extrae exactamente una vez por intento.
12. API y DOM generan artefactos con nombres no colisionantes.
13. El bloqueo solo se libera con resultado durable.
14. Cada carpeta realiza como máximo un retorno confirmado a `/movimientos`.
15. No existe retorno duplicado al finalizar el ciclo.
16. Todas las actuaciones conservan su carpeta, dependencia, ciudad e incidente de origen.
17. `COMPLETADO`, `PARCIAL`, `SIN_RESULTADOS` y errores se persisten con estados distintos.
18. Un fallo de persistencia detiene el avance del lote.
19. Las pruebas no escriben en el log de producción.
20. La suite completa, el piloto de una carpeta y el piloto de varias carpetas finalizan satisfactoriamente.

## 20. Orden de implementación

1. Crear fixtures sanitizadas y pruebas que reproduzcan el fallo actual.
2. Separar configuración de logging y verificar que las pruebas no toquen producción.
3. Crear constantes/enum de estados y validación de transiciones.
4. Implementar la puerta central y pruebas del bloqueo.
5. Dividir `_abrir_movimientos_causa()` de la apertura de carpeta.
6. Implementar detectores puros y `_esperar_movimientos_listos()`.
7. Implementar descriptores por dependencia/incidente y relocalización.
8. Enriquecer el listener API y crear ventanas por carpeta.
9. Implementar la estabilidad de `/actuaciones` sin depender de adjuntos.
10. Convertir `_ejecutar_extraccion_detalles()` en una transformación sin clics.
11. Implementar `_extraer_informacion_proceso()` y artefactos atómicos.
12. Corregir retorno único y política de reintentos.
13. Consolidar carpetas e inferir la causa.
14. Cambiar el contrato público y actualizar `main.py` y scripts.
15. Adaptar `GestorCola` para estados finales reales.
16. Ejecutar pruebas unitarias, integración, regresión y `git diff --check`.
17. Ejecutar un piloto visible de una causa con una carpeta.
18. Ejecutar un piloto visible de una causa con varias carpetas.
19. Revisar artefactos, log y SQLite del piloto.
20. Autorizar un lote pequeño; solo después considerar reanudar el procesamiento masivo.

## 21. Puerta de salida hacia producción

Antes del primer piloto:

- conservar y no sobrescribir cambios de usuario ya presentes en el repositorio;
- confirmar que no existe otra ejecución de `main.py` usando los mismos archivos;
- usar una copia o base de datos de piloto;
- usar un CSV de piloto o respaldo verificable;
- usar un log exclusivo del piloto.

Antes del lote masivo:

- revisar manualmente al menos un manifiesto completo y uno parcial/error;
- comprobar que el número de manifiestos coincide con las carpetas procesadas;
- confirmar que no hay eventos de navegación entre `NAVEGACION_BLOQUEADA` y el evento terminal de extracción;
- confirmar que SQLite y el CSV representan el mismo estado de causa;
- documentar cualquier selector ajustado durante el piloto.

## 22. Decisiones explícitamente prohibidas

- No resolver el problema agregando más `.first`.
- No usar sleeps fijos como sustituto de condiciones de estabilidad.
- No considerar **Datos generales** una señal exclusiva.
- No exigir adjuntos para declarar estable una carpeta.
- No capturar una excepción y continuar si no se guardó evidencia.
- No liberar el bloqueo incondicionalmente desde `finally`.
- No reiniciar toda la causa después de haber persistido una carpeta dentro del mismo intento.
- No marcar `PARCIAL` como `PROCESADO`.
- No ejecutar pruebas contra `ejecucion_produccion.log`.
- No incluir `AgenteExplorador` en este parche sin ampliar explícitamente el alcance y sus pruebas.

Con estas decisiones, la siguiente fase de implementación tiene responsabilidades, transiciones, contratos, errores, pruebas y límites definidos sin depender de interpretación adicional.
