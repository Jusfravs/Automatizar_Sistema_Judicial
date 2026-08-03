# tests/test_prompt_procesador.py
import json
import unittest
from src.prompt_procesador import (
    cargar_plantilla_prompt,
    construir_prompt,
    limpiar_y_validar_json,
)


class TestPromptProcesador(unittest.TestCase):
    def test_cargar_plantilla(self):
        """La plantilla de prompt debe cargarse correctamente."""
        contenido = cargar_plantilla_prompt()
        self.assertIn("Antigravity", contenido)
        self.assertIn("{causa_id}", contenido)
        self.assertIn("{texto_extraido_del_expediente}", contenido)

    def test_construir_prompt(self):
        """Los marcadores de posición deben reemplazarse adecuadamente."""
        prompt = construir_prompt(
            causa_id="23331-2022-04261",
            texto_extraido="AUTO DE CALIFICACION ADMITIDO A TRAMITE",
            numero_actual=5,
            total_causas=100,
        )
        self.assertIn("23331-2022-04261", prompt)
        self.assertIn("AUTO DE CALIFICACION ADMITIDO A TRAMITE", prompt)
        self.assertIn("5 de 100", prompt)

    def test_limpiar_y_validar_json_valido(self):
        """Debe parsear correctamente un JSON bien formateado."""
        raw_json = """{
            "numero_causa": "23331-2022-04261",
            "etapa_procesal_detectada": "1 PRESENTACION Y CALIFICACION",
            "fase_procesal_detectada": "1.3 CALIFICACION",
            "fecha_ultimo_movimiento": "15/01/2024",
            "resumen_ultimo_movimiento": "Auto de calificación emitido.",
            "requiere_revision_humana": false,
            "unidad_judicial": "Unidad Judicial Civil",
            "actores": {
                "demandante": "BANCO X",
                "demandado": "JUAN PEREZ"
            }
        }"""
        res = limpiar_y_validar_json(raw_json, causa_id="23331-2022-04261")
        self.assertEqual(res["numero_causa"], "23331-2022-04261")
        self.assertEqual(res["fase_procesal_detectada"], "1.3 CALIFICACION")
        self.assertFalse(res["requiere_revision_humana"])

    def test_limpiar_markdown_json(self):
        """Debe remover delimitadores ```json``` antes de parsear."""
        raw_json = """```json
        {
            "numero_causa": "23331-2022-04261",
            "etapa_procesal_detectada": "6 LIQUIDACION Y EMBARGO",
            "fase_procesal_detectada": "6.2 MANDAMIENTO DE EJECUCION",
            "resumen_ultimo_movimiento": "Mandamiento emitido",
            "requiere_revision_humana": false,
            "actores": {
                "demandante": "BANCO X",
                "demandado": "PEDRO GOMEZ"
            }
        }
        ```"""
        res = limpiar_y_validar_json(raw_json, causa_id="23331-2022-04261")
        self.assertEqual(res["fase_procesal_detectada"], "6.2 MANDAMIENTO DE EJECUCION")

    def test_fallback_json_invalido(self):
        """Ante un JSON malformado, debe retornar fallback seguro con requiere_revision_humana=True."""
        res = limpiar_y_validar_json("texto no json", causa_id="CAUSA-TEST")
        self.assertTrue(res["requiere_revision_humana"])
        self.assertEqual(res["etapa_procesal_detectada"], "Indeterminada")
        self.assertEqual(res["numero_causa"], "CAUSA-TEST")
