---
name: revision-procesal-judicial
description: Audita fases y fechas de causas judiciales cuando se pide revisar, validar o certificar una clasificación procesal. No usar para solo reprocesar datos sin una revisión de evidencia.
---

# Revisión procesal judicial

El objetivo es determinar si una fase o fecha está sustentada por las actuaciones,
no solo si coincide con el resultado que el sistema ya tenía guardado.

## Regla principal

Una re-inferencia que reproduce la clasificación almacenada solo demuestra
consistencia interna. Nunca la presentes como una corrección o certificación sin
contrastar la evidencia procesal que origina la fase.

## Cómo revisar

- Lee las actuaciones relevantes, las personas demandadas/procesadas y la fecha
  de cada hito antes de concluir que un caso está correcto.
- Busca evidencia que contradiga la fase propuesta: actuaciones posteriores,
  citaciones no realizadas, archivos por incumplimiento, o providencias que
  mencionen una fase anterior sin constituir el hito que la ordena.
- Distingue respuestas de terceros a oficios o requerimientos (por ejemplo SRI,
  CNT, Registro Civil) de la contestación de la demanda. Las primeras no son
  evidencia de `CONTESTACION` ni pueden bloquear una regla de citación pendiente.
- Para `2.1 CITACION (PERSONA/BOLETA)`, exige evidencia atribuible de citación
  exitosa para **cada** demandado/procesado registrado. Una citación no realizada
  o una gestión para localizar a una persona mantiene la causa antes de citación
  completa; no la des por superada por una constancia genérica o por la citación
  de otra persona.
- Separa siempre dos diagnósticos: (1) error de regla con actuaciones suficientes,
  que se corrige y se re-infiere localmente; y (2) historial desactualizado o
  incompleto, que requiere una nueva consulta a SATJE.

## Entrega de la revisión

Para cada causa revisada, indica la fase y fecha guardadas, la evidencia concreta,
la fase y fecha que corresponde y si necesita ajuste de regla, re-inferencia local
o reproceso en SATJE. Si la evidencia no permite concluir, declárala pendiente de
revisión en vez de certificarla como correcta.
