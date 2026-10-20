"""
Exportación del Rol de Pagos a Excel (.xlsx) con 4 hojas:
Rol de pagos, Costo empleador, Planilla IESS y Transferencias.

Cada hoja se describe con una lista de columnas (título, función que saca el valor de un
detalle, tipo) y `_hoja()` hace el resto. Los totales son fórmulas =SUM() reales de Excel.

Ejecuta `python exportar.py` para correr el self-check.
"""
import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

FILA_TABLA = 5  # encabezados de la tabla; filas 1-3 son el membrete de la empresa
FONDO = PatternFill("solid", fgColor="F2F0EA")
FINO, DOBLE = Side(style="thin"), Side(style="double")


def _hoja(wb, titulo, empresa, subtitulo, columnas, detalles, color=None):
    """
    columnas: lista de (título, fn(d) -> valor, tipo) con tipo 'txt' | 'int' | 'num'.
    Si fn devuelve un texto que empieza con '=', es una fórmula y '{r}' se reemplaza por la fila.
    color: (índice de columna, hex) para resaltar la columna más importante de la hoja.
    """
    ws = wb.create_sheet(titulo)
    ws["A1"] = empresa["nombre"]
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


def libro_rol(cab, detalles, empresa, mes_nombre):
    """Devuelve el .xlsx del rol (bytes) listo para enviar con Flask."""
    anio = cab["anio"]
    sub = f"RUC {empresa['ruc']} · Rol de pagos {mes_nombre} {anio}"
    ced = ("Cédula", lambda d: str(d["cedula"]), "txt")
    emp = ("Empleado", lambda d: d["nombre"], "txt")
    col = lambda titulo, k: (titulo, lambda d: d[k], "num")   # columna numérica simple

    wb = Workbook()
    wb.remove(wb.active)

    _hoja(wb, "Rol de pagos", empresa, sub, [
        ced, emp, ("Cargo", lambda d: d["cargo"], "txt"), ("Días", lambda d: d["dias"], "int"),
        col("Sueldo ganado", "sueldo_ganado"), col("Horas 50%", "v_h50"), col("Horas 100%", "v_h100"),
        col("Comisiones", "comisiones"), col("Total gravado", "total_gravado"),
        col("Décimo 13° mensual", "decimo13_pagado"), col("Décimo 14° mensual", "decimo14_pagado"),
        col("Fondos de reserva", "fondos_pagado"), col("Total ingresos", "total_ingresos"),
        col("Aporte IESS 9,45%", "iess_personal"), col("Retención IR", "ir"),
        col("Anticipos", "anticipos"), col("Préstamo IESS", "prestamos_iess"),
        col("Total descuentos", "total_descuentos"), col("NETO A RECIBIR", "neto"),
    ], detalles, color=(19, "1D6A4E"))

    _hoja(wb, "Costo empleador", empresa, sub, [
        ced, emp, col("Total gravado", "total_gravado"), col("Décimo 13°", "p13"),
        col("Décimo 14°", "p14"), col("Vacaciones", "p_vac"), col("Fondos de reserva", "p_fondos"),
        col("Aporte patronal 11,15%", "patronal"), col("IECE 0,5% + SECAP 0,5%", "iece_secap"),
        col("Total provisiones y aportes", "total_provisiones"), col("COSTO TOTAL", "costo_total"),
    ], detalles, color=(11, "3E4A7C"))

    _hoja(wb, "Planilla IESS", empresa, sub, [
        ced, emp, col("Total gravado (base de aportación)", "total_gravado"),
        col("Aporte personal 9,45%", "iess_personal"), col("Aporte patronal 11,15%", "patronal"),
        col("IECE + SECAP 1%", "iece_secap"),
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


if __name__ == "__main__":
    from openpyxl import load_workbook
    from calculos import calcular_rol

    empresa = {"nombre": "FERIAUTO SAS", "ruc": "1790000000001"}
    base = dict(nombres="María", apellidos="López", cargo="Vendedora", sueldo=1500,
                fecha_ingreso="2024-01-15", mensualiza_decimos=0, mensualiza_fondos=0)
    emps = [dict(base, cedula="0912345675"),
            dict(base, cedula="1710034065", nombres="Juan", apellidos="Pérez", sueldo=800,
                 mensualiza_decimos=1, mensualiza_fondos=1)]
    novs = [dict(dias=30, h50=10, comisiones=200), dict(dias=30, anticipos=50)]
    detalles = [calcular_rol(e, n, 2026, 10) for e, n in zip(emps, novs)]
    cab = dict(anio=2026, mes=10)

    datos = libro_rol(cab, detalles, empresa, "Octubre")
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
    print("OK exportar")
