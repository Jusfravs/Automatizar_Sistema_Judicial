import unittest
from src.agente_extractor import AgenteExtractor, MotorInferenciaProcesal
from src.motor_busqueda_web import BotJudicial


class TestClasificacionArbol(unittest.TestCase):
    """
    Suite de pruebas unitarias para la Regla del Árbol Procesal.
    Verifica que la ubicación procesal se base strictly en la jerarquía
    y rama activa del árbol de actuaciones, previniendo falsos positivos por
    palabras clave aisladas.
    """

    def setUp(self):
        self.extractor = AgenteExtractor()

    def test_segmentacion_por_instancia(self):
        """Verifica que las actuaciones se agrupen correctamente por rama de instancia."""
        actuaciones = [
            {"fecha": "01/01/2023", "detalle": "PRESENTACION DE DEMANDA Y ANEXOS"},
            {"fecha": "10/01/2023", "detalle": "AUTO DE CALIFICACION Y CITESE AL DEMANDADO"},
            {"fecha": "05/06/2023", "detalle": "SEGUNDA INSTANCIA: CORTE PROVINCIAL RECIBE APELACION"},
            {"fecha": "20/06/2023", "detalle": "CORTE PROVINCIAL RESUELVE RECURSO DE APELACION"}
        ]
        
        instancias = MotorInferenciaProcesal._segmentar_por_instancia(actuaciones)
        self.assertIn("PRIMERA INSTANCIA", instancias)
        self.assertIn("SEGUNDA INSTANCIA", instancias)
        self.assertEqual(len(instancias["PRIMERA INSTANCIA"]), 2)
        self.assertEqual(len(instancias["SEGUNDA INSTANCIA"]), 2)

    def test_seleccion_rama_activa(self):
        """Verifica que la rama activa sea la de mayor jerarquía procesal."""
        instancias = {
            "PRIMERA INSTANCIA": [{"fecha": "01/01/2023", "detalle": "CITACION"}],
            "SEGUNDA INSTANCIA": [{"fecha": "10/05/2023", "detalle": "RECURSO DE APELACION EN CORTE PROVINCIAL"}]
        }
        
        nombre_rama, actuaciones_rama = MotorInferenciaProcesal._seleccionar_rama_activa(instancias)
        self.assertEqual(nombre_rama, "SEGUNDA INSTANCIA")
        self.assertEqual(len(actuaciones_rama), 1)

    def test_ejecutivo_en_citacion_no_es_mandamiento(self):
        """
        Un caso de procedimiento EJECUTIVO cuyas actuaciones están en etapa de CITACION
        NO debe clasificarse como MANDAMIENTO DE EJECUCION.
        """
        actuaciones = [
            {"fecha": "01/02/2023", "detalle": "INGRESO DE DEMANDA Y SORTEO"},
            {"fecha": "05/02/2023", "detalle": "AUTO DE CALIFICACION DE LA DEMANDA"},
            {"fecha": "20/02/2023", "detalle": "BOLETA DE CITACION AL DEMANDADO NOTIFICADA EN SU DOMICILIO"}
        ]
        
        etapa, fase, fecha = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(etapa, "2 CITACION")
        self.assertEqual(fase, "2.1 CITACION (PERSONA/BOLETA)")
        self.assertNotEqual(etapa, "6 LIQUIDACION Y EMBARGO")
        self.assertNotEqual(fase, "6.2 MANDAMIENTO DE EJECUCION")

    def test_ejecutivo_con_mandamiento_real(self):
        """
        Un caso que contenga explícitamente el auto de 'Mandamiento de ejecución' en sus actuaciones
        SÍ debe clasificarse como MANDAMIENTO DE EJECUCION.
        """
        actuaciones = [
            {"fecha": "01/02/2023", "detalle": "AUTO DE CALIFICACION"},
            {"fecha": "20/02/2023", "detalle": "CITACION AL DEMANDADO"},
            {"fecha": "10/05/2023", "detalle": "SENTENCIA EMITIDA POR EL JUEZ DECLARA CON LUGAR"},
            {"fecha": "15/06/2023", "detalle": "AUTO DICTA MANDAMIENTO DE EJECUCION Y ORDEN DE PAGO EN 3 DIAS"}
        ]
        
        etapa, fase, fecha = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(etapa, "6 LIQUIDACION Y EMBARGO")
        self.assertEqual(fase, "6.2 MANDAMIENTO DE EJECUCION")
        self.assertEqual(fecha, "15/06/2023")

    def test_sin_embargo_no_activa_embargo_y_prevalece_perito(self):
        actuaciones = [
            {
                "fecha": "29/11/2024",
                "detalle": (
                    "La condena depende de la conducta procesal. Sin embargo, "
                    "tratandose de pagares corresponde aplicar otra norma."
                ),
            },
            {
                "fecha": "12/08/2025",
                "detalle": "NOMBRAMIENTO DE PERITO LIQUIDADOR",
            },
            {
                "fecha": "27/08/2025",
                "detalle": "SE NOTIFICA EL CONTENIDO DEL INFORME PERICIAL",
            },
        ]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertEqual(
            resultado.ultima_fase, "6.1 LIQUIDACION PERITO LIQUIDADOR"
        )
        self.assertEqual(resultado.fecha_fin_ultima_fase, "12/08/2025")

    def test_sin_embargo_con_html_tampoco_activa_embargo(self):
        actuaciones = [{
            "fecha": "29/11/2024",
            "detalle": "SIN&nbsp;<strong>EMBARGO</strong>, SE ACLARA LA NORMA",
        }]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertNotEqual(resultado.ultima_fase, "6.3 EMBARGO")

    def test_orden_real_de_embargo_conserva_fase_6_3(self):
        actuaciones = [{
            "fecha": "10/05/2025",
            "detalle": "SE ORDENA EL EMBARGO DE LOS BIENES DEL EJECUTADO",
        }]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertEqual(resultado.ultima_fase, "6.3 EMBARGO")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "10/05/2025")

    def test_descripcion_inicial_con_liquidacion_no_activa_fase_6_1(self):
        actuaciones = [
            {
                "fecha": "10/02/2026",
                "detalle": (
                    "RECIBIDO EL PROCESO CIVIL, PROCEDIMIENTO EJECUTIVO, "
                    "ASUNTO: COBRO Y LIQUIDACION DE OBLIGACIONES. "
                    "SEGUIDO POR LA PARTE ACTORA CONTRA LA DEMANDADA."
                ) * 3,
            },
            {
                "fecha": "04/03/2026",
                "detalle": "CALIFICACION DE SOLICITUD Y/O DEMANDA",
            },
        ]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertEqual(resultado.ultima_fase, "1.3 CALIFICACION")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "04/03/2026")

    def test_perito_liquidador_real_sigue_activando_fase_6_1(self):
        actuaciones = [
            {
                "fecha": "24/07/2026",
                "detalle": "NOMBRAMIENTO DE PERITO LIQUIDADOR (AUTO DE SUSTANCIACION)",
            },
            {
                "fecha": "25/07/2026",
                "detalle": "SE NOTIFICA EL CONTENIDO DEL INFORME PERICIAL",
            },
        ]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertEqual(resultado.ultima_fase, "6.1 LIQUIDACION PERITO LIQUIDADOR")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "24/07/2026")

    def test_embargo_real_no_retrocede_por_citacion_fallida_antigua(self):
        actuaciones = [
            {"fecha": "26/08/2024", "detalle": "AUTO DE CALIFICACION"},
            {"fecha": "10/09/2024", "detalle": "CITACION: NO REALIZADA - DIRECCION INCORRECTA"},
            {"fecha": "10/11/2025", "detalle": "SE ORDENA EL EMBARGO DE LOS BIENES DEL EJECUTADO"},
        ]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertEqual(resultado.ultima_fase, "6.3 EMBARGO")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "10/11/2025")
        self.assertEqual(resultado.get("REGLA_APLICADA"), "hallazgo_taxonomia")

    def test_ejecutoriado_que_sea_el_auto_no_es_sentencia_ejecutoriada(self):
        actuaciones = [
            {
                "fecha": "04/08/2025",
                "detalle": (
                    "LA DEMANDA SE CALIFICA Y ADMITE A TRAMITE. SE ORDENA LA CITACION. "
                    "EJECUTORIADO QUE SEA EL PRESENTE AUTO, LA PARTE ACTORA DARA "
                    "FACILIDADES PARA OBTENER COPIAS PARA LA CITACION."
                ),
            },
            {
                "fecha": "04/08/2025",
                "detalle": "CALIFICACION DE SOLICITUD Y/O DEMANDA",
            },
        ]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertEqual(resultado.ultima_fase, "1.3 CALIFICACION")
        self.assertNotEqual(resultado.ultima_fase, "5.3 SENTENCIA EJECUTORIADA")

    def test_acta_mediacion_con_efecto_de_sentencia_ejecutoriada_es_5_3(self):
        actuaciones = [{
            "fecha": "05/03/2025",
            "detalle": (
                "EL ACTA DE MEDIACION CON ACUERDO TOTAL TIENE EL EFECTO DE "
                "SENTENCIA EJECUTORIADA Y COSA JUZGADA. SE ARCHIVA LA CAUSA."
            ),
        }]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertEqual(resultado.ultima_fase, "5.3 SENTENCIA EJECUTORIADA")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "05/03/2025")

    def test_incumplimiento_posterior_no_mueve_fecha_del_mandamiento(self):
        actuaciones = [
            {
                "fecha": "06/04/2023",
                "detalle": "MANDAMIENTO DE EJECUCION (AUTO INTERLOCUTORIO)",
            },
            {
                "fecha": "25/05/2023",
                "detalle": (
                    "RAZON: LA PARTE EJECUTADA NO HA PAGADO DENTRO DEL TERMINO "
                    "CONCEDIDO EN EL MANDAMIENTO DE EJECUCION."
                ),
            },
        ]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertEqual(resultado.ultima_fase, "6.2 MANDAMIENTO DE EJECUCION")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "06/04/2023")

    def test_solicitud_de_razon_de_cumplimiento_no_mueve_fecha_mandamiento(self):
        actuaciones = [
            {"fecha": "09/03/2026", "detalle": "MANDAMIENTO DE EJECUCION (AUTO INTERLOCUTORIO)"},
            {
                "fecha": "02/04/2026",
                "detalle": (
                    "SE DISPONE QUE EL SECRETARIO SIENTE RAZON SI LA PARTE "
                    "DEMANDADA DIO CUMPLIMIENTO O NO CON EL MANDAMIENTO DE "
                    "EJECUCION ORDENADO EN AUTOS."
                ),
            },
        ]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertEqual(resultado.ultima_fase, "6.2 MANDAMIENTO DE EJECUCION")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "09/03/2026")

    def test_embargo_informado_de_otro_expediente_no_avanza_a_6_3(self):
        actuaciones = [
            {"fecha": "22/05/2023", "detalle": "MANDAMIENTO DE EJECUCION"},
            {
                "fecha": "16/05/2024",
                "detalle": (
                    "SE INCORPORA OFICIO Y SE PONE EN CONOCIMIENTO QUE DENTRO DE LA "
                    "CAUSA NRO. 23331-2023-00123 SE HA ORDENADO EL EMBARGO DEL BIEN "
                    "INMUEBLE PARA QUE LOS ACREEDORES HAGAN VALER SUS DERECHOS."
                ),
            },
        ]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertEqual(resultado.ultima_fase, "6.2 MANDAMIENTO DE EJECUCION")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "22/05/2023")

    def test_nulidad_por_falta_de_citacion_retrocede_a_calificacion(self):
        actuaciones = [
            {"fecha": "15/12/2022", "detalle": "AUTO DE CALIFICACION"},
            {"fecha": "30/08/2023", "detalle": "NULIDAD POR FALTA DE CITACION (AUTO INTERLOCUTORIO)"},
        ]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertEqual(resultado.ultima_fase, "1.3 CALIFICACION")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "15/12/2022")
        self.assertEqual(resultado.get("REGLA_APLICADA"), "regla_2_citacion_fallida")

    def test_segunda_instancia_activa_clasificacion(self):
        """
        Si un caso tiene Primera Instancia en Citación pero la rama de Segunda Instancia registra Apelación,
        la clasificación debe basarse en la rama de Segunda Instancia.
        """
        actuaciones = [
            {"fecha": "01/01/2023", "detalle": "BOLETA DE CITACION"},
            {"fecha": "10/04/2023", "detalle": "SEGUNDA INSTANCIA CORTE PROVINCIAL RECURSO DE APELACION ADMITIDO"}
        ]
        
        etapa, fase, fecha = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(etapa, "5 SENTENCIA")
        self.assertEqual(fase, "5.2 APELACION")

    def test_keyword_en_html_no_sobreescribe_fase_real(self):
        """
        HTML con 'mandamiento de ejecución' en encabezados o menús no debe alterar la clasificación
        si la tabla de actuaciones indica una etapa previa (ej. Audiencia).
        """
        html_con_menu = """
        <html>
        <body>
            <div class="menu-lateral">Procesos de Mandamiento de Ejecución y Cobranzas</div>
            <table>
                <tr><td>10/03/2023</td><td>AUTO SEÑALA FECHA Y HORA PARA AUDIENCIA PRELIMINAR</td></tr>
            </table>
        </body>
        </html>
        """
        resultado = self.extractor.procesar_html_string(html_con_menu)
        self.assertEqual(resultado["ETAPA_PROCESAL"], "4 AUDIENCIA")
        self.assertIn("AUDIENCIA", resultado["FASE_PROCESAL"])
        self.assertNotIn("MANDAMIENTO", resultado["FASE_PROCESAL"])



    def test_regla_2_usa_fecha_de_calificacion_sin_dependencia_del_orden(self):
        actuaciones_base = [
            {"fecha": "16/12/2022", "detalle": "CALIFICACION DE SOLICITUD Y/O DEMANDA (RAZON DE NOTIFICACION)"},
            {"fecha": "04/07/2023", "detalle": "CITACION: NO REALIZADA - CAMBIO DE DIRECCION"},
            {"fecha": "01/12/2022", "detalle": "PRESENTACION DE DEMANDA"},
        ]
        ordenes = (
            actuaciones_base,
            list(reversed(actuaciones_base)),
            [actuaciones_base[1], actuaciones_base[2], actuaciones_base[0]],
        )
        for actuaciones in ordenes:
            resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
            self.assertEqual(resultado.ultima_etapa, "1 PRESENTACION Y CALIFICACION")
            self.assertEqual(resultado.ultima_fase, "1.3 CALIFICACION")
            self.assertEqual(resultado.fecha_fin_ultima_fase, "16/12/2022")
            self.assertIn("CALIFICACION DE SOLICITUD", resultado.get("ACTUACION_RESPALDO"))
            self.assertEqual(resultado.get("REGLA_APLICADA"), "regla_2_citacion_fallida")

    def test_regla_2_elige_la_calificacion_mas_reciente(self):
        actuaciones = [
            {"fecha": "16/12/2022", "detalle": "AUTO DE CALIFICACION"},
            {"fecha": "10/01/2023", "detalle": "CALIFICACION DE DEMANDA"},
            {"fecha": "04/07/2023", "detalle": "CITACION NO REALIZADA"},
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_etapa, "1 PRESENTACION Y CALIFICACION")
        self.assertEqual(resultado.ultima_fase, "1.3 CALIFICACION")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "10/01/2023")

    def test_regla_2_ignora_mencion_generica_posterior_de_califica(self):
        actuaciones = [
            {"fecha": "19/01/2023", "detalle": "CALIFICACION DE SOLICITUD Y/O DEMANDA (AUTO DE SUSTANCIACION)"},
            {"fecha": "02/03/2023", "detalle": "CITACION: NO REALIZADA - DESCONOCIDO"},
            {"fecha": "10/03/2026", "detalle": "En un auto posterior el juzgador califica la conducta procesal de las partes."},
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_fase, "1.3 CALIFICACION")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "19/01/2023")
        self.assertIn("CALIFICACION DE SOLICITUD", resultado.get("ACTUACION_RESPALDO"))

    def test_regla_5_usa_acto_explicito_y_no_mencion_posterior(self):
        actuaciones = [
            {"fecha": "19/01/2023", "detalle": "CALIFICACION DE SOLICITUD Y/O DEMANDA (RAZON DE NOTIFICACION)"},
            {
                "fecha": "10/03/2026",
                "detalle": (
                    "AUTO QUE DECLARA ABANDONO POR FALTA DE IMPULSO PROCESAL. "
                    "En sus consideraciones califica la conducta de las partes. "
                    "RAZON DE EJECUTORIA."
                ),
            },
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.get("REGLA_APLICADA"), "regla_5_abandono_ejecutoria")
        self.assertEqual(resultado.ultima_fase, "1.3 CALIFICACION")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "19/01/2023")
        self.assertIn("CALIFICACION DE SOLICITUD", resultado.get("ACTUACION_RESPALDO"))

    def test_citacion_realizada_con_dos_puntos_anula_fallo_anterior(self):
        actuaciones = [
            {"fecha": "10/01/2023", "detalle": "AUTO DE CALIFICACION"},
            {"fecha": "04/02/2023", "detalle": "CITACION: NO REALIZADA - CAMBIO DE DIRECCION"},
            {"fecha": "10/02/2023", "detalle": "CITACIÓN: REALIZADA - EN PERSONA"},
            {"fecha": "20/03/2023", "detalle": "SENTENCIA"},
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_fase, "5.1 SENTENCIA EMITIDA POR EL JUEZ")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "20/03/2023")
        self.assertEqual(resultado.get("REGLA_APLICADA"), "hallazgo_taxonomia")

    def test_regla_2_recupera_fecha_calificacion_fuera_de_rama_activa(self):
        actuaciones = [
            {"fecha": "10/01/2023", "detalle": "AUTO DE CALIFICACION"},
            {"fecha": "01/02/2023", "detalle": "CORTE NACIONAL - DESPACHO DEPRECATORIO"},
            {"fecha": "04/02/2023", "detalle": "CITACION: NO REALIZADA - CAMBIO DE DIRECCION"},
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_fase, "1.3 CALIFICACION")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "10/01/2023")
        self.assertEqual(resultado.get("REGLA_APLICADA"), "regla_2_citacion_fallida")

    def test_regla_2_sin_calificacion_no_hereda_fecha_de_citacion(self):
        actuaciones = [{"fecha": "04/07/2023", "detalle": "CITACION NO REALIZADA"}]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_etapa, "1 PRESENTACION Y CALIFICACION")
        self.assertEqual(resultado.ultima_fase, "1.3 CALIFICACION")
        self.assertIsNone(resultado.fecha_fin_ultima_fase)
        self.assertEqual(resultado.get("REGLA_APLICADA"), "regla_2_citacion_fallida")

    def test_boletas_de_notificacion_no_convierten_aclaracion_en_citacion(self):
        actuaciones = [
            {"fecha": "16/01/2023", "detalle": "COMPLETAR Y/O ACLARAR LA SOLICITUD Y/O DEMANDA"},
            {
                "fecha": "17/01/2023",
                "detalle": "MEDIANTE BOLETAS JUDICIALES NOTIFIQUE EL AUTO QUE ANTECEDE AL ABOGADO",
            },
            {"fecha": "27/01/2023", "detalle": "ARCHIVO POR NO COMPLETAR DEMANDA (AUTO INTERLOCUTORIO). NOTIFIQUESE."},
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_fase, "1.2 COMPLETAR/ACLARAR DEMANDA")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "27/01/2023")

    def test_advertencia_de_sentencia_en_auto_inicial_no_es_sentencia(self):
        actuaciones = [
            {
                "fecha": "14/07/2026",
                "detalle": (
                    "LA DEMANDA SE CALIFICA DE CLARA Y COMPLETA Y SE ADMITE A TRAMITE. "
                    "EL DEMANDADO SERA CITADO Y PODRA PROPONER EXCEPCIONES; BAJO "
                    "PREVENCION QUE DE NO HACERLO SE PRONUNCIARA INMEDIATAMENTE SENTENCIA."
                ),
            },
            {"fecha": "14/07/2026", "detalle": "CALIFICACION DE SOLICITUD Y/O DEMANDA (AUTO DE SUSTANCIACION)"},
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_fase, "1.3 CALIFICACION")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "14/07/2026")

    def test_sentencia_real_sigue_reconocida(self):
        actuaciones = [
            {"fecha": "10/01/2026", "detalle": "AUTO DE CALIFICACION"},
            {"fecha": "20/06/2026", "detalle": "SENTENCIA (RESOLUCION)"},
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_fase, "5.1 SENTENCIA EMITIDA POR EL JUEZ")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "20/06/2026")

    def test_citacion_real_prevalece_sobre_advertencia_de_sentencia(self):
        actuaciones = [
            {
                "fecha": "18/12/2025",
                "detalle": (
                    "LA DEMANDA SE CALIFICA Y SE ADMITE A TRAMITE. EL DEMANDADO PODRA "
                    "PROPONER EXCEPCIONES; DE NO HACERLO SE PRONUNCIARA SENTENCIA."
                ),
            },
            {"fecha": "18/12/2025", "detalle": "CALIFICACION DE SOLICITUD Y/O DEMANDA"},
            {"fecha": "13/05/2026", "detalle": "CITACION: REALIZADA - BOLETA FIJADA"},
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_fase, "2.1 CITACION (PERSONA/BOLETA)")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "13/05/2026")

    def test_acta_ambigua_no_anula_una_citacion_fallida(self):
        actuaciones = [
            {"fecha": "14/03/2025", "detalle": "CALIFICACION DE SOLICITUD Y/O DEMANDA"},
            {
                "fecha": "14/03/2025",
                "detalle": "SE REMITIRAN BOLETAS A LA OFICINA DE CITACIONES Y, DE NO CONTESTAR, SE PRONUNCIARA SENTENCIA",
            },
            {"fecha": "02/09/2025", "detalle": "ACTA DE CITACION"},
            {"fecha": "02/09/2025", "detalle": "CITACION: NO REALIZADA - OTROS"},
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.get("REGLA_APLICADA"), "regla_2_citacion_fallida")
        self.assertEqual(resultado.ultima_fase, "1.3 CALIFICACION")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "14/03/2025")

    def test_acta_posterior_confirma_citacion_y_no_retrocede_fase_avanzada(self):
        actuaciones = [
            {"fecha": "10/01/2023", "detalle": "CALIFICACION DE SOLICITUD Y/O DEMANDA"},
            {"fecha": "02/02/2023", "detalle": "RAZON ENVIO A CITACIONES: PROCESO ASIGNADO A UN CITADOR"},
            {"fecha": "10/02/2023", "detalle": "ACTA DE CITACION"},
            {"fecha": "20/04/2023", "detalle": "SENTENCIA (RESOLUCION)"},
            {"fecha": "01/06/2023", "detalle": "NOMBRAMIENTO DE PERITO LIQUIDADOR"},
            {"fecha": "20/06/2023", "detalle": "INFORME DEL PERITO"},
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_fase, "6.1 LIQUIDACION PERITO LIQUIDADOR")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "20/06/2023")

    def test_fallo_posterior_al_acta_retrocede_a_calificacion(self):
        actuaciones = [
            {"fecha": "10/01/2023", "detalle": "CALIFICACION DE SOLICITUD Y/O DEMANDA"},
            {"fecha": "02/02/2023", "detalle": "ACTA DE CITACION"},
            {"fecha": "03/02/2023", "detalle": "CITACION: NO REALIZADA - DIRECCION INCORRECTA"},
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.get("REGLA_APLICADA"), "regla_2_citacion_fallida")
        self.assertEqual(resultado.ultima_fase, "1.3 CALIFICACION")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "10/01/2023")

    def test_referencia_doctrinal_a_corte_nacional_no_crea_casacion(self):
        actuaciones = [
            {
                "fecha": "23/06/2022",
                "detalle": "RAZON DE EJECUTORIA: LA SENTENCIA SE ENCUENTRA EJECUTORIADA",
                "CLAVE_CARPETA": "causa_1",
            },
            {
                "fecha": "02/03/2022",
                "detalle": (
                    "DEPRECATORIO PARA PRACTICAR CITACION. ES UN ASUNTO LOGISTICO, "
                    "TAL COMO LO SENALA LA CORTE NACIONAL DE JUSTICIA EN OFICIO "
                    "CIRCULAR; SE DISPONE DEVOLVER EL DEPRECATORIO."
                ) * 4,
                "CLAVE_CARPETA": "causa_2",
            },
        ]
        segmentos = MotorInferenciaProcesal._segmentar_por_instancia(actuaciones)
        self.assertNotIn("CASACION", segmentos)
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_fase, "5.3 SENTENCIA EJECUTORIADA")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "23/06/2022")

    def test_perito_sin_informe_conserva_fecha_real_de_ejecutoria(self):
        actuaciones = [
            {"fecha": "27/06/2025", "detalle": "SENTENCIA (RESOLUCION)"},
            {"fecha": "19/08/2025", "detalle": "RAZON DE EJECUTORIA (RAZON)"},
            {"fecha": "20/07/2026", "detalle": "NOMBRAMIENTO DE PERITO (AUTO DE SUSTANCIACION)"},
        ]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertEqual(resultado.ultima_fase, "5.3 SENTENCIA EJECUTORIADA")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "19/08/2025")
        self.assertEqual(resultado.fase_actual, "6.1 LIQUIDACION PERITO LIQUIDADOR")
        self.assertEqual(resultado.get("REGLA_APLICADA"), "regla_7_perito_sin_informe")

    def test_perito_sin_ejecutoria_visible_conserva_respaldo_historico(self):
        actuaciones = [
            {"fecha": "06/07/2026", "detalle": "NOMBRAMIENTO DE PERITO (AUTO DE SUSTANCIACION)"},
        ]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertEqual(resultado.ultima_fase, "5.3 SENTENCIA EJECUTORIADA")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "06/07/2026")
        self.assertEqual(resultado.fase_actual, "6.1 LIQUIDACION PERITO LIQUIDADOR")

    def test_publicacion_del_aviso_no_cierra_la_fase_de_remate(self):
        actuaciones = [
            {"fecha": "10/04/2023", "detalle": "ACTA DE EMBARGO"},
            {"fecha": "15/11/2024", "detalle": "SE FIJA FECHA PARA QUE TENGA LUGAR EL REMATE DEL BIEN"},
            {
                "fecha": "19/11/2024",
                "detalle": "PROCEDO A PUBLICAR EL AVISO DE REMATE CORRESPONDIENTE A LA CAUSA",
            },
        ]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertEqual(resultado.ultima_fase, "6.3 EMBARGO")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "10/04/2023")
        self.assertEqual(resultado.fase_actual, "6.4 REMATE")

    def test_cita_doctrinal_de_embargo_no_supera_ejecutoria(self):
        actuaciones = [
            {
                "fecha": "10/07/2019",
                "detalle": (
                    "SENTENCIA. LA DOCTRINA DICE QUE EL JUICIO EJECUTIVO ES UN "
                    "PROCEDIMIENTO PARA LLEVAR A EFECTO MEDIANTE EMBARGO Y VENTA "
                    "DE BIENES EL COBRO DE CREDITOS. SIN EMBARGO, SE ACEPTA LA DEMANDA."
                ),
            },
            {"fecha": "26/07/2019", "detalle": "RAZON DE EJECUTORIA (RAZON)"},
        ]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertEqual(resultado.ultima_fase, "5.3 SENTENCIA EJECUTORIADA")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "26/07/2019")

    def test_peticion_de_embargo_no_supera_mandamiento(self):
        actuaciones = [
            {"fecha": "22/12/2025", "detalle": "MANDAMIENTO DE EJECUCION (AUTO INTERLOCUTORIO)"},
            {
                "fecha": "23/02/2026",
                "detalle": (
                    "VISTOS: AGREGUESE EL ESCRITO Y SE DISPONE: EN RELACION A LA "
                    "PETICION DE EMBARGO DEL AUTOMOTOR, SE EVIDENCIA UNA PRENDA "
                    "VIGENTE, RAZON POR LA CUAL ESTE JUZGADOR NO PUEDE EJECUTAR "
                    "LA PETICION; POR TANTO, SE LO NIEGA."
                ),
            },
        ]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertEqual(resultado.ultima_fase, "6.2 MANDAMIENTO DE EJECUCION")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "22/12/2025")

    def test_mencion_normativa_de_embargo_no_supera_calificacion(self):
        actuaciones = [
            {"fecha": "26/08/2024", "detalle": "AUTO DE CALIFICACION"},
            {
                "fecha": "10/11/2025",
                "detalle": (
                    "EL ACTOR HACE MENCION A LA PROVIDENCIA PREVENTIVA DE SECUESTRO "
                    "Y A LA NORMATIVA PREVISTA PARA EMBARGO, QUE SOLO CABE EN "
                    "EJECUCION. PREVIO A PROVEER, ACLARE SU REQUERIMIENTO."
                ),
            },
        ]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertEqual(resultado.ultima_fase, "1.3 CALIFICACION")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "26/08/2024")

    def test_embargo_no_ordenado_y_remate_negado_no_superan_mandamiento(self):
        actuaciones = [
            {"fecha": "21/05/2026", "detalle": "MANDAMIENTO DE EJECUCION (AUTO INTERLOCUTORIO)"},
            {
                "fecha": "23/07/2026",
                "detalle": (
                    "SE SOLICITA PUBLICACION PARA QUE TERCEROS INTERVENGAN EN EL "
                    "REMATE DEL BIEN. EN LA PRESENTE CAUSA NO SE HA ORDENADO EMBARGO "
                    "DE BIEN ALGUNO, POR LO QUE SE NIEGA LA PUBLICACION SOLICITADA."
                ),
            },
        ]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertEqual(resultado.ultima_fase, "6.2 MANDAMIENTO DE EJECUCION")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "21/05/2026")

    def test_orden_explicita_de_embargo_sigue_siendo_fase_6_3(self):
        actuaciones = [
            {"fecha": "21/05/2026", "detalle": "MANDAMIENTO DE EJECUCION"},
            {"fecha": "23/07/2026", "detalle": "SE ORDENA EL EMBARGO DEL VEHICULO DEL EJECUTADO"},
        ]

        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)

        self.assertEqual(resultado.ultima_fase, "6.3 EMBARGO")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "23/07/2026")

    def test_consulta_a_superintendencia_no_es_congelamiento(self):
        actuaciones = [
            {"fecha": "09/03/2026", "detalle": "MANDAMIENTO DE EJECUCION (AUTO INTERLOCUTORIO)"},
            {
                "fecha": "21/05/2026",
                "detalle": (
                    "OFICIESE A LA SUPERINTENDENCIA DE BANCOS PARA QUE CERTIFIQUE "
                    "SI LOS EJECUTADOS MANTIENEN CUENTAS CORRIENTES O DE AHORROS."
                ),
            },
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_fase, "6.2 MANDAMIENTO DE EJECUCION")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "09/03/2026")

    def test_cuentas_congeladas_con_montos_si_son_fase_6_5(self):
        actuaciones = [
            {"fecha": "09/03/2026", "detalle": "MANDAMIENTO DE EJECUCION"},
            {
                "fecha": "21/05/2026",
                "detalle": (
                    "EL BANCO INFORMA QUE TRES CUENTAS FUERON CONGELADAS POR LOS "
                    "MONTOS DE USD 120, USD 80 Y USD 45."
                ),
            },
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_fase, "6.5 CONGELAMIENTO DE CUENTAS / CIERRE")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "21/05/2026")

    def test_transferencia_de_valores_retenidos_si_es_fase_6_5(self):
        actuaciones = [
            {"fecha": "09/03/2026", "detalle": "MANDAMIENTO DE EJECUCION"},
            {
                "fecha": "25/05/2026",
                "detalle": (
                    "SE DISPONE QUE EL BANCO TRANSFIERA LOS VALORES RETENIDOS A "
                    "LA CUENTA JUDICIAL DE ESTA CAUSA."
                ),
            },
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_fase, "6.5 CONGELAMIENTO DE CUENTAS / CIERRE")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "25/05/2026")

    def test_publicacion_y_fecha_de_remate_no_equivalen_a_remate_ejecutado(self):
        actuaciones = [
            {"fecha": "10/04/2023", "detalle": "ACTA DE EMBARGO"},
            {"fecha": "15/11/2024", "detalle": "SE FIJA FECHA PARA EL REMATE DEL BIEN"},
            {"fecha": "19/11/2024", "detalle": "SE PUBLICA EL AVISO DE REMATE"},
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_fase, "6.3 EMBARGO")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "10/04/2023")
        self.assertEqual(resultado.fase_actual, "6.4 REMATE")

    def test_adjudicacion_acredita_remate_ejecutado(self):
        actuaciones = [
            {"fecha": "10/04/2023", "detalle": "ACTA DE EMBARGO"},
            {"fecha": "19/11/2024", "detalle": "SE PUBLICA EL AVISO DE REMATE"},
            {"fecha": "22/01/2025", "detalle": "AUTO DE ADJUDICACION: SE ADJUDICA EL BIEN AL POSTOR GANADOR"},
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_fase, "6.4 REMATE")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "22/01/2025")

    def test_articulo_372_y_orden_de_pagar_identifican_mandamiento(self):
        actuaciones = [
            {"fecha": "09/06/2025", "detalle": "RAZON DE EJECUTORIA"},
            {
                "fecha": "13/05/2026",
                "detalle": (
                    "DE CONFORMIDAD AL ARTICULO 372 DEL COGEP, SE ORDENA QUE LA "
                    "PARTE EJECUTADA PAGUE USD 3.717,72 EN EL TERMINO DE CINCO DIAS."
                ),
            },
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_fase, "6.2 MANDAMIENTO DE EJECUCION")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "13/05/2026")

    def test_orden_de_pago_mercantil_dentro_de_sentencia_no_es_mandamiento(self):
        actuaciones = [
            {
                "fecha": "31/07/2023",
                "detalle": (
                    "SENTENCIA. SE DETERMINA QUE EL TITULO VALOR CONTIENE UNA "
                    "ORDEN DE PAGO POR SU NATURALEZA MERCANTIL."
                ),
            },
            {"fecha": "04/08/2023", "detalle": "RAZON DE EJECUTORIA"},
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_fase, "5.3 SENTENCIA EJECUTORIADA")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "04/08/2023")

    def test_formula_sentencia_que_antecede_debidamente_ejecutoriada(self):
        actuaciones = [
            {"fecha": "29/10/2018", "detalle": "SENTENCIA (RESOLUCION)"},
            {
                "fecha": "08/11/2018",
                "detalle": (
                    "RAZON: LA SENTENCIA QUE ANTECEDE SE ENCUENTRA "
                    "DEBIDAMENTE EJECUTORIADA POR EL MINISTERIO DE LA LEY."
                ),
            },
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_fase, "5.3 SENTENCIA EJECUTORIADA")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "08/11/2018")

    def test_publicacion_posterior_no_reemplaza_fecha_del_mandamiento(self):
        actuaciones = [
            {"fecha": "08/05/2026", "detalle": "MANDAMIENTO DE EJECUCION (AUTO INTERLOCUTORIO)"},
            {
                "fecha": "22/06/2026",
                "detalle": (
                    "SE DISPONE LA PUBLICACION DEL MANDAMIENTO DE EJECUCION PARA "
                    "CONOCIMIENTO DE TERCEROS POR INCUMPLIMIENTO."
                ),
            },
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_fase, "6.2 MANDAMIENTO DE EJECUCION")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "08/05/2026")

    def test_acta_de_sorteo_no_desplaza_una_calificacion_real(self):
        actuaciones = [
            {"fecha": "07/07/2026", "detalle": "ACTA DE SORTEO"},
            {"fecha": "14/07/2026", "detalle": "CALIFICACION DE SOLICITUD Y/O DEMANDA"},
        ]
        resultado = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        self.assertEqual(resultado.ultima_fase, "1.3 CALIFICACION")
        self.assertEqual(resultado.fecha_fin_ultima_fase, "14/07/2026")

if __name__ == "__main__":
    unittest.main()
