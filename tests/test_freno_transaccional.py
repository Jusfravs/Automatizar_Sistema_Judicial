import importlib
import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from src.gestor_cola import GestorCola
from src.motor_busqueda_web import BotJudicial


class BotonFalso:
    def __init__(self):
        self.clicks = 0

    def click(self):
        self.clicks += 1


class PaginaFalsa:
    url = "https://ejemplo.local/actuaciones"

    @staticmethod
    def is_closed():
        return False


class FrenoNavegacionTests(unittest.TestCase):
    def crear_bot(self):
        return BotJudicial("https://ejemplo.local")

    def test_bloqueo_impide_click_real(self):
        bot = self.crear_bot()
        boton = BotonFalso()
        bot._bloqueo_navegacion = {
            "activo": True,
            "token": "intento:carpeta",
            "causa": "23331202202089",
        }

        with self.assertRaisesRegex(RuntimeError, "NAVEGACION_BLOQUEADA"):
            bot._click_navegacion(boton, "click_prohibido")

        self.assertEqual(boton.clicks, 0)
        self.assertEqual(len(bot._intentos_navegacion_bloqueados), 1)

    def test_ventana_api_excluye_respuestas_previas_y_otra_causa(self):
        bot = self.crear_bot()
        bot.paquetes_api_interceptados = [
            {"secuencia": 4, "url": "/api/actuaciones", "data": {"idJuicio": "23331202202089"}},
            {"secuencia": 5, "url": "/api/actuaciones", "data": {"idJuicio": "23331202202088"}},
            {"secuencia": 6, "url": "/api/actuaciones", "data": {"idJuicio": "23331202202089"}},
            {"secuencia": 7, "url": "/api/actuaciones", "data": {"idJuicio": "23331202202089"}},
        ]

        paquetes = bot._paquetes_ventana(5, 6, "23331202202089")

        self.assertEqual([paquete["secuencia"] for paquete in paquetes], [6])

    def test_extraccion_transforma_sin_pagina_ni_navegacion(self):
        bot = self.crear_bot()
        bot.page = None
        bot.extractor.procesar_html_string = lambda contenido: {}
        bot._aplicar_inferencia_consolidada = lambda datos: datos

        datos = bot._ejecutar_extraccion_detalles(
            "23331202202089",
            paquetes_api=[{
                "data": {
                    "idJuicio": "23331202202089",
                    "actuaciones": [{"fecha": "24/02/2023", "detalle": "SENTENCIA"}],
                }
            }],
            contenido_html="<html><body></body></html>",
        )

        self.assertEqual(len(datos["HISTORIAL_ACTUACIONES"]), 1)
        self.assertEqual(datos["ORIGEN_DATA"], "API")

    def test_bloqueo_solo_se_libera_con_manifiesto_terminal(self):
        bot = self.crear_bot()
        bot.page = PaginaFalsa()
        bot._intento_actual = "intento"
        descriptor = {"clave_carpeta": "carpeta"}
        token = bot._activar_bloqueo_navegacion("23331202202089", descriptor)
        with tempfile.TemporaryDirectory() as temporal:
            manifiesto = os.path.join(temporal, "result.json")
            with open(manifiesto, "w", encoding="utf-8") as archivo:
                json.dump({"estado": "COMPLETA"}, archivo)
            bot._finalizar_bloqueo_navegacion(token, manifiesto)

        self.assertIsNone(bot._bloqueo_navegacion)

    def test_flujo_envia_busqueda_y_devuelve_contrato_sin_resultados(self):
        bot = self.crear_bot()
        llamadas = []
        bot._preparar_busqueda = lambda causa: llamadas.append("preparar") or causa
        bot._cambiar_estado_navegacion = lambda *args, **kwargs: None
        bot._esperar_busqueda_habilitada = (
            lambda causa: llamadas.append("esperar_habilitada")
        )
        bot._enviar_busqueda_una_vez = (
            lambda causa, intento: llamadas.append("enviar")
        )
        bot._esperar_resultados = (
            lambda causa: llamadas.append("resultados") or "SIN_RESULTADOS"
        )
        bot._volver_al_buscador = lambda causa: llamadas.append("volver") or True

        resultado = bot.procesar_flujo_judicatura("23331-2022-02089")

        self.assertEqual(
            llamadas,
            ["preparar", "esperar_habilitada", "enviar", "resultados", "volver"],
        )
        self.assertEqual(resultado["estado"], "SIN_RESULTADOS")
        self.assertTrue(resultado["regreso_confirmado"])

    def test_maquina_rechaza_transicion_no_permitida(self):
        bot = self.crear_bot()
        bot.ultimo_estado_navegacion = "MOVIMIENTOS_LISTOS"

        with self.assertRaisesRegex(RuntimeError, "TRANSICION_NO_PERMITIDA"):
            bot._cambiar_estado_navegacion(
                "23331202202089",
                "MOVIMIENTOS_LISTOS",
                "BUSQUEDA_ENVIADA",
                "salto_invalido",
            )

    def test_consolidacion_conserva_origen_y_conteos(self):
        bot = self.crear_bot()
        bot._descriptores_actuales = [{"clave_carpeta": "carpeta-1"}]
        bot._aplicar_inferencia_consolidada = lambda datos: datos
        actuacion = {
            "fecha": "24/02/2023",
            "detalle": "SENTENCIA",
            "CAUSA": "23331202202089",
            "CLAVE_CARPETA": "carpeta-1",
            "ORIGEN_CARPETA": "carpeta-1",
            "DEPENDENCIA_JURISDICCIONAL": "UNIDAD A",
            "CIUDAD_CARPETA": "QUININDÉ",
            "INSTANCIA_CARPETA": "1",
            "ORIGEN_DATA": "API",
        }

        resultado = bot._consolidar_resultados_carpetas(
            "23331202202089",
            [{"estado": "COMPLETA", "datos": {"HISTORIAL_ACTUACIONES": [actuacion]}}],
        )

        consolidada = resultado["datos"]["HISTORIAL_ACTUACIONES"][0]
        self.assertEqual(consolidada["ORIGEN_CARPETA"], "carpeta-1")
        self.assertEqual(resultado["estado"], "COMPLETADO")
        self.assertEqual(resultado["carpetas_descubiertas"], 1)
        self.assertEqual(resultado["carpetas_completas"], 1)


class PersistenciaTransaccionalTests(unittest.TestCase):
    def test_estado_final_parcial_se_confirma_en_misma_transaccion(self):
        with tempfile.TemporaryDirectory() as temporal:
            ruta = os.path.join(temporal, "estado.db")
            cola = GestorCola(ruta_db=ruta)
            cola.poblar_cola(["CAUSA-001"])
            cola.obtener_siguiente()
            cola.registrar_resultado_transaccional(
                "CAUSA-001", {"estado": "PARCIAL"}, "TEST", estado_final="PARCIAL"
            )
            conexion = sqlite3.connect(ruta)
            try:
                estado = conexion.execute(
                    "SELECT estado FROM juicios WHERE numero_causa = ?", ("CAUSA-001",)
                ).fetchone()[0]
            finally:
                conexion.close()
        self.assertEqual(estado, "PARCIAL")

    def test_importar_logger_no_crea_filehandler(self):
        import src.logger_config as logger_config
        with patch("logging.FileHandler") as file_handler:
            importlib.reload(logger_config)
        file_handler.assert_not_called()


if __name__ == "__main__":
    unittest.main()
