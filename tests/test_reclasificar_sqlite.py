import unittest

import pandas as pd

from scripts.reclasificar_desde_sqlite import (
    _reclasificar_datos,
    _reporte_tiene_revision_manual_automatica,
)


class TestReclasificarDesdeSQLite(unittest.TestCase):
    def test_limpia_revision_manual_automatica_si_citacion_es_siguiente_paso(self):
        datos = {
            "COMENTARIO_ULTIMO": "REVISION MANUAL",
            "HISTORIAL_ACTUACIONES": [
                {
                    "fecha": "16/09/2015",
                    "detalle": "CALIFICACION DE SOLICITUD Y/O DEMANDA",
                },
                {
                    "fecha": "05/06/2017",
                    "detalle": (
                        "EL ACTOR NO HA PROPORCIONADO LAS COPIAS PERTINENTES PARA "
                        "REALIZAR LA CITACION. NO SE HA TRABADO LA LITIS. "
                        "SE ORDENA EL ARCHIVO DE LA PRESENTE CAUSA."
                    ),
                },
            ],
        }

        _, nuevos = _reclasificar_datos(datos, causa="17230-2015-13845")

        self.assertEqual(nuevos["ETAPA ACTUAL"], "2 CITACION")
        self.assertEqual(nuevos["FASE ACTUAL"], "2.1 CITACION (PERSONA/BOLETA)")
        self.assertEqual(nuevos["COMENTARIO_ULTIMO"], "")
        self.assertIsNone(datos["COMENTARIO_ULTIMO"])

    def test_detecta_solo_la_marca_automatica_exacta_en_reporte(self):
        class Repo:
            df = pd.DataFrame({
                "NUMERO_JUICIO": ["17230-2015-13845", "17233-2024-07607"],
                "COMENTARIO_ULTIMO": ["REVISION MANUAL", "por citar"],
            })

        self.assertTrue(
            _reporte_tiene_revision_manual_automatica(Repo(), "17230-2015-13845")
        )
        self.assertFalse(
            _reporte_tiene_revision_manual_automatica(Repo(), "17233-2024-07607")
        )
