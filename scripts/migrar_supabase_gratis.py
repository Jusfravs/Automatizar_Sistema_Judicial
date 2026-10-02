"""Migra una exportación verificada al esquema compacto de Supabase Free.

Los secretos se leen del entorno o con getpass; nunca se guardan en archivos.
La base de origen no se modifica. Se puede reanudar la carga de Storage.
"""

from __future__ import annotations

import argparse
import getpass
import gzip
import hashlib
import json
import os
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import psycopg2
from psycopg2 import sql


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.credenciales_supabase import guardar as guardar_credencial, obtener as obtener_credencial

DEFAULT_ARCHIVE = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SistemaJudicial" / "supabase_historico_20261002"
PROJECT_REF = "kwofqyuyzqooepjiuiae"
BUCKET = "judicial-historico"
HEAVY = {
    "expedientes": {"datos_json": None},
    "resultados_ejecucion": {"datos_json": {}},
    "actuaciones": {"detalle": ""},
    "actuaciones_procesales": {"detalle": "", "datos_json": {}},
}
IMPORT_ORDER = (
    "ejecuciones", "expedientes", "cola_trabajo", "resultados_ejecucion",
    "actuaciones", "eventos_auditoria", "actuaciones_procesales",
    "ejecuciones_inferencia", "auditorias_ia", "revisiones_ia",
    "hitos_procesales",
)


def secret(name: str, prompt: str) -> str:
    value = obtener_credencial(name) or getpass.getpass(prompt)
    if not value:
        raise ValueError(f"Falta {name}")
    return value


def read_manifest(directory: Path) -> dict:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("formato") != "judicial-jsonl-gzip-v1":
        raise ValueError("Formato de archivo histórico desconocido")
    if set(manifest["tablas"]) != set(IMPORT_ORDER) | {"schema_migrations"}:
        raise ValueError("El archivo no contiene exactamente las tablas esperadas")
    for entry in manifest["objetos"]:
        path = directory / entry["archivo"]
        if path.parent != directory or not path.is_file():
            raise ValueError(f"Objeto ausente o fuera del directorio: {entry['archivo']}")
        if path.stat().st_size != entry["bytes"]:
            raise ValueError(f"Tamaño inválido: {path.name}")
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        if digest != entry["sha256"]:
            raise ValueError(f"SHA256 inválido: {path.name}")
    return manifest


def object_name(prefix: str, filename: str) -> str:
    return f"{prefix}/{filename}"


def storage_request(name: str, key: str, *, data: bytes | None = None) -> bytes:
    route = "object" if data is not None else "object/authenticated"
    url = (f"https://{PROJECT_REF}.supabase.co/storage/v1/{route}/"
           f"{quote(BUCKET)}/{quote(name, safe='/')}")
    headers = {"apikey": key}
    if not key.startswith("sb_secret_"):
        headers["Authorization"] = f"Bearer {key}"
    if data is not None:
        headers.update({"Content-Type": "application/gzip", "x-upsert": "true"})
    request = Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with urlopen(request, timeout=180) as response:
        return response.read()


def storage_error(exc: HTTPError) -> tuple[str, str]:
    try:
        payload = json.loads(exc.read(4096))
    except (ValueError, UnicodeDecodeError):
        return "", ""
    if not isinstance(payload, dict):
        return "", ""
    code = str(payload.get("code") or payload.get("error") or "")
    message = str(payload.get("message") or "")
    return code[:80], message[:180]


def missing_storage_object(status: int, code: str, message: str) -> bool:
    if status not in (400, 404):
        return False
    return (code.lower() in {"nosuchkey", "not_found", "objectnotfound"}
            or "object not found" in message.lower())


def upload_archive(directory: Path, manifest: dict, prefix: str, key: str) -> None:
    for index, entry in enumerate(manifest["objetos"], 1):
        name = object_name(prefix, entry["archivo"])
        try:
            remote = storage_request(name, key)
        except HTTPError as exc:
            code, message = storage_error(exc)
            if not missing_storage_object(exc.code, code, message):
                raise RuntimeError(f"Storage GET {name}: HTTP {exc.code}; {code}: {message}") from exc
        else:
            if hashlib.sha256(remote).hexdigest() == entry["sha256"]:
                print(f"[{index}/{len(manifest['objetos'])}] Ya verificado: {name}", flush=True)
                continue
            raise RuntimeError(f"Objeto remoto distinto; no se sobrescribe: {name}")
        data = (directory / entry["archivo"]).read_bytes()
        for attempt in range(3):
            try:
                storage_request(name, key, data=data)
                remote = storage_request(name, key)
                if hashlib.sha256(remote).hexdigest() != entry["sha256"]:
                    raise RuntimeError(f"SHA256 remoto inválido: {name}")
                break
            except (URLError, TimeoutError, HTTPError) as exc:
                if isinstance(exc, HTTPError) and exc.code < 500:
                    raise RuntimeError(f"Storage POST {name}: HTTP {exc.code}") from exc
                if attempt == 2:
                    raise RuntimeError(f"Storage no respondió tras tres intentos: {name}") from exc
                time.sleep(2 ** attempt)
        print(f"[{index}/{len(manifest['objetos'])}] Subido y verificado: {name}", flush=True)


def verify_remote_archive(manifest: dict, prefix: str, key: str) -> None:
    for index, entry in enumerate(manifest["objetos"], 1):
        name = object_name(prefix, entry["archivo"])
        content = storage_request(name, key)
        if len(content) != entry["bytes"] or hashlib.sha256(content).hexdigest() != entry["sha256"]:
            raise RuntimeError(f"Objeto remoto incompleto o diferente: {name}")
        if index % 10 == 0 or index == len(manifest["objetos"]):
            print(f"Storage verificado: {index}/{len(manifest['objetos'])}", flush=True)


def copy_value(value: object) -> str:
    if value is None:
        return r"\N"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    elif isinstance(value, bool):
        value = "true" if value else "false"
    else:
        value = str(value)
    return value.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def prepare_copy(directory: Path, manifest: dict, prefix: str, output: Path) -> tuple[dict, Counter]:
    columns: dict[str, list[str]] = {}
    counts: Counter = Counter()
    files = {table: (output / f"{table}.copy").open("w", encoding="utf-8", newline="\n")
             for table in IMPORT_ORDER}
    try:
        for entry in manifest["objetos"]:
            segment = object_name(prefix, entry["archivo"])
            segment_count = 0
            with gzip.open(directory / entry["archivo"], "rt", encoding="utf-8") as source:
                for line in source:
                    table, raw = line.split("\t", 1)
                    row = json.loads(raw)
                    counts[table] += 1
                    segment_count += 1
                    if table == "schema_migrations":
                        continue
                    if table not in files or not isinstance(row, dict):
                        raise ValueError(f"Fila inesperada: {table}")
                    if table not in columns:
                        columns[table] = list(row)
                        if table in HEAVY:
                            columns[table].append("archivo_segmento")
                    for field, replacement in HEAVY.get(table, {}).items():
                        row[field] = replacement
                    if table in HEAVY:
                        row["archivo_segmento"] = segment
                    if set(row) != set(columns[table]):
                        raise ValueError(f"Columnas inconsistentes en {table}")
                    files[table].write("\t".join(copy_value(row[field]) for field in columns[table]) + "\n")
            if segment_count != entry["filas"]:
                raise ValueError(f"Número de filas inválido en {entry['archivo']}")
    finally:
        for target in files.values():
            target.close()
    if dict(counts) != {k: v for k, v in manifest["tablas"].items() if v}:
        raise ValueError("El total de filas no coincide con el manifiesto")
    return columns, counts


def connect(password: str, ca_file: Path):
    if not ca_file.is_file():
        raise ValueError(f"Falta certificado CA: {ca_file}")
    return psycopg2.connect(
        host="aws-0-us-east-2.pooler.supabase.com", port=5432,
        dbname="postgres", user=f"postgres.{PROJECT_REF}", password=password,
        sslmode="verify-full", sslrootcert=str(ca_file), connect_timeout=20,
    )


def preflight_target(password: str, ca_file: Path) -> None:
    conn = connect(password, ca_file)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.expedientes'), to_regclass('public.resultados_ejecucion')")
            if any(cur.fetchone()):
                raise RuntimeError("La base destino ya contiene tablas judiciales")
            cur.execute("SELECT pg_database_size(current_database())")
            if cur.fetchone()[0] >= 100_000_000:
                raise RuntimeError("El proyecto destino no está vacío; revisa su tamaño antes de importar")
    finally:
        conn.close()
    print("Conexión TLS y base destino verificadas.", flush=True)


def migrate_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.expedientes'), to_regclass('public.resultados_ejecucion')")
        if any(cur.fetchone()):
            raise RuntimeError("La base destino ya contiene tablas judiciales")
        cur.execute("CREATE TABLE IF NOT EXISTS public.schema_migrations (version VARCHAR(255) PRIMARY KEY, checksum CHAR(64) NOT NULL, aplicada_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        cur.execute("SELECT COUNT(*) FROM public.schema_migrations")
        if cur.fetchone()[0]:
            raise RuntimeError("La base destino ya tiene migraciones; se exige un proyecto vacío")
        for path in (*sorted((ROOT / "migrations" / "postgres").glob("*.sql")),
                     ROOT / "migrations" / "supabase" / "001_archivo_historico.sql"):
            content = path.read_text(encoding="utf-8")
            cur.execute(content)
            cur.execute("INSERT INTO public.schema_migrations (version, checksum) VALUES (%s, %s)",
                        (path.name, hashlib.sha256(content.encode("utf-8")).hexdigest()))
            print(f"Esquema: {path.name}", flush=True)


def import_data(conn, directory: Path, manifest: dict, prefix: str, copy_dir: Path) -> None:
    columns, counts = prepare_copy(directory, manifest, prefix, copy_dir)
    with conn.cursor() as cur:
        for table in IMPORT_ORDER:
            if not counts[table]:
                continue
            query = sql.SQL("COPY public.{} ({}) FROM STDIN WITH (FORMAT text)").format(
                sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, columns[table])))
            with (copy_dir / f"{table}.copy").open("r", encoding="utf-8", newline="") as source:
                cur.copy_expert(query.as_string(conn), source)
            print(f"Importado: {table} ({counts[table]})", flush=True)
        for entry in manifest["objetos"]:
            cur.execute("INSERT INTO public.archivo_historico_objetos (nombre, sha256, bytes, filas) VALUES (%s, %s, %s, %s)",
                        (object_name(prefix, entry["archivo"]), entry["sha256"], entry["bytes"], entry["filas"]))
        for table in IMPORT_ORDER:
            cur.execute(sql.SQL("SELECT COUNT(*) FROM public.{}").format(sql.Identifier(table)))
            actual = cur.fetchone()[0]
            if actual != manifest["tablas"][table]:
                raise RuntimeError(f"Filas distintas en {table}: {actual}")
            cur.execute("SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s AND column_name = 'id'", (table,))
            if not cur.fetchone():
                continue
            cur.execute("SELECT pg_get_serial_sequence(%s, 'id')", (f"public.{table}",))
            sequence = cur.fetchone()[0]
            if sequence:
                cur.execute(sql.SQL("SELECT COALESCE(MAX(id), 0) FROM public.{}").format(sql.Identifier(table)))
                max_id = cur.fetchone()[0]
                if max_id:
                    cur.execute("SELECT setval(%s, %s, true)", (sequence, max_id))
        cur.execute("SELECT pg_database_size(current_database())")
        size = cur.fetchone()[0]
        print(f"Tamaño estimado de destino antes del commit: {size:,} bytes", flush=True)
        if size >= 450_000_000:
            raise RuntimeError("El destino queda demasiado cerca de los 500 MB del plan Free")


def activate_common_config(ca_file: Path) -> None:
    path = ROOT / "config_consola.json"
    original = path.read_text(encoding="utf-8")
    config = json.loads(original)
    db = config.setdefault("base_de_datos", {})
    db.update({
        "motor": "postgres", "host": "aws-0-us-east-2.pooler.supabase.com",
        "puerto": 5432, "nombre_db": "postgres",
        "usuario": f"postgres.{PROJECT_REF}", "password_env": "SUPABASE_DB_PASSWORD",
        "sslmode": "verify-full", "sslrootcert": str(ca_file),
    })
    backup_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SistemaJudicial" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / "config_consola_pre_supabase.json"
    if not backup.exists():
        backup.write_text(original, encoding="utf-8")
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    print(f"Configuración común activada; copia anterior: {backup}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archivo", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--prefijo", default="migracion-20261002")
    parser.add_argument("--ca", type=Path, default=Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SistemaJudicial" / "supabase-prod-ca-2021.crt")
    parser.add_argument("--solo-preparar", action="store_true")
    parser.add_argument("--solo-subir", action="store_true")
    parser.add_argument("--solo-importar", action="store_true")
    args = parser.parse_args()
    if sum((args.solo_preparar, args.solo_subir, args.solo_importar)) > 1:
        parser.error("Selecciona una sola etapa")
    manifest = read_manifest(args.archivo)
    print(f"Archivo verificado: {sum(manifest['tablas'].values()):,} filas, {len(manifest['objetos'])} objetos", flush=True)
    with tempfile.TemporaryDirectory(prefix="judicial-copy-") as temporary:
        if args.solo_preparar:
            _, counts = prepare_copy(args.archivo, manifest, args.prefijo, Path(temporary))
            print(f"COPY preparado y comprobado: {sum(counts.values()):,} filas", flush=True)
            return 0
        password = None
        if not args.solo_subir:
            password = secret("SUPABASE_DB_PASSWORD", "Contraseña de la base de Supabase: ")
            preflight_target(password, args.ca)
        key = (obtener_credencial("SUPABASE_SECRET_KEY")
               or obtener_credencial("SUPABASE_SERVICE_ROLE_KEY")
               or getpass.getpass("Clave Secret API (o service_role) de Supabase: "))
        if not key:
            raise ValueError("Falta la clave de Supabase Storage")
        if not args.solo_importar:
            upload_archive(args.archivo, manifest, args.prefijo, key)
            guardar_credencial("SUPABASE_SECRET_KEY", key)
        if args.solo_subir:
            return 0
        if args.solo_importar:
            verify_remote_archive(manifest, args.prefijo, key)
            guardar_credencial("SUPABASE_SECRET_KEY", key)
        conn = connect(password, args.ca)
        try:
            guardar_credencial("SUPABASE_DB_PASSWORD", password)
            with conn:
                migrate_schema(conn)
                import_data(conn, args.archivo, manifest, args.prefijo, Path(temporary))
        finally:
            conn.close()
        print("Migración confirmada y filas verificadas.", flush=True)
        activate_common_config(args.ca)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, psycopg2.Error, HTTPError, URLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
