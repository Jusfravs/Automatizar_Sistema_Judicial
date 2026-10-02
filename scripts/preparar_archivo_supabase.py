"""Exporta todas las filas de PostgreSQL a segmentos privados y verificables.

El resultado se puede cargar a Supabase Storage sin exponer contraseñas ni
datos judiciales en Git. La copia local original no se modifica.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from psycopg2 import sql


def segmento_de_causa(numero_causa: str | None, cantidad: int) -> str:
    if numero_causa is None:
        return "global.jsonl.gz"
    digest = hashlib.md5(str(numero_causa).encode("utf-8")).digest()
    return f"historico-{digest[0] % cantidad:02d}.jsonl.gz"


def exportar(config: Path, destino: Path, segmentos: int = 64) -> dict:
    if not 1 <= segmentos <= 256:
        raise ValueError("SEGMENTOS_FUERA_DE_RANGO")
    destino = Path(destino).expanduser().resolve()
    if destino.exists() and any(destino.iterdir()):
        raise ValueError(f"DESTINO_NO_VACIO:{destino}")
    destino.mkdir(parents=True, exist_ok=True)
    with Path(config).open(encoding="utf-8") as archivo:
        db = json.load(archivo)["base_de_datos"]
    password = os.environ.get(db.get("password_env", "POSTGRES_PASSWORD"), "")
    if not password:
        raise ValueError("POSTGRES_PASSWORD_NO_CONFIGURADA")

    conn = psycopg2.connect(
        host=db["host"], port=db["puerto"], dbname=db["nombre_db"],
        user=db["usuario"], password=password, connect_timeout=10,
    )
    conn.set_session(readonly=True, isolation_level="REPEATABLE READ")
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tablas = [fila[0] for fila in cursor.fetchall()]
            cursor.execute("""
                SELECT table_name FROM information_schema.columns
                WHERE table_schema = 'public' AND column_name = 'numero_causa'
            """)
            con_causa = {fila[0] for fila in cursor.fetchall()}

        nombres = [f"historico-{i:02d}.jsonl.gz" for i in range(segmentos)]
        nombres.append("global.jsonl.gz")
        conteos = {tabla: 0 for tabla in tablas}
        conteos_archivos = {nombre: 0 for nombre in nombres}
        with ExitStack() as stack:
            archivos = {
                nombre: stack.enter_context(gzip.open(destino / nombre, "wb", compresslevel=6))
                for nombre in nombres
            }
            for indice, tabla in enumerate(tablas):
                cursor = conn.cursor(name=f"archivo_{indice}")
                cursor.itersize = 1000
                causa = sql.SQL("t.numero_causa") if tabla in con_causa else sql.SQL("NULL::text")
                cursor.execute(sql.SQL("SELECT {}, row_to_json(t)::text FROM public.{} t").format(
                    causa, sql.Identifier(tabla)
                ))
                for numero_causa, fila_json in cursor:
                    nombre = segmento_de_causa(numero_causa, segmentos)
                    archivos[nombre].write(tabla.encode("ascii") + b"\t" + fila_json.encode("utf-8") + b"\n")
                    conteos[tabla] += 1
                    conteos_archivos[nombre] += 1
                cursor.close()

        objetos = []
        for nombre in nombres:
            ruta = destino / nombre
            with ruta.open("rb") as archivo:
                checksum = hashlib.file_digest(archivo, "sha256").hexdigest()
            if ruta.stat().st_size > 45_000_000:
                raise ValueError(f"SEGMENTO_EXCEDE_LIMITE:{nombre}")
            objetos.append({
                "archivo": nombre,
                "bytes": ruta.stat().st_size,
                "sha256": checksum,
                "filas": conteos_archivos[nombre],
            })
        manifiesto = {
            "formato": "judicial-jsonl-gzip-v1",
            "creado_utc": datetime.now(timezone.utc).isoformat(),
            "segmentos": segmentos,
            "base_origen": db["nombre_db"],
            "tablas": conteos,
            "objetos": objetos,
        }
        (destino / "manifest.json").write_text(
            json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return manifiesto
    finally:
        conn.rollback()
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1] / "config_consola.json")
    parser.add_argument("--destino", required=True, type=Path)
    parser.add_argument("--segmentos", type=int, default=64)
    args = parser.parse_args()
    manifiesto = exportar(args.config, args.destino, args.segmentos)
    print(f"Tablas: {len(manifiesto['tablas'])}")
    print(f"Filas: {sum(manifiesto['tablas'].values())}")
    print(f"Objetos: {len(manifiesto['objetos'])}")
    print(f"Bytes comprimidos: {sum(o['bytes'] for o in manifiesto['objetos'])}")
    print(f"Manifiesto: {args.destino / 'manifest.json'}")


if __name__ == "__main__":
    main()
