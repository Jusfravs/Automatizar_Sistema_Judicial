# src/agente_extractor.py
import html
import os
import re
import json
import unicodedata
from datetime import datetime
from bs4 import BeautifulSoup
from src.logger_config import obtener_logger

logger = obtener_logger("AgenteExtractor")


def _decodificar_entidades_satje(texto):
    """Convierte entidades no estandar de SATJE solo para reglas contextuales."""
    texto_satje = str(texto or "")
    texto_satje = re.sub(
        r"&([A-Z])(?:ACUTE|GRAVE|UML|CIRC|TILDE);", r"\1", texto_satje
    )
    texto_satje = re.sub(r"&NBSP;|&#160;", " ", texto_satje)
    texto_satje = re.sub(r"&(?:LDQUO|RDQUO|LSQUO|RSQUO);", '"', texto_satje)
    texto_satje = re.sub(r"&AMP;", "&", texto_satje)
    return html.unescape(texto_satje)


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


class ResultadoInferencia(tuple):
    """
    Resultado enriquecido de la inferencia procesal.
    Compatible con desempaquetado de 3-tupla: (etapa, fase, fecha)
    y con acceso por diccionario/propiedades para las nuevas columnas Excel.
    """
    def __new__(cls, ultima_etapa, ultima_fase, fecha_fin, etapa_actual=None, fase_actual=None, mensaje_especial=None, **_):
        return super().__new__(cls, (ultima_etapa, ultima_fase, fecha_fin))

    def __init__(self, ultima_etapa, ultima_fase, fecha_fin, etapa_actual=None, fase_actual=None, mensaje_especial=None, actuacion_respaldo=None, regla_aplicada=None, fase_original=None, fecha_original=None):
        self.ultima_etapa = ultima_etapa
        self.ultima_fase = ultima_fase
        self.fecha_fin_ultima_fase = fecha_fin
        self.etapa_actual = etapa_actual or ultima_etapa
        self.fase_actual = fase_actual or ultima_fase
        self.mensaje_especial = mensaje_especial
        self.actuacion_respaldo = actuacion_respaldo
        self.regla_aplicada = regla_aplicada
        self.fase_original = fase_original
        self.fecha_original = fecha_original

    def get(self, key, default=None):
        mapping = {
            "ULTIMA_ETAPA": self.ultima_etapa,
            "ULTIMA_FASE": self.ultima_fase,
            "FECHA_FIN_ULTIMA_FASE": self.fecha_fin_ultima_fase,
            "ETAPA_ACTUAL": self.etapa_actual,
            "FASE_ACTUAL": self.fase_actual,
            "FECHA_INICIO_FASE_ACTUAL": self.fecha_fin_ultima_fase,
            "MENSAJE_ESPECIAL": self.mensaje_especial,
            "ACTUACION_RESPALDO": self.actuacion_respaldo,
            "REGLA_APLICADA": self.regla_aplicada,
            "FASE_ORIGINAL": self.fase_original,
            "FECHA_ORIGINAL": self.fecha_original,
            "ETAPA_PROCESAL": self.ultima_etapa,
            "FASE_PROCESAL": self.ultima_fase,
            "FECHA INICIAL FASE ACTUAL": self.fecha_fin_ultima_fase
        }
        return mapping.get(key, default)

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.get(key)
        return super().__getitem__(key)


class MotorInferenciaProcesal:
    """
    Motor de Inferencia Procesal Autónoma basado en MODULO_FILTRO_CASOS.md y MOLDE_NUEVOS_CAMBIOS.md.
    Combina coincidencia conceptual por similitud semántica con inferencia
    de reglas de negocio procesales (deducción de transiciones de estado, 
    evaluación de carátulas, oficios bancarios, cadenas periciales, citaciones y 7 reglas avanzadas).
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
        (
            "6 LIQUIDACION Y EMBARGO", "6.5 CONGELAMIENTO DE CUENTAS / CIERRE",
            [
                "CONGELAMIENTO", "CONGELAMIENTO DE CUENTAS", "RETENCION DE CUENTAS",
                "BLOQUEO DE CUENTAS", "OFICIO RETENCION", "MEDIDA CAUTELAR BANCARIA",
                "RETENCION BANCARIA", "INMOVILIZACION DE FONDOS",
                "SUPERINTENDENCIA DE BANCOS", "OFICIO EMITIDO POR EL BANCO",
                "OFICIO EMITIDO POR BANCO", "AGREGUESE EL OFICIO EMITIDO POR EL BANCO",
                "AGREGUESE OFICIO EMITIDO POR EL BANCO", "OFICIO BANCO", "CIERRE DE PROCESO BANCARIO",
                "CONGELADA", "CONGELADAS", "RETENIDOS", "RETENIDAS",
                "TRANSFIERA", "TRANSFIERAN", "TRANSFERENCIA DE VALORES"
            ]
        ),
        (
            "6 LIQUIDACION Y EMBARGO", "6.4 REMATE",
            [
                "REMATE", "SUBASTA", "POSTURA", "CONVOCATORIA A REMATE",
                "AVALUO DE BIEN", "FECHA DE REMATE", "OFERTA DE REMATE",
                "PUBLICACION REMATE", "FECHA DE PUBLICACION REMATE",
                "AUTO DE ADJUDICACION", "ADJUDICACION"
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
                "LIQUIDACION PERITO LIQUIDADOR", "PERITO LIQUIDADOR", "INFORME DE LIQUIDACION",
                "LIQUIDACION DE CAPITAL E INTERESES", "INFORME PERICIAL DE LIQUIDACION",
                "NOMBRAMIENTO DE PERITO", "INFORME DEL PERITO", "PERITO NOMBRADO"
            ]
        ),
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
                "RECURSO DE APELACION", "CONCEDE RECURSO DE APELACION", "CONCEDE RECURSO",
                "CONCEDESE EL RECURSO", "INTERPONE RECURSO DE APELACION", "ELEVA EN APELACION",
                "FUNDAMENTACION DE APELACION", "ELEVA ALZADA", "RECURSO DE APELACION INTERPUESTO"
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
        (
            "4 AUDIENCIA", "4.3 ACUERDO DE MEDIACION",
            [
                "ACUERDO DE MEDIACION", "ACTA DE MEDIACION", "ACTA DE MEDIACION CON ACUERDO",
                "ACTA DE ACUERDO TOTAL", "ARCHIVO POR ACUERDO DE MEDIACION", "CONCILIACION DE MEDIACION",
                "DERIVACION A MEDIACION"
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
                "FIJACION FECHA AUDIENCIA", "FIJACION DE FECHA DE AUDIENCIA", "FIJACION DE AUDIENCIA",
                "SEÑALA AUDIENCIA", "SENALA DIA Y HORA", "SEÑALA FECHA Y HORA", "SENALA FECHA Y HORA",
                "CONVOCA A AUDIENCIA", "SEÑALAMIENTO DE AUDIENCIA", "FECHA AUDIENCIA",
                "DILIGENCIA DE AUDIENCIA PARA EL", "CONVOCATORIA A AUDIENCIA",
                "SUSPENCION Y NUEVO SEÑALAMIENTO DE AUDIENCIA", "SUSPENSION Y NUEVO SEÑALAMIENTO",
                "NUEVA FECHA AUDIENCIA", "REPROGRAMACION AUDIENCIA", "CALIFICACION DE LA CONTESTACION Y CONVOCATORIA"
            ]
        ),
        (
            "3 CONTESTACION", "3.1 CONTESTACION",
            [
                "CONTESTACION", "CONTESTA", "EXCEPCIONES", "ALLANAMIENTO",
                "RESPONDE DEMANDA", "ESCRITO DE CONTESTACION", "OPONE EXCEPCIONES"
            ]
        ),
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
                "BOLETA DE CITACION", "DILIGENCIA DE NOTIFICACIÓN", "CITACION REALIZADA",
                "CITACION NO REALIZADA", "REENVIO CITACION", "RAZON ENVIO A CITACIONES", "RAZON DE NO CITACION"
            ]
        ),
        (
            "1 PRESENTACION Y CALIFICACION", "1.3 CALIFICACION",
            [
                "CALIFICACION", "CALIFICA", "CALIFICADA", "AUTO INICIAL",
                "ADMITIDA", "ADMITE", "ACEPTA A TRAMITE", "CALIFICA LA DEMANDA",
                "AUTO DE CALIFICACION", "DEMANDA Y CALIFICACION"
            ]
        ),
        (
            "1 PRESENTACION Y CALIFICACION", "1.2 COMPLETAR/ACLARAR DEMANDA",
            [
                "COMPLETAR", "COMPLETAR DEMANDA", "ACLARAR DEMANDA", "ACLARACION",
                "SUBSANAR", "MANDAR A COMPLETAR", "PREVENCION DE COMPLETAR",
                "COMPLETA DEMANDA", "COMPLETAR Y/O ACLARAR", "COMPLETAR Y ACLARAR"
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
        """Devuelve el índice numérico de la fase para comparaciones de precedencia."""
        if not fase:
            return -1
        for idx, f in enumerate(cls.ORDEN_FASES):
            if f in fase or fase in f:
                return idx
        return -1

    @classmethod
    def _termino_procesal_presente(cls, texto_normalizado, termino):
        """Evita que conectores linguisticos activen fases procesales."""
        termino_norm = normalizar_texto(termino)
        texto_evaluable = str(texto_normalizado or "")
        texto_limpio = re.sub(r"<[^>]+>", " ", texto_evaluable)
        texto_limpio = re.sub(r"\s+", " ", texto_limpio).strip()
        es_rotulo_breve = len(texto_limpio) <= 220
        texto_contextual = _decodificar_entidades_satje(texto_evaluable)
        texto_contextual = re.sub(r"<[^>]+>", " ", texto_contextual)
        texto_contextual = re.sub(r"\s+", " ", texto_contextual).strip()

        if termino_norm in {"NOTIFICAR", "NOTIFIQUESE", "CITAR", "CITESE", "CITAR AL DEMANDADO", "SE CITA"}:
            # Son ordenes futuras o notificaciones ordinarias, no constancia de
            # que la citacion de la demanda ya se haya practicado.
            return False

        if termino_norm == "SORTEO":
            # El acta de sorteo identifica la radicacion inicial, pero no es
            # evidencia suficiente de una fase procesal sustantiva.
            return False

        if termino_norm == "AUTO INICIAL":
            if termino_norm not in texto_evaluable:
                return False
            if re.match(r"^RAZON\b", texto_limpio) or "PONGO EN CONOCIMIENTO" in texto_limpio or "EXTRACTO" in texto_limpio:
                return False

        if "FIJACION" in termino_norm:
            if re.search(r"\bFIJACION\s+DE\s+(?:BOLETAS?|CARTELES?|EXTRACTOS?)\b", texto_limpio):
                return False

        if termino_norm in {
            "FIJACION FECHA AUDIENCIA", "FIJACION DE FECHA DE AUDIENCIA", "FIJACION DE AUDIENCIA",
            "SEÑALA AUDIENCIA", "SENALA DIA Y HORA", "CONVOCA A AUDIENCIA", "SEÑALAMIENTO DE AUDIENCIA",
            "FECHA AUDIENCIA", "DILIGENCIA DE AUDIENCIA PARA EL", "CONVOCATORIA A AUDIENCIA",
            "SUSPENCION Y NUEVO SEÑALAMIENTO DE AUDIENCIA", "SUSPENSION Y NUEVO SEÑALAMIENTO",
            "NUEVA FECHA AUDIENCIA", "REPROGRAMACION AUDIENCIA", "CALIFICACION DE LA CONTESTACION Y CONVOCATORIA"
        }:
            if termino_norm not in texto_evaluable:
                return False
            if re.search(r"\bFIJACION\s+DE\s+(?:BOLETAS?|CARTELES?|EXTRACTOS?)\b", texto_limpio):
                return False
            es_rotulo_fijacion = es_rotulo_breve and bool(re.search(r"\b(?:AUDIENCIA|CONVOCATORIA|SENALAMIENTO)\b", texto_limpio))
            accion_fijacion = bool(re.search(r"\b(?:SENALA|CONVOCA|CONVOCATORIA|FIJA|SENALAMIENTO)\b.{0,60}\b(?:DIA\s+Y\s+HORA|AUDIENCIA)\b", texto_limpio))
            return es_rotulo_fijacion or accion_fijacion

        if termino_norm in {
            "ACTA RESUMEN", "ACTA DE AUDIENCIA", "AUDIENCIA PRELIMINAR",
            "AUDIENCIA DE JUICIO", "INSTALACION DE AUDIENCIA",
            "DILIGENCIA DE AUDIENCIA", "DESARROLLO DE AUDIENCIA",
            "ACTA RESUMEN DE AUDIENCIA", "AUDIENCIA CELEBRADA"
        }:
            if termino_norm not in texto_evaluable:
                return False
            if re.search(r"\b(?:PREVIO\s+A|CONVOQUESE\s+A|SENALARA|SE\s+SENALARA)\b.{0,60}\bAUDIENCIA\b", texto_limpio):
                return False
            es_rotulo_audiencia = es_rotulo_breve and bool(re.match(r"^(?:ACTA (?:DE )?AUDIENCIA|ACTA RESUMEN|AUDIENCIA PRELIMINAR|AUDIENCIA UNICA|AUDIENCIA DE JUICIO)\b", texto_limpio))
            audiencia_instalada = bool(re.search(r"\b(?:SE\s+INSTALA|INSTALADA|CELEBRADA|LLEVAD[AO]\s+A\s+CABO|DESARROLLO\s+DE)\b.{0,60}\bAUDIENCIA\b", texto_limpio))
            return es_rotulo_audiencia or audiencia_instalada or "ACTA RESUMEN" in texto_limpio

        if termino_norm in {"CONTESTACION", "CONTESTA", "EXCEPCIONES", "ALLANAMIENTO", "RESPONDE DEMANDA", "ESCRITO DE CONTESTACION", "OPONE EXCEPCIONES"}:
            if termino_norm not in texto_evaluable:
                return False
            if re.search(
                r"\b(?:SE\s+CONCEDE|CONCEDASE|PARA\s+QUE|A\s+FIN\s+DE\s+QUE|DEBERA|DEBE|TERMINO\s+DE\s+\w+\s+DIAS\s+PARA\s+QUE)\b.{0,140}\b(?:CONTESTE|CONTESTAR|CONTESTA|CONTESTEN)\b",
                texto_limpio,
            ) and not any(
                m in texto_evaluable
                for m in (
                    "ESCRITO DE CONTESTACION",
                    "PRESENTA CONTESTACION",
                    "AGREGUESE AL PROCESO EL ESCRITO DE CONTESTACION",
                    "CONTESTA LA DEMANDA DE FECHA",
                    "OPONE EXCEPCIONES",
                    "CONTESTACION: REALIZADA",
                )
            ):
                return False
            if re.search(r"\bART(?:ICULO|\.)?\s*\d+\b.{0,80}\b(?:CONTESTACI[OÓ]N|FALTA\s+DE\s+CONTESTACI[OÓ]N)\b", texto_limpio) and not any(
                m in texto_evaluable for m in ("ESCRITO DE CONTESTACION", "PRESENTA CONTESTACION", "CALIFICA LA CONTESTACION")
            ):
                return False
            if re.search(r"\bNO\s+(?:HA|HAN|HABER|HABIENDO)\s+(?:CONTESTAD[OA]|DADO\s+CONTESTACI[OÓ]N)\b", texto_limpio):
                return False
            if re.search(r"\bSIN\s+(?:HABER|QUE\s+HAYAN?)\s+CONTESTAD[OA]\b", texto_limpio):
                return False
            if "FALTA DE CONTESTACION" in texto_limpio or "CONTESTACION DE ESTA PROVIDENCIA" in texto_limpio:
                return False
            if "ACTAS DE NO CITACION" in texto_limpio or "RAZON DE NO CITACION" in texto_limpio:
                return False
            marcadores_respuesta = (
                "CONTESTACION A LA DEMANDA",
                "ESCRITO DE CONTESTACION",
                "PRESENTA CONTESTACION",
                "AGREGUESE EL ESCRITO DE CONTESTACION",
                "AGREGUESE AL PROCESO EL ESCRITO DE CONTESTACION",
                "CONTESTA LA DEMANDA",
                "SE DA POR CONTESTADA",
                "SE TIENE POR CONTESTADA",
                "OPONE EXCEPCIONES",
                "PRESENTA EXCEPCIONES",
                "CALIFICA LA CONTESTACION",
            )
            es_rotulo_contestacion = es_rotulo_breve and bool(re.match(
                r"^(?:CONTESTACION|ESCRITO DE CONTESTACION|EXCEPCIONES|ALLANAMIENTO|OPOSICION DE EXCEPCIONES)\b",
                texto_limpio,
            ))
            es_auto_calificacion = bool(re.search(r"\b(?:CALIFICACI[OÓ]N|ADMITIR LA DEMANDA|AUTO DE SUSTANCIACI[OÓ]N|AUTO INICIAL|DEMANDA Y CALIFICACI[OÓ]N)\b", texto_limpio))
            if es_auto_calificacion and not any(m in texto_limpio for m in ("CALIFICA LA CONTESTACION", "ESCRITO DE CONTESTACION")):
                return False
            return es_rotulo_contestacion or any(
                marcador in texto_evaluable for marcador in marcadores_respuesta
            )

        if termino_norm in {"ACUERDO DE MEDIACION", "MEDIACION", "ACTA DE MEDIACION", "CENTRO DE MEDIACION", "CONCILIACION DE MEDIACION", "ACTA DE MEDIACION CON ACUERDO", "ACTA DE ACUERDO TOTAL", "ARCHIVO POR ACUERDO DE MEDIACION", "DERIVACION A MEDIACION"}:
            if termino_norm not in texto_evaluable:
                return False
            if re.search(r"\b(?:PUEDEN|PODRAN|FACULTAD\s+DE)\s+ACUDIR\b.{0,60}\bMEDIACI[OÓ]N\b", texto_limpio):
                return False
            if re.search(r"\b(?:INFORMA|HACE\s+CONOCER)\b.{0,60}\bCENTRO\s+DE\s+MEDIACI[OÓ]N\b", texto_limpio) and not any(
                k in texto_limpio for k in ("ACTA DE MEDIACION", "ACUERDO DE MEDIACION", "DERIVACION A MEDIACION", "ACTA DE ACUERDO")
            ):
                return False
            marcadores_mediacion = (
                "ACTA DE MEDIACION",
                "ACUERDO DE MEDIACION",
                "ACTA DE ACUERDO TOTAL",
                "ACTA Y EXPEDIENTE N",
                "ARCHIVO POR ACUERDO DE MEDIACION",
                "DERIVACION A MEDIACION",
                "CENTRO DE MEDIACION DE LA FUNCION JUDICIAL",
                "CONCILIACION DE MEDIACION",
            )
            es_rotulo_mediacion = es_rotulo_breve and bool(re.match(
                r"^(?:ACUERDO DE MEDIACION|ACTA DE MEDIACION|DERIVACION A MEDIACION|ARCHIVO POR ACUERDO DE MEDIACION)\b",
                texto_limpio,
            ))
            return es_rotulo_mediacion or any(
                m in texto_evaluable for m in marcadores_mediacion
            )

        if termino_norm in {"APELACION", "RECURSO DE APELACION", "ALZADA", "CONCEDE RECURSO", "CORTE PROVINCIAL", "FUNDAMENTACION DE APELACION", "ELEVA ALZADA", "CONCEDE RECURSO DE APELACION", "CONCEDESE EL RECURSO", "INTERPONE RECURSO DE APELACION", "ELEVA EN APELACION", "RECURSO DE APELACION INTERPUESTO"}:
            if termino_norm not in texto_evaluable:
                return False
            if "OFICINA DE SORTEOS" in texto_limpio or "SORTEOS DE LA CORTE PROVINCIAL" in texto_limpio or "SISTEMA SATJE" in texto_limpio:
                return False
            if any(k in texto_limpio for k in ("GACETA JUDICIAL", "SENTENCIA N.", "JUICIOS NUMEROS", "JUICIOS N.", "TRATADISTA")):
                return False
            if termino_norm == "CORTE PROVINCIAL" and not any(k in texto_limpio for k in ("ELEVA", "REMITASE", "SALA DE LA CORTE PROVINCIAL", "APELACION")):
                return False
            marcadores_apelacion = (
                "CONCEDE RECURSO",
                "CONCEDE EL RECURSO",
                "CONCEDESE EL RECURSO",
                "RECURSO DE APELACION",
                "INTERPONE RECURSO",
                "INTERPONE APELACION",
                "ELEVA ALZADA",
                "ELEVA EN APELACION",
                "SUBE EN APELACION",
                "FUNDAMENTACION DE APELACION",
                "APELACION ADMITIDA",
                "APELACION ADMITIDO",
            )
            es_rotulo_apelacion = es_rotulo_breve and bool(re.match(
                r"^(?:APELACION|RECURSO DE APELACION|CONCESION DE RECURSO|AUTO DE APELACION)\b",
                texto_limpio,
            ))
            return es_rotulo_apelacion or any(
                m in texto_evaluable for m in marcadores_apelacion
            )

        if termino_norm in {"CALIFICACION", "CALIFICA", "CALIFICADA"}:
            if termino_norm not in texto_evaluable:
                return False
            if re.search(
                r"\b(?:SIN\s+ESTAR|PREVIO\s+A\s+SER|SIN\s+SER|NO|DEVUELTA\s+SIN\s+ESTAR)\s+CALIFICAD[OA]\b",
                texto_limpio,
            ):
                return False

        if termino_norm == "EDICTO":
            if not re.search(r"\bEDICTO\b", texto_limpio):
                return False

        if termino_norm == "CITACION":
            if re.search(
                r"\b(?:SE\s+)?(?:ORDENA|DISPONE)\b.{0,45}\bCITACION\b",
                texto_limpio,
            ):
                # Ordenar la diligencia no demuestra que ya fue practicada.
                return False
            if termino_norm not in texto_evaluable:
                return False
            marcadores_citacion = (
                "CITACION REALIZADA",
                "CITACION NO REALIZADA",
                "RAZON DE CITACION",
                "RAZON ENVIO A CITACIONES",
                "ACTA DE CITACION",
                "DILIGENCIA DE CITACION",
                "BOLETA DE CITACION",
                "GESTION REALIZADA POR EL CITADOR",
                "LEGALMENTE CITADA",
                "LEGALMENTE CITADO",
            )
            return es_rotulo_breve or any(
                marcador in texto_evaluable for marcador in marcadores_citacion
            )

        if termino_norm in {"BOLETA", "BOLETAS"}:
            if termino_norm not in texto_evaluable:
                return False
            if re.search(
                r"\b(?:ELABORAR|EMITIR|REMITIR|SE\s+ORDENA\s+CITAR|ORDENESE\s+CITAR|DISPONESE\s+CITAR)\b",
                texto_limpio,
            ) and not re.search(
                r"\b(?:NOTIFICADA|ENTREGADA|FIJADA|CITADO|REALIZADA)\b",
                texto_limpio,
            ):
                return False
            if re.search(r"\bSE\s+ORDENA\s+CITAR\b", texto_limpio) and not re.search(r"\b(?:ACTA|RAZON|DILIGENCIA|ENTREGADA|FIJADA)\b", texto_limpio):
                return False
            return any(
                marcador in texto_evaluable
                for marcador in (
                    "BOLETA DE CITACION",
                    "BOLETAS DE CITACION",
                    "BOLETA FIJADA",
                    "RAZON ENVIO A CITACIONES",
                    "GESTION REALIZADA POR EL CITADOR",
                )
            )

        if termino_norm == "CITADO":
            if termino_norm not in texto_evaluable:
                return False
            return any(
                marcador in texto_evaluable
                for marcador in (
                    "LEGALMENTE CITADO",
                    "HA SIDO CITADO",
                    "SE ENCUENTRA CITADO",
                    "CITADO Y NOTIFICADO",
                )
            )

        if termino_norm == "ORDEN DE PAGO":
            # En las sentencias cambiarias se describe doctrinalmente que el
            # titulo valor "contiene una orden de pago". Eso no es el auto de
            # mandamiento previsto en el art. 372 del COGEP.
            if re.search(
                r"\bTITULO\s+VALOR\b.{0,90}\b(?:CONTIENE|CONSTITUYE)\b"
                r".{0,40}\bORDEN\s+DE\s+PAGO\b",
                texto_contextual,
            ):
                return False
            es_rotulo_orden = es_rotulo_breve and bool(re.match(
                r"^(?:ORDEN DE PAGO|AUTO DE EJECUCION)\b", texto_contextual
            ))
            orden_explicita = bool(re.search(
                r"\b(?:DICTA|EMITE|EXPIDE|NOTIFICA)\b.{0,80}\bORDEN DE PAGO\b",
                texto_contextual,
            ))
            mandato_art_372 = bool(
                re.search(r"\bARTICULO\s+372\b", texto_contextual)
                and re.search(
                    r"\bSE\s+ORDENA\b.{0,180}\b(?:PAGUE|PAGUEN|CANCELE|CANCELEN)\b",
                    texto_contextual,
                )
            )
            mandato_pago_cinco_dias = bool(
                re.search(
                    r"\bSE\s+ORDENA\b.{0,220}\b(?:PAGUE|PAGUEN|CANCELE|CANCELEN)\b",
                    texto_contextual,
                )
                and re.search(r"\bTERMINO\s+DE\s+(?:CINCO|5)\s+DIAS\b", texto_contextual)
            )
            return es_rotulo_orden or orden_explicita or mandato_art_372 or mandato_pago_cinco_dias

        if termino_norm in {"MANDAMIENTO", "MANDAMIENTO DE EJECUCION"}:
            if termino_norm not in texto_evaluable:
                return False
            # Una razon de incumplimiento menciona el mandamiento anterior,
            # pero no debe reemplazar la fecha en que este fue dictado.
            if (
                "INCUMPLIMIENTO DE MANDAMIENTO" in texto_evaluable
                or re.search(
                    r"\b(?:PUBLICA|PUBLIQUE|PUBLICACION)\b.{0,110}"
                    r"\bMANDAMIENTO(?: DE EJECUCION)?\b",
                    texto_contextual,
                )
                or re.search(
                    r"\bSI\b.{0,90}\b(?:DIO|HA\s+DADO|DADO)\b.{0,50}"
                    r"\bCUMPLIMIENTO\b.{0,100}\bMANDAMIENTO\b",
                    texto_contextual,
                )
                or re.search(
                    r"\bNO\s+HA\s+PAGADO\b.{0,180}\bMANDAMIENTO\b",
                    texto_contextual,
                )
                or re.search(
                    r"\bTERMINO\s+CONCEDIDO\b.{0,100}\bMANDAMIENTO\b",
                    texto_contextual,
                )
            ):
                return False
            es_rotulo_mandamiento = es_rotulo_breve and bool(re.match(
                r"^(?:MANDAMIENTO(?: DE EJECUCION)?|AUTO (?:DE|QUE DICTA) EJECUCION|NOTIFICACION DE MANDAMIENTO)\b",
                texto_limpio,
            ))
            encabezado_mandamiento = bool(
                re.search(r"\bMANDAMIENTO DE EJECUCION\s*:", texto_limpio)
                and re.search(
                    r"\b(?:PAGUE|PAGUEN|CANCELE|CANCELEN)\b",
                    texto_limpio,
                )
            )
            accion_mandamiento = bool(re.search(
                r"\b(?:DICTA|EMITE|ORDENA|DISPONE|NOTIFICA|EXPIDE)\b.{0,90}"
                r"\bMANDAMIENTO(?: DE EJECUCION)?\b",
                texto_limpio,
            ))
            return es_rotulo_mandamiento or encabezado_mandamiento or accion_mandamiento

        terminos_bancarios = {
            "CONGELAMIENTO", "CONGELAMIENTO DE CUENTAS", "RETENCION DE CUENTAS",
            "BLOQUEO DE CUENTAS", "OFICIO RETENCION", "MEDIDA CAUTELAR BANCARIA",
            "RETENCION BANCARIA", "INMOVILIZACION DE FONDOS",
            "SUPERINTENDENCIA DE BANCOS", "OFICIO EMITIDO POR EL BANCO",
            "OFICIO EMITIDO POR BANCO", "AGREGUESE EL OFICIO EMITIDO POR EL BANCO",
            "AGREGUESE OFICIO EMITIDO POR EL BANCO", "OFICIO BANCO",
            "CIERRE DE PROCESO BANCARIO",
            "CONGELADA", "CONGELADAS", "RETENIDOS", "RETENIDAS",
            "TRANSFIERA", "TRANSFIERAN", "TRANSFERENCIA DE VALORES",
        }
        if termino_norm in terminos_bancarios:
            if termino_norm not in texto_evaluable:
                return False
            # Pedir que se certifique la existencia de cuentas solo localiza
            # activos; no prueba retencion, congelamiento ni recuperacion.
            cuenta_afectada = bool(
                re.search(
                    r"\bCUENTAS?\b.{0,140}\b(?:CONGELAD[AO]S?|RETENID[AO]S?|"
                    r"BLOQUEAD[AO]S?|INMOVILIZAD[AO]S?)\b",
                    texto_contextual,
                )
                or re.search(
                    r"\b(?:CONGELAD[AO]S?|RETENID[AO]S?|BLOQUEAD[AO]S?|"
                    r"INMOVILIZAD[AO]S?)\b.{0,140}\b(?:CUENTAS?|FONDOS?|VALORES?)\b",
                    texto_contextual,
                )
            )
            transferencia_valores = bool(
                re.search(
                    r"\b(?:TRANSFIER[AE]N?|TRANSFERENCIAS?|TRANSFERID[AO]S?)\b"
                    r".{0,180}\b(?:VALORES?|FONDOS?|DINERO|MONTOS?|CUENTA JUDICIAL)\b",
                    texto_contextual,
                )
                or re.search(
                    r"\b(?:VALORES?|FONDOS?|DINERO|MONTOS?)\b.{0,180}"
                    r"\b(?:TRANSFIER[AE]N?|TRANSFERENCIAS?|TRANSFERID[AO]S?)\b",
                    texto_contextual,
                )
            )
            es_rotulo_ejecutado = es_rotulo_breve and bool(re.match(
                r"^(?:CONGELAMIENTO|RETENCION|BLOQUEO|INMOVILIZACION) DE (?:CUENTAS|FONDOS)\b",
                texto_contextual,
            ))
            return es_rotulo_ejecutado or cuenta_afectada or transferencia_valores

        if termino_norm in {"LIQUIDACION", "LIQUIDADOR", "PERITO LIQUIDADOR", "LIQUIDACION PERITO LIQUIDADOR"}:
            if termino_norm not in texto_evaluable:
                return False
            if re.search(r"\b(?:DIRECTOR|GERENTE|REPRESENTANTE|APODERADO)\b.{0,40}\bLIQUIDADOR\b", texto_limpio):
                return False
            marcadores_liquidacion = (
                "PERITO LIQUIDADOR",
                "LIQUIDACION PERITO LIQUIDADOR",
                "INFORME DE LIQUIDACION",
                "INFORME PERICIAL DE LIQUIDACION",
                "LIQUIDACION DE CAPITAL E INTERESES",
                "NOMBRAMIENTO DE PERITO",
                "INFORME DEL PERITO",
                "APRUEBA LA LIQUIDACION",
                "APROBACION DE LIQUIDACION",
                "PRACTIQUE LA LIQUIDACION",
                "PRACTICAR LA LIQUIDACION",
                "PRESENTA LA LIQUIDACION",
                "TRASLADO CON LA LIQUIDACION",
                "PERITO NOMBRADO",
            )
            es_rotulo_liquidacion = es_rotulo_breve and bool(re.match(
                r"^(?:LIQUIDACION|PERITO LIQUIDADOR|NOMBRAMIENTO DE PERITO|INFORME PERICIAL)\b",
                texto_limpio,
            ))
            return es_rotulo_liquidacion or any(
                marcador in texto_evaluable for marcador in marcadores_liquidacion
            )

        if termino_norm in {
            "EJECUTORIA", "EJECUTORIADA", "SENTENCIA EJECUTORIADA",
            "AUTO FIRME", "SENTENCIA EN FIRME", "CERTIFICO EJECUTORIA",
        }:
            if termino_norm not in texto_evaluable:
                return False
            texto_sin_condicion_futura = re.sub(
                r"\b(?:UNA VEZ\s+)?EJECUTORIAD[OA]\s+QUE\s+SEA\s+EL\s+PRESENTE\s+AUTO\b",
                " ",
                texto_limpio,
            )
            texto_sin_condicion_futura = re.sub(
                r"\b(?:TIENE|CONFIERE\s+AL\s+ACTA\s+DE\s+MEDIACI[OÓ]N\s+EL\s+CAR[AÁ]CTER\s+DE|CON\s+EFECTO\s+DE)\s+SENTENCIA\s+EJECUTORIADA\b",
                " ",
                texto_sin_condicion_futura,
            )
            if termino_norm not in texto_sin_condicion_futura:
                return False
            marcadores_ejecutoria = (
                "RAZON DE EJECUTORIA",
                "RAZON DE EJECUTORIADA",
                "SENTENCIA EJECUTORIADA",
                "SENTENCIA SE ENCUENTRA EJECUTORIADA",
                "SENTENCIA EN FIRME",
                "AUTO FIRME",
                "CERTIFICO EJECUTORIA",
                "HA CAUSADO EJECUTORIA",
                "DECLARA EJECUTORIADA",
            )
            es_rotulo_ejecutoria = es_rotulo_breve and bool(re.match(
                r"^(?:RAZON DE )?(?:SENTENCIA )?EJECUTORIAD[AO]?\b",
                texto_sin_condicion_futura,
            ))
            sentencia_declarada_ejecutoriada = bool(re.search(
                r"\bSENTENCIA\b.{0,120}\bSE\s+ENCUENTRA\b.{0,50}"
                r"\bEJECUTORIADA\b",
                texto_sin_condicion_futura,
            ))
            return es_rotulo_ejecutoria or sentencia_declarada_ejecutoriada or any(
                marcador in texto_sin_condicion_futura for marcador in marcadores_ejecutoria
            )

        if termino_norm == "SENTENCIA":
            if termino_norm not in texto_evaluable:
                return False
            if re.search(
                r"\b(?:PRONUNCIARA|DICTARA|EMITIRA)\b.{0,50}\bSENTENCIA\b",
                texto_limpio,
            ):
                return False
            marcadores_sentencia_emitida = (
                "SENTENCIA QUE ANTECEDE",
                "SENTENCIA SE ENCUENTRA",
                "SENTENCIA EMITIDA",
            )
            return es_rotulo_breve or any(
                marcador in texto_evaluable for marcador in marcadores_sentencia_emitida
            )

        if termino_norm in {"RESOLUCION", "FALLO"}:
            if termino_norm not in texto_evaluable:
                return False
            if re.search(
                r"\b(?:CALIFICA|CITAR|AUTO\s+INICIAL|ADMITE\s+A\s+TRAMITE|SE\s+RESUELVE\s+CITAR)\b",
                texto_evaluable,
            ) and not any(
                k in texto_evaluable
                for k in ("SENTENCIA", "ACEPTA LA DEMANDA", "DECLARA CON LUGAR")
            ):
                return False
            return es_rotulo_breve or bool(
                re.search(r"\b(?:PARTE RESOLUTIVA|FALLA)\b", texto_evaluable)
            )

        terminos_remate = {
            "REMATE", "SUBASTA", "POSTURA", "CONVOCATORIA A REMATE",
            "AVALUO DE BIEN", "FECHA DE REMATE", "OFERTA DE REMATE",
            "PUBLICACION REMATE", "FECHA DE PUBLICACION REMATE",
            "AUTO DE ADJUDICACION", "ADJUDICACION",
        }
        if termino_norm in terminos_remate:
            if termino_norm not in texto_evaluable:
                return False
            if re.search(
                r"\b(?:NO\s+SE\s+HA\s+REALIZADO|NO\s+SE\s+REALIZO|SE\s+NIEGA|"
                r"PREVIO\s+A\s+SENALAR)\b.{0,100}\bREMATE\b",
                texto_contextual,
            ):
                return False
            es_acta_ejecutada = es_rotulo_breve and bool(re.match(
                r"^(?:ACTA DE REMATE|AUTO DE ADJUDICACION|ADJUDICACION)\b",
                texto_contextual,
            ))
            resultado_remate = bool(
                re.search(
                    r"\b(?:SE\s+)?(?:REALIZO|PRACTICO|CONCLUYO|CERRO)\b.{0,100}\bREMATE\b",
                    texto_contextual,
                )
                or re.search(
                    r"\bREMATE\b.{0,140}\b(?:REALIZADO|CONCLUIDO|CERRADO|ADJUDICAD[AO]|"
                    r"MEJOR POSTURA|POSTOR GANADOR)\b",
                    texto_contextual,
                )
                or re.search(r"\b(?:AUTO DE )?ADJUDICACION\b", texto_contextual)
                or re.search(
                    r"\b(?:VALORES?|FONDOS?|PRODUCTO)\b.{0,140}\bREMATE\b.{0,180}"
                    r"\b(?:TRANSFIER|ENTREG|PAG)\w*\b",
                    texto_contextual,
                )
            )
            return es_acta_ejecutada or resultado_remate

        if termino_norm == "EMBARGO":
            if termino_norm not in texto_evaluable:
                return False
            texto_sin_conector = re.sub(
                r"\bSIN(?:\s|&NBSP;|&#160;|<[^>]+>)+EMBARGO\b",
                " ",
                texto_limpio,
                flags=re.IGNORECASE,
            )
            if not re.search(r"\bEMBARGO\b", texto_sin_conector):
                return False
            if re.search(
                r"\bNO\s+SE\s+HA\s+ORDENADO\b.{0,35}\bEMBARGO\b",
                texto_sin_conector,
            ):
                return False
            if re.search(
                r"\b(?:NO\s+PUEDE\s+EJECUTAR|SE\s+(?:LO\s+|LA\s+)?NIEGA)\b",
                texto_sin_conector,
            ):
                # Una solicitud de embargo expresamente rechazada no es una
                # orden, aunque la providencia empiece con "se dispone".
                return False
            if (
                "PONE EN CONOCIMIENTO" in texto_sin_conector
                and re.search(
                    r"\bDENTRO DE LA CAUSA\b.{0,180}\bORDENAD[OA]\b"
                    r".{0,50}\bEMBARGO\b",
                    texto_sin_conector,
                )
            ):
                return False
            # Una cita doctrinal, una peticion, una referencia normativa o una
            # negativa expresa no equivalen a que el juzgado decrete embargo.
            es_rotulo_embargo = es_rotulo_breve and bool(re.match(
                r"^(?:EMBARGO|ACTA DE EMBARGO|INSCRIPCION DE EMBARGO)\b",
                texto_sin_conector,
            ))
            accion_embargo = bool(re.search(
                r"\b(?:ORDENA|ORDENAD[OA]|DISPONE|DECRETA|TRABA|PRACTICA|INSCRIBE|EJECUTA|REALIZA)\b"
                r".{0,100}\bEMBARGO\b",
                texto_sin_conector,
            ))
            return es_rotulo_embargo or accion_embargo

        return termino_norm in texto_evaluable

    @classmethod
    def calcular_siguiente_fase(cls, fase_actual):
        """
        Dada la fase actual encontrada, retorna la siguiente fase y etapa según ORDEN_FASES.
        Si la fase es la última (6.5), retorna la misma fase.
        Si la fase es 6.4 REMATE o 6.5 CONGELAMIENTO, no avanza.
        """
        if fase_actual in ("2.1 CITACION (PERSONA/BOLETA)", "2.2 CITACION POR PRENSA"):
            return "CONTESTACION", "CONTESTACION"

        idx = cls.obtener_indice_fase(fase_actual)
        if idx < 0:
            return None, None

        if idx >= len(cls.ORDEN_FASES) - 1 or cls.ORDEN_FASES[idx] in ("6.4 REMATE", "6.5 CONGELAMIENTO DE CUENTAS / CIERRE"):
            return cls.MAPEO_ETAPAS.get(cls.ORDEN_FASES[idx]), cls.ORDEN_FASES[idx]

        siguiente_fase = cls.ORDEN_FASES[idx + 1]
        siguiente_etapa = cls.MAPEO_ETAPAS.get(siguiente_fase)
        return siguiente_etapa, siguiente_fase


    @staticmethod
    def _fecha_ordenable(fecha):
        """Convierte fechas de actuaciones a un valor comparable sin alterar su formato de salida."""
        if fecha is None:
            return datetime.min
        valor = str(fecha).strip()
        for formato in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(valor[:10], formato)
            except ValueError:
                continue
        return datetime.min

    @classmethod
    def _hallazgo_mas_reciente(cls, hallazgos, fase):
        """Devuelve la evidencia fechada m??s reciente de una fase, sin depender del orden de entrada."""
        candidatos = [h for h in hallazgos if h["fase"] == fase and h.get("fecha")]
        if not candidatos:
            return None
        return max(enumerate(candidatos), key=lambda item: (cls._fecha_ordenable(item[1]["fecha"]), item[0]))[1]

    @classmethod
    def _hallazgos_fase_en_actuaciones(cls, actuaciones, fase):
        """Reune la evidencia fechada de una fase en todo el historial disponible."""
        candidatos = []
        for etapa, fase_taxonomia, terminos in cls.TAXONOMIA_COMPLETA:
            if fase_taxonomia != fase:
                continue
            for act in actuaciones:
                norm = normalizar_texto(act.get("detalle", ""))
                if any(cls._termino_procesal_presente(norm, termino) for termino in terminos):
                    candidatos.append({
                        "etapa": etapa,
                        "fase": fase,
                        "fecha": act.get("fecha"),
                        "prioridad": cls.obtener_indice_fase(fase),
                        "actuacion": norm,
                    })
            break
        return candidatos

    @classmethod
    def _hallazgo_fase_en_actuaciones(cls, actuaciones, fase):
        """Busca la evidencia fechada mas reciente de una fase en todo el historial."""
        return cls._hallazgo_mas_reciente(
            cls._hallazgos_fase_en_actuaciones(actuaciones, fase), fase
        )

    @classmethod
    def _hallazgo_calificacion_principal(cls, hallazgos):
        """Prioriza el acto de calificacion, no menciones incidentales posteriores."""
        candidatos = [
            hallazgo
            for hallazgo in hallazgos
            if hallazgo.get("fase") == "1.3 CALIFICACION" and hallazgo.get("fecha")
        ]
        if not candidatos:
            return None

        marcadores_explicitos = (
            "CALIFICACION DE SOLICITUD",
            "CALIFICACION DE DEMANDA",
            "AUTO DE CALIFICACION",
            "CALIFICA LA DEMANDA",
            "DEMANDA Y CALIFICACION",
            "ACEPTA A TRAMITE",
            "ADMITE A TRAMITE",
            "AUTO INICIAL",
        )
        explicitos = [
            hallazgo
            for hallazgo in candidatos
            if any(marcador in hallazgo.get("actuacion", "") for marcador in marcadores_explicitos)
            and "RAZON:" not in hallazgo.get("actuacion", "")
            and "RAZON " not in hallazgo.get("actuacion", "")
            and "EXTRACTO" not in hallazgo.get("actuacion", "")
        ]
        return cls._hallazgo_mas_reciente(
            explicitos or candidatos, "1.3 CALIFICACION"
        )

    @staticmethod
    def _es_citacion_fallida(texto_normalizado):
        return bool(
            re.search(r"\bCITACION\W*NO\s+REALIZADA\b", texto_normalizado)
            or "REENVIO CITACION" in texto_normalizado
            or "RAZON ENVIO A CITACIONES" in texto_normalizado
            or "RAZON DE NO CITACION" in texto_normalizado
        )

    @staticmethod
    def _es_citacion_fallida_explicita(texto_normalizado):
        return bool(
            re.search(r"\bCITACION\W*NO\s+REALIZADA\b", texto_normalizado)
            or re.search(r"\bNO\s+(?:SE\s+)?(?:ENCUENTRA\s+|HA\s+SIDO\s+|PUDO\s+|HE\s+PODIDO\s+|HA\s+EFECTUADO\s+|SE\s+HA\s+)CITAD[OA]\b", texto_normalizado)
            or re.search(r"\bNO\s+SE\s+CITO\b", texto_normalizado)
            or re.search(r"\bCONSTA\s+QUE\s+NO\s+SE\s+HA\s+CITADO\b", texto_normalizado)
            or re.search(r"\bNO\s+SE\s+HA\s+CITADO\b", texto_normalizado)
            or re.search(r"\bNO\s+SE\s+HA\s+EFECTUADO\b.{0,40}\bCITACI[OÓ]N\b", texto_normalizado)
            or re.search(r"\bDEVUELTA\s+SIN\s+CITAR\b", texto_normalizado)
            or "RAZON DE NO CITACION" in texto_normalizado
            or "NO HA SIDO CITADO" in texto_normalizado
            or "NO SE ENCUENTRA CITADO" in texto_normalizado
            or "NO HE PODIDO CITAR" in texto_normalizado
            or "ACTA DE NO CITACION" in texto_normalizado
            or "ACTAS DE NO CITACION" in texto_normalizado
            or "ACTA DE NO CITACI" in texto_normalizado
            or "REENVIO CITACION" in texto_normalizado
            or "NULIDAD POR FALTA DE CITACION" in texto_normalizado
            or "DIRECCION INCORRECTA" in texto_normalizado
            or "NO EXISTE LA DIRECCION" in texto_normalizado
        )

    @staticmethod
    def _es_citacion_exitosa(texto_normalizado):
        if MotorInferenciaProcesal._es_citacion_fallida_explicita(texto_normalizado):
            return False
        if re.search(r"\b(?:SE\s+DISPONE|ORDENA|A\s+FIN\s+DE\s+QUE\s+SEA)\s+LEGALMENTE\s+CITAD[OA]\b", texto_normalizado):
            return False
        if any(k in texto_normalizado for k in ("NO SE ENCUENTRA CITADO", "NO HE PODIDO CITAR", "NO HA SIDO CITADO", "NO EXISTE LA DIRECCION", "DIRECCION INCORRECTA")):
            return False
        return bool(
            re.search(r"\bCITACION\W*REALIZADA\b", texto_normalizado)
            or "BOLETA DE CITACION NOTIFICADA" in texto_normalizado
            or "CITADO Y NOTIFICADO" in texto_normalizado
            or "LEGALMENTE CITADO" in texto_normalizado
            or "LEGALMENTE CITADA" in texto_normalizado
            or "CITADOS EN PERSONA" in texto_normalizado
            or "CITADA EN PERSONA" in texto_normalizado
            or "BOLETA 3" in texto_normalizado
            or "TERCERA GESTION" in texto_normalizado
        )

    @classmethod
    def _decision_con_evidencia(cls, regla, etapa, fase, evidencia):
        """Crea una decisi??n at??mica y nunca reutiliza una fecha de otra fase."""
        if evidencia:
            return {**evidencia, "etapa": etapa, "fase": fase}
        logger.warning("[DECISION_FASE] %s", json.dumps({"regla_aplicada": regla, "fase_final": fase, "advertencia": "sin_evidencia_de_fecha"}, ensure_ascii=False))
        return {"etapa": etapa, "fase": fase, "fecha": None, "actuacion": None}

    @classmethod
    def _segmentar_por_instancia(cls, actuaciones):
        """
        Segmenta las actuaciones según la instancia procesal o rama del árbol.
        Devuelve un diccionario { 'PRIMERA INSTANCIA': [...], 'SEGUNDA INSTANCIA': [...], ... }
        """
        instancias = {
            "PRIMERA INSTANCIA": []
        }
        instancia_actual = "PRIMERA INSTANCIA"

        for act in actuaciones:
            detalle = act.get("detalle", "")
            norm = normalizar_texto(detalle)
            detalle_limpio = re.sub(r"<[^>]+>", " ", norm)
            detalle_limpio = re.sub(r"\s+", " ", detalle_limpio).strip()
            es_rotulo_estructural = len(detalle_limpio) <= 300
            contexto_organo = normalizar_texto(" ".join(
                str(act.get(campo, "") or "")
                for campo in (
                    "DEPENDENCIA_JURISDICCIONAL",
                    "DEPENDENCIA",
                    "ORGANO_JURISDICCIONAL",
                )
            ))
            
            # Detectar cambio de instancia o rama en el árbol de actuaciones
            marcadores_segunda = ["CORTE PROVINCIAL", "SEGUNDA INSTANCIA", "SALA ESPECIALIZADA", "TRIBUNAL DE ALZADA"]
            marcadores_casacion = ["CORTE NACIONAL", "CASACION", "SALA DE LO CONTENCIOSO"]
            es_segunda = any(k in contexto_organo for k in marcadores_segunda) or (
                es_rotulo_estructural and any(k in norm for k in marcadores_segunda)
            )
            es_casacion = any(k in contexto_organo for k in marcadores_casacion) or (
                es_rotulo_estructural and any(k in norm for k in marcadores_casacion)
            )
            if es_casacion:
                instancia_actual = "CASACION"
                if instancia_actual not in instancias:
                    instancias[instancia_actual] = []
            elif es_segunda:
                instancia_actual = "SEGUNDA INSTANCIA"
                if instancia_actual not in instancias:
                    instancias[instancia_actual] = []
            elif "INSTANCIA" in act and act["INSTANCIA"]:
                instancia_actual = str(act["INSTANCIA"]).upper()
                if instancia_actual not in instancias:
                    instancias[instancia_actual] = []

            instancias[instancia_actual].append(act)

        return instancias

    @classmethod
    def _seleccionar_rama_activa(cls, instancias_dict):
        """
        Selecciona la rama activa del árbol (la de mayor jerarquía procesal que contenga actuaciones).
        Prioridad: CASACION > SEGUNDA INSTANCIA > PRIMERA INSTANCIA (o cualquier otra instancia personalizada).
        """
        for orden in ["CASACION", "SEGUNDA INSTANCIA", "TRIBUNAL"]:
            if orden in instancias_dict and instancias_dict[orden]:
                return orden, instancias_dict[orden]

        # Si no hay instancias superiores, retornar la primera disponible con actuaciones
        for nombre, lista_acts in instancias_dict.items():
            if lista_acts:
                return nombre, lista_acts

        return "PRIMERA INSTANCIA", []

    @classmethod
    def inferir_estado_procesal(cls, actuaciones, texto_global=""):
        """
        Analiza el estado procesal basándose ESTRICTAMENTE en la jerarquía del Árbol de Actuaciones y 7 Reglas Especiales:
        Retorna una instancia de ResultadoInferencia.
        """
        if not actuaciones and not texto_global:
            return ResultadoInferencia(None, None, None)

        # PASO 1 & 2: Segmentar por instancia y seleccionar la rama activa
        if actuaciones:
            instancias = cls._segmentar_por_instancia(actuaciones)
            nombre_rama, actuaciones_rama = cls._seleccionar_rama_activa(instancias)
        else:
            nombre_rama, actuaciones_rama = "TEXTO_GLOBAL", []

        if not actuaciones_rama and not texto_global:
            return ResultadoInferencia(None, None, None)

        actuaciones_evaluar = list(actuaciones_rama)

        tiene_calificacion_demanda = False
        tiene_contestacion = False
        tiene_calificacion_contestacion = False

        for act in actuaciones_evaluar:
            detalle = act.get("detalle", "")
            norm = normalizar_texto(detalle)

            if any(k in norm for k in ["CALIFICACION LA DEMANDA", "CALIFICA LA DEMANDA", "AUTO DE CALIFICACION", "AUTO INICIAL", "ACEPTA A TRAMITE"]):
                tiene_calificacion_demanda = True
            if any(k in norm for k in ["CONTESTACION", "RESPONDE DEMANDA", "EXCEPCIONES", "ALLANAMIENTO"]):
                tiene_contestacion = True
            if tiene_contestacion and any(k in norm for k in ["CALIFICACION DE LA CONTESTACION", "CALIFICA CONTESTACION", "CONVOCATORIA", "CONVOCA A AUDIENCIA"]):
                tiene_calificacion_contestacion = True

        hallazgos = []

        # PASO 3: Evaluar actuaciones en la rama activa.
        for act in actuaciones_evaluar:
            detalle = act.get("detalle", "")
            fecha = act.get("fecha", None)
            norm = normalizar_texto(detalle)
            if not norm:
                continue

            if not tiene_calificacion_demanda and any(k in norm for k in ["CARATULA", "INGRESO DE CAUSA", "PRESENTACION", "LIBELO"]):
                hallazgos.append({
                    "etapa": "1 PRESENTACION Y CALIFICACION",
                    "fase": "1.1 PRESENTAR DEMANDA",
                    "fecha": fecha,
                    "prioridad": cls.obtener_indice_fase("1.1 PRESENTAR DEMANDA"),
                    "actuacion": norm
                })

            for etapa, fase, terminos in cls.TAXONOMIA_COMPLETA:
                for term in terminos:
                    term_norm = normalizar_texto(term)
                    if cls._termino_procesal_presente(norm, term_norm):
                        prioridad = cls.obtener_indice_fase(fase)
                        hallazgos.append({
                            "etapa": etapa,
                            "fase": fase,
                            "fecha": fecha,
                            "prioridad": prioridad,
                            "actuacion": norm
                        })
                        break

        if tiene_contestacion and tiene_calificacion_contestacion:
            fecha_ref = actuaciones_evaluar[0]["fecha"] if actuaciones_evaluar else None
            hallazgos.append({
                "etapa": "4 AUDIENCIA",
                "fase": "4.1 FIJACION FECHA AUDIENCIA",
                "fecha": fecha_ref,
                "prioridad": cls.obtener_indice_fase("4.1 FIJACION FECHA AUDIENCIA"),
                "actuacion": "CALIFICACION DE CONTESTACION"
            })

        if not hallazgos and texto_global:
            norm_global = normalizar_texto(texto_global)
            for etapa, fase, terminos in cls.TAXONOMIA_COMPLETA:
                for term in terminos:
                    term_norm = normalizar_texto(term)
                    if cls._termino_procesal_presente(norm_global, term_norm):
                        prioridad = cls.obtener_indice_fase(fase)
                        fecha_ref = actuaciones_evaluar[0]["fecha"] if actuaciones_evaluar else None
                        hallazgos.append({
                            "etapa": etapa,
                            "fase": fase,
                            "fecha": fecha_ref,
                            "prioridad": prioridad,
                            "actuacion": "TEXTO_GLOBAL"
                        })
                        break

        if not hallazgos:
            if actuaciones_evaluar:
                fecha_ref = actuaciones_evaluar[0].get("fecha")
                hallazgos.append({
                    "etapa": "1 PRESENTACION Y CALIFICACION",
                    "fase": "1.1 PRESENTAR DEMANDA",
                    "fecha": fecha_ref,
                    "prioridad": cls.obtener_indice_fase("1.1 PRESENTAR DEMANDA"),
                    "actuacion": actuaciones_evaluar[0].get("detalle", "")
                })
            else:
                return ResultadoInferencia(None, None, None)

        # PASO 4: Emitir clasificación respetando el avance en la rama activa.
        hallazgos_ordenados = sorted(hallazgos, key=lambda x: x["prioridad"], reverse=True)
        fase_mas_avanzada = hallazgos_ordenados[0]["fase"]
        mejor = cls._hallazgo_mas_reciente(hallazgos, fase_mas_avanzada)
        if mejor is None:
            mejor = hallazgos_ordenados[0]

        decision = dict(mejor)
        fase_original = decision["fase"]
        fecha_original = decision.get("fecha")
        regla_aplicada = "hallazgo_taxonomia"

        # --- APLICACIÓN DE LAS 7 REGLAS DE NEGOCIO DEL MOLDE ---
        texto_actuaciones_unido = " ".join([normalizar_texto(a.get("detalle", "")) for a in actuaciones_evaluar])

        # Regla 2: citación no realizada sin una citación exitosa posterior.
        actuaciones_normalizadas = [
            (act, normalizar_texto(act.get("detalle", "")))
            for act in actuaciones_evaluar
        ]
        citaciones_fallidas = [act for act, norm in actuaciones_normalizadas if cls._es_citacion_fallida_explicita(norm)]
        citaciones_pendientes = [
            act for act, norm in actuaciones_normalizadas
            if "RAZON ENVIO A CITACIONES" in norm
            and not cls._es_citacion_fallida_explicita(norm)
        ]
        citaciones_exitosas = [act for act, norm in actuaciones_normalizadas if cls._es_citacion_exitosa(norm)]
        citaciones_prensa = [
            act for act, norm in actuaciones_normalizadas
            if any(k in norm for k in ("CITACION POR PRENSA", "CITACION POR LA PRENSA", "POR LA PRENSA EN UNO DE LOS PERIODICOS", "EXTRACTO DE CITACION", "ART 56", "ART. 56"))
            and not cls._es_citacion_fallida_explicita(norm)
        ]

        tiene_fallo_no_resuelto = False
        if citaciones_fallidas:
            stop_words = {"DEMANDADO", "DEMANDADA", "ACTOR", "ACTORA", "SENOR", "SENORA", "SENORES", "CITADO", "CITADA", "CITACIONES", "CITACION", "RAZON", "DIRECCION", "INCORRECTA", "ENVIO", "GESTION", "REALIZADA", "CITADOR", "BOLETA", "NULIDAD", "FALTA", "DENTRO", "CAUSA", "CONSTA", "PROCESO", "AUTO", "SIDO", "PORQUE", "CONSECUENCIA", "SEGUNDO", "PRIMERO", "PRIMERA", "TERCERO", "TERCERA", "CUARTO", "CUARTA"}
            for item_fallo in citaciones_fallidas:
                act_fallo = item_fallo[0] if isinstance(item_fallo, tuple) else item_fallo
                norm_fallo = item_fallo[1] if isinstance(item_fallo, tuple) else normalizar_texto(item_fallo.get("detalle", ""))
                fecha_fallo = cls._fecha_ordenable(act_fallo.get("fecha"))
                match_persona = re.search(r"\(PERSONA\s+[^\)]+\)", norm_fallo)
                persona_str = match_persona.group(0) if match_persona else None
                palabras_fallo = [w for w in re.findall(r"\b[A-Z]{4,}\b", norm_fallo) if w not in stop_words]

                exito_posterior = False
                for item_exito in (citaciones_exitosas + citaciones_prensa):
                    act_exito = item_exito[0] if isinstance(item_exito, tuple) else item_exito
                    norm_exito = item_exito[1] if isinstance(item_exito, tuple) else normalizar_texto(item_exito.get("detalle", ""))
                    fecha_exito = cls._fecha_ordenable(act_exito.get("fecha"))
                    es_generic_label = any(k in norm_exito for k in ("- RAZON", "(RAZON)", "RAZON")) and not any(k in norm_exito for k in ("BOLETA 3", "EN PERSONA", "NOTIFICADA", "PRENSA", "EXTRACTO"))
                    if fecha_exito > fecha_fallo or (fecha_exito == fecha_fallo and not es_generic_label):
                        if persona_str:
                            if persona_str in norm_exito:
                                exito_posterior = True
                                break
                        elif palabras_fallo:
                            if any(re.search(r"\b" + p + r"\b", norm_exito) for p in palabras_fallo):
                                exito_posterior = True
                                break
                        else:
                            exito_posterior = True
                            break
                if not exito_posterior:
                    tiene_fallo_no_resuelto = True
                    break

        fallo_sin_exito_posterior = tiene_fallo_no_resuelto
        pendiente_sin_exito = bool(citaciones_pendientes) and not (citaciones_exitosas or citaciones_prensa)
        fase_hasta_citacion = cls.obtener_indice_fase("2.1 CITACION (PERSONA/BOLETA)")
        evidencia_posterior_a_citacion = (
            decision.get("prioridad", -1) > fase_hasta_citacion
        )
        if (fallo_sin_exito_posterior or pendiente_sin_exito) and not evidencia_posterior_a_citacion:
            evidencia = cls._hallazgo_calificacion_principal(
                cls._hallazgos_fase_en_actuaciones(
                    actuaciones, "1.3 CALIFICACION"
                )
            )
            decision = cls._decision_con_evidencia("regla_2_citacion_fallida", "1 PRESENTACION Y CALIFICACION", "1.3 CALIFICACION", evidencia)
            regla_aplicada = "regla_2_citacion_fallida"

        # Regla 5: Abandono por falta de impulso procesal con razón de ejecutoria
        tiene_abandono = "ABANDONO POR FALTA DE IMPULSO PROCESAL" in texto_actuaciones_unido
        tiene_ejecutoria = any(k in texto_actuaciones_unido for k in ["RAZON DE EJECUTORIA", "EJECUTORIADA"])
        if tiene_abandono and tiene_ejecutoria:
            evidencia = cls._hallazgo_calificacion_principal(
                cls._hallazgos_fase_en_actuaciones(
                    actuaciones, "1.3 CALIFICACION"
                )
            )
            decision = cls._decision_con_evidencia("regla_5_abandono_ejecutoria", "1 PRESENTACION Y CALIFICACION", "1.3 CALIFICACION", evidencia)
            regla_aplicada = "regla_5_abandono_ejecutoria"

        # Regla 6: Acuerdo de Mediación antes de Razón de Ejecutoria
        tiene_mediacion = any(k in texto_actuaciones_unido for k in ["ACUERDO DE MEDIACION", "ACTA DE MEDIACION", "MEDIACIÓN"])
        if tiene_mediacion and not tiene_ejecutoria:
            evidencia = cls._hallazgo_mas_reciente(hallazgos, "4.3 ACUERDO DE MEDIACION")
            decision = cls._decision_con_evidencia("regla_6_mediacion_sin_ejecutoria", "4 AUDIENCIA", "4.3 ACUERDO DE MEDIACION", evidencia)
            regla_aplicada = "regla_6_mediacion_sin_ejecutoria"

        # Regla 7: Nombramiento de Perito sin Informe Pericial posterior
        tiene_nombramiento_perito = any(k in texto_actuaciones_unido for k in ["NOMBRAMIENTO DE PERITO", "PERITO LIQUIDADOR NOMBRADO", "ACTA SORTEO PERITO"])
        tiene_informe_perito = any(k in texto_actuaciones_unido for k in ["INFORME PERICIAL", "INFORME DEL PERITO", "INFORME PERITO LIQUIDADOR"])

        # El portal SATJE etiqueta el escrito de informe pericial genericamente como "ESCRITO"
        # con contenido "ANEXOS, Escrito, FePresentacion" — sin escribir "INFORME PERICIAL" en el texto.
        # Si hay un ESCRITO posterior al NOMBRAMIENTO DE PERITO, tratarlo como confirmacion del informe.
        if tiene_nombramiento_perito and not tiene_informe_perito:
            actuaciones_ord = sorted(actuaciones_evaluar, key=lambda a: cls._fecha_ordenable(a.get("fecha")))
            fecha_ultimo_nombramiento = None
            for a in actuaciones_ord:
                norm_a = normalizar_texto(a.get("detalle", ""))
                if "NOMBRAMIENTO DE PERITO" in norm_a or "PERITO LIQUIDADOR NOMBRADO" in norm_a or "ACTA SORTEO PERITO" in norm_a:
                    fecha_ultimo_nombramiento = cls._fecha_ordenable(a.get("fecha"))
            if fecha_ultimo_nombramiento:
                for a in actuaciones_ord:
                    norm_a = normalizar_texto(a.get("detalle", ""))
                    fecha_a = cls._fecha_ordenable(a.get("fecha"))
                    if fecha_a > fecha_ultimo_nombramiento and any(k in norm_a for k in ("ESCRITO", "ANEXOS", "FEPRESENTACION", "INFORME")):
                        tiene_informe_perito = True
                        break

        if decision["fase"] == "6.1 LIQUIDACION PERITO LIQUIDADOR" and not tiene_informe_perito:
            evidencia_ejecutoria = cls._hallazgo_mas_reciente(
                hallazgos, "5.3 SENTENCIA EJECUTORIADA"
            )
            evidencia = evidencia_ejecutoria or decision
            decision = cls._decision_con_evidencia(
                "regla_7_perito_sin_informe", "5 SENTENCIA",
                "5.3 SENTENCIA EJECUTORIADA", evidencia,
            )
            regla_aplicada = "regla_7_perito_sin_informe"

        ultima_etapa = decision["etapa"]
        ultima_fase = decision["fase"]
        fecha_fin = decision.get("fecha")
        actuacion_respaldo = decision.get("actuacion")

        # Regla 1: Remate o Congelamiento (no avanzar a siguiente fase)
        mensaje_especial = None
        tiene_derivacion_mediacion = any(k in texto_actuaciones_unido for k in ["DERIVACION A MEDIACION", "ARCHIVO POR ACUERDO DE MEDIACION", "ACTA DE MEDIACION CON ACUERDO", "ACTA DE MEDIACION"])
        if tiene_derivacion_mediacion and ultima_fase in ("4.3 ACUERDO DE MEDIACION", "5.3 SENTENCIA EJECUTORIADA", "5.1 SENTENCIA EMITIDA POR EL JUEZ"):
            mensaje_especial = "REVISION MANUAL"

        if ultima_fase == "6.4 REMATE":
            etapa_actual = "6 LIQUIDACION Y EMBARGO"
            fase_actual = "6.4 REMATE"
            mensaje_especial = "CASO SOLVENTADO POR REMATE"
        elif ultima_fase == "6.5 CONGELAMIENTO DE CUENTAS / CIERRE":
            etapa_actual = "6 LIQUIDACION Y EMBARGO"
            fase_actual = "6.5 CONGELAMIENTO DE CUENTAS / CIERRE"
            mensaje_especial = "CASO SOLVENTADO POR CONGELAMIENTO"
        elif mensaje_especial == "REVISION MANUAL":
            etapa_actual = "REVISION MANUAL"
            fase_actual = "REVISION MANUAL"
        else:
            etapa_actual, fase_actual = cls.calcular_siguiente_fase(ultima_fase)

        return ResultadoInferencia(
            ultima_etapa=ultima_etapa,
            ultima_fase=ultima_fase,
            fecha_fin=fecha_fin,
            etapa_actual=etapa_actual,
            fase_actual=fase_actual,
            mensaje_especial=mensaje_especial,
            actuacion_respaldo=actuacion_respaldo,
            regla_aplicada=regla_aplicada,
            fase_original=fase_original,
            fecha_original=fecha_original
        )


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
                if MotorInferenciaProcesal._termino_procesal_presente(
                    texto_norm, term_norm
                ):
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
            res_inf = MotorInferenciaProcesal.inferir_estado_procesal(
                actuaciones, texto_global=soup.get_text(" ", strip=True)
            )

            if res_inf and res_inf.get("ULTIMA_ETAPA"):
                etapa_inferida = res_inf.get("ULTIMA_ETAPA")
                fase_inferida = res_inf.get("ULTIMA_FASE")
                fecha_inferida = res_inf.get("FECHA_FIN_ULTIMA_FASE")

                nav_arbol.bajar_nivel(f"Inferencia Autónoma exitosa -> '{fase_inferida}' en fecha {fecha_inferida}")
                resultado["ETAPA_PROCESAL"] = etapa_inferida
                resultado["FASE_PROCESAL"] = fase_inferida
                resultado["FECHA INICIAL FASE ACTUAL"] = fecha_inferida

                # Campos enriquecidos para nuevas columnas MOLDE
                resultado["ULTIMA ETAPA"] = etapa_inferida
                resultado["ULTIMA FASE"] = fase_inferida
                resultado["FECHA FIN ULTIMA FASE"] = resultado["FECHA INICIAL FASE ACTUAL"]
                resultado["ETAPA ACTUAL"] = res_inf.get("ETAPA_ACTUAL") or etapa_inferida
                resultado["FASE ACTUAL"] = res_inf.get("FASE_ACTUAL") or fase_inferida
                resultado["FECHA INICIO FASE ACTUAL"] = resultado["FECHA FIN ULTIMA FASE"]
                if res_inf.get("MENSAJE_ESPECIAL"):
                    resultado["COMENTARIO_ULTIMO"] = res_inf.get("MENSAJE_ESPECIAL")
                
                # Log estructurado de la decisión de fase para auditoría
                try:
                    log_payload = {
                        "source": "dom",
                        "reason": "inferencia_autonoma",
                        "fase_deducida": fase_inferida,
                        "etapa": etapa_inferida,
                        "fase_original": res_inf.get("FASE_ORIGINAL"),
                        "fecha_original": res_inf.get("FECHA_ORIGINAL"),
                        "fase_final": fase_inferida,
                        "fecha_final": resultado["FECHA INICIAL FASE ACTUAL"],
                        "actuacion_respaldo": res_inf.get("ACTUACION_RESPALDO"),
                        "regla_aplicada": res_inf.get("REGLA_APLICADA"),
                        "fecha_elegida": resultado["FECHA INICIAL FASE ACTUAL"],
                        "num_actuaciones": len(actuaciones)
                    }
                    logger.info("[DECISION_FASE] %s", json.dumps(log_payload, ensure_ascii=False))
                except Exception:
                    pass
            elif actuaciones:
                # Fallback contextual si se encontraron actuaciones pero ninguna cuadró strictly
                fecha_fallback = actuaciones[0]["fecha"]
                resultado["FECHA INICIAL FASE ACTUAL"] = fecha_fallback
                resultado["FECHA FIN ULTIMA FASE"] = fecha_fallback
                resultado["ULTIMA ETAPA"] = "ESTADO DESCONOCIDO"
                resultado["ULTIMA FASE"] = actuaciones[0]["detalle"][:100]
                resultado["ETAPA ACTUAL"] = "ESTADO DESCONOCIDO"
                resultado["FASE ACTUAL"] = actuaciones[0]["detalle"][:100]
                resultado["FECHA INICIO FASE ACTUAL"] = fecha_fallback
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
