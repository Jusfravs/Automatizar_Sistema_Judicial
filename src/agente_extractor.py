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


class MotorInferenciaProcesal:
    """
    Motor de Inferencia Procesal Autónoma basado en MODULO_FILTRO_CASOS.md.
    Combina coincidencia conceptual por similitud semántica con inferencia
    de reglas de negocio procesales (deducción de transiciones de estado, 
    evaluación de carátulas, oficios bancarios, cadenas periciales y citaciones).
    """

    # Jerarquía procesal ordenada de menor a mayor avance
    ORDEN_FASES = [
        "1.1 PRESENTAR DEMANDA",
        "1.2 COMPLETAR/ACLARAR DEMANDA",
        "1.3 CALIFICACION",
        "2.1 CITACION (PERSONA/BOLETA)",
        "2.2 CITACION POR PRENSA",
        "3.1 CONTESTACION",
        "4.1 FIJACION FECHA AUDIENCIA",
        "4.2 AUDIENCIA / ACTA RESUMEN",
        "4.3 ACUERDO DE MEDIACION",
        "5.1 SENTENCIA EMITIDA POR EL JUEZ",
        "5.2 APELACION",
        "5.3 SENTENCIA EJECUTORIADA",
        "6.1 LIQUIDACION PERITO LIQUIDADOR",
        "6.2 MANDAMIENTO DE EJECUCION",
        "6.3 EMBARGO",
        "6.4 REMATE",
        "6.5 CONGELAMIENTO DE CUENTAS / CIERRE"
    ]

    MAPEO_ETAPAS = {
        "1.1 PRESENTAR DEMANDA": "1 PRESENTACION Y CALIFICACION",
        "1.2 COMPLETAR/ACLARAR DEMANDA": "1 PRESENTACION Y CALIFICACION",
        "1.3 CALIFICACION": "1 PRESENTACION Y CALIFICACION",
        "2.1 CITACION (PERSONA/BOLETA)": "2 CITACION",
        "2.2 CITACION POR PRENSA": "2 CITACION",
        "3.1 CONTESTACION": "3 CONTESTACION",
        "4.1 FIJACION FECHA AUDIENCIA": "4 AUDIENCIA",
        "4.2 AUDIENCIA / ACTA RESUMEN": "4 AUDIENCIA",
        "4.3 ACUERDO DE MEDIACION": "4 AUDIENCIA",
        "5.1 SENTENCIA EMITIDA POR EL JUEZ": "5 SENTENCIA",
        "5.2 APELACION": "5 SENTENCIA",
        "5.3 SENTENCIA EJECUTORIADA": "5 SENTENCIA",
        "6.1 LIQUIDACION PERITO LIQUIDADOR": "6 LIQUIDACION Y EMBARGO",
        "6.2 MANDAMIENTO DE EJECUCION": "6 LIQUIDACION Y EMBARGO",
        "6.3 EMBARGO": "6 LIQUIDACION Y EMBARGO",
        "6.4 REMATE": "6 LIQUIDACION Y EMBARGO",
        "6.5 CONGELAMIENTO DE CUENTAS / CIERRE": "6 LIQUIDACION Y EMBARGO",
    }

    TAXONOMIA_COMPLETA = [
        # Fase 6: LIQUIDACION Y EMBARGO
        (
            "6 LIQUIDACION Y EMBARGO", "6.5 CONGELAMIENTO DE CUENTAS / CIERRE",
            [
                "CONGELAMIENTO", "CONGELAMIENTO DE CUENTAS", "RETENCION DE CUENTAS",
                "BLOQUEO DE CUENTAS", "OFICIO RETENCION", "MEDIDA CAUTELAR BANCARIA",
                "RETENCION BANCARIA", "INMOVILIZACION DE FONDOS",
                "SUPERINTENDENCIA DE BANCOS", "OFICIO EMITIDO POR EL BANCO",
                "OFICIO EMITIDO POR BANCO", "AGREGUESE EL OFICIO EMITIDO POR EL BANCO",
                "AGREGUESE OFICIO EMITIDO POR EL BANCO", "OFICIO BANCO", "CIERRE DE PROCESO BANCARIO"
            ]
        ),
        (
            "6 LIQUIDACION Y EMBARGO", "6.4 REMATE",
            [
                "REMATE", "SUBASTA", "POSTURA", "CONVOCATORIA A REMATE",
                "AVALUO DE BIEN", "FECHA DE REMATE", "OFERTA DE REMATE",
                "PUBLICACION REMATE", "FECHA DE PUBLICACION REMATE"
            ]
        ),
        (
            "6 LIQUIDACION Y EMBARGO", "6.3 EMBARGO",
            [
                "EMBARGO", "DESPOSEIMIENTO", "RETENCION DE BIEN", "RETENCION DE BIENES",
                "SECUESTRO DE ACTIVOS", "SECUESTRO DE BIENES", "INSCRIBIR EMBARGO",
                "APREHENSION", "RETENCION DE VEHICULO", "ACTA DE EMBARGO",
                "EMBARGAR BIENES", "EMBARGAR SERVICIOS"
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
                "LIQUIDACION DE CAPITAL E INTERESES", "INFORME PERICIAL DE LIQUIDACION",
                "NOMBRAMIENTO DE PERITO", "INFORME DEL PERITO"
            ]
        ),

        # Fase 5: SENTENCIA
        (
            "5 SENTENCIA", "5.3 SENTENCIA EJECUTORIADA",
            [
                "SENTENCIA EJECUTORIADA", "EJECUTORIA", "EJECUTORIADA",
                "CAUSA ESTADO", "AUTO FIRME", "SENTENCIA EN FIRME",
                "CERTIFICO EJECUTORIA", "RAZON DE EJECUTORIA", "RAZON DE EJECUTORIADA"
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
            "4 AUDIENCIA", "4.3 ACUERDO DE MEDIACION",
            [
                "ACUERDO DE MEDIACION", "MEDIACION", "ACTA DE MEDIACION",
                "CENTRO DE MEDIACION", "CONCILIACION DE MEDIACION"
            ]
        ),
        (
            "4 AUDIENCIA", "4.2 AUDIENCIA / ACTA RESUMEN",
            [
                "ACTA RESUMEN", "ACTA DE AUDIENCIA", "AUDIENCIA PRELIMINAR",
                "AUDIENCIA DE JUICIO", "INSTALACION DE AUDIENCIA",
                "DILIGENCIA DE AUDIENCIA", "DESARROLLO DE AUDIENCIA",
                "ACTA RESUMEN DE AUDIENCIA", "AUDIENCIA CELEBRADA"
            ]
        ),
        (
            "4 AUDIENCIA", "4.1 FIJACION FECHA AUDIENCIA",
            [
                "FIJACION FECHA AUDIENCIA", "FIJACION", "SEÑALA AUDIENCIA",
                "CONVOCA A AUDIENCIA", "SEÑALAMIENTO DE AUDIENCIA", "FECHA AUDIENCIA",
                "DILIGENCIA DE AUDIENCIA PARA EL", "CONVOCATORIA A AUDIENCIA",
                "SUSPENCION Y NUEVO SEÑALAMIENTO DE AUDIENCIA",
                "SUSPENSION Y NUEVO SEÑALAMIENTO", "NUEVA FECHA AUDIENCIA",
                "REPROGRAMACION AUDIENCIA", "CALIFICACION DE LA CONTESTACION Y CONVOCATORIA"
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
                "PUBLICACIÓN DE CITACIÓN", "EXTRACTO DE CITACIÓN", "PUBLICACION PRENSA",
                "OFICIO PRENSA", "EDICTO"
            ]
        ),
        (
            "2 CITACION", "2.1 CITACION (PERSONA/BOLETA)",
            [
                "CITACION", "CITAR", "CITADO", "CITESE", "BOLETA", "BOLETAS",
                "BOLETA FIJADA", "RAZON DE CITACION", "DILIGENCIA DE CITACION",
                "ACTA DE CITACION", "NOTIFICACION DE DEMANDA", "OFICIO DE CITACION",
                "CITAR AL DEMANDADO", "SE CITA", "NOTIFICAR", "NOTIFIQUESE",
                "BOLETA DE CITACION", "DILIGENCIA DE NOTIFICACIÓN", "CITACION REALIZADA"
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
            "1 PRESENTACION Y CALIFICACION", "1.2 COMPLETAR/ACLARAR DEMANDA",
            [
                "COMPLETAR", "COMPLETAR DEMANDA", "ACLARAR DEMANDA", "ACLARACION",
                "SUBSANAR", "MANDAR A COMPLETAR", "PREVENCION DE COMPLETAR",
                "COMPLETA DEMANDA", "COMPLETAR Y/O ACLARAR"
            ]
        ),
        (
            "1 PRESENTACION Y CALIFICACION", "1.1 PRESENTAR DEMANDA",
            [
                "PRESENTAR DEMANDA", "DEMANDA", "PRESENTACION", "INGRESO DE CAUSA",
                "SORTEO", "INGRESO DEMANDA", "LIBELO DE DEMANDA", "CARATULA DE JUICIO",
                "CARATULA"
            ]
        )
    ]

    @classmethod
    def obtener_indice_fase(cls, fase):
        """Retorna la posición jerárquica de una fase."""
        for idx, f in enumerate(cls.ORDEN_FASES):
            if f in fase or fase in f:
                return idx
        return -1

    @classmethod
    def inferir_estado_procesal(cls, actuaciones, texto_global=""):
        """
        Analiza las actuaciones procesales cronológicamente aplicando las reglas de autonomía
        e inferencia de MODULO_FILTRO_CASOS.md.
        
        Reglas de Inferencia Implementadas:
        1. Carátula de Juicio -> Si no hay auto de calificación aún, la primera actuación o carátula 
           se infiere como PRESENTAR DEMANDA.
        2. Citación por prensa vs persona -> Inspección de boletines, extractos o prensa.
        3. Contestación con Calificación/Convocatoria -> Salto automático e inferencia directa a FIJACION FECHA AUDIENCIA.
        4. Nombramiento de Perito -> Informe perito liquidador en cadena de liquidación.
        5. Oficios Bancarios / Superintendencia de Bancos -> Inferencia de CONGELAMIENTO DE CUENTAS / CIERRE.
        6. Selección del hito más avanzado según jerarquía procesal.
        """
        if not actuaciones and not texto_global:
            return None, None, None

        hallazgos = []  # Lista de dicts: {"etapa": ..., "fase": ..., "fecha": ..., "prioridad": ...}
        tiene_calificacion_demanda = False
        tiene_contestacion = False
        tiene_calificacion_contestacion = False
        tiene_nombramiento_perito = False
        tiene_embargo = False

        # 1. Escaneo preliminar para flags contextuales de la causa
        for act in actuaciones:
            detalle = act.get("detalle", "")
            norm = normalizar_texto(detalle)

            if any(k in norm for k in ["CALIFICACION LA DEMANDA", "CALIFICA LA DEMANDA", "AUTO DE CALIFICACION", "AUTO INICIAL", "ACEPTA A TRAMITE"]):
                tiene_calificacion_demanda = True

            if any(k in norm for k in ["CONTESTACION", "RESPONDE DEMANDA", "EXCEPCIONES", "ALLANAMIENTO"]):
                tiene_contestacion = True

            if tiene_contestacion and any(k in norm for k in ["CALIFICACION DE LA CONTESTACION", "CALIFICA CONTESTACION", "CONVOCATORIA", "CONVOCA A AUDIENCIA"]):
                tiene_calificacion_contestacion = True

            if any(k in norm for k in ["NOMBRAMIENTO DE PERITO", "DESIGNA PERITO", "NOMBRAMIENTO PERITO"]):
                tiene_nombramiento_perito = True

            if any(k in norm for k in ["EMBARGO", "DESPOSEIMIENTO", "ACTA DE EMBARGO"]):
                tiene_embargo = True

        # 2. Evaluación individual de cada actuación
        for act in actuaciones:
            detalle = act.get("detalle", "")
            fecha = act.get("fecha", None)
            norm = normalizar_texto(detalle)
            if not norm:
                continue

            # Regla de Inferencia 1: Carátula de juicio / Presentación si NO hay calificación aún
            if not tiene_calificacion_demanda and any(k in norm for k in ["CARATULA", "INGRESO DE CAUSA", "PRESENTACION", "LIBELO"]):
                hallazgos.append({
                    "etapa": "1 PRESENTACION Y CALIFICACION",
                    "fase": "1.1 PRESENTAR DEMANDA (CARATULA DE JUICIO)",
                    "fecha": fecha,
                    "prioridad": cls.obtener_indice_fase("1.1 PRESENTAR DEMANDA")
                })

            # Regla de Inferencia 5: Oficio del Banco / Superintendencia de Bancos -> Congelamiento y Cierre
            if any(k in norm for k in ["SUPERINTENDENCIA DE BANCOS", "AGREGUESE OFICIO EMITIDO POR BANCO", "AGREGUESE EL OFICIO EMITIDO POR EL BANCO", "OFICIO EMITIDO POR EL BANCO"]):
                hallazgos.append({
                    "etapa": "6 LIQUIDACION Y EMBARGO",
                    "fase": "6.5 CONGELAMIENTO DE CUENTAS / CIERRE",
                    "fecha": fecha,
                    "prioridad": cls.obtener_indice_fase("6.5 CONGELAMIENTO DE CUENTAS / CIERRE")
                })

            # Regla de Inferencia 4: Nombramiento de perito seguido de escrito/informe -> Liquidación perito liquidador
            if tiene_nombramiento_perito and any(k in norm for k in ["INFORME", "ESCRITO", "LIQUIDACION", "PERITO"]):
                hallazgos.append({
                    "etapa": "6 LIQUIDACION Y EMBARGO",
                    "fase": "6.1 LIQUIDACION PERITO LIQUIDADOR",
                    "fecha": fecha,
                    "prioridad": cls.obtener_indice_fase("6.1 LIQUIDACION PERITO LIQUIDADOR")
                })

            # Evaluación contra la Taxonomía Semántica Completa
            for etapa, fase, terminos in cls.TAXONOMIA_COMPLETA:
                for term in terminos:
                    term_norm = normalizar_texto(term)
                    if term_norm in norm:
                        prioridad = cls.obtener_indice_fase(fase)
                        hallazgos.append({
                            "etapa": etapa,
                            "fase": fase,
                            "fecha": fecha,
                            "prioridad": prioridad
                        })
                        break

        # Regla de Inferencia 3: Contestación con calificación/convocatoria -> Avance automático a FIJACION FECHA AUDIENCIA
        if tiene_contestacion and tiene_calificacion_contestacion:
            fecha_ref = actuaciones[0]["fecha"] if actuaciones else None
            hallazgos.append({
                "etapa": "4 AUDIENCIA",
                "fase": "4.1 FIJACION FECHA AUDIENCIA",
                "fecha": fecha_ref,
                "prioridad": cls.obtener_indice_fase("4.1 FIJACION FECHA AUDIENCIA")
            })

        # Regla de Inferencia 2: Si no hubo hallazgos en actuaciones, probar en contexto global
        if not hallazgos and texto_global:
            norm_global = normalizar_texto(texto_global)
            for etapa, fase, terminos in cls.TAXONOMIA_COMPLETA:
                for term in terminos:
                    term_norm = normalizar_texto(term)
                    if term_norm in norm_global:
                        prioridad = cls.obtener_indice_fase(fase)
                        fecha_ref = actuaciones[0]["fecha"] if actuaciones else None
                        hallazgos.append({
                            "etapa": etapa,
                            "fase": fase,
                            "fecha": fecha_ref,
                            "prioridad": prioridad
                        })
                        break

        if not hallazgos:
            return None, None, None

        # 3. Seleccionar el hito más avanzado procesalmente
        hallazgos_ordenados = sorted(hallazgos, key=lambda x: x["prioridad"], reverse=True)
        mejor = hallazgos_ordenados[0]
        return mejor["etapa"], mejor["fase"], mejor["fecha"]


class AgenteExtractor:
    """
    Agente Extractor Semántico y Autónomo (e-SATJE).
    Analiza el contenido completo de expedientes judiciales basándose en la taxonomía
    ampliada y el motor de inferencia procesal de 6 fases.
    Aplica coincidencia semántica y navegación dinámica en árbol (Move Up / Move Down).
    """
    TAXONOMIA_COMPLETA = MotorInferenciaProcesal.TAXONOMIA_COMPLETA

    def evaluar_similitud_semantica(self, texto):
        """
        Evalúa la similitud semántica del texto encontrado con la taxonomía judicial de 6 fases.
        Retorna (Etapa, Fase, Score) o (None, None, 0.0)
        """
        texto_norm = normalizar_texto(texto)
        if not texto_norm:
            return None, None, 0.0

        for etapa, fase, terminos in self.TAXONOMIA_COMPLETA:
            for term in terminos:
                term_norm = normalizar_texto(term)
                if term_norm in texto_norm:
                    return etapa, fase, 1.0

                palabras_term = [p for p in term_norm.split() if len(p) > 3]
                if palabras_term:
                    coincidencias = sum(1 for p in palabras_term if p in texto_norm)
                    ratio = coincidencias / len(palabras_term)
                    if ratio >= 0.7:
                        return etapa, fase, round(ratio, 2)

        return None, None, 0.0

    def procesar_html_string(self, contenido_html):
        """
        Procesa el contenido HTML recibido como string, extrayendo las actuaciones,
        la fecha de inicio de causa e infiriendo la fase procesal autónomamente.
        """
        resultado = {
            "FECHA INICIO JUICIO": None,
            "FECHA INICIAL FASE ACTUAL": None,
            "ETAPA_PROCESAL": None,
            "FASE_PROCESAL": None,
            "HISTORIAL_ACTUACIONES": []
        }

        if not contenido_html or not contenido_html.strip():
            logger.warning("Contenido HTML vacío recibido para procesamiento.")
            return resultado

        nav_arbol = NavegadorArbolContenido()

        try:
            try:
                soup = BeautifulSoup(contenido_html, "lxml")
            except Exception:
                soup = BeautifulSoup(contenido_html, "html.parser")

            # PASO 1: Extraer actuaciones estructuradas o de texto plano
            actuaciones = self._extraer_actuaciones_profundas(soup)

            if actuaciones:
                nav_arbol.bajar_nivel("Actuaciones estructuradas detectadas")
            else:
                nav_arbol.subir_nivel("Sin actuaciones estructuradas; recurriendo a texto plano")
                actuaciones = self._extraer_actuaciones_texto_plano(soup)

            resultado["HISTORIAL_ACTUACIONES"] = actuaciones

            # Extracción de Fecha de Inicio de Causa
            fecha_inicio = self._extraer_fecha_inicio(soup, actuaciones)
            resultado["FECHA INICIO JUICIO"] = fecha_inicio

            # PASO 2: Inferencia Procesal Autónoma
            etapa_inferida, fase_inferida, fecha_inferida = MotorInferenciaProcesal.inferir_estado_procesal(
                actuaciones, texto_global=soup.get_text(" ", strip=True)
            )

            if etapa_inferida:
                nav_arbol.bajar_nivel(f"Inferencia Autónoma exitosa -> '{fase_inferida}' en fecha {fecha_inferida}")
                resultado["ETAPA_PROCESAL"] = etapa_inferida
                resultado["FASE_PROCESAL"] = fase_inferida
                resultado["FECHA INICIAL FASE ACTUAL"] = fecha_inferida or (actuaciones[0]["fecha"] if actuaciones else None)
            elif actuaciones:
                # Fallback contextual si se encontraron actuaciones pero ninguna cuadró estrictamente
                resultado["FECHA INICIAL FASE ACTUAL"] = actuaciones[0]["fecha"]
                resultado["ETAPA_PROCESAL"] = "ESTADO DESCONOCIDO"
                resultado["FASE_PROCESAL"] = actuaciones[0]["detalle"][:100]

            return resultado

        except Exception as e:
            logger.error("Error al procesar contenido HTML: %s", e)
            return resultado

    def procesar_archivo_html(self, ruta_html):
        """
        Lee y procesa un archivo HTML desde disco delegando en procesar_html_string.
        """
        if not os.path.exists(ruta_html):
            logger.error("No existe el archivo: %s", ruta_html)
            return {
                "FECHA INICIO JUICIO": None,
                "FECHA INICIAL FASE ACTUAL": None,
                "ETAPA_PROCESAL": None,
                "FASE_PROCESAL": None,
                "HISTORIAL_ACTUACIONES": []
            }

        try:
            with open(ruta_html, "r", encoding="utf-8", errors="ignore") as f:
                contenido_html = f.read()
            return self.procesar_html_string(contenido_html)
        except Exception as e:
            logger.error("Error al leer archivo %s: %s", ruta_html, e)
            return {
                "FECHA INICIO JUICIO": None,
                "FECHA INICIAL FASE ACTUAL": None,
                "ETAPA_PROCESAL": None,
                "FASE_PROCESAL": None,
                "HISTORIAL_ACTUACIONES": []
            }

    def _extraer_actuaciones_profundas(self, soup):
        """Extrae filas de tabla y contenedores estructurados de actuaciones."""
        actuaciones = []
        filas = soup.find_all(["tr", "mat-row"])
        filas += soup.find_all("div", attrs={"role": ["row", "listitem", "gridcell"]})

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
        for elem in soup.find_all(string=re.compile(r"Fecha de ingreso|Fecha ingreso|Fecha presentación|Fecha inicio", re.IGNORECASE)):
            parent_text = elem.parent.get_text(strip=True) if elem.parent else str(elem)
            m = re.search(r'\d{2}/\d{2}/\d{4}', parent_text)
            if m:
                return m.group(0)

        if actuaciones:
            return actuaciones[-1]["fecha"]
        return None
