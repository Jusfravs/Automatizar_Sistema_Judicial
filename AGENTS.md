## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## Windows PowerShell

Codex CLI runs commands in Windows PowerShell on this machine. Use PowerShell
syntax instead of mixing in CMD or Bash flags: use `Get-ChildItem -Force`
instead of `ls -la`, and `Get-ChildItem -LiteralPath <path> -File -Recurse`
instead of `dir /s /b`. Avoid `&&`, which is not available in Windows
PowerShell 5.1; run dependent commands separately or use `;` only when the
second command may safely run regardless of the first. Use `Get-Content
-LiteralPath <path>` for reading files and quote paths containing spaces.

Open this repository with `ABRIR_CODEX_CASOS_JUDICIALES.cmd` so the CLI starts
at the project root with the active Codex model/provider, project-scoped
write access, approval prompts for operations outside the project, and web
search enabled.

## Verificacion obligatoria y uso de herramientas

- No describas una accion como ejecutada si no invocaste una herramienta y
  recibiste su resultado. No simules intentos de comandos narrandolos en texto.
- Antes de afirmar que un archivo existe, leelo o comprueba su ruta con una
  herramienta. Si falla el acceso, detente y comunica el comando real y el
  error real; no encadenes intentos especulativos con sintaxis de otros shells.
- Este proyecto usa Windows PowerShell. Emplea `Get-ChildItem`, `Get-Content`,
  `Test-Path` y `Set-Location`; no uses opciones de Bash/CMD como `ls -la`,
  `dir /s /b` ni `&&` en PowerShell.
- No inventes resultados de pruebas, métricas de rendimiento, tablas, vistas,
  índices, estados de producción ni verificaciones. Antes de documentarlos,
  comprueba el código, el esquema y la salida de las pruebas correspondientes.
- Distingue siempre entre hechos observados, hipótesis y propuestas. Si una
  validación no se ejecutó o no pudo completarse, dilo claramente y no declares
  completado el plan ni listo el sistema para producción.
- Para cambios solicitados, inspecciona primero los archivos pertinentes,
  modifica solo lo necesario y ejecuta comprobaciones proporcionadas al cambio.

## Equipo de agentes de desarrollo

- Los perfiles del proyecto están en `.codex/agents/`; su contrato y flujo de
  trabajo están en `DOCUMENTACION/01_GENERAL/EQUIPO_AGENTES.md`.
- Delega solo tareas independientes con objetivo, evidencia, archivos editables,
  criterio de aceptación y acciones externas autorizadas. El coordinador
  conserva la integración y la comunicación final.
- `desarrollador` modifica producción; `qa_automatizado` modifica pruebas
  asignadas; los otros perfiles investigan o revisan en lectura. Serializa
  cualquier edición del mismo archivo y pide revisión independiente del diff.
- No invoques los siete perfiles por rutina: elige los necesarios para el riesgo
  real de la tarea y respeta el límite de tres subagentes activos.
