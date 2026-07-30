# Automatización Sistema Judicial (e-SATJE) - Arquitectura Multi-Agente

Sistema automatizado de consulta, extracción y procesamiento masivo de información procesal desde el portal e-SATJE de la Función Judicial del Ecuador.

---

## Arquitectura del Sistema Multi-Agente

El proyecto utiliza una arquitectura desacoplada orientada a eventos y persistencia de estados para procesamiento masivo resiliente:

```
                  +-------------------------+
                  |  Base de Datos Fuente   |
                  |   (Excel / CSV 4,017)   |
                  +------------+------------+
                               |
                               v
                  +-------------------------+
                  |    src/gestor_cola.py   |
                  |     (SQLite Engine)     |
                  +------------+------------+
                               |
            +------------------+------------------+
            |                                     |
            v                                     v
+-----------------------+             +-----------------------+
| src/agente_explorador |             | src/agente_extractor  |
|  (Playwright Browser) |             |  (BS4 Offline Parser) |
+-----------+-----------+             +-----------+-----------+
            |                                     |
            +------------------+------------------+
                               |
                               v
                  +-------------------------+
                  |   src/orquestador.py    |
                  |   (Control de Ciclo)    |
                  +------------+------------+
                               |
                               v
                  +-------------------------+
                  |   src/gestor_estado.py  |
                  |  (Consolidación Pandas) |
                  +-------------------------+
```

### Componentes Principales

1. **Gestor de Cola (`src/gestor_cola.py`)**: Administra la base de datos local SQLite (`estado_casos.db`). Garantiza la transaccionalidad atómica y gestiona la cola de estados (`PENDIENTE`, `EN_PROCESO`, `COMPLETADO`, `ERROR`).
2. **Agente Explorador (`src/agente_explorador.py` / `src/motor_busqueda_web.py`)**: Módulo RPA con Playwright encargado de interactuar con el portal Angular del e-SATJE, realizar la búsqueda por causa y descargar las actuaciones procesales.
3. **Agente Extractor (`src/agente_extractor.py`)**: Motor de procesamiento en segundo plano que parsea el HTML local mediante `BeautifulSoup` (parser `lxml`) para clasificar actuaciones en el Árbol Procesal Judicial con similitud semántica de 6 fases.
4. **Gestor de Estado y Reporte (`src/gestor_estado.py` / `src/gestor_casos.py`)**: Normaliza y consolida los resultados exportando a CSV (`data/reporte_trabajo.csv`) y Excel (`data/REPORTE_PROCESADO_FINAL.xlsx`).
5. **Orquestador (`src/orquestador.py` / `main.py`)**: Punto de entrada principal que integra el ciclo completo y gestiona reintentos preventivos.
6. **Auditoría y Limpieza (`src/auditor.py`, `src/limpieza.py`)**: Módulos de aseguramiento de calidad del lote y purga de temporales.

---

## Requisitos Previos e Instalación

### Requisitos del Sistema
* Python 3.10 o superior
* Git

### Instalación de Dependencias

1. Clonar el repositorio:
   ```bash
   git clone <URL_REPOSITORIO>
   cd "Casos Judiciales"
   ```

2. Crear e instanciar el entorno virtual:
   ```bash
   python -m venv .venv
   # En Windows:
   .venv\Scripts\activate
   ```

3. Instalar las librerías de Python:
   ```bash
   pip install -r requirements.txt
   ```

4. Instalar los binarios de navegador Chromium para Playwright:
   ```bash
   python -m playwright install chromium
   ```

---

## Instrucciones de Ejecución

### 0. Migración de Base de Datos (OBLIGATORIO en primera ejecución)

Antes de ejecutar el sistema por primera vez (o si la base de datos tiene problemas), ejecutar:
```bash
python migracion_db.py
```
Esto:
- Crea un backup de `estado_casos.db`
- Crea las tablas faltantes (`resultados_expediente`, `eventos_extraccion`)
- Añade índices de rendimiento
- Recupera registros huérfanos atrapados en `EN_PROCESO`

### 1. Ejecución Principal / Orquestador en Producción

Para ejecutar el orquestador principal con interfaz asistida:
```bash
python main.py
```

Para reanudar desde un número de causa específico:
```bash
python main.py 23331-2022-04261
```

Para la ejecución en modo headless masivo:
```bash
python -m src.orquestador
```

> **Nota**: Ambos flujos ahora sincronizan sus resultados en SQLite (`estado_casos.db`) además del CSV.

### 2. Auditoría e Integridad del Lote

Para validar la integridad de los 4,017 registros procesados:
```bash
python -m src.auditor
```

### 3. Mantenimiento y Purga de Temporales

Para eliminar los archivos HTML descargados conservando la base de datos `estado_casos.db`:
```bash
python -m src.limpieza
```

---

## Registros y Auditoría

* **Log de Producción**: `ejecucion_produccion.log`
* **Base de Estado**: `estado_casos.db` (SQLite con tablas: `juicios`, `resultados_expediente`, `eventos_extraccion`)
* **Resultados Finales**: `data/reporte_trabajo.csv` / `data/REPORTE_PROCESADO_FINAL.xlsx`
* **Casos Fallidos**: `data/casos_fallidos.txt`
