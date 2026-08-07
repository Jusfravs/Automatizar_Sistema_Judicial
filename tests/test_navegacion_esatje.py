import unittest

from src.motor_busqueda_web import BotJudicial
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


class CampoFalso:
    def __init__(self, valor):
        self.valor = valor

    def input_value(self):
        return self.valor


class BotonFalso:
    def __init__(self, habilitado=True, disabled=None, clases="", etiqueta=""):
        self.habilitado = habilitado
        self.disabled = disabled
        self.clases = clases
        self.etiqueta = etiqueta
        self.clicks = 0

    def is_visible(self):
        return True

    def is_enabled(self):
        return self.habilitado

    def get_attribute(self, nombre):
        atributos = {
            "aria-disabled": "false",
            "disabled": self.disabled,
            "class": self.clases,
            "aria-label": self.etiqueta,
        }
        return atributos.get(nombre)

    def scroll_into_view_if_needed(self):
        return None

    def click(self):
        self.clicks += 1


class FilaFalsa:
    def __init__(self, texto):
        self.texto = texto

    def is_visible(self):
        return True

    def inner_text(self):
        return self.texto


class ColeccionFalsa:
    def __init__(self, elementos):
        self.elementos = elementos

    def count(self):
        return len(self.elementos)

    def nth(self, indice):
        return self.elementos[indice]


class PaginaFilasFalsa:
    def __init__(self, filas):
        self.filas = filas

    def locator(self, selector):
        self.ultimo_selector = selector
        return ColeccionFalsa(self.filas)


class PaginaCaptchaFalsa:
    def __init__(self, renderizado):
        self.renderizado = renderizado

    def locator(self, selector):
        return ColeccionFalsa([object()] if self.renderizado else [])


class NavegacionEsatjeTests(unittest.TestCase):
    def crear_bot(self, **navegacion):
        return BotJudicial("https://ejemplo.local", navegacion)

    def test_detecta_montaje_del_captcha(self):
        bot = self.crear_bot()
        bot.page = PaginaCaptchaFalsa(False)
        self.assertFalse(bot._captcha_renderizado())
        bot.page = PaginaCaptchaFalsa(True)
        self.assertTrue(bot._captcha_renderizado())

    def test_canoniza_causa_con_guiones(self):
        self.assertEqual(
            BotJudicial._causa_canonica("23331-2022-02089"),
            "23331202202089",
        )

    def test_formatea_causa_para_la_mascara_del_portal(self):
        self.assertEqual(
            BotJudicial._causa_para_formulario("23331202202089"),
            "23331-2022-02089",
        )
        self.assertEqual(
            BotJudicial._causa_para_formulario("23331-2022-02089"),
            "23331-2022-02089",
        )

    def test_boton_con_disabled_html_no_se_considera_habilitado(self):
        self.assertFalse(BotJudicial._boton_habilitado(BotonFalso(disabled="true")))
        self.assertFalse(
            BotJudicial._boton_habilitado(
                BotonFalso(clases="mat-mdc-button-disabled")
            )
        )
        self.assertTrue(BotJudicial._boton_habilitado(BotonFalso()))

    def test_buscar_hace_un_solo_clic_por_intento(self):
        bot = self.crear_bot()
        campo = CampoFalso("23331-2022-02089")
        boton = BotonFalso()
        bot._input_causa_unico = lambda: campo
        bot._boton_buscar_unico = lambda: boton
        bot._captcha_visible = lambda: False

        bot._enviar_busqueda_una_vez("23331202202089", "intento-1")

        self.assertEqual(boton.clicks, 1)
        with self.assertRaisesRegex(RuntimeError, "DOBLE_CLICK_BUSCAR_BLOQUEADO"):
            bot._enviar_busqueda_una_vez("23331202202089", "intento-1")
        self.assertEqual(boton.clicks, 1)

    def test_buscar_deshabilitado_no_hace_clic(self):
        bot = self.crear_bot(captcha_timeout_ms=0)
        campo = CampoFalso("23331202202089")
        boton = BotonFalso(habilitado=False)
        bot._input_causa_unico = lambda: campo
        bot._boton_buscar_unico = lambda: boton
        bot._captcha_visible = lambda: True
        bot._cambiar_estado_navegacion = lambda *args, **kwargs: None

        with self.assertRaises(PlaywrightTimeoutError):
            bot._esperar_busqueda_habilitada("23331202202089")
        self.assertEqual(boton.clicks, 0)

    def test_resultados_elige_solo_fila_de_causa_canonica(self):
        filas = [
            FilaFalsa("1 14/06/2022 23331202202088 COBRO"),
            FilaFalsa("2 15/06/2022 23331202202089 COBRO"),
        ]
        bot = self.crear_bot()
        bot.page = PaginaFilasFalsa(filas)

        coincidencias = bot._filas_resultado_coincidentes("23331-2022-02089")

        self.assertEqual(coincidencias, [filas[1]])

    def test_paquetes_descarta_otra_causa(self):
        bot = self.crear_bot()
        paquetes = [
            {
                "url": "https://portal/api/actuaciones",
                "data": {"idJuicio": "23331202202089", "actuaciones": []},
            },
            {
                "url": "https://portal/api/actuaciones",
                "data": {"idJuicio": "23331202202088", "actuaciones": []},
            },
        ]

        seleccionados = bot._paquetes_api_de_carpeta(paquetes, "23331-2022-02089")

        self.assertEqual(seleccionados, [paquetes[0]])

    def test_consolidacion_conserva_origen_por_actuacion(self):
        bot = self.crear_bot()
        descriptor = {
            "clave": "DEPENDENCIA JURISDICCIONAL: UNIDAD A CIUDAD: QUININDE",
            "indice_visual": 2,
            "texto": "Dependencia jurisdiccional: Unidad A Ciudad: Quinind?",
        }
        bot._descriptores_carpetas_actuaciones = lambda: [descriptor]
        bot._localizar_fila_carpeta = lambda valor: object()
        bot._boton_carpeta_en_fila = lambda fila, contexto: BotonFalso()
        bot._esperar_actuaciones = lambda causa: True
        bot._volver_a_datos_generales = lambda causa: True
        bot.paquetes_api_interceptados = []
        bot._ejecutar_extraccion_detalles = lambda *args, **kwargs: {
            "HISTORIAL_ACTUACIONES": [{"fecha": "24/02/2023", "detalle": "ACTUACION"}]
        }

        resultado = bot._procesar_todas_las_carpetas("23331202202089")

        actuacion = resultado["HISTORIAL_ACTUACIONES"][0]
        self.assertEqual(actuacion["CAUSA"], "23331202202089")
        self.assertEqual(actuacion["CLAVE_CARPETA"], descriptor["clave"])
        self.assertEqual(actuacion["ORIGEN_DATA"], "DOM")


if __name__ == "__main__":
    unittest.main()

