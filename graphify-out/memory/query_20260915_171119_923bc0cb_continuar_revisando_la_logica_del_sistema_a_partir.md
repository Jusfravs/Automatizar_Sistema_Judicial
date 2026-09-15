---
type: "query"
date: "2026-09-15T17:11:19.861640+00:00"
question: "Continuar revisando la logica del sistema a partir de las preguntas del grafo, conectando o corrigiendo funciones cuando sea necesario sin tocar la inferencia ni la ubicacion por palabras clave"
contributor: "graphify"
outcome: "useful"
source_nodes: ["GestorCola", ".bloquear_ejecucion()", "GestorCasos", ".guardar()", "BotJudicialTransaccional"]
---

# Q: Continuar revisando la logica del sistema a partir de las preguntas del grafo, conectando o corrigiendo funciones cuando sea necesario sin tocar la inferencia ni la ubicacion por palabras clave

## Answer

Expanded tokens: persistencia, transaccional, consolidacion, retorno, navegacion, estado, cola, causa, resultado, error, guardar, carpeta. La revision encontro una carrera real entre recuperar_huerfanos y una ejecucion activa; se corrigio con GestorCola.bloquear_ejecucion y se integro en main y Orquestador. Se preserva el error original si BEGIN IMMEDIATE falla. GestorCasos.guardar ahora publica el CSV atomically mediante archivo temporal y os.replace; la carga Excel usa una copia temporal unica sin PowerShell. La herencia BotJudicialTransaccional/BotJudicial es coherente y activa, por lo que no se fusiono. MotorInferenciaProcesal y sus umbrales/reglas no fueron modificados. Verificacion: 258 pruebas OK y 3 integraciones PostgreSQL omitidas; grafo actualizado a 1220 nodos y 2289 aristas, sin endpoints faltantes, colgantes ni aristas colapsadas.

## Outcome

- Signal: useful

## Source Nodes

- GestorCola
- .bloquear_ejecucion()
- GestorCasos
- .guardar()
- BotJudicialTransaccional