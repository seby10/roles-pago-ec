"""Completa la plantilla institucional conservada y produce el Word editable."""
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import json
import shutil
import zipfile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.text.paragraph import Paragraph
from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'entregables_integrador'
BUILD = ROOT / '.test-output/formato-final'
REFERENCE = Path(r'C:\Users\sebas\Downloads\FORMATO DE TRABAJO FINAL.docx')
FINAL = OUT / 'Informe_Integrador_FERIAUTO_Grupo1.docx'
LINEA = 'Software, Tecnologías de la Información y Ciencia de Datos'
URL = 'https://seby10.pythonanywhere.com/'
BUILD.mkdir(parents=True, exist_ok=True)
retained = BUILD / REFERENCE.name
if not retained.exists():
    shutil.copy2(REFERENCE, retained)
assert retained.read_bytes() == REFERENCE.read_bytes()
if FINAL.exists():
    backup = BUILD / ('informe-previo-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.docx')
    shutil.copy2(FINAL, backup)

source = Document(REFERENCE)
doc = Document(REFERENCE)
patterns = [deepcopy(p._p) for p in source.paragraphs]
for element in list(doc._element.body):
    if element.tag != qn('w:sectPr'):
        doc._element.body.remove(element)


def paragraph(text='', pattern=22, bold=None, align=None, after=7, before=0, keep=False):
    element = deepcopy(patterns[pattern])
    for child in list(element):
        if child.tag != qn('w:pPr'):
            element.remove(child)
    doc._element.body.insert(len(doc._element.body) - 1, element)
    p = Paragraph(element, doc._body)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.line_spacing = 1.08
    p.paragraph_format.keep_with_next = keep
    p.paragraph_format.widow_control = True
    if align is not None:
        p.alignment = align
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0, 0, 0)
    if bold is not None:
        run.bold = bold
    return p


def plain_heading(text, pattern=24, before=9):
    p = paragraph(text, pattern=pattern, bold=True, before=before, after=8, keep=True)
    # La fuente usa numeración automática con dos párrafos PP/YY de muestra.
    # Se conserva el aspecto, con el prefijo explícito y sin esos residuos.
    ppr = p._p.get_or_add_pPr()
    for e in list(ppr):
        if e.tag == qn('w:numPr'):
            ppr.remove(e)
    p.paragraph_format.left_indent = Cm(.64)
    p.paragraph_format.first_line_indent = Cm(0)
    outline = OxmlElement('w:outlineLvl')
    outline.set(qn('w:val'), '1')
    ppr.append(outline)
    return p


def subheading(text):
    return plain_heading(text, before=7)


def new_page():
    p = paragraph('', pattern=0, after=0)
    p.paragraph_format.page_break_before = True
    p.paragraph_format.line_spacing = Pt(12)


def metadata(label, value, pattern=7):
    p = paragraph(label + '\t' + value, pattern=pattern, after=12,
                  align=WD_ALIGN_PARAGRAPH.LEFT)
    p.paragraph_format.left_indent = Cm(6.25)
    p.paragraph_format.first_line_indent = Cm(-6.25)
    p.paragraph_format.tab_stops.clear_all()
    p.paragraph_format.tab_stops.add_tab_stop(Cm(6.25))
    if label:
        run = p.runs[0]
        run.text = label + '\t'
        run.bold = True
        value_run = p.add_run(value)
        value_run.font.name = 'Arial'
        value_run.font.size = Pt(10)
    return p


def link(p, text, url):
    rel = p.part.relate_to(url, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', is_external=True)
    h = OxmlElement('w:hyperlink'); h.set(qn('r:id'), rel)
    r = OxmlElement('w:r'); rp = OxmlElement('w:rPr')
    f = OxmlElement('w:rFonts'); f.set(qn('w:ascii'), 'Arial'); f.set(qn('w:hAnsi'), 'Arial'); rp.append(f)
    s = OxmlElement('w:sz'); s.set(qn('w:val'), '20'); rp.append(s)
    c = OxmlElement('w:color'); c.set(qn('w:val'), '174A73'); rp.append(c)
    r.append(rp); t = OxmlElement('w:t'); t.text = text; r.append(t); h.append(r); p._p.append(h)


def table(caption, headers, rows, widths):
    paragraph(caption, after=5, before=4, keep=True)
    t = doc.add_table(rows=1, cols=len(headers))
    t.autofit = False
    for i, width in enumerate(widths):
        t.columns[i].width = Cm(width)
    for j, text in enumerate(headers):
        t.rows[0].cells[j].text = text
    for values in rows:
        cells = t.add_row().cells
        for j, text in enumerate(values):
            cells[j].text = str(text)
    tblpr = t._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for side in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        e = OxmlElement('w:' + side)
        for k, v in [('val', 'single'), ('sz', '4'), ('color', 'D9D9D9')]: e.set(qn('w:' + k), v)
        borders.append(e)
    tblpr.append(borders)
    for i, row in enumerate(t.rows):
        trpr = row._tr.get_or_add_trPr()
        cant = OxmlElement('w:cantSplit'); trpr.append(cant)
        if i == 0:
            repeat = OxmlElement('w:tblHeader'); trpr.append(repeat)
        for j, cell in enumerate(row.cells):
            cell.width = Cm(widths[j])
            cell.vertical_alignment = 1
            tcpr = cell._tc.get_or_add_tcPr()
            margins = OxmlElement('w:tcMar')
            for side, value in [('top','75'),('bottom','75'),('left','100'),('right','100')]:
                e = OxmlElement('w:' + side); e.set(qn('w:w'), value); e.set(qn('w:type'), 'dxa'); margins.append(e)
            tcpr.append(margins)
            if i == 0 or i % 2 == 0:
                shade = OxmlElement('w:shd'); shade.set(qn('w:fill'), 'E8EDF0' if i == 0 else 'F6F7F8'); tcpr.append(shade)
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.05
                for run in p.runs:
                    run.font.name = 'Arial'; run.font.size = Pt(10); run.bold = i == 0
                    run.font.color.rgb = RGBColor(0, 0, 0)
    paragraph('', pattern=0, after=3)
    return t


# PORTADA, con los campos y el orden del documento proporcionado.
paragraph('', pattern=0, after=0)
paragraph('PROYECTO FINAL INTEGRADOR', pattern=1, bold=True,
          align=WD_ALIGN_PARAGRAPH.CENTER, after=17)
paragraph('PORTADA', pattern=3, bold=True, after=12)
paragraph('UNIVERSIDAD TÉCNICA DE AMBATO', pattern=4, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
paragraph('Facultad de Ingeniería en Sistemas, Electrónica e Industrial', pattern=5,
          align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
paragraph('Proyecto Académico de Fin de Semestre: julio a diciembre de 2026', pattern=6,
          align=WD_ALIGN_PARAGRAPH.CENTER, after=24)
metadata('Título:', 'Plataforma integradora de Emprendimiento y Legislación Laboral para FERIAUTO S.A.S.')
metadata('Carrera:', 'Software', 8)
metadata('Unidad de Organización Curricular:', 'PROFESIONAL', 9)
metadata('Línea de Investigación:', LINEA, 10)
metadata('Nivel y Paralelo:', 'Octavo A', 11)
metadata('Alumnos participantes:', 'Constante Naranjo Fabricio Sebastián', 12)
metadata('', 'Conterón Villamarín Britani Jhanina', 13)
metadata('', 'García Fernández Daylé', 13)
metadata('', 'Montero López Pablo Andrés', 13)
metadata('Módulo y Docente:', 'Emprendimiento y Legislación Laboral\nIng. María Francisca Cazorla Logroño, Mg.', 15)
paragraph('Ambato, Ecuador\nNoviembre de 2026', pattern=4,
          align=WD_ALIGN_PARAGRAPH.CENTER, before=18, after=10)
p = paragraph('', align=WD_ALIGN_PARAGRAPH.CENTER, before=6)
link(p, URL, URL)

# 2: apertura del informe en el orden exacto de la plantilla.
new_page()
paragraph('INFORME DEL PROYECTO', pattern=18, bold=True, after=15)
plain_heading('2.1 Título', pattern=21)
paragraph('Plataforma integradora de Emprendimiento y Legislación Laboral para FERIAUTO S.A.S.')
plain_heading('2.2 Objetivos')
paragraph('Objetivo general. Integrar los trabajos y las automatizaciones desarrollados durante el semestre en una plataforma que permita navegar por los cuatro módulos de la asignatura, visualizar sus resultados y consultar las evidencias correspondientes.')
paragraph('Objetivos específicos. Organizar los informes, talleres, archivos de cálculo y recursos audiovisuales según su módulo; relacionar las síntesis con sus documentos de respaldo; conservar los escenarios y períodos de cada entrega; y facilitar la exposición grupal mediante un recorrido común y material de apoyo.')
plain_heading('2.3 Resumen', pattern=27)
paragraph('El proyecto reúne los productos académicos elaborados sobre FERIAUTO durante el semestre en una plataforma de consulta. Se organizaron cuatro módulos: Emprendimiento, Obligaciones tributarias, Remuneraciones y nómina, y Liquidación laboral. La integración conserva 33 documentos y tres carpetas audiovisuales, con una biblioteca que permite buscar y filtrar recursos, consultar páginas y descargar los archivos originales. Los módulos muestran los resultados previamente documentados y mantienen los accesos a las herramientas de nómina y paz y salvo. Se diferencian el estudio económico inicial, el supuesto tributario y el escenario laboral posterior para evitar interpretarlos como una sola operación. El resultado es un dashboard publicado que permite explicar la relación entre la propuesta de negocio, su formalización simulada, la gestión del equipo y el cierre laboral. La actividad integradora se limita a organizar y presentar los trabajos existentes, sin desarrollar nuevos casos, repetir cálculos ni crear nuevas automatizaciones.')
plain_heading('2.4 Palabras clave', pattern=30)
paragraph('Emprendimiento, obligaciones tributarias, nómina, liquidación laboral, integración documental, FERIAUTO.', align=WD_ALIGN_PARAGRAPH.LEFT)
plain_heading('2.5 Introducción', pattern=32)
paragraph('FERIAUTO se planteó como una plataforma móvil para organizar la compraventa de vehículos usados en la feria de Ambato. A partir de esa propuesta, el grupo trabajó el modelo de negocio, el estudio económico, las obligaciones tributarias y las relaciones laborales. Los productos quedaron distribuidos en informes, talleres, hojas de cálculo, videos y herramientas de la plataforma [1]–[4].')
paragraph('El problema de la entrega final era la dispersión de esas evidencias y la dificultad de mostrar sus conexiones durante la defensa. La integración responde a esa necesidad con una navegación común y fuentes consultables. La documentación conserva su condición académica: las simulaciones no acreditan contratos, declaraciones, registros de marca, firmas ni trámites oficiales realizados.')

# 3: materiales y proceso, sin nuevas actividades de cálculo.
new_page()
plain_heading('2.6 Materiales y Metodología', pattern=35)
paragraph('Se utilizó un procedimiento de revisión, clasificación y vinculación de los productos existentes. Las fuentes principales fueron los informes PEA 1, PEA 2 y PEA 3, los trabajos de la APE 4, las hojas de cálculo del semestre, los PDF ministeriales conservados y las carpetas de videos compartidas por el grupo [1]–[6].')
table('Tabla 1. Fuentes principales organizadas en el integrador.',
      ['Módulo', 'Fuentes y evidencias del semestre'], [
          ['Emprendimiento', 'PEA 1, Canvas, perfil estratégico, mercado y operación, Taller 05 y pitch.'],
          ['Obligaciones tributarias', 'PEA 2, RUC simulado, comprobantes, IVA, SENADI y prácticas complementarias.'],
          ['Remuneraciones y nómina', 'PEA 3, organigrama, tabla de remuneraciones, roles y casos judiciales.'],
          ['Liquidación laboral', 'APE 4, resultados ministeriales, paz y salvo, muestras documentales y videos.'],
      ], [4.7, 12.3])
subheading('Revisión y selección de evidencias')
paragraph('Primero se identificaron los entregables consolidados de cada unidad. Después se revisaron las páginas que respaldan las cifras mostradas en el dashboard. Los trabajos de MACASOFT, INDUMETAL y del facturador SRI se clasificaron como prácticas complementarias, de modo que sus operaciones no se atribuyan al consolidado de FERIAUTO. Tampoco se trasladó al resultado del emprendimiento el análisis financiero de otras empresas.')
subheading('Organización y trazabilidad')
paragraph('Cada documento se registró con título, módulo, contexto, procedencia, extensión y número de páginas cuando corresponde. Las copias conservan el contenido de los archivos originales. Las vistas de los PDF facilitan la lectura dentro de la plataforma y la descarga permite consultar el documento completo. Los videos permanecen en sus carpetas originales de Drive, con sus permisos de acceso.')
subheading('Integración funcional')
paragraph('Se incorporaron una portada, cuatro páginas de módulo, una biblioteca y un visor documental sobre la aplicación existente de Flask. Las herramientas previas de empleados, organigrama, escalas, roles y paz y salvo conservaron su funcionamiento. La base de datos y los expedientes operativos se mantuvieron separados de las muestras académicas de consulta pública.')
subheading('Comprobación del recorrido')
paragraph('Se verificaron los enlaces internos, la búsqueda y sus filtros, las vistas por página, las descargas y el arranque del integrador. Las pruebas de integración se realizaron con bases temporales; en la actualización del servidor se comprobó la conservación de los registros existentes y se dejó una copia de respaldo. La revisión documental se centró en mantener resultados, períodos y fuentes, sin producir nuevos valores.')

# 4: resultados de las dos primeras unidades.
new_page()
plain_heading('2.7 Resultados y Discusión', pattern=38)
subheading('2.7.1 Emprendimiento')
paragraph('El primer módulo relaciona el problema de informalidad y desconfianza en la feria de vehículos con la propuesta de centralizar la oferta y verificar información. El Canvas plantea un modelo B2G: el GAD Municipalidad de Ambato sería el cliente institucional y la ciudadanía utilizaría el servicio. La consulta enlaza la idea, el perfil estratégico, el mercado, la operación y el plan empresarial consolidado [1].')
table('Tabla 2. Resultados conservados del estudio económico inicial.', ['Concepto', 'Resultado reportado'], [
    ['Inversión inicial', 'USD 5.150'], ['Costo mensual total', 'USD 2.458'],
    ['Ingresos mensuales', 'USD 3.000'], ['Resultado mensual', 'USD 542'],
    ['Margen y recuperación simple', '18,1 % y 9,5 meses'],
], [9, 8])
paragraph('Fuente: PEA 1, pp. 3 y 14–16 [1]. Son resultados del estudio inicial; la integración no los recalcula.', after=10)
paragraph('El propio plan reconoce que la plantilla económica de USD 3 por 1.000 usuarios y el Canvas B2G gratuito responden a supuestos diferentes. Además, el costo inicial de talento humano no incorpora todos los beneficios laborales. Por ello, el dashboard conserva la etapa del estudio y evita presentar esos datos como equivalentes al escenario posterior de nómina. Las discrepancias del sondeo también permanecen identificadas, sin generar nuevos indicadores a partir de una muestra no conciliada [1].')
subheading('2.7.2 Obligaciones tributarias')
paragraph('El segundo módulo reúne el ejercicio de FERIAUTO S.A.S. para septiembre de 2026, con RUC simulado 1850001234001 y Régimen General. Las facturas, compras, notas de crédito y retenciones del informe permiten seguir el origen de los resultados. Se incluyen la simulación de marca y las prácticas de clase, conservando el contexto de cada empresa [2].')
table('Tabla 3. Resultados de IVA del ejercicio ya elaborado.', ['Concepto', 'USD'], [
    ['IVA generado', '442,50'], ['Crédito por compras', '540,00'],
    ['Retenciones recibidas', '450,00'], ['IVA por pagar', '0,00'],
    ['Crédito para el siguiente período', '547,50'],
], [12, 5])
paragraph('Fuente: PEA 2, pp. 11–12 [2]. Los resultados corresponden únicamente al período académico indicado y no se suman a las prácticas de otras empresas.')

# 5: resultados laborales con escenarios y fuentes separados.
new_page()
subheading('2.7.3 Remuneraciones y nómina')
paragraph('La PEA 3 documenta una estructura de cinco trabajadores para un contrato municipal simulado de USD 4.500 mensuales por desarrollo, mantenimiento y soporte. La plataforma relaciona el organigrama con los cargos y sus remuneraciones, y conserva el historial de roles, los archivos Excel y las pantallas de novedades y beneficios. Las cifras de la tabla corresponden al informe y pueden diferir de un padrón editado posteriormente [3].')
table('Tabla 4. Escenario laboral documentado en la PEA 3.', ['Concepto', 'USD mensuales'], [
    ['Remuneraciones base', '2.650,00'], ['Costo inicial del personal', '3.490,85'],
    ['Otros costos', '530,00'], ['Resultado inicial', '479,15'],
    ['Costo del personal desde el mes 13', '3.711,60'], ['Resultado desde el mes 13', '258,40'],
], [12, 5])
paragraph('Fuente: PEA 3, pp. 3 y 13–14 [3]. Los valores desde el mes 13 incluyen los fondos de reserva previstos en ese trabajo.')
paragraph('La lectura conjunta muestra la evolución de los supuestos del semestre. El ingreso de USD 3.000 de la PEA 1 y el contrato de USD 4.500 de la PEA 3 no representan la misma estructura de costos. Separarlos permite discutir la relación entre el servicio ofrecido y el costo laboral sin sustituir ni rehacer el estudio inicial.')
subheading('2.7.4 Liquidación laboral y paz y salvo')
paragraph('El cuarto módulo conserva el caso ficticio de Mateo Demostración Rivera: ingreso el 1 de octubre de 2026, salida el 17 de noviembre de 2026, sueldo de USD 510 y terminación por acuerdo entre las partes. Los derechos se respaldan en el resultado del simulador del Ministerio obtenido con esos datos hipotéticos, no en una nueva calculadora del integrador [4], [5].')
table('Tabla 5. Resultados ministeriales existentes del caso académico.', ['Rubro', 'USD'], [
    ['Décimo tercero', '66,58'], ['Décimo cuarto', '62,93'], ['Vacaciones', '33,32'],
    ['Indemnizaciones por acuerdo', '0,00'], ['Total aproximado por acuerdo', '162,83'],
    ['Total comparativo por despido intempestivo', '1.692,83'],
], [12, 5])
paragraph('Fuente: PDF ministerial del acuerdo y PDF comparativo [5]. Son supuestos de terminación diferentes y sus totales no deben sumarse.')
paragraph('El flujo previo de paz y salvo organiza ocho áreas y 21 requisitos, de los cuales 19 son previos a la emisión y dos corresponden al seguimiento. La biblioteca permite consultar muestras del certificado, la liquidación administrativa y el resumen para firma. Estas muestras no acreditan firmas, pagos ni registros oficiales completados [4].')

# 6: discusión de integración y conclusiones.
new_page()
subheading('2.7.5 Integración de documentos, herramientas y videos')
paragraph('El resultado funcional es una portada con cuatro módulos, una biblioteca de 33 documentos y accesos a tres carpetas audiovisuales. Cada módulo presenta una síntesis y conduce a las evidencias que la respaldan. El visor permite seleccionar la página y regresar al módulo; los archivos de cálculo y Word mantienen su descarga en el formato original [6].')
paragraph('El elevator pitch y el Canvas complementan la explicación de Emprendimiento. Los casos judiciales se relacionan con el análisis laboral en Nómina y Liquidación. El video del despido ideal se incorpora como reflexión sobre comunicación, empatía y trato humano; no se presenta como el procedimiento legal de despido ni reemplaza las evidencias de terminación. Los videos se consultan en Drive sin modificar sus permisos [6], [7].')
paragraph('La aplicación se encuentra publicada en ', after=0)
p = paragraph('', after=10); link(p, URL, URL)
paragraph('Para la defensa se propone abrir la portada, explicar la idea y un resultado económico, consultar la evidencia del IVA, mostrar el organigrama o un rol ya guardado y cerrar con el resultado ministerial y una muestra de paz y salvo. El informe, la presentación y el guion de exposición están disponibles en la portada. El recorrido utiliza resultados existentes y no exige generar otro rol o preparar un caso nuevo.')
subheading('Discusión de coherencia y alcance')
paragraph('La principal aportación consiste en hacer consultables las relaciones entre los productos del semestre. El plan de negocio da contexto a la actividad; la documentación tributaria organiza el ejercicio de formalización; la nómina muestra la estructura del equipo y su costo; y la liquidación reúne el cierre con respaldo documental. Esa relación es académica y no convierte las simulaciones en operaciones empresariales reales.')
paragraph('La trazabilidad también permite reconocer límites de las fuentes. Los escenarios económicos se mantienen por etapa, las prácticas de otras empresas se identifican como complementarias y las muestras laborales conservan su estado documental. De esta forma, las diferencias entre entregas se explican durante la exposición sin alterarlas para hacerlas coincidir artificialmente.')
plain_heading('2.8 Conclusiones', pattern=41)
paragraph('La plataforma reúne los cuatro módulos requeridos y permite navegar entre contenidos, resultados y evidencias del mismo proyecto académico. La biblioteca y el visor reducen la dispersión de archivos y facilitan demostrar qué trabajo sustenta cada síntesis.')
paragraph('La integración preserva los documentos, los casos y las automatizaciones desarrollados durante el semestre. Los resultados económicos, tributarios y laborales se presentan con su fuente y su supuesto, lo que evita confundir períodos o sumar casos diferentes.')
paragraph('El informe y las diapositivas apoyan una defensa centrada en productos ya elaborados. El grupo puede explicar el recorrido completo de FERIAUTO, utilizar los videos como complemento y mostrar las herramientas existentes sin repetir cálculos ni crear nuevas automatizaciones.')

# 7: referencias IEEE, con fuentes locales y enlaces de consulta verificables.
new_page()
plain_heading('2.9 Referencias bibliográficas', pattern=44)
references = [
    '[1] Grupo 1, “Informe PEA 1 y Plan de Negocios FERIAUTO”, Universidad Técnica de Ambato, Carrera de Software, 2026, pp. 3 y 6–17. Archivo: GuiaAPE1_Grupo01.pdf.',
    '[2] Grupo 1, “Obligaciones tributarias y formalización de FERIAUTO S.A.S.”, Universidad Técnica de Ambato, Carrera de Software, 2026, pp. 6–12 y 16–19. Archivo: Informe_PEA2_ObligacionesTributarias_GRUPO1.pdf.',
    '[3] Grupo 1, “Contratación laboral, deberes y derechos del empleador y del trabajador: FERIAUTO”, Universidad Técnica de Ambato, 2026, pp. 3 y 13–14. Archivo: Informe_PEA3_ContratacionLaboral_FERIAUTO.pdf.',
    '[4] Grupo 1, “Informe APE 4: despidos, liquidaciones y paz y salvo”, Universidad Técnica de Ambato, 2026. Informe y muestras documentales del expediente ficticio conservados en la biblioteca del proyecto.',
    '[5] Ministerio del Trabajo del Ecuador, “Calculadora de liquidaciones”, resultados aproximados consultados el 17 de noviembre de 2026 para el supuesto académico por acuerdo entre las partes y su comparación por despido intempestivo. PDF originales conservados como evidencias del caso.',
    '[6] Grupo 1, “FERIAUTO: plataforma integradora de Emprendimiento y Legislación Laboral”, 2026. [En línea]. Disponible en: https://seby10.pythonanywhere.com/. [Consultado: 21-nov-2026].',
    '[7] Grupo 1, “Recursos audiovisuales del curso: elevator pitch y Canvas, casos judiciales y despido ideal”, carpetas de Google Drive compartidas para la integración, 2026.',
]
for ref in references:
    p = paragraph(ref, after=13, align=WD_ALIGN_PARAGRAPH.LEFT)
    p.paragraph_format.left_indent = Cm(1.15)
    p.paragraph_format.first_line_indent = Cm(-.51)
subheading('Acceso a las fuentes del proyecto')
for text, target in [
    ('Biblioteca del semestre', URL + 'biblioteca'),
    ('Elevator pitch y Canvas', 'https://drive.google.com/drive/folders/1S1RCbYb9AZY72_6UmDs2rxGvg-UPEIoo?usp=drive_link'),
    ('Casos judiciales', 'https://drive.google.com/drive/folders/1LFZ4ZDc7JSGp34sxZMzw_23p3q9AyFas?usp=drive_link'),
    ('El despido ideal', 'https://drive.google.com/drive/folders/17RSFaqTzWO9NHoiQlu3Uh48nbLa4KJ32?usp=drive_link'),
]:
    p = paragraph('', after=10); link(p, text, target)
paragraph('Los informes y talleres completos se consultan como evidencias externas desde la plataforma; no se incorporan como páginas adicionales de este informe.', before=7)

# 8: evidencias auténticas y esquema editable, como solicita la plantilla.
new_page()
plain_heading('2.10 Fotografías y gráficos', pattern=47)
paragraph('Las siguientes figuras muestran la plataforma publicada y el criterio de organización de sus módulos. La captura corresponde al funcionamiento real del proyecto; el esquema sintetiza la relación entre los trabajos del semestre.')
proof = ROOT / '.test-output/plataforma-publicada.jpg'
if proof.is_file():
    p = paragraph('', pattern=0, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
    p.add_run().add_picture(str(proof), width=Cm(17))
    paragraph('Figura 1. Portada de FERIAUTO publicada con acceso a los cuatro módulos. Fuente: captura de la plataforma del grupo.', after=13)
table('Figura 2. Relación entre los módulos y las evidencias integradas.',
      ['Etapa del recorrido', 'Relación con el proyecto'], [
          ['1. Emprendimiento', 'Define la propuesta, los usuarios, el modelo y el estudio económico inicial.'],
          ['2. Obligaciones tributarias', 'Organiza la formalización simulada y los documentos de las operaciones trabajadas.'],
          ['3. Remuneraciones y nómina', 'Relaciona cargos, remuneraciones, beneficios y roles con el costo del equipo.'],
          ['4. Liquidación laboral', 'Conserva la causal, los resultados ministeriales y las evidencias del cierre.'],
      ], [5.7, 11.3])
paragraph('Fuente: organización de los trabajos PEA 1, PEA 2, PEA 3 y APE 4. Elaboración del grupo a partir de las evidencias existentes.', after=12)
paragraph('En la exposición, las carpetas audiovisuales y los documentos se abren desde su módulo. La navegación permite regresar al recorrido sin perder la relación entre el resultado mostrado y su fuente.')

doc.core_properties.title = 'Plataforma integradora de Emprendimiento y Legislación Laboral para FERIAUTO S.A.S.'
doc.core_properties.author = 'Grupo 1, Carrera de Software, Universidad Técnica de Ambato'
doc.core_properties.subject = 'Proyecto Académico de Fin de Semestre, julio a diciembre de 2026'
doc.core_properties.comments = ''

# Completar únicamente el texto de los controles institucionales, sin reconstruirlos.
header = doc.sections[0].header._element
for sdt in header.xpath('.//w:sdt'):
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    tags = sdt.xpath('./w:sdtPr/w:tag/@w:val', namespaces=ns)
    value = {'CARRERA': 'SOFTWARE', 'correo': 'carrera.sistemas@uta.edu.ec'}.get(tags[0] if tags else '')
    if value:
        texts = sdt.xpath('./w:sdtContent//w:t', namespaces=ns)
        assert len(texts) == 1, 'El control requiere inspección antes de editarlo'
        texts[0].text = value
        # El control de correo conserva el estilo gris y grande del placeholder
        # hasta que se selecciona un valor en Word. Aplicar su tamaño de origen
        # (6 pt en sdtPr) evita que el valor real choque con el logotipo.
        if tags[0] == 'correo':
            for run in sdt.xpath('./w:sdtContent//w:r', namespaces=ns):
                props = run.find(qn('w:rPr'))
                if props is None:
                    props = OxmlElement('w:rPr'); run.insert(0, props)
                for name in ['rStyle', 'sz', 'szCs', 'color']:
                    for prop in props.findall(qn('w:' + name)): props.remove(prop)
                for name, val in [('sz', '12'), ('szCs', '12'), ('color', '000000')]:
                    prop = OxmlElement('w:' + name); prop.set(qn('w:val'), val); props.append(prop)
        for placeholder in sdt.xpath('./w:sdtPr/w:showingPlcHdr', namespaces=ns):
            placeholder.getparent().remove(placeholder)
        for color in sdt.xpath('./w:sdtContent//w:rPr/w:color', namespaces=ns):
            color.set(qn('w:val'), '000000')
            for attribute in list(color.attrib):
                if attribute != qn('w:val'): del color.attrib[attribute]

draft = BytesIO(); doc.save(draft)
edited = zipfile.ZipFile(BytesIO(draft.getvalue()))
original = zipfile.ZipFile(REFERENCE)
editable = {'word/document.xml', 'word/header1.xml', 'word/_rels/document.xml.rels',
            '[Content_Types].xml', 'word/settings.xml', 'docProps/core.xml'}
with zipfile.ZipFile(FINAL, 'w', compression=zipfile.ZIP_DEFLATED) as target:
    for name in edited.namelist():
        data = original.read(name) if name in original.namelist() and name not in editable else edited.read(name)
        target.writestr(name, data)

final_zip = zipfile.ZipFile(FINAL)
preserved = [n for n in original.namelist() if n not in editable]
assert all(original.read(n) == final_zip.read(n) for n in preserved)
assert REFERENCE.read_bytes() == retained.read_bytes()
evidence = {
    'reference': str(REFERENCE), 'reference_sha256': sha256(REFERENCE.read_bytes()).hexdigest(),
    'template_pages': 1, 'section_count': len(doc.sections), 'output': str(FINAL),
    'preserved_parts': {n: sha256(original.read(n)).hexdigest() for n in preserved},
    'editable_parts': sorted(editable), 'assigned_research_line': LINEA,
    'render_method': 'Word native ExportAsFixedFormat, macros disabled; Poppler PNG',
}
(BUILD / 'evidencia-plantilla.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
print(FINAL)
print('Partes de la plantilla preservadas:', len(preserved))
