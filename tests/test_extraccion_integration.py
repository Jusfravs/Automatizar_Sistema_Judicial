import json
from pathlib import Path

from src.motor_busqueda_web import BotJudicial
from src.agente_extractor import AgenteExtractor


FIXTURE_DIR = Path(__file__).parent.parent / "data" / "temp_htmls"


def load_json(name):
    p = FIXTURE_DIR / name
    assert p.exists(), f"Fixture not found: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


def load_html(name):
    p = FIXTURE_DIR / name
    assert p.exists(), f"Fixture not found: {p}"
    return p.read_text(encoding="utf-8")


def test_api_mandamiento_detection():
    bot = BotJudicial(url_portal="https://example.local")
    data = load_json("training_case_api.json")

    # Simular paquete API interceptado por la página con la forma esperada por el motor
    # (lista de dicts donde cada dict puede contener 'actuaciones')
    api_payload = [{"actuaciones": [{"fecha": "2022-06-15", "actuacion": "Mandamiento de ejecución"}]}]
    bot.paquetes_api_interceptados = [{"url": "https://api.mock/causa/23331-2022-04261", "data": api_payload}]

    datos = bot._ejecutar_extraccion_detalles(numero_juicio="23331-2022-04261")

    assert datos is not None, "No se devolvieron datos desde _ejecutar_extraccion_detalles"
    assert datos.get("FASE_PROCESAL"), "FASE_PROCESAL no encontrado"
    assert "MANDAMIENTO" in datos.get("FASE_PROCESAL").upper(), f"FASE_PROCESAL inesperada: {datos.get('FASE_PROCESAL')}"
    # La fecha esperada según el fixture
    assert datos.get("FECHA INICIAL FASE ACTUAL") in ("2022-06-15", "15/06/2022"), f"Fecha incorrecta: {datos.get('FECHA INICIAL FASE ACTUAL')}"



def test_api_usa_fecha_de_la_actuacion_detectada():
    """La fecha de la fase debe provenir de su actuacion, no del inicio del juicio."""
    bot = BotJudicial(url_portal="https://example.local")
    api_payload = [{
        "fechaIngreso": "2020-01-01",
        "actuaciones": [
            {"fechaCrea": "15/01/2022", "actuacion": "Boleta de citacion al demandado"}
        ]
    }]
    bot.paquetes_api_interceptados = [{"url": "https://api.mock/causa/fecha", "data": api_payload}]

    datos = bot._ejecutar_extraccion_detalles(numero_juicio="fecha-actuacion")

    assert "CITACION" in datos["FASE_PROCESAL"].upper()
    assert datos["FECHA INICIAL FASE ACTUAL"] == "15/01/2022"
    assert datos["FECHA FIN ULTIMA FASE"] == "15/01/2022"

def test_dom_extractor_detects_mandamiento():
    extractor = AgenteExtractor()
    html = load_html("training_case.html")

    resultado = extractor.procesar_html_string(html)

    assert resultado is not None
    assert resultado.get("FASE_PROCESAL") is not None
    assert "MANDAMIENTO" in resultado.get("FASE_PROCESAL").upper() or "MANDAMIENTO" in (resultado.get('HISTORIAL_ACTUACIONES') and json.dumps(resultado.get('HISTORIAL_ACTUACIONES')).upper()), "No se detectó mandamiento en procesamiento DOM"


def test_variant_1_dom_multiple_actuaciones():
    """Test caso variante 1: Mandamiento en tabla de actuaciones."""
    extractor = AgenteExtractor()
    html = load_html("case_variant_1.html")
    
    resultado = extractor.procesar_html_string(html)
    
    assert resultado is not None, "No se devolvieron datos"
    assert resultado.get("FASE_PROCESAL"), "FASE_PROCESAL vacío"
    assert "MANDAMIENTO" in resultado.get("FASE_PROCESAL").upper() or "EJECUCION" in resultado.get("FASE_PROCESAL").upper(), f"No se detectó ejecución/mandamiento, fases encontradas: {resultado.get('FASE_PROCESAL')}"
    assert len(resultado.get("HISTORIAL_ACTUACIONES", [])) > 0, "No se extrajeron actuaciones"


def test_variant_2_api_ejecutivo_type():
    """Test caso variante 2: nombreTipoAccion='EJECUTIVO' con actuaciones de CITACION no debe deducir mandamiento."""
    bot = BotJudicial(url_portal="https://example.local")
    data = load_json("case_variant_2_api.json")
    # Inyectar actuaciones reales de citación en el paquete API
    data["actuaciones"] = [
        {"fecha": "10/01/2022", "actuacion": "Calificación de la demanda"},
        {"fecha": "15/01/2022", "actuacion": "Boleta de citación al demandado"}
    ]
    
    bot.paquetes_api_interceptados = [{"url": "https://api.mock/causa/54321-2022-00456", "data": [data]}]
    
    datos = bot._ejecutar_extraccion_detalles(numero_juicio="54321-2022-00456")
    
    assert datos is not None
    assert datos.get("FASE_PROCESAL"), f"FASE_PROCESAL vacío: {datos}"
    # Bajo la Regla del Árbol, debe clasificarse como CITACION (no MANDAMIENTO DE EJECUCION)
    assert "CITACION" in datos.get("FASE_PROCESAL").upper(), f"Se esperaba CITACION pero se obtuvo: {datos.get('FASE_PROCESAL')}"
    assert "MANDAMIENTO" not in datos.get("FASE_PROCESAL").upper(), "Falso positivo: se dedujo MANDAMIENTO solo por tipo de acción EJECUTIVO"
    assert datos.get("FECHA INICIAL FASE ACTUAL") is not None, "No se estableció fecha"
