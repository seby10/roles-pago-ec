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
"""
AREAS = {
    'jefatura': ('Jefe inmediato', 'Entrega de funciones, proyectos, documentos y reasignación de subordinados.'),
    'tecnologia': ('Tecnología y bienes', 'Equipos, activos, credenciales y revocación de accesos en la fecha efectiva.'),
    'finanzas': ('Finanzas', 'Conciliación de nómina, anticipos, préstamos y respaldos; sin descuentos automáticos.'),
    'talento': ('Talento humano', 'Revisar vacaciones, beneficios, liquidación y trámites de salida según régimen.'),
}
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
        return dict(paz_csrf=token, PAZ_AREAS=AREAS, PAZ_ALCANCE=ALCANCE)

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
                with db():
                    id = db().execute('INSERT INTO paz_expedientes(empleado_id,snapshot,fecha_salida,motivo,creado_en) VALUES (?,?,?,?,?)',
                                      (seleccionado, json.dumps(snapshot, ensure_ascii=False), salida.isoformat(), motivo, ahora())).lastrowid
                    for area, persona in asignados.items():
                        db().execute('INSERT INTO paz_revisiones(expediente_id,area,responsable_id,responsable,cargo) VALUES (?,?,?,?,?)',
                                     (id, area, persona['id'], f"{persona['nombres']} {persona['apellidos']}", persona['cargo']))
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
        return render_template('paz_ver.html', e=e, revisiones=revisiones, adjuntos=adjuntos, roles=roles,
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
        if tipo not in ('respaldo', 'firmado'):
            abort(400)
        if (tipo == 'respaldo' and e['estado'] != 'en_revision') or (tipo == 'firmado' and e['estado'] != 'emitido'):
            abort(409, 'Este estado no permite cargar ese documento.')
        if tipo == 'respaldo' and not db().execute('SELECT 1 FROM paz_revisiones WHERE id=? AND expediente_id=?', (revision, id)).fetchone():
            abort(400, 'Selecciona la revisión a la que corresponde el respaldo.')
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
                               (id, revision if tipo == 'respaldo' else None, tipo, nombre, mime, contenido, hashlib.sha256(contenido).hexdigest(), ahora())).lastrowid
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
        return send_file(io.BytesIO(a['contenido']), mimetype=a['mime'], as_attachment=True, download_name=a['nombre'])

    @bp.post('/<int:id>/emitir')
    def emitir(id):
        with db():
            db().execute('BEGIN IMMEDIATE')
            e = expediente(id)
            revisiones = rows('SELECT * FROM paz_revisiones WHERE expediente_id=? ORDER BY id', (id,))
            if e['estado'] != 'en_revision':
                abort(409)
            if len(revisiones) != 4 or any(r['estado'] not in ('conforme', 'no_aplica') for r in revisiones):
                flash('Completa las cuatro revisiones y resuelve las observaciones antes de emitir.', 'warning')
                return redirect(url_for('paz.ver', id=id))
            if db().execute('SELECT 1 FROM empleados WHERE reporta_a=? AND activo=1', (e['empleado_id'],)).fetchone():
                flash('Hay subordinados activos pendientes de reasignación.', 'warning')
                return redirect(url_for('paz.ver', id=id))
            emitido = ahora()
            adjuntos = rows('SELECT nombre,sha256,revision_id FROM paz_adjuntos WHERE expediente_id=? ORDER BY id', (id,))
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
                         download_name=f"paz-salvo-{id:06d}.pdf")

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
