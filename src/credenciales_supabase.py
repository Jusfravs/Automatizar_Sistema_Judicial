"""Credenciales de Supabase en el almacén seguro del usuario de Windows."""

from __future__ import annotations

import os

SERVICE = "SistemaJudicial-Supabase"


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
    try:
        import keyring
    except ImportError as exc:
        raise RuntimeError("Instala las dependencias del proyecto para usar el almacén seguro") from exc
    keyring.set_password(SERVICE, nombre, valor)
