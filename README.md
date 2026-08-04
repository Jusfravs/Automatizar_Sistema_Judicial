# Automatización Sistema Judicial (e-SATJE) - Arquitectura Multi-Agente

Sistema automatizado de alta resiliencia para la consulta, extracción, análisis semántico y procesamiento masivo de información procesal desde el portal e-SATJE de la Función Judicial del Ecuador.

---

## 📐 Arquitectura del Sistema Multi-Agente

El proyecto utiliza una arquitectura desacoplada orientada a eventos, tolerancia a fallos y persistencia transaccional SQLite para procesar lotes masivos de causas judiciales (ej. 4,017 juicios).

```
                     +---------------------------------------+
                     |    Origen de Datos (Excel / CSV)     |
                     | (data/REPORTE JUICIOS PARA REVISIÓN) |
                     +-------------------+-------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |     src/gestor_cola.py (SQLite DB)    |
                     |   Tabla: juicios (PENDIENTE/PROCESO)  |
                     +-------------------+-------------------+
                                         |
               +-------------------------+-------------------------+
               |                                                   |
               v                                                   v
+-----------------------------+                     +-----------------------------+
|    src/agente_explorador    |                     |    src/agente_extractor     |
|   (RPA Playwright/API REST) |                     |   (BS4 / Parser Offline)    |
|   - Navegación Angular      |                     |   - Árbol Procesal 6 Fases  |
|   - Descarga de HTML/PDFs   |                     |   - Inferencia & Mandamientos|
+--------------+--------------+                     +--------------+--------------+
               |                                                   |
               +-------------------------+-------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |          src/orquestador.py           |
                     |          (main.py - Loop Principal)   |
                     +-------------------+-------------------+
                                         |
               +-------------------------+-------------------------+
               |                                                   |
               v                                                   v
+-----------------------------+                     +-----------------------------+
|    src/prompt_procesador    |                     |     src/gestor_estado.py    |
| (Reglas / Filtros Especiales|                     |  (Consolidación CSV / Excel)|
+-----------------------------+                     +-----------------------------+
```

---

## 🧩 Componentes Principales

| Componente | Archivo | Descripción |
| :--- | :--- | :--- |
| **Gestor de Cola** | [gestor_cola.py](file:///c:/Users/HP/OneDrive/Desktop/Casos%20Judiciales/src/gestor_cola.py) | Administra la BD SQLite (`estado_casos.db`). Garantiza la transaccionalidad atómica de la cola de estados (`PENDIENTE`, `EN_PROCESO`, `COMPLETADO`, `ERROR`). |
| **Agente Explorador / Motor Web** | [agente_explorador.py](file:///c:/Users/HP/OneDrive/Desktop/Casos%20Judiciales/src/agente_explorador.py)<br>[motor_busqueda_web.py](file:///c:/Users/HP/OneDrive/Desktop/Casos%20Judiciales/src/motor_busqueda_web.py) | Módulo RPA con Playwright (Chromium) y fallback a peticiones API REST directas al e-SATJE. Automatiza la búsqueda por causa, manejo de iFrames y descarga de actuaciones procesales. |
| **Agente Extractor** | [agente_extractor.py](file:///c:/Users/HP/OneDrive/Desktop/Casos%20Judiciales/src/agente_extractor.py) | Motor de extracción offline con `BeautifulSoup` (`lxml`). Modula la clasificación procesal en 6 etapas: *Presentación/Calificación*, *Citación*, *Contestación*, *Audiencia*, *Sentencia/Ejecutoria* y *Liquidación/Embargo/Remate*. |
| **Procesador de Prompts & Filtros** | [prompt_procesador.py](file:///c:/Users/HP/OneDrive/Desktop/Casos%20Judiciales/src/prompt_procesador.py) | Infiere estados avanzados mediante reglas semánticas y la matriz de reglas definida en [Prompt_correcion_Filtro.txt](file:///c:/Users/HP/OneDrive/Desktop/Casos%20Judiciales/Prompt_correcion_Filtro.txt) y [MODULO_FILTRO_CASOS.md](file:///c:/Users/HP/OneDrive/Desktop/Casos%20Judiciales/MODULO_FILTRO_CASOS.md). |
| **Gestor de Estado y Casos** | [gestor_casos.py](file:///c:/Users/HP/OneDrive/Desktop/Casos%20Judiciales/src/gestor_casos.py)<br>[gestor_estado.py](file:///c:/Users/HP/OneDrive/Desktop/Casos%20Judiciales/src/gestor_estado.py) | Normaliza la información procesada y exporta sincronizadamente a `data/reporte_trabajo.csv` y Excel final `data/REPORTE_PROCESADO_FINAL.xlsx`. |
| **Orquestador Central** | [orquestador.py](file:///c:/Users/HP/OneDrive/Desktop/Casos%20Judiciales/src/orquestador.py)<br>[main.py](file:///c:/Users/HP/OneDrive/Desktop/Casos%20Judiciales/main.py) | Punto de entrada del flujo. Controla el ciclo de vida del bot, reintentos automáticos y soporte para reanudación por número de causa. |
| **Adaptador Antigravity** | [antigravity_adapter.py](file:///c:/Users/HP/OneDrive/Desktop/Casos%20Judiciales/src/antigravity_adapter.py) | Puerta de enlace de compatibilidad para ejecución e integración con la suite Antigravity IDE. |
| **Auditoría y Purga** | [auditor.py](file:///c:/Users/HP/OneDrive/Desktop/Casos%20Judiciales/src/auditor.py)<br>[limpieza.py](file:///c:/Users/HP/OneDrive/Desktop/Casos%20Judiciales/src/limpieza.py) | Valida la integridad del total de casos procesados y permite purgar archivos HTML temporales conservando la base de datos. |

---

## 📂 Estructura del Proyecto

```
Casos Judiciales/
├── config.json                       # Configuración activa del sistema (filtros, rutas, URLs)
├── main.py                           # Punto de entrada interactivo y CLI
├── migracion_db.py                   # Script de migración y estructuración de estado_casos.db
├── Prompt_correcion_Filtro.txt       # Prompt y matriz de reglas para clasificación procesal
├── MODULO_FILTRO_CASOS.md            # Especificación detallada de las 6 etapas del filtro procesal
├── test_inferencia_casos.py          # Herramienta interactiva para prueba de inferencia de causas
├── requirements.txt                  # Dependencias de Python
├── config/
│   └── extraction_keywords.yml       # Palabras clave y heurísticas en YAML
├── src/
│   ├── agente_explorador.py          # RPA de exploración y descargas
│   ├── agente_extractor.py           # Parser HTML y motor de clasificaciónprocesal
│   ├── antigravity_adapter.py        # Adaptador de integración Antigravity
│   ├── auditor.py                    # Auditor de integridad de lote
│   ├── gestor_casos.py               # Manipulación y persistencia de casos
│   ├── gestor_cola.py                # Motor SQLite de la cola de trabajo
│   ├── gestor_estado.py              # Exportación y consolidación en CSV/Excel
│   ├── limpieza.py                   # Script de purga de archivos temporales
│   ├── logger_config.py              # Configuración global de logs
│   ├── motor_busqueda_web.py         # Control de Playwright y peticiones API e-SATJE
│   ├── orquestador.py                # Orquestador del ciclo de trabajo masivo
│   └── prompt_procesador.py          # Módulo de inferencia y procesamiento de prompts
├── tests/
│   ├── test_clasificacion_arbol.py   # Pruebas unitarias del árbol de decisión procesal
│   ├── test_extraccion_api.py        # Pruebas de integración con la API del e-SATJE
│   ├── test_extraccion_integration.py# Pruebas end-to-end de extracción HTML
│   ├── test_migracion.py             # Pruebas del esquema y migración SQLite
│   └── test_prompt_procesador.py     # Pruebas de la lógica del procesador de prompts
└── scripts/
    ├── analyze_api.py                # Diagnóstico de respuestas JSON de la API
    ├── analyze_latest_html.py        # Inspección rápida del último HTML descargado
    ├── persist_and_advance.py        # Guardado forzado y avance en la cola
    ├── reset_db.py                   # Reinicio y desbloqueo masivo de registros en la DB
    └── run_bot_api.py                # Ejecución de prueba por API
```

---

## ⚙️ Configuración (`config.json`)

El archivo [config.json](file:///c:/Users/HP/OneDrive/Desktop/Casos%20Judiciales/config.json) define los parámetros de ejecución:

```json
{
    "filtros_activos": {
        "sucursal": "LOS RIOS",
        "oficina": "",
        "estado_judicial": "ACTIVO",
        "columna_estado_judicial": "ESTADO.1",
        "inicio_desde_juicio": "23331-2022-04261"
    },
    "rutas": {
        "archivo_csv": "data/reporte_trabajo.csv",
        "archivo_origen": "data/REPORTE JUICIOS PARA REVISIÓN JULIO.xlsx",
        "archivo_excel_final": "data/REPORTE_PROCESADO_FINAL.xlsx",
        "hoja_lectura": "migrado"
    },
    "navegacion": {
        "url_portal": "https://procesosjudiciales.funcionjudicial.gob.ec/busqueda-filtros"
    },
    "sistema": {
        "intervalo_autoguardado": 5
    },
    "auditoria": {
        "total_esperado": 4017
    }
}
```

---

## 💻 Requisitos Previos e Instalación

### Requisitos del Sistema
- Python **3.10** o superior
- Git
- Navegador Chromium (gestionado por Playwright)

### Paso a Paso de Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/Jusfravs/Automatizar_Sistema_Judicial.git
   cd "Casos Judiciales"
   ```

2. **Crear e instalar el entorno virtual:**
   ```bash
   python -m venv .venv
   
   # En Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   ```

3. **Instalar dependencias de Python:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Instalar los binarios de Playwright:**
   ```bash
   python -m playwright install chromium
   ```

---

## 🚀 Guía de Ejecución

### 1. Migración e Inicialización de la Base de Datos (Primer uso)
Antes de lanzar el orquestador o tras realizar actualizaciones de estructura en SQLite:
```bash
python migracion_db.py
```
*Crea backups automáticos, genera las tablas `juicios`, `resultados_expediente` y `eventos_extraccion`, y recupera registros que hayan quedado bloqueados en estado `EN_PROCESO`.*

### 2. Ejecución Principal asistida / CLI
Para iniciar la ejecución interactiva o reanudar el bot:
```bash
python main.py
```

Para reanudar directamente desde un número de juicio específico:
```bash
python main.py 23331-2022-04261
```

### 3. Ejecución Desatendida / Orquestador Masivo
Para ejecutar en segundo plano con control total de reintentos:
```bash
python -m src.orquestador
```

### 4. Prueba Interactiva de Inferencia de Casos
Para probar cómo clasifica el sistema el expediente de un juicio en particular:
```bash
python test_inferencia_casos.py
```

### 5. Auditoría de Integridad del Lote
Para verificar el avance frente a las 4,017 causas esperadas:
```bash
python -m src.auditor
```

### 6. Purga de Temporales
Para eliminar archivos HTML descargados conservando la base de datos `estado_casos.db`:
```bash
python -m src.limpieza
```

---

## 🧪 Suite de Pruebas Unitarias e Integración (`pytest`)

El proyecto incluye pruebas automatizadas con `pytest`:

```bash
# Ejecutar todas las pruebas
pytest

# Probar la clasificación del árbol procesal
pytest tests/test_clasificacion_arbol.py

# Probar la integración de extracción HTML
pytest tests/test_extraccion_integration.py

# Probar la integración con la API REST del e-SATJE
pytest tests/test_extraccion_api.py

# Probar la migración y estructura SQLite
pytest tests/test_migracion.py

# Probar el procesador de prompts y reglas
pytest tests/test_prompt_procesador.py
```

---

## 🛠️ Herramientas de Mantenimiento (`scripts/`)

- **Reiniciar estados en la BD:**
  ```bash
  python scripts/reset_db.py
  ```
- **Persistir datos y avanzar cola:**
  ```bash
  python scripts/persist_and_advance.py
  ```
- **Análisis de respuestas API / HTML:**
  ```bash
  python scripts/analyze_api.py
  python scripts/analyze_latest_html.py
  ```

---

## 📊 Archivos de Salida y Registros

- **Base de Datos Principal:** `estado_casos.db` (SQLite)
- **Reporte CSV de Trabajo:** `data/reporte_trabajo.csv`
- **Reporte Excel Final:** `data/REPORTE_PROCESADO_FINAL.xlsx`
- **Casos Fallidos:** `data/casos_fallidos.txt`
- **Log de Ejecución:** `ejecucion_produccion.log`
