# Plan de implementación: freno de navegación en Información del proceso

## 1. Objetivo

Corregir el flujo automático de e-SATJE para que la navegación se detenga completamente al llegar a la pantalla **Información del proceso**.

En esa pantalla, el sistema deberá:

1. Confirmar que pertenece a la causa y carpeta procesal esperadas.
2. Suspender todos los clics de navegación.
3. Esperar a que la pantalla y sus actuaciones terminen de cargar.
4. Ejecutar la captura API y DOM.
5. Extraer, consolidar e inferir fase, etapa y fecha.
6. Guardar los datos y artefactos.
7. Emitir una señal explícita `EXTRACCION_COMPLETA`.
8. Recién entonces reanudar la navegación para regresar a **Datos generales**, procesar otra carpeta procesal o continuar con la siguiente causa.

## 2. Resultado funcional esperado

```text
BUSCADOR
  -> BUSCAR
  -> RESULTADOS
  -> carpeta Detalle
  -> /movimientos: Datos generales
  -> carpeta Actuaciones Judiciales
  -> /actuaciones: Información del proceso
  -> NAVEGACIÓN BLOQUEADA
  -> RECOLECCIÓN API/DOM
  -> INFERENCIA
  -> PERSISTENCIA
  -> EXTRACCION_COMPLETA
  -> NAVEGACIÓN REANUDADA
  -> regresar a /movimientos o al buscador
```

La pantalla **Información del proceso** será el límite exacto entre el módulo de navegación y el módulo de extracción.

## 3. Problemas que se deben corregir

### 3.1. Carrera de renderizado en `/movimientos`

Después de abrir el resultado, el código espera el cambio de URL a `/movimientos`, pero busca inmediatamente la carpeta siguiente. La evidencia muestra que el portal todavía puede presentar el overlay **Buscando...** y no haber renderizado las filas.

Se deberá esperar que:

- desaparezca el indicador de carga;
- aparezcan las filas de dependencias o instancias;
- el número de proceso coincida con la causa;
- exista al menos una carpeta procesal visible y accionable.

### 3.2. Confusión entre carpetas procesales y archivos adjuntos

Las carpetas de la pantalla `/movimientos` representan dependencias o instancias que conducen a **Información del proceso**.

Los botones `Ver archivos` de `/actuaciones` representan adjuntos individuales. No deben tratarse como carpetas procesales ni pulsarse durante la extracción normal.

### 3.3. Freno insuficiente

Detectar el texto **Información del proceso** actualmente funciona solo como una señal de pantalla lista. Después de esa detección todavía se ejecuta un recorrido automático de botones.

La llegada a esa pantalla debe activar un estado bloqueante donde ninguna función de navegación pueda hacer clic hasta que termine la extracción.

### 3.4. Señales de pantalla no exclusivas

El texto **Datos generales** también aparece dentro de `/actuaciones`. Por lo tanto, no permite distinguir por sí solo entre:

- `/movimientos`: lista de carpetas procesales;
- `/actuaciones`: información y actuaciones del proceso.

Las validaciones deberán combinar URL, encabezados, controles exclusivos y número de causa.

### 3.5. Pruebas y producción comparten el mismo log

Las pruebas automatizadas escriben eventos sintéticos en `ejecucion_produccion.log`, lo que mezcla evidencia real con datos de prueba.

Se deberán separar los destinos de logging para obtener un diagnóstico confiable.

## 4. Nueva máquina de estados

Implementar los siguientes estados explícitos:

```text
PREPARAR_BUSCADOR
CAUSA_ESCRITA
ESPERAR_FIN_CAPTCHA
BUSQUEDA_HABILITADA
BUSQUEDA_ENVIADA
RESULTADOS_LISTOS
ABRIENDO_DETALLE
MOVIMIENTOS_CARGANDO
DATOS_GENERALES_LISTOS
CARPETAS_PROCESALES_DESCUBIERTAS
ABRIENDO_INFORMACION_PROCESO
INFORMACION_PROCESO_CARGANDO
INFORMACION_PROCESO_LISTA
NAVEGACION_BLOQUEADA
EXTRACCION_EN_PROGRESO
INFERENCIA_EN_PROGRESO
PERSISTENCIA_EN_PROGRESO
EXTRACCION_COMPLETA
NAVEGACION_REANUDADA
VOLVER_A_DATOS_GENERALES
VOLVER_AL_BUSCADOR
CAUSA_COMPLETADA
```

Estados de error relevantes:

```text
MOVIMIENTOS_TIMEOUT
CARPETA_PROCESAL_AUSENTE
CARPETA_PROCESAL_AMBIGUA
INFORMACION_PROCESO_TIMEOUT
CAUSA_INCONSISTENTE
EXTRACCION_ERROR
PERSISTENCIA_ERROR
RETORNO_ERROR
CAUSA_PARCIAL
```

## 5. Separar claramente las tres pantallas

### 5.1. Resultados de búsqueda

Condiciones mínimas:

- URL o vista correspondiente a resultados;
- causa solicitada en una única fila;
- carpeta **Detalle** localizada dentro de esa fila.

Acción permitida:

- hacer clic únicamente en la carpeta **Detalle** de la fila validada.

### 5.2. Datos generales y movimientos

Condiciones mínimas:

- URL `/movimientos`;
- ausencia del overlay **Buscando...**;
- encabezado **Datos generales**;
- número de proceso coincidente;
- cabecera **Actuaciones Judiciales**;
- filas de dependencias completamente renderizadas.

Acciones permitidas:

- descubrir las carpetas procesales;
- hacer clic en una carpeta procesal pendiente.

### 5.3. Información del proceso

Condiciones mínimas:

- URL `/actuaciones`;
- encabezado **Información del proceso**;
- número de proceso coincidente;
- controles como **Exportar PDF**, **Ampliar todo** o **Contraer todo**;
- tabla o árbol de actuaciones renderizado y estable.

Acciones permitidas:

- lectura de DOM;
- captura de paquetes API;
- extracción e inferencia;
- guardado de evidencia.

Acciones prohibidas mientras la extracción no termine:

- pulsar `Ver archivos`;
- pulsar `Regresar`;
- usar `go_back()`;
- abrir otra carpeta;
- iniciar otra causa.

## 6. Implementar un bloqueo real de navegación

Agregar al controlador un estado explícito, por ejemplo:

```python
self.navegacion_bloqueada = False
self.motivo_bloqueo = None
```

Al validar **Información del proceso**:

```python
self.navegacion_bloqueada = True
self.motivo_bloqueo = "EXTRACCION_INFORMACION_PROCESO"
```

Todas las funciones que realizan clics o navegación deberán comprobar este estado antes de actuar.

El bloqueo solo se liberará dentro de un bloque `finally`, después de que la extracción haya terminado correctamente o se haya registrado completamente el error:

```python
try:
    extraer()
    inferir()
    persistir()
    estado = "EXTRACCION_COMPLETA"
except Exception:
    registrar_error()
    estado = "EXTRACCION_ERROR"
finally:
    liberar_navegacion_si_el_resultado_esta_registrado()
```

No debe liberarse el bloqueo solamente porque haya vencido un timeout interno sin guardar evidencia.

## 7. Corregir la espera de `/movimientos`

Crear una función específica:

```python
_esperar_movimientos_listos(causa)
```

Esta función deberá:

1. Esperar la URL `/movimientos`.
2. Esperar que desaparezcan overlays, spinners o textos **Buscando...**.
3. Validar **Datos generales** y el número de proceso.
4. Esperar una cantidad estable de filas durante varias comprobaciones consecutivas.
5. Localizar únicamente controles visibles dentro de las filas renderizadas.
6. Devolver descriptores de carpetas procesales, no locators persistentes.

La carpeta no deberá buscarse inmediatamente después del cambio de URL.

## 8. Descubrir carpetas procesales antes de entrar a `/actuaciones`

Mover el descubrimiento de carpetas al estado `/movimientos`.

Cada descriptor deberá contener:

- causa;
- dependencia jurisdiccional;
- ciudad;
- número o índice de instancia;
- fecha;
- actores y demandados;
- texto normalizado de la fila;
- identificadores obtenidos de la API cuando existan;
- clave estable de carpeta.

Antes de cada clic se deberá volver a localizar la fila desde su descriptor, porque Angular puede reconstruir el DOM.

No se deberá exigir que exista exactamente una carpeta en toda la página. La regla correcta es:

- una única carpeta accionable dentro de cada fila procesal validada;
- cero, una o varias filas procesales para la causa.

## 9. Crear el punto de entrada exclusivo a extracción

Sustituir el recorrido actual dentro de `/actuaciones` por una función bloqueante, por ejemplo:

```python
_extraer_informacion_proceso(causa, descriptor_carpeta)
```

Responsabilidades:

1. Validar la pantalla final.
2. Bloquear navegación.
3. Delimitar los paquetes API pertenecientes a la carpeta.
4. Esperar que las actuaciones estén estables.
5. Ejecutar `_ejecutar_extraccion_detalles()` una sola vez para esa carpeta.
6. Adjuntar metadatos de dependencia e instancia.
7. Guardar HTML, JSON y diagnóstico.
8. Retornar un resultado completo o un error estructurado.
9. Emitir `EXTRACCION_COMPLETA` o `EXTRACCION_ERROR`.

Los botones `Ver archivos` no formarán parte de este recorrido.

## 10. Definir cuándo la pantalla está estable

La estabilidad no debe depender únicamente de que exista el encabezado **Información del proceso**.

Utilizar una firma de pantalla compuesta por:

- URL;
- causa;
- cantidad de filas o actuaciones;
- cantidad de fechas detectadas;
- tamaño del texto de la sección de actuaciones;
- último identificador de actuación, si existe;
- finalización de la respuesta API de actuaciones;
- ausencia del overlay de carga.

La firma deberá permanecer igual durante varias comprobaciones consecutivas antes de iniciar la extracción.

Los botones `Ver archivos` podrán contarse para diagnosticar la carga, pero no se usarán como carpetas ni se pulsarán.

## 11. Orden transaccional de extracción

Para cada carpeta procesal:

```text
INFORMACION_PROCESO_LISTA
  -> NAVEGACION_BLOQUEADA
  -> capturar API
  -> capturar DOM e iframes
  -> normalizar actuaciones
  -> inferir etapa/fase/fecha
  -> guardar artefactos
  -> añadir resultado al consolidado de la causa
  -> EXTRACCION_COMPLETA
  -> NAVEGACION_REANUDADA
```

Si falla la inferencia pero la extracción fue obtenida, se debe conservar la evidencia y registrar un resultado parcial. No se deberá descartar automáticamente todo lo recolectado.

## 12. Retorno y continuación

Solo después de `EXTRACCION_COMPLETA` o de un `EXTRACCION_ERROR` ya registrado:

1. Liberar el bloqueo de navegación.
2. Regresar de `/actuaciones` a `/movimientos`.
3. Esperar nuevamente que **Datos generales** esté estable.
4. Confirmar la causa.
5. Reubicar las carpetas a partir de sus descriptores.
6. Procesar la siguiente carpeta pendiente.
7. Cuando no existan carpetas pendientes, consolidar la causa.
8. Regresar al buscador.

Eliminar el retorno duplicado que pueda hacer retroceder más de una pantalla después de terminar el ciclo de carpetas.

## 13. Cambios previstos por archivo

### `src/motor_busqueda_web.py`

- Reorganizar `_procesar_flujo_autonomo()` con los nuevos estados.
- Separar `_abrir_detalle_causa()` de la apertura de actuaciones.
- Crear `_esperar_movimientos_listos()`.
- Descubrir carpetas procesales en `/movimientos`.
- Crear el bloqueo y desbloqueo de navegación.
- Sustituir `_procesar_todas_las_carpetas()` por un recorrido de carpetas procesales de `/movimientos`.
- Invocar la extracción inmediatamente después de validar **Información del proceso**.
- Eliminar o retirar el código asistido inalcanzable situado después del retorno al flujo autónomo.

### `src/agente_explorador.py`

- Añadir selectores específicos para overlays de carga y filas de `/movimientos`.
- Separar selectores de carpeta procesal y botones `Ver archivos`.
- Correlacionar respuestas API por causa y carpeta procesal.

### `src/agente_extractor.py`

- Mantener metadatos de carpeta, dependencia e instancia.
- Procesar una sola captura estable por carpeta.
- Consolidar todas las carpetas antes de la inferencia final de la causa.

### `main.py`

- Interpretar estados `COMPLETADO`, `PARCIAL`, `EXTRACCION_ERROR` y errores de navegación.
- No comenzar otra causa mientras el bot reporte navegación bloqueada.

### `src/logger_config.py`

- Permitir un archivo de log configurable por entorno.
- Usar un log independiente durante las pruebas.

### `tests/test_navegacion_esatje.py`

- Sustituir pruebas que simulan el flujo incorrecto.
- Incorporar verificaciones del freno, extracción y reanudación.

## 14. Pruebas requeridas

### 14.1. Espera de `/movimientos`

1. La URL cambia, pero el overlay **Buscando...** sigue visible: no buscar ni pulsar la carpeta.
2. El overlay desaparece y la fila aparece: localizar la carpeta correcta.
3. Angular reconstruye las filas: volver a localizarlas mediante descriptor.
4. Existen varias dependencias: descubrirlas todas sin declarar ambigüedad global.

### 14.2. Freno en Información del proceso

1. Al detectar `/actuaciones`, activar `navegacion_bloqueada`.
2. Mientras el bloqueo esté activo, cualquier intento de clic debe fallar con un error controlado.
3. Verificar que ningún botón `Ver archivos` reciba clic.
4. Verificar que `_ejecutar_extraccion_detalles()` se invoque exactamente una vez por carpeta procesal.
5. Verificar que `Regresar` no se pulse antes de terminar la extracción.

### 14.3. Reanudación

1. Extracción correcta: emitir `EXTRACCION_COMPLETA` y regresar.
2. Error de extracción: guardar evidencia, emitir `EXTRACCION_ERROR` y liberar el bloqueo de forma segura.
3. Varias carpetas procesales: repetir el ciclo completo para cada una.
4. Última carpeta terminada: consolidar antes de volver al buscador.

### 14.4. Integración con artefactos reales

Usar los artefactos guardados:

- pantalla `/movimientos` con overlay **Buscando...**;
- pantalla `/movimientos` ya cargada;
- pantalla `/actuaciones` con **Información del proceso**;
- HTML final que contiene numerosos botones `Ver archivos`.

La prueba deberá demostrar que los botones de adjuntos se ignoran durante la navegación normal.

### 14.5. Logging

1. Ejecutar `pytest` y comprobar que no escribe en `ejecucion_produccion.log`.
2. Ejecutar una causa real y comprobar que el log solo contiene eventos de esa ejecución.

## 15. Eventos de auditoría esperados

```text
MOVIMIENTOS_CARGANDO
DATOS_GENERALES_LISTOS
CARPETAS_PROCESALES_DESCUBIERTAS
ABRIENDO_INFORMACION_PROCESO
INFORMACION_PROCESO_LISTA
NAVEGACION_BLOQUEADA
EXTRACCION_EN_PROGRESO
INFERENCIA_EN_PROGRESO
PERSISTENCIA_EN_PROGRESO
EXTRACCION_COMPLETA
NAVEGACION_REANUDADA
VOLVER_A_DATOS_GENERALES
```

El evento `NAVEGACION_BLOQUEADA` deberá incluir:

- causa;
- clave de carpeta procesal;
- URL;
- número de paquetes API capturados;
- número inicial de actuaciones visibles;
- instante de inicio.

`EXTRACCION_COMPLETA` deberá incluir:

- número de actuaciones extraídas;
- origen API o DOM;
- etapa, fase y fecha inferidas;
- rutas de artefactos;
- duración total;
- instante de desbloqueo.

## 16. Criterios de aceptación

La implementación estará terminada cuando:

1. El bot no busque la carpeta de `/movimientos` mientras aparezca **Buscando...**.
2. Se procesen cero, una o varias carpetas procesales sin utilizar una selección global `.first`.
3. Al llegar a **Información del proceso**, no se realice ningún clic adicional antes de terminar la extracción.
4. Los botones `Ver archivos` no se confundan con carpetas procesales.
5. La extracción se ejecute exactamente una vez por carpeta procesal.
6. La navegación permanezca bloqueada durante extracción, inferencia y persistencia.
7. Solo `EXTRACCION_COMPLETA` o un error ya registrado permitan regresar.
8. Las actuaciones de todas las dependencias conserven su origen.
9. La causa siguiente no comience antes de consolidar y guardar la actual.
10. Los logs de pruebas y producción estén separados.
11. Las pruebas automatizadas y una prueba visible de extremo a extremo sean satisfactorias.

## 17. Orden recomendado de implementación

1. Crear fixtures de `/movimientos` cargando, `/movimientos` estable y `/actuaciones` estable.
2. Escribir las pruebas del freno que inicialmente deben fallar.
3. Separar los detectores de las tres pantallas.
4. Implementar `_esperar_movimientos_listos()`.
5. Mover el descubrimiento de carpetas a `/movimientos`.
6. Implementar el bloqueo central de navegación.
7. Crear `_extraer_informacion_proceso()` como operación bloqueante.
8. Prohibir clics en `Ver archivos` durante el flujo principal.
9. Corregir el retorno y eliminar retrocesos duplicados.
10. Separar los logs de pruebas y producción.
11. Ejecutar pruebas unitarias e integración con artefactos.
12. Probar una causa real con una carpeta.
13. Probar una causa real con varias dependencias.
14. Ejecutar un lote piloto antes de reanudar el procesamiento masivo.

## 18. Alcance

Este documento define el plan de corrección. No implementa todavía los cambios en el bot.

La lectura automática de archivos adjuntos mediante los botones `Ver archivos` queda fuera de este cambio. Podrá implementarse posteriormente como un módulo independiente, sin interferir con el freno principal de **Información del proceso**.
