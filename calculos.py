"""
Motor de cálculo del Rol de Pagos — Ecuador 2026 (versión demostrativa).

Función pura: recibe empleado + novedades del mes y devuelve TODOS los valores
del rol. No toca la base de datos, así se puede probar y explicar aislada.

Flujo de cada rol:
    sueldo ganado + horas extras + comisiones  = TOTAL GRAVADO (aporta al IESS y paga IR)
    + décimos / fondos mensualizados           = NO GRAVADO   (no aporta ni paga IR)
    = TOTAL INGRESOS
    − IESS personal 9,45% − retención IR − anticipos − préstamos IESS = TOTAL DESCUENTOS
    = NETO A RECIBIR
    Costo empleador = gravado + provisiones (13°, 14°, vacaciones, fondos de reserva)
                      + aporte patronal 11,15% + IECE 0,5% + SECAP 0,5%

Ejecuta `python calculos.py` para correr el self-check con casos resueltos a mano.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import calendar

# ---------------------------------------------------------------- parámetros 2026
SBU = Decimal("482")                 # Salario Básico Unificado 2026
IESS_PERSONAL = Decimal("0.0945")    # aporte del trabajador
IESS_PATRONAL = Decimal("0.1115")    # aporte del empleador (NO incluye IECE/SECAP)
IECE_SECAP = Decimal("0.01")         # IECE 0,5% + SECAP 0,5%, adicionales al 11,15% → costo patronal 12,15%
FONDOS_RESERVA = Decimal("0.0833")   # 8,33% (≈ 1/12), desde el mes 13
HORAS_MES = Decimal("240")           # 40 h/semana × 4 semanas → valor hora = sueldo / 240
RECARGO_50 = Decimal("1.5")          # suplementarias diurnas (hasta 4 h/día, 12 h/semana)
RECARGO_100 = Decimal("2")           # extraordinarias (fines de semana, feriados) y suplementarias 24:00-06:00

# Tabla IR personas naturales 2026 (SRI, Res. NAC-DGERCGC25-00000043)
# (desde, hasta, impuesto sobre la fracción básica, % sobre el excedente)
TABLA_IR_2026 = [
    (Decimal("0"),      Decimal("12208"),  Decimal("0"),     Decimal("0")),
    (Decimal("12208"),  Decimal("15549"),  Decimal("0"),     Decimal("0.05")),
    (Decimal("15549"),  Decimal("20188"),  Decimal("167"),   Decimal("0.10")),
    (Decimal("20188"),  Decimal("26700"),  Decimal("631"),   Decimal("0.12")),
    (Decimal("26700"),  Decimal("35136"),  Decimal("1412"),  Decimal("0.15")),
    (Decimal("35136"),  Decimal("46575"),  Decimal("2678"),  Decimal("0.20")),
    (Decimal("46575"),  Decimal("62005"),  Decimal("4965"),  Decimal("0.25")),
    (Decimal("62005"),  Decimal("82679"),  Decimal("8823"),  Decimal("0.30")),
    (Decimal("82679"),  Decimal("109956"), Decimal("15025"), Decimal("0.35")),
    (Decimal("109956"), None,              Decimal("24572"), Decimal("0.37")),
]

# Rebaja por gastos personales 2026: 18% del menor entre los gastos proyectados y un tope
# en canastas familiares básicas (CFB enero 2026 = $821,80) que crece con las cargas familiares.
CANASTA_2026 = Decimal("821.80")
REBAJA_GP = Decimal("0.18")
CANASTAS_POR_CARGAS = {0: 7, 1: 9, 2: 11, 3: 14, 4: 17, 5: 20}   # 5 o más cargas → 20 canastas

# Salarios mínimos sectoriales (Código del Trabajo): ningún sueldo puede ser menor al mínimo de la
# estructura ocupacional del cargo. Comisión sectorial 12 "Tecnología: hardware y software", rama 1
# "Informática y actividades conexas" (CIIU J62). Para 2026 no se emitió tabla nueva: según el MDT rige la
# tabla 2025 (Acuerdo MDT-2024-301) y los valores menores al SBU suben a $482.
# Un cargo no contemplado no puede ganar menos que el menor valor de su rama (art. 5 del acuerdo).
# código → (descripción, mínimo mensual)
ESCALA_SECTORIAL_2026 = {  # R.O. 2.º Supl. 708 (20-dic-2024), Anexo 1, págs. 64-65
    "A1": ("A1 · Director / jefe de área", Decimal("507.37")),
    "B1": ("B1 · Supervisor de sistemas, desarrollo, tecnología y proyectos", Decimal("506.67")),
    "B2": ("B2 · Analista de calidad de software / administrador de BD", Decimal("505.97")),
    "C1": ("C1 · Analista / programador semi senior de software", Decimal("504.56")),
    "C3": ("C3 · Programador junior de software", Decimal("500.80")),
    "D1": ("D1 · Técnico de help desk", Decimal("498.93")),
    "E2": ("E2 · Menor valor de la rama (cargo no contemplado)", Decimal("493.29")),
}


def minimo_sectorial(estructura):
    return ESCALA_SECTORIAL_2026.get(estructura or "", ("", SBU))[1]


def r2(x):
    """Redondeo contable a centavos (half-up, no el 'redondeo bancario' de round())."""
    return Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def impuesto_renta_anual(base_anual):
    """Devuelve (impuesto causado anual, tramo usado). Impuesto = fracción básica + % × excedente."""
    for tramo in TABLA_IR_2026:
        desde, hasta, impuesto_fb, pct = tramo
        if hasta is None or base_anual <= hasta:
            return r2(impuesto_fb + (base_anual - desde) * pct), tramo
    raise AssertionError("inalcanzable: el último tramo no tiene techo")


def rebaja_gastos_personales(gastos_anuales, cargas):
    """Devuelve (rebaja, tope de gastos). La rebaja resta del IMPUESTO, no de la base imponible."""
    tope = CANASTA_2026 * CANASTAS_POR_CARGAS[min(int(cargas), 5)]
    return r2(min(Decimal(str(gastos_anuales)), tope) * REBAJA_GP), r2(tope)


def tiene_fondos_reserva(fecha_ingreso, anio, mes):
    # ponytail: año cumplido al cierre del mes → 8,33% completo; en la práctica el mes 13 se prorratea por días.
    fin_mes = date(anio, mes, calendar.monthrange(anio, mes)[1])
    return (fin_mes - date.fromisoformat(fecha_ingreso)).days >= 365


def cedula_valida(cedula):
    """Cédula ecuatoriana: 10 dígitos, provincia 01-24 (o 30), tercer dígito < 6, verificador módulo 10."""
    if len(cedula) != 10 or not cedula.isdigit():
        return False
    if not (1 <= int(cedula[:2]) <= 24 or cedula[:2] == "30") or int(cedula[2]) >= 6:
        return False
    suma = 0
    for i, d in enumerate(cedula[:9]):
        p = int(d) * (2 if i % 2 == 0 else 1)
        suma += p - 9 if p > 9 else p
    return (10 - suma % 10) % 10 == int(cedula[9])


def calcular_rol(empleado, novedades, anio, mes):
    """
    empleado:  dict con sueldo, fecha_ingreso ('YYYY-MM-DD'), mensualiza_decimos, mensualiza_fondos,
               gastos_personales (anual proyectado), cargas (+ datos de identificación)
    novedades: dict con dias, h50, h100, comisiones, anticipos, prestamos_iess
    Devuelve un dict plano listo para guardarse en roles_detalle (floats).
    """
    D = lambda k, src=novedades: Decimal(str(src.get(k) or 0))
    sueldo = Decimal(str(empleado["sueldo"]))
    dias = int(novedades.get("dias", 30))
    h50, h100 = D("h50"), D("h100")
    comisiones, anticipos, prestamos_iess = r2(D("comisiones")), r2(D("anticipos")), r2(D("prestamos_iess"))
    gastos_personales, cargas = D("gastos_personales", empleado), int(empleado.get("cargas") or 0)

    # ---- 1. INGRESOS GRAVADOS (aportan al IESS y pagan IR)
    sueldo_ganado = r2(sueldo * dias / 30)          # mes comercial de 30 días
    valor_hora = sueldo / HORAS_MES
    v_h50 = r2(h50 * valor_hora * RECARGO_50)
    v_h100 = r2(h100 * valor_hora * RECARGO_100)
    total_gravado = sueldo_ganado + v_h50 + v_h100 + comisiones

    # ---- 2. PROVISIONES (beneficios de ley que el empleador acumula cada mes)
    # Código del Trabajo: 13° y vacaciones se calculan sobre TODO lo percibido (incluye extras y comisiones);
    # el 14° sobre el SBU, no sobre el sueldo.
    p13 = r2(total_gravado / 12)
    p14 = r2(SBU / 12 * dias / 30)
    p_vac = r2(total_gravado / 24)
    con_fondos = tiene_fondos_reserva(empleado["fecha_ingreso"], anio, mes)
    p_fondos = r2(total_gravado * FONDOS_RESERVA) if con_fondos else Decimal("0.00")
    patronal = r2(total_gravado * IESS_PATRONAL)
    iece_secap = r2(total_gravado * IECE_SECAP)

    # ---- 3. NO GRAVADOS: lo mensualizado se paga en el rol en vez de acumularse.
    # Por ley los fondos de reserva se pagan mensualizados salvo que el trabajador pida acumularlos en el IESS;
    # los décimos se acumulan salvo que el trabajador pida mensualizarlos.
    decimo13_pagado = p13 if empleado["mensualiza_decimos"] else Decimal("0.00")
    decimo14_pagado = p14 if empleado["mensualiza_decimos"] else Decimal("0.00")
    fondos_pagado = p_fondos if empleado["mensualiza_fondos"] else Decimal("0.00")
    total_no_gravado = decimo13_pagado + decimo14_pagado + fondos_pagado
    total_ingresos = total_gravado + total_no_gravado

    # ---- 4. DESCUENTOS
    iess_personal = r2(total_gravado * IESS_PERSONAL)
    # Base imponible: el SRI solo deja restar el aporte personal al IESS.
    # SIMPLIFICACIÓN: se proyecta el mes actual × 12 (como si fuera enero); un sistema real reliquida
    # cada mes con lo ya ganado y retenido: (IR proyectado − retenido) / meses restantes.
    base_ir_anual = r2((total_gravado - iess_personal) * 12)
    ir_causado, (ir_desde, _, ir_fb, ir_pct) = impuesto_renta_anual(base_ir_anual)
    rebaja_gp, tope_gp = rebaja_gastos_personales(gastos_personales, cargas)
    ir_anual = max(ir_causado - rebaja_gp, Decimal("0.00"))   # la rebaja no puede dejar impuesto negativo
    ir = r2(ir_anual / 12)
    total_descuentos = iess_personal + ir + anticipos + prestamos_iess

    # ---- 5. NETO y COSTO EMPLEADOR
    neto = total_ingresos - total_descuentos
    total_provisiones = p13 + p14 + p_vac + p_fondos + patronal + iece_secap
    # El costo no cambia por mensualizar: el 13° pagado hoy o en diciembre cuesta lo mismo.
    costo_total = total_gravado + total_provisiones

    avisos = []
    if sueldo < SBU:
        avisos.append(f"Sueldo inferior al SBU 2026 (${SBU}) para jornada completa")
    elif sueldo < minimo_sectorial(empleado.get("estructura")):
        avisos.append(f"Sueldo inferior al mínimo sectorial 2026 de su cargo (${minimo_sectorial(empleado.get('estructura'))})")
    if h50 > 48:
        avisos.append("Supera 12 h suplementarias por semana (~48 h/mes)")
    if neto < 0:
        avisos.append("Neto negativo: los descuentos superan los ingresos")

    resultado = dict(
        nombre=f'{empleado.get("nombres", "")} {empleado.get("apellidos", "")}'.strip(),
        cedula=empleado.get("cedula", ""), cargo=empleado.get("cargo", ""), sueldo=sueldo,
        dias=dias, h50=h50, h100=h100, comisiones=comisiones, anticipos=anticipos, prestamos_iess=prestamos_iess,
        mensualiza_decimos=int(bool(empleado["mensualiza_decimos"])),
        mensualiza_fondos=int(bool(empleado["mensualiza_fondos"])),
        gastos_personales=gastos_personales, cargas=cargas,
        sueldo_ganado=sueldo_ganado, valor_hora=r2(valor_hora), v_h50=v_h50, v_h100=v_h100,
        total_gravado=total_gravado, decimo13_pagado=decimo13_pagado, decimo14_pagado=decimo14_pagado,
        fondos_pagado=fondos_pagado, total_no_gravado=total_no_gravado, total_ingresos=total_ingresos,
        iess_personal=iess_personal, base_ir_anual=base_ir_anual, ir_causado=ir_causado,
        rebaja_gp=rebaja_gp, tope_gp=tope_gp, ir_anual=ir_anual, ir=ir,
        ir_tramo_desde=ir_desde, ir_impuesto_fb=ir_fb, ir_pct=ir_pct * 100,
        total_descuentos=total_descuentos, neto=neto,
        p13=p13, p14=p14, p_vac=p_vac, p_fondos=p_fondos, patronal=patronal, iece_secap=iece_secap,
        total_provisiones=total_provisiones, costo_total=costo_total,
        tiene_fondos=int(con_fondos), avisos="; ".join(avisos),
    )
    # SQLite no guarda Decimal: se convierte al final, los cálculos ya se hicieron exactos.
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in resultado.items()}


if __name__ == "__main__":
    # Caso 1 (README): sueldo $1.500, 10 h al 50%, comisión $200, > 1 año, acumula fondos, sin gastos personales.
    emp = dict(nombres="María", apellidos="López", sueldo=1500, fecha_ingreso="2024-01-15",
               mensualiza_decimos=0, mensualiza_fondos=0)
    r = calcular_rol(emp, dict(dias=30, h50=10, comisiones=200), 2026, 10)
    esperado = dict(v_h50=93.75, total_gravado=1793.75, iess_personal=169.51, base_ir_anual=19490.88,
                    ir_causado=561.19, rebaja_gp=0, ir=46.77, neto=1577.47, p13=149.48, p14=40.17,
                    p_vac=74.74, p_fondos=149.42, patronal=200.00, iece_secap=17.94, costo_total=2425.50)
    for k, v in esperado.items():
        assert r[k] == v, f"{k}: {r[k]} != {v}"

    # Caso 2: mismo empleado, cobra fondos mensualizados → suben ingresos no gravados y neto; costo igual.
    r2_ = calcular_rol({**emp, "mensualiza_fondos": 1}, dict(dias=30, h50=10, comisiones=200), 2026, 10)
    assert r2_["neto"] == round(1577.47 + 149.42, 2) and r2_["costo_total"] == 2425.50 and r2_["ir"] == 46.77

    # Caso 3: rebaja por gastos personales. $8.000 de gastos con 2 cargas (tope 11 CFB = $9.039,80):
    # rebaja = 18% × 8.000 = 1.440; IR causado 561,19 − 1.440 < 0 → retención 0.
    r = calcular_rol({**emp, "gastos_personales": 8000, "cargas": 2}, dict(dias=30, h50=10, comisiones=200), 2026, 10)
    assert r["rebaja_gp"] == 1440 and r["tope_gp"] == 9039.80 and r["ir"] == 0
    assert rebaja_gastos_personales(Decimal("99999"), 0) == (Decimal("1035.47"), Decimal("5752.60"))  # 7 CFB
    assert rebaja_gastos_personales(Decimal("99999"), 9)[1] == Decimal("16436.00")                     # 20 CFB

    # Caso 4: sueldo básico → exento de IR; ingresó hace < 1 año → sin fondos de reserva.
    r = calcular_rol(dict(sueldo=482, fecha_ingreso="2026-02-01", mensualiza_decimos=1, mensualiza_fondos=1),
                     dict(dias=30, anticipos=50), 2026, 10)
    assert r["ir"] == 0 and r["p_fondos"] == 0 and r["tiene_fondos"] == 0
    assert r["iess_personal"] == 45.55 and r["decimo14_pagado"] == 40.17
    assert r["neto"] == round(482 - 45.55 - 50 + 40.17 + 40.17, 2)   # 13° y 14° mensualizados suman al neto

    # Bordes de la tabla IR y de fondos de reserva.
    assert impuesto_renta_anual(Decimal("12208"))[0] == 0
    assert impuesto_renta_anual(Decimal("15549"))[0] == Decimal("167.05")
    assert tiene_fondos_reserva("2025-10-01", 2026, 10) and not tiene_fondos_reserva("2025-11-01", 2026, 10)
    assert cedula_valida("1710034065") and not cedula_valida("1710034066")
    print("OK: todos los cálculos coinciden con los casos resueltos a mano.")
