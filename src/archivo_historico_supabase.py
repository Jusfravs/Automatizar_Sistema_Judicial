"""Lectura verificada del historial judicial guardado en Storage privado."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
from functools import lru_cache
from urllib.parse import quote
from urllib.request import Request, urlopen
from src.credenciales_supabase import obtener as obtener_credencial_supabase


BUCKET = "judicial-historico"


def recuperar_fila(conn, tabla: str, identificador: str | int, segmento: str) -> dict:
    """Devuelve la fila original, sin los campos vaciados en PostgreSQL."""
    if tabla not in {"expedientes", "resultados_ejecucion", "actuaciones", "actuaciones_procesales"}:
        raise ValueError("Tabla histórica no admitida")
    with conn.cursor() as cur:
        cur.execute(
            "SELECT sha256 FROM public.archivo_historico_objetos WHERE nombre = %s",
            (segmento,),
        )
        found = cur.fetchone()
    if not found:
        raise LookupError(f"Segmento histórico no registrado: {segmento}")
    url = os.getenv("SUPABASE_URL", "https://kwofqyuyzqooepjiuiae.supabase.co").rstrip("/")
    key = (obtener_credencial_supabase("SUPABASE_SECRET_KEY")
           or obtener_credencial_supabase("SUPABASE_SERVICE_ROLE_KEY"))
    if not key:
        raise RuntimeError("SUPABASE_SECRET_KEY es necesaria para leer el historial privado")
    records = _load_segment(url, key, segmento, found[0], tabla)
    try:
        return records[str(identificador)]
    except KeyError as exc:
        raise LookupError(f"Fila histórica ausente: {tabla}/{identificador}") from exc


@lru_cache(maxsize=8)
def _load_segment(url: str, key: str, segmento: str, sha256: str, tabla: str) -> dict[str, dict]:
    endpoint = f"{url}/storage/v1/object/authenticated/{quote(BUCKET)}/{quote(segmento, safe='/')}"
    headers = {"apikey": key}
    if not key.startswith("sb_secret_"):
        headers["Authorization"] = f"Bearer {key}"
    request = Request(endpoint, headers=headers)
    with urlopen(request, timeout=180) as response:
        compressed = response.read()
    if hashlib.sha256(compressed).hexdigest() != sha256:
        raise RuntimeError(f"Integridad histórica inválida: {segmento}")
    index = {}
    with gzip.open(io.BytesIO(compressed), "rt", encoding="utf-8") as source:
        for line in source:
            name, data = line.split("\t", 1)
            if name != tabla:
                continue
            row = json.loads(data)
            row_id = row["numero_causa"] if tabla == "expedientes" else row.get("id", row.get("actuacion_id"))
            index[str(row_id)] = row
    return index
