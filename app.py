"""
Módulo demostrativo de Roles de Pago (Ecuador 2026) — Flask + SQLite.
Ejecutar:  iniciar.bat (Windows) / ./iniciar.sh (macOS, Linux)
      o:   pip install -r requirements.txt  &&  python app.py   →  http://127.0.0.1:5050
La base roles.db se crea sola con empleados de ejemplo; "Reiniciar demo" (pie de página) la vuelve al inicio.
"""
import os
import sqlite3
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from flask import Flask, flash, g, redirect, render_template, request, url_for
from markupsafe import Markup

import calculos

DB_PATH = Path(__file__).with_name("roles.db")
EMPRESA = {"nombre": "FERIAUTO SAS", "ruc": "1790000000001", "region": "Sierra"}  # ficticia
# La región solo cambia la FECHA de pago del 14°, no el monto: Sierra/Amazonía hasta el 15 de agosto,
# Costa/Galápagos hasta el 15 de marzo. El 13° se paga hasta el 24 de diciembre.
MESES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
TIPOS_CONTRATO = ["Indefinido", "Plazo fijo", "Eventual", "Ocasional", "Por obra o servicio"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS empleados (
    id INTEGER PRIMARY KEY,
    cedula TEXT NOT NULL UNIQUE,
    nombres TEXT NOT NULL,
    apellidos TEXT NOT NULL,
    cargo TEXT NOT NULL,
    sueldo REAL NOT NULL CHECK (sueldo > 0),
    fecha_ingreso TEXT NOT NULL,
    tipo_contrato TEXT NOT NULL,
    activo INTEGER NOT NULL DEFAULT 1,
    mensualiza_decimos INTEGER NOT NULL DEFAULT 0,
    mensualiza_fondos INTEGER NOT NULL DEFAULT 1,  -- por ley los fondos se pagan mensualizados salvo pedido
    gastos_personales REAL NOT NULL DEFAULT 0,     -- proyección anual entregada al empleador (formulario SRI-GP)
    cargas INTEGER NOT NULL DEFAULT 0 CHECK (cargas >= 0)
);
CREATE TABLE IF NOT EXISTS roles_cabecera (
    id INTEGER PRIMARY KEY,
    anio INTEGER NOT NULL,
    mes INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
    generado_en TEXT NOT NULL,
    n_empleados INTEGER NOT NULL,
    total_ingresos REAL NOT NULL,
    total_descuentos REAL NOT NULL,
    total_neto REAL NOT NULL,
    total_costo REAL NOT NULL,
    total_iess REAL NOT NULL,
    total_ir REAL NOT NULL,
    UNIQUE (anio, mes)                -- un solo rol por periodo; regenerar lo reemplaza
);
CREATE TABLE IF NOT EXISTS roles_detalle (
    id INTEGER PRIMARY KEY,
    rol_id INTEGER NOT NULL REFERENCES roles_cabecera(id) ON DELETE CASCADE,
    empleado_id INTEGER NOT NULL REFERENCES empleados(id),
    -- snapshot del empleado: si luego cambia su sueldo, el rol histórico no se altera
    nombre TEXT, cedula TEXT, cargo TEXT, sueldo REAL,
    -- novedades del mes (ingresadas a mano)
    dias INTEGER, h50 REAL, h100 REAL, comisiones REAL, anticipos REAL, prestamos_iess REAL,
    mensualiza_decimos INTEGER, mensualiza_fondos INTEGER, gastos_personales REAL, cargas INTEGER,
    -- resultados de calculos.calcular_rol()
    sueldo_ganado REAL, valor_hora REAL, v_h50 REAL, v_h100 REAL, total_gravado REAL,
    decimo13_pagado REAL, decimo14_pagado REAL, fondos_pagado REAL, total_no_gravado REAL,
    total_ingresos REAL, iess_personal REAL, base_ir_anual REAL, ir_causado REAL, rebaja_gp REAL,
    tope_gp REAL, ir_anual REAL, ir REAL,
    ir_tramo_desde REAL, ir_impuesto_fb REAL, ir_pct REAL, total_descuentos REAL, neto REAL,
    p13 REAL, p14 REAL, p_vac REAL, p_fondos REAL, patronal REAL, iece_secap REAL,
    total_provisiones REAL, costo_total REAL, tiene_fondos INTEGER, avisos TEXT
);
"""

SCHEMA_VERSION = 2  # súbelo si cambias SCHEMA: la base vieja se respalda y se crea una nueva

SEMILLA = [  # empleados de ejemplo (ficticios, cédulas con dígito verificador válido)
    # cédula, nombres, apellidos, cargo, sueldo, ingreso, contrato, mensualiza 13°/14°, mensualiza F.R., gastos personales, cargas
    ("1712345675", "María Fernanda", "López Andrade", "Contadora", 1500, "2024-01-15", "Indefinido", 0, 0, 0, 0),
    ("0912345675", "Carlos Andrés", "Pérez Vera", "Vendedor", 650, "2025-03-01", "Indefinido", 1, 1, 0, 0),
    ("0104567896", "Ana Lucía", "Torres Mena", "Asistente administrativa", 482, "2026-02-01", "Plazo fijo", 0, 1, 0, 0),
    ("1309876546", "Jorge Luis", "Castillo Ruiz", "Gerente general", 3200, "2020-06-01", "Indefinido", 0, 1, 8000, 2),
]
CAMPOS_EMPLEADO = ("cedula", "nombres", "apellidos", "cargo", "sueldo", "fecha_ingreso", "tipo_contrato",
                   "mensualiza_decimos", "mensualiza_fondos", "gastos_personales", "cargas")

app = Flask(__name__)
app.secret_key = "demo-roles-pago"  # ponytail: solo para mensajes flash; no hay login


# ------------------------------------------------------------------ base de datos
def db():
    if "db" not in g:
        if not DB_PATH.exists():  # borraron roles.db con la app corriendo → se recrea con la semilla
            init_db()
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def cerrar_db(_):
    if (conn := g.pop("db", None)) is not None:
        conn.close()


def filas(sql, params=()):
    return [dict(r) for r in db().execute(sql, params)]


def init_db():
    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
        conn.close()
        if version != SCHEMA_VERSION:  # esquema viejo: se respalda en vez de borrarse
            DB_PATH.replace(DB_PATH.with_name(f"roles_v{version}_respaldo.db"))
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        if conn.execute("SELECT COUNT(*) FROM empleados").fetchone()[0] == 0:
            conn.executemany(f"INSERT INTO empleados ({', '.join(CAMPOS_EMPLEADO)}) "
                             f"VALUES ({', '.join('?' * len(CAMPOS_EMPLEADO))})", SEMILLA)
    conn.close()


# ------------------------------------------------------------------ helpers de vista
@app.template_filter("cifra")
def cifra(valor):
    """1793.75 → '1.793,75' (formato ecuatoriano: punto de miles, coma decimal)."""
    return f"{float(valor or 0):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


@app.template_filter("money")
def money(valor):
    return f"$ {cifra(valor)}"


@app.template_filter("dash")
def dash(valor):
    """Cifra para tablas; un cero se muestra como '—' atenuado (convención de libro contable)."""
    return cifra(valor) if round(float(valor or 0), 2) else Markup('<span class="zero">—</span>')


@app.context_processor
def globales():
    return dict(EMPRESA=EMPRESA, MESES=MESES, P={
        "sbu": int(calculos.SBU), "iess_personal": "9,45%", "patronal": "11,15%",
        "iece_secap": "1%", "fondos": "8,33%", "canasta": cifra(calculos.CANASTA_2026),
        "canastas": calculos.CANASTAS_POR_CARGAS})


def antiguedad(fecha_ingreso):
    ini, hoy = date.fromisoformat(fecha_ingreso), date.today()
    meses = (hoy.year - ini.year) * 12 + hoy.month - ini.month - (hoy.day < ini.day)
    anios, meses = divmod(max(meses, 0), 12)
    partes = [f"{anios} año{'s' * (anios != 1)}"] if anios else []
    return " ".join(partes + [f"{meses} mes{'es' * (meses != 1)}"])


def numero(texto, defecto="0"):
    """Convierte un input del formulario a Decimal ≥ 0; lanza ValueError si no es válido."""
    try:
        valor = Decimal((texto or defecto).strip().replace(",", "."))
    except InvalidOperation:
        raise ValueError(texto)
    if valor < 0 or not valor.is_finite():
        raise ValueError(texto)
    return valor


# ------------------------------------------------------------------ empleados (CRUD)
@app.get("/empleados")
def empleados_lista():
    empleados = filas("SELECT * FROM empleados ORDER BY activo DESC, apellidos")
    for e in empleados:
        e["antiguedad"] = antiguedad(e["fecha_ingreso"])
    return render_template("empleados.html", empleados=empleados)


@app.get("/empleados/nuevo")
def empleado_nuevo():
    return render_template("empleado_form.html", e=None, tipos_contrato=TIPOS_CONTRATO, errores=[])


@app.get("/empleados/<int:id>/editar")
def empleado_editar(id):
    e = filas("SELECT * FROM empleados WHERE id = ?", (id,))
    if not e:
        flash("Empleado no encontrado.", "danger")
        return redirect(url_for("empleados_lista"))
    return render_template("empleado_form.html", e=e[0], tipos_contrato=TIPOS_CONTRATO, errores=[])


@app.post("/empleados/guardar")
def empleado_guardar():
    f = request.form
    e = {k: f.get(k, "").strip() for k in
         ("id", "cedula", "nombres", "apellidos", "cargo", "sueldo", "fecha_ingreso", "tipo_contrato",
          "gastos_personales", "cargas")}
    for k in ("activo", "mensualiza_decimos", "mensualiza_fondos"):
        e[k] = int(k in f)

    errores = []
    if not calculos.cedula_valida(e["cedula"]):
        errores.append("Cédula inválida (10 dígitos con verificador módulo 10).")
    if not (e["nombres"] and e["apellidos"] and e["cargo"]):
        errores.append("Nombres, apellidos y cargo son obligatorios.")
    try:
        if numero(e["sueldo"]) <= 0:
            raise ValueError
    except ValueError:
        errores.append("El sueldo debe ser un número mayor a 0.")
    try:
        if date.fromisoformat(e["fecha_ingreso"]) > date.today():
            errores.append("La fecha de ingreso no puede ser futura.")
    except ValueError:
        errores.append("Fecha de ingreso inválida.")
    if e["tipo_contrato"] not in TIPOS_CONTRATO:
        errores.append("Tipo de contrato inválido.")
    try:
        numero(e["gastos_personales"])
        if not 0 <= int(e["cargas"] or 0) <= 20:
            raise ValueError
    except ValueError:
        errores.append("Gastos personales y cargas familiares deben ser números ≥ 0.")

    if not errores:
        campos = CAMPOS_EMPLEADO + ("activo",)
        valores = [e[k] for k in campos]
        valores[campos.index("sueldo")] = float(numero(e["sueldo"]))
        valores[campos.index("gastos_personales")] = float(numero(e["gastos_personales"]))
        valores[campos.index("cargas")] = int(e["cargas"] or 0)
        try:
            with db():
                if e["id"]:
                    db().execute(f"UPDATE empleados SET {', '.join(c + ' = ?' for c in campos)} WHERE id = ?",
                                 valores + [int(e["id"])])
                else:
                    db().execute(f"INSERT INTO empleados ({', '.join(campos)}) VALUES ({', '.join('?' * len(campos))})",
                                 valores)
        except sqlite3.IntegrityError:
            errores.append("Ya existe un empleado con esa cédula.")
        else:
            flash(f"Empleado {e['nombres']} {e['apellidos']} guardado.", "success")
            return redirect(url_for("empleados_lista"))

    return render_template("empleado_form.html", e=e, tipos_contrato=TIPOS_CONTRATO, errores=errores)


@app.post("/empleados/<int:id>/toggle")
def empleado_toggle(id):
    with db():
        db().execute("UPDATE empleados SET activo = 1 - activo WHERE id = ?", (id,))
    flash("Estado del empleado actualizado.", "success")
    return redirect(url_for("empleados_lista"))


@app.post("/empleados/<int:id>/eliminar")
def empleado_eliminar(id):
    if db().execute("SELECT 1 FROM roles_detalle WHERE empleado_id = ? LIMIT 1", (id,)).fetchone():
        flash("No se puede eliminar: el empleado aparece en roles generados. Inactívalo en su lugar.", "warning")
    else:
        with db():
            db().execute("DELETE FROM empleados WHERE id = ?", (id,))
        flash("Empleado eliminado.", "success")
    return redirect(url_for("empleados_lista"))


# ------------------------------------------------------------------ roles de pago
@app.get("/")
def roles_lista():
    roles = filas("SELECT * FROM roles_cabecera ORDER BY anio DESC, mes DESC")
    n_activos = db().execute("SELECT COUNT(*) FROM empleados WHERE activo = 1").fetchone()[0]
    return render_template("roles.html", roles=roles, n_activos=n_activos)


@app.get("/roles/nuevo")
def rol_nuevo():
    hoy = date.today()
    anio = request.args.get("anio", hoy.year, type=int)
    mes = request.args.get("mes", hoy.month, type=int)
    if not 1 <= mes <= 12:
        mes = hoy.month

    cab = filas("SELECT id FROM roles_cabecera WHERE anio = ? AND mes = ?", (anio, mes))
    previas = {}  # si el rol ya existe, se precargan sus novedades para editarlas
    if cab:
        previas = {d["empleado_id"]: d for d in filas("SELECT * FROM roles_detalle WHERE rol_id = ?", (cab[0]["id"],))}

    lista = []
    for e in filas("SELECT * FROM empleados WHERE activo = 1 ORDER BY apellidos"):
        p = previas.get(e["id"], {})
        lista.append(dict(e=e, dias=p.get("dias", 30), h50=p.get("h50", 0), h100=p.get("h100", 0),
                          comisiones=p.get("comisiones", 0), anticipos=p.get("anticipos", 0),
                          prestamos_iess=p.get("prestamos_iess", 0)))
    return render_template("rol_nuevo.html", anio=anio, mes=mes, anios=list(range(hoy.year - 2, hoy.year + 2)),
                           existe=bool(cab), filas=lista)


@app.post("/roles/generar")
def rol_generar():
    f = request.form
    anio, mes = int(f["anio"]), int(f["mes"])
    empleados = filas("SELECT * FROM empleados WHERE activo = 1")

    detalles = []
    try:
        for e in empleados:
            i = e["id"]
            dias = int(numero(f.get(f"dias_{i}"), "30"))
            if not 1 <= dias <= 30:
                raise ValueError(f"días de {e['nombres']}")
            novedades = dict(dias=dias, h50=numero(f.get(f"h50_{i}")), h100=numero(f.get(f"h100_{i}")),
                             comisiones=numero(f.get(f"com_{i}")), anticipos=numero(f.get(f"ant_{i}")),
                             prestamos_iess=numero(f.get(f"pre_{i}")))
            detalles.append({"empleado_id": i, **calculos.calcular_rol(e, novedades, anio, mes)})
    except ValueError as err:
        flash(f"Revisa las novedades: valor inválido ({err}). Usa números ≥ 0 y días entre 1 y 30.", "danger")
        return redirect(url_for("rol_nuevo", anio=anio, mes=mes))
    if not detalles:
        flash("No hay empleados activos para procesar.", "warning")
        return redirect(url_for("empleados_lista"))

    def total(campo):
        return round(sum(Decimal(str(d[campo])) for d in detalles), 2)

    cabecera = dict(
        anio=anio, mes=mes, generado_en=date.today().isoformat(), n_empleados=len(detalles),
        total_ingresos=total("total_ingresos"), total_descuentos=total("total_descuentos"),
        total_neto=total("neto"), total_costo=total("costo_total"), total_ir=total("ir"),
        # planilla IESS = lo que se transfiere al IESS: aporte personal + patronal + IECE/SECAP
        total_iess=total("iess_personal") + total("patronal") + total("iece_secap"))
    cabecera = {k: float(v) if isinstance(v, Decimal) else v for k, v in cabecera.items()}

    with db():  # transacción: o se guarda todo el rol o nada
        db().execute("DELETE FROM roles_cabecera WHERE anio = ? AND mes = ?", (anio, mes))  # cascada al detalle
        cur = db().execute(f"INSERT INTO roles_cabecera ({', '.join(cabecera)}) VALUES ({', '.join('?' * len(cabecera))})",
                           list(cabecera.values()))
        rol_id = cur.lastrowid
        for d in detalles:
            d["rol_id"] = rol_id
            db().execute(f"INSERT INTO roles_detalle ({', '.join(d)}) VALUES ({', '.join('?' * len(d))})", list(d.values()))

    flash(f"Rol de {MESES[mes]} {anio} generado para {len(detalles)} empleados.", "success")
    return redirect(url_for("rol_ver", id=rol_id))


@app.get("/roles/<int:id>")
def rol_ver(id):
    cab = filas("SELECT * FROM roles_cabecera WHERE id = ?", (id,))
    if not cab:
        flash("Rol no encontrado.", "danger")
        return redirect(url_for("roles_lista"))
    detalles = filas("SELECT * FROM roles_detalle WHERE rol_id = ? ORDER BY nombre", (id,))
    return render_template("rol_ver.html", cab=cab[0], detalles=detalles)


@app.get("/roles/<int:id>/empleado/<int:det_id>")
def rol_individual(id, det_id):
    cab = filas("SELECT * FROM roles_cabecera WHERE id = ?", (id,))
    d = filas("SELECT * FROM roles_detalle WHERE id = ? AND rol_id = ?", (det_id, id))
    if not (cab and d):
        flash("Rol individual no encontrado.", "danger")
        return redirect(url_for("roles_lista"))
    return render_template("rol_individual.html", cab=cab[0], d=d[0])


@app.post("/roles/<int:id>/eliminar")
def rol_eliminar(id):
    with db():
        db().execute("DELETE FROM roles_cabecera WHERE id = ?", (id,))
    flash("Rol eliminado.", "success")
    return redirect(url_for("roles_lista"))


@app.post("/demo/reiniciar")
def demo_reiniciar():
    """Vuelve a los 4 empleados de ejemplo y sin roles (útil antes de cada práctica)."""
    DB_PATH.unlink(missing_ok=True)
    init_db()
    flash("Demo reiniciada: 4 empleados de ejemplo y ningún rol generado.", "success")
    return redirect(url_for("roles_lista"))


init_db()

if __name__ == "__main__":
    # 5050 y no 5000: en macOS el puerto 5000 lo ocupa AirPlay.
    app.run(debug=True, port=int(os.environ.get("PORT", 5050)))
