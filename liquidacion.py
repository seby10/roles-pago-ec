"""Registro de resultados del Ministerio. Solo concilia sumas; no calcula derechos."""
from datetime import date
from decimal import Decimal, InvalidOperation

URL_OFICIAL='https://calculadoras.trabajo.gob.ec/liquidaciones'
CAUSAS={
 'mutuo_acuerdo':'Por acuerdo de las partes.',
 'obra':'Por la conclusión de la obra, período de labor o servicios objeto del contrato.',
 'extincion':'Por muerte o incapacidad del empleador o extinción de la persona jurídica contratante.',
 'muerte':'Por muerte del trabajador o incapacidad permanente y total para el trabajo.',
 'fuerza_mayor':'Por caso fortuito o fuerza mayor que imposibiliten el trabajo.',
 'visto_empleador':'Por voluntad del empleador previo visto bueno.',
 'visto_trabajador':'Por voluntad del trabajador previo visto bueno.',
 'desahucio':'Por desahucio.',
 'despido':'Por despido Intempestivo.',
 'prueba':'Por Terminación dentro del periodo de prueba.',
 'otra_ct':'Por las causas legalmente previstas en el contrato o disposición específica.',
 'cese_publico':'Cesación de funciones en el sector público (requiere fuente específica).',
}
RUBROS={
 'decimo13':'Valor Decimotercera Remuneración',
 'decimo14':'Valor Decimocuarta Remuneración',
 'vacaciones':'Valor Vacaciones Ultimo Periodo',
 'despido':'Valor Indemnización Despido Intempestivo',
 'desahucio':'Valor Indemnización Desahucio',
 'embarazo':'Valor Indemnización Mujer Embarazada',
 'sindical':'Valor Indemnización Dirigente Sindical',
 'discapacidad':'Valor Indemnización Por Discapacidad',
 'enfermedad':'Valor Indemnización Enfermedad No Profesional',
 'plazo':'Valor Indemnización Terminación Antes de Plazo',
}
CAMPOS={**{k:(v,'usd') for k,v in RUBROS.items()},
 'total_ministerio':('TOTAL LIQUIDACIÓN APROXIMADA A RECIBIR del Ministerio','usd'),
 'saldo_anterior':('Vacaciones: saldo anterior según kárdex (días)','dias'),
 'devengadas':('Vacaciones: días devengados según respaldo, no calculados aquí','dias'),
 'gozadas':('Vacaciones: días gozados según kárdex','dias'),
 'ajuste_vac':('Vacaciones: ajuste de días respaldado','ajuste'),
 'vacaciones_pendientes':('Días sin gozar utilizados en la calculadora oficial','dias'),
 'sueldo_pendiente':('Saldo de remuneraciones pendiente según conciliación de nómina','usd'),
 'otros_haberes':('Otros haberes empresariales documentados','usd'),
 'iess':('Aporte personal IESS pendiente, valor conciliado','usd'),
 'ir':('Retención IR pendiente, valor conciliado','usd'),
 'anticipos':('Anticipos pendientes de compensar','usd'),
 'prestamos':('Préstamos con respaldo de compensación','usd'),
 'otras_deducciones':('Otras deducciones legalmente justificadas','usd'),
}
SOURCES=[('Calculadora oficial de liquidaciones del Ministerio del Trabajo',URL_OFICIAL)]


def leer_pdf_oficial(contenido):
    """Lectura asistida del formato observado. No acredita autenticidad de un PDF."""
    import io
    import re
    from pypdf import PdfReader
    lector=PdfReader(io.BytesIO(contenido))
    if lector.is_encrypted or len(lector.pages)>20:
        raise ValueError('Usa un PDF simple del resultado de la calculadora oficial.')
    texto='\n'.join(p.extract_text(extraction_mode='layout') or '' for p in lector.pages)
    if 'SIMULADOR CALCULADORA DE LIQUIDACIONES' not in texto:
        raise ValueError('No se reconoció el formato de texto del simulador. Adjunta el original y registra los valores manualmente.')
    patrones={**RUBROS,'enfermedad':'Valor Indemnización Enfermedad No','plazo':'Valor Indemnización Terminación Antes de','total_ministerio':'Total Liquidación Aproximada a Recibir'}
    valores={}
    for k,label in patrones.items():
        linea=next((s for s in texto.splitlines() if label in s), '')
        cantidad=re.search(r'\$\s*([0-9]+(?:\.[0-9]{1,2})?)\s*$',linea)
        if not cantidad:
            raise ValueError('No se pudieron leer todos los rubros con seguridad. Consulta el PDF y transcríbelos manualmente.')
        valores[k]=f'{dec(cantidad.group(1)):.2f}'
    if sum(dec(valores[k]) for k in RUBROS)!=dec(valores['total_ministerio']):
        raise ValueError('Los importes leídos no coinciden con el total. Verifica manualmente el documento.')
    return valores


def dec(v,nombre='',negativo=False):
    try:
        n=Decimal(str(v or '0').strip().replace(',','.'))
    except InvalidOperation:
        raise ValueError(f'{nombre}: número inválido.')
    if not n.is_finite() or abs(n)>100000000 or (n<0 and not negativo):
        raise ValueError(f'{nombre}: valor fuera del rango permitido.')
    return n


def registrar_resultado(datos, ingreso, salida, regimen, causa, region='Sierra'):
    if regimen!='CT':
        raise ValueError('La calculadora indicada se basa en el contrato individual del Código del Trabajo. Para otro régimen se requiere la fuente y procedimiento específicos; no se trasladan reglas de CT automáticamente.')
    if causa not in CAUSAS or causa=='cese_publico':
        raise ValueError('Selecciona una causa del Código del Trabajo.')
    try:
        consulta=date.fromisoformat(datos.get('fecha_consulta',''))
    except ValueError:
        raise ValueError('Registra la fecha de consulta al Ministerio.')
    if consulta>date.today():
        raise ValueError('La fecha de consulta no puede ser futura.')
    numeros={k:dec(datos.get(k),label,tipo=='ajuste') for k,(label,tipo) in CAMPOS.items()}
    for k,(_,tipo) in CAMPOS.items():
        if tipo=='usd' and numeros[k]!=numeros[k].quantize(Decimal('.01')):
            raise ValueError('Los valores monetarios deben transcribirse con máximo dos decimales.')
    suma=sum(numeros[k] for k in RUBROS)
    if suma!=numeros['total_ministerio']:
        raise ValueError('Los rubros transcritos no suman el total mostrado por el Ministerio. Revisa la captura; no se recalculan los derechos para corregirlo.')
    saldo=numeros['saldo_anterior']+numeros['devengadas']-numeros['gozadas']+numeros['ajuste_vac']
    if saldo<0 or saldo!=numeros['vacaciones_pendientes']:
        raise ValueError('El kárdex registrado debe coincidir con los días sin gozar usados en la consulta oficial.')
    if numeros['vacaciones']>0 and not numeros['vacaciones_pendientes']:
        raise ValueError('Registra los días sin gozar utilizados en la calculadora y su kárdex.')
    total=suma+numeros['sueldo_pendiente']+numeros['otros_haberes']
    ded=sum(numeros[k] for k in ('iess','ir','anticipos','prestamos','otras_deducciones'))
    if ded>total:
        raise ValueError('Las deducciones documentadas superan los haberes registrados.')
    def fila(k,label=None,oficial=True):
        return dict(codigo=k,concepto=label or CAMPOS[k][0],valor=f'{numeros[k]:.2f}',formula='Importe transcrito del resultado oficial; ver evidencia adjunta' if oficial else 'Saldo empresarial conciliado y respaldado; no es un resultado de la calculadora ministerial')
    return dict(ingresos=[fila(k) for k in RUBROS]+[fila('sueldo_pendiente',oficial=False),fila('otros_haberes',oficial=False)],
                descuentos=[fila(k,oficial=False) for k in ('iess','ir','anticipos','prestamos','otras_deducciones')],
                total_oficial=f'{suma:.2f}',total_haberes=f'{total:.2f}',total_deducciones=f'{ded:.2f}',neto=f'{total-ded:.2f}',
                vacaciones=dict(anterior=str(numeros['saldo_anterior']),devengadas=str(numeros['devengadas']),gozadas=str(numeros['gozadas']),ajuste=str(numeros['ajuste_vac']),saldo=str(saldo),liquidables=str(numeros['vacaciones_pendientes']),derecho_anual='según kárdex y consulta oficial'),
                causa=CAUSAS[causa],regimen=regimen,avisos=[],fuentes=SOURCES,fecha_consulta=consulta.isoformat(),fuente_url=URL_OFICIAL,
                metodo='Valores de derechos laborales transcritos de la calculadora oficial del Ministerio del Trabajo. El sistema solo verifica sumas y organiza los saldos empresariales respaldados; no calcula décimos, vacaciones ni indemnizaciones. El Ministerio denomina su resultado liquidación aproximada. No sustituye el acta oficial de finiquito.')
