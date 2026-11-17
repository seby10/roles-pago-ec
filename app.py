"""
Módulo demostrativo de Roles de Pago (Ecuador 2026) — Flask + SQLite.
Ejecutar:  iniciar.bat (Windows) / ./iniciar.sh (macOS, Linux)
      o:   pip install -r requirements.txt  &&  python app.py   →  http://127.0.0.1:5050
La base roles.db se crea sola con empleados de ejemplo; "Reiniciar demo" (pie de página) la vuelve al inicio.
"""
import base64
import io
import json
import os
import sqlite3
from contextlib import closing
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import hmac
import secrets

from flask import Flask, flash, g, redirect, render_template, request, send_file, session, url_for
from markupsafe import Markup

import calculos
import exportar

DB_PATH = Path(os.environ.get("ROLES_DB_PATH") or Path(__file__).with_name("roles.db"))
# Valores iniciales de Parámetros (se guardan en la tabla parametros y se editan desde la app).
# Datos simulados del emprendimiento (proyecto académico).
PARAMETROS_INICIALES = {
    "nombre": "FERIAUTO S.A.S.", "ruc": "1850001234001", "region": "Sierra", "regimen": "CT",
    "actividad": "Plataforma digital para la feria de vehículos de Ambato",
    "cliente": "GAD Municipalidad de Ambato",
    "ingreso_mensual": "4500",  # contrato B2G simulado con el GAD: desarrollo, mantenimiento y soporte de la plataforma
    "otros_costos": "530",      # costos fijos 430 + variables 100 (Taller 05)
    "departamentos": "\n".join(["Gerencia General", "Tecnología", "Finanzas", "Marketing", "Operaciones"]),
    "logo": "", "logo_mime": "",
}
# Parámetros de cálculo editables: (clave, etiqueta, tipo). Los porcentajes se guardan como "9.45" (no 0.0945).
CAMPOS_CALCULO = [
    ("sbu", "Salario Básico Unificado (SBU)", "usd"), ("canasta", "Canasta familiar básica", "usd"),
    ("iess_personal", "Aporte personal IESS", "pct"), ("iess_patronal", "Aporte patronal IESS", "pct"),
    ("iece", "IECE (patronal adicional)", "pct"), ("secap", "SECAP (patronal adicional)", "pct"),
    ("fondos", "Fondos de reserva", "pct"), ("dias_vacaciones", "Días de vacaciones al año", "dias"),
    ("recargo_sup", "Factor horas suplementarias", "factor"), ("recargo_ext", "Factor horas extraordinarias", "factor"),
]
REGIONES = ["Sierra", "Amazonía", "Costa", "Galápagos"]
# La región solo cambia la FECHA de pago del 14°, no el monto: Sierra/Amazonía hasta el 15 de agosto,
# Costa/Galápagos hasta el 15 de marzo. El 13° se paga hasta el 24 de diciembre.
MESES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

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
    mensualiza_13 INTEGER NOT NULL DEFAULT 1,      -- décimo tercero pagado cada mes (a pedido del trabajador)
    mensualiza_14 INTEGER NOT NULL DEFAULT 0,      -- décimo cuarto pagado cada mes
    mensualiza_fondos INTEGER NOT NULL DEFAULT 1,  -- por ley los fondos se pagan mensualizados salvo pedido
    gastos_personales REAL NOT NULL DEFAULT 0,     -- proyección anual entregada al empleador (formulario SRI-GP)
    cargas INTEGER NOT NULL DEFAULT 0 CHECK (cargas >= 0),
    catastrofica INTEGER NOT NULL DEFAULT 0,       -- enfermedad catastrófica: tope de 100 canastas
    -- organización: de aquí sale el organigrama
    departamento TEXT NOT NULL DEFAULT '',
    reporta_a INTEGER REFERENCES empleados(id),    -- jefe inmediato; NULL = máxima autoridad
    funcion TEXT NOT NULL DEFAULT '',              -- función principal del cargo
    estructura TEXT NOT NULL DEFAULT ''            -- código de la escala del régimen (estructura ocupacional o grado)
);
CREATE TABLE IF NOT EXISTS parametros (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS escalas (               -- una escala salarial por régimen laboral
    id INTEGER PRIMARY KEY,
    regimen TEXT NOT NULL,
    codigo TEXT NOT NULL,
    denominacion TEXT NOT NULL,
    grupo TEXT NOT NULL DEFAULT '',
    valor REAL NOT NULL CHECK (valor > 0),
    UNIQUE (regimen, codigo)
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
    regimen TEXT NOT NULL DEFAULT 'CT',
    params TEXT NOT NULL DEFAULT '{}',  -- porcentajes con que se calculó (el rol histórico no cambia si cambian)
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
    mensualiza_13 INTEGER, mensualiza_14 INTEGER, mensualiza_fondos INTEGER, gastos_personales REAL, cargas INTEGER, catastrofica INTEGER,
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

SCHEMA_VERSION = 7  # v7: migración aditiva de paz y salvo, conserva empleados y roles de v6

# Equipo de FERIAUTO: los 4 socios fundadores, contratados bajo el Código del Trabajo desde el inicio
# de actividades (01-09-2026), y el primer empleado (ficticio). Sueldos sobre el mínimo sectorial de cada
# estructura y con jerarquía (Gerente General > directores > programador). Cédulas ficticias con dígito válido.
# reporta_a usa la posición en esta lista (1 = Gerente General).
SEMILLA = [
    # cédula, nombres, apellidos, cargo, sueldo, ingreso, contrato, mensualiza 13°, 14°, F.R.,
    # gastos personales, cargas, enfermedad catastrófica, departamento, reporta_a, función, estructura ocupacional
    ("1712345675", "Sebastián", "Constante", "Gerente General", 550, "2026-09-01", "Indefinido", 1, 0, 1, 0, 0, 0,
     "Gerencia General", None,
     "Representa legalmente a la empresa, dirige la estrategia y negocia el contrato con el GAD de Ambato.", "A1"),
    ("0912345675", "Pablo", "Montero", "Director de Tecnología", 530, "2026-09-01", "Indefinido", 1, 0, 1, 0, 0, 0,
     "Tecnología", 1,
     "Lidera el desarrollo de la plataforma, la integración con bases oficiales y la seguridad de los datos.", "A1"),
    ("0104567896", "Daylé", "García", "Directora Financiera", 530, "2026-09-01", "Indefinido", 1, 0, 1, 0, 0, 0,
     "Finanzas", 1,
     "Administra presupuesto, nómina, facturación y obligaciones tributarias con el SRI y el IESS.", "A1"),
    ("1309876546", "Jhanina", "Conterón", "Directora de Marketing", 530, "2026-09-01", "Indefinido", 1, 0, 1, 0, 0, 0,
     "Marketing", 1,
     "Posiciona la marca, gestiona la relación con comerciantes de la feria y la adopción de la app.", "A1"),
    ("1721345674", "Andrés", "Villacís", "Programador Junior", 510, "2026-10-01", "Indefinido", 1, 0, 1, 0, 0, 0,
     "Tecnología", 2,
     "Desarrolla y prueba módulos de la app y da soporte a los usuarios de la feria.", "C3"),
]
CAMPOS_EMPLEADO = ("cedula", "nombres", "apellidos", "cargo", "sueldo", "fecha_ingreso", "tipo_contrato",
                   "mensualiza_13", "mensualiza_14", "mensualiza_fondos", "gastos_personales", "cargas", "catastrofica",
                   "departamento", "reporta_a", "funcion", "estructura")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024   # subida del logo
# Publicación: si EDIT_PASSWORD está definida, la app queda en solo lectura y solo quien ingrese la clave
# puede modificar datos. Sin la variable (uso local en clase) todo es editable, como siempre.
EDIT_PASSWORD = os.environ.get("EDIT_PASSWORD", "")
# La clave de sesión firma la cookie del modo edición: publicada, nunca puede ser la del repositorio.
# Sin SECRET_KEY se genera una aleatoria (las sesiones se pierden al reiniciar el servidor, nada más).
app.secret_key = os.environ.get("SECRET_KEY") or (secrets.token_hex(32) if EDIT_PASSWORD else "demo-roles-pago")

import paz_salvo
paz_salvo.registrar(app, db=lambda: db(), empresa=lambda: empresa(), password=lambda: EDIT_PASSWORD)


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


def valores_legales(regimen):
    """Parámetros de cálculo por defecto del régimen, como texto para la tabla parametros."""
    r = calculos.REGIMENES[regimen]
    return {"sbu": str(calculos.SBU), "canasta": str(calculos.CANASTA_2026),
            "fondos": str(calculos.FONDOS_RESERVA * 100),
            **{k: str(r[k]) for k in ("iess_personal", "iess_patronal", "iece", "secap", "dias_vacaciones",
                                      "recargo_sup", "recargo_ext")}}


def sembrar_escala(conn, regimen):
    conn.execute("DELETE FROM escalas WHERE regimen = ?", (regimen,))
    conn.executemany("INSERT INTO escalas (regimen, codigo, denominacion, grupo, valor) VALUES (?, ?, ?, ?, ?)",
                     [(regimen, c, d, gr, float(v)) for c, d, gr, v in calculos.ESCALAS_BASE[regimen]])


def init_db():
    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
        conn.close()
        if version == 6:
            # SQLite backup también incluye cambios de un posible journal/WAL.
            with closing(sqlite3.connect(DB_PATH)) as origen, closing(sqlite3.connect(
                    DB_PATH.with_name("roles_v6_pre_paz_salvo_respaldo.db"))) as respaldo:
                origen.backup(respaldo)
        elif version != SCHEMA_VERSION:  # versiones anteriores mantienen el comportamiento histórico
            DB_PATH.replace(DB_PATH.with_name(f"roles_v{version}_respaldo.db"))
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)
        conn.executescript(paz_salvo.SCHEMA)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        if conn.execute("SELECT COUNT(*) FROM parametros").fetchone()[0] == 0:
            iniciales = {**PARAMETROS_INICIALES, **valores_legales(PARAMETROS_INICIALES["regimen"])}
            conn.executemany("INSERT INTO parametros VALUES (?, ?)", iniciales.items())
            for regimen in calculos.REGIMENES:
                sembrar_escala(conn, regimen)
        if conn.execute("SELECT COUNT(*) FROM empleados").fetchone()[0] == 0:
            conn.executemany(f"INSERT INTO empleados ({', '.join(CAMPOS_EMPLEADO)}) "
                             f"VALUES ({', '.join('?' * len(CAMPOS_EMPLEADO))})", SEMILLA)
    conn.close()


def empresa():
    """Parámetros de la empresa (tabla parametros) con los números ya convertidos. Uno por petición."""
    if "empresa" not in g:
        e = {r["clave"]: r["valor"] for r in filas("SELECT clave, valor FROM parametros")}
        e = {**PARAMETROS_INICIALES, **valores_legales(e.get("regimen", "CT")), **e}
        for k in ("ingreso_mensual", "otros_costos"):
            e[k] = float(e[k] or 0)
        e["departamentos"] = [d.strip() for d in e["departamentos"].splitlines() if d.strip()]
        e["reg"] = calculos.REGIMENES[e["regimen"]]
        g.empresa = e
    return g.empresa


def escala_actual(regimen=None):
    return filas("SELECT * FROM escalas WHERE regimen = ? ORDER BY valor DESC, codigo",
                 (regimen or empresa()["regimen"],))


def params():
    """Parámetros para calculos.calcular_rol: régimen, porcentajes y escala que la empresa tiene guardados."""
    if "params" not in g:
        e = empresa()
        D = lambda k: Decimal(str(e[k]))
        g.params = dict(
            regimen=e["regimen"], regla=e["reg"]["regla"], sbu=D("sbu"), canasta=D("canasta"),
            iess_personal=D("iess_personal") / 100, iess_patronal=D("iess_patronal") / 100,
            iece=D("iece") / 100, secap=D("secap") / 100, fondos=D("fondos") / 100,
            dias_vacaciones=int(e["dias_vacaciones"]), recargo_sup=D("recargo_sup"), recargo_ext=D("recargo_ext"),
            escala={x["codigo"]: (x["denominacion"], Decimal(str(x["valor"]))) for x in escala_actual()})
    return g.params


def pct(x):
    """Decimal o texto '9.45' → '9,45%' (sin ceros de más: 0.5 → '0,5%', 8.33 → '8,33%')."""
    return f"{Decimal(str(x)).normalize():f}".replace(".", ",") + "%"


def vista_params():
    """Lo que las plantillas muestran de los parámetros. Se guarda con cada rol para que el histórico no cambie."""
    e = empresa()
    iece_secap = Decimal(str(e["iece"])) + Decimal(str(e["secap"]))
    return {"regimen": e["regimen"], "regimen_nombre": e["reg"]["nombre"], "sbu": cifra(e["sbu"]),
            "iess_personal": pct(e["iess_personal"]), "patronal": pct(e["iess_patronal"]),
            "iece": pct(e["iece"]), "secap": pct(e["secap"]), "iece_secap": pct(iece_secap),
            "hay_iece_secap": bool(iece_secap),
            # solo los aportes adicionales que se cobran: "SECAP 0,5%" o "IECE 0,5% + SECAP 0,5%"
            "adicionales": " + ".join(f"{n} {pct(e[k])}" for n, k in (("IECE", "iece"), ("SECAP", "secap"))
                                      if Decimal(str(e[k]))),
            "patronal_total": pct(Decimal(str(e["iess_patronal"])) + iece_secap), "fondos": pct(e["fondos"]),
            "dias_vacaciones": int(e["dias_vacaciones"]), "vac_divisor": 360 // int(e["dias_vacaciones"]),
            "f_sup": float(e["recargo_sup"]), "f_ext": float(e["recargo_ext"]),
            "recargo_sup": pct((Decimal(str(e["recargo_sup"])) - 1) * 100),
            "recargo_ext": pct((Decimal(str(e["recargo_ext"])) - 1) * 100),
            "canasta": cifra(e["canasta"]), "canastas": calculos.CANASTAS_POR_CARGAS,
            "canastas_cat": calculos.CANASTAS_CATASTROFICA}


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


@app.template_filter("fecha")
def fecha(iso):
    """'2026-10-19' → '19 oct 2026'."""
    d = date.fromisoformat(iso)
    return f"{d.day} {MESES[d.month][:3].lower()} {d.year}"


@app.before_request
def solo_lectura():
    """Con EDIT_PASSWORD, cualquier POST que cambie datos exige haber ingresado la clave."""
    if (EDIT_PASSWORD and request.method == "POST" and not session.get("editor")
            and request.endpoint not in ("login", "rol_preview")):  # la vista previa solo calcula
        flash("Esta es una versión de solo lectura. Ingresa la clave de edición para hacer cambios.", "warning")
        return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if not EDIT_PASSWORD:
        return redirect(url_for("resumen"))
    if request.method == "POST":
        if hmac.compare_digest(request.form.get("clave", ""), EDIT_PASSWORD):
            session["editor"] = True
            flash("Modo edición activado.", "success")
            return redirect(url_for("resumen"))
        flash("Clave incorrecta.", "danger")
    return render_template("login.html")


@app.get("/logout")
def logout():
    session.pop("editor", None)
    return redirect(url_for("resumen"))


@app.context_processor
def globales():
    return dict(EMPRESA=empresa(), REG=empresa()["reg"], REGIMENES=calculos.REGIMENES, MESES=MESES,
                SOLO_LECTURA=bool(EDIT_PASSWORD) and not session.get("editor"), PUBLICADO=bool(EDIT_PASSWORD),
                P=vista_params())


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
    empleados = filas("SELECT * FROM empleados ORDER BY activo DESC, reporta_a IS NOT NULL, apellidos")
    nombres = {e["id"]: f'{e["nombres"]} {e["apellidos"]}' for e in empleados}
    for e in empleados:
        e["antiguedad"] = antiguedad(e["fecha_ingreso"])
        e["jefe"] = nombres.get(e["reporta_a"], "")
        e["avisos"] = calculos.revisar_escala(Decimal(str(e["sueldo"])), e["estructura"], params())
    return render_template("empleados.html", empleados=empleados)


@app.get("/empleados/nuevo")
def empleado_nuevo():
    return render_template("empleado_form.html", **form_ctx(None, []))


@app.get("/empleados/<int:id>/editar")
def empleado_editar(id):
    e = filas("SELECT * FROM empleados WHERE id = ?", (id,))
    if not e:
        flash("Empleado no encontrado.", "danger")
        return redirect(url_for("empleados_lista"))
    return render_template("empleado_form.html", **form_ctx(e[0], []))


def genera_ciclo(empleado_id, jefe_id):
    """True si poner a jefe_id como jefe de empleado_id cierra un ciclo (el jefe ya depende del empleado)."""
    jefes = {r["id"]: r["reporta_a"] for r in filas("SELECT id, reporta_a FROM empleados")}
    actual = jefe_id
    while actual is not None:
        if actual == empleado_id:
            return True
        actual = jefes.get(actual)
    return False


def form_ctx(e, errores):
    """Contexto común del formulario de empleado (listas para los select)."""
    otros = filas("SELECT id, nombres, apellidos, cargo FROM empleados WHERE id != ? ORDER BY apellidos",
                  (int(e["id"]) if e and e.get("id") else 0,))
    departamentos = empresa()["departamentos"]
    if e and e.get("departamento") and e["departamento"] not in departamentos:
        departamentos = departamentos + [e["departamento"]]   # departamento que ya no está en Parámetros
    return dict(e=e, errores=errores, tipos_contrato=empresa()["reg"]["contratos"], departamentos=departamentos,
                jefes=otros, escala=escala_actual())


@app.post("/empleados/guardar")
def empleado_guardar():
    f = request.form
    e = {k: f.get(k, "").strip() for k in
         ("id", "cedula", "nombres", "apellidos", "cargo", "sueldo", "fecha_ingreso", "tipo_contrato",
          "gastos_personales", "cargas", "departamento", "reporta_a", "funcion", "estructura")}
    for k in ("activo", "mensualiza_13", "mensualiza_14", "mensualiza_fondos", "catastrofica"):
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
    if e["tipo_contrato"] not in empresa()["reg"]["contratos"]:
        errores.append(f"Tipo de contrato inválido para el régimen {empresa()['reg']['nombre']}.")
    try:
        numero(e["gastos_personales"])
        if not 0 <= int(e["cargas"] or 0) <= 20:
            raise ValueError
    except ValueError:
        errores.append("Gastos personales y cargas familiares deben ser números ≥ 0.")
    if not e["departamento"]:
        errores.append("Elige un departamento.")
    if e["estructura"] and e["estructura"] not in params()["escala"]:
        errores.append("Esa escala no existe en el régimen actual.")
    if e["reporta_a"] and e["reporta_a"] == e["id"]:
        errores.append("Un empleado no puede reportarse a sí mismo.")
    elif e["reporta_a"] and e["id"] and genera_ciclo(int(e["id"]), int(e["reporta_a"])):
        errores.append("Esa línea de reporte crea un ciclo en el organigrama.")

    if not errores:
        campos = CAMPOS_EMPLEADO + ("activo",)
        valores = [e[k] for k in campos]
        valores[campos.index("sueldo")] = float(numero(e["sueldo"]))
        valores[campos.index("gastos_personales")] = float(numero(e["gastos_personales"]))
        valores[campos.index("cargas")] = int(e["cargas"] or 0)
        valores[campos.index("reporta_a")] = int(e["reporta_a"]) if e["reporta_a"] else None
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

    return render_template("empleado_form.html", **form_ctx(e, errores))


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
    elif (db().execute("SELECT 1 FROM paz_expedientes WHERE empleado_id = ? LIMIT 1", (id,)).fetchone()
          or db().execute("SELECT 1 FROM paz_revisiones WHERE responsable_id = ? LIMIT 1", (id,)).fetchone()):
        flash("No se puede eliminar: tiene un expediente de paz y salvo. Inactívalo en su lugar.", "warning")
    elif db().execute("SELECT 1 FROM empleados WHERE reporta_a = ? LIMIT 1", (id,)).fetchone():
        flash("No se puede eliminar: otros cargos le reportan. Cambia primero su jefe inmediato.", "warning")
    else:
        with db():
            db().execute("DELETE FROM empleados WHERE id = ?", (id,))
        flash("Empleado eliminado.", "success")
    return redirect(url_for("empleados_lista"))


# ------------------------------------------------------------------ roles de pago
@app.get("/roles")
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


def novedades_de(f, e):
    """Lee del formulario las novedades de un empleado (inputs dias_<id>, h50_<id>, ...)."""
    i = e["id"]
    dias = int(numero(f.get(f"dias_{i}"), "30"))
    if not 1 <= dias <= 30:
        raise ValueError(f"días de {e['nombres']}")
    return dict(dias=dias, h50=numero(f.get(f"h50_{i}")), h100=numero(f.get(f"h100_{i}")),
                comisiones=numero(f.get(f"com_{i}")), anticipos=numero(f.get(f"ant_{i}")),
                prestamos_iess=numero(f.get(f"pre_{i}")))


@app.post("/roles/preview")
def rol_preview():
    """Vista previa en vivo: mismo cálculo que el rol definitivo, sin guardar nada."""
    f = request.form
    anio, mes = int(f["anio"]), int(f["mes"])
    salida = {}
    for e in filas("SELECT * FROM empleados WHERE activo = 1"):
        try:
            r = calculos.calcular_rol(e, novedades_de(f, e), anio, mes, params())
            salida[e["id"]] = {k: r[k] for k in ("total_ingresos", "total_descuentos", "ir", "neto", "costo_total")}
        except ValueError:
            salida[e["id"]] = None  # fila con un valor inválido: la página la marca
    return salida


@app.post("/roles/generar")
def rol_generar():
    f = request.form
    anio, mes = int(f["anio"]), int(f["mes"])
    empleados = filas("SELECT * FROM empleados WHERE activo = 1")

    detalles = []
    try:
        for e in empleados:
            detalles.append({"empleado_id": e["id"], **calculos.calcular_rol(e, novedades_de(f, e), anio, mes, params())})
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
        # planilla IESS = lo que se transfiere al IESS: aporte personal + patronal + adicionales (SECAP)
        total_iess=total("iess_personal") + total("patronal") + total("iece_secap"),
        regimen=empresa()["regimen"], params=json.dumps(vista_params()))
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


def params_rol(cab):
    """Porcentajes con los que se generó el rol (no los actuales): el histórico no cambia."""
    return {**vista_params(), **json.loads(cab["params"]), "canastas": calculos.CANASTAS_POR_CARGAS}


@app.get("/roles/<int:id>")
def rol_ver(id):
    cab = filas("SELECT * FROM roles_cabecera WHERE id = ?", (id,))
    if not cab:
        flash("Rol no encontrado.", "danger")
        return redirect(url_for("roles_lista"))
    detalles = filas("SELECT * FROM roles_detalle WHERE rol_id = ? ORDER BY nombre", (id,))
    return render_template("rol_ver.html", cab=cab[0], detalles=detalles, P=params_rol(cab[0]))


@app.get("/roles/<int:id>/empleado/<int:det_id>")
def rol_individual(id, det_id):
    cab = filas("SELECT * FROM roles_cabecera WHERE id = ?", (id,))
    d = filas("SELECT * FROM roles_detalle WHERE id = ? AND rol_id = ?", (det_id, id))
    if not (cab and d):
        flash("Rol individual no encontrado.", "danger")
        return redirect(url_for("roles_lista"))
    # anterior / siguiente en el mismo orden que el consolidado
    orden = filas("SELECT id, nombre FROM roles_detalle WHERE rol_id = ? ORDER BY nombre", (id,))
    pos = next(i for i, o in enumerate(orden) if o["id"] == det_id)
    nav = dict(pos=pos + 1, total=len(orden),
               anterior=orden[pos - 1] if pos > 0 else None,
               siguiente=orden[pos + 1] if pos + 1 < len(orden) else None)
    return render_template("rol_individual.html", cab=cab[0], d=d[0], nav=nav, P=params_rol(cab[0]))


@app.get("/roles/<int:id>/excel")
def rol_excel(id):
    """Libro .xlsx con 4 hojas: rol, costo empleador, planilla IESS y transferencias bancarias."""
    cab = filas("SELECT * FROM roles_cabecera WHERE id = ?", (id,))
    if not cab:
        flash("Rol no encontrado.", "danger")
        return redirect(url_for("roles_lista"))
    cab = cab[0]
    detalles = filas("SELECT * FROM roles_detalle WHERE rol_id = ? ORDER BY nombre", (id,))
    contenido = exportar.libro_rol(cab, detalles, empresa(), MESES[cab["mes"]], json.loads(cab["params"]))
    nombre = f"rol_{cab['anio']}_{cab['mes']:02d}_{MESES[cab['mes']].lower()}.xlsx"
    return send_file(io.BytesIO(contenido), as_attachment=True, download_name=nombre,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.post("/roles/<int:id>/eliminar")
def rol_eliminar(id):
    with db():
        db().execute("DELETE FROM roles_cabecera WHERE id = ?", (id,))
    flash("Rol eliminado.", "success")
    return redirect(url_for("roles_lista"))


# ------------------------------------------------------------------ organigrama y tabla de remuneraciones
def estructura_organizacional():
    """Árbol de cargos (empleados activos) y tabla de remuneraciones por cargo, con el mismo cálculo del rol."""
    hoy, p = date.today(), params()
    empleados = filas("SELECT * FROM empleados WHERE activo = 1 ORDER BY id")
    activos = {e["id"] for e in empleados}

    # Árbol: un empleado es raíz si no reporta a nadie o su jefe ya no está activo.
    hijos = {}
    for e in empleados:
        e["grado"] = p["escala"].get(e["estructura"], ("", 0))
        e["avisos"] = calculos.revisar_escala(Decimal(str(e["sueldo"])), e["estructura"], p)
        hijos.setdefault(e["reporta_a"] if e["reporta_a"] in activos else None, []).append(e)

    def rama(e, nivel=1):
        return dict(e=e, nivel=nivel, jefe=e["reporta_a"] in activos,
                    hijos=[rama(h, nivel + 1) for h in hijos.get(e["id"], [])])
    raices = [rama(e) for e in hijos.get(None, [])]

    # Tabla: una fila por cargo y sueldo (si dos personas comparten cargo y sueldo, se suman como n = 2).
    tabla = {}
    for e in empleados:
        r = calculos.calcular_rol(e, dict(dias=30), hoy.year, hoy.month, p)
        fila = tabla.setdefault((e["cargo"], e["sueldo"]), dict(
            cargo=e["cargo"], departamento=e["departamento"], sueldo=e["sueldo"], codigo=e["estructura"],
            estructura=f'{e["estructura"]} · {e["grado"][0]}' if e["grado"][0] else "",
            minimo=float(e["grado"][1]), avisos=e["avisos"],
            n=0, sueldo_total=0, iess_personal=0, patronal=0, p13=0, p14=0, p_vac=0, p_fondos=0, costo=0,
            fondos_futuros=0))
        fila["n"] += 1
        fondos_futuros = 0 if r["tiene_fondos"] else float(calculos.r2(Decimal(str(r["total_gravado"])) * p["fondos"]))
        for k, v in (("sueldo_total", r["sueldo_ganado"]), ("iess_personal", r["iess_personal"]),
                     ("patronal", r["patronal"] + r["iece_secap"]), ("p13", r["p13"]), ("p14", r["p14"]),
                     ("p_vac", r["p_vac"]), ("p_fondos", r["p_fondos"]), ("costo", r["costo_total"]),
                     ("fondos_futuros", fondos_futuros)):
            fila[k] = round(fila[k] + v, 2)
    tabla = list(tabla.values())
    return dict(raices=raices, tabla=tabla, anio=hoy.year, mes=hoy.month, empleados=empleados,
                costo_personal=round(sum(t["costo"] for t in tabla), 2),
                fondos_futuros=round(sum(t["fondos_futuros"] for t in tabla), 2),
                ingreso=min((e["fecha_ingreso"] for e in empleados), default=None))


@app.get("/organigrama")
def organigrama():
    return render_template("organigrama.html", **estructura_organizacional())


@app.get("/organigrama/excel")
def organigrama_excel():
    """Tabla de remuneraciones con fórmulas vivas (PEA 3): cambia sueldo o n.º y todo se recalcula."""
    datos = estructura_organizacional()
    contenido = exportar.libro_remuneraciones(datos["tabla"], empresa(), params(), vista_params())
    nombre = "".join(c for c in empresa()["nombre"].lower() if c.isalnum())[:30] or "empresa"
    return send_file(io.BytesIO(contenido), as_attachment=True, download_name=f"tabla_remuneraciones_{nombre}.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ------------------------------------------------------------------ resumen (dashboard)
DIA_SRI = {1: 10, 2: 12, 3: 14, 4: 16, 5: 18, 6: 20, 7: 22, 8: 24, 9: 26, 0: 28}  # por el 9.º dígito del RUC


def obligaciones(hoy, e):
    """Próximos vencimientos de nómina: IESS, SRI, décimos, utilidades y formulario 107."""
    ruc = e["ruc"]
    dia_sri = DIA_SRI[int(ruc[8])] if len(ruc) >= 9 and ruc[8].isdigit() else 28
    eventos = []
    for k in range(14):
        anio, mes = hoy.year + (hoy.month - 1 + k) // 12, (hoy.month - 1 + k) % 12 + 1
        ant = MESES[12 if mes == 1 else mes - 1].lower()
        eventos += [
            (date(anio, mes, 15), "Planilla de aportes IESS", f"Aportes personal y patronal de {ant}", "costo"),
            (date(anio, mes, dia_sri), "Retenciones en la fuente · SRI",
             f"Formulario 103 de {ant} (día {dia_sri} por el 9.º dígito del RUC)", "desc"),
        ]
        if mes == 12:
            eventos.append((date(anio, 12, 24), "Pago del décimo tercero",
                            "A quienes lo acumulan: lo percibido de diciembre a noviembre ÷ 12", "neto"))
        if mes == (8 if e["region"] in ("Sierra", "Amazonía") else 3):
            eventos.append((date(anio, mes, 15), "Pago del décimo cuarto",
                            f"Región {e['region']}: un SBU proporcional al tiempo trabajado", "neto"))
        if mes == 4 and e["regimen"] == "CT":
            eventos.append((date(anio, 4, 15), "Participación de utilidades (15 %)",
                            "Código del Trabajo, art. 97 y 105", "neto"))
        if mes == 1:
            eventos.append((date(anio, 1, 31), "Entregar formulario 107",
                            "Comprobante anual de retenciones a cada trabajador", "desc"))
    return sorted((ev for ev in eventos if ev[0] >= hoy), key=lambda ev: ev[0])[:6]


@app.get("/")
def resumen():
    hoy = date.today()
    org = estructura_organizacional()
    roles = filas("SELECT * FROM roles_cabecera ORDER BY anio DESC, mes DESC LIMIT 6")[::-1]

    por_dep = {}
    for t in org["tabla"]:
        d = por_dep.setdefault(t["departamento"], dict(nombre=t["departamento"] or "Sin departamento", n=0, costo=0))
        d["n"] += t["n"]
        d["costo"] = round(d["costo"] + t["costo"], 2)
    por_dep = sorted(por_dep.values(), key=lambda d: -d["costo"])

    tabla = org["tabla"]
    composicion = dict(sueldos=sum(t["sueldo_total"] for t in tabla), patronal=sum(t["patronal"] for t in tabla),
                       provisiones=sum(t["p13"] + t["p14"] + t["p_vac"] + t["p_fondos"] for t in tabla))

    # Fondos de reserva: quién cumple un año en los próximos 90 días (desde el mes 13 el costo sube).
    proximos_fondos = []
    for emp in org["empleados"]:
        ini = date.fromisoformat(emp["fecha_ingreso"])
        aniversario = date(ini.year + 1, ini.month, min(ini.day, 28))
        if 0 <= (aniversario - hoy).days <= 90:
            proximos_fondos.append(dict(e=emp, fecha=aniversario.isoformat()))

    alertas = [dict(e=emp, aviso=a) for emp in org["empleados"] for a in emp["avisos"]]
    return render_template("resumen.html", org=org, roles=roles, por_dep=por_dep, composicion=composicion,
                           alertas=alertas, proximos_fondos=proximos_fondos, obligaciones=obligaciones(hoy, empresa()),
                           hoy=hoy, n_escala=len(params()["escala"]))


# ------------------------------------------------------------------ parámetros
LOGO_TIPOS = {b"\x89PNG": "image/png", b"\xff\xd8\xff": "image/jpeg", b"RIFF": "image/webp"}


def render_parametros(errores=(), form=None):
    e = empresa()
    return render_template("parametros.html", campos=CAMPOS_CALCULO, regiones=REGIONES, errores=errores, form=form,
                           legales=valores_legales(e["regimen"]), tabla_ir=calculos.TABLA_IR_2026)


@app.route("/parametros", methods=["GET", "POST"])
def parametros():
    if request.method == "GET":
        return render_parametros()
    e, f = empresa(), request.form
    nuevos = {k: f.get(k, "").strip() for k in ("nombre", "ruc", "actividad", "region", "regimen", "cliente",
                                                "ingreso_mensual", "otros_costos", "departamentos")}
    errores = []
    if not nuevos["nombre"]:
        errores.append("El nombre de la empresa es obligatorio.")
    if not (len(nuevos["ruc"]) == 13 and nuevos["ruc"].isdigit()):
        errores.append("El RUC debe tener 13 dígitos.")
    if nuevos["region"] not in REGIONES or nuevos["regimen"] not in calculos.REGIMENES:
        errores.append("Región o régimen inválido.")
    if not [d for d in nuevos["departamentos"].splitlines() if d.strip()]:
        errores.append("Define al menos un departamento.")
    try:
        for k in ("ingreso_mensual", "otros_costos"):
            nuevos[k] = str(numero(nuevos[k]))
    except ValueError:
        errores.append("Ingreso mensual y otros costos deben ser números ≥ 0.")

    cambia_regimen = nuevos["regimen"] != e["regimen"]
    if cambia_regimen or "restablecer" in f:
        nuevos.update(valores_legales(nuevos["regimen"]))   # porcentajes legales del régimen; luego se ajustan
    else:
        for k, etiqueta, tipo in CAMPOS_CALCULO:
            try:
                v = numero(f.get(k))
                fuera = {"usd": v <= 0, "pct": v > 100, "factor": v < 1, "dias": not 1 <= v <= 60}.get(tipo, False)
                if fuera:
                    raise ValueError
                nuevos[k] = str(int(v) if tipo == "dias" else v)
            except ValueError:
                errores.append(f"{etiqueta}: valor inválido.")
    if errores:
        return render_parametros(errores, f)
    with db():
        db().executemany("INSERT OR REPLACE INTO parametros VALUES (?, ?)", nuevos.items())
    if cambia_regimen:
        codigos = {x["codigo"] for x in escala_actual(nuevos["regimen"])}
        sin_grado = sum(1 for x in filas("SELECT estructura FROM empleados WHERE activo = 1")
                        if x["estructura"] not in codigos)
        flash(f"Régimen cambiado a {calculos.REGIMENES[nuevos['regimen']]['nombre']}: se cargaron sus porcentajes "
              "legales y su escala salarial."
              + (f" {sin_grado} empleado(s) deben elegir su grado en la nueva escala (Empleados → Editar)."
                 if sin_grado else ""), "warning")
    else:
        flash("Parámetros guardados. Los roles ya generados conservan los valores con que se calcularon.", "success")
    return redirect(url_for("parametros"))


@app.post("/parametros/logo")
def parametros_logo():
    if "quitar" in request.form:
        datos, mime = "", ""
    else:
        archivo = request.files.get("logo")
        contenido = archivo.read() if archivo else b""
        mime = next((m for firma, m in LOGO_TIPOS.items() if contenido.startswith(firma)), None)
        if not mime and contenido.lstrip()[:5].lower() in (b"<svg ", b"<?xml", b"<svg>", b"<svg\n"):
            mime = "image/svg+xml"
        if not contenido or not mime or len(contenido) > 512 * 1024:
            flash("Sube un logo PNG, JPG, WEBP o SVG de hasta 512 KB.", "danger")
            return redirect(url_for("parametros"))
        datos = base64.b64encode(contenido).decode()
    with db():
        db().executemany("INSERT OR REPLACE INTO parametros VALUES (?, ?)", [("logo", datos), ("logo_mime", mime)])
    flash("Logo actualizado." if datos else "Se restauró el logo por defecto.", "success")
    return redirect(url_for("parametros"))


@app.get("/logo")
def logo():
    e = empresa()
    if not e["logo"]:
        return redirect(url_for("static", filename="logo.svg"))
    r = send_file(io.BytesIO(base64.b64decode(e["logo"])), mimetype=e["logo_mime"], max_age=0)
    # un SVG subido no puede ejecutar scripts aunque se abra directo en el navegador
    r.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'"
    r.headers["X-Content-Type-Options"] = "nosniff"
    return r


# ------------------------------------------------------------------ escalas salariales
@app.get("/escalas")
def escalas():
    regimen = request.args.get("regimen", empresa()["regimen"])
    if regimen not in calculos.REGIMENES:
        regimen = empresa()["regimen"]
    uso = {}
    for x in filas("SELECT id, estructura, nombres, apellidos, cargo, sueldo FROM empleados WHERE activo = 1"):
        uso.setdefault(x["estructura"], []).append(x)
    return render_template("escalas.html", regimen=regimen, R=calculos.REGIMENES[regimen],
                           filas=escala_actual(regimen), uso=uso if regimen == empresa()["regimen"] else {},
                           activo=regimen == empresa()["regimen"])


@app.post("/escalas/guardar")
def escalas_guardar():
    f, regimen = request.form, request.form.get("regimen", "")
    if regimen not in calculos.REGIMENES:
        return redirect(url_for("escalas"))
    errores, cambios, borrar = [], [], []
    for x in escala_actual(regimen):
        i = x["id"]
        if f"borrar_{i}" in f:
            borrar.append((i,))
            continue
        try:
            valor = numero(f.get(f"valor_{i}"))
            if valor <= 0:
                raise ValueError
        except ValueError:
            errores.append(f"{x['codigo']}: valor inválido.")
            continue
        cambios.append((f.get(f"denominacion_{i}", "").strip() or x["denominacion"],
                        f.get(f"grupo_{i}", "").strip(), float(valor), i))
    nuevo = {k: f.get(f"nuevo_{k}", "").strip() for k in ("codigo", "denominacion", "grupo", "valor")}
    if any(nuevo.values()):
        try:
            if not (nuevo["codigo"] and nuevo["denominacion"]) or numero(nuevo["valor"]) <= 0:
                raise ValueError
        except ValueError:
            errores.append("Nueva fila: código, denominación y un valor mayor a 0 son obligatorios.")
    if errores:
        for er in errores:
            flash(er, "danger")
        return redirect(url_for("escalas", regimen=regimen))
    try:
        with db():
            db().executemany("UPDATE escalas SET denominacion = ?, grupo = ?, valor = ? WHERE id = ?", cambios)
            db().executemany("DELETE FROM escalas WHERE id = ?", borrar)
            if nuevo["codigo"]:
                db().execute("INSERT INTO escalas (regimen, codigo, denominacion, grupo, valor) VALUES (?, ?, ?, ?, ?)",
                             (regimen, nuevo["codigo"].upper(), nuevo["denominacion"], nuevo["grupo"],
                              float(numero(nuevo["valor"]))))
    except sqlite3.IntegrityError:
        flash(f"Ya existe el código {nuevo['codigo'].upper()} en esta escala.", "danger")
    else:
        flash("Escala guardada.", "success")
    return redirect(url_for("escalas", regimen=regimen))


@app.post("/escalas/restaurar")
def escalas_restaurar():
    regimen = request.form.get("regimen", "")
    if regimen in calculos.REGIMENES:
        with db():
            sembrar_escala(db(), regimen)
        flash(f"Se restauró la escala oficial de {calculos.REGIMENES[regimen]['nombre']}.", "success")
    return redirect(url_for("escalas", regimen=regimen))


@app.post("/demo/reiniciar")
def demo_reiniciar():
    """Vuelve a los parámetros y empleados de ejemplo, sin roles (útil antes de cada práctica)."""
    DB_PATH.unlink(missing_ok=True)
    init_db()
    flash("Demo reiniciada: datos de FERIAUTO, 5 empleados de ejemplo y ningún rol generado.", "success")
    return redirect(url_for("resumen"))


init_db()

if __name__ == "__main__":
    # 5050 y no 5000: en macOS el puerto 5000 lo ocupa AirPlay.
    app.run(debug=True, port=int(os.environ.get("PORT", 5050)))
