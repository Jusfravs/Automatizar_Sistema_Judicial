import json
import unittest
from pathlib import Path

from src.agente_extractor import AgenteExtractor
from src.motor_busqueda_web import BotJudicial


FIXTURE_DIR = Path(__file__).parent.parent / "data" / "temp_htmls"


def load_json(name):
    p = FIXTURE_DIR / name
    assert p.exists(), f"Fixture not found: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


def load_html(name):
    p = FIXTURE_DIR / name
    assert p.exists(), f"Fixture not found: {p}"
    return p.read_text(encoding="utf-8")


class TestExtraccionIntegration(unittest.TestCase):
    def test_api_mandamiento_detection(self):
        bot = BotJudicial(url_portal="https://example.local")
        # Simular paquete API interceptado por la página con la forma esperada por el motor
        # (lista de dicts donde cada dict puede contener 'actuaciones')
        api_payload = [{"actuaciones": [{"fecha": "2022-06-15", "actuacion": "Mandamiento de ejecución"}]}]
        bot.paquetes_api_interceptados = [{"url": "https://api.mock/causa/23331-2022-04261", "data": api_payload}]

        datos = bot._ejecutar_extraccion_detalles(numero_juicio="23331-2022-04261")

        self.assertIsNotNone(datos)
        self.assertEqual(datos["ULTIMA FASE"], "6.2 MANDAMIENTO DE EJECUCION")
        self.assertEqual(datos["FASE ACTUAL"], "6.3 EMBARGO")
        self.assertEqual(datos["FASE_PROCESAL"], datos["FASE ACTUAL"])
        self.assertEqual(datos["ETAPA_PROCESAL"], datos["ETAPA ACTUAL"])
        self.assertEqual(datos["FECHA FIN ULTIMA FASE"], "2022-06-15")
        self.assertEqual(datos["FECHA INICIAL FASE ACTUAL"], "2022-06-15")

    def test_api_usa_fecha_de_la_actuacion_detectada(self):
        """La boleta pendiente inicia citación sin cerrar la calificación previa."""
        bot = BotJudicial(url_portal="https://example.local")
        api_payload = [{
            "fechaIngreso": "2020-01-01",
            "actuaciones": [
                {"fechaCrea": "10/01/2022", "actuacion": "Calificación de la demanda"},
                {"fechaCrea": "15/01/2022", "actuacion": "Boleta de citacion al demandado"},
            ]
        }]
        bot.paquetes_api_interceptados = [{"url": "https://api.mock/causa/fecha", "data": api_payload}]

        datos = bot._ejecutar_extraccion_detalles(numero_juicio="fecha-actuacion")

        self.assertEqual(datos["ULTIMA FASE"], "1.3 CALIFICACION")
        self.assertEqual(datos["FASE ACTUAL"], "2.1 CITACION (PERSONA/BOLETA)")
        self.assertEqual(datos["FASE_PROCESAL"], datos["FASE ACTUAL"])
        self.assertEqual(datos["ETAPA_PROCESAL"], datos["ETAPA ACTUAL"])
        self.assertEqual(datos["FECHA INICIAL FASE ACTUAL"], "15/01/2022")
        self.assertEqual(datos["FECHA INICIO FASE ACTUAL"], "15/01/2022")
        self.assertEqual(datos["FECHA FIN ULTIMA FASE"], "10/01/2022")

    def test_boleta_reiterada_sin_constancia_sigue_pendiente(self):
        """El número de intento no acredita la citación del demandado."""
        for titulo in (
            "BOLETA DE CITACION AL DEMANDADO - BOLETA 3",
            "BOLETA DE CITACION AL DEMANDADO - TERCERA GESTION",
        ):
            with self.subTest(titulo=titulo):
                bot = BotJudicial(url_portal="https://example.local")
                bot.paquetes_api_interceptados = [{
                    "url": "https://api.mock/causa/sintetica",
                    "data": [{"actuaciones": [
                        {"fecha": "10/01/2022", "actuacion": "CALIFICACION DE LA DEMANDA"},
                        {"fecha": "15/01/2022", "actuacion": titulo},
                    ]}],
                }]

                datos = bot._ejecutar_extraccion_detalles(numero_juicio="causa-sintetica")

                self.assertEqual(datos["ULTIMA FASE"], "1.3 CALIFICACION")
                self.assertEqual(datos["FASE ACTUAL"], "2.1 CITACION (PERSONA/BOLETA)")
                self.assertEqual(datos["ETAPA_PROCESAL"], datos["ETAPA ACTUAL"])
                self.assertEqual(datos["FASE_PROCESAL"], datos["FASE ACTUAL"])
                self.assertEqual(datos["FECHA FIN ULTIMA FASE"], "10/01/2022")
                self.assertEqual(datos["FECHA INICIAL FASE ACTUAL"], "15/01/2022")
                self.assertEqual(datos["FECHA INICIO FASE ACTUAL"], "15/01/2022")

    def test_boleta_no_notificada_no_equivale_a_notificada(self):
        """La negación explícita impide acreditar 2.1; la constancia positiva sí lo acredita."""
        escenarios = (
            (
                "BOLETA DE CITACION AL DEMANDADO NO NOTIFICADA",
                "1.3 CALIFICACION",
                "2.1 CITACION (PERSONA/BOLETA)",
                "10/01/2022",
            ),
            (
                "BOLETA DE CITACION AL DEMANDADO NOTIFICADA",
                "2.1 CITACION (PERSONA/BOLETA)",
                "CONTESTACION",
                "15/01/2022",
            ),
        )
        for titulo, ultimo_hito, fase_actual, fecha_fin in escenarios:
            with self.subTest(titulo=titulo):
                bot = BotJudicial(url_portal="https://example.local")
                bot.paquetes_api_interceptados = [{
                    "url": "https://api.mock/causa/sintetica",
                    "data": [{"actuaciones": [
                        {"fecha": "10/01/2022", "actuacion": "CALIFICACION DE LA DEMANDA"},
                        {"fecha": "15/01/2022", "actuacion": titulo},
                    ]}],
                }]

                datos = bot._ejecutar_extraccion_detalles(numero_juicio="causa-sintetica")

                self.assertEqual(datos["ULTIMA FASE"], ultimo_hito)
                self.assertEqual(datos["FASE ACTUAL"], fase_actual)
                self.assertEqual(datos["ETAPA_PROCESAL"], datos["ETAPA ACTUAL"])
                self.assertEqual(datos["FASE_PROCESAL"], datos["FASE ACTUAL"])
                self.assertEqual(datos["FECHA FIN ULTIMA FASE"], fecha_fin)
                self.assertEqual(datos["FECHA INICIAL FASE ACTUAL"], "15/01/2022")
                self.assertEqual(datos["FECHA INICIO FASE ACTUAL"], "15/01/2022")

    def test_dom_extractor_detects_mandamiento(self):
        extractor = AgenteExtractor()
        html = load_html("training_case.html")

        resultado = extractor.procesar_html_string(html)

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["ULTIMA FASE"], "6.2 MANDAMIENTO DE EJECUCION")
        self.assertEqual(resultado["FASE ACTUAL"], "6.3 EMBARGO")
        self.assertEqual(resultado["FASE_PROCESAL"], resultado["FASE ACTUAL"])

    def test_caso_referencia_conserva_fecha_de_calificacion(self):
        extractor = AgenteExtractor()
        resultado = extractor.procesar_html_string(load_html("23331-2022-04191.html"))

        self.assertEqual(resultado["ULTIMA ETAPA"], "1 PRESENTACION Y CALIFICACION")
        self.assertEqual(resultado["ULTIMA FASE"], "1.3 CALIFICACION")
        self.assertEqual(resultado["ETAPA ACTUAL"], "2 CITACION")
        self.assertEqual(resultado["FASE ACTUAL"], "2.1 CITACION (PERSONA/BOLETA)")
        self.assertEqual(resultado["ETAPA_PROCESAL"], resultado["ETAPA ACTUAL"])
        self.assertEqual(resultado["FASE_PROCESAL"], resultado["FASE ACTUAL"])
        for campo in ("FECHA FIN ULTIMA FASE", "FECHA INICIAL FASE ACTUAL", "FECHA INICIO FASE ACTUAL"):
            with self.subTest(campo=campo):
                self.assertEqual(resultado[campo], "16/12/2022")

    def test_variant_1_dom_multiple_actuaciones(self):
        """Test caso variante 1: Mandamiento en tabla de actuaciones."""
        extractor = AgenteExtractor()
        resultado = extractor.procesar_html_string(load_html("case_variant_1.html"))

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["ULTIMA FASE"], "6.2 MANDAMIENTO DE EJECUCION")
        self.assertEqual(resultado["FASE ACTUAL"], "6.3 EMBARGO")
        self.assertEqual(resultado["FASE_PROCESAL"], resultado["FASE ACTUAL"])
        self.assertGreater(len(resultado.get("HISTORIAL_ACTUACIONES", [])), 0)

    def test_variant_2_api_ejecutivo_type(self):
        """Test caso variante 2: nombreTipoAccion='EJECUTIVO' con actuaciones de CITACION no debe deducir mandamiento."""
        bot = BotJudicial(url_portal="https://example.local")
        data = load_json("case_variant_2_api.json")
        # Inyectar actuaciones sintéticas de citación en el paquete API.
        data["actuaciones"] = [
            {"fecha": "10/01/2022", "actuacion": "Calificación de la demanda"},
            {"fecha": "15/01/2022", "actuacion": "Boleta de citación al demandado"}
        ]

        bot.paquetes_api_interceptados = [{"url": "https://api.mock/causa/54321-2022-00456", "data": [data]}]

        datos = bot._ejecutar_extraccion_detalles(numero_juicio="54321-2022-00456")

        self.assertIsNotNone(datos)
        self.assertEqual(datos["ULTIMA FASE"], "1.3 CALIFICACION")
        self.assertEqual(datos["FASE ACTUAL"], "2.1 CITACION (PERSONA/BOLETA)")
        self.assertEqual(datos["FASE_PROCESAL"], datos["FASE ACTUAL"])
        self.assertEqual(datos["ETAPA_PROCESAL"], datos["ETAPA ACTUAL"])
        self.assertNotIn("MANDAMIENTO", datos["ULTIMA FASE"])
        self.assertEqual(datos["FECHA FIN ULTIMA FASE"], "10/01/2022")
        self.assertEqual(datos["FECHA INICIAL FASE ACTUAL"], "15/01/2022")
        self.assertEqual(datos["FECHA INICIO FASE ACTUAL"], "15/01/2022")
