"""Adapta la presentación a la identidad visual nueva de la plataforma (colores y tipografía).

Lee la presentación original (copia de respaldo en respaldo_presentacion_antes_redisenio_v2/),
cambia la paleta y las fuentes sin tocar textos ni geometría, y ajusta el tamaño de un
texto solo si la fuente nueva lo haría ocupar más líneas que antes.
Uso: python rediseno_visual_pptx.py
"""
import shutil
from pathlib import Path
from PIL import ImageFont
from pptx import Presentation
from pptx.util import Pt

AQUI = Path(__file__).resolve().parent
ORIGEN = AQUI / 'respaldo_presentacion_antes_redisenio_v2' / 'Presentacion_Integrador_FERIAUTO_Grupo1.pptx'
DESTINO = AQUI / 'Presentacion_Integrador_FERIAUTO_Grupo1.pptx'

COLORES = {  # paleta anterior -> paleta nueva (misma que la web)
    'F6F5F1': 'F3F2EC', '192B37': '12201A', '21684F': '0E6B4A', '3E4A7C': '38489A',
    'A14F32': 'B24F27', '596267': '68726C', 'D5D9D5': 'D4D1C5', 'EAF1ED': 'E2F1E8',
    'EDF1EE': 'F8F7F2',
}
CUERPO, TITULO = 'Segoe UI', 'Georgia'
FUENTES = Path('C:/Windows/Fonts')
TTF = {('Arial', False): 'arial.ttf', ('Arial', True): 'arialbd.ttf', ('Segoe UI', False): 'segoeui.ttf',
       ('Segoe UI', True): 'segoeuib.ttf', ('Georgia', False): 'georgia.ttf', ('Georgia', True): 'georgiab.ttf'}
_cache = {}


def fuente(nombre, negrita, pt):
    k = (nombre, negrita, round(pt * 4))
    if k not in _cache:
        _cache[k] = ImageFont.truetype(str(FUENTES / TTF[(nombre, negrita)]), max(1, round(pt * 10)))  # x10 para precisión
    return _cache[k]


def lineas(texto, nombre, negrita, pt, ancho_pt):
    f, total = fuente(nombre, negrita, pt), 0
    for parrafo in texto.split('\n'):
        n, actual = 1, ''
        for palabra in parrafo.split(' '):
            prueba = (actual + ' ' + palabra).strip()
            if f.getlength(prueba) / 10 > ancho_pt and actual:
                n, actual = n + 1, palabra
            else:
                actual = prueba
        total += n
    return total


def recolorar(p):
    for part in p.part.package.iter_parts():
        if not str(part.partname).startswith(('/ppt/slides/', '/ppt/slideLayouts/', '/ppt/slideMasters/', '/ppt/theme/')):
            continue
        blob = getattr(part, '_element', None)
        if blob is None:
            continue
        for el in blob.iter():
            if el.tag.endswith('}srgbClr') and el.get('val', '').upper() in COLORES:
                el.set('val', COLORES[el.get('val').upper()])


def ajustar_texto(tf, ancho_pt, cambios):
    runs = [r for para in tf.paragraphs for r in para.runs]
    if not runs:
        return
    for para in tf.paragraphs:
        for r in para.runs:
            pt = r.font.size.pt if r.font.size else None
            if pt is None:
                continue
            # Georgia usa cifras de texto (con ascendentes): los números grandes llevan Segoe UI en negrita
            r.font.name = TITULO if pt >= 26 and not any(ch.isdigit() for ch in r.text) else CUERPO
            if pt >= 26 and r.font.name == CUERPO and any(ch.isdigit() for ch in r.text):
                r.font.bold = True
    # ¿ocupa más líneas que antes? se reduce el tamaño (hasta -15 %) hasta igualarlo
    for para in tf.paragraphs:
        rs = [r for r in para.runs if r.font.size]
        if not rs or not para.text.strip():
            continue
        pt, neg = rs[0].font.size.pt, bool(rs[0].font.bold)
        nuevo = TITULO if pt >= 26 and not any(ch.isdigit() for ch in para.text) else CUERPO
        antes = lineas(para.text, 'Arial', neg, pt, ancho_pt)
        nuevo_pt = pt
        while lineas(para.text, nuevo, neg, nuevo_pt, ancho_pt) > antes and nuevo_pt > pt * .85:
            nuevo_pt -= .5
        if nuevo_pt != pt:
            for r in rs:
                r.font.size = Pt(nuevo_pt)
            cambios.append((para.text[:40], pt, nuevo_pt))


def recorrer(shapes, cambios):
    for sh in shapes:
        if sh.shape_type == 6:
            recorrer(sh.shapes, cambios)
            continue
        if sh.has_text_frame:
            bp = sh.text_frame._txBody.bodyPr
            ancho = (sh.width - int(bp.get('lIns', 91440)) - int(bp.get('rIns', 91440))) / 12700
            ajustar_texto(sh.text_frame, ancho, cambios)
        if getattr(sh, 'has_table', False) and sh.has_table:
            t = sh.table
            for fila in t.rows:
                for i, c in enumerate(fila.cells):
                    ancho = (t.columns[i].width - c.margin_left - c.margin_right) / 12700
                    ajustar_texto(c.text_frame, ancho, cambios)


CAPTURAS = {2: 'plataforma_inicio.png', 6: 'plataforma_organigrama.png'}  # lámina -> captura de la interfaz nueva


def cambiar_capturas(p):
    for n, archivo in CAPTURAS.items():
        diap = p.slides[n - 1]
        viejo = next(sh for sh in diap.shapes if sh.shape_type == 13 and sh.image.size[0] > 1000)
        x, y, w, h = viejo.left, viejo.top, viejo.width, viejo.height
        nuevo = diap.shapes.add_picture(str(AQUI / 'presentacion_build' / 'assets' / archivo), x, y, w, h)
        viejo._element.addprevious(nuevo._element)   # misma capa que la captura anterior
        viejo._element.getparent().remove(viejo._element)


def main():
    if not ORIGEN.exists():
        ORIGEN.parent.mkdir(exist_ok=True)
        shutil.copy2(DESTINO, ORIGEN)
    p = Presentation(str(ORIGEN))
    recolorar(p)
    cambiar_capturas(p)
    cambios = []
    for s in p.slides:
        recorrer(s.shapes, cambios)
    p.save(str(DESTINO))
    print(f'Presentación actualizada: {DESTINO.name}')
    for c in cambios:
        print(f'  tamaño ajustado {c[1]} -> {c[2]} pt: {c[0]!r}')


if __name__ == '__main__':
    main()
