"""
Motor de cálculo del Rol de Pagos — Ecuador 2026 (versión demostrativa).

Función pura: recibe empleado + novedades del mes y devuelve TODOS los valores
del rol. No toca la base de datos, así se puede probar y explicar aislada.

Flujo de cada rol:
    sueldo ganado + horas extras + comisiones  = TOTAL GRAVADO (aporta al IESS y paga IR)
    + décimos / fondos mensualizados           = NO GRAVADO   (no aporta ni paga IR)
    = TOTAL INGRESOS
    − IESS personal − retención IR − anticipos − préstamos IESS = TOTAL DESCUENTOS
    = NETO A RECIBIR
    Costo empleador = gravado + provisiones (13°, 14°, vacaciones, fondos de reserva)
                      + aporte patronal (+ SECAP en el sector privado)

Los porcentajes, vacaciones, recargos de horas extra y la escala salarial dependen del régimen
laboral (REGIMENES: Código del Trabajo, LOSEP, LOEP, LOES) y llegan en el dict `p`.

Ejecuta `python calculos.py` para correr el self-check con casos resueltos a mano.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import calendar

# ---------------------------------------------------------------- parámetros generales 2026
SBU = Decimal("482")                 # Salario Básico Unificado 2026 (Acuerdo MDT-2025-195)
FONDOS_RESERVA = Decimal("0.0833")   # 8,33% (≈ 1/12), desde el mes 13 (CT art. 196; LOSEP art. 99)
HORAS_MES = Decimal("240")           # 40 h/semana × 4 semanas → valor hora = sueldo / 240

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
CANASTAS_CATASTROFICA = 100   # enfermedad catastrófica, rara o huérfana del trabajador o de una carga

# ---------------------------------------------------------------- regímenes laborales
# Lo que cambia según la ley que rige a la entidad. Los porcentajes son los valores legales por defecto;
# la empresa puede ajustarlos en Parámetros (p. ej. si cambia una resolución del IESS).
#   regla de la escala: "minimo" → el sueldo no puede ser menor al de la escala (CT, salarios sectoriales)
#                       "fija"   → la remuneración es la del grado (LOSEP, LOES)
#                       "techo"  → la escala es un máximo que fija el directorio (LOEP)
REGIMENES = {
    "CT": dict(
        nombre="Código del Trabajo", sector="Sector privado",
        # IECE: el instituto se suprimió en 2015 y el MDT informó en 2025 que su 0,5 % se eliminó con la
        # reforma al Código Monetario → 0 por defecto (editable si se vuelve a cobrar). SECAP 0,5 % sigue.
        iess_personal="9.45", iess_patronal="11.15", iece="0", secap="0.5",
        dias_vacaciones=15, recargo_sup="1.5", recargo_ext="2", regla="minimo",
        escala="Salarios mínimos sectoriales", columna="Mínimo sectorial",
        contratos=["Indefinido", "Plazo fijo", "Eventual", "Ocasional", "Por obra o servicio", "Jornada parcial"],
        nota="Trabajadores privados. Sueldo ≥ mínimo sectorial de su estructura ocupacional (y ≥ SBU). "
             "Vacaciones 15 días al año (CT art. 69); horas suplementarias +50 % y extraordinarias +100 % (art. 55). "
             "Con jornada distribuida (hasta 10 h diarias, Acuerdo MDT-2026-059) solo hay recargo sobre 40 h semanales."),
    "LOSEP": dict(
        nombre="LOSEP", sector="Sector público",
        iess_personal="11.45", iess_patronal="9.15", iece="0", secap="0",
        dias_vacaciones=30, recargo_sup="1.25", recargo_ext="1.6", regla="fija",
        escala="Escala de remuneraciones del sector público", columna="RMU del grado",
        contratos=["Nombramiento permanente", "Nombramiento provisional", "Libre nombramiento y remoción",
                   "Servicios ocasionales"],
        nota="Servidores públicos (Ley Orgánica del Servicio Público). La remuneración mensual unificada es la del "
             "grado de la escala del MDT. Vacaciones 30 días (art. 29); horas suplementarias +25 % y "
             "extraordinarias +60 % (art. 114). Aportes IESS 11,45 % personal y 9,15 % patronal (C.D. 501); "
             "los GAD y entidades descentralizadas aportan 11,15 % patronal: ajústalo en Parámetros. Sin IECE ni SECAP."),
    "LOEP": dict(
        nombre="LOEP", sector="Empresas públicas",
        iess_personal="11.45", iess_patronal="9.15", iece="0", secap="0",
        dias_vacaciones=30, recargo_sup="1.25", recargo_ext="1.6", regla="techo",
        escala="Escala de la empresa pública (techos)", columna="Techo del grado",
        contratos=["Libre designación y remoción", "Nombramiento", "Contrato ocasional", "Obrero (Código del Trabajo)"],
        nota="Ley Orgánica de Empresas Públicas: el directorio aprueba la escala de remuneraciones (art. 17) sin "
             "superar los techos del MDT. Supletoriamente se aplica la LOSEP; los obreros se rigen por el CT."),
    "LOES": dict(
        nombre="LOES", sector="Educación superior pública",
        iess_personal="11.45", iess_patronal="9.15", iece="0", secap="0",
        dias_vacaciones=30, recargo_sup="1.25", recargo_ext="1.6", regla="minimo",
        escala="Escalafón del personal académico", columna="Mínimo de la categoría",
        contratos=["Titular (nombramiento)", "No titular ocasional", "Invitado", "Honorario"],
        nota="Personal académico de universidades y escuelas politécnicas públicas (LOES y Reglamento de Carrera "
             "y Escalafón del Profesor del CES). Cada universidad fija la remuneración entre el mínimo y el máximo "
             "referencial del CES para la categoría; supletoriamente LOSEP."),
}

# Escalas oficiales que se cargan por defecto (la empresa puede editarlas en Escalas salariales).
# (código, denominación / cargo, grupo, valor mensual)
ESCALAS_BASE = {
    # CT · Comisión sectorial 12 "Tecnología: hardware y software", rama 1 "Informática y actividades conexas"
    # (CIIU J62). Para 2026 el MDT no emitió tabla nueva: rige la 2025 (Acuerdo MDT-2024-301, R.O. 2.º Supl. 708,
    # 20-dic-2024) y solo los valores menores al SBU suben a $482 (MDT-2025-195, disposición general única).
    # B3, C2 y D2 se derivaron de la tabla 2023 × el incremento 2023-2025 (±0,02).
    "CT": [
        ("A1", "Director / jefe de área", "Dirección", "507.37"),
        ("B1", "Supervisor de sistemas, desarrollo, tecnología y proyectos", "Supervisión", "506.67"),
        ("B2", "Arquitecto de software / administrador de base de datos", "Supervisión", "505.97"),
        ("B3", "Analista de I+D / controller de calidad de software", "Supervisión", "505.27"),
        ("C1", "Analista de software, redes o sistemas / programador semi senior", "Técnico", "504.56"),
        ("C2", "Técnico en mantenimiento de computadoras y cableado estructurado", "Técnico", "502.68"),
        ("C3", "Programador junior de software", "Técnico", "500.80"),
        ("D1", "Técnico de help desk", "Operativo", "498.93"),
        ("D2", "Técnico de ensamblaje y mantenimiento de equipos", "Operativo", "497.05"),
        ("E2", "Asistente o auxiliar de sistemas (menor valor de la rama)", "Operativo", "493.29"),
    ],
    # LOSEP · Escala nacional de remuneraciones mensuales unificadas (22 grados) y nivel jerárquico superior
    # (Acuerdo MDT-2024-039, 17-mar-2024). Sin incremento en 2026.
    "LOSEP": [
        ("SPS1", "Servidor público de servicios 1", "Servicios", "527"),
        ("SPS2", "Servidor público de servicios 2", "Servicios", "553"),
        ("SPA1", "Servidor público de apoyo 1", "Apoyo", "585"),
        ("SPA2", "Servidor público de apoyo 2", "Apoyo", "622"),
        ("SPA3", "Servidor público de apoyo 3", "Apoyo", "675"),
        ("SPA4", "Servidor público de apoyo 4", "Apoyo", "733"),
        ("SP1", "Servidor público 1", "Profesional", "817"),
        ("SP2", "Servidor público 2", "Profesional", "901"),
        ("SP3", "Servidor público 3", "Profesional", "986"),
        ("SP4", "Servidor público 4", "Profesional", "1086"),
        ("SP5", "Servidor público 5", "Profesional", "1212"),
        ("SP6", "Servidor público 6", "Profesional", "1412"),
        ("SP7", "Servidor público 7", "Profesional", "1676"),
        ("SP8", "Servidor público 8", "Profesional", "1760"),
        ("SP9", "Servidor público 9", "Profesional", "2034"),
        ("SP10", "Servidor público 10", "Profesional", "2308"),
        ("SP11", "Servidor público 11", "Profesional", "2358"),
        ("SP12", "Servidor público 12", "Profesional", "2408"),
        ("SP13", "Servidor público 13", "Profesional", "2670"),
        ("SP14", "Servidor público 14", "Profesional", "3188"),
        ("SP15", "Servidor público 15", "Profesional", "3848"),
        ("SP16", "Servidor público 16", "Profesional", "4500"),
        ("NJS1", "Nivel jerárquico superior 1", "Jerárquico superior", "2115"),
        ("NJS2", "Nivel jerárquico superior 2", "Jerárquico superior", "2368"),
        ("NJS3", "Nivel jerárquico superior 3", "Jerárquico superior", "2418"),
        ("NJS4", "Nivel jerárquico superior 4", "Jerárquico superior", "2597"),
        ("NJS5", "Nivel jerárquico superior 5", "Jerárquico superior", "3247"),
        ("NJS6", "Nivel jerárquico superior 6", "Jerárquico superior", "3854"),
        ("NJS7", "Nivel jerárquico superior 7", "Jerárquico superior", "4283"),
        ("NJS8", "Nivel jerárquico superior 8", "Jerárquico superior", "4463"),
        ("NJS9", "Nivel jerárquico superior 9", "Jerárquico superior", "4869"),
        ("NJS10", "Nivel jerárquico superior 10", "Jerárquico superior", "5072"),
    ],
    # LOEP · El directorio aprueba su escala; los procesos gobernantes y adjetivos no superan la escala nacional
    # y nadie puede igualar la RMU del Presidente (MDT-2024-039, art. 4). Se cargan esos valores como techo.
    "LOEP": [
        ("SPS1", "Servidor público de servicios 1", "Servicios", "527"),
        ("SPS2", "Servidor público de servicios 2", "Servicios", "553"),
        ("SPA1", "Servidor público de apoyo 1", "Apoyo", "585"),
        ("SPA2", "Servidor público de apoyo 2", "Apoyo", "622"),
        ("SPA3", "Servidor público de apoyo 3", "Apoyo", "675"),
        ("SPA4", "Servidor público de apoyo 4", "Apoyo", "733"),
        ("SP1", "Servidor público 1", "Profesional", "817"),
        ("SP2", "Servidor público 2", "Profesional", "901"),
        ("SP3", "Servidor público 3", "Profesional", "986"),
        ("SP4", "Servidor público 4", "Profesional", "1086"),
        ("SP5", "Servidor público 5", "Profesional", "1212"),
        ("SP6", "Servidor público 6", "Profesional", "1412"),
        ("SP7", "Servidor público 7", "Profesional", "1676"),
        ("SP8", "Servidor público 8", "Profesional", "1760"),
        ("SP9", "Servidor público 9", "Profesional", "2034"),
        ("SP10", "Servidor público 10", "Profesional", "2308"),
        ("SP11", "Servidor público 11", "Profesional", "2358"),
        ("SP12", "Servidor público 12", "Profesional", "2408"),
        ("SP13", "Servidor público 13", "Profesional", "2670"),
        ("SP14", "Servidor público 14", "Profesional", "3188"),
        ("SP15", "Servidor público 15", "Profesional", "3848"),
        ("SP16", "Servidor público 16", "Profesional", "4500"),
        ("NJS1", "Nivel jerárquico superior 1", "Jerárquico superior", "2115"),
        ("NJS2", "Nivel jerárquico superior 2", "Jerárquico superior", "2368"),
        ("NJS3", "Nivel jerárquico superior 3", "Jerárquico superior", "2418"),
        ("NJS4", "Nivel jerárquico superior 4", "Jerárquico superior", "2597"),
        ("NJS5", "Nivel jerárquico superior 5", "Jerárquico superior", "3247"),
        ("NJS6", "Nivel jerárquico superior 6", "Jerárquico superior", "3854"),
        ("NJS7", "Nivel jerárquico superior 7", "Jerárquico superior", "4283"),
        ("NJS8", "Nivel jerárquico superior 8", "Jerárquico superior", "4463"),
        ("NJS9", "Nivel jerárquico superior 9", "Jerárquico superior", "4869"),
        ("NJS10", "Nivel jerárquico superior 10", "Jerárquico superior", "5072"),
    ],
    # LOES · Personal académico titular a tiempo completo: mínimos referenciales del CES para universidades
    # públicas (Reglamento de Carrera y Escalafón, art. 69; RPC-SE-20-No.057-2021). Cada universidad fija su
    # tabla entre el mínimo y el máximo (indicado en el grupo).
    "LOES": [
        ("AUX1", "Profesor auxiliar 1", "Auxiliar · máx. 2.552,68", "1676"),
        ("AUX2", "Profesor auxiliar 2", "Auxiliar · máx. 2.750,67", "1855"),
        ("AGR1", "Profesor agregado 1", "Agregado · máx. 3.193,90", "2034"),
        ("AGR2", "Profesor agregado 2", "Agregado · máx. 3.441,62", "2392"),
        ("AGR3", "Profesor agregado 3", "Agregado · máx. 3.708,55", "2574"),
        ("PRI1", "Profesor principal 1", "Principal · máx. 4.306,13", "2967"),
        ("PRI2", "Profesor principal 2", "Principal · máx. 4.640,11", "3367"),
        ("PRI3", "Profesor principal 3", "Principal · máx. 5.000,00", "3673.79"),
    ],
}


def parametros_defecto(regimen="CT"):
    """Parámetros legales del régimen listos para calcular_rol (Decimal; porcentajes como fracción)."""
    r = REGIMENES[regimen]
    pct = lambda k: Decimal(r[k]) / 100
    return dict(regimen=regimen, sbu=SBU, iess_personal=pct("iess_personal"), iess_patronal=pct("iess_patronal"),
                iece=pct("iece"), secap=pct("secap"), fondos=FONDOS_RESERVA, dias_vacaciones=r["dias_vacaciones"],
                recargo_sup=Decimal(r["recargo_sup"]), recargo_ext=Decimal(r["recargo_ext"]),
                canasta=CANASTA_2026, regla=r["regla"],
                escala={c: (d, Decimal(v)) for c, d, _, v in ESCALAS_BASE[regimen]})


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


def canastas_tope(cargas, catastrofica=False):
    return CANASTAS_CATASTROFICA if catastrofica else CANASTAS_POR_CARGAS[min(int(cargas), 5)]


def rebaja_gastos_personales(gastos_anuales, cargas, canasta=CANASTA_2026, catastrofica=False):
    """Devuelve (rebaja, tope de gastos). La rebaja resta del IMPUESTO, no de la base imponible."""
    tope = canasta * canastas_tope(cargas, catastrofica)
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


def revisar_escala(sueldo, estructura, p):
    """Avisos de la remuneración frente a la escala del régimen (lista vacía si cumple)."""
    nombre = REGIMENES[p["regimen"]]["nombre"]
    if p["regla"] == "minimo" and sueldo < p["sbu"]:
        return [f"Sueldo inferior al SBU 2026 (${p['sbu']}) para jornada completa"]
    if not estructura:
        return [] if p["regla"] == "minimo" else [f"Sin grado asignado en la escala {nombre}"]
    if estructura not in p["escala"]:
        return [f"La escala {estructura} no existe en el régimen {nombre}"]
    valor = p["escala"][estructura][1]
    if p["regla"] == "minimo" and sueldo < valor:
        return [f"Sueldo inferior al mínimo sectorial de su estructura {estructura} (${valor})"]
    if p["regla"] == "fija" and sueldo != valor:
        return [f"Remuneración distinta a la del grado {estructura} (${valor})"]
    if p["regla"] == "techo" and sueldo > valor:
        return [f"Supera el techo del grado {estructura} (${valor})"]
    return []


def calcular_rol(empleado, novedades, anio, mes, p=None):
    """
    empleado:  dict con sueldo, fecha_ingreso ('YYYY-MM-DD'), mensualiza_13, mensualiza_14, mensualiza_fondos,
               gastos_personales (anual proyectado), cargas, estructura (+ datos de identificación)
    novedades: dict con dias, h50 (suplementarias), h100 (extraordinarias), comisiones, anticipos, prestamos_iess
    p:         parámetros del régimen (parametros_defecto() o los guardados por la empresa); por defecto CT
    Devuelve un dict plano listo para guardarse en roles_detalle (floats).
    """
    p = p or parametros_defecto()
    D = lambda k, src=novedades: Decimal(str(src.get(k) or 0))
    sueldo = Decimal(str(empleado["sueldo"]))
    dias = int(novedades.get("dias", 30))
    h50, h100 = D("h50"), D("h100")
    comisiones, anticipos, prestamos_iess = r2(D("comisiones")), r2(D("anticipos")), r2(D("prestamos_iess"))
    gastos_personales, cargas = D("gastos_personales", empleado), int(empleado.get("cargas") or 0)
    catastrofica = int(bool(empleado.get("catastrofica")))

    # ---- 1. INGRESOS GRAVADOS (aportan al IESS y pagan IR)
    sueldo_ganado = r2(sueldo * dias / 30)          # mes comercial de 30 días
    valor_hora = sueldo / HORAS_MES
    v_h50 = r2(h50 * valor_hora * p["recargo_sup"])     # CT ×1,5 · LOSEP ×1,25
    v_h100 = r2(h100 * valor_hora * p["recargo_ext"])   # CT ×2 · LOSEP ×1,6
    total_gravado = sueldo_ganado + v_h50 + v_h100 + comisiones

    # ---- 2. PROVISIONES (beneficios de ley que el empleador acumula cada mes)
    # 13° y vacaciones se calculan sobre TODO lo percibido (incluye extras y comisiones); el 14° sobre el SBU.
    p13 = r2(total_gravado / 12)
    p14 = r2(p["sbu"] / 12 * dias / 30)
    p_vac = r2(total_gravado * p["dias_vacaciones"] / 360)   # 15 días → 1/24 (CT) · 30 días → 1/12 (LOSEP)
    con_fondos = tiene_fondos_reserva(empleado["fecha_ingreso"], anio, mes)
    p_fondos = r2(total_gravado * p["fondos"]) if con_fondos else Decimal("0.00")
    patronal = r2(total_gravado * p["iess_patronal"])
    iece_secap = r2(total_gravado * (p["iece"] + p["secap"]))

    # ---- 3. NO GRAVADOS: lo mensualizado se paga en el rol en vez de acumularse (cada uno a pedido del
    # trabajador; los fondos de reserva se pagan mensualizados salvo que pida acumularlos en el IESS).
    decimo13_pagado = p13 if empleado["mensualiza_13"] else Decimal("0.00")
    decimo14_pagado = p14 if empleado["mensualiza_14"] else Decimal("0.00")
    fondos_pagado = p_fondos if empleado["mensualiza_fondos"] else Decimal("0.00")
    total_no_gravado = decimo13_pagado + decimo14_pagado + fondos_pagado
    total_ingresos = total_gravado + total_no_gravado

    # ---- 4. DESCUENTOS
    iess_personal = r2(total_gravado * p["iess_personal"])
    # Base imponible: el SRI solo deja restar el aporte personal al IESS.
    # SIMPLIFICACIÓN: se proyecta el mes actual × 12 (como si fuera enero); un sistema real reliquida
    # cada mes con lo ya ganado y retenido: (IR proyectado − retenido) / meses restantes.
    base_ir_anual = r2((total_gravado - iess_personal) * 12)
    ir_causado, (ir_desde, _, ir_fb, ir_pct) = impuesto_renta_anual(base_ir_anual)
    rebaja_gp, tope_gp = rebaja_gastos_personales(gastos_personales, cargas, p["canasta"], catastrofica)
    ir_anual = max(ir_causado - rebaja_gp, Decimal("0.00"))   # la rebaja no puede dejar impuesto negativo
    ir = r2(ir_anual / 12)
    total_descuentos = iess_personal + ir + anticipos + prestamos_iess

    # ---- 5. NETO y COSTO EMPLEADOR
    neto = total_ingresos - total_descuentos
    total_provisiones = p13 + p14 + p_vac + p_fondos + patronal + iece_secap
    # El costo no cambia por mensualizar: el 13° pagado hoy o en diciembre cuesta lo mismo.
    costo_total = total_gravado + total_provisiones

    avisos = revisar_escala(sueldo, empleado.get("estructura"), p)
    if h50 > 48:
        avisos.append("Supera 12 h suplementarias por semana (~48 h/mes)")
    if neto < 0:
        avisos.append("Neto negativo: los descuentos superan los ingresos")

    resultado = dict(
        nombre=f'{empleado.get("nombres", "")} {empleado.get("apellidos", "")}'.strip(),
        cedula=empleado.get("cedula", ""), cargo=empleado.get("cargo", ""), sueldo=sueldo,
        dias=dias, h50=h50, h100=h100, comisiones=comisiones, anticipos=anticipos, prestamos_iess=prestamos_iess,
        mensualiza_13=int(bool(empleado["mensualiza_13"])), mensualiza_14=int(bool(empleado["mensualiza_14"])),
        mensualiza_fondos=int(bool(empleado["mensualiza_fondos"])),
        gastos_personales=gastos_personales, cargas=cargas, catastrofica=catastrofica,
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
               mensualiza_13=0, mensualiza_14=0, mensualiza_fondos=0)
    r = calcular_rol(emp, dict(dias=30, h50=10, comisiones=200), 2026, 10)
    esperado = dict(v_h50=93.75, total_gravado=1793.75, iess_personal=169.51, base_ir_anual=19490.88,
                    ir_causado=561.19, rebaja_gp=0, ir=46.77, neto=1577.47, p13=149.48, p14=40.17,
                    p_vac=74.74, p_fondos=149.42, patronal=200.00, iece_secap=8.97, costo_total=2416.53)
    for k, v in esperado.items():
        assert r[k] == v, f"{k}: {r[k]} != {v}"

    # Caso 2: mismo empleado, cobra fondos mensualizados → suben ingresos no gravados y neto; costo igual.
    r2_ = calcular_rol({**emp, "mensualiza_fondos": 1}, dict(dias=30, h50=10, comisiones=200), 2026, 10)
    assert r2_["neto"] == round(1577.47 + 149.42, 2) and r2_["costo_total"] == 2416.53 and r2_["ir"] == 46.77

    # Caso 3: rebaja por gastos personales. $8.000 de gastos con 2 cargas (tope 11 CFB = $9.039,80):
    # rebaja = 18% × 8.000 = 1.440; IR causado 561,19 − 1.440 < 0 → retención 0.
    r = calcular_rol({**emp, "gastos_personales": 8000, "cargas": 2}, dict(dias=30, h50=10, comisiones=200), 2026, 10)
    assert r["rebaja_gp"] == 1440 and r["tope_gp"] == 9039.80 and r["ir"] == 0
    assert rebaja_gastos_personales(Decimal("99999"), 0) == (Decimal("1035.47"), Decimal("5752.60"))  # 7 CFB
    assert rebaja_gastos_personales(Decimal("99999"), 9)[1] == Decimal("16436.00")                     # 20 CFB
    assert rebaja_gastos_personales(Decimal("99999"), 0, catastrofica=True) == (Decimal("14792.40"), Decimal("82180.00"))

    # Caso 5: mismo sueldo en LOSEP: aportes 11,45 % / 9,15 %, sin IECE/SECAP, vacaciones 30 días, extras ×1,25.
    p = parametros_defecto("LOSEP")
    r = calcular_rol({**emp, "estructura": "SP5"}, dict(dias=30, h50=10, comisiones=200), 2026, 10, p)
    assert r["v_h50"] == 78.13 and r["total_gravado"] == 1778.13 and r["iece_secap"] == 0
    assert r["iess_personal"] == 203.6 and r["patronal"] == 162.7 and r["p_vac"] == 148.18
    assert "distinta a la del grado SP5" in r["avisos"]
    assert not calcular_rol({**emp, "sueldo": 1212, "estructura": "SP5"}, dict(dias=30), 2026, 10, p)["avisos"]
    assert "no existe" in calcular_rol({**emp, "estructura": "A1"}, dict(dias=30), 2026, 10, p)["avisos"]
    assert len(ESCALAS_BASE["LOSEP"]) == 32 and len(ESCALAS_BASE["CT"]) == 10

    # Caso 4: sueldo básico → exento de IR; ingresó hace < 1 año → sin fondos de reserva.
    r = calcular_rol(dict(sueldo=482, fecha_ingreso="2026-02-01", mensualiza_13=1, mensualiza_14=1, mensualiza_fondos=1),
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
