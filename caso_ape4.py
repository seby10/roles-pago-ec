"""Datos y documentos ficticios reproducibles para demostrar la guía APE 4."""
import io
import liquidacion
from pathlib import Path

CEDULA = '1729999902'
INGRESO='2026-10-01'
SALIDA='2026-11-17'
NOMBRE='Mateo Demostración Rivera'
DIRECTORIO=Path(__file__).parent/'casos'/'ape4'


def entradas():
    r={k:'0' for k in liquidacion.CAMPOS}
    r.update(decimo13='66.58',decimo14='62.93',vacaciones='33.32',total_ministerio='162.83',devengadas='1.96',vacaciones_pendientes='1.96',fecha_consulta='2026-11-17',
             justificacion='CASO FICTICIO APE 4. Consulta REAL al simulador oficial del Ministerio del Trabajo el 17/11/2026: acuerdo entre las partes, Sierra, ingreso 01/10/2026, salida 17/11/2026, remuneración USD 510, ambos décimos acumulados y 1,96 días sin gozar. PDF descargado desde el botón de impresión del portal. Remuneraciones y aportes del período ya pagados según conciliación ficticia; sin deducciones ni otros haberes pendientes. Se conservan el PDF original y capturas de datos/resultados; las cifras no se calculan en la aplicación.')
    return r


def pdf_evidencia(area):
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from xml.sax.saxutils import escape
    textos={
     'jefatura':'Informe final de labores y acta de entrega: proyectos y archivos transferidos al responsable. Sin subordinados. Sin pendientes de gestión en este supuesto.',
     'tecnologia':'Inventario DEMO-PORTATIL-001, cargador y ratón entregados. Correo mateo.demo@example.invalid, cuenta ofimática, nube y VPN cerrados o transferidos el 17/11/2026. Respaldo de archivos verificado. No se incluyen contraseñas ni claves privadas.',
     'finanzas':'Conciliación ficticia: las remuneraciones y aportes personales hasta la salida ya fueron atendidos; no quedan saldos de nómina, anticipos, préstamos, IR ni otras deducciones. Ambos décimos se acumulan. Los valores de liquidación se consultaron en la calculadora del Ministerio y se respaldan con su PDF original separado. Este documento no es un comprobante bancario real.',
     'talento':'Acuerdo ficticio de terminación entre las partes con salida 17/11/2026. Ingreso 01/10/2026. Kárdex académico: saldo anterior 0; 1,96 días devengados consignados para el caso; ninguna vacación gozada ni ajuste; saldo 1,96 días, coincidente con la consulta al Ministerio. Ambos décimos acumulados. Certificados de trabajo y documentos preparados para entrega. Aviso IESS y registro SUT son actuaciones posteriores pendientes; no se simulan comprobantes oficiales.',
     'bienes':'Acta de entrega recepción ficticia: inventario de herramientas, mobiliario y materiales conciliado. Equipo DEMO-PORTATIL-001 entregado a Tecnología; sin valores por descuentos de activos.',
     'seguridad':'Registro ficticio de devolución de credencial DEMO-ACC-01 y llaves. Accesos físicos dados de baja en la fecha de salida. No se asignaron equipos de protección personal especiales para este puesto administrativo.',
     'salud':'Constancia administrativa ficticia de examen de retiro realizado en la fecha de salida. Documento exclusivamente para simulación académica; no acredita un examen médico real. No contiene diagnósticos, resultados clínicos ni historia clínica.',
     'compras':'En este supuesto privado el trabajador no administra contratos ni procesos de compras públicas y no está obligado por su puesto a presentar declaración patrimonial de fin de gestión. La no aplicación debe justificarse, no presumirse para otros puestos.',
    }
    b=io.BytesIO();styles=getSampleStyleSheet()
    story=[Paragraph('EVIDENCIA FICTICIA PARA DEMOSTRACIÓN APE 4',styles['Title']),Spacer(1,15),Paragraph(escape(area.upper()),styles['Heading1']),
           Paragraph(escape(NOMBRE+' | CI ficticia '+CEDULA+' | salida '+SALIDA),styles['BodyText']),Spacer(1,12),Paragraph(escape(textos[area]),styles['BodyText']),Spacer(1,20),
           Paragraph('SIN VALIDEZ LABORAL, MÉDICA, BANCARIA NI REGISTRO OFICIAL. Los responsables y firmas no se suplantan.',styles['BodyText'])]
    SimpleDocTemplate(b,pagesize=A4).build(story)
    return b.getvalue()


def imagen_dispositivo():
    from PIL import Image, ImageDraw
    im=Image.new('RGB',(1000,500),'#eaf0f5');draw=ImageDraw.Draw(im)
    draw.rounded_rectangle((200,60,800,380),radius=15,fill='#283b50')
    draw.rectangle((225,85,775,345),fill='#bad5e6')
    draw.polygon([(200,380),(800,380),(900,430),(100,430)],fill='#65788b')
    draw.text((245,180),'DISPOSITIVO FICTICIO DEMO-PORTATIL-001',fill='#102b45')
    draw.text((320,460),'SIMULACION ACADEMICA APE 4',fill='#102b45')
    b=io.BytesIO();im.save(b,format='PNG');return b.getvalue()
