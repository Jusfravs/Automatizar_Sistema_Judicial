# Plan de solución: `REGRESO_AL_BUSCADOR_NO_CONFIRMADO`

## 0. Estado y alcance

- Fecha del diagnóstico: 7 de agosto de 2026.
- Estado: parche implementado, validado localmente y aprobado en pilotos reales de 1, 2 y 3 carpetas; reanudación masiva pendiente de autorización.
- Este documento define la solución aplicada. La implementación no autoriza por sí sola
  reanudar el lote: antes deben completarse los respaldos y pilotos de la sección 6.
- Alcance: retorno controlado al buscador, ciclo de varias carpetas, clasificación del resultado, persistencia y recuperación de las causas afectadas.
- Fuera de alcance: extracción de adjuntos, cambios al motor de inferencia procesal y ejecución masiva.

## 1. Conclusión ejecutiva

La excepción de `main.py` no es la causa raíz. Es el freno de seguridad que evitó iniciar otra causa cuando el bot devolvió `regreso_confirmado=False`.

La ejecución real reveló dos defectos independientes:

1. La máquina de estados permite abrir la primera carpeta desde `CARPETAS_DESCUBIERTAS`, pero no permite abrir la segunda o siguientes desde `MOVIMIENTOS_LISTOS`.
2. El retorno a `/busqueda-filtros` depende de `page.wait_for_url()` con espera de evento `load`, no de una confirmación por estado visible. En una SPA, el control puede cambiar de ruta sin satisfacer esa espera o puede requerir el respaldo `go_back()`. El método actual tampoco ejecuta ese respaldo cuando existe un botón visible pero su clic no produce una transición confirmada.

Por tanto, no se debe eliminar el `RuntimeError` de `main.py`. Deben corregirse las causas anteriores y mantener el freno final.

## 2. Evidencia observada

### 2.1. Causa `23331-2023-04275`

- Carpetas descubiertas: 1.
- Carpetas con manifiesto durable: 1.
- La extracción terminó como `EXTRACCION_COMPLETA`.
- El primer retorno al buscador agotó 30 segundos esperando `load`.
- La recuperación posterior confirmó el buscador y dejó `regreso_confirmado=True`.
- A pesar de estar completa, la causa quedó persistida como `PARCIAL` por haber pasado por el bloque genérico de excepción.

Conclusión: falso negativo de retorno y clasificación final incorrecta.

### 2.2. Causa `23331-2022-03525`

- Carpetas descubiertas: 2.
- Carpetas procesadas: 1.
- Error: `TRANSICION_NO_PERMITIDA:MOVIMIENTOS_LISTOS->ABRIENDO_INFORMACION_PROCESO`.
- `regreso_confirmado=True` después de la recuperación.
- SQLite quedó en `PARCIAL` con una carpeta pendiente.

Conclusión: defecto reproducible de la tabla de transiciones para múltiples carpetas.

### 2.3. Causa `23331-2022-03524`

- Carpetas descubiertas: 3.
- Carpetas procesadas: 1.
- Ocurrió el mismo error de transición al intentar abrir la segunda carpeta.
- El intento de recuperación al buscador agotó 30 segundos.
- `regreso_confirmado=False`.
- `main.py` persistió el resultado parcial y detuvo el lote con `REGRESO_AL_BUSCADOR_NO_CONFIRMADO`.

Conclusión: el freno final actuó correctamente, pero el resultado fue provocado por los dos defectos anteriores.

### 2.4. Estado de los datos antes de la recuperación

SQLite contenía al iniciar la recuperación:

| Causa | Estado SQLite | Procesadas/descubiertas | Regreso |
|---|---:|---:|---:|
| `23331-2023-04275` | `PARCIAL` | 1/1 | `true` |
| `23331-2022-03525` | `PARCIAL` | 1/2 | `true` |
| `23331-2022-03524` | `PARCIAL` | 1/3 | `false` |

Los manifiestos ya escritos son válidos y no deben borrarse. El CSV, el Excel final, SQLite y `data/casos_fallidos.txt` fueron actualizados durante la ejecución y deben respaldarse antes de cualquier recuperación.

## 3. Causas técnicas

### 3.1. Transición ausente
### 2.5. Resultado de los pilotos del 7 de agosto de 2026

| Causa | Carpetas | Estado final | Regreso | Estrategia |
|---|---:|---:|---:|---|
| `23331-2023-04275` | 1/1 | `PROCESADO` / `COMPLETADO` | `true` | 1 clic, 0 `go_back()` |
| `23331-2022-03525` | 2/2 | `PROCESADO` / `COMPLETADO` | `true` | 1 clic, 0 `go_back()` |
| `23331-2022-03524` | 3/3 | `PROCESADO` / `COMPLETADO` | `true` | 1 clic, 0 `go_back()` |

Los tres pilotos terminaron en `/busqueda-filtros`, con detector estricto listo,
manifiestos `COMPLETA` para todas las carpetas y sin iniciar una causa adicional.
Las transiciones de la segunda y tercera carpeta se observaron como
`MOVIMIENTOS_LISTOS -> ABRIENDO_INFORMACION_PROCESO`.

El primer intento de la causa de dos carpetas recibió una página externa de
protección F5/TSPD antes de presentar el formulario. No se intentó evadirla. Un
único reintento limpio posterior completó el piloto.

Los pilotos descubrieron además dos condiciones no visibles en las pruebas
iniciales: el control `Regresar` conduce a `/causas`, mientras el acceso lateral
`routerlink="/busqueda-filtros"` lleva directamente al buscador; y las ejecuciones
`--solo` no deben reemplazar la lista global de fallidos. Ambas condiciones quedaron
incorporadas al parche y cubiertas por pruebas.


La tabla `TRANSICIONES_VALIDAS` admite:

```text
CARPETAS_DESCUBIERTAS -> ABRIENDO_INFORMACION_PROCESO
```

pero omite:

```text
MOVIMIENTOS_LISTOS -> ABRIENDO_INFORMACION_PROCESO
```

Después de regresar desde la primera carpeta, el estado correcto es `MOVIMIENTOS_LISTOS`. La segunda carpeta debe poder abrirse desde ese estado sin volver a ejecutar el descubrimiento global.

### 3.2. Confirmación de retorno acoplada a navegación `load`

`_volver_al_buscador()` hace clic y después llama a `page.wait_for_url()` con el comportamiento predeterminado de Playwright. El log confirma que esperó una navegación hasta `load` durante 30 segundos.

En e-SATJE, que es una SPA, la condición de éxito debe ser observable:

- ruta exacta `/busqueda-filtros` o `/busqueda`;
- un único campo de número de causa;
- campo visible y editable;
- ausencia de una pantalla de movimientos o actuaciones activa.

No se debe depender de que ocurra un nuevo evento `load`.

### 3.3. Respaldo incompleto

Si existe exactamente un botón visible, el método lo pulsa y espera. Cuando ese clic no confirma la transición, el timeout se propaga y no se intenta el único `go_back()` permitido.

El respaldo actual solo se usa cuando no existe exactamente un candidato visible. Esto no cumple la política definida para “control presente pero sin transición”.

### 3.4. Segundo intento implícito y poco auditable

Cuando el retorno normal falla, `_procesar_flujo_autonomo()` entra en su `except` y puede llamar nuevamente a `_volver_al_buscador()`. Esto permite dos clics o dos estrategias completas sin un contexto compartido que limite y audite los intentos.

### 3.5. Clasificación incorrecta

Si existe al menos una carpeta durable, el bloque de excepción fuerza `estado="PARCIAL"`, incluso cuando:

- todas las carpetas fueron completadas y solo falló la confirmación del retorno; o
- faltan carpetas por un error de navegación.

Estos casos deben conservar los datos durables, pero su estado principal debe reflejar `ERROR_NAVEGACION` y exigir reintento.

### 3.6. Confirmación de CSV no comprobada

`GestorCasos.guardar()` devuelve `False` ante determinados fallos. `main.py` llama el método sin comprobar su valor, por lo que actualmente un fallo silencioso podría no activar `PERSISTENCIA_ERROR`.
### 3.7. Sobrescritura de fallidos en modo piloto

La persistencia histórica reemplazaba `data/casos_fallidos.txt` con los fallos de
la ejecución actual. En modo `--solo`, un piloto exitoso podía vaciar causas ajenas
todavía pendientes. La actualización del piloto debe funcionar como una combinación
acotada: retirar solo las causas procesadas en ese piloto, reinsertar las que vuelvan
a fallar y conservar las demás en su orden original.


## 4. Diseño de la corrección

### 4.1. Corregir la máquina de estados

Añadir exclusivamente la transición:

```text
MOVIMIENTOS_LISTOS -> ABRIENDO_INFORMACION_PROCESO
```

Mantener `MOVIMIENTOS_LISTOS -> CONSOLIDACION_EN_PROGRESO` para cuando no queden claves pendientes.

No relajar globalmente la validación ni permitir destinos arbitrarios.

### 4.2. Crear un detector puro del buscador

Implementar `_diagnosticar_buscador()` sin clics ni navegación. Debe devolver un diccionario con:

```python
{
    "url": "...",
    "ruta_valida": True,
    "campos_causa": 1,
    "campo_visible": True,
    "campo_habilitado": True,
    "movimientos_visibles": False,
    "actuaciones_visibles": False,
    "listo": True,
}
```

La confirmación se basará en `listo`, no solamente en la URL.

### 4.3. Crear una espera por sondeo visible

Implementar `_esperar_buscador_listo(causa, timeout_ms)`:

1. consultar el detector puro;
2. retornar inmediatamente si ya está listo;
3. sondear cada `sondeo_estabilidad_ms`;
4. exigir dos observaciones consecutivas válidas;
5. no usar `wait_for_url(..., wait_until="load")` como condición principal;
6. al agotar el tiempo, devolver o adjuntar el último diagnóstico.

Añadir `retorno_buscador_timeout_ms` a `config.json`, separado de `movimientos_timeout_ms`.

### 4.4. Hacer el retorno acotado e idempotente

`_volver_al_buscador()` tendrá una sola ejecución por causa:

1. Si el detector ya confirma el buscador, terminar sin navegación.
2. Localizar primero un único acceso directo validado a `/busqueda-filtros` y registrar sus atributos; usar el control `Regresar` solo cuando el acceso directo no esté disponible.
3. Hacer como máximo un clic por el wrapper central.
4. Esperar mediante `_esperar_buscador_listo()`.
5. Si el clic no produjo transición y la página continúa inequívocamente en `/movimientos`, permitir un único `go_back()`.
6. Volver a esperar mediante el detector.
7. Si sigue sin confirmarse, guardar evidencia y lanzar `RETORNO_BUSCADOR_ERROR`.

Registrar en un contexto por causa:

```python
{
    "iniciado": True,
    "clicks": 0 | 1,
    "go_back": 0 | 1,
    "estrategia": "ya_visible | control | go_back",
    "url_inicial": "...",
    "url_final": "...",
    "diagnostico_final": {...},
}
```

El bloque `except` no repetirá la estrategia completa. Si el retorno ya fue intentado, solo podrá realizar una revalidación de lectura para detectar una transición tardía.

### 4.5. Separar resultado de extracción y estado de navegación

El resultado conservará todas las carpetas durables, pero añadirá:

```python
{
    "estado": "ERROR_NAVEGACION",
    "estado_extraccion": "COMPLETADO | PARCIAL | EXTRACCION_ERROR",
    "requiere_reintento": True,
    "regreso_confirmado": False,
    "retorno_buscador": {...},
}
```

### 4.8. Conservar fallidos ajenos durante pilotos

En una ejecución `--solo`, leer la lista existente y actualizar únicamente la causa
objetivo:

- si termina correctamente, retirarla de la lista;
- si falla, mantenerla o añadirla una sola vez;
- conservar sin cambios todas las causas que no pertenecen al piloto.

Reglas:

- Todas las carpetas completas y retorno confirmado: `COMPLETADO`.
- Algunas carpetas útiles y todas las claves recorridas: `PARCIAL`.
- Quedan carpetas sin recorrer por un error de navegación: `ERROR_NAVEGACION`.
- Extracción completa pero retorno no confirmado: `ERROR_NAVEGACION` con `estado_extraccion="COMPLETADO"`.
- `regreso_confirmado=False` siempre impide avanzar a otra causa.

### 4.6. Mantener y reforzar el freno de `main.py`

Conservar el control que genera `REGRESO_AL_BUSCADOR_NO_CONFIRMADO`.

Además:

- comprobar `if not repo.guardar(): raise RuntimeError("PERSISTENCIA_ERROR:CSV")`;
- no escribir datos derivados en el CSV para `ERROR_NAVEGACION`;
- persistir en SQLite el resultado estructurado, manifiestos y diagnóstico de retorno;
- registrar la causa como reintentable;
- detener el lote después de confirmar esa persistencia de error.

### 4.7. Guardar evidencia del retorno

Ante cualquier fallo del retorno, guardar en un directorio del intento:

- `return_diagnostic.json`;
- `return_page.html`;
- `return_screen.png`;
- URL, estado operativo, candidatos encontrados y estrategias ejecutadas.

Esta captura ocurre con el bloqueo de extracción ya liberado y no autoriza navegación adicional.

## 5. Plan de pruebas

### 5.1. Máquina de estados y múltiples carpetas

1. Dos carpetas: ambas se abren exactamente una vez.
2. Tres carpetas: se producen tres manifiestos y dos retornos intermedios más el retorno de la última carpeta.
3. Después de cada retorno: `MOVIMIENTOS_LISTOS -> ABRIENDO_INFORMACION_PROCESO` es válida.
4. Una transición ajena sigue fallando con `TRANSICION_NO_PERMITIDA`.
5. El número de `resultados_carpetas` coincide con `carpetas_descubiertas` antes de consolidar como completo.

### 5.2. Retorno al buscador

1. Ya está en el buscador: cero clics y cero `go_back()`.
2. El clic cambia inmediatamente la URL antes de iniciar la espera: éxito por detector.
3. Angular cambia tarde la ruta y monta el campo: éxito por sondeo.
4. El clic no cambia la vista: un único `go_back()`.
5. El clic cambia la URL pero el campo aún no existe: esperar hasta que el campo sea válido.
6. Ruta correcta con dos campos: no confirmar.
7. Botón ambiguo: no hacer clic; usar solo el respaldo permitido si la pantalla origen es válida.
8. Fallan clic y respaldo: evidencia durable, `ERROR_NAVEGACION` y cero segunda estrategia desde el `except`.

7. Un piloto exitoso conserva todos los fallidos ajenos y retira solo su causa objetivo.
### 5.3. Clasificación y persistencia

1. 1/1 completa más retorno confirmado: `COMPLETADO`, no `PARCIAL`.
2. 1/2 o 1/3 por fallo de navegación: `ERROR_NAVEGACION`, `requiere_reintento=True`.
3. Extracción completa con retorno no confirmado: datos conservados en SQLite, sin marcar CSV como final.
4. `repo.guardar()` devuelve `False`: `PERSISTENCIA_ERROR` y lote detenido.
5. SQLite falla: lote detenido sin iniciar la siguiente causa.
6. `regreso_confirmado=False`: se mantiene el `RuntimeError` de seguridad.

### 5.4. Regresión

- Ejecutar toda la suite existente.
- Confirmar que las pruebas no modifican `ejecucion_produccion.log`.
- Ejecutar `py_compile` y `git diff --check`.

## 6. Recuperación de las causas afectadas

1. No borrar los manifiestos existentes.
2. Respaldar con timestamp:
   - `data/reporte_trabajo.csv`;
   - `data/REPORTE_PROCESADO_FINAL.xlsx`;
   - `estado_casos.db`;
   - `data/casos_fallidos.txt`.
3. Generar un inventario desde SQLite usando:
   - `regreso_confirmado = false`;
   - `resultados_carpetas < carpetas_descubiertas`;
   - errores `TRANSICION_NO_PERMITIDA` o timeout de retorno.
4. Incluir como mínimo las tres causas confirmadas en la sección 2.4.
5. Añadir o utilizar un modo de piloto `--solo <causa>` que garantice que `main.py` no procesa causas posteriores.
6. Reprocesar primero una causa de una carpeta (`23331-2023-04275`).
7. Reprocesar una causa de dos carpetas (`23331-2022-03525`).
8. Reprocesar una causa de tres carpetas (`23331-2022-03524`).
9. Confirmar por causa:
   - manifiestos igual a carpetas descubiertas;
   - `regreso_confirmado=True`;
   - estado SQLite correcto;
   - CSV y SQLite con la misma inferencia final;
   - ausencia de navegación entre bloqueo y resultado durable.
10. Solo después retirar la marca reintentable o sobrescribir `PARCIAL` con el estado final.

`data/casos_fallidos.txt` no es suficiente para esta recuperación porque las causas parciales con regreso confirmado pueden no aparecer allí. SQLite será la fuente del inventario.

## 7. Archivos implementados

- `src/motor_busqueda_web.py`: transición, detector, espera, retorno acotado, diagnóstico y clasificación.
- `main.py`: confirmación del retorno, comprobación booleana de `repo.guardar()`, modo de piloto individual y conservación de fallidos ajenos.
- `config.json`: `retorno_buscador_timeout_ms`.
- `tests/test_regreso_buscador.py`: retorno SPA, fallback, clasificación, modo `--solo`, persistencia y ciclos de varias carpetas.
- `data/backups/recuperacion_20260807_120637/`: respaldo verificado previo a los pilotos.

No se requiere modificar `src/agente_extractor.py` ni las reglas de inferencia.

## 8. Criterios de aceptación

1. Una causa de varias carpetas recorre todas las claves sin violar la máquina de estados.
2. El retorno se confirma por ruta y formulario visibles, no por evento `load`.
3. El control de retorno recibe como máximo un clic y el respaldo usa como máximo un `go_back()`.
4. El `except` no repite una navegación ya intentada.
5. Todo fallo de retorno genera evidencia durable y `ERROR_NAVEGACION`.
6. Una extracción 1/1 completa no queda como `PARCIAL` por un falso timeout.
7. Una causa 1/2 o 1/3 nunca se considera finalizada.
8. `repo.guardar() == False` detiene el lote.
9. Las tres causas afectadas se recuperan mediante pilotos individuales y terminan consistentes en CSV y SQLite.
10. La suite completa queda verde y el piloto no inicia una causa adicional.

## 9. Orden de implementación

1. Añadir primero las pruebas fallidas de transición y retorno SPA.
2. Corregir la tabla de transiciones.
3. Implementar detector y espera pura del buscador.
4. Refactorizar el retorno con un clic, un respaldo y contexto auditable.
5. Impedir el segundo retorno desde el bloque genérico de excepción.
6. Corregir clasificación y contrato de navegación.
7. Comprobar el retorno booleano de `repo.guardar()`.
8. Añadir el modo `--solo` para pilotos y recuperación.
9. Ejecutar suite, compilación y revisión estática.
10. Respaldar datos y ejecutar los tres pilotos en el orden definido.
11. Auditar manifiestos, SQLite, CSV y logs.
12. Autorizar la reanudación del lote únicamente si todos los criterios de aceptación se cumplen.

## 10. Estado de implementación

- [x] Transición de segunda y siguientes carpetas.
- [x] Detector puro y sondeo estable del buscador.
- [x] Retorno acotado a un clic y un `go_back()`.
- [x] Revalidación tardía sin segundo intento de navegación.
- [x] Clasificación separada de extracción y navegación.
- [x] Validación booleana de `GestorCasos.guardar()`.
- [x] Modo `--solo <causa>`.
- [x] Pruebas automáticas y compilación local (`66 passed`).
- [x] Respaldos e inventario de recuperación.
- [x] Pilotos reales de 1, 2 y 3 carpetas.
- [ ] Autorización de reanudación masiva.
