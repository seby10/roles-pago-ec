"""Expediente interno de entrega y cierre. No sustituye el finiquito del SUT."""
import hashlib
import hmac
import io
import json
import secrets
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename
import liquidacion

SCHEMA = """
CREATE TABLE IF NOT EXISTS paz_expedientes (
 id INTEGER PRIMARY KEY, empleado_id INTEGER NOT NULL REFERENCES empleados(id),
 snapshot TEXT NOT NULL, fecha_salida TEXT NOT NULL, motivo TEXT NOT NULL,
 estado TEXT NOT NULL DEFAULT 'en_revision' CHECK(estado IN ('en_revision','emitido','firmado','anulado')),
 creado_en TEXT NOT NULL, emitido_en TEXT, pdf BLOB, pdf_hash TEXT,
 firmado_id INTEGER REFERENCES paz_adjuntos(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS paz_un_abierto ON paz_expedientes(empleado_id)
 WHERE estado IN ('en_revision','emitido');
CREATE TABLE IF NOT EXISTS paz_revisiones (
 id INTEGER PRIMARY KEY, expediente_id INTEGER NOT NULL REFERENCES paz_expedientes(id),
 area TEXT NOT NULL, responsable_id INTEGER NOT NULL REFERENCES empleados(id),
 responsable TEXT NOT NULL, cargo TEXT NOT NULL,
 estado TEXT NOT NULL DEFAULT 'pendiente' CHECK(estado IN ('pendiente','observado','conforme','no_aplica')),
 observacion TEXT NOT NULL DEFAULT '', revisado_en TEXT,
 UNIQUE(expediente_id,area)
);
CREATE TABLE IF NOT EXISTS paz_adjuntos (
 id INTEGER PRIMARY KEY, expediente_id INTEGER NOT NULL REFERENCES paz_expedientes(id),
 revision_id INTEGER REFERENCES paz_revisiones(id), tipo TEXT NOT NULL,
 nombre TEXT NOT NULL, mime TEXT NOT NULL, contenido BLOB NOT NULL,
 sha256 TEXT NOT NULL, creado_en TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS paz_eventos (
 id INTEGER PRIMARY KEY, expediente_id INTEGER NOT NULL REFERENCES paz_expedientes(id),
 fecha TEXT NOT NULL, actor TEXT NOT NULL, detalle TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS paz_requisitos (
 id INTEGER PRIMARY KEY, revision_id INTEGER NOT NULL REFERENCES paz_revisiones(id),
 titulo TEXT NOT NULL, bloquea INTEGER NOT NULL DEFAULT 1,
 estado TEXT NOT NULL DEFAULT 'pendiente', observacion TEXT NOT NULL DEFAULT '',
 fecha TEXT, evidencia_id INTEGER REFERENCES paz_adjuntos(id)
);
CREATE TABLE IF NOT EXISTS paz_liquidaciones (
 expediente_id INTEGER PRIMARY KEY REFERENCES paz_expedientes(id),
 entradas TEXT NOT NULL, resultado TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'borrador',
 actualizado_en TEXT NOT NULL, aprobado_en TEXT, pdf BLOB, pdf_hash TEXT
);
CREATE TABLE IF NOT EXISTS paz_documentos (
 expediente_id INTEGER NOT NULL REFERENCES paz_expedientes(id), tipo TEXT NOT NULL,
 pdf BLOB NOT NULL, sha256 TEXT NOT NULL, creado_en TEXT NOT NULL,
 PRIMARY KEY(expediente_id,tipo)
);
"""
AREAS = {
    'jefatura': ('Jefe inmediato', 'Entrega de funciones, proyectos, documentos y reasignación de subordinados.'),
    'tecnologia': ('Tecnología y bienes', 'Equipos, activos, credenciales y revocación de accesos en la fecha efectiva.'),
    'finanzas': ('Finanzas', 'Conciliación de nómina, anticipos, préstamos y respaldos; sin descuentos automáticos.'),
    'talento': ('Talento humano', 'Revisar vacaciones, beneficios, liquidación y trámites de salida según régimen.'),
    'bienes': ('Activos y almacén', 'Inventario, herramientas, materiales y actas de devolución.'),
    'seguridad': ('Seguridad y accesos físicos', 'Llaves, credenciales, equipos de protección y accesos a instalaciones.'),
    'salud': ('Medicina ocupacional', 'Constancia administrativa del examen de retiro; sin historias clínicas ni diagnósticos.'),
    'compras': ('Compras y control institucional', 'Contratos, compras y declaración patrimonial cuando el puesto y régimen lo exijan.'),
}
REQUISITOS = {
 'jefatura': [('Informe final de labores y recepción del jefe', 1), ('Entrega de documentos y transferencia de archivos físicos y digitales', 1), ('Pendientes, proyectos y reasignación de subordinados', 1)],
 'tecnologia': [('Entrega de dispositivos y accesorios con inventario', 1), ('Cierre o transferencia de correo, cuentas, nube y VPN', 1), ('Ofimática, licencias, certificados y permisos de software', 1), ('Respaldo y transferencia de información; bloqueo o revocación de accesos', 1)],
 'finanzas': [('Conciliación de nómina, pagos previos y rubros de liquidación', 1), ('Anticipos, préstamos, gastos y deducciones respaldadas', 1)],
 'talento': [('Documento de terminación y causal identificada', 1), ('Kárdex de vacaciones, permisos y beneficios sociales', 1), ('Entrega de certificados y documentos al trabajador', 1), ('Seguimiento del aviso de salida IESS', 0), ('Seguimiento de finiquito SUT y comprobante de pago (cuando aplique)', 0)],
 'bienes': [('Devolución de activos, herramientas y materiales', 1), ('Acta de entrega recepción e inventario conciliado', 1)],
 'seguridad': [('Entrega de llaves, tarjetas y credenciales físicas', 1), ('Equipos de protección y baja de accesos a instalaciones', 1)],
 'salud': [('Constancia del examen médico ocupacional de retiro', 1)],
 'compras': [('Entrega o reasignación de administración de contratos y compras', 1), ('Declaración patrimonial de fin de gestión cuando sea exigible', 1)],
}


def migrar(conn):
    columnas = {r[1] for r in conn.execute('PRAGMA table_info(paz_expedientes)')}
    for nombre, declaracion in [('version_flujo', 'INTEGER NOT NULL DEFAULT 1'), ('causa', "TEXT NOT NULL DEFAULT ''")]:
        if nombre not in columnas:
            conn.execute(f'ALTER TABLE paz_expedientes ADD COLUMN {nombre} {declaracion}')


def crear_requisitos(conn, revision_id, area):
    conn.executemany('INSERT INTO paz_requisitos(revision_id,titulo,bloquea) VALUES (?,?,?)',
                     [(revision_id, titulo, bloquea) for titulo, bloquea in REQUISITOS[area]])
ALCANCE = ('Esta constancia documenta únicamente las entregas y revisiones internas detalladas. '
           'No sustituye el acta de finiquito, la liquidación pormenorizada ni los registros ante el Ministerio '
           'del Trabajo o el IESS. No constituye renuncia de derechos laborales ni autoriza descuentos. '
           'Los pagos y trámites legales deben cumplirse independientemente de este expediente.')
MAX_FILE = 10 * 1024 * 1024


def ahora():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def registrar(app, db, empresa, password):
    bp = Blueprint('paz', __name__, url_prefix='/paz-salvo')

    def rows(sql, args=()):
        return [dict(r) for r in db().execute(sql, args)]

    def expediente(id):
        r = rows('SELECT * FROM paz_expedientes WHERE id=?', (id,))
        if not r:
            abort(404)
        r = r[0]
        r['datos'] = json.loads(r['snapshot'])
        return r

    def evento(id, detalle):
        db().execute('INSERT INTO paz_eventos(expediente_id,fecha,actor,detalle) VALUES (?,?,?,?)',
                     (id, ahora(), 'Editor administrativo' if password() else 'Operador local (demo)', detalle))

    def token():
        if 'paz_csrf' not in session:
            session['paz_csrf'] = secrets.token_hex(32)
        return session['paz_csrf']

    @bp.context_processor
    def contexto():
        return dict(paz_csrf=token, PAZ_AREAS=AREAS, PAZ_ALCANCE=ALCANCE, CAUSAS=liquidacion.CAUSAS)

    @bp.before_request
    def proteger():
        # Los expedientes y adjuntos no participan del modo de lectura público de la nómina.
        if password() and not session.get('editor'):
            return redirect(url_for('login'))
        if request.method == 'POST' and not hmac.compare_digest(
                session.get('paz_csrf', ''), request.form.get('csrf', '')):
            abort(400, 'Sesión vencida. Recarga el formulario antes de enviar.')
        if request.method == 'POST' and not session.get('paz_csrf'):
            abort(400)

    @bp.after_request
    def privado(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @bp.errorhandler(413)
    def grande(_):
        return render_template('paz_error.html', mensaje='El archivo supera el límite de 10 MB.'), 413

    @bp.get('')
    def lista():
        expedientes = rows('SELECT id,snapshot,fecha_salida,estado FROM paz_expedientes ORDER BY id DESC')
        for e in expedientes:
            e['datos'] = json.loads(e.pop('snapshot'))
        return render_template('paz_lista.html', expedientes=expedientes)

    @bp.get('/caso-ape4')
    def caso():
        import caso_ape4
        return render_template('paz_caso.html',caso=caso_ape4)

    @bp.get('/caso-ape4/archivos')
    def caso_archivos():
        import caso_ape4
        import zipfile
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
            for area in AREAS:
                z.writestr(f'evidencia-ficticia-{area}.pdf',caso_ape4.pdf_evidencia(area))
            z.writestr('dispositivo-ficticio.png',caso_ape4.imagen_dispositivo())
            for p in caso_ape4.DIRECTORIO.iterdir():
                if p.is_file():
                    z.writestr(p.name,p.read_bytes())
            z.writestr('datos-caso.json',json.dumps(caso_ape4.entradas(),ensure_ascii=False,indent=2))
        return send_file(io.BytesIO(b.getvalue()),mimetype='application/zip',as_attachment=True,download_name='caso-ficticio-APE4.zip')

    @bp.post('/caso-ape4/preparar')
    def caso_preparar():
        import caso_ape4 as c
        if empresa()['regimen']!='CT' or empresa()['region']!='Sierra':
            abort(409,'El caso de referencia usa CT y Sierra. No se modifican automáticamente los parámetros de tu empresa.')
        equipo=rows('SELECT * FROM empleados WHERE activo=1 AND cedula<>? ORDER BY id',(c.CEDULA,))
        if not equipo:
            abort(409,'Registra al menos un responsable activo distinto del trabajador ficticio.')
        def elegir(depto):
            return next((x for x in equipo if x['departamento']==depto),equipo[0])
        gerencia=elegir('Gerencia General');tecnologia=elegir('Tecnología');finanzas=elegir('Finanzas')
        with db():
            db().execute('BEGIN IMMEDIATE')
            trabajador=rows('SELECT * FROM empleados WHERE cedula=?',(c.CEDULA,))
            if trabajador:
                eid=trabajador[0]['id']
                abierto=rows("SELECT id FROM paz_expedientes WHERE empleado_id=? AND estado IN ('en_revision','emitido')",(eid,))
                if abierto:
                    return redirect(url_for('paz.ver',id=abierto[0]['id']))
                if trabajador[0]['nombres']!='Mateo Demostración':
                    abort(409,'La cédula ficticia coincide con otro registro. No se modifica ese empleado.')
            else:
                eid=db().execute("INSERT INTO empleados(cedula,nombres,apellidos,cargo,sueldo,fecha_ingreso,tipo_contrato,mensualiza_13,mensualiza_14,departamento,reporta_a,estructura,activo) VALUES (?,'Mateo Demostración','Rivera','Programador de demostración',510,?,'Indefinido',0,0,'Tecnología',?,'C3',0)",(c.CEDULA,c.INGRESO,tecnologia['id'])).lastrowid
            snapshot=dict(nombres='Mateo Demostración',apellidos='Rivera',cedula=c.CEDULA,cargo='Programador de demostración',departamento='Tecnología',fecha_ingreso=c.INGRESO,reporta_a=tecnologia['id'],
                          jefe=tecnologia['nombres']+' '+tecnologia['apellidos'],empresa=empresa()['nombre'],ruc=empresa()['ruc'],regimen='CT',region='Sierra',sueldo=510,mensualiza_13=0,mensualiza_14=0,mensualiza_fondos=1,
                          representante=gerencia['nombres']+' '+gerencia['apellidos'],representante_cedula=gerencia['cedula'],representante_cargo=gerencia['cargo'],delegacion='',caso_demo=True)
            id=db().execute("INSERT INTO paz_expedientes(empleado_id,snapshot,fecha_salida,motivo,creado_en,version_flujo,causa) VALUES (?,?,?,?,?,2,'mutuo_acuerdo')",(eid,json.dumps(snapshot,ensure_ascii=False),c.SALIDA,'CASO FICTICIO APE 4: acuerdo entre las partes; sin saldos de nómina pendientes.',ahora())).lastrowid
            ids={}
            evidencias={}
            def adjunto(rid,nombre,mime,contenido):
                return db().execute("INSERT INTO paz_adjuntos(expediente_id,revision_id,tipo,nombre,mime,contenido,sha256,creado_en) VALUES (?,?,'respaldo',?,?,?,?,?)",(id,rid,nombre,mime,contenido,hashlib.sha256(contenido).hexdigest(),ahora())).lastrowid
            for area in AREAS:
                persona=tecnologia if area in ('jefatura','tecnologia') else finanzas if area in ('finanzas','bienes','compras') else gerencia
                rid=db().execute('INSERT INTO paz_revisiones(expediente_id,area,responsable_id,responsable,cargo) VALUES (?,?,?,?,?)',(id,area,persona['id'],persona['nombres']+' '+persona['apellidos'],persona['cargo'])).lastrowid
                ids[area]=rid
                crear_requisitos(db(),rid,area)
                evidencias[area]=adjunto(rid,f'evidencia-FICTICIA-{area}.pdf','application/pdf',c.pdf_evidencia(area))
            adjunto(ids['tecnologia'],'dispositivo-FICTICIO.png','image/png',c.imagen_dispositivo())
            oficial=adjunto(ids['finanzas'],'liquidacion-OFICIAL-ministerio.pdf','application/pdf',(c.DIRECTORIO/'liquidacion-oficial.pdf').read_bytes())
            adjunto(ids['finanzas'],'consulta-datos-ministerio.jpg','image/jpeg',(c.DIRECTORIO/'consulta-ministerio-datos.jpg').read_bytes())
            valores=c.entradas()
            valores.update(evidencia_ministerio=str(oficial),evidencia_finanzas=str(evidencias['finanzas']),evidencia_vacaciones=str(evidencias['talento']))
            resultado=liquidacion.registrar_resultado(valores,c.INGRESO,c.SALIDA,'CT','mutuo_acuerdo')
            db().execute("INSERT INTO paz_liquidaciones(expediente_id,entradas,resultado,estado,actualizado_en) VALUES (?,?,?,'borrador',?)",(id,json.dumps(valores,ensure_ascii=False),json.dumps(resultado,ensure_ascii=False),ahora()))
            evento(id,'Caso FICTICIO APE 4 preparado con evidencias académicas y PDF REAL del simulador ministerial. Todas las revisiones y aprobaciones quedan pendientes para la demostración.')
        return redirect(url_for('paz.ver',id=id))

    @bp.post('/<int:id>/simular-revisiones')
    def simular(id):
        with db():
            db().execute('BEGIN IMMEDIATE')
            e=expediente(id)
            if not e['datos'].get('caso_demo') or e['estado']!='en_revision' or not request.form.get('confirmacion'):
                abort(400,'Esta acción solo está disponible para el caso ficticio APE 4 y exige confirmar la simulación.')
            for r in rows('SELECT * FROM paz_revisiones WHERE expediente_id=?',(id,)):
                evidencia=rows("SELECT id FROM paz_adjuntos WHERE expediente_id=? AND revision_id=? AND nombre LIKE 'evidencia-FICTICIA-%' ORDER BY id LIMIT 1",(id,r['id']))
                if not evidencia:
                    abort(409,'Falta un respaldo ficticio del área para ejecutar el recorrido.')
                estado='no_aplica' if r['area']=='compras' else 'conforme'
                nota=('SIMULACIÓN ACADÉMICA: el puesto privado no administra contratos ni requiere declaración patrimonial.' if estado=='no_aplica' else 'SIMULACIÓN ACADÉMICA: se registra la revisión del supuesto con el documento ficticio del área; no acredita una entrega real.')
                for q in rows('SELECT * FROM paz_requisitos WHERE revision_id=? AND bloquea=1',(r['id'],)):
                    db().execute('UPDATE paz_requisitos SET estado=?,observacion=?,fecha=?,evidencia_id=? WHERE id=?',(estado,nota,date.today().isoformat(),evidencia[0]['id'] if estado=='conforme' else None,q['id']))
                    evento(id,f"SIMULACIÓN APE 4 · {q['titulo']}: {estado}.")
                db().execute('UPDATE paz_revisiones SET estado=?,observacion=?,revisado_en=? WHERE id=?',(estado,nota,ahora(),r['id']))
            evento(id,'Recorrido ficticio de revisiones completado por instrucción del operador. La liquidación sigue requiriendo verificación y aprobación. IESS y SUT siguen pendientes.')
        flash('Recorrido ficticio completado. Verifica y aprueba los valores del Ministerio para emitir el resumen.','success')
        return redirect(url_for('paz.ver',id=id))

    @bp.route('/nuevo', methods=['GET', 'POST'])
    def nuevo():
        empleados = rows('SELECT * FROM empleados ORDER BY apellidos,nombres')
        seleccionado = request.form.get('empleado', type=int) if request.method == 'POST' else request.args.get('empleado', type=int)
        elegido = next((e for e in empleados if e['id'] == seleccionado), None)
        responsables = [e for e in empleados if e['activo'] and e['id'] != seleccionado]
        sugeridos = {'jefatura': elegido['reporta_a'] if elegido else None}
        for area, departamento in [('tecnologia', 'Tecnología'), ('finanzas', 'Finanzas')]:
            grupo = [e for e in responsables if e['departamento'].casefold() == departamento.casefold()]
            ids = {e['id'] for e in grupo}
            cabezas = [e for e in grupo if e['reporta_a'] not in ids]
            sugeridos[area] = cabezas[0]['id'] if len(cabezas) == 1 else None
        error = None
        if request.method == 'POST':
            try:
                if not elegido:
                    raise ValueError('Selecciona un empleado.')
                salida = date.fromisoformat(request.form.get('fecha_salida', ''))
                if salida < date.fromisoformat(elegido['fecha_ingreso']):
                    raise ValueError('La salida no puede ser anterior al ingreso.')
                motivo = request.form.get('motivo', '').strip()
                causa = request.form.get('causa', '')
                if causa not in liquidacion.CAUSAS or ((empresa()['regimen'] == 'CT') == (causa == 'cese_publico')):
                    raise ValueError('Selecciona una causa de terminación compatible con el régimen.')
                if not motivo or len(motivo) > 1000:
                    raise ValueError('Describe el motivo en un máximo de 1000 caracteres.')
                mapa = {e['id']: e for e in responsables}
                asignados = {area: mapa.get(request.form.get(area, type=int)) for area in AREAS}
                representante = mapa.get(request.form.get('representante', type=int))
                if not representante or not all(asignados.values()):
                    raise ValueError('Asigna responsables activos para las cuatro áreas y un representante distinto del trabajador.')
                delegacion = request.form.get('delegacion', '').strip()
                if len(delegacion) > 1000 or (asignados['jefatura']['id'] != elegido['reporta_a'] and not delegacion):
                    raise ValueError('Justifica la designación de jefatura cuando no coincide con el jefe registrado (máximo 1000 caracteres).')
                snapshot = {k: elegido[k] for k in ('nombres', 'apellidos', 'cedula', 'cargo', 'departamento', 'fecha_ingreso', 'reporta_a')}
                jefe = next((e for e in empleados if e['id'] == elegido['reporta_a']), None)
                snapshot.update(empresa=empresa()['nombre'], ruc=empresa()['ruc'], regimen=empresa()['regimen'],
                                jefe=f"{jefe['nombres']} {jefe['apellidos']}" if jefe else 'Sin jefe registrado',
                                representante=f"{representante['nombres']} {representante['apellidos']}",
                                representante_cedula=representante['cedula'], representante_cargo=representante['cargo'])
                snapshot['delegacion'] = delegacion
                snapshot.update({k: elegido[k] for k in ('sueldo','mensualiza_13','mensualiza_14','mensualiza_fondos')})
                snapshot['region'] = empresa()['region']
                with db():
                    id = db().execute('INSERT INTO paz_expedientes(empleado_id,snapshot,fecha_salida,motivo,creado_en,version_flujo,causa) VALUES (?,?,?,?,?,2,?)',
                                      (seleccionado, json.dumps(snapshot, ensure_ascii=False), salida.isoformat(), motivo, ahora(), causa)).lastrowid
                    for area, persona in asignados.items():
                        rid = db().execute('INSERT INTO paz_revisiones(expediente_id,area,responsable_id,responsable,cargo) VALUES (?,?,?,?,?)',
                                     (id, area, persona['id'], f"{persona['nombres']} {persona['apellidos']}", persona['cargo'])).lastrowid
                        crear_requisitos(db(), rid, area)
                    evento(id, 'Expediente creado; responsables y datos laborales conservados como copia histórica.')
                return redirect(url_for('paz.ver', id=id))
            except (ValueError, sqlite3.IntegrityError) as exc:
                error = str(exc) if isinstance(exc, ValueError) else 'Este empleado ya tiene un expediente abierto. Revísalo desde la lista.'
        return render_template('paz_nuevo.html', empleados=empleados, elegido=elegido, responsables=responsables,
                               sugeridos=sugeridos, error=error, hoy=date.today().isoformat())

    @bp.get('/<int:id>')
    def ver(id):
        e = expediente(id)
        revisiones = rows('SELECT * FROM paz_revisiones WHERE expediente_id=? ORDER BY id', (id,))
        adjuntos = rows('SELECT id,revision_id,nombre,tipo,sha256,creado_en FROM paz_adjuntos WHERE expediente_id=? ORDER BY id', (id,))
        roles = rows('SELECT c.id,c.anio,c.mes,d.neto FROM roles_detalle d JOIN roles_cabecera c ON c.id=d.rol_id WHERE d.empleado_id=? ORDER BY c.anio DESC,c.mes DESC LIMIT 3', (e['empleado_id'],))
        subordinados = rows('SELECT nombres,apellidos,activo FROM empleados WHERE reporta_a=?', (e['empleado_id'],))
        requisitos = rows('SELECT q.* FROM paz_requisitos q JOIN paz_revisiones r ON r.id=q.revision_id WHERE r.expediente_id=? ORDER BY q.id', (id,))
        liq = rows('SELECT estado,resultado FROM paz_liquidaciones WHERE expediente_id=?', (id,))
        documentos = rows('SELECT tipo,sha256 FROM paz_documentos WHERE expediente_id=?', (id,))
        return render_template('paz_ver_completo.html' if e['version_flujo']==2 else 'paz_ver.html', e=e, revisiones=revisiones, adjuntos=adjuntos, roles=roles,
                               requisitos=requisitos, liquidacion=liq[0] if liq else None, documentos=documentos,
                               hoy=date.today().isoformat(),
                               eventos=rows('SELECT * FROM paz_eventos WHERE expediente_id=? ORDER BY id DESC', (id,)),
                               subordinados=subordinados, limite_sut=(date.fromisoformat(e['fecha_salida']) + timedelta(days=15)).isoformat())

    @bp.post('/<int:id>/revision/<int:revision>')
    def revisar(id, revision):
        db().execute('BEGIN IMMEDIATE')
        e = expediente(id)
        r = rows('SELECT * FROM paz_revisiones WHERE id=? AND expediente_id=?', (revision, id))
        if not r:
            abort(404)
        estado = request.form.get('estado')
        nota = request.form.get('observacion', '').strip()
        if e['estado'] != 'en_revision':
            abort(409, 'El expediente ya está cerrado para cambios.')
        if estado not in ('pendiente', 'observado', 'conforme', 'no_aplica') or not nota or len(nota) > 3000:
            abort(400, 'Selecciona un estado y describe la revisión (máximo 3000 caracteres).')
        pendientes = rows("SELECT estado FROM paz_requisitos WHERE revision_id=? AND bloquea=1", (revision,))
        if estado in ('conforme','no_aplica') and any(x['estado'] not in ('conforme','no_aplica') for x in pendientes):
            flash('Resuelve los requisitos individuales obligatorios de esta área antes de aprobarla.', 'warning')
            return redirect(url_for('paz.ver', id=id, _anchor=f'area-{revision}'))
        if estado == 'conforme' and not db().execute('SELECT 1 FROM paz_adjuntos WHERE revision_id=?', (revision,)).fetchone():
            flash('Adjunta el respaldo de esta revisión antes de marcarla conforme.', 'warning')
        elif estado in ('conforme', 'no_aplica') and not request.form.get('confirmacion'):
            flash('Confirma que verificaste la revisión del responsable indicado.', 'warning')
        elif r[0]['area'] == 'jefatura' and estado in ('conforme', 'no_aplica') and db().execute(
                'SELECT 1 FROM empleados WHERE reporta_a=? AND activo=1', (e['empleado_id'],)).fetchone():
            flash('Reasigna primero los subordinados activos desde Empleados.', 'warning')
        else:
            with db():
                db().execute('UPDATE paz_revisiones SET estado=?,observacion=?,revisado_en=? WHERE id=?', (estado, nota, ahora(), revision))
                evento(id, f"{AREAS[r[0]['area']][0]} · {r[0]['responsable']} · {estado}: {nota}")
        return redirect(url_for('paz.ver', id=id))

    @bp.post('/<int:id>/adjuntos')
    def adjuntar(id):
        # Límite específico: el logo y el resto de formularios conservan su límite de 2 MB.
        e = expediente(id)
        tipo = request.form.get('tipo', 'respaldo')
        revision = request.form.get('revision', type=int)
        if tipo not in ('respaldo', 'firmado', 'seguimiento'):
            abort(400)
        if (tipo == 'respaldo' and e['estado'] != 'en_revision') or (tipo == 'firmado' and e['estado'] != 'emitido'):
            abort(409, 'Este estado no permite cargar ese documento.')
        if tipo == 'respaldo' and not db().execute('SELECT 1 FROM paz_revisiones WHERE id=? AND expediente_id=?', (revision, id)).fetchone():
            abort(400, 'Selecciona la revisión a la que corresponde el respaldo.')
        if tipo == 'seguimiento' and (e['estado'] not in ('emitido','firmado') or not db().execute(
                "SELECT 1 FROM paz_revisiones WHERE id=? AND expediente_id=? AND area='talento'", (revision,id)).fetchone()):
            abort(400, 'Los respaldos posteriores se incorporan al seguimiento legal de Talento humano.')
        if tipo != 'firmado' and db().execute("SELECT 1 FROM paz_revisiones WHERE id=? AND area='salud'", (revision,)).fetchone() and not request.form.get('sin_diagnosticos'):
            abort(400, 'En medicina ocupacional carga solo una constancia administrativa sin diagnósticos ni historia clínica.')
        if tipo == 'firmado' and not request.form.get('firmas_verificadas'):
            abort(400, 'Confirma que revisaste las firmas y que corresponden al PDF emitido.')
        archivo = request.files.get('archivo')
        if not archivo or not archivo.filename:
            abort(400, 'Selecciona un archivo.')
        nombre = secure_filename(archivo.filename)[:180]
        extension = Path(nombre).suffix.lower()
        contenido = archivo.stream.read(MAX_FILE + 1)
        if not contenido or len(contenido) > MAX_FILE:
            abort(400, 'Archivo vacío o mayor a 10 MB.')
        mime = {'.pdf': 'application/pdf', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}.get(extension)
        if not mime or (tipo == 'firmado' and extension != '.pdf'):
            abort(400, 'Usa PDF, PNG o JPG; el documento firmado debe ser PDF.')
        try:
            if extension == '.pdf':
                from pypdf import PdfReader
                if not contenido.startswith(b'%PDF-'):
                    raise ValueError()
                lector = PdfReader(io.BytesIO(contenido))
                if lector.is_encrypted or not 1 <= len(lector.pages) <= 200:
                    raise ValueError()
                # No admitir PDF con adjuntos, JavaScript o acciones automáticas.
                raiz = lector.trailer['/Root']
                nombres = raiz['/Names'] if '/Names' in raiz else {}
                if any(k in raiz for k in ('/OpenAction', '/AA')) or any(
                        k in nombres for k in ('/JavaScript', '/EmbeddedFiles')):
                    raise ValueError()
            else:
                from PIL import Image
                with Image.open(io.BytesIO(contenido)) as imagen:
                    if imagen.format != ('PNG' if extension == '.png' else 'JPEG'):
                        raise ValueError()
                    imagen.verify()
        except Exception:
            abort(400, 'El contenido no es válido, está protegido o contiene elementos no admitidos. Exporta un PDF simple o una imagen.')
        with db():
            # Serializa cambios de estado y carga para impedir modificaciones posteriores a la emisión.
            db().execute('BEGIN IMMEDIATE')
            if expediente(id)['estado'] != e['estado']:
                abort(409)
            if db().execute('SELECT COUNT(*) FROM paz_adjuntos WHERE expediente_id=?', (id,)).fetchone()[0] >= 50:
                abort(400, 'Máximo 50 archivos por expediente.')
            aid = db().execute('INSERT INTO paz_adjuntos(expediente_id,revision_id,tipo,nombre,mime,contenido,sha256,creado_en) VALUES (?,?,?,?,?,?,?,?)',
                               (id, revision if tipo != 'firmado' else None, tipo, nombre, mime, contenido, hashlib.sha256(contenido).hexdigest(), ahora())).lastrowid
            evento(id, f'Archivo {tipo} incorporado: {nombre}; SHA-256 {hashlib.sha256(contenido).hexdigest()}')
            if tipo == 'firmado':
                db().execute("UPDATE paz_expedientes SET estado='firmado',firmado_id=? WHERE id=?", (aid, id))
                evento(id, 'Copia firmada archivada tras verificación manual del operador; no es validación criptográfica.')
        return redirect(url_for('paz.ver', id=id))

    @app.before_request
    def limite_adjuntos():
        if request.endpoint == 'paz.adjuntar':
            request.max_content_length = MAX_FILE + 512 * 1024

    @bp.get('/<int:id>/adjuntos/<int:adjunto>')
    def descargar(id, adjunto):
        archivo = rows('SELECT * FROM paz_adjuntos WHERE id=? AND expediente_id=?', (adjunto, id))
        if not archivo:
            abort(404)
        a = archivo[0]
        response = send_file(io.BytesIO(a['contenido']), mimetype=a['mime'], as_attachment=request.args.get('ver') != '1', download_name=a['nombre'])
        response.headers['Content-Security-Policy'] = "sandbox; default-src 'none'"
        return response

    @bp.get('/<int:id>/evidencia/<int:adjunto>')
    def visualizar(id, adjunto):
        archivo = rows('SELECT id,nombre,mime,sha256 FROM paz_adjuntos WHERE id=? AND expediente_id=?', (adjunto,id))
        if not archivo:
            abort(404)
        return render_template('paz_evidencia.html', e=expediente(id), a=archivo[0])

    @bp.post('/<int:id>/requisito/<int:requisito>')
    def requisito_guardar(id, requisito):
        with db():
            db().execute('BEGIN IMMEDIATE')
            e = expediente(id)
            q = rows('SELECT q.*,r.area FROM paz_requisitos q JOIN paz_revisiones r ON r.id=q.revision_id WHERE q.id=? AND r.expediente_id=?', (requisito,id))
            if not q:
                abort(404)
            q=q[0]
            if e['estado'] != 'en_revision' and not (e['estado'] in ('emitido','firmado') and not q['bloquea']):
                abort(409)
            estado = request.form.get('estado')
            nota = request.form.get('observacion','').strip()
            evidencia = request.form.get('evidencia', type=int)
            try:
                fecha = date.fromisoformat(request.form.get('fecha',''))
            except ValueError:
                abort(400, 'Indica una fecha válida para la verificación.')
            if fecha > date.today() or estado not in ('pendiente','observado','conforme','no_aplica') or not nota or len(nota)>3000:
                abort(400, 'Revisa el estado, la fecha (no futura) y la observación (hasta 3000 caracteres).')
            if estado in ('conforme','no_aplica') and not request.form.get('confirmacion'):
                abort(400, 'Confirma la verificación del requisito.')
            if estado == 'conforme' and not db().execute('SELECT 1 FROM paz_adjuntos WHERE id=? AND expediente_id=? AND revision_id=?', (evidencia,id,q['revision_id'])).fetchone():
                abort(400, 'Selecciona una evidencia de esta área para marcar conforme.')
            db().execute('UPDATE paz_requisitos SET estado=?,observacion=?,fecha=?,evidencia_id=? WHERE id=?',
                         (estado,nota,fecha.isoformat(),evidencia if estado=='conforme' else None,requisito))
            if e['estado']=='en_revision':
                db().execute("UPDATE paz_revisiones SET estado='pendiente' WHERE id=?", (q['revision_id'],))
            evento(id, f"Requisito: {q['titulo']} · {estado} · fecha {fecha}: {nota}")
        return redirect(url_for('paz.ver', id=id, _anchor=f"area-{q['revision_id']}"))

    @bp.post('/<int:id>/emitir')
    def emitir(id):
        with db():
            db().execute('BEGIN IMMEDIATE')
            e = expediente(id)
            revisiones = rows('SELECT * FROM paz_revisiones WHERE expediente_id=? ORDER BY id', (id,))
            if e['estado'] != 'en_revision':
                abort(409)
            if not revisiones or any(r['estado'] not in ('conforme', 'no_aplica') for r in revisiones):
                flash('Completa las revisiones de todas las áreas y resuelve las observaciones antes de emitir.', 'warning')
                return redirect(url_for('paz.ver', id=id))
            if db().execute('SELECT 1 FROM empleados WHERE reporta_a=? AND activo=1', (e['empleado_id'],)).fetchone():
                flash('Hay subordinados activos pendientes de reasignación.', 'warning')
                return redirect(url_for('paz.ver', id=id))
            emitido = ahora()
            adjuntos = rows('SELECT nombre,sha256,revision_id FROM paz_adjuntos WHERE expediente_id=? ORDER BY id', (id,))
            if e['version_flujo']==2:
                liq = rows("SELECT * FROM paz_liquidaciones WHERE expediente_id=? AND estado='aprobado'", (id,))
                requisitos = rows('SELECT q.* FROM paz_requisitos q JOIN paz_revisiones r ON r.id=q.revision_id WHERE r.expediente_id=?', (id,))
                if len(revisiones)!=len(AREAS) or not requisitos or any(q['bloquea'] and q['estado'] not in ('conforme','no_aplica') for q in requisitos) or not liq:
                    flash('Verifica los requisitos obligatorios y aprueba la liquidación antes de emitir el resumen final.', 'warning')
                    return redirect(url_for('paz.ver', id=id))
                from documentos_laborales import crear
                for tipo in ('paz','liquidacion','resumen'):
                    contenido = liq[0]['pdf'] if tipo=='liquidacion' else crear(tipo,e,revisiones,requisitos,json.loads(liq[0]['resultado']),emitido,AREAS,ALCANCE)
                    db().execute('INSERT INTO paz_documentos VALUES (?,?,?,?,?)', (id,tipo,contenido,hashlib.sha256(contenido).hexdigest(),emitido))
                pdf = contenido  # último documento: resumen general para firma de las partes
            else:
                pdf = generar_pdf(e, revisiones, adjuntos, emitido)
            db().execute("UPDATE paz_expedientes SET estado='emitido',emitido_en=?,pdf=?,pdf_hash=? WHERE id=?",
                         (emitido, pdf, hashlib.sha256(pdf).hexdigest(), id))
            evento(id, 'PDF emitido e inmovilizado para firma de las partes.')
        return redirect(url_for('paz.ver', id=id))

    @bp.get('/<int:id>/pdf')
    def pdf(id):
        e = expediente(id)
        if not e['pdf']:
            abort(409, 'Completa las revisiones y emite el documento primero.')
        return send_file(io.BytesIO(e['pdf']), mimetype='application/pdf', as_attachment=True,
                         download_name=f"{'resumen-final' if e['version_flujo']==2 else 'paz-salvo'}-{id:06d}.pdf")

    @bp.route('/<int:id>/liquidacion', methods=['GET','POST'])
    def liquidar(id):
        e=expediente(id)
        if e['version_flujo']!=2:
            abort(409, 'Expediente histórico del flujo anterior. Sus documentos permanecen sin modificaciones.')
        guardada=rows('SELECT * FROM paz_liquidaciones WHERE expediente_id=?', (id,))
        d=e['datos']
        valores={k:'0' for k in liquidacion.CAMPOS}
        valores['fecha_consulta']=date.today().isoformat()
        if guardada:
            valores.update(json.loads(guardada[0]['entradas']))
        resultado=json.loads(guardada[0]['resultado']) if guardada else None
        error=None
        if request.method=='POST':
            if e['estado']!='en_revision':
                abort(409, 'La liquidación del expediente emitido es inmutable.')
            valores={k:request.form.get(k,'') for k in [*liquidacion.CAMPOS,'fecha_consulta','justificacion','evidencia_finanzas','evidencia_vacaciones','evidencia_ministerio']}
            try:
                if not 15<=len(valores['justificacion'].strip())<=6000:
                    raise ValueError('Explica las bases, períodos, pagos previos, ajustes y deducciones en 15 a 6000 caracteres.')
                resultado=liquidacion.registrar_resultado(valores,d['fecha_ingreso'],e['fecha_salida'],d['regimen'],e['causa'],d.get('region','Sierra'))
                aprobar=request.form.get('accion')=='aprobar'
                if aprobar:
                    if not request.form.get('confirmacion'):
                        raise ValueError('Confirma la revisión financiera y de Talento humano antes de aprobar.')
                    for campo,area in [('evidencia_finanzas','finanzas'),('evidencia_vacaciones','talento'),('evidencia_ministerio','finanzas')]:
                        if not db().execute('SELECT 1 FROM paz_adjuntos a JOIN paz_revisiones r ON r.id=a.revision_id WHERE a.id=? AND a.expediente_id=? AND r.area=?', (valores[campo],id,area)).fetchone():
                            raise ValueError('Selecciona la captura o PDF del resultado ministerial en Finanzas, la conciliación y el kárdex en Talento humano, todos del mismo expediente.')
                with db():
                    db().execute('BEGIN IMMEDIATE')
                    if expediente(id)['estado']!='en_revision':
                        abort(409)
                    pdf=None
                    if aprobar:
                        from documentos_laborales import crear
                        pdf=crear('liquidacion',e,rows('SELECT * FROM paz_revisiones WHERE expediente_id=?',(id,)),[],resultado,ahora(),AREAS,ALCANCE)
                    db().execute('INSERT INTO paz_liquidaciones(expediente_id,entradas,resultado,estado,actualizado_en,aprobado_en,pdf,pdf_hash) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(expediente_id) DO UPDATE SET entradas=excluded.entradas,resultado=excluded.resultado,estado=excluded.estado,actualizado_en=excluded.actualizado_en,aprobado_en=excluded.aprobado_en,pdf=excluded.pdf,pdf_hash=excluded.pdf_hash',
                                 (id,json.dumps(valores,ensure_ascii=False),json.dumps(resultado,ensure_ascii=False),'aprobado' if aprobar else 'borrador',ahora(),ahora() if aprobar else None,pdf,hashlib.sha256(pdf).hexdigest() if pdf else None))
                    evento(id, f"Liquidación {'aprobada' if aprobar else 'registrada en borrador'}: haberes USD {resultado['total_haberes']}, deducciones USD {resultado['total_deducciones']}, neto USD {resultado['neto']}. Datos de consulta y justificación: {json.dumps(valores,ensure_ascii=False)}")
                flash('Resultados oficiales verificados y aprobados; ya puedes descargar su PDF.' if aprobar else 'Transcripción guardada. Coteja los valores con la evidencia antes de aprobar.', 'success')
                return redirect(url_for('paz.liquidar',id=id))
            except ValueError as exc:
                error=str(exc)
        evidencias=rows('SELECT a.id,a.nombre,r.area FROM paz_adjuntos a JOIN paz_revisiones r ON r.id=a.revision_id WHERE a.expediente_id=? AND r.area IN (\'finanzas\',\'talento\')',(id,))
        return render_template('paz_liquidacion.html',e=e,valores=valores,resultado=resultado,campos=liquidacion.CAMPOS,evidencias=evidencias,error=error,
                               estado=guardada[0]['estado'] if guardada else 'sin calcular',fuentes=liquidacion.SOURCES)

    @bp.get('/<int:id>/documento/<tipo>')
    def documento(id,tipo):
        if tipo not in ('paz','liquidacion','resumen'):
            abort(404)
        e=expediente(id)
        registros=rows('SELECT pdf FROM paz_documentos WHERE expediente_id=? AND tipo=?',(id,tipo))
        if not registros and tipo=='liquidacion':
            registros=rows("SELECT pdf FROM paz_liquidaciones WHERE expediente_id=? AND estado='aprobado'",(id,))
        if not registros:
            abort(409, 'El documento aún no ha sido aprobado o emitido.')
        return send_file(io.BytesIO(registros[0]['pdf']),mimetype='application/pdf',as_attachment=request.args.get('ver')!='1',download_name=f'{tipo}-PS-{id:06d}.pdf')

    @bp.post('/<int:id>/liquidacion/leer-pdf')
    def leer_pdf(id):
        e=expediente(id)
        if e['estado']!='en_revision' or e['version_flujo']!=2:
            abort(409)
        evidencia=request.form.get('evidencia',type=int)
        archivos=rows("SELECT a.* FROM paz_adjuntos a JOIN paz_revisiones r ON r.id=a.revision_id WHERE a.id=? AND a.expediente_id=? AND a.mime='application/pdf' AND r.area='finanzas'",(evidencia,id))
        if not archivos:
            abort(400,'Selecciona el PDF ministerial cargado en Finanzas.')
        try:
            importados=liquidacion.leer_pdf_oficial(archivos[0]['contenido'])
        except Exception as exc:
            flash(str(exc) if isinstance(exc,ValueError) else 'No se pudo leer el PDF. Registra los valores manualmente conservando el respaldo.','warning')
            return redirect(url_for('paz.liquidar',id=id))
        with db():
            db().execute('BEGIN IMMEDIATE')
            if expediente(id)['estado']!='en_revision':
                abort(409)
            anterior=rows('SELECT entradas FROM paz_liquidaciones WHERE expediente_id=?',(id,))
            valores={k:'0' for k in liquidacion.CAMPOS}
            if anterior:
                valores.update(json.loads(anterior[0]['entradas']))
            valores.update(importados,evidencia_ministerio=str(evidencia))
            valores.setdefault('fecha_consulta',date.today().isoformat())
            db().execute("INSERT INTO paz_liquidaciones(expediente_id,entradas,resultado,estado,actualizado_en) VALUES (?,?,?,'borrador',?) ON CONFLICT(expediente_id) DO UPDATE SET entradas=excluded.entradas,resultado='{}',estado='borrador',actualizado_en=excluded.actualizado_en,aprobado_en=NULL,pdf=NULL,pdf_hash=NULL",(id,json.dumps(valores,ensure_ascii=False),'{}',ahora()))
            evento(id,f'Lectura asistida del PDF adjunto {evidencia}: total ministerial USD {importados["total_ministerio"]}. Pendiente de cotejo visual y validación de datos de entrada.')
        flash('Se leyeron los rubros del PDF. Revisa los datos de consulta, registra el kárdex y coteja visualmente antes de aprobar.','success')
        return redirect(url_for('paz.liquidar',id=id))

    @bp.get('/<int:id>/descargar-expediente')
    def exportar_expediente(id):
        import zipfile
        e=expediente(id)
        b=io.BytesIO()
        archivos=rows('SELECT * FROM paz_adjuntos WHERE expediente_id=?',(id,))
        with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
            for a in archivos:
                z.writestr(f"evidencias/{a['id']:04d}-{a['nombre']}",a['contenido'])
            for doc in rows('SELECT * FROM paz_documentos WHERE expediente_id=?',(id,)):
                z.writestr(doc['tipo']+'.pdf',doc['pdf'])
            z.writestr('indice.json',json.dumps(dict(expediente={k:v for k,v in e.items() if k not in ('pdf',)},
                                                   archivos=[{k:a[k] for k in ('id','nombre','tipo','sha256','creado_en')} for a in archivos],
                                                   historial=rows('SELECT * FROM paz_eventos WHERE expediente_id=?',(id,))),ensure_ascii=False,indent=2))
        return send_file(io.BytesIO(b.getvalue()),mimetype='application/zip',as_attachment=True,download_name=f'expediente-PS-{id:06d}.zip')

    @bp.post('/<int:id>/anular')
    def anular(id):
        razon = request.form.get('razon', '').strip()
        if not razon or len(razon) > 1000:
            abort(400, 'Indica el motivo de anulación (máximo 1000 caracteres).')
        with db():
            db().execute('BEGIN IMMEDIATE')
            if expediente(id)['estado'] not in ('en_revision', 'emitido'):
                abort(409)
            db().execute("UPDATE paz_expedientes SET estado='anulado' WHERE id=?", (id,))
            evento(id, 'ANULADO: ' + razon + '. El PDF anterior, si existe, se conserva únicamente como antecedente.')
        return redirect(url_for('paz.ver', id=id))

    app.register_blueprint(bp)


def generar_pdf(e, revisiones, adjuntos, emitido):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

    salida = io.BytesIO()
    estilos = getSampleStyleSheet()
    estilos.add(ParagraphStyle('SmallPaz', parent=estilos['BodyText'], fontSize=8, leading=11, wordWrap='CJK'))
    estilos.add(ParagraphStyle('FirmaPaz', parent=estilos['BodyText'], alignment=TA_CENTER, fontSize=9))
    def p(texto, estilo='BodyText'):
        return Paragraph(escape(str(texto)).replace('\n', '<br/>'), estilos[estilo])
    datos = e['datos']
    story = [p(datos['empresa'], 'Title'), p('PAZ Y SALVO · CONSTANCIA INTERNA', 'Heading1'),
             p(f"Expediente PS-{e['id']:06d} · RUC {datos['ruc']} · Emitido {emitido}", 'SmallPaz'),
             Spacer(1, 5 * mm), p(f"Trabajador: {datos['nombres']} {datos['apellidos']} · Cédula {datos['cedula']}"),
             p(f"Cargo: {datos['cargo']} · Departamento: {datos['departamento']}"),
             p(f"Ingreso: {datos['fecha_ingreso']} · Salida prevista/efectiva: {e['fecha_salida']} · Régimen: {datos['regimen']}"),
             p(f"Jefe registrado al abrir: {datos['jefe']}"), p(f"Motivo informado: {e['motivo']}"),
             Spacer(1, 4 * mm), p('Alcance y derechos', 'Heading2'), p(ALCANCE),
             p('Revisiones registradas', 'Heading2')]
    if datos.get('delegacion'):
        story.append(p('Designación de jefatura: ' + datos['delegacion']))
    for r in revisiones:
        story.append(KeepTogether([p(f"{AREAS[r['area']][0]} · {r['estado'].replace('_', ' ')}", 'Heading3'),
                                  p(f"Responsable: {r['responsable']} · {r['cargo']}"),
                                  p(r['observacion']), p(f"Registrado: {r['revisado_en']}", 'SmallPaz')]))
    story += [p('Respaldos del expediente', 'Heading2')]
    por_revision = {r['id']: AREAS[r['area']][0] for r in revisiones}
    for a in adjuntos:
        story += [p(f"{por_revision.get(a['revision_id'], 'Respaldo')}: {a['nombre']} · SHA-256: {a['sha256']}", 'SmallPaz')]
    story += [Spacer(1, 5 * mm), p('Firmas de las partes', 'Heading2'),
              p(f"Expediente PS-{e['id']:06d} · {datos['nombres']} {datos['apellidos']} · CI {datos['cedula']} · Salida: {e['fecha_salida']}", 'SmallPaz'),
              p('Las firmas dejan constancia de las entregas y revisiones descritas, con el alcance indicado. '
                'Cada parte recibirá una copia. Lugar y fecha de firma: __________________________________'), Spacer(1, 15 * mm)]
    tabla = Table([[p('________________________________', 'FirmaPaz'), p('________________________________', 'FirmaPaz')],
                   [p(f"{datos['nombres']} {datos['apellidos']}", 'FirmaPaz'), p(datos['representante'], 'FirmaPaz')],
                   [p(f"Trabajador · CI {datos['cedula']}", 'FirmaPaz'), p(f"Por el empleador · CI {datos['representante_cedula']}", 'FirmaPaz')],
                   [p('', 'FirmaPaz'), p(datos['representante_cargo'], 'FirmaPaz')]], colWidths=[85 * mm, 85 * mm])
    tabla.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story += [KeepTogether(tabla), Spacer(1, 5 * mm),
              p('Registro administrativo centralizado: las revisiones no son firmas electrónicas ni acreditan por sí solas la identidad del responsable. '
                'Los respaldos se conservan en el expediente y no se fusionan con este PDF.', 'SmallPaz')]
    def pie(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(20 * mm, 12 * mm, f"PS-{e['id']:06d} · Constancia interna · Página {doc.page}")
        canvas.restoreState()
    SimpleDocTemplate(salida, pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm,
                      topMargin=18 * mm, bottomMargin=22 * mm, title=f"Paz y salvo PS-{e['id']:06d}").build(story, onFirstPage=pie, onLaterPages=pie)
    return salida.getvalue()
