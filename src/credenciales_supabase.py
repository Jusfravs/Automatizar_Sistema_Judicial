"""Credenciales de Supabase en el almacén seguro del usuario de Windows."""

from __future__ import annotations

import os
import sys

SERVICE = "SistemaJudicial-Supabase"


def comprobar_almacen() -> None:
    try:
        import keyring
    except ImportError as exc:
        raise RuntimeError(
            f"Falta keyring en {sys.executable}. Instálalo con "
            f"'{sys.executable} -m pip install keyring==25.7.0' "
            "antes de ejecutar la migración"
        ) from exc
    keyring.get_keyring()


def obtener(nombre: str) -> str:
    value = os.getenv(nombre, "")
    if value:
        return value
    try:
        import keyring
    except ImportError:
        return ""
    return keyring.get_password(SERVICE, nombre) or ""


def guardar(nombre: str, valor: str) -> None:
    if nombre not in {"SUPABASE_DB_PASSWORD", "SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY"}:
        raise ValueError("Credencial no permitida")
    if not valor:
        raise ValueError("No se guarda una credencial vacía")
    comprobar_almacen()
    import keyring
    keyring.set_password(SERVICE, nombre, valor)
