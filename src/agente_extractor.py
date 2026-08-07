# src/agente_extractor.py
import os
import re
import json
import unicodedata
from datetime import datetime
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
    def calcular_siguiente_fase(cls, fase_actual):
        """
        Dada la fase actual encontrada, retorna la siguiente fase y etapa según ORDEN_FASES.
        Si la fase es la última (6.5), retorna la misma fase.
        Si la fase es 6.4 REMATE o 6.5 CONGELAMIENTO, no avanza.
        """
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
            
            # Detectar cambio de instancia o rama en el árbol de actuaciones
            if any(k in norm for k in ["CORTE PROVINCIAL", "SEGUNDA INSTANCIA", "SALA ESPECIALIZADA", "TRIBUNAL DE ALZADA"]):
                instancia_actual = "SEGUNDA INSTANCIA"
                if instancia_actual not in instancias:
                    instancias[instancia_actual] = []
            elif any(k in norm for k in ["CORTE NACIONAL", "CASACION", "SALA DE LO CONTENCIOSO"]):
                instancia_actual = "CASACION"
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

            if any(k in norm for k in ["SUPERINTENDENCIA DE BANCOS", "AGREGUESE OFICIO EMITIDO POR BANCO", "AGREGUESE EL OFICIO EMITIDO POR EL BANCO"]):
                hallazgos.append({
                    "etapa": "6 LIQUIDACION Y EMBARGO",
                    "fase": "6.5 CONGELAMIENTO DE CUENTAS / CIERRE",
                    "fecha": fecha,
                    "prioridad": cls.obtener_indice_fase("6.5 CONGELAMIENTO DE CUENTAS / CIERRE"),
                    "actuacion": norm
                })

            for etapa, fase, terminos in cls.TAXONOMIA_COMPLETA:
                for term in terminos:
                    term_norm = normalizar_texto(term)
                    if term_norm in norm:
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
                    if term_norm in norm_global:
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
            return ResultadoInferencia(None, None, None)

        # PASO 4: Emitir clasificación respetando el avance en la rama activa.
        hallazgos_ordenados = sorted(hallazgos, key=lambda x: x["prioridad"], reverse=True)
        mejor = hallazgos_ordenados[0]

        decision = dict(mejor)
        fase_original = decision["fase"]
        fecha_original = decision.get("fecha")
        regla_aplicada = "hallazgo_taxonomia"

        # --- APLICACIÓN DE LAS 7 REGLAS DE NEGOCIO DEL MOLDE ---
        texto_actuaciones_unido = " ".join([normalizar_texto(a.get("detalle", "")) for a in actuaciones_evaluar])

        # Regla 2: Citación no realizada / reenvío citación sin citación realizada posterior
        tiene_citacion_fallida = (
            any(k in texto_actuaciones_unido for k in ["CITACION NO REALIZADA", "REENVIO CITACION", "RAZON ENVIO A CITACIONES", "RAZON DE NO CITACION"])
            or ("CITACION" in texto_actuaciones_unido and "NO REALIZADA" in texto_actuaciones_unido)
        )
        tiene_citacion_exitosa = any(k in texto_actuaciones_unido for k in ["CITACION REALIZADA", "BOLETA DE CITACION NOTIFICADA", "ACTA DE CITACION", "CITADO Y NOTIFICADO"])
        if tiene_citacion_fallida and not tiene_citacion_exitosa:
            evidencia = cls._hallazgo_mas_reciente(hallazgos, "1.3 CALIFICACION")
            decision = cls._decision_con_evidencia("regla_2_citacion_fallida", "1 PRESENTACION Y CALIFICACION", "1.3 CALIFICACION", evidencia)
            regla_aplicada = "regla_2_citacion_fallida"

        # Regla 5: Abandono por falta de impulso procesal con razón de ejecutoria
        tiene_abandono = "ABANDONO POR FALTA DE IMPULSO PROCESAL" in texto_actuaciones_unido
        tiene_ejecutoria = any(k in texto_actuaciones_unido for k in ["RAZON DE EJECUTORIA", "EJECUTORIADA"])
        if tiene_abandono and tiene_ejecutoria:
            evidencia = cls._hallazgo_mas_reciente(hallazgos, "1.3 CALIFICACION")
            decision = cls._decision_con_evidencia("regla_5_abandono_ejecutoria", "1 PRESENTACION Y CALIFICACION", "1.3 CALIFICACION", evidencia)
            regla_aplicada = "regla_5_abandono_ejecutoria"

        # Regla 6: Acuerdo de Mediación antes de Razón de Ejecutoria
        tiene_mediacion = any(k in texto_actuaciones_unido for k in ["ACUERDO DE MEDIACION", "ACTA DE MEDIACION", "MEDIACIÓN"])
        if tiene_mediacion and not tiene_ejecutoria:
            evidencia = cls._hallazgo_mas_reciente(hallazgos, "4.3 ACUERDO DE MEDIACION")
            decision = cls._decision_con_evidencia("regla_6_mediacion_sin_ejecutoria", "5 SENTENCIA", "5.3 SENTENCIA EJECUTORIADA", evidencia)
            regla_aplicada = "regla_6_mediacion_sin_ejecutoria"

        # Regla 7: Nombramiento de Perito sin Informe Pericial posterior
        tiene_nombramiento_perito = any(k in texto_actuaciones_unido for k in ["NOMBRAMIENTO DE PERITO", "PERITO LIQUIDADOR NOMBRADO"])
        tiene_informe_perito = any(k in texto_actuaciones_unido for k in ["INFORME PERICIAL", "INFORME DEL PERITO", "INFORME PERITO LIQUIDADOR"])
        if decision["fase"] == "6.1 LIQUIDACION PERITO LIQUIDADOR" and tiene_nombramiento_perito and not tiene_informe_perito:
            evidencia = cls._hallazgo_mas_reciente(hallazgos, "6.1 LIQUIDACION PERITO LIQUIDADOR")
            decision = cls._decision_con_evidencia("regla_7_perito_sin_informe", "5 SENTENCIA", "5.3 SENTENCIA EJECUTORIADA", evidencia)
            regla_aplicada = "regla_7_perito_sin_informe"

        ultima_etapa = decision["etapa"]
        ultima_fase = decision["fase"]
        fecha_fin = decision.get("fecha")
        actuacion_respaldo = decision.get("actuacion")

        # Regla 1: Remate o Congelamiento (no avanzar a siguiente fase)
        mensaje_especial = None
        if ultima_fase == "6.4 REMATE":
            etapa_actual = "6 LIQUIDACION Y EMBARGO"
            fase_actual = "6.4 REMATE"
            mensaje_especial = "CASO SOLVENTADO POR REMATE"
        elif ultima_fase == "6.5 CONGELAMIENTO DE CUENTAS / CIERRE":
            etapa_actual = "6 LIQUIDACION Y EMBARGO"
            fase_actual = "6.5 CONGELAMIENTO DE CUENTAS / CIERRE"
            mensaje_especial = "CASO SOLVENTADO POR CONGELAMIENTO"
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
