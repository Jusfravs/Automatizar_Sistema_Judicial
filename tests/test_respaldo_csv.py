"""Pruebas de tolerancia a bloqueos temporales del CSV en Windows/OneDrive."""

import errno
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.gestor_casos import GestorCasos


def _gestor_con_csv(ruta):
    gestor = GestorCasos.__new__(GestorCasos)
    gestor.ruta_csv = str(ruta)
    gestor.df = pd.DataFrame({"NUMERO_JUICIO": ["CAUSA-001"]})
    gestor.df.to_csv(ruta, index=False)
    return gestor


def test_guardar_reintenta_bloqueo_temporal_al_crear_respaldo(tmp_path):
    gestor = _gestor_con_csv(tmp_path / "reporte.csv")
    bloqueo = OSError(errno.EBUSY, "archivo en uso")

    with patch(
        "src.gestor_casos.shutil.copy2", side_effect=[bloqueo, None]
    ) as copiar, patch("src.gestor_casos.time.sleep") as dormir:
        assert gestor.guardar() is True

    assert copiar.call_count == 2
    dormir.assert_called_once_with(0.5)


def test_guardar_no_reintenta_error_no_transitorio_en_respaldo(tmp_path):
    gestor = _gestor_con_csv(tmp_path / "reporte.csv")

    with patch(
        "src.gestor_casos.shutil.copy2", side_effect=OSError(errno.ENOENT, "no existe")
    ) as copiar, patch("src.gestor_casos.time.sleep") as dormir:
        assert gestor.guardar() is False

    assert copiar.call_count == 1
    dormir.assert_not_called()
