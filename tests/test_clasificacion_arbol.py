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


if __name__ == "__main__":
    unittest.main()
