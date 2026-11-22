"""Copia literal de fuentes autorizadas; se ejecuta al preparar la entrega, no al navegar."""
import hashlib
import json
import shutil
import subprocess
import argparse
from pathlib import Path
from pypdf import PdfReader

RAIZ = Path(__file__).resolve().parent
ORIGEN = RAIZ.parent
DESTINO = RAIZ / "evidencias_integrador"

# id, módulo, título, tipo, contexto, archivo original, descripción
FUENTES = [
    ("pea1", "emprendimiento", "PEA 1 · Plan de negocios FERIAUTO", "Informe", "FERIAUTO · etapa inicial", "GuiaAPE1_Grupo01.pdf", "Informe institucional y plan empresarial con mercado, operación y resultados económicos."),
    ("oportunidad", "emprendimiento", "Tarea 01 · Problema y oportunidad", "Trabajo", "FERIAUTO", "Tarea01_TallerClase_2.pdf", "Alternativas evaluadas y elección de la feria de vehículos de Ambato."),
    ("canvas", "emprendimiento", "Tarea 02 · Business Model Canvas", "Trabajo", "FERIAUTO", "Tarea02_BusinessModelCanvas_Grupo.pdf", "Modelo de negocio y propuesta de valor."),
    ("estrategia", "emprendimiento", "Taller 03 · Perfil estratégico", "Trabajo", "FERIAUTO", "Taller03_TallerPerfilEstrategico_Grupo.pdf", "Identidad, misión, visión, FODA y estrategias."),
    ("mercado", "emprendimiento", "Taller 04 · Mercado y operación", "Trabajo", "FERIAUTO", "Taller04_Mercado_Operacion_Emprendimiento_Grupo.pdf", "Clientes, competencia, sondeo y proceso operativo."),
    ("viabilidad", "emprendimiento", "Taller 05 · Viabilidad financiera", "Trabajo", "FERIAUTO · escenario inicial", "Taller05_Vialidad_Financiera_Costos_Grupos.pdf", "Inversión, costos, ingresos y resultado mensual de la propuesta inicial."),
    ("costos-excel", "emprendimiento", "Libro de costos del semestre", "Hoja de cálculo", "Plantilla trabajada en clase", "Plantilla vialidad financiera-costos.xlsx", "Libro original para consulta; conserva las hojas y fórmulas existentes."),
    ("unidad1", "emprendimiento", "Unidad 1 · Emprendimiento", "Contenido de clase", "Material de la asignatura", "all_unidad1_emprendimiento.pdf", "Referencia conceptual del proceso de emprendimiento."),
    ("pea2", "tributarias", "PEA 2 · Obligaciones tributarias FERIAUTO", "Informe", "FERIAUTO · septiembre de 2026 · simulación", "Informe_PEA2_ObligacionesTributarias_GRUPO1.pdf", "RUC, comprobantes, declaración de IVA y registro de marca consolidados."),
    ("ruc", "tributarias", "Tarea 06 · Simulación de RUC", "Práctica complementaria", "MACASOFT · práctica individual", "Tarea06_SimulacionRUC_ConstanteSebastian.pdf", "Ejercicio previo de inscripción y consulta; empresa diferente de FERIAUTO."),
    ("facturador", "tributarias", "Tarea 07 · Facturador SRI", "Práctica complementaria", "Práctica del facturador SRI", "Tarea07_facturadorSRI_ConstanteSebastian.pdf.pdf", "Captura del ejercicio de facturación en clase; no es una venta del consolidado PEA 2."),
    ("comprobantes", "tributarias", "Tarea 08 · Comprobantes y retenciones", "Práctica complementaria", "INDUMETAL · práctica individual", "Tarea08_ObligacionesTributariaas_ConstanteSebastian.pdf", "Comprobantes tributarios del ejercicio previo de otra empresa."),
    ("iva-practica", "tributarias", "Tarea 09 · Declaración de IVA", "Práctica complementaria", "INDUMETAL · práctica individual", "Tarea09_ObligacionesTributariasII_ConstanteSebastians.pdf", "Declaración del caso de clase; sus valores no se suman al PEA 2 de FERIAUTO."),
    ("marca", "tributarias", "Tarea 10 · Registro de marca", "Trabajo", "FERIAUTO · simulación SENADI", "Tarea10_RegistroMarcaGamificacion_Grupo1.pdf", "Búsqueda y protección de la identidad del emprendimiento."),
    ("senadi", "tributarias", "Expediente simulado SENADI", "Evidencia", "FERIAUTO · simulación académica", "senadi_2026_FERIAUTO.pdf", "Respaldo documental del ejercicio de registro de marca."),
    ("importacion", "tributarias", "Tarea 11 · Importación de tecnología", "Práctica complementaria", "Grupo 1 · comercio exterior", "Tarea11_ImportacionTecnologia_Grupo01.pdf", "Infografía complementaria; no constituye una importación de FERIAUTO."),
    ("unidad2", "tributarias", "Unidad 2 · Obligaciones tributarias", "Contenido de clase", "Material de la asignatura", "2.1 Obligaciones tributarias de emprendedores.pdf", "Contenido de referencia trabajado en la unidad."),
    ("pea3", "nomina", "PEA 3 · Contratación laboral FERIAUTO", "Informe", "FERIAUTO · escenario laboral", "PEA3/Informe_PEA3_ContratacionLaboral_FERIAUTO.pdf", "Organigrama, remuneraciones y sostenibilidad del contrato municipal simulado."),
    ("pea3-grupo", "nomina", "PEA 3 · Entrega grupal", "Informe", "FERIAUTO · Grupo 1", "PEA3/Informe_PEA3_ContratacionLaboral_FERIAUTOGrupo1.pdf", "Informe entregado por el grupo y enlace documentado de la plataforma."),
    ("tabla-remuneraciones", "nomina", "Tabla de remuneraciones FERIAUTO", "Hoja de cálculo", "FERIAUTO · PEA 3", "PEA3/Tabla_remuneraciones_FERIAUTO.xlsx", "Libro elaborado previamente con parámetros y remuneraciones."),
    ("rol-diciembre", "nomina", "Rol de diciembre de 2026", "Hoja de cálculo", "Exportación existente del semestre", "rol_2026_12_diciembre.xlsx", "Rol ya exportado; se consulta el archivo original sin regenerarlo."),
    ("contratacion", "nomina", "APE 3 · Análisis de contratación", "Trabajo", "Grupo 1 · casos de clase", "APE3_Analisis_Contratacion_Laboral-GRUPO1.pdf", "Análisis previo de derechos y formas de contratación laboral."),
    ("unidad3", "nomina", "Unidad 3 · Estructura salarial", "Contenido de clase", "Material de la asignatura", "3.3 Estructura salarial y orgánico funcional.pdf", "Fundamentos del organigrama y las remuneraciones."),
    ("beneficios", "nomina", "Unidad 3 · Beneficios laborales", "Contenido de clase", "Material de la asignatura", "3.5 Otros beneficios laborales normativa Ecuatoriana.pdf", "Material de consulta del semestre sobre beneficios sociales."),
    ("ministerio", "liquidacion", "Liquidación original del Ministerio", "Evidencia", "Mateo Demostración · acuerdo entre las partes", "roles_pago/casos/ape4/liquidacion-oficial.pdf", "Resultado obtenido el 17 de noviembre de 2026 con datos ficticios: USD 162,83."),
    ("ministerio-comparacion", "liquidacion", "Comparación por despido intempestivo", "Evidencia", "Mateo Demostración · comparación académica", "roles_pago/casos/ape4/comparacion-despido-oficial.pdf", "Consulta oficial ya realizada: total aproximado USD 1.692,83."),
    ("paz-certificado", "liquidacion", "Certificado de paz y salvo de muestra", "Evidencia", "Expediente ficticio APE 4", "roles_pago/entregables_ape4/certificado-paz-y-salvo.pdf", "Documento generado previamente para la demostración académica."),
    ("paz-liquidacion", "liquidacion", "Liquidación administrativa de muestra", "Evidencia", "Expediente ficticio APE 4", "roles_pago/entregables_ape4/liquidacion-administrativa.pdf", "Consolidación previa de importes respaldados por el simulador ministerial."),
    ("paz-resumen", "liquidacion", "Resumen general para firma", "Evidencia", "Expediente ficticio APE 4 · sin firmas", "roles_pago/entregables_ape4/resumen-general-para-firma.pdf", "Copia de muestra con espacios para las firmas de las partes."),
    ("paz-informe", "liquidacion", "APE 4 · Informe de paz y salvo", "Informe", "FERIAUTO · expediente ficticio", "roles_pago/entregables_ape4/informe-APE4-paz-y-salvo-pulido.docx", "Informe previo sobre terminación, liquidación y evidencias documentales."),
    ("comparativa", "liquidacion", "Tabla comparativa del Ministerio", "Hoja de cálculo", "Expediente ficticio APE 4", "roles_pago/entregables_ape4/tabla-comparativa-ministerio.xlsx", "Tabla existente de los resultados ministeriales consultados."),
    ("casos-terminacion", "liquidacion", "Casos de terminación de clase", "Contenido de clase", "Material de la asignatura", "Casos_Liquidaciones_Diferentes_Causales_UTA.pdf", "Casos proporcionados en la asignatura; se conservan para consulta."),
    ("unidad4", "liquidacion", "Unidad 4 · Terminación del contrato", "Contenido de clase", "Material de la asignatura", "4.1 Terminación_del_Contrato_Laboral Normativa Ecuatoriana.pdf", "Referencia conceptual de las formas de terminación laboral."),
]


def preparar():
    DESTINO.mkdir(exist_ok=True)
    catalogo = []
    for clave, modulo, titulo, tipo, contexto, fuente, descripcion in FUENTES:
        original = ORIGEN / fuente
        if not original.is_file():
            raise FileNotFoundError(original)
        nombre = clave + original.suffix.lower()
        copia = DESTINO / nombre
        shutil.copy2(original, copia)
        catalogo.append(dict(id=clave, modulo=modulo, titulo=titulo, tipo=tipo, contexto=contexto,
                             fuente=fuente, descripcion=descripcion, archivo=nombre,
                             paginas=len(PdfReader(copia).pages) if copia.suffix == ".pdf" else None,
                             bytes=copia.stat().st_size, sha256=hashlib.sha256(copia.read_bytes()).hexdigest()))
    (DESTINO / "catalogo.json").write_text(json.dumps(catalogo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(catalogo)} fuentes copiadas literalmente y verificadas en {DESTINO}")


def vistas_previas(pdftoppm):
    """Renderiza páginas del PDF para consulta en navegadores sin visor incorporado."""
    catalogo = json.loads((DESTINO / "catalogo.json").read_text(encoding="utf-8"))
    for doc in catalogo:
        if not doc["paginas"]:
            continue
        carpeta = DESTINO / "vistas" / doc["id"]
        carpeta.mkdir(parents=True, exist_ok=True)
        if not (carpeta / f"{doc['paginas']}.jpg").is_file():
            subprocess.run([str(pdftoppm), "-jpeg", "-jpegopt", "quality=80,optimize=y",
                            "-scale-to", "1500", str(DESTINO / doc["archivo"]), str(carpeta / "pagina")],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for imagen in carpeta.glob("pagina-*.jpg"):
                imagen.replace(carpeta / f"{int(imagen.stem.split('-')[-1])}.jpg")
        doc["vista_previa"] = True
        print(f"Vista previa: {doc['id']} ({doc['paginas']} páginas)", flush=True)
    (DESTINO / "catalogo.json").write_text(json.dumps(catalogo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def optimizar_vistas():
    """Reduce el peso de las vistas sin cambiar resolución ni archivos originales."""
    from PIL import Image
    catalogo = json.loads((DESTINO / "catalogo.json").read_text(encoding="utf-8"))
    anterior = nuevo = 0
    for doc in catalogo:
        if not doc.get("vista_previa"):
            continue
        carpeta = DESTINO / "vistas" / doc["id"]
        for pagina in range(1, doc["paginas"] + 1):
            jpg, webp = carpeta / f"{pagina}.jpg", carpeta / f"{pagina}.webp"
            anterior += jpg.stat().st_size
            if not webp.is_file():
                with Image.open(jpg) as imagen:
                    imagen.save(webp, format="WEBP", quality=85, method=6)
            nuevo += webp.stat().st_size
        doc["vista_formato"] = "webp"
        print(f"Optimizado: {doc['id']}", flush=True)
    (DESTINO / "catalogo.json").write_text(json.dumps(catalogo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Vistas: {anterior / 1048576:.1f} → {nuevo / 1048576:.1f} MiB", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdftoppm", help="Ruta del renderizador para preparar vistas de los originales")
    parser.add_argument("--optimizar-vistas", action="store_true", help="Comprime vistas en WebP y conserva los originales")
    argumentos = parser.parse_args()
    if argumentos.optimizar_vistas:
        optimizar_vistas()
    elif argumentos.pdftoppm:
        vistas_previas(argumentos.pdftoppm)
    else:
        preparar()
