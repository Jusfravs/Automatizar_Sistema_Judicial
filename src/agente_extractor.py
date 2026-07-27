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
    Implementa la regla de navegación jerárquica estricta:
    - Escalada por Ausencia (Move Up): Si el contenido del nodo actual no guarda relación semántica,
      sube un nivel (directorio padre) para buscar en un contexto más amplio.
    - Profundización por Hallazgo (Move Down): Si encuentra información que coincide con una fase principal,
      baja un nivel (directorio hijo/subcarpeta) para determinar la sub-fase específica exacta.
    """
    def __init__(self):
        self.nivel_actual = 2  # Nivel inicial: Inspección profunda de contenido / actuaciones

    def subir_nivel(self, motivo=""):
        """Move Up: Escalada por ausencia hacia un contexto más amplio."""
        if self.nivel_actual > 0:
            self.nivel_actual -= 1
            logger.info(f"[ÁRBOL NAV] [MOVE UP] Escalada por ausencia -> Subiendo al Nivel {self.nivel_actual} ({motivo})")
        return self.nivel_actual

    def bajar_nivel(self, motivo=""):
        """Move Down: Profundización por hallazgo hacia sub-fase específica."""
        if self.nivel_actual < 3:
            self.nivel_actual += 1
            logger.info(f"[ÁRBOL NAV] [MOVE DOWN] Profundización por hallazgo -> Bajando al Nivel {self.nivel_actual} ({motivo})")
        return self.nivel_actual


class AgenteExtractor:
    """
    Agente Extractor Semántico Adaptativo (e-SATJE).
    Analiza el contenido completo de expedientes judiciales basándose en la taxonomía de 6 fases y sus sub-fases.
    Aplica coincidencia por similitud semántica y navegación dinámica en árbol (Move Up / Move Down).
    """
    TAXONOMIA_COMPLETA = [
        # Fase 6: LIQUIDACION Y EMBARGO
        (
            "6 LIQUIDACION Y EMBARGO", "6.5 CONGELAMIENTO DE CUENTAS",
            [
                "CONGELAMIENTO", "CONGELAMIENTO DE CUENTAS", "RETENCION DE CUENTAS",
                "BLOQUEO DE CUENTAS", "OFICIO RETENCION", "MEDIDA CAUTELAR BANCARIA",
                "RETENCION BANCARIA", "INMOVILIZACION DE FONDOS"
            ]
        ),
        (
            "6 LIQUIDACION Y EMBARGO", "6.4 REMATE",
            [
                "REMATE", "SUBASTA", "POSTURA", "CONVOCATORIA A REMATE",
                "AVALUO DE BIEN", "FECHA DE REMATE", "OFERTA DE REMATE"
            ]
        ),
        (
            "6 LIQUIDACION Y EMBARGO", "6.3 EMBARGO",
            [
                "EMBARGO", "DESPOSEIMIENTO", "RETENCION DE BIEN", "RETENCION DE BIENES",
                "SECUESTRO DE ACTIVOS", "SECUESTRO DE BIENES", "INSCRIBIR EMBARGO",
                "APREHENSION", "RETENCION DE VEHICULO", "ACTA DE EMBARGO"
            ]
        ),
        (
            "6 LIQUIDACION Y EMBARGO", "6.2 MANDAMIENTO DE EJECUCION",
            [
                "MANDAMIENTO DE EJECUCION", "MANDAMIENTO", "AUTO DE EJECUCION",
                "ORDEN DE PAGO", "CUMPLASE SENTENCIA", "NOTIFICACION DE MANDAMIENTO",
                "REQUERIMIENTO DE PAGO"
            ]
        ),
        (
            "6 LIQUIDACION Y EMBARGO", "6.1 LIQUIDACION PERITO LIQUIDADOR",
            [
                "LIQUIDACION PERITO LIQUIDADOR", "LIQUIDADOR", "LIQUIDACION",
                "PERITO LIQUIDADOR", "INFORME DE LIQUIDACION",
                "LIQUIDACION DE CAPITAL E INTERESES", "INFORME PERICIAL DE LIQUIDACION"
            ]
        ),

        # Fase 5: SENTENCIA
        (
            "5 SENTENCIA", "5.3 SENTENCIA EJECUTORIADA",
            [
                "SENTENCIA EJECUTORIADA", "EJECUTORIA", "EJECUTORIADA",
                "CAUSA ESTADO", "AUTO FIRME", "SENTENCIA EN FIRME",
                "CERTIFICO EJECUTORIA", "RAZON DE EJECUTORIA"
            ]
        ),
        (
            "5 SENTENCIA", "5.2 APELACION",
            [
                "APELACION", "RECURSO DE APELACION", "ALZADA", "CONCEDE RECURSO",
                "CORTE PROVINCIAL", "FUNDAMENTACION DE APELACION", "ELEVA ALZADA"
            ]
        ),
        (
            "5 SENTENCIA", "5.1 SENTENCIA EMITIDA POR EL JUEZ",
            [
                "SENTENCIA EMITIDA POR EL JUEZ", "SENTENCIA", "FALLO", "RESOLUCION",
                "JUEZ RESUELVE", "ACEPTA LA DEMANDA", "DECLARA CON LUGAR",
                "SENTENCIA ORAL", "DICTAMEN JUDICIAL"
            ]
        ),

        # Fase 4: AUDIENCIA
        (
            "4 AUDIENCIA", "4.2 AUDIENCIA",
            [
                "AUDIENCIA", "AUDIENCIA PRELIMINAR", "AUDIENCIA DE JUICIO",
                "ACTA DE AUDIENCIA", "INSTALACION DE AUDIENCIA",
                "DILIGENCIA DE AUDIENCIA", "DESARROLLO DE AUDIENCIA"
            ]
        ),
        (
            "4 AUDIENCIA", "4.1 FIJACION FECHA AUDIENCIA",
            [
                "FIJACION FECHA AUDIENCIA", "FIJACION", "SEÑALA AUDIENCIA",
                "CONVOCA A AUDIENCIA", "SEÑALAMIENTO DE AUDIENCIA", "FECHA AUDIENCIA",
                "DILIGENCIA DE AUDIENCIA PARA EL", "CONVOCATORIA A AUDIENCIA"
            ]
        ),

        # Fase 3: CONTESTACION
        (
            "3 CONTESTACION", "3.1 CONTESTACION",
            [
                "CONTESTACION", "CONTESTA", "EXCEPCIONES", "ALLANAMIENTO",
                "RESPONDE DEMANDA", "ESCRITO DE CONTESTACION", "OPONE EXCEPCIONES"
            ]
        ),

        # Fase 2: CITACION
        (
            "2 CITACION", "2.2 CITACION POR PRENSA",
            [
                "CITACION POR PRENSA", "PRENSA", "DIARIO", "PERIÓDICO",
                "PUBLICACIÓN DE CITACIÓN", "EXTRACTO DE CITACIÓN", "PUBLICACION PRENSA"
            ]
        ),
        (
            "2 CITACION", "2.1 CITACION",
            [
                "CITACION", "CITAR", "CITADO", "CITESE", "BOLETA", "BOLETAS",
                "RAZON DE CITACION", "DILIGENCIA DE CITACION", "ACTA DE CITACION",
                "NOTIFICACION DE DEMANDA", "OFICIO DE CITACION", "CITAR AL DEMANDADO",
                "SE CITA", "NOTIFICAR", "NOTIFIQUESE", "BOLETA DE CITACION",
                "DILIGENCIA DE NOTIFICACIÓN"
            ]
        ),

        # Fase 1: PRESENTACION Y CALIFICACION
        (
            "1 PRESENTACION Y CALIFICACION", "1.3 CALIFICACION",
            [
                "CALIFICACION", "CALIFICA", "CALIFICADA", "AUTO INICIAL",
                "ADMITIDA", "ADMITE", "ACEPTA A TRAMITE", "CALIFICA LA DEMANDA",
                "AUTO DE CALIFICACION"
            ]
        ),
        (
            "1 PRESENTACION Y CALIFICACION", "1.2 COMPLETAR",
            [
                "COMPLETAR", "COMPLETAR DEMANDA", "ACLARAR DEMANDA", "ACLARACION",
                "SUBSANAR", "MANDAR A COMPLETAR", "PREVENCION DE COMPLETAR",
                "COMPLETA DEMANDA"
            ]
        ),
        (
            "1 PRESENTACION Y CALIFICACION", "1.1 PRESENTAR DEMANDA",
            [
                "PRESENTAR DEMANDA", "DEMANDA", "PRESENTACION", "INGRESO DE CAUSA",
                "SORTEO", "INGRESO DEMANDA", "LIBELO DE DEMANDA"
            ]
        )
    ]

    def evaluar_similitud_semantica(self, texto):
        """
        Evalúa la similitud semántica del texto encontrado con la taxonomía judicial de 6 fases y sub-fases.
        Retorna (Etapa, Fase, Score) o (None, None, 0.0)
        """
        texto_norm = normalizar_texto(texto)
        if not texto_norm:
            return None, None, 0.0

        for etapa, fase, terminos in self.TAXONOMIA_COMPLETA:
            for term in terminos:
                term_norm = normalizar_texto(term)
                # 1. Coincidencia directa o contenida
                if term_norm in texto_norm:
                    return etapa, fase, 1.0

                # 2. Coincidencia semántica flexible por raíces conceptuales
                palabras_term = [p for p in term_norm.split() if len(p) > 3]
                if palabras_term:
                    coincidencias = sum(1 for p in palabras_term if p in texto_norm)
                    ratio = coincidencias / len(palabras_term)
                    if ratio >= 0.7:
                        return etapa, fase, round(ratio, 2)

        return None, None, 0.0

    def procesar_archivo_html(self, ruta_html):
        """
        Lee y procesa todo el contenido dentro del archivo/carpeta HTML aplicando la lógica de navegación
        dinámica en árbol (Move Up / Move Down) y clasificación exacta según la taxonomía.
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

            # --- PASO 1: Inspección Profunda del Nodo de Actuaciones (Nivel 2) ---
            actuaciones = self._extraer_actuaciones_profundas(soup)

            if actuaciones:
                nav_arbol.bajar_nivel("Contenido estructurado detectado -> Profundizando en actuaciones (Move Down)")
            else:
                nav_arbol.subir_nivel("Sin contenido estructurado en Nivel 2 -> Escalada por ausencia a texto plano (Move Up)")
                actuaciones = self._extraer_actuaciones_texto_plano(soup)

            resultado["HISTORIAL_ACTUACIONES"] = actuaciones

            # Extracción de Fecha de Inicio de Causa
            fecha_inicio = self._extraer_fecha_inicio(soup, actuaciones)
            resultado["FECHA INICIO JUICIO"] = fecha_inicio

            # --- PASO 2: Navegación Semántica Adaptativa en Árbol ---
            etapa_hallada, fase_hallada, fecha_hallada = self._evaluar_arbol_semantico(actuaciones, nav_arbol, soup)

            if etapa_hallada:
                resultado["ETAPA_PROCESAL"] = etapa_hallada
                resultado["FASE_PROCESAL"] = fase_hallada
                resultado["FECHA INICIAL FASE ACTUAL"] = fecha_hallada
            elif actuaciones:
                # Fallback contextual si se encontraron actuaciones pero ninguna cuadró estrictamente
                resultado["FECHA INICIAL FASE ACTUAL"] = actuaciones[0]["fecha"]
                resultado["ETAPA_PROCESAL"] = "ESTADO DESCONOCIDO"
                resultado["FASE_PROCESAL"] = actuaciones[0]["detalle"][:100]

            return resultado

        except Exception as e:
            logger.error(f"Error al procesar {ruta_html}: {e}")
            return resultado

    def _extraer_actuaciones_profundas(self, soup):
        """Extrae filas de tabla y contenedores estructurados de actuaciones."""
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
                detalle_act = re.sub(r'\d{2}/\d{2}/\d{4}(\s+\d{2}:\d{2})?', '', texto_completo).strip()
                if len(detalle_act) > 3 and not any(ign in detalle_act.upper() for ign in ["BUSQUEDA", "PAGINA", "FECHA INGRESO"]):
                    actuaciones.append({"fecha": fecha_act, "detalle": detalle_act.upper()})

        # Evitar duplicaciones manteniendo orden cronológico
        vistas = set()
        actuaciones_unicas = []
        for act in actuaciones:
            clave = (act["fecha"], act["detalle"][:50])
            if clave not in vistas:
                vistas.add(clave)
                actuaciones_unicas.append(act)

        return actuaciones_unicas

    def _extraer_actuaciones_texto_plano(self, soup):
        """Escaneo en profundidad de bloques de texto alternativo."""
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
        """Obtiene la fecha de inicio del expediente."""
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
        Ejecuta la navegación en el árbol:
        - Si en las actuaciones actuales hay hallazgo -> Move Down (profundiza a la sub-fase específica).
        - Si no hay hallazgo en las actuaciones -> Move Up (escalada por ausencia al contenido del nodo padre HTML).
        """
        # 1. Evaluar actuaciones ordenadas por fecha reciente (Nivel hijo/detalle)
        for act in actuaciones:
            etapa, fase, score = self.evaluar_similitud_semantica(act["detalle"])
            if etapa and score >= 0.7:
                nav_arbol.bajar_nivel(f"Move Down -> Mapeado exacto a '{fase}' (Score: {score}) en fecha {act['fecha']}")
                return etapa, fase, act["fecha"]

        # 2. Move Up: Escalada por ausencia si no hubo hallazgo directo en las actuaciones
        nav_arbol.subir_nivel("Move Up -> Sin hallazgo en actuaciones. Escalando a contexto global del documento (Nivel Padre)")
        texto_global = soup.get_text(" ", strip=True)
        etapa_g, fase_g, score_g = self.evaluar_similitud_semantica(texto_global)

        if etapa_g and score_g >= 0.7:
            nav_arbol.bajar_nivel(f"Move Down -> Mapeado en contexto padre a '{fase_g}' (Score: {score_g})")
            fecha_ref = actuaciones[0]["fecha"] if actuaciones else None
            return etapa_g, fase_g, fecha_ref

        return None, None, None
