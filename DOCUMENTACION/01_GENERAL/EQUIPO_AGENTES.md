# Equipo de agentes de desarrollo

Los perfiles están en `.codex/agents/` y se seleccionan por nombre en Codex. El coordinador principal asigna el objetivo, archivos y criterios de aceptación, integra resultados y comunica límites. Son siete capacidades disponibles, no siete procesos simultáneos; la configuración admite hasta tres subagentes activos por sesión.

| Agente | Entrega | Propiedad |
| --- | --- | --- |
| `arquitecto` | Plan, contratos, invariantes, riesgos y aceptación | Lectura |
| `desarrollador` | Cambio mínimo de producción y verificación | Archivos de producción asignados |
| `qa_automatizado` | Pruebas conductuales, resultados y defectos | `tests/` y fixtures asignados |
| `revisor_seguridad` | Hallazgos priorizados o alcance sin hallazgos | Lectura |
| `navegacion_judicial` | Diagnóstico ESATJE, CAPTCHA y carpetas | Lectura |
| `postgres_concurrencia` | Diagnóstico de cola, transacciones y trabajadores | Lectura |
| `excel_procesal` | Discrepancias por fila/columna y evidencia de origen | Lectura |

## Inicio sin daemon

Ejecuta `ABRIR_CODEX_CASOS_JUDICIALES.cmd` desde el Explorador o usa este comando desde una terminal:

```powershell
codex --no-daemon --cd "C:\Users\pasante.callcenter\OneDrive - ESPOIR\Escritorio\Automatizar_Sistema_Judicial"
```

Dentro de esa sesión, el coordinador puede iniciar los perfiles por su nombre y `/agent` permite revisar o cambiar entre los agentes activos. No uses `codex agents` para este flujo: ese centro de sesiones requiere el servidor de fondo. Los siete perfiles fueron verificados mediante una prueba de humo real con `codex --no-daemon`; se ejecutaron en tres oleadas y todos respondieron `OK`.

## Método de trabajo

1. El coordinador define objetivo, evidencia, archivos que puede tocar cada agente, criterio de aceptación y acciones externas permitidas. Solo delega trabajo independiente.
2. El arquitecto planifica cambios que cruzan módulos o contratos de datos. Los especialistas investigan los riesgos de su dominio y entregan evidencia al desarrollador.
3. El desarrollador modifica producción. QA construye o ejecuta pruebas independientes. El revisor examina el diff y los riesgos de seguridad y mantenimiento.
4. El coordinador resuelve hallazgos y ejecuta la verificación de integración pertinente. Nadie certifica su propio cambio.

Cada encargo debe incluir `objetivo`, `evidencia disponible`, `archivos editables`, `criterio de aceptación`, `acciones externas permitidas` y `formato de entrega`. Cada agente separa hechos, inferencias, cambios, pruebas ejecutadas y riesgos pendientes, con rutas o comandos comprobables.

## Límites operativos

- Un rol no autoriza por sí mismo lotes reales, migraciones, escrituras en PostgreSQL, publicaciones ni fusiones. La tarea debe autorizar la acción concreta.
- No incluir claves, datos personales de causas ni Excel operativos en prompts, commits o logs compartidos. Usar muestras sintéticas o datos existentes autorizados.
- Ante evidencia judicial ambigua, conservar el dato original y marcar revisión manual. No fabricar títulos, fechas, fases ni estados.
- Una prueba verde no reemplaza la revisión del resultado real; una revisión manual no reemplaza pruebas repetibles.
- Si dos agentes necesitan editar el mismo archivo, el coordinador serializa los cambios. Los especialistas de lectura recomiendan; el desarrollador implementa.

## Ejemplo de asignación

Para una última gestión judicial errónea, `excel_procesal` identifica la actuación de origen y la discrepancia en fila/columna; `desarrollador` corrige la causa; `qa_automatizado` agrega una regresión; `revisor_seguridad` revisa el diff. Si el problema proviene del portal, entra `navegacion_judicial`. Si hay duplicación o pérdida en la cola, entra `postgres_concurrencia`.

En el caso `07331-2026-00445`, el especialista debe distinguir la fecha de la actuación de la fecha de consulta y verificar el título antes de proponer el valor final. Si falta evidencia local, entrega una necesidad de revisión manual.
