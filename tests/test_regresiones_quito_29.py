import json
import sqlite3
import unittest
from datetime import datetime
from pathlib import Path

from src.agente_extractor import MotorInferenciaProcesal


DB_QUITO = Path(__file__).resolve().parents[1] / "data" / "quito" / "estado_casos_quito.db"


CASOS_ESPERADOS = {
    "17230-2016-17734": ("1.3 CALIFICACION", "2016-12-07"),
    "17233-2017-00375": ("1.3 CALIFICACION", "2017-05-30"),
    "17230-2015-17343": ("1.3 CALIFICACION", "2016-11-18"),
    "17233-2024-01557": ("1.3 CALIFICACION", "2024-10-17"),
    "17230-2016-03164": ("1.3 CALIFICACION", "2016-04-04"),
    "17230-2016-05679": ("1.3 CALIFICACION", "2017-07-11"),
    "17230-2016-04908": ("5.3 SENTENCIA EJECUTORIADA", "2019-12-18"),
    "17233-2024-05000": ("1.3 CALIFICACION", "2024-06-25"),
    "17233-2020-01411": ("1.3 CALIFICACION", "2021-04-19"),
    "17307-2014-0329":  ("2.2 CITACION POR PRENSA", "2017-09-22T15:14:00.000+00:00"),
    "17315-2024-00284": ("1.3 CALIFICACION", "2024-04-05"),
    "17233-2025-11175": ("1.3 CALIFICACION", "2025-11-17"),
    "17230-2016-11413": ("5.3 SENTENCIA EJECUTORIADA", "2016-09-30"),
    "17233-2022-05783": ("3.1 CONTESTACION", "2024-07-22"),
    "17230-2015-15007": ("4.3 ACUERDO DE MEDIACION", "2016-08-19"),
    "17233-2018-03830": ("1.3 CALIFICACION", "2018-09-17"),
    "17233-2017-02258": ("1.3 CALIFICACION", "2017-12-11"),
    "17233-2022-06854": ("1.3 CALIFICACION", "2022-11-25"),
    "17233-2024-07607": ("1.3 CALIFICACION", "2026-07-06"),
    "17233-2019-00127": ("5.1 SENTENCIA EMITIDA POR EL JUEZ", "2022-10-26"),
    "17233-2025-09411": ("1.3 CALIFICACION", "2025-09-15"),
    "17233-2025-09167": ("1.3 CALIFICACION", "2025-12-12"),
    "17230-2015-13845": ("2.1 CITACION (PERSONA/BOLETA)", "2017-04-04"),
    "17233-2025-06383": ("1.2 COMPLETAR/ACLARAR DEMANDA", "2025-07-23"),
    "17233-2017-00211": ("1.3 CALIFICACION", "2018-04-19"),
    "17230-2015-13843": ("1.3 CALIFICACION", "2015-09-07"),
    "17233-2025-11170": ("1.3 CALIFICACION", "2025-11-14"),
    "17233-2025-11354": ("1.2 COMPLETAR/ACLARAR DEMANDA", "2026-04-01"),
    "17231-2025-00028": ("1.3 CALIFICACION", "2025-01-29"),
}


def _normalizar_causa(valor):
    return "".join(caracter for caracter in str(valor or "") if caracter.isdigit())


def _fecha_iso(valor):
    texto = str(valor or "").strip()
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto[:10], formato).date().isoformat()
        except ValueError:
            continue
    return texto


@unittest.skipUnless(DB_QUITO.exists(), "SQLite de Quito no disponible")
class TestRegresionesQuito29(unittest.TestCase):
    def test_los_29_historiales_conservan_fase_y_fecha_del_evento_real(self):
        with sqlite3.connect(DB_QUITO) as conexion:
            resultados = {
                _normalizar_causa(causa): json.loads(datos_json)
                for causa, datos_json in conexion.execute(
                    "SELECT numero_causa, datos_json FROM resultados_expediente"
                )
            }

        self.assertEqual(len(CASOS_ESPERADOS), 29)
        for causa, (fase_esperada, fecha_esperada) in CASOS_ESPERADOS.items():
            with self.subTest(causa=causa):
                resultado = resultados[_normalizar_causa(causa)]
                actuaciones = (resultado.get("datos") or {}).get(
                    "HISTORIAL_ACTUACIONES"
                ) or []
                inferencia = MotorInferenciaProcesal.inferir_estado_procesal(
                    actuaciones
                )
                self.assertEqual(inferencia.ultima_fase, fase_esperada)
                self.assertEqual(
                    _fecha_iso(inferencia.fecha_fin_ultima_fase),
                    fecha_esperada,
                )


if __name__ == "__main__":
    unittest.main()
