import io
import json
import unittest
from datetime import date
from pathlib import Path
import test_paz_salvo as legado
from test_paz_salvo import sistema, conexion, pdf_simple
from pypdf import PdfReader
import liquidacion
import caso_ape4


class ExpedienteCompletoTest(unittest.TestCase):
    setUp=legado.PazSalvoTest.setUp
    tearDown=legado.PazSalvoTest.tearDown
    post=legado.PazSalvoTest.post
    consulta=legado.PazSalvoTest.consulta

    def preparar(self):
        r=self.post('/paz-salvo/caso-ape4/preparar')
        self.assertEqual(r.status_code,302)
        return 1

    def verificar(self):
        for qid,rid in self.consulta('SELECT id,revision_id FROM paz_requisitos WHERE bloquea=1'):
            aid=self.consulta(f'SELECT id FROM paz_adjuntos WHERE revision_id={rid} ORDER BY id LIMIT 1')[0][0]
            r=self.post(f'/paz-salvo/1/requisito/{qid}',estado='conforme',observacion='SIMULACIÓN: respaldo ficticio cotejado en la demostración.',fecha=date.today().isoformat(),confirmacion='1',evidencia=str(aid))
            self.assertEqual(r.status_code,302)
        for (rid,) in self.consulta('SELECT id FROM paz_revisiones'):
            self.post(f'/paz-salvo/1/revision/{rid}',estado='conforme',observacion='SIMULACIÓN: revisión del área comprobada.',confirmacion='1')

    def aprobar(self):
        entradas=json.loads(self.consulta('SELECT entradas FROM paz_liquidaciones')[0][0])
        r=self.post('/paz-salvo/1/liquidacion',**entradas,accion='aprobar',confirmacion='1')
        self.assertEqual(r.status_code,302,r.get_data(as_text=True)[:500])

    def test_flujo_completo_tres_pdf_y_original(self):
        self.preparar()
        self.assertEqual(self.consulta('SELECT COUNT(*) FROM empleados')[0][0],6)
        self.assertEqual(self.consulta('SELECT COUNT(*) FROM paz_revisiones')[0][0],8)
        self.assertEqual(self.consulta('SELECT COUNT(*) FROM paz_requisitos')[0][0],21)
        self.verificar();self.aprobar()
        self.post('/paz-salvo/1/emitir')
        self.assertEqual(self.consulta('SELECT estado FROM paz_expedientes')[0][0],'emitido')
        for tipo in ('paz','liquidacion','resumen'):
            r=self.client.get('/paz-salvo/1/documento/'+tipo)
            self.assertEqual(r.status_code,200)
            texto=' '.join(p.extract_text() for p in PdfReader(io.BytesIO(r.data)).pages)
            self.assertIn('Mateo',texto)
            if tipo!='paz': self.assertIn('162.83',texto)
        a=self.consulta("SELECT id FROM paz_adjuntos WHERE nombre='liquidacion-OFICIAL-ministerio.pdf'")[0][0]
        original=self.client.get(f'/paz-salvo/1/adjuntos/{a}').data
        self.assertEqual(original,(caso_ape4.DIRECTORIO/'liquidacion-oficial.pdf').read_bytes())
        self.assertEqual(self.client.get('/paz-salvo/1/descargar-expediente').mimetype,'application/zip')

    def test_interfaz_guia_emision_y_descarga_segun_estado(self):
        self.preparar()
        html=self.client.get('/paz-salvo/1').get_data(as_text=True)
        self.assertIn('Continuar revisiones',html)
        self.assertIn('19 requisitos previos',html)
        self.assertIn('type="submit" disabled>Generar certificado',html)
        self.verificar();self.aprobar()
        html=self.client.get('/paz-salvo/1').get_data(as_text=True)
        self.assertIn('Listo para emitir',html)
        self.assertNotIn('type="submit" disabled>Generar certificado',html)
        self.post('/paz-salvo/1/emitir')
        html=self.client.get('/paz-salvo/1').get_data(as_text=True)
        self.assertIn('Descargar resumen para firma',html)
        self.assertIn('Archivar el resumen firmado',html)
        self.assertNotIn('>Generar certificado, liquidación y resumen</button>',html)

    def test_formulario_liquidacion_conserva_todos_los_importes(self):
        self.preparar()
        html=self.client.get('/paz-salvo/1/liquidacion').get_data(as_text=True)
        for campo in liquidacion.CAMPOS:
            self.assertEqual(html.count(f'name="{campo}"'),1,campo)
        self.assertIn('Control de vacaciones (días)',html)
        self.assertIn('Saldos adicionales y deducciones (USD)',html)

    def test_requisito_pendiente_bloquea_area_y_emision(self):
        self.preparar()
        self.post('/paz-salvo/1/revision/1',estado='conforme',observacion='Todos revisados',confirmacion='1')
        self.assertEqual(self.consulta('SELECT estado FROM paz_revisiones WHERE id=1')[0][0],'pendiente')
        self.post('/paz-salvo/1/emitir')
        self.assertEqual(self.client.get('/paz-salvo/1/pdf').status_code,409)

    def test_lectura_pdf_no_aprueba_automaticamente(self):
        self.preparar()
        a=self.consulta("SELECT id FROM paz_adjuntos WHERE nombre='liquidacion-OFICIAL-ministerio.pdf'")[0][0]
        r=self.post('/paz-salvo/1/liquidacion/leer-pdf',evidencia=str(a))
        self.assertEqual(r.status_code,302)
        self.assertEqual(self.consulta('SELECT estado FROM paz_liquidaciones')[0][0],'borrador')
        v=json.loads(self.consulta('SELECT entradas FROM paz_liquidaciones')[0][0])
        self.assertEqual(v['total_ministerio'],'162.83')
        self.assertEqual(self.client.get('/paz-salvo/1/documento/liquidacion').status_code,409)

    def test_no_aprueba_sin_evidencia_ministerio(self):
        self.preparar()
        v=json.loads(self.consulta('SELECT entradas FROM paz_liquidaciones')[0][0]);v['evidencia_ministerio']='999'
        r=self.post('/paz-salvo/1/liquidacion',**v,accion='aprobar',confirmacion='1')
        self.assertEqual(r.status_code,200)
        self.assertEqual(self.consulta('SELECT estado FROM paz_liquidaciones')[0][0],'borrador')

    def test_totales_erroneos_no_se_corrigen_con_formula_propia(self):
        v=caso_ape4.entradas();v['total_ministerio']='999.99'
        with self.assertRaisesRegex(ValueError,'no suman'):
            liquidacion.registrar_resultado(v,caso_ape4.INGRESO,caso_ape4.SALIDA,'CT','mutuo_acuerdo')

    def test_rechaza_evidencia_de_otra_area_y_fecha_futura(self):
        self.preparar()
        self.assertEqual(self.post('/paz-salvo/1/requisito/1',estado='conforme',observacion='Prueba',fecha='2099-01-01',confirmacion='1',evidencia='1').status_code,400)
        self.assertEqual(self.post('/paz-salvo/1/requisito/1',estado='conforme',observacion='Prueba',fecha=date.today().isoformat(),confirmacion='1',evidencia='2').status_code,400)

    def test_previsualiza_pdf_imagen_y_protege_medicos(self):
        self.preparar()
        for (a,) in self.consulta('SELECT id FROM paz_adjuntos LIMIT 2'):
            self.assertEqual(self.client.get(f'/paz-salvo/1/evidencia/{a}').status_code,200)
        rid=self.consulta("SELECT id FROM paz_revisiones WHERE area='salud'")[0][0]
        self.assertEqual(self.post('/paz-salvo/1/adjuntos',revision=str(rid),tipo='respaldo',archivo=(io.BytesIO(pdf_simple()),'salud.pdf')).status_code,400)

    def test_seguimiento_posterior_no_reescribe_resumen(self):
        self.preparar();self.verificar();self.aprobar();self.post('/paz-salvo/1/emitir')
        antes=self.client.get('/paz-salvo/1/pdf').data
        q,rid=self.consulta('SELECT id,revision_id FROM paz_requisitos WHERE bloquea=0 LIMIT 1')[0]
        self.post('/paz-salvo/1/adjuntos',revision=str(rid),tipo='seguimiento',archivo=(io.BytesIO(pdf_simple()),'seguimiento-ficticio.pdf'))
        aid=self.consulta('SELECT MAX(id) FROM paz_adjuntos')[0][0]
        self.assertEqual(self.post(f'/paz-salvo/1/requisito/{q}',estado='conforme',observacion='Seguimiento posterior FICTICIO.',fecha=date.today().isoformat(),confirmacion='1',evidencia=str(aid)).status_code,302)
        self.assertEqual(self.client.get('/paz-salvo/1/pdf').data,antes)
        self.assertEqual(self.post('/paz-salvo/1/requisito/1',estado='observado',observacion='Cambio',fecha=date.today().isoformat()).status_code,409)

    def test_pdf_oficial_y_comparativo_leidos_sin_calcular_derechos(self):
        a=liquidacion.leer_pdf_oficial((caso_ape4.DIRECTORIO/'liquidacion-oficial.pdf').read_bytes())
        b=liquidacion.leer_pdf_oficial((caso_ape4.DIRECTORIO/'comparacion-despido-oficial.pdf').read_bytes())
        self.assertEqual(a['total_ministerio'],'162.83')
        self.assertEqual(b['total_ministerio'],'1692.83')
        self.assertEqual(b['despido'],'1530.00')
        self.assertTrue(sistema.calculos.cedula_valida(caso_ape4.CEDULA))

    def test_migracion_7_conserva_pdf_y_estados(self):
        self.preparar()
        antes=self.consulta('SELECT snapshot,estado FROM paz_expedientes')
        with conexion(sistema.DB_PATH) as c:c.execute('PRAGMA user_version=7')
        sistema.init_db()
        self.assertEqual(self.consulta('SELECT snapshot,estado FROM paz_expedientes'),antes)
        self.assertTrue(sistema.DB_PATH.with_name('roles_v7_pre_paz_salvo_respaldo.db').exists())

    def test_simulacion_exclusiva_del_caso_ficticio(self):
        self.preparar()
        self.assertEqual(self.post('/paz-salvo/1/simular-revisiones').status_code,400)
        self.assertEqual(self.post('/paz-salvo/1/simular-revisiones',confirmacion='1').status_code,302)
        self.assertEqual(self.consulta("SELECT COUNT(*) FROM paz_requisitos WHERE bloquea=1 AND estado='pendiente'")[0][0],0)
        self.assertEqual(self.consulta("SELECT COUNT(*) FROM paz_requisitos WHERE bloquea=0 AND estado='pendiente'")[0][0],2)
        self.assertEqual(self.consulta('SELECT estado FROM paz_liquidaciones')[0][0],'borrador')
        with conexion(sistema.DB_PATH) as db:
            e=json.loads(db.execute('SELECT snapshot FROM paz_expedientes').fetchone()[0]);e.pop('caso_demo')
            db.execute('UPDATE paz_expedientes SET snapshot=?',(json.dumps(e),))
        self.assertEqual(self.post('/paz-salvo/1/simular-revisiones',confirmacion='1').status_code,400)


if __name__=='__main__':unittest.main()
