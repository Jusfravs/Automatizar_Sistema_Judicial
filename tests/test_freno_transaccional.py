import importlib
import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from src.gestor_casos import GestorCasos
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
    def crear_bot(self, **navegacion):
        return BotJudicial("https://ejemplo.local", navegacion)

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
        bot._activar_captcha_con_click_inicial = (
            lambda causa, intento: llamadas.append("activar_captcha")
        )
        bot._resolver_o_esperar_captcha = (
            lambda causa, intento: llamadas.append("resolver_captcha")
        )
        bot._enviar_busqueda_una_vez = (
            lambda causa, intento: llamadas.append("enviar")
        )
        bot._esperar_despues_captcha = (
            lambda causa: llamadas.append("esperar_10s")
        )
        bot._esperar_resultados = (
            lambda causa: llamadas.append("resultados") or "SIN_RESULTADOS"
        )
        bot._volver_al_buscador = lambda causa: llamadas.append("volver") or True

        resultado = bot.procesar_flujo_judicatura("23331-2022-02089")

        self.assertEqual(
            llamadas,
            [
                "preparar", "activar_captcha", "resolver_captcha", "esperar_10s",
                "enviar", "resultados", "volver",
            ],
        )
        self.assertEqual(resultado["estado"], "SIN_RESULTADOS")
        self.assertTrue(resultado["regreso_confirmado"])

    def test_flujo_marca_notificacion_sin_resultados_para_revision_manual(self):
        bot = self.crear_bot()
        llamadas = []
        bot._preparar_busqueda = lambda causa: llamadas.append("preparar") or causa
        bot._cambiar_estado_navegacion = lambda *args, **kwargs: None
        bot._activar_captcha_con_click_inicial = (
            lambda causa, intento: llamadas.append("activar_captcha")
        )
        bot._resolver_o_esperar_captcha = (
            lambda causa, intento: llamadas.append("resolver_captcha")
        )
        bot._enviar_busqueda_una_vez = (
            lambda causa, intento: llamadas.append("enviar")
        )
        bot._esperar_despues_captcha = (
            lambda causa: llamadas.append("esperar_10s")
        )
        bot._esperar_resultados = lambda causa: (
            llamadas.append("resultados")
            or "VERIFICACION_MANUAL_SIN_RESULTADOS"
        )
        bot._volver_al_buscador = lambda causa: llamadas.append("volver") or True

        resultado = bot.procesar_flujo_judicatura("12331-2016-1181")

        self.assertEqual(resultado["estado"], "ERROR_VERIFICACION_MANUAL")
        self.assertEqual(
            resultado["error"],
            "Verificar manualmente (La consulta no devolvi\u00f3 resultados)",
        )
        self.assertFalse(resultado["requiere_reintento"])
        self.assertTrue(resultado["regreso_confirmado"])
        self.assertEqual(llamadas.count("resultados"), 1)

    def test_busqueda_rechazada_reintenta_sin_doble_click(self):
        bot = self.crear_bot(max_reintentos_transicion=2)
        bot._intento_actual = "intento-global"
        bot.ultimo_estado_navegacion = "PREPARAR_BUSCADOR"
        preparados = []
        enviados = []
        evidencias = []
        respuestas = iter([
            RuntimeError("BUSQUEDA_RECHAZADA_FORMULARIO"),
            {"fila": True},
        ])

        bot._preparar_busqueda = (
            lambda causa: preparados.append(causa) or "1233120140845"
        )
        bot._esperar_busqueda_habilitada = lambda causa: None
        bot._esperar_despues_captcha = lambda causa: None
        bot._enviar_busqueda_una_vez = (
            lambda causa, intento: enviados.append(intento)
        )
        bot._guardar_evidencia_busqueda = (
            lambda causa, intento, error: evidencias.append((intento, str(error))) or {}
        )

        def cambiar(causa, anterior, siguiente, accion, **extra):
            bot.ultimo_estado_navegacion = siguiente

        def esperar(causa):
            respuesta = next(respuestas)
            if isinstance(respuesta, Exception):
                bot.ultimo_estado_navegacion = "BUSQUEDA_RECHAZADA"
                raise respuesta
            return respuesta

        bot._cambiar_estado_navegacion = cambiar
        bot._esperar_resultados = esperar

        resultado = bot._buscar_resultado_con_reintentos(
            "12331-2014-0845", "1233120140845"
        )

        self.assertEqual(resultado, {"fila": True})
        self.assertEqual(preparados, ["12331-2014-0845"] * 2)
        self.assertEqual(len(enviados), 2)
        self.assertNotEqual(enviados[0], enviados[1])
        self.assertEqual(evidencias, [(1, "BUSQUEDA_RECHAZADA_FORMULARIO")])

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
            [{
                "estado": "COMPLETA",
                "descriptor": {"fecha_ingreso": "24/02/2023 10:30"},
                "datos": {
                    "FECHA INICIO JUICIO": "01/03/2023",
                    "HISTORIAL_ACTUACIONES": [actuacion],
                },
            }],
        )

        consolidada = resultado["datos"]["HISTORIAL_ACTUACIONES"][0]
        self.assertEqual(consolidada["ORIGEN_CARPETA"], "carpeta-1")
        self.assertEqual(resultado["estado"], "COMPLETADO")
        self.assertEqual(resultado["carpetas_descubiertas"], 1)
        self.assertEqual(resultado["carpetas_completas"], 1)
        self.assertEqual(resultado["datos"]["FECHA INICIO JUICIO"], "24/02/2023")

    def test_actualizar_caso_actualiza_todas_las_filas_del_mismo_juicio(self):
        gestor = GestorCasos.__new__(GestorCasos)
        gestor.df = pd.DataFrame({
            "NUMERO_JUICIO": ["23331-2022-02089", "23331-2022-02089", "OTRA"],
            "ESTADO.1": ["ACTIVO", "FIN", "ACTIVO"],
            "ULTIMA ETAPA": [None, None, None],
        })

        actualizado = gestor.actualizar_caso(
            "23331-2022-02089", {"ULTIMA ETAPA": "6 LIQUIDACION Y EMBARGO"}
        )

        self.assertTrue(actualizado)
        self.assertEqual(
            gestor.df.loc[:1, "ULTIMA ETAPA"].tolist(),
            ["6 LIQUIDACION Y EMBARGO", "6 LIQUIDACION Y EMBARGO"],
        )
        self.assertIsNone(gestor.df.loc[2, "ULTIMA ETAPA"])


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
