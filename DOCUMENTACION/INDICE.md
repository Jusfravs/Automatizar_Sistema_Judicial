# Índice de documentación

Toda la documentación Markdown del proyecto está centralizada en esta carpeta y
clasificada por propósito. Los nombres numerados mantienen un orden estable al
navegar desde el explorador de archivos o GitHub.

La referencia operativa vigente es el [Manual de uso](01_GENERAL/MANUAL_DE_USO.md)
junto con el [Contexto de reanudación](01_GENERAL/CONTEXTO_REANUDACION.md).
Los documentos en `03_PLANES`, `04_DIAGNOSTICOS_Y_CORRECCIONES` y `05_AVANCES`
registran decisiones y hechos de su fecha; no sustituyen el estado operativo actual.

## 01_GENERAL

Documentos introductorios y operativos de alcance general.

- [README](01_GENERAL/README.md): descripción general, arquitectura y estructura del proyecto.
- [Visión del proyecto](01_GENERAL/Vision_Proyecto.md): objetivos, componentes y flujo completo.
- [Manual de uso](01_GENERAL/MANUAL_DE_USO.md): preparación, ejecución, supervisión y recuperación vigentes.
- [Manual anterior (archivo)](01_GENERAL/MANUAL_DE_USO_ANTERIOR_20260824.md): referencia histórica; puede incluir rutas y políticas ya reemplazadas.
- [Contexto de reanudación](01_GENERAL/CONTEXTO_REANUDACION.md): estado operativo y decisiones vigentes.

## 02_MODULOS_Y_CONFIGURACION

Reglas funcionales, especificaciones y configuración de componentes.

- [Módulo de filtro de casos](02_MODULOS_Y_CONFIGURACION/MODULO_FILTRO_CASOS.md): árbol y reglas procesales.
- [Molde de nuevos cambios](02_MODULOS_Y_CONFIGURACION/MOLDE_NUEVOS_CAMBIOS.md): estructura y requisitos del reporte.
- [Configuración de AutoCaptcha](02_MODULOS_Y_CONFIGURACION/CONFIGURACION_AUTOCAPTCHA.md): activación segura y parámetros.

## 03_PLANES

Planes técnicos de implementación, automatización y corrección.

- [API de AutoCaptcha](03_PLANES/PLAN_IMPLEMENTACION_API_AUTOCAPTCHA.md).
- [Automatización de botones e-SATJE](03_PLANES/PLAN_AUTOMATIZACION_BOTONES_ESATJE.md).
- [Freno en Información del proceso](03_PLANES/PLAN_CORRECCION_FRENO_INFORMACION_PROCESO.md).
- [Lectura selectiva de adjuntos PDF](03_PLANES/PLAN_IMPLEMENTACION_LECTURA_SELECTIVA_ADJUNTOS_PDF.md): propuesta de evidencia documental, límites de lectura y despliegue seguro.
- [Regreso al buscador no confirmado](03_PLANES/PLAN_SOLUCION_REGRESO_BUSCADOR_NO_CONFIRMADO.md).

## 04_DIAGNOSTICOS_Y_CORRECCIONES

Análisis de incidentes y soluciones puntuales documentadas.

- [Diagnóstico y análisis de logs RPA](04_DIAGNOSTICOS_Y_CORRECCIONES/Diagnóstico%20y%20Análisis%20de%20Logs%20RPA.md).
- [Corrección de fecha derivada](04_DIAGNOSTICOS_Y_CORRECCIONES/CORRECCION_FECHA_DERIVADA.md).

## 05_AVANCES

Historial cronológico de checkpoints del proyecto.

- [Checkpoint 00: estado inicial y diagnóstico](05_AVANCES/00_Estado_Inicial_y_Diagnostico.md).
- [Checkpoint 01: estabilización y bugs](05_AVANCES/01_Estabilizacion_y_Bugs.md).
- [Checkpoint 02: migración SQLite y cola](05_AVANCES/02_Migracion_SQLite_y_Cola.md).
- [Checkpoint 03: inferencia y Excel base](05_AVANCES/03_Inferencia_y_Excel_Base.md).

## Convención para documentos nuevos

1. Guardar cada nuevo `.md` en la categoría correspondiente.
2. Añadirlo a este índice.
3. Usar enlaces relativos entre documentos.
4. No volver a crear archivos Markdown dispersos en la raíz del proyecto.
