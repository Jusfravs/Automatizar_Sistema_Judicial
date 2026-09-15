---
type: "query"
date: "2026-09-15T16:13:40.587016+00:00"
question: "Revisar la logica del sistema a partir de las preguntas sugeridas sin modificar la inferencia procesal"
contributor: "graphify"
outcome: "useful"
source_nodes: ["main()", "GestorCola", ".reservar_causa()", "MotorInferenciaProcesal"]
---

# Q: Revisar la logica del sistema a partir de las preguntas sugeridas sin modificar la inferencia procesal

## Answer

La revision encontro un defecto real fuera de la inferencia: main.py procesaba la lista CSV y escribia el resultado final en GestorCola sin reservar antes la causa como EN_PROCESO. Se agrego GestorCola.reservar_causa y se conecto antes del navegador. Los lotes solo reservan PENDIENTE; --solo permite reproceso terminal pero bloquea EN_PROCESO. Las reglas, umbrales y palabras clave de MotorInferenciaProcesal no cambiaron. Verificado con 250 pruebas OK y 3 integraciones PostgreSQL omitidas por entorno.

## Outcome

- Signal: useful

## Source Nodes

- main()
- GestorCola
- .reservar_causa()
- MotorInferenciaProcesal