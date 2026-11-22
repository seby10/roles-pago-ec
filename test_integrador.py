"""Integración documental: navegación, originales y ausencia de cambios en nómina."""
import hashlib
import json
import os
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

_bootstrap = tempfile.TemporaryDirectory()
os.environ["ROLES_DB_PATH"] = str(Path(_bootstrap.name) / "bootstrap.db")
import app as sistema
import integrador


class Enlaces(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        atributos = dict(attrs)
        if tag == "a" and atributos.get("href", "").startswith("/"):
            self.urls.append(atributos["href"])


class IntegradorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.anterior = sistema.DB_PATH
        self.password = sistema.EDIT_PASSWORD
        sistema.DB_PATH = Path(self.tmp.name) / "roles.db"
        sistema.EDIT_PASSWORD = "clave-prueba"
        sistema.app.config.update(TESTING=True)
        sistema.init_db()
        self.client = sistema.app.test_client()

    def tearDown(self):
        sistema.DB_PATH = self.anterior
        sistema.EDIT_PASSWORD = self.password
        self.tmp.cleanup()

    def test_recorrido_completo_en_solo_lectura_y_enlaces(self):
        antes = sistema.DB_PATH.read_bytes()
        rutas = ["/", "/biblioteca", "/nomina/resumen", "/roles", "/organigrama"]
        rutas += ["/modulos/" + m["id"] for m in integrador.MODULOS]
        for ruta in rutas:
            respuesta = self.client.get(ruta)
            self.assertEqual(respuesta.status_code, 200, ruta)
            parser = Enlaces()
            parser.feed(respuesta.get_data(as_text=True))
            for enlace in parser.urls:
                respuesta_enlace = self.client.get(urlsplit(enlace).path, follow_redirects=True)
                try:
                    self.assertEqual(respuesta_enlace.status_code, 200, enlace)
                finally:
                    respuesta_enlace.close()
        self.assertEqual(sistema.DB_PATH.read_bytes(), antes, "La consulta modificó datos laborales")

    def test_fuentes_conservadas_y_vistas_disponibles(self):
        catalogo = integrador.documentos()
        self.assertEqual(len({d["id"] for d in catalogo}), len(catalogo))
        for d in catalogo:
            pagina = self.client.get("/documentos/" + d["id"])
            self.assertEqual(pagina.status_code, 200)
            if d.get("vista_previa"):
                for n in range(1, d["paginas"] + 1):
                    formato = d.get("vista_formato", "jpg")
                    self.assertTrue((integrador.DIRECTORIO / "vistas" / d["id"] / f"{n}.{formato}").is_file())
                imagen = self.client.get(f'/documentos/{d["id"]}/pagina/1')
                try:
                    self.assertEqual(imagen.mimetype, "image/webp" if d.get("vista_formato") == "webp" else "image/jpeg")
                    self.assertTrue(imagen.data.startswith(b"RIFF" if d.get("vista_formato") == "webp" else b"\xff\xd8"))
                finally:
                    imagen.close()
            respuesta = self.client.get("/documentos/" + d["id"] + "/archivo")
            try:
                self.assertEqual(respuesta.status_code, 200, d["id"])
                self.assertEqual(hashlib.sha256(respuesta.data).hexdigest(), d["sha256"])
                self.assertEqual((integrador.RAIZ.parent / d["fuente"]).read_bytes(), respuesta.data)
            finally:
                respuesta.close()

    def test_busqueda_filtros_y_estado_vacio(self):
        texto = self.client.get("/biblioteca?q=nomina&modulo=nomina").get_data(as_text=True)
        self.assertIn("beneficios", texto.lower())
        texto = self.client.get("/biblioteca?q=CANVAS").get_data(as_text=True)
        self.assertIn("Business Model Canvas", texto)
        texto = self.client.get("/biblioteca?q=IVA").get_data(as_text=True)
        self.assertIn("PEA 2", texto)
        self.assertNotIn("Liquidación administrativa de muestra", texto)
        texto = self.client.get("/biblioteca?q=zzzxysinresultados").get_data(as_text=True)
        self.assertIn("No encontramos documentos", texto)
        texto = self.client.get("/biblioteca?modulo=tributarias&tipo=Informe").get_data(as_text=True)
        self.assertIn("PEA 2", texto)
        self.assertNotIn("PEA 1 · Plan", texto)

    def test_limites_del_visor_y_rutas_no_permitidas(self):
        texto = self.client.get("/documentos/pea1?pagina=9999").get_data(as_text=True)
        self.assertIn('value="17"', texto)
        texto = self.client.get("/documentos/pea1?pagina=-2").get_data(as_text=True)
        self.assertIn('value="1"', texto)
        for ruta in ("/documentos/no-existe", "/documentos/no-existe/archivo", "/modulos/otro",
                     "/entrega-final/roles.db", "/documentos/roles.db/archivo", "/documentos/pea1/pagina/99",
                     "/documentos/pea1/pagina/0"):
            self.assertEqual(self.client.get(ruta).status_code, 404, ruta)
        respuesta = self.client.get("/documentos/pea1/archivo", headers={"Range": "bytes=0-99"})
        try:
            self.assertEqual(respuesta.status_code, 206)
        finally:
            respuesta.close()

    def test_entregables_descargables(self):
        for clave, firma in (("informe", b"%PDF"), ("presentacion", b"PK"), ("laminas", b"%PDF"),
                             ("guion", b"# Guion")):
            respuesta = self.client.get("/entrega-final/" + clave)
            try:
                self.assertEqual(respuesta.status_code, 200)
                self.assertTrue(respuesta.data.startswith(firma), clave)
                self.assertIn("attachment", respuesta.headers["Content-Disposition"])
            finally:
                respuesta.close()

    def test_videos_en_modulos_y_busqueda_sin_confundir_procedimiento_legal(self):
        liquidacion = self.client.get("/modulos/liquidacion").get_data(as_text=True)
        self.assertIn("El despido ideal", liquidacion)
        self.assertIn("no se presenta como el procedimiento legal", liquidacion)
        self.assertIn("1LFZ4ZDc7JSGp34sxZMzw_23p3q9AyFas", liquidacion)
        emprendimiento = self.client.get("/modulos/emprendimiento").get_data(as_text=True)
        self.assertIn("Elevator pitch y Canvas", emprendimiento)
        self.assertNotIn("El despido ideal", emprendimiento)
        resultados = self.client.get("/biblioteca?tipo=Video&q=despido").get_data(as_text=True)
        self.assertIn("17RSFaqTzWO9NHoiQlu3Uh48nbLa4KJ32", resultados)
        self.assertNotIn("Elevator pitch y Canvas", resultados)
        self.assertNotIn("No encontramos documentos", resultados)


if __name__ == "__main__":
    unittest.main()
