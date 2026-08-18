# Plan de implementación: automatización de botones en e-SATJE

## 1. Objetivo

Convertir el flujo asistido actual en un flujo automático después de que el CAPTCHA haya terminado o se haya cerrado.

Para cada número de causa, el bot deberá:

1. Escribir y verificar el número de causa.
2. Esperar pasivamente a que finalice el CAPTCHA y el botón **BUSCAR** quede habilitado.
3. Hacer exactamente un clic en **BUSCAR**.
4. Esperar y validar los resultados.
5. Abrir la carpeta **Detalle** de la fila que corresponda a la causa solicitada.
6. Esperar y validar la pantalla **Datos generales**.
7. Abrir cada carpeta de **Actuaciones Judiciales** disponible.
8. Extraer y consolidar las actuaciones de todas las carpetas.
9. Cerrar o regresar automáticamente hasta el buscador para continuar con la siguiente causa.

El CAPTCHA no será resuelto por el bot. La automatización debe esperar a que el reto termine por sí solo o sea resuelto por el operador y, desde ese momento, continuar sin clics manuales.

## 2. Referencias visuales verificadas

| Captura | Estado de la interfaz | Control que debe pulsar el bot | Condición previa |
| --- | --- | --- | --- |
| `Captura de pantalla 2026-08-06 200811.png` | Formulario de búsqueda | Botón **BUSCAR** | CAPTCHA cerrado, botón visible y habilitado, causa todavía escrita. |
| `Captura de pantalla 2026-08-06 200842.png` | Tabla de resultados | Carpeta de la columna **Detalle** | La fila contiene la misma causa solicitada. |
| `Captura de pantalla 2026-08-06 200930.png` | Pantalla **Datos generales** | Carpeta de la columna **Actuaciones Judiciales** | El número mostrado en **Número de proceso** coincide con la causa. |

Las carpetas de las capturas 2 y 3 no son el mismo control:

- La primera abre los datos generales de la causa desde la tabla de resultados.
- La segunda abre las actuaciones de una dependencia o instancia dentro de la causa.

El código debe reconocer y validar cada pantalla antes de intentar el siguiente clic.

## 3. Diagnóstico del flujo actual

El proyecto ya cuenta con:

- llenado del número de causa;
- navegador visible con Playwright;
- escucha de respuestas JSON;
- extracción por API y respaldo DOM;
- intentos parciales de abrir carpetas;
- recuperación básica ante cierre del navegador.

Sin embargo, todavía existen los siguientes puntos de intervención o riesgo:

1. `BotJudicial.procesar_flujo_judicatura()` llena la causa y solicita al operador resolver el CAPTCHA, buscar y navegar manualmente.
2. El clic actual de carpeta usa selectores globales y `.first`, por lo que puede abrir un control que no pertenece a la causa solicitada.
3. El flujo pasa directamente de “buscador” a esperar **Información del proceso**, sin modelar por separado la tabla de resultados y la pantalla **Datos generales**.
4. Después de extraer, el sistema espera que el operador cierre el expediente.
5. `AgenteExplorador.descargar_html_juicio()` puede presionar `Enter` cuando **BUSCAR** está deshabilitado. Esto no debe ocurrir durante el CAPTCHA.
6. Las respuestas API capturadas durante búsqueda, datos generales y actuaciones pueden mezclarse si no se delimitan por transición o carpeta.
7. No existe una garantía de “un solo clic” en **BUSCAR** ante timeouts o reintentos.

## 4. Principios obligatorios de implementación

1. No resolver ni eludir el CAPTCHA.
2. No pulsar **BUSCAR** mientras esté deshabilitado.
3. No usar `Enter` como reemplazo cuando **BUSCAR** esté deshabilitado.
4. Hacer un solo clic de búsqueda por intento transaccional.
5. No utilizar coordenadas de pantalla.
6. No usar `.first` sobre botones o carpetas globales.
7. Localizar cada botón de carpeta dentro de la fila validada.
8. Esperar cambios verificables del DOM o respuestas de red; las pausas fijas solo podrán usarse como estabilización breve, nunca como condición principal.
9. No continuar si el número de causa de la pantalla actual no coincide con el solicitado.
10. No dar una causa por completada si alguna carpeta requerida no fue procesada, salvo que quede registrada expresamente como resultado parcial.

## 5. Máquina de estados propuesta

```text
PREPARAR_BUSCADOR
  -> CAUSA_ESCRITA
  -> ESPERAR_FIN_CAPTCHA
  -> BUSQUEDA_HABILITADA
  -> BUSQUEDA_ENVIADA
  -> RESULTADOS_LISTOS | SIN_RESULTADOS | CAPTCHA_TIMEOUT
  -> DETALLE_CAUSA_ABIERTO
  -> DATOS_GENERALES_LISTOS
  -> DESCUBRIR_CARPETAS_ACTUACIONES
  -> ABRIR_CARPETA[n]
  -> ACTUACIONES_LISTAS[n]
  -> EXTRAER_CARPETA[n]
  -> VOLVER_A_DATOS_GENERALES
  -> CONSOLIDAR_EVIDENCIA
  -> VOLVER_AL_BUSCADOR
  -> CAUSA_COMPLETADA | CAUSA_PARCIAL | CAUSA_ERROR
```

Cada transición deberá declarar:

- condición de entrada;
- acción permitida;
- señal de éxito;
- timeout configurable;
- cantidad máxima de reintentos;
- evidencia registrada;
- estado de error específico.

## 6. Nivel 1: espera del CAPTCHA y clic en BUSCAR

### 6.1. Preparación de la causa

1. Regresar al formulario de búsqueda si la página se encuentra en otro nivel.
2. Localizar el campo por `formcontrolname`, etiqueta o placeholder.
3. Limpiarlo y escribir la causa.
4. Disparar los eventos necesarios para que Angular actualice el formulario.
5. Volver a leer el valor del campo y comprobar que coincide con la causa solicitada.

La comparación debe utilizar una versión canónica del número:

```python
causa_canonica = solo_digitos(numero_juicio)
```

Esto es necesario porque el archivo de origen puede contener `23331-2022-02089`, mientras el portal muestra `23331202202089`.

### 6.2. Espera pasiva del CAPTCHA

Crear una función dedicada, por ejemplo:

```python
_esperar_busqueda_habilitada(numero_juicio)
```

La función deberá esperar simultáneamente que:

- el formulario siga visible;
- el valor canónico del campo siga siendo la causa solicitada;
- no exista un diálogo, iframe, backdrop o contenedor de CAPTCHA visible, cuando el portal exponga uno identificable;
- el botón **BUSCAR** esté visible;
- el botón no tenga `disabled`;
- `aria-disabled` no sea `true`;
- el estado habilitado permanezca estable durante una comprobación breve consecutiva.

La desaparición visual del CAPTCHA y el estado habilitado del botón deben ser las señales de avance. No se debe usar un `sleep` fijo suponiendo que el CAPTCHA ya terminó.

El timeout será configurable. Se recomienda conservar inicialmente un máximo de cinco minutos, compatible con el tiempo de intervención actual.

Si el timeout vence:

- no pulsar **BUSCAR**;
- registrar `CAPTCHA_TIMEOUT`;
- guardar captura de pantalla y HTML;
- dejar la causa pendiente de reintento o revisión, según la política de cola.

### 6.3. Clic único e idempotente

Localizar el botón prioritariamente por rol y nombre accesible exacto:

```python
page.get_by_role("button", name=re.compile(r"^BUSCAR$", re.IGNORECASE))
```

Usar selectores CSS como respaldo, no como primera opción.

Antes del clic:

1. Verificar nuevamente la causa escrita.
2. Verificar que el botón esté visible y habilitado.
3. Armar la espera de respuesta o de cambio de pantalla.
4. Marcar la transacción como `busqueda_enviada`.
5. Ejecutar un único `click()`.

Después del clic, si hay timeout, inspeccionar primero si ya apareció:

- la tabla de resultados;
- el contador **Registros encontrados**;
- el mensaje de cero resultados;
- una respuesta API válida;
- un error del portal.

No hacer un segundo clic automáticamente sobre la misma pantalla. Para reintentar será necesario reiniciar de forma explícita toda la transacción de la causa y asignarle un nuevo identificador de intento.

## 7. Nivel 2: tabla de resultados y carpeta Detalle

Crear funciones separadas:

```python
_esperar_resultados(numero_juicio)
_abrir_detalle_causa(numero_juicio)
```

### 7.1. Validación de resultados

La pantalla de resultados debe validarse mediante varias señales:

- encabezado o sección **Filtros de búsqueda**;
- texto **Número de causa**;
- contador **Registros encontrados**;
- tabla con las columnas **No.**, **Fecha de ingreso**, **No. proceso**, **Acción/Infracción** y **Detalle**.

Si el portal indica cero resultados, devolver `SIN_RESULTADOS` sin buscar carpetas.

### 7.2. Selección determinista de la fila

1. Recorrer únicamente las filas de la tabla de resultados.
2. Obtener el texto de la columna **No. proceso**.
3. Canonicalizarlo a solo dígitos.
4. Compararlo con la causa solicitada.
5. Exigir una única coincidencia.

Si no hay coincidencia, registrar `CAUSA_NO_ENCONTRADA_EN_TABLA`.

Si hay más de una coincidencia exacta, registrar `RESULTADO_AMBIGUO` y no abrir una fila arbitraria.

### 7.3. Clic en la carpeta correcta

Dentro de la fila validada:

1. Localizar la celda asociada a la columna **Detalle**.
2. Buscar el elemento accionable `button` o `a` que contiene el icono de carpeta.
3. Hacer scroll si es necesario.
4. Comprobar visibilidad y habilitación.
5. Pulsar el elemento accionable, no el icono interno si este no recibe eventos.

El uso de `force=True` quedará como último recurso documentado y nunca reemplazará la validación de la fila.

### 7.4. Señal de éxito

No se considerará abierto el detalle hasta comprobar:

- encabezado **Datos generales**;
- campo **Número de proceso**;
- número canónico coincidente;
- tabla o sección con **Actuaciones Judiciales**.

Esta pantalla constituye un estado intermedio independiente. No debe confundirse con la vista interna que aparece después de abrir la carpeta de actuaciones.

## 8. Nivel 3: carpetas de Actuaciones Judiciales

Crear funciones especializadas:

```python
_descubrir_carpetas_actuaciones(numero_juicio)
_abrir_carpeta_actuaciones(descriptor)
_esperar_actuaciones(descriptor)
_extraer_carpeta_actuaciones(descriptor)
_volver_a_datos_generales(numero_juicio)
```

### 8.1. Descubrimiento

Recorrer las filas o tarjetas bajo la cabecera **Actuaciones Judiciales** y construir un descriptor por carpeta con:

- índice visual inicial;
- número o identificador de instancia;
- dependencia jurisdiccional;
- ciudad;
- fecha;
- actores y demandados;
- texto normalizado de la fila;
- clave estable derivada de ese contexto.

No conservar un `Locator` para reutilizarlo después de una navegación, porque Angular puede reconstruir el DOM y dejarlo obsoleto. Antes de cada clic se deberá volver a localizar la fila usando su descriptor.

### 8.2. Recorrido de todas las carpetas

Para cada descriptor pendiente:

1. Confirmar que se mantiene la pantalla **Datos generales** de la causa correcta.
2. Volver a localizar la fila por su clave estable.
3. Localizar el botón o enlace de carpeta dentro de esa fila.
4. Registrar el cursor o instante inicial de captura API.
5. Hacer un clic.
6. Esperar la vista interna de actuaciones.
7. Extraer datos por API y, si no son suficientes, por DOM.
8. Guardar el origen de la carpeta en cada actuación.
9. Cerrar la vista interna o regresar automáticamente a **Datos generales**.
10. Confirmar nuevamente la causa y continuar con la siguiente carpeta.

Una carpeta no deberá procesarse dos veces. Si una carpeta falla después de sus reintentos, se registrará el resultado como parcial y se continuará con las demás cuando sea seguro hacerlo.

### 8.3. Señal de apertura de actuaciones

La apertura deberá confirmarse con señales que pertenezcan a la vista interna, por ejemplo:

- **Información del proceso**;
- **Exportar PDF**;
- **Ampliar todo** o **Contraer todo**;
- tabla, árbol o elementos concretos de actuaciones;
- respuesta JSON de `actuacionesJudiciales` correspondiente a la causa.

No basta con encontrar el encabezado **Actuaciones Judiciales** de la pantalla **Datos generales**, porque ese texto ya existe antes del clic.

### 8.4. Retorno automático

Después de extraer una carpeta, el bot deberá identificar y utilizar el control real de cierre o retorno de la vista interna. El orden de respaldo será:

1. Botón accesible **Cerrar**, `X` o equivalente del contenedor abierto.
2. Botón **Regresar** cuando su destino sea **Datos generales**.
3. Historial del navegador únicamente si se comprobó que la apertura produjo navegación real.

No se debe esperar a que el operador cierre el expediente. El éxito del retorno se confirma cuando reaparecen **Datos generales**, el número correcto y la lista de carpetas.

Al terminar todas las carpetas se utilizará el control **Regresar** necesario para volver al formulario de búsqueda y se verificará que el campo de causa vuelva a estar visible.

## 9. Captura API y respaldo DOM por carpeta

La lista global de respuestas interceptadas debe segmentarse por causa y carpeta.

Antes de abrir una carpeta:

- registrar un cursor de captura, timestamp o identificador de transición;
- limpiar únicamente el segmento correspondiente cuando sea seguro;
- conservar las respuestas anteriores ya asociadas.

Después del clic:

- aceptar solamente respuestas posteriores al cursor;
- priorizar endpoints relacionados con actuaciones;
- verificar `idJuicio` o número de causa cuando esté presente;
- asociar cada paquete JSON con la clave de carpeta;
- descartar de la inferencia paquetes de búsqueda, catálogos o causas distintas.

Si la API no contiene actuaciones utilizables, capturar el DOM de esa misma carpeta. Los artefactos deben nombrarse con causa y clave de carpeta para evitar sobrescrituras.

Ejemplo:

```text
data/temp_htmls/23331-2022-04191_carpeta_01.html
data/temp_htmls/23331-2022-04191_carpeta_01_api.json
```

## 10. Consolidación de actuaciones

Cada actuación consolidada deberá conservar, además de fecha y detalle:

- causa;
- clave de carpeta;
- dependencia;
- ciudad;
- instancia o número de fila;
- origen `api` o `dom`;
- identificador del registro cuando exista.

La deduplicación debe utilizar identificadores del portal cuando estén disponibles. Como respaldo, podrá usarse una clave compuesta normalizada de fecha, detalle, dependencia e instancia.

La inferencia procesal se ejecutará una sola vez después de consolidar todas las carpetas, permitiendo que el motor seleccione correctamente la rama o instancia activa.

## 11. Funciones y responsabilidades propuestas

### `src/motor_busqueda_web.py`

Responsable de orquestar la máquina de estados:

```python
_preparar_busqueda(numero_juicio)
_esperar_busqueda_habilitada(numero_juicio)
_enviar_busqueda_una_vez(numero_juicio, intento_id)
_esperar_resultados(numero_juicio)
_abrir_detalle_causa(numero_juicio)
_esperar_datos_generales(numero_juicio)
_procesar_todas_las_carpetas(numero_juicio)
_volver_al_buscador(numero_juicio)
```

### `src/agente_explorador.py`

Responsable de:

- selectores semánticos y relativos a filas;
- descubrimiento de carpetas;
- apertura y retorno de vistas;
- correlación de respuestas API con causa y carpeta;
- respaldo DOM localizado.

Debe eliminarse el comportamiento que presiona `Enter` cuando **BUSCAR** está deshabilitado.

### `src/agente_extractor.py`

Responsable de:

- normalizar las actuaciones obtenidas por cada carpeta;
- preservar metadatos de dependencia e instancia;
- consolidar sin perder el origen.

### `config.json`

Agregar parámetros configurables, por ejemplo:

```json
{
  "navegacion": {
    "captcha_timeout_ms": 300000,
    "resultados_timeout_ms": 30000,
    "datos_generales_timeout_ms": 30000,
    "actuaciones_timeout_ms": 30000,
    "max_reintentos_transicion": 2
  }
}
```

Los valores definitivos deberán ajustarse después de medir el portal real.

## 12. Estados de salida y manejo de errores

| Estado | Significado | Acción |
| --- | --- | --- |
| `COMPLETADO` | Todas las carpetas fueron extraídas y consolidadas. | Guardar e ir a la siguiente causa. |
| `SIN_RESULTADOS` | El portal confirmó cero resultados. | Registrar conforme a la regla de negocio existente. |
| `CAPTCHA_TIMEOUT` | El CAPTCHA no terminó dentro del límite. | No hacer clic; dejar para reintento o revisión. |
| `RESULTADO_AMBIGUO` | Más de una fila coincide exactamente. | No abrir una fila arbitraria. |
| `DETALLE_INCONSISTENTE` | El número de proceso abierto no coincide. | Guardar evidencia y regresar. |
| `PARCIAL` | Al menos una carpeta falló, pero otras fueron extraídas. | Conservar evidencia y marcar revisión. |
| `ERROR_NAVEGACION` | No se confirmó una transición. | Reintentar de forma limitada desde un estado conocido. |
| `SESION_EXPIRADA` | El portal perdió la sesión. | Reiniciar sesión y reencolar la causa. |

Cada fallo deberá guardar:

- captura de pantalla;
- HTML;
- URL;
- estado de la máquina;
- selector intentado;
- causa y carpeta;
- último paquete API relacionado;
- excepción completa.

## 13. Trazabilidad

Añadir eventos estructurados `NAVEGACION_ESATJE` con un formato similar a:

```json
{
  "causa": "23331202202089",
  "intento_id": "...",
  "estado_anterior": "BUSQUEDA_HABILITADA",
  "estado_siguiente": "BUSQUEDA_ENVIADA",
  "accion": "click_buscar",
  "click_numero": 1,
  "selector": "role=button[name=BUSCAR]",
  "duracion_ms": 842,
  "resultado": "ok"
}
```

Para las carpetas, incluir además:

- clave de carpeta;
- dependencia;
- número de actuaciones API;
- número de actuaciones DOM;
- resultado de retorno a **Datos generales**.

## 14. Estrategia de selectores

Orden recomendado:

1. Rol y nombre accesible.
2. Etiqueta o encabezado de columna y relación con su fila.
3. Atributos estables de Angular, `formcontrolname` o atributos funcionales.
4. Botón o enlace que contenga un icono de carpeta dentro de una fila ya validada.
5. XPath relativo como último respaldo.

Evitar:

- coordenadas;
- clases visuales generadas por Angular como selector único;
- `nth()` o índices globales sin validar el contenido de la fila;
- texto parcial que pueda coincidir con encabezados y controles distintos;
- `force=True` como comportamiento normal.

## 15. Plan de pruebas

### 15.1. Pruebas unitarias de estados

1. **BUSCAR deshabilitado:** el bot espera y no hace clic ni presiona `Enter`.
2. **CAPTCHA cerrado:** al habilitarse el botón se ejecuta un solo clic.
3. **Timeout de CAPTCHA:** no se produce ningún envío.
4. **Timeout después del clic:** no se genera un segundo clic automático.
5. **Causa con guiones:** coincide con el número sin guiones mostrado por el portal.

### 15.2. Pruebas de la tabla de resultados

1. Una fila correcta: abre su carpeta.
2. La primera fila es incorrecta y la segunda correcta: abre solamente la segunda.
3. Cero resultados: devuelve `SIN_RESULTADOS`.
4. Más de una coincidencia exacta: devuelve `RESULTADO_AMBIGUO`.
5. Carpeta no accionable: registra el fallo sin pulsar otro botón global.

### 15.3. Pruebas de Datos generales

1. El número de proceso coincide: continúa.
2. El número no coincide: detiene la extracción.
3. Una carpeta de actuaciones: abre, extrae y regresa.
4. Varias carpetas: procesa cada una exactamente una vez.
5. Angular reconstruye el DOM: vuelve a localizar la siguiente fila sin usar un locator obsoleto.
6. Una carpeta falla: procesa las demás y devuelve `PARCIAL`.

### 15.4. Pruebas de API y DOM

1. Respuesta API de actuaciones válida y correlacionada con la causa.
2. Paquete de búsqueda no se interpreta como actuación.
3. Paquete perteneciente a otra causa se descarta.
4. API vacía activa respaldo DOM de la misma carpeta.
5. Consolidación elimina duplicados sin mezclar instancias.

### 15.5. Prueba visible de extremo a extremo

Ejecutar en navegador visible una causa controlada y comprobar en video o log:

1. El operador resuelve o espera el CAPTCHA.
2. El bot detecta su cierre.
3. El bot hace un clic en **BUSCAR**.
4. Abre la carpeta **Detalle** correcta.
5. Abre todas las carpetas de **Actuaciones Judiciales**.
6. Regresa automáticamente al buscador.
7. Guarda un único resultado consolidado.

## 16. Plan de ejecución

1. Guardar fixtures anonimizados de las tres pantallas y de la vista interna de actuaciones.
2. Inspeccionar el DOM real para identificar el contenedor del CAPTCHA, los botones accionables y el control de cierre de actuaciones.
3. Crear las pruebas de máquina de estados y clic único.
4. Extraer del flujo principal las funciones de navegación indicadas.
5. Implementar la espera de CAPTCHA y eliminar el respaldo por `Enter` cuando el botón esté deshabilitado.
6. Implementar el clic único en **BUSCAR** y la validación de resultados.
7. Implementar la selección de fila por causa canónica y la carpeta **Detalle** relativa.
8. Implementar el estado **Datos generales** y el recorrido de todas las carpetas.
9. Implementar el cierre o retorno automático después de cada carpeta.
10. Segmentar la captura API y los artefactos por carpeta.
11. Consolidar actuaciones y ejecutar la inferencia al final del recorrido.
12. Ejecutar pruebas unitarias e integración local.
13. Realizar una prueba visible con una causa y luego un lote pequeño.
14. Activar el procesamiento masivo solamente después de revisar logs, duplicados y estados parciales.

## 17. Despliegue gradual

1. **Prueba individual:** una causa con una carpeta.
2. **Prueba de estructura:** una causa con varias carpetas o instancias.
3. **Lote piloto:** entre 5 y 10 causas conocidas.
4. **Lote controlado:** todas las causas pendientes de una sola sesión.
5. **Producción:** procesamiento masivo con métricas de timeout, errores, causas parciales y clics por transición.

La métrica `click_buscar_por_intento` debe ser siempre `0` cuando vence el CAPTCHA y `1` cuando la búsqueda fue enviada.

## 18. Criterios de aceptación

La implementación estará terminada cuando:

1. El bot espere el cierre del CAPTCHA sin intentar resolverlo ni eludirlo.
2. **BUSCAR** se pulse exactamente una vez después de quedar habilitado.
3. Nunca se presione `Enter` mientras el botón esté deshabilitado.
4. Se abra exclusivamente la fila que coincide con la causa solicitada.
5. Se valide la pantalla **Datos generales** antes de abrir actuaciones.
6. Se abran todas las carpetas de **Actuaciones Judiciales** una sola vez.
7. El bot cierre o regrese automáticamente después de cada extracción.
8. Las actuaciones mantengan su dependencia e instancia de origen.
9. Los paquetes API de distintas pantallas o causas no se mezclen.
10. La inferencia y el guardado final no necesiten clics del operador después del CAPTCHA.
11. Los errores y resultados parciales queden registrados con evidencia reproducible.
12. Todas las pruebas existentes y las nuevas pruebas de navegación sean satisfactorias.

## 19. Archivos previstos

| Archivo | Cambio |
| --- | --- |
| `src/motor_busqueda_web.py` | Máquina de estados, espera del CAPTCHA, clic único, orquestación y retorno automático. |
| `src/agente_explorador.py` | Selectores relativos, carpetas, correlación API y eliminación del `Enter` inseguro. |
| `src/agente_extractor.py` | Metadatos y consolidación de actuaciones por carpeta o instancia. |
| `config.json` | Timeouts y reintentos configurables. |
| `main.py` | Tratamiento de estados completos, parciales, sin resultados y timeout de CAPTCHA. |
| `tests/test_navegacion_esatje.py` | Pruebas nuevas de estados, CAPTCHA y botones. |
| `tests/test_extraccion_integration.py` | Integración API/DOM y consolidación. |
| `data/temp_htmls/` | Fixtures HTML/JSON anonimizados por pantalla y carpeta. |

## 20. Fuera de alcance

- Resolver automáticamente el CAPTCHA.
- Eludir controles WAF o mecanismos anti-bot.
- Cambiar las reglas de inferencia procesal.
- Usar reconocimiento visual o coordenadas como método principal de clic.

El alcance comienza cuando el CAPTCHA finaliza y comprende todos los clics y retornos necesarios hasta dejar lista la siguiente causa.
