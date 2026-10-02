import gzip
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.migrar_supabase_gratis import missing_storage_object, prepare_copy, storage_error
from src.archivo_historico_supabase import _load_segment, recuperar_fila


class _Cursor:
    def __init__(self, sha):
        self.sha = sha

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, *_):
        pass

    def fetchone(self):
        return (self.sha,)


class _Connection:
    def __init__(self, sha):
        self.sha = sha

    def cursor(self):
        return _Cursor(self.sha)


class ArchivoSupabaseTests(unittest.TestCase):
    def setUp(self):
        _load_segment.cache_clear()

    def test_copia_compacta_conserva_original_en_archivo(self):
        original = {"id": 7, "numero_causa": "123", "detalle": "Texto\tcon\nsaltos", "datos_json": {"historial": [1, 2]}}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            compressed = gzip.compress(("actuaciones_procesales\t" + json.dumps(original) + "\n").encode())
            (root / "historico-00.jsonl.gz").write_bytes(compressed)
            manifest = {"objetos": [{"archivo": "historico-00.jsonl.gz", "filas": 1}],
                        "tablas": {"actuaciones_procesales": 1}}
            columns, counts = prepare_copy(root, manifest, "lote", root)
            self.assertEqual(counts["actuaciones_procesales"], 1)
            self.assertEqual(columns["actuaciones_procesales"][-1], "archivo_segmento")
            compact = (root / "actuaciones_procesales.copy").read_text(encoding="utf-8")
            self.assertIn("lote/historico-00.jsonl.gz", compact)
            self.assertNotIn("Texto", compact)
            self.assertEqual(json.loads(gzip.decompress(compressed).decode().split("\t", 1)[1]), original)

    def test_lector_verifica_hash_y_reconstruye_fila(self):
        original = {"id": 7, "numero_causa": "123", "datos_json": {"texto": "íntegro"}}
        compressed = gzip.compress(("resultados_ejecucion\t" + json.dumps(original) + "\n").encode())
        sha = hashlib.sha256(compressed).hexdigest()
        with patch.dict(os.environ, {"SUPABASE_SERVICE_ROLE_KEY": "clave-local-de-prueba"}), \
             patch("src.archivo_historico_supabase.urlopen") as opener:
            opener.return_value.__enter__.return_value.read.return_value = compressed
            restored = recuperar_fila(_Connection(sha), "resultados_ejecucion", 7, "lote/historico-00.jsonl.gz")
            self.assertEqual(restored, original)
            self.assertIn("/object/authenticated/", opener.call_args.args[0].full_url)
        _load_segment.cache_clear()
        with patch.dict(os.environ, {"SUPABASE_SERVICE_ROLE_KEY": "clave-local-de-prueba"}), \
             patch("src.archivo_historico_supabase.urlopen") as opener:
            opener.return_value.__enter__.return_value.read.return_value = compressed
            with self.assertRaisesRegex(RuntimeError, "Integridad"):
                recuperar_fila(_Connection("0" * 64), "resultados_ejecucion", 7, "lote/historico-00.jsonl.gz")

    def test_clave_secret_va_solo_en_apikey(self):
        original = {"id": 9, "datos_json": {"ok": True}}
        compressed = gzip.compress(("resultados_ejecucion\t" + json.dumps(original) + "\n").encode())
        sha = hashlib.sha256(compressed).hexdigest()
        with patch.dict(os.environ, {"SUPABASE_SECRET_KEY": "sb_secret_prueba"}), \
             patch("src.archivo_historico_supabase.urlopen") as opener:
            opener.return_value.__enter__.return_value.read.return_value = compressed
            self.assertEqual(recuperar_fila(_Connection(sha), "resultados_ejecucion", 9, "lote/secret.gz"), original)
            headers = opener.call_args.args[0].headers
            self.assertEqual(headers["Apikey"], "sb_secret_prueba")
            self.assertNotIn("Authorization", headers)

    def test_storage_400_solo_se_acepta_para_objeto_ausente(self):
        error = HTTPError("https://example.test", 400, "Bad Request", {},
                          io.BytesIO(b'{"code":"NoSuchKey","message":"Object not found"}'))
        code, message = storage_error(error)
        self.assertTrue(missing_storage_object(400, code, message))
        self.assertFalse(missing_storage_object(400, "InvalidJWT", "Invalid JWT"))


if __name__ == "__main__":
    unittest.main()
