import pytest

from src.motor_busqueda_web import BotJudicial


def test_mandamiento_api_reconocido():
    """Simula una respuesta JSON de la API que contiene una actuación 'Mandamiento de ejecución' y verifica que
    el extractor la clasifique como MANDAMIENTO DE EJECUCION (fase 6.2).
    """
    bot = BotJudicial(url_portal="https://example.local")

    # Simular paquete API interceptado
    bot.paquetes_api_interceptados = [
        {
            "url": "https://api.mock/causa/23331-2022-04261",
            "data": [
                {
                    "actuaciones": [
                        {"fecha": "01/01/2024", "actuacion": "Mandamiento de ejecución"}
                    ]
                }
            ]
        }
    ]

    datos = bot._ejecutar_extraccion_detalles()

    assert datos is not None
    assert datos.get("FASE_PROCESAL") is not None
    assert "MANDAMIENTO" in datos.get("FASE_PROCESAL").upper()
    assert datos.get("ETAPA_PROCESAL") is not None
    assert "LIQUIDACION" in datos.get("ETAPA_PROCESAL").upper()
