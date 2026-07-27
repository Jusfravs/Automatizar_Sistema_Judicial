# src/agente_extractor.py
import os
import re
import unicodedata
from bs4 import BeautifulSoup
from src.logger_config import obtener_logger

logger = obtener_logger("AgenteExtractor")


def normalizar_texto(texto):
    """
    Normaliza texto removiendo tildes, caracteres especiales y convirtiendo a mayúsculas.
    """
    if not texto:
        return ""
    texto = unicodedata.normalize('NFD', str(texto))
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto.upper().strip()


class NavegadorArbolContenido:
    """
    Navegador estructural del árbol procesal y de contenido.
    Implementa la regla de navegación jerárquica:
    - Si no hay resultados en el nivel actual -> Retrocede / Sube un nivel para buscar en contexto padre.
    - Si hay resultados en el nivel actual -> Avanza / Baja un nivel para profundizar en detalles.
    """
    def __init__(self):
        self.nivel_actual = 2  # Nivel inicial: Inspección profunda de contenido
        self.historial_niveles = []

    def subir_nivel(self, motivo=""):
        """Sube un nivel en el árbol jerárquico (de detalle a resumen padre)."""
        if self.nivel_actual > 0:
            self.nivel_actual -= 1
            logger.info(f"[ÁRBOL NAV] Sin resultados en nivel actual -> Subiendo al Nivel {self.nivel_actual} ({motivo})")
        return self.nivel_actual

    def bajar_nivel(self, motivo=""):
        """Baja un nivel en el árbol jerárquico (de resumen a profundización de detalles)."""
        if self.nivel_actual < 3:
            self.nivel_actual += 1
            logger.info(f"[ÁRBOL NAV] Coincidencias encontradas -> Bajando al Nivel {self.nivel_actual} ({motivo})")
        return self.nivel_actual


class AgenteExtractor:
    """
    Agente Extractor Offline: Parseador semántico de archivos HTML locales con BeautifulSoup.
    Realiza búsqueda por similitud semántica y navegación jerárquica en el árbol de información.
    """
    DICCIONARIO_SEMANTICO = [
        # (Etapa, Fase, Lista de términos/patrones semánticos)
        (
            "6 LIQUIDACION Y EMBARGO", "6.5 CONGELAMIENTO DE CUENTAS",
            ["CONGELAMIENTO", "RETENCION DE CUENTAS", "RETENCION", "BLOQUEO DE CUENTAS", "OFICIO RETENCION", "MEDIDA CAUTELAR BANCARIA"]
        ),
        (
            "6 LIQUIDACION Y EMBARGO", "6.4 REMATE",
            ["REMATE", "SUBASTA", "POSTURA", "CONVOCATORIA A REMATE", "AVALUO DE BIEN"]
        ),
        (
            "6 LIQUIDACION Y EMBARGO", "6.3 EMBARGO",
            ["EMBARGO", "DESPOSEIMIENTO", "RETENCION DE VEHICULO", "INSCRIBIR EMBARGO", "APREHENSION"]
        ),
        (
            "6 LIQUIDACION Y EMBARGO", "6.2 MANDAMIENTO DE EJECUCION",
            ["MANDAMIENTO", "MANDAMIENTO DE EJECUCION", "AUTO DE EJECUCION", "ORDEN DE PAGO", "CUMPLASE SENTENCIA"]
        ),
        (
            "6 LIQUIDACION Y EMBARGO", "6.1 LIQUIDACION PERITO LIQUIDADOR",
            ["LIQUIDADOR", "LIQUIDACION", "PERITO LIQUIDADOR", "INFORME DE LIQUIDACION", "LIQUIDACION DE CAPITAL E INTERESES"]
        ),
        (
            "5 SENTENCIA", "5.3 SENTENCIA EJECUTORIADA",
            ["EJECUTORIA", "EJECUTORIADA", "SENTENCIA EJECUTORIADA", "CAUSA ESTADO", "AUTO FIRME", "SENTENCIA EN FIRME"]
        ),
        (
            "5 SENTENCIA", "5.2 APELACION",
            ["APELACION", "RECURSO DE APELACION", "ALZADA", "CONCEDE RECURSO", "CORTE PROVINCIAL"]
        ),
        (
            "5 SENTENCIA", "5.1 SENTENCIA EMITIDA POR EL JUEZ",
            ["SENTENCIA", "FALLO", "RESOLUCION", "JUEZ RESUELVE", "ACEPTA LA DEMANDA", "DECLARA CON LUGAR", "SENTENCIA ORAL"]
        ),
        (
            "4 AUDIENCIA", "4.2 AUDIENCIA",
            ["AUDIENCIA", "AUDIENCIA PRELIMINAR", "AUDIENCIA DE JUICIO", "ACTA DE AUDIENCIA", "INSTALACION DE AUDIENCIA", "DILIGENCIA DE AUDIENCIA"]
        ),
        (
            "4 AUDIENCIA", "4.1 FIJACION FECHA AUDIENCIA",
            ["FIJACION", "SEÑALA AUDIENCIA", "CONVOCA A AUDIENCIA", "SEÑALAMIENTO DE AUDIENCIA", "FECHA AUDIENCIA", "DILIGENCIA DE AUDIENCIA PARA EL"]
        ),
        (
            "3 CONTESTACION", "3.1 CONTESTACION",
            ["CONTESTACION", "CONTESTA", "EXCEPCIONES", "ALLANAMIENTO", "RESPONDE DEMANDA", "ESCRITO DE CONTESTACION"]
        ),
        (
            "2 CITACION", "2.2 CITACION POR PRENSA",
            ["PRENSA", "CITACION POR PRENSA", "DIARIO", "PERIÓDICO", "PUBLICACIÓN DE CITACIÓN", "EXTRACTO DE CITACIÓN"]
        ),
        (
            "2 CITACION", "2.1 CITACION",
            [
                "CITACION", "CITAR", "CITADO", "CITESE", "BOLETA", "BOLETAS",
                "RAZON DE CITACION", "DILIGENCIA DE CITACION", "ACTA DE CITACION",
                "NOTIFICACION DE DEMANDA", "OFICIO DE CITACION", "CITAR AL DEMANDADO",
                "SE CITA", "NOTIFICAR", "NOTIFIQUESE", "BOLETA DE CITACION"
            ]
        ),
        (
            "1 PRESENTACION Y CALIFICACION", "1.3 CALIFICACION",
            ["CALIFICACION", "CALIFICA", "CALIFICADA", "AUTO INICIAL", "ADMITIDA", "ADMITE", "ACEPTA A TRAMITE", "CALIFICA LA DEMANDA"]
        ),
        (
            "1 PRESENTACION Y CALIFICACION", "1.1 PRESENTAR DEMANDA",
            ["DEMANDA", "PRESENTACION", "INGRESO DE CAUSA", "SORTEO", "INGRESO DEMANDA"]
        )
    ]

    def evaluar_similitud_semantica(self, texto):
        """
        Evalúa el texto de una actuación buscando coincidencia semántica flexible
        con los conceptos del árbol procesal.
        Retorna (Etapa, Fase, Confianza) o (None, None, 0.0)
        """
        texto_norm = normalizar_texto(texto)
        if not texto_norm:
            return None, None, 0.0

        for etapa, fase, terminos in self.DICCIONARIO_SEMANTICO:
            for term in terminos:
                term_norm = normalizar_texto(term)
                # 1. Coincidencia exacta o contenida
                if term_norm in texto_norm:
                    return etapa, fase, 1.0

                # 2. Coincidencia semántica flexible por palabras clave raíz (Stemming heurístico)
                palabras_term = [p for p in term_norm.split() if len(p) > 3]
                if palabras_term:
                    coincidencias = sum(1 for p in palabras_term if p in texto_norm)
                    ratio = coincidencias / len(palabras_term)
                    if ratio >= 0.7:
                        return etapa, fase, round(ratio, 2)

        return None, None, 0.0

    def procesar_archivo_html(self, ruta_html):
        """
        Analiza todo el contenido del archivo HTML local aplicando navegación en árbol
        y coincidencia por similitud semántica.
        """
        resultado = {
            "FECHA INICIO JUICIO": None,
            "FECHA INICIAL FASE ACTUAL": None,
            "ETAPA_PROCESAL": None,
            "FASE_PROCESAL": None,
            "HISTORIAL_ACTUACIONES": []
        }

        if not os.path.exists(ruta_html):
            logger.error(f"No existe el archivo: {ruta_html}")
            return resultado

        nav_arbol = NavegadorArbolContenido()

        try:
            with open(ruta_html, "r", encoding="utf-8", errors="ignore") as f:
                contenido_html = f.read()

            try:
                soup = BeautifulSoup(contenido_html, "lxml")
            except Exception:
                soup = BeautifulSoup(contenido_html, "html.parser")

            # --- NIVEL 2: Inspección Profunda de Actuaciones y Tablas ---
            actuaciones = self._extraer_actuaciones_profundas(soup)

            if actuaciones:
                nav_arbol.bajar_nivel("Actuaciones encontradas en Nivel 2")
            else:
                nav_arbol.subir_nivel("Sin actuaciones estructuradas en Nivel 2. Subiendo a Nivel 1 (Escaneo Global)")
                actuaciones = self._extraer_actuaciones_texto_plano(soup)

            resultado["HISTORIAL_ACTUACIONES"] = actuaciones

            # Extracción de Fecha de Inicio
            fecha_inicio = self._extraer_fecha_inicio(soup, actuaciones)
            resultado["FECHA INICIO JUICIO"] = fecha_inicio

            # --- BÚSQUEDA POR SIMILITUD SEMÁNTICA EN EL ÁRBOL DE CONTENIDO ---
            etapa_hallada, fase_hallada, fecha_hallada = self._evaluar_arbol_semantico(actuaciones, nav_arbol, soup)

            if etapa_hallada:
                resultado["ETAPA_PROCESAL"] = etapa_hallada
                resultado["FASE_PROCESAL"] = fase_hallada
                resultado["FECHA INICIAL FASE ACTUAL"] = fecha_hallada
            elif actuaciones:
                # Fallback contextual si no hubo match directo pero hay actuaciones
                resultado["FECHA INICIAL FASE ACTUAL"] = actuaciones[0]["fecha"]
                resultado["ETAPA_PROCESAL"] = "ESTADO DESCONOCIDO"
                resultado["FASE_PROCESAL"] = actuaciones[0]["detalle"][:100]

            return resultado

        except Exception as e:
            logger.error(f"Error al procesar {ruta_html}: {e}")
            return resultado

    def _extraer_actuaciones_profundas(self, soup):
        """Extrae elementos de tabla o contenedores con estructura detallada."""
        actuaciones = []
        filas = soup.find_all(["tr", "mat-row", "div"])

        for fila in filas:
            cols = fila.find_all(["td", "th", "div", "span"])
            textos = [c.get_text(strip=True) for c in cols if c.get_text(strip=True)]
            if not textos:
                continue

            texto_completo = " ".join(textos)
            m_f = re.search(r'\d{2}/\d{2}/\d{4}', texto_completo)
            if m_f:
                fecha_act = m_f.group(0)
                # Limpiar la fecha del detalle
                detalle_act = re.sub(r'\d{2}/\d{2}/\d{4}(\s+\d{2}:\d{2})?', '', texto_completo).strip()
                if len(detalle_act) > 3 and not any(ign in detalle_act.upper() for ign in ["BUSQUEDA", "PAGINA", "FECHA INGRESO"]):
                    actuaciones.append({"fecha": fecha_act, "detalle": detalle_act.upper()})

        # Eliminar duplicados manteniendo orden
        vistas = set()
        actuaciones_unicas = []
        for act in actuaciones:
            clave = (act["fecha"], act["detalle"][:50])
            if clave not in vistas:
                vistas.add(clave)
                actuaciones_unicas.append(act)

        return actuaciones_unicas

    def _extraer_actuaciones_texto_plano(self, soup):
        """Escaneo alternativo en bloques de texto cuando falla la estructura de tablas."""
        actuaciones = []
        texto_pagina = soup.get_text("\n", strip=True)
        lineas = [l.strip() for l in texto_pagina.split("\n") if l.strip()]

        for idx, line in enumerate(lineas):
            m_f = re.search(r'(\d{2}/\d{2}/\d{4})', line)
            if m_f:
                fecha_act = m_f.group(1)
                linea_limpia = re.sub(r'\d{2}/\d{2}/\d{4}(\s+\d{2}:\d{2})?', '', line).strip()
                if len(linea_limpia) > 3:
                    detalle_act = linea_limpia.upper()
                elif (idx + 1) < len(lineas):
                    detalle_act = lineas[idx + 1].upper()
                else:
                    detalle_act = ""

                if not any(ign in detalle_act for ign in ["FECHA DE INGRESO", "BUSQUEDA", "CONSULTA"]):
                    actuaciones.append({"fecha": fecha_act, "detalle": detalle_act})

        return actuaciones

    def _extraer_fecha_inicio(self, soup, actuaciones):
        """Busca la fecha de inicio del juicio en encabezados o como fallback en la actuación más antigua."""
        for elem in soup.find_all(text=re.compile(r"Fecha de ingreso|Fecha ingreso|Fecha presentación|Fecha inicio", re.IGNORECASE)):
            parent_text = elem.parent.get_text(strip=True) if elem.parent else str(elem)
            m = re.search(r'\d{2}/\d{2}/\d{4}', parent_text)
            if m:
                return m.group(0)

        if actuaciones:
            return actuaciones[-1]["fecha"]
        return None

    def _evaluar_arbol_semantico(self, actuaciones, nav_arbol, soup):
        """
        Navega jerárquicamente por el contenido evaluando la similitud semántica.
        - Si encuentra coincidencia en actuaciones (Nivel 2/1): baja un nivel y retorna el detalle más relevante.
        - Si no encuentra en actuaciones: sube un nivel (Nivel 0) y escanea el texto global del documento HTML.
        """
        # 1. Evaluar actuaciones en orden cronológico inverso (la más reciente primero)
        for act in actuaciones:
            etapa, fase, score = self.evaluar_similitud_semantica(act["detalle"])
            if etapa and score >= 0.7:
                nav_arbol.bajar_nivel(f"Coincidencia semántica '{fase}' (Score: {score}) en actuación del {act['fecha']}")
                return etapa, fase, act["fecha"]

        # 2. Si no hubo coincidencia en actuaciones -> Subir un nivel en el árbol para evaluar el HTML global
        nav_arbol.subir_nivel("Sin coincidencia semántica en lista de actuaciones. Escaneando DOM global (Nivel 0)")
        texto_global = soup.get_text(" ", strip=True)
        etapa_g, fase_g, score_g = self.evaluar_similitud_semantica(texto_global)

        if etapa_g and score_g >= 0.7:
            fecha_ref = actuaciones[0]["fecha"] if actuaciones else None
            return etapa_g, fase_g, fecha_ref

        return None, None, None
