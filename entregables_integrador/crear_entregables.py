"""Construye los entregables del integrador con resultados ya documentados."""
from pathlib import Path
import os
import subprocess
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader
from pptx import Presentation
from pptx.util import Inches

OUT = Path(__file__).resolve().parent
RUNTIME = Path(r'C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1118-904-0_26.1118.904.0_x64__3k8sg7r9htsxt\dependencies')
POPPLER = RUNTIME / 'native/poppler/Library/bin/pdftoppm.exe'
BASE_URL = os.environ.get('INTEGRADOR_URL', 'https://seby10.pythonanywhere.com').rstrip('/')
PITCH_URL = 'https://drive.google.com/drive/folders/1S1RCbYb9AZY72_6UmDs2rxGvg-UPEIoo'
CASOS_URL = 'https://drive.google.com/drive/folders/1LFZ4ZDc7JSGp34sxZMzw_23p3q9AyFas'
DESPIDO_URL = 'https://drive.google.com/drive/folders/17RSFaqTzWO9NHoiQlu3Uh48nbLa4KJ32'
for name, file in [('TNR','times.ttf'),('TNR-Bold','timesbd.ttf'),('TNR-Italic','timesi.ttf'),('Arial','arial.ttf'),('Arial-Bold','arialbd.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(Path('C:/Windows/Fonts') / file)))
pdfmetrics.registerFontFamily('TNR', normal='TNR', bold='TNR-Bold', italic='TNR-Italic', boldItalic='TNR-Bold')
pdfmetrics.registerFontFamily('Arial', normal='Arial', bold='Arial-Bold', italic='Arial', boldItalic='Arial-Bold')

INK = colors.HexColor('#152b3b')
GREEN = colors.HexColor('#22674d')
GRAY = colors.HexColor('#5b6267')
PALE = colors.HexColor('#edf2ef')
styles = {
    'body': ParagraphStyle('body', fontName='TNR', fontSize=11, leading=14.8, spaceAfter=9, alignment=TA_JUSTIFY),
    'h1': ParagraphStyle('h1', fontName='TNR-Bold', fontSize=14, leading=17, spaceAfter=15, textColor=colors.black),
    'h2': ParagraphStyle('h2', fontName='TNR-Bold', fontSize=11.5, leading=14.5, spaceBefore=8, spaceAfter=7, textColor=colors.black),
    'small': ParagraphStyle('small', fontName='TNR', fontSize=9.2, leading=12, spaceAfter=7),
    'cell': ParagraphStyle('cell', fontName='TNR', fontSize=10, leading=13),
    'head': ParagraphStyle('head', fontName='TNR-Bold', fontSize=10, leading=13, textColor=colors.white),
    'cover': ParagraphStyle('cover', fontName='TNR-Bold', fontSize=16, leading=20, alignment=TA_CENTER, spaceAfter=15),
    'center': ParagraphStyle('center', fontName='TNR', fontSize=11, leading=15, alignment=TA_CENTER, spaceAfter=10),
}
story = []
def p(text, kind='body'):
    return Paragraph(text, styles[kind])
def add(text, kind='body'):
    story.append(p(text, kind))
def heading(text): add(text, 'h1')
def sub(text): add(text, 'h2')
def table(rows, widths):
    captions = {
        'Actividad': 'Tabla 1. Actividades y criterios de integración.',
        'Resultado previo del Taller 05': 'Tabla 2. Resultados económicos del escenario inicial.',
        'IVA del ejercicio septiembre de 2026': 'Tabla 3. Resultados tributarios conservados del informe PEA 2.',
        'Escenario PEA 3 ya documentado': 'Tabla 4. Escenario histórico de costo laboral y sostenibilidad.',
        'Rubros del PDF ministerial existente': 'Tabla 5. Resultados ministeriales de los supuestos ya trabajados.',
        'Destino': 'Tabla 6. Accesos de la plataforma integrada.',
    }
    if rows[0][0] in captions:
        story.append(p(captions[rows[0][0]], 'small'))
    data=[[p(str(c), 'head' if i==0 else 'cell') for c in row] for i,row in enumerate(rows)]
    t=Table(data, colWidths=widths, hAlign='LEFT', repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),INK),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f2f4f5')]),('GRID',(0,0),(-1,-1),.5,colors.HexColor('#D9D9D9')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    story.extend([t,Spacer(1,12)])
def new(): story.append(PageBreak())
W,H=A4
CW=W-170
def header(c,doc):
    c.saveState()
    c.drawImage(str(OUT/'image2.png'),42,H-78,48,48,preserveAspectRatio=True,mask='auto')
    c.drawImage(str(OUT/'image1.png'),W-90,H-78,48,48,preserveAspectRatio=True,mask='auto')
    c.setFont('TNR-Bold',9)
    for text,y in [('UNIVERSIDAD TÉCNICA DE AMBATO',H-35),('FACULTAD DE INGENIERÍA EN SISTEMAS ELECTRÓNICA E INDUSTRIAL',H-48),('CARRERA DE SOFTWARE',H-61),('CICLO ACADÉMICO JULIO A DICIEMBRE 2026',H-74)]:
        c.drawCentredString(W/2,y,text)
    c.setFont('TNR',9)
    c.drawString(85,30,'FERIAUTO S.A.S. · Proyecto final integrador · Grupo 1')
    c.drawRightString(W-85,30,str(doc.page))
    c.restoreState()

# 1 Portada institucional
story.append(Spacer(1,30))
add('INFORME DE GUÍA PRÁCTICA','cover')
add('PROYECTO FINAL INTEGRADOR','cover')
add('Plataforma de Emprendimiento y Legislación Laboral<br/>FERIAUTO S.A.S.','center')
story.append(Spacer(1,25))
table([
    ['Dato académico','Información'],
    ['Tema','Integración de los trabajos y automatizaciones desarrollados durante el semestre'],
    ['Unidad de Organización Curricular','PROFESIONAL'],
    ['Nivel y paralelo','Octavo A'],
    ['Modalidad','Grupal'],
    ['Alumnos participantes','Constante Naranjo Fabricio Sebastián<br/>Conterón Villamarín Britani Jhanina<br/>García Fernández Daylé<br/>Montero López Pablo Andrés'],
    ['Asignatura','Emprendimiento y Legislación Laboral'],
    ['Docente','Ing. María Francisca Cazorla Logroño, Mg.'],
    ['Ciclo académico','Julio a diciembre de 2026'],
],[145,CW-145])
story.append(Spacer(1,18))
add('Ambato, Ecuador<br/>Noviembre de 2026','center')

# 2 Objetivos y proceso
new();heading('1 Objetivos y organización del trabajo')
add('La plataforma reúne los productos de FERIAUTO en cuatro módulos: emprendimiento, obligaciones tributarias, remuneraciones y nómina, y liquidación laboral. Permite consultar el proceso desde la idea de negocio hasta la desvinculación de un trabajador, con los documentos de cada etapa.')
sub('Objetivo general')
add('Integrar los trabajos y automatizaciones desarrollados durante el semestre en una plataforma que reúna los principales contenidos de la asignatura y facilite su consulta y exposición grupal.')
sub('Objetivos específicos')
add('1. Clasificar los informes, talleres, hojas de cálculo y evidencias por módulo y procedencia.<br/>2. Relacionar los resultados económicos, tributarios y laborales con sus documentos originales.<br/>3. Facilitar una navegación común que conecte la consulta documental con las herramientas laborales existentes.')
sub('Modalidad y alcance')
add('Trabajo grupal de integración. Se organizaron los productos ya elaborados; se conservaron los casos, cálculos y automatizaciones del semestre. Los supuestos tributarios, societarios y laborales se presentan como ejercicios académicos. La integración no acredita trámites reales ni modifica los informes históricos.')
sub('Instrucciones, recursos y actividades')
add('La consigna exige cuatro módulos navegables, resultados y documentos. Se utilizaron los informes PEA 1 y PEA 2, talleres y materiales de unidad, productos de PEA 3 y APE 4, hojas Excel y la plataforma Flask y SQLite existente. La biblioteca concentra las evidencias con su identificación de origen.')
table([['Actividad','Criterio de organización'],['Inventario y lectura','Distinguir informes consolidados, trabajos complementarios y contenidos de clase.'],['Síntesis de resultados','Transcribir resultados documentados con fuente, página, período y contexto.'],['Integración','Reunir cuatro módulos, accesos a herramientas existentes y biblioteca.'],['Revisión','Comprobar navegación, documentos, coherencia de escenarios y exposición.']],[120,CW-120])

#3 Emprendimiento
new();heading('2 Resultados del módulo de emprendimiento')
add('FERIAUTO propone una plataforma móvil o PWA para la feria de vehículos usados de Ambato. Atiende la informalidad y la falta de información verificable mediante perfiles, validación de vehículos y contacto entre compradores y vendedores. El modelo B2G distingue al GAD Municipalidad de Ambato como cliente institucional y a los ciudadanos como usuarios del servicio [1, pp. 6–9].')
sub('Productos integrados')
add('Se reúnen la identificación del problema y la oportunidad, el Business Model Canvas, el perfil estratégico, el estudio de mercado y operación, el estudio económico y el informe con el plan de negocios. El recorrido conecta la propuesta de valor con los recursos, actividades, costos e ingresos, en lugar de presentar archivos aislados.')
add(f'El <link href="{PITCH_URL}" color="#174a73">recurso audiovisual de elevator pitch y Canvas</link> del grupo se incorpora como evidencia complementaria de la comunicación del modelo de negocio. Su carpeta se abre desde el módulo y la biblioteca; los videos se consultan en Drive.')
table([['Resultado previo del Taller 05','Valor documentado'],['Inversión inicial','USD 5.150,00'],['Costos fijos mensuales','USD 430,00'],['Costos variables mensuales','USD 100,00'],['Talento humano mensual','USD 1.928,00'],['Costo mensual total','USD 2.458,00'],['Ingresos mensuales','USD 3.000,00'],['Resultado mensual y margen','USD 542,00 · 18,1 %'],['Recuperación simple','9,5 meses']],[260,CW-260])
add('Fuente: informe PEA 1, pp. 3 y 15; valores transcritos del trabajo existente [1].','small')
sub('Lectura de los escenarios')
add('El informe original reconoce la diferencia entre el modelo B2G gratuito para el ciudadano y la estimación inicial de USD 3 por 1.000 usuarios. También señala que el talento humano de ese taller no incorpora todos los beneficios laborales [1, p. 16]. El dashboard conserva este escenario como antecedente y lo distingue del escenario de PEA 3, con un contrato municipal simulado de USD 4.500 mensuales y costos laborales completos [3, pp. 3 y 13].')

#4 Tributarias
new();heading('3 Resultados del módulo de obligaciones tributarias')
add('El módulo utiliza el informe consolidado de FERIAUTO como eje: RUC simulado, actividades económicas, régimen seleccionado en el ejercicio, comprobantes y declaración del IVA de septiembre de 2026. Los trabajos de otras empresas permanecen identificados como prácticas complementarias; sus operaciones no se atribuyen a FERIAUTO [2].')
sub('Identificación y respaldo documental')
add('El RUC académico es 1850001234001. El informe registra FERIAUTO S.A.S., inicio de actividades el 1 de septiembre de 2026 y actividad principal CIIU J62010101. Las actividades adicionales de software a medida y hospedaje de datos acompañan el modelo tecnológico. La selección de Régimen General se consulta como parte del ejercicio entregado [2, pp. 6–7].')
add('Se enlazan las facturas, notas de crédito y débito, guía de remisión y comprobantes de retención ya elaborados. Una operación de servicios al GAD y la adquisición de cuatro computadoras permiten seguir la relación entre documento y resultado del período [2, pp. 8–11].')
table([['IVA del ejercicio septiembre de 2026','USD'],['Impuesto generado en ventas','442,50'],['Crédito por adquisiciones','540,00'],['Retenciones de IVA recibidas','450,00'],['Impuesto a pagar','0,00'],['Crédito tributario para el próximo período','547,50']],[300,CW-300])
add('Fuente: informe PEA 2, pp. 11–12. Se muestran resultados previos, sin recalcularlos [2].','small')
sub('Formalización y materiales de consulta')
add('El módulo también vincula el trabajo de registro de marca FERIAUTO y los documentos de clase sobre RUC, comprobantes e importación de tecnología. Las tasas, condiciones y formularios del informe corresponden a la simulación elaborada durante el semestre; su integración no constituye una actualización normativa ni una declaración ante el SRI.')

#5 Nomina
new();heading('4 Resultados del módulo de remuneraciones y nómina')
add('Se conserva la herramienta desarrollada en PEA 3: empleados, organigrama, escalas salariales, parámetros, roles consolidados e individuales y exportación a Excel. La estructura de personal y la tabla de remuneraciones utilizan los mismos registros, lo que permite seguir la relación entre cargo, sueldo, beneficios y costo empresarial [3].')
sub('Evidencias y resultados históricos')
add('El informe de PEA 3 documenta cinco trabajadores: cuatro directivos y un programador junior, con una masa salarial de USD 2.650. El caso utiliza un contrato B2G simulado de USD 4.500 al mes, distinto de la estimación inicial de emprendimiento. La plataforma conserva los roles históricos con los parámetros de su generación [3, pp. 3–4 y 14].')
table([['Escenario PEA 3 ya documentado','USD mensuales'],['Ingreso del contrato municipal simulado','4.500,00'],['Costo del personal al inicio','3.490,85'],['Otros costos','530,00'],['Resultado mensual al inicio','479,15'],['Costo del personal desde el mes 13','3.711,60'],['Resultado desde el mes 13','258,40']],[300,CW-300])
add('Fuente: informe PEA 3 de 22 páginas, Tabla 12, p. 13 [3]. El resumen muestra ese escenario histórico y no sustituye las cifras de los registros actuales.','small')
sub('Uso dentro del integrador')
add('Desde el módulo se abre el resumen laboral, el organigrama, el historial de roles y la documentación académica. El lector puede consultar los resultados y descargar los archivos ya disponibles. La edición y generación de roles pertenecen a la automatización previa; la integración añade organización y accesos sin crear otro motor de cálculo.')
add(f'Los contenidos incluyen sueldos, horas extra, aportes, descuentos y beneficios sociales. Los informes y hojas Excel conservan los procedimientos trabajados. La carpeta de <link href="{CASOS_URL}" color="#174a73">casos judiciales del grupo</link> se vincula a nómina y liquidación como recurso audiovisual complementario, con acceso desde ambos módulos y la biblioteca.')

#6 Liquidacion
new();heading('5 Resultados del módulo de liquidación laboral')
add('Se integra el expediente de paz y salvo de APE 4 junto con las evidencias de terminación laboral, los resultados ministeriales y los documentos de salida ya elaborados. La herramienta existente organiza ocho áreas, 21 requisitos y una revisión documental antes de emitir los documentos; 19 requisitos corresponden a controles previos y dos al seguimiento posterior [4].')
sub('Caso académico conservado')
add('El caso ficticio de Mateo Demostración Rivera contempla ingreso el 1 de octubre y salida el 17 de noviembre de 2026, remuneración de USD 510, región Sierra, décimos acumulados y terminación por acuerdo entre las partes. Se conservan los resultados del simulador del Ministerio obtenidos el 17 de noviembre de 2026; la integración no crea otra liquidación ni recalcula derechos [4], [5].')
table([['Rubros del PDF ministerial existente','USD'],['Décimo tercero','66,58'],['Décimo cuarto','62,93'],['Vacaciones','33,32'],['Indemnizaciones','0,00'],['Total aproximado por acuerdo','162,83'],['Total del caso comparativo por despido','1.692,83']],[300,CW-300])
add('Fuente: PDF ministerial del acuerdo y PDF comparativo por despido. Son resultados aproximados de un supuesto académico [5], [6].','small')
sub('Relación entre revisión y documentos')
add('El recorrido muestra las formas de terminación estudiadas, el resultado de liquidación conservado, el control de pendientes por área y los productos de salida: certificado de paz y salvo, liquidación administrativa y resumen general para firma. El paz y salvo administrativo no reemplaza los documentos oficiales ni demuestra por sí solo el cumplimiento de los trámites.')
add(f'Las muestras corresponden a un caso ficticio; las firmas y trámites mantienen sus propios estados. Se enlazan los <link href="{CASOS_URL}" color="#174a73">casos judiciales</link> y el video de <link href="{DESPIDO_URL}" color="#174a73">despido ideal</link> del grupo. Este último se identifica como reflexión sobre trato humano y comunicación, no como procedimiento legal de terminación.')

#7 Navegacion
new();heading('6 Integración y navegación de la plataforma')
add('La portada presenta los cuatro módulos en el mismo orden de la consigna. Cada módulo contiene una síntesis, resultados con su fuente y enlaces a evidencias. La biblioteca permite buscar documentos y consultarlos sin abandonar la estructura del integrador. Las herramientas de nómina y paz y salvo mantienen sus recorridos anteriores.')
table([['Destino','Ruta de navegación'],['Inicio integrador','/'],['Emprendimiento','/modulos/emprendimiento'],['Obligaciones tributarias','/modulos/tributarias'],['Remuneraciones y nómina','/modulos/nomina'],['Liquidación laboral','/modulos/liquidacion'],['Biblioteca de evidencias','/biblioteca'],['Resumen de la herramienta laboral','/nomina/resumen']],[190,CW-190])
sub('Acceso y recorrido de demostración')
add(f'Acceso principal a la plataforma: <link href="{BASE_URL}/" color="#174a73">{BASE_URL}/</link>. Como respaldo, la copia local se abre en <link href="http://127.0.0.1:5050" color="#174a73">http://127.0.0.1:5050</link> al ejecutar la aplicación. Los tres recursos audiovisuales disponen de tarjetas en el inicio y sus módulos y pueden localizarse en la biblioteca. Los enlaces abren las carpetas originales de Drive, sin duplicar archivos ni modificar sus permisos.')
add('Para la defensa se propone abrir la portada, explicar el modelo de negocio, mostrar un resultado económico y su fuente, consultar el IVA documentado, abrir el organigrama o un rol existente y cerrar con el resultado ministerial y las evidencias de paz y salvo. La exposición se centra en productos ya realizados.')
sub('Criterios de coherencia')
add('La integración distingue las etapas económicas y los períodos; identifica los documentos complementarios de otros casos; conserva los originales; y permite volver del visor a la biblioteca o al módulo. Esta organización evita confundir el resultado inicial de USD 542 con el escenario laboral posterior o mezclar ejercicios tributarios de distintas empresas.')

#8 Cierre
new();heading('7 Conclusiones y recomendaciones')
add('Los cuatro módulos permiten reconstruir el proceso de FERIAUTO con documentos verificables: propuesta de negocio y viabilidad inicial, formalización tributaria simulada, estructura de personal y remuneraciones, y cierre de la relación laboral. La plataforma convierte esos productos en un recorrido de consulta y defensa grupal.')
add('La conservación de fuentes y escenarios da sentido a las diferencias entre entregas. El resultado económico del Taller 05 y el presupuesto de PEA 3 corresponden a supuestos distintos; la lectura conjunta explica la evolución del proyecto sin reemplazar los trabajos anteriores.')
add('Se recomienda utilizar los documentos consolidados como evidencias principales, abrir los archivos antes de la exposición y actualizar la versión publicada desde la misma copia revisada. Durante la defensa, conviene mostrar resultados existentes y su respaldo documental. Los datos del ejercicio y las muestras de firma deben conservar su identificación académica.')
sub('Habilidades blandas y responsabilidades')
add('El trabajo articula la organización del equipo, la comunicación de resultados, el pensamiento crítico ante diferencias entre fuentes y la responsabilidad al presentar simulaciones y estados documentales. La presentación de apoyo incluye notas para distribuir la explicación de los cuatro módulos entre los integrantes.')
sub('Referencias bibliográficas')
refs=[
    '[1] Grupo 1, “Informe PEA 1 y Plan de Negocios FERIAUTO”, GuiaAPE1_Grupo01.pdf, Universidad Técnica de Ambato, 2026, pp. 3, 6–9 y 15–17.',
    '[2] Grupo 1, “Obligaciones tributarias y formalización de FERIAUTO S.A.S.”, Informe_PEA2_ObligacionesTributarias_GRUPO1.pdf, Universidad Técnica de Ambato, 2026, pp. 6–12 y 18–19.',
    '[3] Grupo 1, “Contratación laboral, deberes y derechos”, Informe_PEA3_ContratacionLaboral_FERIAUTO.pdf, Universidad Técnica de Ambato, 2026, pp. 3–4 y 13–14.',
    '[4] Grupo 1, “Paz y salvo y liquidación laboral”, entregables y aplicación APE 4 de FERIAUTO, 2026.',
    '[5] Ministerio del Trabajo, “Resultado del simulador de liquidaciones”, caso ficticio por acuerdo, PDF conservado, 17 nov. 2026. [En línea]. Disponible: https://calculadoras.trabajo.gob.ec/liquidaciones',
    '[6] Ministerio del Trabajo, “Resultado del simulador de liquidaciones”, comparación por despido intempestivo, PDF conservado, 17 nov. 2026.',
]
for r in refs:add(escape(r),'small')
sub('Anexos y evidencias')
add('Los informes originales, talleres, hojas de cálculo y respaldos se consultan en la biblioteca de la plataforma y desde cada módulo. Se mantienen fuera de este informe para facilitar su consulta y respetar el límite de páginas.','small')
REPORT=OUT/'Informe_Integrador_FERIAUTO_Grupo1.pdf'
SimpleDocTemplate(str(REPORT),pagesize=A4,rightMargin=85,leftMargin=85,topMargin=108,bottomMargin=51,title='Proyecto final integrador FERIAUTO Grupo 1',author='Grupo 1 UTA FISEI').build(story,onFirstPage=header,onLaterPages=header)
assert len(PdfReader(REPORT).pages)<=10

# Presentación 16:9: fuentes amplias y una sola idea por lámina.
slides=[
('FERIAUTO','Proyecto final integrador','Emprendimiento y Legislación Laboral\nGrupo 1 · Octavo A · UTA FISEI\nJulio a diciembre de 2026','Abrir con la portada del dashboard. Presentar al grupo y el propósito: reunir los trabajos del semestre, sin nuevos casos ni cálculos.'),
('01','Un recorrido de cuatro módulos','Emprendimiento → Obligaciones tributarias\nRemuneraciones y nómina → Liquidación laboral\nCada resultado conduce a su documento de respaldo.','Sebastián: mostrar la portada. Explicar que la biblioteca conecta informes y talleres con las herramientas que ya existían. Tiempo sugerido: 45 segundos.'),
('02','Emprendimiento','FERIAUTO digitaliza la feria de vehículos de Ambato.\nModelo B2G: GAD como cliente, ciudadanía como usuaria.\nEvidencias: Canvas, plan y video de elevator pitch.','Sebastián: abrir módulo Emprendimiento y el informe PEA 1. Fuente principal: GuiaAPE1_Grupo01.pdf pp. 6–9. Mostrar el acceso a la carpeta del elevator pitch y Canvas; no es necesario reproducir todo el video. No presentar la encuesta como muestra representativa.'),
('03','Resultados económicos en su contexto','Taller 05: inversión USD 5.150 · resultado USD 542/mes.\nIngreso inicial USD 3.000 · costo USD 2.458.\nPEA 3: contrato simulado USD 4.500/mes.','Jhanina: explicar que se muestran etapas diferentes. PEA 1 pp. 15–16 reconoce diferencia entre B2G y estimación de USD 3 por usuario. No comparar márgenes como si fueran el mismo supuesto.'),
('04','Obligaciones tributarias','RUC simulado: 1850001234001 · FERIAUTO S.A.S.\nSeptiembre 2026: IVA a pagar USD 0,00.\nCrédito documentado para siguiente período: USD 547,50.','Jhanina: abrir informe PEA 2 pp. 11–12. Mencionar IVA generado 442,50, compras 540 y retenciones 450. Son resultados del ejercicio existente, no actualización de reglas tributarias. Mostrar un comprobante del mismo informe.'),
('05','Remuneraciones y nómina','Organigrama, cargos, sueldos y beneficios conectados.\nRoles y Excel, con acceso al video de casos judiciales.\nPEA 3: cinco trabajadores y costo inicial USD 3.490,85.','Daylé: abrir módulo Nómina, organigrama y un rol que ya esté guardado. Explicar el costo laboral en el escenario histórico PEA 3 y mostrar el enlace compartido de casos judiciales, también presente en Liquidación. No generar nuevos roles para la defensa del integrador.'),
('06','Liquidación laboral y paz y salvo','Caso por acuerdo · resultado aproximado USD 162,83.\nOcho áreas · revisión documental · documentos para firma.\nVideo del despido ideal: reflexión sobre trato humano.','Pablo: abrir módulo Liquidación y evidencia ministerial. Mostrar una muestra de certificado, liquidación o resumen. Explicar que 21 requisitos incluyen 19 previos y dos de seguimiento. El video del despido ideal trata el trato humano y la comunicación: no presentarlo como procedimiento legal. Mostrar también el acceso a casos judiciales. No afirmar que hay firmas o registros oficiales completados.'),
('07','Demostración de la integración','1. Abrir un módulo y localizar su resultado.\n2. Consultar el documento o recurso audiovisual de respaldo.\n3. Ir a la herramienta laboral y volver a la biblioteca.','Pablo: realizar recorrido breve sobre los archivos existentes. Acceso principal: '+BASE_URL+'/. Respaldo local: http://127.0.0.1:5050. Demostrar las tarjetas de Drive y la búsqueda en biblioteca, conservando el archivo y sus permisos en origen.'),
('08','Qué aporta el integrador','Cuatro módulos con navegación común.\nResultados conservados con etapa, período y fuente.\nDocumentos y automatizaciones del semestre en un lugar.','Cierre grupal: la integración facilita comprender y defender el trabajo del semestre. Enfatizar trazabilidad y organización. Dejar portada abierta para preguntas. Referencias: informes PEA 1, PEA 2, PEA 3 y expediente APE 4.'),
]
SW,SH=960,540
PRES=OUT/'Presentacion_Integrador_FERIAUTO_Grupo1.pdf'
c=canvas.Canvas(str(PRES),pagesize=(SW,SH))
c.setTitle('Presentación del proyecto final integrador FERIAUTO')
for idx,(k,title,body,notes) in enumerate(slides):
    c.setFillColor(colors.HexColor('#f6f5f1'));c.rect(0,0,SW,SH,fill=1,stroke=0)
    c.setFillColor(INK);c.rect(0,0,18,SH,fill=1,stroke=0)
    c.setFont('Arial-Bold',13);c.setFillColor(GREEN);c.drawString(64,479,'FERIAUTO  /  '+('GRUPO 1' if idx==0 else 'PROYECTO INTEGRADOR  /  '+k))
    pp=Paragraph(escape(title),ParagraphStyle('st',fontName='Arial-Bold',fontSize=34,leading=40,textColor=INK))
    _,ht=pp.wrap(820,100);pp.drawOn(c,64,425-ht)
    y=310
    for line in body.split('\n'):
        pp=Paragraph(escape(line),ParagraphStyle('sb',fontName='Arial',fontSize=23 if idx else 25,leading=32,textColor=INK))
        _,ht=pp.wrap(800,200);pp.drawOn(c,64,y-ht);y-=ht+24
    c.setFillColor(GRAY);c.setFont('Arial',10)
    c.drawString(64,39,'UTA · FISEI · Software · Emprendimiento y Legislación Laboral')
    c.drawRightString(900,39,f'{idx+1:02d} / {len(slides):02d}')
    c.showPage()
c.save()
QA=OUT/'revision';QA.mkdir(exist_ok=True)
subprocess.run([str(POPPLER),'-png','-r','110',str(REPORT),str(QA/'informe')],check=True,capture_output=True)
subprocess.run([str(POPPLER),'-png','-r','120',str(PRES),str(QA/'lamina')],check=True,capture_output=True)
prs=Presentation();prs.slide_width=Inches(13.333333);prs.slide_height=Inches(7.5)
for idx,s in enumerate(slides):
    slide=prs.slides.add_slide(prs.slide_layouts[6])
    slide.shapes.add_picture(str(QA/f'lamina-{idx+1}.png'),0,0,width=prs.slide_width,height=prs.slide_height)
    slide.notes_slide.notes_text_frame.text=s[3]
prs.save(OUT/'Presentacion_Integrador_FERIAUTO_Grupo1.pptx')
guide=['# Guion de exposición del integrador','','Duración orientativa: 7 a 9 minutos. El reparto puede ajustarse por el grupo.','']
for i,s in enumerate(slides):guide.extend([f'## Lámina {i+1} — {s[1]}','',s[3],''])
(OUT/'Guion_Exposicion_Grupo1.md').write_text('\n'.join(guide),encoding='utf-8')
print('Informe:',len(PdfReader(REPORT).pages),'páginas; presentación:',len(slides),'láminas')
