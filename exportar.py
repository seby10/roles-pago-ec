"""
Exportación del Rol de Pagos a Excel (.xlsx) con 4 hojas:
Rol de pagos, Costo empleador, Planilla IESS y Transferencias.

Cada hoja se describe con una lista de columnas (título, función que saca el valor de un
detalle, tipo) y `_hoja()` hace el resto. Los totales son fórmulas =SUM() reales de Excel.

Ejecuta `python exportar.py` para correr el self-check.
"""
import io

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

from calculos import TABLA_IR_2026

FILA_TABLA = 5  # encabezados de la tabla; filas 1-3 son el membrete de la empresa
FONDO = PatternFill("solid", fgColor="F2F0EA")
AMARILLO = PatternFill("solid", fgColor="FFF6D6")   # celdas editables
FINO, DOBLE = Side(style="thin"), Side(style="double")


def _texto(c):
    """Datos escritos por el usuario (nombres, cargos...): siempre texto. openpyxl trataría '=...' como fórmula."""
    if isinstance(c.value, str):
        c.data_type = "s"
    return c


def _hoja(wb, titulo, empresa, subtitulo, columnas, detalles, color=None):
    """
    columnas: lista de (título, fn(d) -> valor, tipo) con tipo 'txt' | 'int' | 'num'.
    Si fn devuelve un texto que empieza con '=', es una fórmula y '{r}' se reemplaza por la fila.
    color: (índice de columna, hex) para resaltar la columna más importante de la hoja.
    """
    ws = wb.create_sheet(titulo)
    ws["A1"] = empresa["nombre"]
    _texto(ws["A1"])
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = subtitulo
    ws["A3"] = "Valores en USD"
    ws["A3"].font = Font(italic=True, color="666666")

    ultima = FILA_TABLA + len(detalles)          # última fila de datos
    fila_total = ultima + 1
    for j, (nombre, fn, tipo) in enumerate(columnas, start=1):
        letra = ws.cell(row=1, column=j).column_letter
        verde = color and color[0] == j
        tinte = Font(bold=True, color=color[1]) if verde else Font(bold=True)

        # encabezado
        c = ws.cell(row=FILA_TABLA, column=j, value=nombre)
        c.font, c.fill = tinte, FONDO
        c.border = Border(bottom=FINO)
        c.alignment = Alignment(wrap_text=True, vertical="center",
                                horizontal="left" if tipo == "txt" else "right")

        # datos
        for i, d in enumerate(detalles, start=FILA_TABLA + 1):
            v = fn(d)
            if isinstance(v, str) and v.startswith("="):
                v = v.format(r=i)
            c = ws.cell(row=i, column=j, value=v)
            if tipo == "txt":
                _texto(c)
                c.number_format = "@"            # texto: conserva ceros iniciales (cédulas)
            elif tipo == "int":
                c.number_format = "0"
            else:
                c.number_format = "#,##0.00"
            if verde:
                c.font = Font(color=color[1], bold=True)

        # totales: =SUM(...) solo en columnas numéricas; borde superior simple, inferior doble
        c = ws.cell(row=fila_total, column=j)
        if j == 1:
            c.value = "TOTALES"
        elif tipo == "num":
            c.value = f"=SUM({letra}{FILA_TABLA + 1}:{letra}{ultima})"
            c.number_format = "#,##0.00"
        c.font = tinte
        c.border = Border(top=FINO, bottom=DOBLE)

        ancho = {"Empleado": 30, "Beneficiario": 30, "Cargo": 22, "Concepto": 24, "Cédula": 13}
        ws.column_dimensions[letra].width = ancho.get(nombre, 14)
    ws.row_dimensions[FILA_TABLA].height = 45
    ws.freeze_panes = ws.cell(row=FILA_TABLA + 1, column=3)  # debajo de encabezados, a la derecha de Empleado
    return ws


def libro_rol(cab, detalles, empresa, mes_nombre, P):
    """Devuelve el .xlsx del rol (bytes) listo para enviar con Flask. P: porcentajes con que se generó el rol."""
    anio = cab["anio"]
    sub = f"RUC {empresa['ruc']} · Rol de pagos {mes_nombre} {anio}"
    ced = ("Cédula", lambda d: str(d["cedula"]), "txt")
    emp = ("Empleado", lambda d: d["nombre"], "txt")
    col = lambda titulo, k: (titulo, lambda d: d[k], "num")   # columna numérica simple

    wb = Workbook()
    wb.remove(wb.active)

    _hoja(wb, "Rol de pagos", empresa, sub, [
        ced, emp, ("Cargo", lambda d: d["cargo"], "txt"), ("Días", lambda d: d["dias"], "int"),
        col("Sueldo ganado", "sueldo_ganado"), col("Horas suplementarias", "v_h50"), col("Horas extraordinarias", "v_h100"),
        col("Comisiones", "comisiones"), col("Total gravado", "total_gravado"),
        col("Décimo 13° mensual", "decimo13_pagado"), col("Décimo 14° mensual", "decimo14_pagado"),
        col("Fondos de reserva", "fondos_pagado"), col("Total ingresos", "total_ingresos"),
        col(f"Aporte IESS {P['iess_personal']}", "iess_personal"), col("Retención IR", "ir"),
        col("Anticipos", "anticipos"), col("Préstamo IESS", "prestamos_iess"),
        col("Total descuentos", "total_descuentos"), col("NETO A RECIBIR", "neto"),
    ], detalles, color=(19, "1D6A4E"))

    _hoja(wb, "Costo empleador", empresa, sub, [
        ced, emp, col("Total gravado", "total_gravado"), col("Décimo 13°", "p13"),
        col("Décimo 14°", "p14"), col("Vacaciones", "p_vac"), col("Fondos de reserva", "p_fondos"),
        col(f"Aporte patronal {P['patronal']}", "patronal"), col(P.get("adicionales") or "IECE + SECAP", "iece_secap"),
        col("Total provisiones y aportes", "total_provisiones"), col("COSTO TOTAL", "costo_total"),
    ], detalles, color=(11, "3E4A7C"))

    _hoja(wb, "Planilla IESS", empresa, sub, [
        ced, emp, col("Total gravado (base de aportación)", "total_gravado"),
        col(f"Aporte personal {P['iess_personal']}", "iess_personal"), col(f"Aporte patronal {P['patronal']}", "patronal"),
        col(P.get("adicionales") or "IECE + SECAP", "iece_secap"),
        ("Total a pagar al IESS", lambda d: "=D{r}+E{r}+F{r}", "num"),   # fórmula por fila
        # los fondos solo se depositan en el IESS si el trabajador los acumula (no los mensualiza)
        ("Fondos de reserva a depositar en IESS",
         lambda d: d["p_fondos"] if d["tiene_fondos"] and not d["mensualiza_fondos"] else 0, "num"),
    ], detalles)

    _hoja(wb, "Transferencias", empresa, sub, [
        ced, ("Beneficiario", lambda d: d["nombre"], "txt"), col("Valor a transferir", "neto"),
        ("Concepto", lambda d: f"Rol {mes_nombre} {anio}", "txt"),
    ], detalles)

    wb.active = 0                                 # hoja activa: "Rol de pagos"
    wb.properties.title = wb.properties.creator = empresa["nombre"]
    salida = io.BytesIO()
    wb.save(salida)
    return salida.getvalue()


def _membrete(ws, empresa):
    """Encabezado de 3 filas: empresa, RUC y régimen."""
    ws["A1"] = empresa["nombre"]
    _texto(ws["A1"]).font = Font(bold=True, size=14)
    ws["A2"] = f"RUC {empresa['ruc']}"
    ws["A3"] = f"Régimen: {empresa.get('reg', {}).get('nombre', 'Código del Trabajo')} · Tabla de remuneraciones 2026"
    ws["A3"].font = Font(italic=True, color="666666")


def _encabezados(ws, fila, titulos, anchos):
    """Fila de títulos en negrita con fondo #F2F0EA y el ancho de cada columna."""
    for j, (t, ancho) in enumerate(zip(titulos, anchos), start=1):
        c = ws.cell(row=fila, column=j, value=t)
        c.font, c.fill, c.border = Font(bold=True), FONDO, Border(bottom=FINO)
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="left" if j == 1 else "center")
        ws.column_dimensions[c.column_letter].width = ancho
    ws.row_dimensions[fila].height = 45


def libro_remuneraciones(tabla, empresa, p, P):
    """
    Devuelve el .xlsx (bytes) de la tabla de remuneraciones con FÓRMULAS vivas (PEA 3, requisito 4):
    al cambiar una remuneración, el n.º de trabajadores o un parámetro, todo se recalcula en Excel.
    p: parámetros de cálculo (Decimal) · P: los mismos como texto para los títulos.
    Hojas: Parámetros (celdas con nombre) · Tabla de remuneraciones · Cálculo detallado (1 trabajador).
    """
    wb = Workbook()

    # ---------------------------------------------------------------- 1. Parámetros
    hp = wb.active
    hp.title = "Parámetros"
    _membrete(hp, empresa)
    hp["A5"] = "Cambie los valores amarillos y todo se recalcula"
    hp["A5"].font = Font(bold=True, color="8A6D00")
    _encabezados(hp, 7, ["Parámetro", "Valor", "Detalle"], [38, 16, 62])
    parametros = [   # (nombre del rango, etiqueta, valor, formato, detalle)
        ("SBU", "Salario Básico Unificado 2026", p["sbu"], "#,##0.00", "Base del décimo 14° (SBU ÷ 12)"),
        ("P_PERSONAL", "Aporte personal IESS", p["iess_personal"], "0.00%", "Se descuenta al trabajador"),
        ("P_PATRONAL", "Aporte patronal IESS", p["iess_patronal"], "0.00%", "Lo paga la empresa"),
        ("P_IECE_SECAP", "Aportes adicionales (IECE + SECAP)", p["iece"] + p["secap"], "0.00%",
         f"Adicional al patronal: total {P['patronal_total']}"),
        ("P_FONDOS", "Fondos de reserva", p["fondos"], "0.00%", "Desde el mes 13 de trabajo"),
        ("DIAS_VACACIONES", "Días de vacaciones al año", p["dias_vacaciones"], "0",
         "Provisión mensual = remuneración × días ÷ 360"),
        ("INGRESO_MENSUAL", "Ingreso mensual del contrato con el GAD", empresa["ingreso_mensual"], "#,##0.00", "USD por mes"),
        ("OTROS_COSTOS", "Otros costos mensuales", empresa["otros_costos"], "#,##0.00", "USD por mes (sin personal)"),
    ]
    for i, (nombre, etiqueta, valor, fmt, detalle) in enumerate(parametros, start=8):
        hp.cell(i, 1, etiqueta)
        c = hp.cell(i, 2, float(valor))
        c.number_format, c.fill, c.border = fmt, AMARILLO, Border(bottom=FINO)
        hp.cell(i, 3, detalle).font = Font(italic=True, color="666666")
        wb.defined_names[nombre] = DefinedName(nombre, attr_text=f"'Parámetros'!$B${i}")

    fila_ir = 8 + len(parametros) + 1
    hp.cell(fila_ir, 1, "Tabla del impuesto a la renta 2026 (personas naturales)").font = Font(bold=True)
    for j, t in enumerate(["Desde", "Hasta", "Impuesto fracción básica", "% sobre el excedente"], start=1):
        c = hp.cell(fila_ir + 1, j, t)
        c.font, c.fill, c.border = Font(bold=True), FONDO, Border(bottom=FINO)
        c.alignment = Alignment(wrap_text=True, horizontal="left" if j == 1 else "right")
    for i, (desde, hasta, imp, pct) in enumerate(TABLA_IR_2026, start=fila_ir + 2):
        for j, (v, fmt) in enumerate([(desde, "#,##0.00"), (hasta, "#,##0.00"), (imp, "#,##0.00"), (pct, "0.00%")], 1):
            c = hp.cell(i, j, "en adelante" if v is None else float(v))
            c.number_format = fmt
            c.alignment = Alignment(horizontal="right")
    ini, fin = fila_ir + 2, fila_ir + 1 + len(TABLA_IR_2026)
    wb.defined_names["TABLA_IR"] = DefinedName("TABLA_IR", attr_text=f"'Parámetros'!$A${ini}:$D${fin}")
    hp.column_dimensions["D"].width = 22
    hp.freeze_panes = "A8"

    # ---------------------------------------------------------------- 2. Tabla de remuneraciones
    t = wb.create_sheet("Tabla de remuneraciones")
    _membrete(t, empresa)
    ini, fin = FILA_TABLA + 1, FILA_TABLA + len(tabla)       # filas de datos
    columna = empresa.get("reg", {}).get("columna", "Mínimo sectorial")
    # sin grado (D = 0) se compara con el SBU; la regla depende del régimen
    cumple = {"minimo": '=IF(F{r}>=MAX(D{r},SBU),"Sí","NO")', "fija": '=IF(OR(D{r}=0,F{r}=D{r}),"Sí","NO")',
              "techo": '=IF(OR(D{r}=0,F{r}<=D{r}),"Sí","NO")'}[p["regla"]]
    tot = fin + 1
    # (título, ancho, formato, valor | fórmula con {r}); E, F y M son las entradas (amarillo)
    cols = [
        ("Cargo", 34, "@", lambda d: d["cargo"]),
        ("Departamento", 18, "@", lambda d: d["departamento"]),
        ("Escala / grado", 34, "@", lambda d: d["estructura"] or ""),
        (columna, 12, "#,##0.00", lambda d: d["minimo"]),
        ("N.º trabajadores", 12, "0", lambda d: d["n"]),
        ("Remuneración mensual", 14, "#,##0.00", lambda d: d["sueldo"]),
        ("¿Cumple la escala?", 11, "General", cumple),
        ("Aporte personal IESS", 13, "#,##0.00", "=ROUND(F{r}*P_PERSONAL,2)"),
        (f"Aporte patronal IESS {P['patronal_total']}", 14, "#,##0.00", "=ROUND(F{r}*P_PATRONAL,2)+ROUND(F{r}*P_IECE_SECAP,2)"),
        ("Décimo 13°", 12, "#,##0.00", "=ROUND(F{r}/12,2)"),
        ("Décimo 14°", 12, "#,##0.00", "=ROUND(SBU/12,2)"),
        ("Vacaciones", 12, "#,##0.00", "=ROUND(F{r}*DIAS_VACACIONES/360,2)"),
        ("¿Fondos de reserva?", 11, "General", lambda d: "No"),   # ingresan el 01-09-2026: aún no cumplen el mes 13
        ("Fondos de reserva", 13, "#,##0.00", '=IF(M{r}="Sí",ROUND(F{r}*P_FONDOS,2),0)'),
        ("Costo mensual por trabajador", 15, "#,##0.00", "=F{r}+I{r}+J{r}+K{r}+L{r}+N{r}"),
        ("Costo mensual total", 15, "#,##0.00", "=O{r}*E{r}"),
    ]
    _encabezados(t, FILA_TABLA, [c[0] for c in cols], [c[1] for c in cols])
    for r, d in enumerate(tabla, start=ini):
        for j, (_, _, fmt, v) in enumerate(cols, start=1):
            c = t.cell(r, j, v(d) if callable(v) else v.format(r=r))
            if callable(v):
                _texto(c)
            c.number_format = fmt
            if c.column_letter in "EFM":
                c.fill = AMARILLO
            if fmt == "General":
                c.alignment = Alignment(horizontal="center")
    dv = DataValidation(type="list", formula1='"Sí,No"', allow_blank=False)
    t.add_data_validation(dv)
    dv.add(f"M{ini}:M{fin}")
    t.conditional_formatting.add(f"G{ini}:G{fin}", CellIsRule(operator="equal", formula=['"NO"'],
                                                              font=Font(bold=True, color="9C0006")))

    # totales (borde doble inferior): n.º y costo total con SUM; el resto ponderado por n con SUMPRODUCT
    for j in range(1, len(cols) + 1):
        L = t.cell(1, j).column_letter
        c = t.cell(tot, j)
        if j == 1:
            c.value = "TOTALES"
        elif L in "EP":
            c.value = f"=SUM({L}{ini}:{L}{fin})"
        elif L in "FHIJKLN":
            c.value = f"=SUMPRODUCT({L}{ini}:{L}{fin},$E${ini}:$E${fin})"
        c.number_format = "0" if L == "E" else "#,##0.00"
        c.font, c.border = Font(bold=True), Border(top=FINO, bottom=DOBLE)

    # bloque de sostenibilidad
    a = tot + 2
    t.cell(a, 1, "Sostenibilidad mensual del contrato").font = Font(bold=True, size=12)
    filas = [
        ("Ingreso mensual (contrato con el GAD)", "=INGRESO_MENSUAL", "#,##0.00"),
        ("(−) Costo de personal", f"=P{tot}", "#,##0.00"),
        ("(−) Otros costos", "=OTROS_COSTOS", "#,##0.00"),
        ("Resultado mensual", f"=B{a+1}-B{a+2}-B{a+3}", "#,##0.00"),
        ("Margen sobre ingreso", f"=IF(B{a+1}=0,0,B{a+4}/B{a+1})", "0.00%"),
        ("Personal sobre ingreso", f"=IF(B{a+1}=0,0,B{a+2}/B{a+1})", "0.00%"),
    ]
    for i, (etiqueta, f, fmt) in enumerate(filas, start=a + 1):
        t.cell(i, 1, etiqueta)
        t.cell(i, 2, f).number_format = fmt
    t.cell(a + 4, 1).font = t.cell(a + 4, 2).font = Font(bold=True)
    t.conditional_formatting.add(f"B{a+4}", CellIsRule(operator="greaterThanOrEqual", formula=["0"],
                                 fill=PatternFill("solid", bgColor="C6EFCE"), font=Font(bold=True, color="006100")))
    t.conditional_formatting.add(f"B{a+4}", CellIsRule(operator="lessThan", formula=["0"],
                                 fill=PatternFill("solid", bgColor="FFC7CE"), font=Font(bold=True, color="9C0006")))
    t.freeze_panes = t.cell(ini, 2)       # debajo de los encabezados; el cargo queda fijo

    # ---------------------------------------------------------------- 3. Cálculo detallado (1.er trabajador)
    h = wb.create_sheet("Cálculo detallado")
    _membrete(h, empresa)
    h["A4"] = f"Desarrollo paso a paso: {tabla[0]['cargo']} (primera fila de la tabla de remuneraciones)"
    h["A4"].font = Font(bold=True)
    _encabezados(h, FILA_TABLA, ["Concepto", "Fórmula", "Valor"], [44, 56, 16])
    T = "'Tabla de remuneraciones'!"
    pasos = [   # (concepto, explicación, fórmula, formato); C6 = remuneración, C7 = aporte personal, C8 = base IR...
        ("Remuneración mensual", "Dato de la tabla de remuneraciones", f"={T}F{ini}", "#,##0.00"),
        (f"Aporte personal IESS {P['iess_personal']}", f"Remuneración × {P['iess_personal']}", f"={T}H{ini}", "#,##0.00"),
        ("Ingreso gravado anual proyectado", "(Remuneración − aporte personal) × 12", "=ROUND((C6-C7)*12,2)", "#,##0.00"),
        ("Fracción básica (desde)", "Límite inferior del tramo de la tabla IR", "=VLOOKUP(C8,TABLA_IR,1,TRUE)", "#,##0.00"),
        ("Impuesto de la fracción básica", "Impuesto fijo del tramo", "=VLOOKUP(C8,TABLA_IR,3,TRUE)", "#,##0.00"),
        ("% sobre el excedente", "Porcentaje del tramo", "=VLOOKUP(C8,TABLA_IR,4,TRUE)", "0.00%"),
        ("Impuesto a la renta anual", "Impuesto fracción + (base − desde) × %", "=ROUND(C10+(C8-C9)*C11,2)", "#,##0.00"),
        ("Retención mensual de IR", "IR anual ÷ 12", "=ROUND(C12/12,2)", "#,##0.00"),
        ("NETO A RECIBIR", "Remuneración − aporte personal − retención IR", "=C6-C7-C13", "#,##0.00"),
        (f"Aporte patronal {P['patronal_total']}", f"Remuneración × ({P['patronal']} + {P['iece_secap']} adicionales)", f"={T}I{ini}", "#,##0.00"),
        ("Décimo tercero", "Remuneración ÷ 12", f"={T}J{ini}", "#,##0.00"),
        ("Décimo cuarto", "SBU ÷ 12", f"={T}K{ini}", "#,##0.00"),
        ("Vacaciones", f"Remuneración × {P['dias_vacaciones']} días ÷ 360", f"={T}L{ini}", "#,##0.00"),
        ("Fondos de reserva", f"Remuneración × {P['fondos']} (solo si aplica)", f"={T}N{ini}", "#,##0.00"),
        ("COSTO MENSUAL PARA LA EMPRESA", "Remuneración + patronal + provisiones", "=C6+SUM(C15:C19)", "#,##0.00"),
        ("Costo anual", "Costo mensual × 12", "=C20*12", "#,##0.00"),
        ("Factor de costo", "Costo mensual ÷ remuneración", "=C20/C6", "0.00"),
    ]
    for i, (concepto, texto, f, fmt) in enumerate(pasos, start=FILA_TABLA + 1):
        h.cell(i, 1, concepto)
        h.cell(i, 2, texto).font = Font(italic=True, color="666666")
        h.cell(i, 3, f).number_format = fmt
        if concepto.isupper():
            h.cell(i, 1).font = h.cell(i, 3).font = Font(bold=True)
    ult = FILA_TABLA + len(pasos)
    h.cell(ult + 2, 1, '="Por cada $1 de sueldo, la empresa paga $"&FIXED(C22,2)').font = Font(bold=True)
    h.cell(ult + 3, 1, "Sin rebaja por gastos personales (proyección simplificada)").font = Font(italic=True, color="666666")
    h.freeze_panes = h.cell(FILA_TABLA + 1, 1)

    wb.active = 1                                 # hoja activa: "Tabla de remuneraciones"
    wb.properties.title = wb.properties.creator = empresa["nombre"]
    salida = io.BytesIO()
    wb.save(salida)
    return salida.getvalue()


if __name__ == "__main__":
    from openpyxl import load_workbook
    import calculos
    from calculos import calcular_rol

    P = dict(iess_personal="9,45%", patronal="11,15%", iece="0%", secap="0,5%", iece_secap="0,5%",
             patronal_total="11,65%", fondos="8,33%", dias_vacaciones=15, adicionales="SECAP 0,5%")

    empresa = {"nombre": "FERIAUTO SAS", "ruc": "1790000000001"}
    base = dict(nombres="María", apellidos="López", cargo="Vendedora", sueldo=1500,
                fecha_ingreso="2024-01-15", mensualiza_13=0, mensualiza_14=0, mensualiza_fondos=0)
    emps = [dict(base, cedula="0912345675"),
            dict(base, cedula="1710034065", nombres="Juan", apellidos="Pérez", sueldo=800,
                 mensualiza_13=1, mensualiza_14=1, mensualiza_fondos=1)]
    novs = [dict(dias=30, h50=10, comisiones=200), dict(dias=30, anticipos=50)]
    detalles = [calcular_rol(e, n, 2026, 10) for e, n in zip(emps, novs)]
    cab = dict(anio=2026, mes=10)

    datos = libro_rol(cab, detalles, empresa, "Octubre", P)
    wb = load_workbook(io.BytesIO(datos))

    assert wb.sheetnames == ["Rol de pagos", "Costo empleador", "Planilla IESS", "Transferencias"]
    assert wb.active.title == "Rol de pagos" and wb.properties.creator == "FERIAUTO SAS"
    ws = wb["Rol de pagos"]
    assert ws["A1"].value == "FERIAUTO SAS" and ws["A2"].value == "RUC 1790000000001 · Rol de pagos Octubre 2026"
    assert ws["A6"].value == "0912345675" and ws["A6"].data_type == "s"        # conserva el cero inicial
    assert ws.freeze_panes == "C6"
    for hoja in wb:                                                            # totales = fórmulas SUM reales
        fila = hoja.max_row
        assert hoja.cell(fila, 1).value == "TOTALES"
        formulas = [c.value for c in hoja[fila] if isinstance(c.value, str) and c.value.startswith("=SUM(")]
        assert formulas, f"{hoja.title}: sin fórmulas SUM"
    col_neto = [c.value for c in ws["S"]][5:7]                                  # filas 6-7, columna NETO
    assert ws["S5"].value == "NETO A RECIBIR" and ws["S8"].value == "=SUM(S6:S7)"
    assert round(sum(col_neto), 2) == round(sum(d["neto"] for d in detalles), 2)
    pl = wb["Planilla IESS"]
    assert pl["G6"].value == "=D6+E6+F6"
    assert pl["H6"].value == detalles[0]["p_fondos"] > 0 and pl["H7"].value == 0   # solo quien acumula fondos
    assert wb["Transferencias"]["D6"].value == "Rol Octubre 2026"
    malo = calcular_rol(dict(emps[0], nombres="=HYPERLINK(\"http://x\")", apellidos="", cargo="=1+1"),
                        novs[0], 2026, 10)
    ws = load_workbook(io.BytesIO(libro_rol(cab, [malo], dict(empresa, nombre="=2+2"), "Octubre", P)))["Rol de pagos"]
    assert ws["B6"].data_type == "s" and ws["C6"].value == "=1+1" and ws["C6"].data_type == "s"
    assert ws["A1"].data_type == "s"
    print("OK exportar")

    # ---- libro de remuneraciones: 4 cargos ficticios, estructura y fórmulas
    from decimal import Decimal
    cargos = [("Gerente General", 1200), ("Director Comercial", 1000),
              ("Director Financiero", 1000), ("Director de Operaciones", 1000)]
    tabla = [dict(cargo=c, departamento="Directivo", estructura="", minimo=600, n=1, sueldo=s) for c, s in cargos]
    emp2 = dict(empresa, nombre="FERIAUTO S.A.S.", regimen="Código del Trabajo", cliente="GAD",
                ingreso_mensual=3800, otros_costos=530)
    p = calculos.parametros_defecto("CT")
    wb = load_workbook(io.BytesIO(libro_remuneraciones(tabla, emp2, p, P)))

    assert wb.sheetnames == ["Parámetros", "Tabla de remuneraciones", "Cálculo detallado"]
    assert wb.active.title == "Tabla de remuneraciones" and wb.properties.creator == "FERIAUTO S.A.S."
    nombres = {"SBU": "$B$8", "P_PERSONAL": "$B$9", "P_PATRONAL": "$B$10", "P_IECE_SECAP": "$B$11",
               "P_FONDOS": "$B$12", "DIAS_VACACIONES": "$B$13", "INGRESO_MENSUAL": "$B$14", "OTROS_COSTOS": "$B$15"}
    for n, celda in nombres.items():
        assert wb.defined_names[n].attr_text == "'Parámetros'!" + celda, n
    assert wb.defined_names["TABLA_IR"].attr_text == "'Parámetros'!$A$19:$D$28"
    par = wb["Parámetros"]
    assert par["B8"].value == 482 and par["B9"].value == 0.0945 and par["B14"].value == 3800
    assert par["B8"].fill.fgColor.rgb.endswith("FFF6D6")

    ws = wb["Tabla de remuneraciones"]
    assert ws["A1"].value == "FERIAUTO S.A.S." and ws["A2"].value == "RUC 1790000000001"
    assert ws["A3"].value == "Régimen: Código del Trabajo · Tabla de remuneraciones 2026"
    assert ws.freeze_panes == "B6" and ws["E6"].value == 1 and ws["F6"].value == 1200 and ws["M6"].value == "No"
    for r in range(6, 10):                                   # cada celda de cálculo es fórmula y cita las entradas
        esperado = {"G": f'=IF(F{r}>=MAX(D{r},SBU),"Sí","NO")', "H": f"=ROUND(F{r}*P_PERSONAL,2)",
                    "I": f"=ROUND(F{r}*P_PATRONAL,2)+ROUND(F{r}*P_IECE_SECAP,2)", "J": f"=ROUND(F{r}/12,2)", "K": "=ROUND(SBU/12,2)", "L": f"=ROUND(F{r}*DIAS_VACACIONES/360,2)",
                    "N": f'=IF(M{r}="Sí",ROUND(F{r}*P_FONDOS,2),0)', "O": f"=F{r}+I{r}+J{r}+K{r}+L{r}+N{r}", "P": f"=O{r}*E{r}"}
        for col, f in esperado.items():
            assert ws[f"{col}{r}"].value == f, f"{col}{r}: {ws[f'{col}{r}'].value}"
    assert ws["E10"].value == "=SUM(E6:E9)" and ws["P10"].value == "=SUM(P6:P9)"
    assert ws["H10"].value == "=SUMPRODUCT(H6:H9,$E$6:$E$9)" and ws["F10"].value == "=SUMPRODUCT(F6:F9,$E$6:$E$9)"
    assert ws["B13"].value == "=INGRESO_MENSUAL" and ws["B14"].value == "=P10" and ws["B15"].value == "=OTROS_COSTOS"
    assert ws["B16"].value == "=B13-B14-B15" and ws["B17"].value == "=IF(B13=0,0,B16/B13)"

    cd = wb["Cálculo detallado"]
    assert cd["C6"].value == "='Tabla de remuneraciones'!F6" and cd["C7"].value == "='Tabla de remuneraciones'!H6"
    assert cd["C12"].value == "=ROUND(C10+(C8-C9)*C11,2)" and "TABLA_IR" in cd["C9"].value
    assert all(str(cd[f"C{r}"].value).startswith("=") for r in range(6, 23))
    assert cd["A25"].value == "Sin rebaja por gastos personales (proyección simplificada)"

    # ---- valores esperados (en Python puro, mismas reglas que las fórmulas)
    sueldo = Decimal(1200)
    costo_gg = sueldo * (1 + Decimal("0.1165")) + 100 + Decimal(482) / 12 + 50
    assert abs(float(costo_gg) - (1200 * 1.1165 + 100 + 40.1667 + 50)) < 0.001
    base = (sueldo - sueldo * p["iess_personal"]) * 12
    ir_anual = calculos.impuesto_renta_anual(base)[0]
    print(f"OK libro_remuneraciones (estructura y fórmulas). Esperado GG: costo {costo_gg:.2f}, retención IR {ir_anual / 12:.2f}")

    # ---- recálculo real con LibreOffice, si está instalado
    import glob, os, subprocess, tempfile
    soffice = next(iter(glob.glob(r"C:\Program Files*\LibreOffice*\program\soffice.exe")), None)
    if not soffice:
        print("LibreOffice no instalado: se omite el recálculo numérico (solo se verificó estructura y fórmulas).")
    else:
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "t.xlsx")
            open(ruta, "wb").write(libro_remuneraciones(tabla, emp2, p, P))
            subprocess.run([soffice, "--headless", "--convert-to", "xlsx", "--outdir", os.path.join(d, "out"), ruta],
                           check=True, capture_output=True, timeout=120)
            v = load_workbook(os.path.join(d, "out", "t.xlsx"), data_only=True)
        t, c = v["Tabla de remuneraciones"], v["Cálculo detallado"]
        assert abs(t["O6"].value - float(costo_gg)) < 0.01, t["O6"].value
        assert abs(c["C13"].value - float(ir_anual) / 12) < 0.01, c["C13"].value
        assert abs(t["B16"].value - (3800 - t["P10"].value - 530)) < 0.01
        print(f"OK recálculo LibreOffice: costo GG {t['O6'].value:.2f}, retención IR {c['C13'].value:.2f}, "
              f"resultado mensual {t['B16'].value:.2f}")
