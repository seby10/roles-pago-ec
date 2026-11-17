"""Tres salidas del mismo expediente: certificado, liquidación y resumen de firma."""
import io
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether


def crear(tipo, e, revisiones, requisitos, resultado, emitido, areas, alcance):
    titulos={'paz':'Certificado de paz y salvo administrativo','liquidacion':'Liquidación laboral detallada','resumen':'Resumen general para firma de las partes'}
    b=io.BytesIO()
    estilos=getSampleStyleSheet()
    estilos.add(ParagraphStyle('small', parent=estilos['BodyText'], fontSize=8, leading=11, wordWrap='CJK'))
    estilos['BodyText'].fontSize=9
    estilos['BodyText'].leading=13
    d=e['datos']
    def p(s, style='BodyText'):
        return Paragraph(escape(str(s)).replace('\n','<br/>'), estilos[style])
    def tabla(filas, anchos):
        t=Table([[p(c, 'small') for c in fila] for fila in filas], colWidths=[x*mm for x in anchos], repeatRows=1, hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9eef3')),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#cbd5df')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
        return t
    story=[p(d['empresa'],'Title'),p(titulos[tipo],'Heading1'),p(f"PS-{e['id']:06d} | RUC {d['ruc']} | Régimen {d['regimen']} | Emisión {emitido}",'small'),Spacer(1,4*mm),
           p(f"Trabajador: {d['nombres']} {d['apellidos']} | CI {d['cedula']}"),p(f"Cargo: {d['cargo']} | Departamento: {d['departamento']}"),
           p(f"Ingreso {d['fecha_ingreso']} | Salida {e['fecha_salida']} | Última remuneración USD {d.get('sueldo','ver bases aprobadas')}"),
           p(f"Causa: {resultado['causa']}"),p(f"Detalle: {e['motivo']}"),Spacer(1,3*mm)]
    if tipo in ('paz','resumen'):
        story += [p('Verificación por departamentos','Heading2'),tabla([['Área','Responsable de verificación','Estado','Registro']]+[[areas[r['area']][0],r['responsable'],r['estado'].replace('_',' '),(r['revisado_en'] or '')[:10]] for r in revisiones],[40,62,30,38])]
        if tipo=='paz':
            for r in revisiones:
                story.append(KeepTogether([p(areas[r['area']][0],'Heading2'),
                    tabla([['Requisito','Estado y fecha','Evidencia']]+[[q['titulo'],q['estado'].replace('_',' ')+'\n'+(q['fecha'] or ''),('Archivo #'+str(q['evidencia_id'])) if q['evidencia_id'] else 'Ver observación en expediente'] for q in requisitos if q['revision_id']==r['id']],[105,30,35])]))
            story.append(p('Las observaciones completas y los archivos de cada verificación se conservan en el expediente digital. Los números de archivo identifican sus respaldos.','small'))
        seguimientos=[q for q in requisitos if not q['bloquea']]
        if seguimientos:
            story += [p('Seguimiento legal independiente','Heading2'),p('Estas actuaciones pueden completarse después de este resumen, dentro de los plazos aplicables. El estado corresponde a la fecha de emisión.'),tabla([['Trámite','Estado','Observación']]+[[q['titulo'],q['estado'].replace('_',' '),q['observacion'] or 'Pendiente de seguimiento'] for q in seguimientos],[75,30,65])]
    if tipo in ('liquidacion','resumen'):
        story += [p('Fuente de los valores de liquidación','Heading2'),p('Calculadora oficial del Ministerio del Trabajo: '+resultado['fuente_url'],'small'),p('Consulta: '+resultado['fecha_consulta']+' | Total aproximado informado por el Ministerio: USD '+resultado['total_oficial'])]
        vac=resultado['vacaciones']
        story += [p('Control de vacaciones','Heading2'),p(f"Saldo anterior {vac['anterior']} + devengadas {vac['devengadas']} - gozadas {vac['gozadas']} + ajuste {vac['ajuste']} = saldo {vac['saldo']} días. Días sin gozar utilizados en la consulta oficial: {vac['liquidables']}."),
                  p('Detalle de haberes','Heading2')]
        def rubros(lineas):
            if tipo=='liquidacion':
                return tabla([['Concepto','Origen y respaldo','USD']]+[[r['concepto'],r['formula'],r['valor']] for r in lineas],[58,87,25])
            filas=[[r['concepto'],r['valor']] for r in lineas if r['valor']!='0.00']
            return tabla([['Concepto','USD']]+(filas or [['Sin importes pendientes registrados','0.00']]),[140,30])
        story += [rubros(resultado['ingresos']),p('Deducciones','Heading2'),rubros(resultado['descuentos']),Spacer(1,3*mm),
                  tabla([['Total haberes','Total deducciones','Valor neto a pagar USD'],[resultado['total_haberes'],resultado['total_deducciones'],resultado['neto']]],[57,56,57]),
                  p(resultado['metodo'],'small')]
        if tipo=='liquidacion':
            story += [p('Validación administrativa','Heading2'),p('Elaboración y revisión financiera: '+next((r['responsable'] for r in revisiones if r['area']=='finanzas'),'')),p('Control de vacaciones y documentación: '+next((r['responsable'] for r in revisiones if r['area']=='talento'),'')),p('Representante designado por el empleador: '+d['representante'])]
        for aviso in resultado['avisos']:
            story.append(p(aviso))
    story += [p('Alcance del documento','Heading2'),p(alcance)]
    if tipo=='resumen':
        texto=f"PS-{e['id']:06d} | {d['nombres']} {d['apellidos']} | CI {d['cedula']} | Neto USD {resultado['neto']}"
        story.append(KeepTogether([p('Firmas de las partes','Heading2'),p(texto,'small'),p('Las partes suscriben el resumen de verificaciones y valores descritos. La firma no constituye prueba de pago por sí sola. Lugar y fecha: ____________________________________'),Spacer(1,13*mm),
                                  tabla([['Trabajador','Por el empleador'],['Firma: __________________________','Firma: __________________________'],[d['nombres']+' '+d['apellidos'],d['representante']],['CI '+d['cedula'],'CI '+d['representante_cedula']]],[85,85])]))
    elif tipo=='liquidacion':
        story.append(KeepTogether([p('Constancia y firmas','Heading2'),p('Valores sujetos a los respaldos del expediente. No constituye un comprobante de pago ni el acta oficial SUT.'),Spacer(1,12*mm),tabla([['Trabajador','Representante del empleador'],['Firma: __________________________','Firma: __________________________'],[d['nombres']+' '+d['apellidos'],d['representante']]],[85,85])]))
    story += [Spacer(1,3*mm),p('La copia suscrita del resumen general se archiva en el expediente. Los archivos de respaldo se consultan separadamente. Verificaciones registradas por un operador administrativo; sin certificación electrónica de identidad.','small')]
    def pie(c, doc):
        c.saveState();c.setFont('Helvetica',8);c.setFillColor(colors.grey)
        c.drawString(20*mm,12*mm,f"PS-{e['id']:06d} | {titulos[tipo]} | Página {doc.page}")
        c.restoreState()
    SimpleDocTemplate(b,pagesize=A4,leftMargin=20*mm,rightMargin=20*mm,topMargin=17*mm,bottomMargin=22*mm,title=titulos[tipo]).build(story,onFirstPage=pie,onLaterPages=pie)
    return b.getvalue()
