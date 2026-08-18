# Plan de implementación: corrección de fecha derivada

## 1. Objetivo

Corregir la inferencia procesal para que la fecha reportada corresponda a la actuación que sustenta la etapa y fase finales, especialmente cuando una regla de negocio reemplaza la clasificación inicialmente seleccionada.

Caso de referencia: `23331-2022-04191`.

Resultado esperado:

- **Última etapa:** `1 PRESENTACION Y CALIFICACION`
- **Última fase:** `1.3 CALIFICACION`
- **Fecha fin última fase:** `16/12/2022`
- **Actuación de respaldo:** `CALIFICACION DE SOLICITUD Y/O DEMANDA (RAZON DE NOTIFICACION)`, registrada a las `16:49`.

## 2. Evidencia del error

En la ejecución del `2026-08-06 18:56:32`, el sistema registró:

```text
fase_deducida: 1.3 CALIFICACION
etapa: 1 PRESENTACION Y CALIFICACION
fecha_elegida: 04/07/2023
```

El HTML fue procesado mediante la ruta de respaldo DOM y produjo 63 actuaciones. La extracción de texto plano sí relacionó correctamente:

```text
16/12/2022 16:49
CALIFICACION DE SOLICITUD Y/O DEMANDA (RAZON DE NOTIFICACION)
```

También detectó posteriormente:

```text
04/07/2023
CITACIÓN: NO REALIZADA - CAMBIO DE DIRECCIÓN
```

Por lo tanto, el problema no se encuentra en la lectura del HTML ni en la asociación inicial entre fecha y actuación.

## 3. Causa raíz

El motor primero selecciona como mejor hallazgo la citación no realizada del `04/07/2023`, conservando esa fecha en `fecha_fin`.

Después, la Regla 2 detecta que existe una citación fallida y que no existe una citación exitosa posterior. En consecuencia, reemplaza:

```python
ultima_etapa = "1 PRESENTACION Y CALIFICACION"
ultima_fase = "1.3 CALIFICACION"
```

Sin embargo, no reemplaza `fecha_fin`. El resultado termina combinando la fase de calificación con la fecha perteneciente a la citación fallida.

La causa técnica es que etapa, fase y fecha no se mantienen como una decisión indivisible cuando se aplican las reglas especiales.

## 4. Cambios propuestos

### 4.1. Crear primero la prueba de regresión

Agregar una prueba unitaria con, al menos, estas actuaciones:

```python
[
    {
        "fecha": "16/12/2022",
        "detalle": "CALIFICACION DE SOLICITUD Y/O DEMANDA (RAZON DE NOTIFICACION)",
    },
    {
        "fecha": "04/07/2023",
        "detalle": "CITACION: NO REALIZADA - CAMBIO DE DIRECCION",
    },
]
```

La prueba deberá exigir simultáneamente:

```text
etapa = 1 PRESENTACION Y CALIFICACION
fase = 1.3 CALIFICACION
fecha = 16/12/2022
```

Esta prueba debe fallar antes de la corrección y aprobar después de implementarla.

### 4.2. Mantener clasificación y evidencia como una unidad

Refactorizar la selección para trabajar con un objeto o estructura que contenga conjuntamente:

- Etapa.
- Fase.
- Fecha.
- Actuación de respaldo.
- Regla que produjo la decisión.

Ninguna regla deberá modificar únicamente la etapa o la fase dejando una fecha anterior sin revisar.

### 4.3. Resolver la fecha de la Regla 2

Cuando la Regla 2 determine que el expediente debe regresar a `1.3 CALIFICACION`:

1. Filtrar los hallazgos que correspondan exactamente a `1.3 CALIFICACION`.
2. Elegir el hallazgo cronológicamente más reciente de esa fase.
3. Asignar conjuntamente su etapa, fase, fecha y actuación de respaldo.
4. Utilizar la fecha solamente después de validar su formato.

La comparación cronológica deberá soportar, al menos:

- `dd/mm/yyyy`.
- Fechas ISO recibidas por la API.

La fecha podrá conservar su formato original en la salida; la conversión será interna y se utilizará para ordenar correctamente.

### 4.4. Definir un comportamiento seguro si falta la calificación

Si la regla obliga a regresar a calificación, pero no existe una actuación explícita que permita conocer su fecha:

- No utilizar la fecha de la citación fallida.
- Devolver una fecha desconocida o vacía según el contrato actual de salida.
- Emitir una advertencia estructurada para revisión.

Es preferible informar que la fecha no fue encontrada antes que presentar como fecha de calificación una fecha perteneciente a otra actuación.

### 4.5. Auditar las demás reglas especiales

Revisar las reglas que actualmente sustituyen la fase después de haber seleccionado `fecha_fin`:

- Citación no realizada sin citación exitosa.
- Abandono por falta de impulso procesal con razón de ejecutoria.
- Acuerdo de mediación sin ejecutoria.
- Nombramiento de perito sin informe posterior.

Cada regla debe declarar de forma explícita cuál es la actuación que respalda su fecha final. Esta auditoría evita que el mismo defecto aparezca en otras fases.

### 4.6. Mejorar la trazabilidad del log

Ampliar `DECISION_FASE` para registrar:

```json
{
  "regla_aplicada": "regla_2_citacion_fallida",
  "fase_original": "2.1 CITACION (PERSONA/BOLETA)",
  "fecha_original": "04/07/2023",
  "fase_final": "1.3 CALIFICACION",
  "fecha_final": "16/12/2022",
  "actuacion_respaldo": "CALIFICACION DE SOLICITUD Y/O DEMANDA (RAZON DE NOTIFICACION)"
}
```

Esto permitirá comprobar desde el terminal por qué se modificó la clasificación y de dónde se obtuvo la fecha definitiva.

## 5. Pruebas requeridas

### Prueba unitaria principal

Validar la combinación exacta de calificación del `16/12/2022` y citación fallida del `04/07/2023`.

### Pruebas de orden

Ejecutar el mismo caso con las actuaciones:

- En orden ascendente.
- En orden descendente.
- En un orden no cronológico.

El resultado siempre debe ser `16/12/2022`.

### Pruebas de múltiples calificaciones

Si existen varias actuaciones de calificación, comprobar que se elige la fecha más reciente perteneciente realmente a esa fase.

### Prueba sin evidencia de calificación

Verificar que una citación fallida sin una actuación explícita de calificación no herede la fecha de la citación.

### Pruebas de integración

Validar:

- La ruta de respaldo DOM con el artefacto real `data/temp_htmls/23331-2022-04191.html`.
- La inferencia mediante actuaciones estructuradas equivalentes a las recibidas por API.
- La propagación de la fecha a `FECHA FIN ULTIMA FASE`, `FECHA INICIAL FASE ACTUAL` y `FECHA INICIO FASE ACTUAL`.
- La suite completa de `pytest` para detectar regresiones.

## 6. Criterios de aceptación

La corrección se considerará terminada cuando:

1. La causa `23331-2022-04191` produzca etapa `1 PRESENTACION Y CALIFICACION`.
2. Produzca fase `1.3 CALIFICACION`.
3. Produzca fecha `16/12/2022` y no `04/07/2023`.
4. La fecha final pertenezca a la actuación que respalda la fase final.
5. El resultado sea independiente del orden de entrada de las actuaciones.
6. Ninguna regla especial pueda cambiar la fase sin definir también la evidencia y la fecha correspondientes.
7. El log indique la regla aplicada y el origen de la fecha final.
8. Todas las pruebas automatizadas existentes continúen aprobando.

## 7. Archivos previstos para la implementación

- `src/agente_extractor.py`: corrección central del motor y trazabilidad.
- `tests/test_clasificacion_arbol.py`: regresión unitaria de la Regla 2.
- `tests/test_extraccion_integration.py`: validación de propagación por las rutas de extracción.

## 8. Alcance

Este documento describe el plan. No incluye todavía la modificación del motor ni de las pruebas automatizadas.
