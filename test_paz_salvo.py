"""Pruebas del flujo, migración y límites de acceso. Nunca abren roles.db."""
import hashlib
import io
import os
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager, closing
from pathlib import Path

_bootstrap = tempfile.TemporaryDirectory()
os.environ['ROLES_DB_PATH'] = str(Path(_bootstrap.name) / 'bootstrap.db')
import app as sistema
from paz_salvo import MAX_FILE
from pypdf import PdfReader, PdfWriter
from werkzeug.test import EnvironBuilder


@contextmanager
def conexion(path):
    conn = sqlite3.connect(path)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def pdf_simple():
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


class PazSalvoTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        sistema.DB_PATH = Path(self.tmp.name) / 'roles.db'
        sistema.EDIT_PASSWORD = ''
        sistema.app.config.update(TESTING=True)
        sistema.init_db()
        self.client = sistema.app.test_client()
        self.client.get('/paz-salvo/nuevo?empleado=5')
        with self.client.session_transaction() as s:
            self.csrf = s['paz_csrf']

    def tearDown(self):
        sistema.EDIT_PASSWORD = ''
        self.tmp.cleanup()

    def post(self, path, **data):
        if path=='/paz-salvo/nuevo':
            for k,v in dict(causa='mutuo_acuerdo',bienes='3',seguridad='1',salud='1',compras='3').items():
                data.setdefault(k,v)
        with closing(EnvironBuilder(path=path, method='POST', data={'csrf': self.csrf, **data})) as builder:
            entorno = builder.get_environ()
            try:
                return self.client.open(entorno)
            finally:
                entorno['wsgi.input'].close()

    def crear(self, empleado=5):
        respuesta=self.post('/paz-salvo/nuevo', empleado=str(empleado), fecha_salida='2026-11-17',
                         motivo='Cierre de relación informado', jefatura='2', tecnologia='2',
                         finanzas='3', talento='1', representante='1')
        # Estas pruebas conservan un expediente v1 para verificar compatibilidad histórica.
        if respuesta.status_code==302:
            with conexion(sistema.DB_PATH) as conn:
                conn.execute('DELETE FROM paz_requisitos')
                conn.execute("DELETE FROM paz_revisiones WHERE area NOT IN ('jefatura','tecnologia','finanzas','talento')")
                conn.execute('UPDATE paz_expedientes SET version_flujo=1')
        return respuesta

    def consulta(self, sql):
        with conexion(sistema.DB_PATH) as conn:
            return conn.execute(sql).fetchall()

    def completar(self):
        for (id,) in self.consulta('SELECT id FROM paz_revisiones ORDER BY id'):
            self.post('/paz-salvo/1/adjuntos', revision=str(id), tipo='respaldo', archivo=(io.BytesIO(pdf_simple()), 'acta.pdf'))
            self.post(f'/paz-salvo/1/revision/{id}', estado='conforme', observacion='Entrega y conciliación verificadas.', confirmacion='1')

    def test_flujo_pdf_y_firmado_inmutable(self):
        self.assertEqual(self.crear().status_code, 302)
        self.assertEqual(self.client.get('/paz-salvo/1').status_code, 200)
        self.completar()
        self.assertEqual(self.post('/paz-salvo/1/emitir').status_code, 302)
        response = self.client.get('/paz-salvo/1/pdf')
        self.assertEqual(response.mimetype, 'application/pdf')
        contenido = response.data
        texto = ' '.join(' '.join(page.extract_text() for page in PdfReader(io.BytesIO(contenido)).pages).split())
        self.assertIn('Andrés', texto)
        self.assertIn('Villacís', texto)
        self.assertIn('Firmas de las partes', texto)
        self.assertIn('No constituye renuncia', texto)
        self.assertEqual(self.consulta('SELECT pdf_hash FROM paz_expedientes')[0][0], hashlib.sha256(contenido).hexdigest())
        self.assertEqual(self.post('/paz-salvo/1/revision/1', estado='observado', observacion='Cambio').status_code, 409)
        self.assertEqual(self.post('/paz-salvo/1/adjuntos', tipo='firmado', firmas_verificadas='1',
                                   archivo=(io.BytesIO(contenido), 'firmado.pdf')).status_code, 302)
        self.assertEqual(self.consulta('SELECT estado FROM paz_expedientes')[0][0], 'firmado')
        self.assertEqual(self.client.get('/paz-salvo/1/pdf').data, contenido)
        self.assertEqual(self.post('/paz-salvo/1/anular', razon='Cambio').status_code, 409)

    def test_bloquea_emision_y_conforme_sin_respaldo(self):
        self.crear()
        self.post('/paz-salvo/1/emitir')
        self.assertEqual(self.client.get('/paz-salvo/1/pdf').status_code, 409)
        self.post('/paz-salvo/1/revision/1', estado='conforme', observacion='OK', confirmacion='1')
        self.assertEqual(self.consulta('SELECT estado FROM paz_revisiones WHERE id=1')[0][0], 'pendiente')

    def test_no_aplica_requiere_justificacion_y_confirmacion(self):
        self.crear()
        self.assertEqual(self.post('/paz-salvo/1/revision/1', estado='no_aplica', observacion='').status_code, 400)
        self.post('/paz-salvo/1/revision/1', estado='no_aplica', observacion='Sin entregas aplicables')
        self.assertEqual(self.consulta('SELECT estado FROM paz_revisiones WHERE id=1')[0][0], 'pendiente')
        self.post('/paz-salvo/1/revision/1', estado='no_aplica', observacion='Sin entregas aplicables', confirmacion='1')
        self.assertEqual(self.consulta('SELECT estado FROM paz_revisiones WHERE id=1')[0][0], 'no_aplica')

    def test_no_autoasignacion_ni_fechas_invalidas(self):
        r = self.post('/paz-salvo/nuevo', empleado='5', fecha_salida='2026-09-01', motivo='Salida',
                      jefatura='5', tecnologia='2', finanzas='3', talento='1', representante='1')
        self.assertIn('anterior al ingreso', r.get_data(as_text=True))
        r = self.post('/paz-salvo/nuevo', empleado='5', fecha_salida='2026-11-17', motivo='Salida',
                      jefatura='5', tecnologia='2', finanzas='3', talento='1', representante='1')
        self.assertIn('Asigna responsables activos', r.get_data(as_text=True))
        self.assertEqual(self.consulta('SELECT COUNT(*) FROM paz_expedientes')[0][0], 0)

    def test_copia_historica_y_no_duplicados(self):
        self.crear()
        self.crear()
        self.assertEqual(self.consulta('SELECT COUNT(*) FROM paz_expedientes')[0][0], 1)
        with conexion(sistema.DB_PATH) as conn:
            conn.execute("UPDATE empleados SET nombres='Cambio' WHERE id=5")
        self.assertIn('Andrés', self.client.get('/paz-salvo/1').get_data(as_text=True))

    def test_jefe_debe_reasignar_subordinados(self):
        self.crear(empleado=2)
        # Para crear una salida de jefe, asignar revisores distintos a sí mismo.
        self.post('/paz-salvo/nuevo', empleado='2', fecha_salida='2026-11-17', motivo='Salida',
                  jefatura='1', tecnologia='1', finanzas='3', talento='1', representante='1', delegacion='Jefe del organigrama')
        self.post('/paz-salvo/1/revision/1', estado='no_aplica', observacion='Sin entregas', confirmacion='1')
        self.assertEqual(self.consulta('SELECT estado FROM paz_revisiones WHERE id=1')[0][0], 'pendiente')

    def test_adjuntos_invalidos_y_de_otro_expediente(self):
        self.crear()
        for nombre in ('x.html', 'falso.pdf', 'falso.png'):
            self.assertEqual(self.post('/paz-salvo/1/adjuntos', revision='1', tipo='respaldo',
                                       archivo=(io.BytesIO(b'<script>alert(1)</script>'), nombre)).status_code, 400)
        self.assertEqual(self.post('/paz-salvo/1/adjuntos', revision='999', archivo=(io.BytesIO(pdf_simple()), 'x.pdf')).status_code, 400)
        self.assertEqual(self.client.get('/paz-salvo/1/adjuntos/999').status_code, 404)
        self.assertEqual(self.post('/paz-salvo/1/adjuntos', tipo='firmado', archivo=(io.BytesIO(pdf_simple()), 'x.pdf')).status_code, 409)

    def test_limites_archivos_y_logo(self):
        self.crear()
        # Un respaldo entre 2 y 10 MB debe pasar el límite anterior del logo.
        contenido = pdf_simple() + b'\n' + b' ' * (3 * 1024 * 1024)
        r = self.post('/paz-salvo/1/adjuntos', revision='1', tipo='respaldo', archivo=(io.BytesIO(contenido), 'grande.pdf'))
        self.assertEqual(r.status_code, 302)
        r = self.post('/paz-salvo/1/adjuntos', revision='1', tipo='respaldo', archivo=(io.BytesIO(b'x' * (MAX_FILE + 1)), 'exceso.pdf'))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(sistema.app.config['MAX_CONTENT_LENGTH'], 2 * 1024 * 1024)

    def test_csrf_y_acceso_privado(self):
        self.assertEqual(self.client.post('/paz-salvo/nuevo', data={}).status_code, 400)
        self.crear()
        sistema.EDIT_PASSWORD = 'prueba'
        for path in ('/paz-salvo', '/paz-salvo/1', '/paz-salvo/1/pdf', '/paz-salvo/1/adjuntos/1'):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 302)
            self.assertTrue(r.location.endswith('/login'))
        with self.client.session_transaction() as s:
            s['editor'] = True
        self.assertEqual(self.client.get('/paz-salvo/1').status_code, 200)
        self.assertEqual(self.client.get('/paz-salvo/1').headers['Cache-Control'], 'no-store')

    def test_anular_permite_reemplazo_sin_borrar_historial(self):
        self.crear()
        self.post('/paz-salvo/1/anular', razon='Fecha de salida corregida')
        self.crear()
        self.assertEqual(self.consulta('SELECT estado FROM paz_expedientes ORDER BY id'), [('anulado',), ('en_revision',)])
        self.assertGreater(self.consulta('SELECT COUNT(*) FROM paz_eventos WHERE expediente_id=1')[0][0], 1)

    def test_no_elimina_empleado_ni_revisor_referenciado(self):
        self.crear()
        self.client.post('/empleados/5/eliminar')
        self.client.post('/empleados/3/eliminar')
        self.assertEqual(self.consulta('SELECT COUNT(*) FROM empleados WHERE id IN (3,5)')[0][0], 2)

    def test_migracion_v6_conserva_datos_y_respalda(self):
        with conexion(sistema.DB_PATH) as conn:
            conn.execute('PRAGMA user_version=6')
            conn.execute("UPDATE empleados SET nombres='Personalizado' WHERE id=5")
            conn.execute("INSERT INTO roles_cabecera(anio,mes,generado_en,n_empleados,total_ingresos,total_descuentos,total_neto,total_costo,total_iess,total_ir) VALUES (2026,10,'2026-11-01',1,500,50,450,600,100,0)")
        sistema.init_db()
        self.assertEqual(self.consulta('PRAGMA user_version')[0][0], 8)
        self.assertEqual(self.consulta('SELECT nombres FROM empleados WHERE id=5')[0][0], 'Personalizado')
        self.assertEqual(self.consulta('SELECT total_neto FROM roles_cabecera')[0][0], 450)
        self.assertTrue(sistema.DB_PATH.with_name('roles_v6_pre_paz_salvo_respaldo.db').exists())


if __name__ == '__main__':
    unittest.main()
