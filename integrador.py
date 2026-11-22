"""Consulta de trabajos del semestre. No calcula ni modifica los módulos laborales."""
import json
import re
import unicodedata
from pathlib import Path

from flask import Blueprint, abort, render_template, request, send_file

from integrador_contenido import IDENTIDAD, MODULOS, RECURSOS

RAIZ = Path(__file__).resolve().parent
DIRECTORIO = RAIZ / "evidencias_integrador"
bp = Blueprint("integrador", __name__)


def documentos():
    return json.loads((DIRECTORIO / "catalogo.json").read_text(encoding="utf-8"))


def normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", texto.casefold()) if not unicodedata.combining(c))


def buscar_documento(clave):
    doc = next((d for d in documentos() if d["id"] == clave), None)
    if doc is None:
        abort(404)
    return doc


@bp.get("/")
def inicio():
    docs = documentos()
    return render_template("integrador_inicio.html", modulos=MODULOS, n_documentos=len(docs), recursos=RECURSOS,
                           conteos={m["id"]: sum(d["modulo"] == m["id"] for d in docs) for m in MODULOS})


@bp.get("/empresa")
def empresa():
    """Identidad del emprendimiento: marca, misión, visión y FODA ya definidos en la PEA 1."""
    return render_template("integrador_empresa.html", ide=IDENTIDAD, modulos=MODULOS)


@bp.get("/modulos/<clave>")
def modulo(clave):
    modulo = next((m for m in MODULOS if m["id"] == clave), None)
    if modulo is None:
        abort(404)
    indice = MODULOS.index(modulo)
    return render_template("integrador_modulo.html", modulo=modulo, modulos=MODULOS,
                           recursos=[r for r in RECURSOS if clave in r["modulos"]],
                           documentos=[d for d in documentos() if d["modulo"] == clave],
                           anterior=MODULOS[indice - 1] if indice else None,
                           siguiente=MODULOS[indice + 1] if indice < 3 else None)


@bp.get("/biblioteca")
def biblioteca():
    q = request.args.get("q", "").strip()[:200]
    modulo = request.args.get("modulo", "")
    tipo = request.args.get("tipo", "")
    docs = documentos()
    titulos = {m["id"]: m["titulo"] for m in MODULOS}
    def coincide(doc):
        claves = doc.get("modulos", [doc.get("modulo")])
        palabras = re.findall(r"\w+", normalizar(" ".join([
            doc["titulo"], doc["descripcion"], doc["contexto"], doc.get("fuente", ""),
            " ".join(titulos[clave] for clave in claves), doc["tipo"], doc.get("nota", "")])).replace("_", " "))
        return all(any(palabra.startswith(termino) for palabra in palabras)
                   for termino in normalizar(q).split())
    resultados = [d for d in docs if (not modulo or d["modulo"] == modulo)
                  and (not tipo or d["tipo"] == tipo)
                  and coincide(d)]
    videos = [r for r in RECURSOS if (not modulo or modulo in r["modulos"])
              and (not tipo or tipo == r["tipo"]) and coincide(r)]
    return render_template("integrador_biblioteca.html", documentos=resultados, modulos=MODULOS,
                           recursos=videos, tipos=sorted({d["tipo"] for d in docs} | {"Video"}), q=q, filtro_modulo=modulo,
                           filtro_tipo=tipo, total=len(docs))


@bp.get("/documentos/<clave>")
def documento(clave):
    doc = buscar_documento(clave)
    pagina = request.args.get("pagina", 1, type=int)
    pagina = max(1, min(pagina or 1, doc.get("paginas") or 1))
    return render_template("integrador_documento.html", doc=doc, pagina=pagina,
                           modulo=next(m for m in MODULOS if m["id"] == doc["modulo"]))


@bp.get("/documentos/<clave>/archivo")
def archivo(clave):
    doc = buscar_documento(clave)
    ruta = (DIRECTORIO / doc["archivo"]).resolve()
    if not ruta.is_relative_to(DIRECTORIO.resolve()) or not ruta.is_file():
        abort(404)
    respuesta = send_file(ruta, as_attachment=request.args.get("descargar") == "1",
                          download_name=Path(doc["fuente"]).name, conditional=True)
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    return respuesta


@bp.get("/documentos/<clave>/pagina/<int:pagina>")
def vista_previa(clave, pagina):
    doc = buscar_documento(clave)
    if not 1 <= pagina <= (doc.get("paginas") or 0):
        abort(404)
    formato = "webp" if doc.get("vista_formato") == "webp" else "jpg"
    ruta = DIRECTORIO / "vistas" / doc["id"] / f"{pagina}.{formato}"
    if not ruta.is_file():
        abort(404)
    return send_file(ruta, mimetype="image/webp" if formato == "webp" else "image/jpeg", conditional=True)


@bp.get("/entrega-final/<clave>")
def entrega(clave):
    # Lista cerrada: nunca se sirve un nombre de archivo proporcionado por el visitante.
    nombres = {"informe": "Informe_Integrador_FERIAUTO_Grupo1.pdf",
               "presentacion": "Presentacion_Integrador_FERIAUTO_Grupo1.pptx",
               "laminas": "Presentacion_Integrador_FERIAUTO_Grupo1.pdf",
               "guion": "Guion_Exposicion_Grupo1.md"}
    nombre = nombres.get(clave)
    if not nombre or not (RAIZ / "entregables_integrador" / nombre).is_file():
        abort(404)
    return send_file(RAIZ / "entregables_integrador" / nombre, as_attachment=True)


def registrar(app):
    app.register_blueprint(bp)
