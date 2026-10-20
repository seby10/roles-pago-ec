# Roles de Pago Ecuador 2026 (demo académica)

Módulo demostrativo para un taller de clase: calcula el rol de pagos mensual de una nómina ecuatoriana (ingresos, descuentos IESS e IR, neto a recibir y costo del empleador). Está hecho con Flask, SQLite y CSS propio (sin Bootstrap ni npm).

> **Aviso:** es una demo académica. No la uses en producción ni para pagar sueldos reales. El cálculo simplifica varios puntos legales (ver sección 7).

---

## 1. Cómo ejecutar

Requisito: **Python 3.9+**. La app corre en local y cada quien tiene su propia base de datos (`roles.db`), así que nadie pisa los datos de otro.

```bash
git clone https://github.com/seby10/roles-pago-ec.git
cd roles-pago-ec
```

Luego, según tu sistema:

- **Windows:** doble clic en `iniciar.bat`.
- **macOS / Linux:** `sh iniciar.sh`.

El script crea un entorno virtual (`.venv`) con las dependencias del proyecto (Flask y openpyxl) para no tocar tu Python global, y abre **http://127.0.0.1:5050**. La primera vez tarda unos segundos porque descarga esas dependencias; después arranca directo. Se detiene con `Ctrl+C`.

Para traer cambios del repositorio: `git pull`.

Si prefieres hacerlo a mano:

```bash
pip install -r requirements.txt
python app.py          # http://127.0.0.1:5050
python calculos.py     # verifica los cálculos contra casos resueltos a mano
```

Para volver a los datos de ejemplo usa **Reiniciar demo**, en el pie de página. Borrar `roles.db` tiene el mismo efecto.

| Si pasa esto | Prueba |
| --- | --- |
| El script dice que falta Python | En Windows, Python debe estar en el PATH (es una casilla del instalador). |
| Linux no puede crear `.venv` | `sudo apt install python3-venv` |
| "Address already in use" | Otro programa usa el 5050: `PORT=5051 python app.py` (en Windows: `set PORT=5051 && python app.py`). |
| La tipografía se ve distinta | Las fuentes vienen de Google Fonts; sin internet se usan las del sistema y todo funciona igual. |

> **¿Por qué no está en Vercel?** Vercel no guarda archivos entre peticiones: la base SQLite se perdería y además todos compartirían los mismos datos. Para un taller tiene más sentido que cada uno corra su copia.

---

## 2. Flujo en 6 pasos

| # | Paso | Ruta | Qué ocurre |
| --- | ------ | ------ | ------------ |
| 1 | Empleados (CRUD) | `/empleados` | Alta, edición, activar/inactivar y eliminar. Cada empleado tiene departamento (Gerencia General, Tecnología, Finanzas, Marketing u Operaciones), **reporta a** (jefe inmediato; vacío = máxima autoridad), función principal y estructura ocupacional (fija su sueldo mínimo sectorial, sección 5.9). También mensualizar décimos y fondos, gastos personales anuales y cargas familiares (0 a 20). El formulario impide reportarse a sí mismo y formar ciclos. No se puede eliminar a un jefe que tiene subordinados: primero hay que cambiarles la línea de reporte. Un empleado que ya aparece en un rol generado no se elimina: se inactiva. |
| 2 | Nuevo rol | `/roles/nuevo` | Eliges año y mes. Por cada empleado activo hay una fila editable con días (30 por defecto), horas 50%, horas 100%, comisiones, anticipos de sueldo y préstamo quirografario IESS. Si el rol del periodo ya existe, sus novedades se precargan. La columna **Neto estimado** se recalcula mientras escribes (`POST /roles/preview` usa el mismo `calculos.py`, sin guardar). `Enter` baja a la fila siguiente. |
| 3 | Generar | `POST /roles/generar` | Por cada empleado activo llama a `calculos.calcular_rol()`, una función pura que no toca la base de datos. Valida días entre 1 y 30 y valores numéricos ≥ 0. |
| 4 | Guardar | (mismo POST) | Dentro de una transacción: borra el rol previo del mismo periodo (si existe), guarda la cabecera y luego los detalles. Regenerar reemplaza el rol. |
| 5 | Vista consolidada | `/roles/<id>` | Totales de ingresos, descuentos y neto por empleado. El costo empleador va en una tabla aparte (provisiones y aportes patronales) que no afecta el neto. Filas clicables; en celular se muestra como tarjetas. Se imprime en A4 horizontal. **Exportar Excel** (`/roles/<id>/excel`) descarga un `.xlsx` con 4 hojas: Rol de pagos, Costo empleador, Planilla IESS y Transferencias (archivo para el banco), con totales como fórmulas `SUM`. |
| 6 | Rol individual | `/roles/<id>/empleado/<det_id>` | Rol imprimible en A4 con firmas, fechas de pago informativas y la sección "¿Cómo se calculó este rol?" de 9 pasos. Botones ← / → (o flechas del teclado) para pasar al siguiente empleado. |
| extra | Organigrama y remuneraciones | `/organigrama` | Árbol de cargos con líneas de autoridad, generado desde "reporta a". Cada tarjeta muestra departamento, cargo, nombre, función y "1 trabajador · sueldo". Debajo está la tabla de remuneraciones que pide la PEA 3 y el panel **"¿Es sostenible?"**. Como el organigrama y la tabla salen de los mismos datos, todo cargo del organigrama aparece en la tabla. |

El listado de roles está en `/`.

Son dos libros Excel distintos. El del **rol** (`/roles/<id>/excel`, paso 5) tiene 4 hojas de nómina y banco. El de la **tabla de remuneraciones** (`/organigrama/excel`, botón *Exportar Excel* del organigrama) tiene tres hojas: *Parámetros* (celdas amarillas editables y la tabla del IR como rango con nombre), *Tabla de remuneraciones* (número de trabajadores y remuneración como entradas; aportes, 13.º, 14.º, vacaciones, fondos y costo como fórmulas, más el bloque de sostenibilidad) y *Cálculo detallado* (el Gerente General paso a paso, con el IR por `VLOOKUP`). Al cambiar el sueldo o el n.º de trabajadores, todo se recalcula en Excel.

---

## 3. Stack y por qué

| Pieza | Por qué |
| ------- | --------- |
| **Flask** | Una sola dependencia. El código se lee casi como pseudocódigo. |
| **sqlite3** (librería estándar) | No necesita servidor de base de datos: todo está en un archivo, `roles.db`. |
| **Jinja + CSS propio** | Plantillas del lado del servidor y un solo archivo de estilos (`static/style.css`), sin build, sin npm y sin Bootstrap. |

Se ejecuta con un solo comando: `python app.py`.

**Diseño "libro contable":** papel cálido, tres colores con significado fijo (verde = neto, arcilla = descuentos, índigo = costo empleador), totales con doble raya contable, celdas en cero como "—" y tablas sin "$" (los valores van en USD). Tipografía: Geist (cifras con dígitos tabulares) e Instrument Serif para títulos, cargadas desde Google Fonts; sin internet, caen a fuentes del sistema. Responsive hasta 375 px.

---

## 4. Esquema de la base de datos

| Tabla | Campos clave | Rol |
| ------- | -------------- | ----- |
| `empleados` | `cedula` (UNIQUE), `nombres`, `apellidos`, `cargo`, `sueldo`, `fecha_ingreso`, `tipo_contrato`, `activo`, `mensualiza_decimos` (0 por defecto), `mensualiza_fondos` (1 por defecto), `gastos_personales`, `cargas`, `departamento`, `reporta_a` (FK a `empleados.id`; NULL = máxima autoridad), `funcion`, `estructura` (código de la tabla sectorial: A1, B1, B2, C1, C3, D1 o E2; vacío si no aplica) | Maestro de empleados y organigrama. `reporta_a` define las líneas de autoridad. |
| `roles_cabecera` | `anio`, `mes` (**UNIQUE**), `generado_en`, `n_empleados`, `total_ingresos`, `total_descuentos`, `total_neto`, `total_costo`, `total_iess`, `total_ir` | Un registro por periodo con los totales. `total_iess` = aporte personal + patronal + IECE/SECAP (lo que se transfiere al IESS). |
| `roles_detalle` | `rol_id` (FK, `ON DELETE CASCADE`), `empleado_id` (FK), **snapshot** de `nombre`, `cedula`, `cargo`, `sueldo`; novedades (`dias`, `h50`, `h100`, `comisiones`, `anticipos`, `prestamos_iess`); resultados (`total_gravado`, `iess_personal`, `rebaja_gp`, `ir`, `neto`, `costo_total`, etc.) | Una fila por empleado y periodo. |

**Por qué `roles_detalle` guarda un snapshot:** al generar el rol copia nombre, cédula, cargo y sueldo. Si luego cambias el sueldo del empleado, los roles de meses pasados no cambian.

**Por qué `UNIQUE(anio, mes)`:** solo puede existir un rol por periodo. Regenerar borra la cabecera anterior (el detalle cae en cascada) en lugar de duplicar datos.

**Versión del esquema:** `PRAGMA user_version` guarda `SCHEMA_VERSION` (hoy 4). La versión 3 agregó las columnas de organización a `empleados`; la 4 solo cambió la semilla, que ahora trae 5 personas (los 4 socios de FERIAUTO y el Programador Junior). Si al arrancar la base tiene otra versión, se renombra como `roles_v<N>_respaldo.db` y se crea una nueva con la semilla. Nada se borra en silencio: al pasar de la 3 a la 4, la base anterior quedó como `roles_v3_respaldo.db`.

---

## 5. Lógica de cálculo

Fuente: `calculos.py`. Los cálculos usan `Decimal` y se redondean a centavos por línea (half-up).

### 5.1 Ingresos gravados (pagan IESS e IR)

``` text
valor hora       = sueldo / 240                      (40 h/semana × 4 semanas)
HE 50%           = h50 × valor hora × 1,5            (suplementarias diurnas)
HE 100%          = h100 × valor hora × 2             (sábados, domingos, feriados y suplementarias de 24:00 a 06:00)
sueldo ganado   = sueldo × días / 30
TOTAL GRAVADO    = sueldo ganado + HE 50% + HE 100% + comisiones
```

El recargo nocturno del 25% no está incluido.

### 5.2 Descuentos

``` text
IESS personal     = gravado × 9,45%
base IR anual     = (gravado − IESS personal) × 12
impuesto causado  = impuesto de la tabla 2026 (sección 5.5)
rebaja GP         = 18% × menor(gastos personales anuales, tope)   (sección 5.6)
IR anual          = máximo(impuesto causado − rebaja GP, 0)
IR mensual        = IR anual / 12
```

La rebaja resta del **impuesto**, no de la base imponible, y el IR anual nunca queda negativo.

### 5.3 Neto

``` text
TOTAL INGRESOS   = gravado + no gravado (décimos y fondos mensualizados)
TOTAL DESCUENTOS = IESS personal + IR mensual + anticipos de sueldo + préstamo quirografario IESS
NETO A RECIBIR   = total ingresos − total descuentos
```

### 5.4 Provisiones y costo del empleador

``` text
13°               = gravado / 12
14°               = SBU (482) / 12 × días / 30
vacaciones        = gravado / 24
fondos de reserva = gravado × 8,33%                  (solo si cumple 365 días al cierre del mes)
aporte patronal   = gravado × 11,15%
IECE 0,5% + SECAP 0,5% = gravado × 1%                (adicionales al 11,15%)
COSTO EMPLEADOR   = gravado + provisiones (13°, 14°, vacaciones, fondos, patronal, IECE/SECAP)
```

El costo patronal de aportes suma 12,15% (11,15% + 1%). Los fondos de reserva se provisionan siempre; si están mensualizados, además se pagan en el rol (sección 5.7).

### 5.5 Tabla de IR 2026 (personas naturales)

Fuente: SRI, Res. NAC-DGERCGC25-00000043. Impuesto anual = impuesto de la fracción básica + % × (base − desde). Es el *impuesto causado*; la rebaja de la sección 5.6 se resta después.

| Desde ($) | Hasta ($) | Impuesto fracción básica ($) | % sobre el excedente |
| ----------: | ----------: | -----------------------------: | ---------------------: |
| 0 | 12.208 | 0 | 0% |
| 12.208 | 15.549 | 0 | 5% |
| 15.549 | 20.188 | 167 | 10% |
| 20.188 | 26.700 | 631 | 12% |
| 26.700 | 35.136 | 1.412 | 15% |
| 35.136 | 46.575 | 2.678 | 20% |
| 46.575 | 62.005 | 4.965 | 25% |
| 62.005 | 82.679 | 8.823 | 30% |
| 82.679 | 109.956 | 15.025 | 35% |
| 109.956 | en adelante | 24.572 | 37% |

### 5.6 Rebaja por gastos personales

Rebaja = 18% × menor(gastos personales anuales proyectados, tope). Tope = canastas × CFB de enero 2026 ($ 821,80). Las canastas dependen de las cargas familiares; 5 o más cargas usan 20 canastas.

| Cargas | Canastas | Tope ($) | Rebaja máxima ($) |
| -------: | ---------: | ---------: | ------------------: |
| 0 | 7 | 5.752,60 | 1.035,47 |
| 1 | 9 | 7.396,20 | 1.331,32 |
| 2 | 11 | 9.039,80 | 1.627,16 |
| 3 | 14 | 11.505,20 | 2.070,94 |
| 4 | 17 | 13.970,60 | 2.514,71 |
| 5 o más | 20 | 16.436,00 | 2.958,48 |

Los gastos personales y las cargas se capturan en la ficha del empleado; la proyección anual es la que entrega el trabajador al empleador.

Ejemplo teórico (no corresponde a un empleado de la semilla): gastos personales de $ 8.000 con 2 cargas. Tope = 11 × 821,80 = 9.039,80; rebaja = 18% × 8.000 = 1.440,00. Si el impuesto causado fuera $ 3.068,65, el IR anual sería 3.068,65 − 1.440,00 = 1.628,65 y el mensual 135,72. Si la rebaja superara el impuesto causado, el IR queda en 0.

### 5.7 Mensualización

Por ley, los **fondos de reserva** se pagan cada mes desde el mes 13, salvo que el trabajador pida acumularlos en el IESS; por eso *mensualiza fondos* viene marcado por defecto. Los **décimos** (13° y 14°) se acumulan, salvo que el trabajador pida mensualizarlos.

Lo mensualizado se paga en el rol como ingreso **no gravado**: no paga IESS ni IR, pero sube el neto. El costo del empleador no cambia, porque la provisión se calcula igual aunque el beneficio se pague hoy o en diciembre.

### 5.8 Fechas de pago (informativas)

El rol individual muestra cuándo se paga cada beneficio: 13° hasta el 24 de diciembre; 14° hasta el 15 de agosto para Sierra/Amazonía o hasta el 15 de marzo para Costa/Galápagos. La fecha sale de `EMPRESA["region"]` en `app.py` (la demo está en Sierra, por eso dice "paga 15 ago"; con "Costa" diría "paga 15 mar"). Es solo informativa: la región no altera ningún monto.

### 5.9 Salario mínimo sectorial

Además del SBU, cada cargo tiene un mínimo según su **estructura ocupacional**. Fuente: R.O. 2.º Suplemento 708 (20-dic-2024), Anexo 1, págs. 64-65; comisión sectorial 12 "Tecnología: hardware y software", rama 1 "Informática y actividades conexas" (CIIU J62). Para 2026 no se emitió tabla nueva: según el Ministerio del Trabajo rige la tabla 2025 (Acuerdo MDT-2024-301) y los valores menores al SBU suben a $ 482. Un cargo no contemplado no puede ganar menos que el menor valor de su rama (art. 5 del acuerdo).

| Estructura | Cargo de referencia | Mínimo mensual ($) |
| --- | --- | ---: |
| A1 | Director / jefe de área | 507,37 |
| B1 | Supervisor de sistemas, desarrollo, tecnología y proyectos | 506,67 |
| B2 | Analista de calidad de software / administrador de BD | 505,97 |
| C1 | Analista / programador semi senior de software | 504,56 |
| C3 | Programador junior de software | 500,80 |
| D1 | Técnico de help desk | 498,93 |
| E2 | Menor valor de la rama (cargo no contemplado) | 493,29 |

Si el sueldo de un empleado es menor al mínimo de su estructura, el rol guarda un aviso (no bloquea la generación), y la tabla de remuneraciones muestra el mínimo junto a cada cargo. Los cuatro socios están en A1 y el Programador Junior en C3 (mínimo $ 500,80; sueldo $ 510). Todos cobran sobre el mínimo de su estructura (sección 7).

---

## 6. Ejemplos resueltos a mano

Los dos casos son de referencia. El primero (María) es un caso de prueba del self-check de `calculos.py`, no un empleado de la semilla. El segundo (Sebastián) es el Gerente General de FERIAUTO, con datos de la semilla. El self-check también prueba la rebaja con María (gastos $ 8.000 y 2 cargas), donde el impuesto queda en 0; una rebaja con impuesto positivo se ilustra en la sección 5.6.

### 6.1 María López (caso de prueba)

Datos: sueldo $ 1.500, 30 días, 10 h al 50%, comisión $ 200, ingreso el 15/01/2024 (más de un año), sin gastos personales ni cargas. Décimos y fondos acumulados (no mensualizados). Periodo: octubre 2026.

``` text
Valor hora              1.500 / 240                     = 6,25
HE 50%                  10 × 6,25 × 1,5                 = 93,75
TOTAL GRAVADO           1.500 + 93,75 + 200             = 1.793,75
IESS personal           1.793,75 × 9,45%                = 169,51
Base IR anual           (1.793,75 − 169,51) × 12        = 19.490,88
Impuesto causado        167 + 10% × (19.490,88 − 15.549) = 561,19
Rebaja GP               sin gastos personales           = 0,00
IR anual                561,19 − 0,00                   = 561,19
IR mensual              561,19 / 12                     = 46,77
DESCUENTOS              169,51 + 46,77                  = 216,28
NETO A RECIBIR          1.793,75 − 216,28               = 1.577,47
```

Provisiones:

| Concepto | Cálculo | Valor |
| ---------- | --------- | ------: |
| 13° | 1.793,75 / 12 | $ 149,48 |
| 14° | 482 / 12 × 30/30 | $ 40,17 |
| Vacaciones | 1.793,75 / 24 | $ 74,74 |
| Fondos de reserva | 1.793,75 × 8,33% | $ 149,42 |
| Aporte patronal | 1.793,75 × 11,15% | $ 200,00 |
| IECE + SECAP | 1.793,75 × 1% | $ 17,94 |
| **Total provisiones** | | **$ 631,75** |

Cadena completa:

``` text
Sueldo bruto (gravado)  $ 1.793,75
− Descuentos            $   216,28   (IESS 169,51 + IR 46,77)
= NETO A RECIBIR        $ 1.577,47
Costo empleador         $ 1.793,75 + provisiones 631,75 = $ 2.425,50
```

Como María acumula los fondos, no se pagan en el rol. Si los mensualizara, su neto sería $ 1.726,89 (suma los $ 149,42 como no gravados); IESS, IR y costo no cambian.

### 6.2 Sebastián Constante (Gerente General)

Datos: sueldo $ 550, 30 días, sin horas extra ni comisiones, sin gastos personales ni cargas. Ingreso el 01/09/2026, contrato indefinido, Código del Trabajo. Décimos acumulados y fondos mensualizados (por defecto), pero todavía no hay fondos que pagar porque no cumple 365 días. Periodo: octubre 2026.

``` text
TOTAL GRAVADO           550 × 30 / 30                   = 550,00
IESS personal           550 × 9,45%                     = 51,98
Base IR anual           (550 − 51,98) × 12              = 5.976,24
Impuesto causado        menor a 12.208: tramo 0%        = 0,00
IR mensual              0 / 12                          = 0,00
DESCUENTOS              51,98 + 0,00                    = 51,98
NETO A RECIBIR          550,00 − 51,98                  = 498,02
```

Provisiones:

| Concepto | Cálculo | Valor |
| ---------- | --------- | ------: |
| 13° | 550 / 12 | $ 45,83 |
| 14° | 482 / 12 × 30/30 | $ 40,17 |
| Vacaciones | 550 / 24 | $ 22,92 |
| Fondos de reserva | 0: cumple 365 días en sep 2027 | $ 0,00 |
| Aporte patronal | 550 × 11,15% | $ 61,33 |
| IECE + SECAP | 550 × 1% | $ 5,50 |
| **Total provisiones** | | **$ 175,75** |

Cadena completa:

``` text
Sueldo bruto (gravado)  $ 550,00
− Descuentos            $  51,98   (IESS 51,98 + IR 0,00)
= NETO A RECIBIR        $ 498,02
Costo empleador         $ 550,00 + provisiones 175,75 = $ 725,75
```

Los décimos están acumulados, así que no suman al neto. Si se mensualizaran, cada uno sumaría al neto, como en 6.1.

---

## 7. Decisiones y simplificaciones

| Decisión | Motivo |
| ---------- | -------- |
| El IR resta el IESS personal (base = (gravado − IESS) × 12) | Es lo que hace el SRI. |
| La rebaja por gastos personales resta del impuesto, no de la base, y no deja impuesto negativo | Así lo marca la norma: 18% del menor entre gastos y tope por cargas. El sistema no valida el formulario de gastos personales. |
| Retención = proyección del mes × 12 / 12 | Simplificación. Un sistema real reliquida cada mes: (IR proyectado − retenido) / meses restantes. Aquí no se reliquida con lo ganado en meses previos. |
| 13° y vacaciones se calculan sobre el total gravado, no solo sobre el sueldo | El Código del Trabajo incluye horas extras y comisiones en la base. |
| 14° sobre el SBU proporcional a los días | El 14° se paga sobre el SBU, no sobre el sueldo. |
| Fondos completos si cumple 365 días al cierre del mes | La ley prorratea el mes 13. Aquí se simplifica a todo o nada. |
| Fondos mensualizados por defecto; décimos acumulados por defecto | Por ley, los fondos se pagan mensualizados salvo pedido de acumularlos en el IESS. Los décimos se acumulan salvo pedido de mensualizarlos. Lo mensualizado no paga IESS ni IR. Pendiente de confirmar la exención de IR (sección 10). |
| IECE 0,5% + SECAP 0,5% se muestran aparte, adicionales al 11,15% | Son costo del empleador. El costo patronal total suma 12,15%. |
| Recargo nocturno del 25% no incluido | Fuera del alcance del taller. |
| Decimal con redondeo half-up por línea | Evita errores de punto flotante y el redondeo bancario de `round()`. Los valores se guardan como float en SQLite al final. |
| Cédula: módulo 10, provincia 01-24 o 30, tercer dígito menor a 6 | Valida el formato. No consulta el Registro Civil. |
| Avisos: sueldo menor al SBU o al mínimo sectorial de su estructura, más de 48 h al 50% al mes, neto negativo | Son advertencias que se guardan en el rol. No bloquean la generación. |
| Sueldos de arranque sobre el mínimo de su estructura y con jerarquía (Gerente General > directores > programador junior) | El mercado paga unos 1.200–1.800 a directores (Paylab y Jobint, abr-2026), pero el contrato con el GAD ($ 4.500) no lo cubre. Subir a esos montos deja el resultado negativo (sección 8, paso 7). |
| El tipo de contrato es informativo | No cambia ningún cálculo. |
| Fechas de pago solo informativas | No cambian ningún monto (sección 5.8). |
| Sin login, sin PDF y sin cierre o aprobación de roles | Es una demo de un solo usuario. Para imprimir se usa el navegador. |

---

## 8. Guion sugerido para la demo (PEA 3, ~6 min)

1. **Empleados:** 5 en total: los 4 socios de FERIAUTO y el Programador Junior Andrés Villacís (contratado, no socio; nombre ficticio), con su departamento y su jefe inmediato.
2. **Organigrama** (`/organigrama`): explicar las líneas de autoridad (desde "reporta a") y la función de cada cargo. Tiene 3 niveles: Gerente General, Director de Tecnología (Pablo Montero) y Programador Junior, que le reporta a él.
3. **Tabla de remuneraciones:** recorrer cada rubro (aportes, 13.º, 14.º, vacaciones, fondos y costo) y explicar por qué cada sueldo supera el mínimo de su estructura (A1: $ 507,37; C3 del programador: $ 500,80). Totales de los 5 trabajadores: remuneraciones $ 2.650,00; aporte personal $ 250,45; patronal $ 322,00; 13.º $ 220,84; 14.º $ 200,85; vacaciones $ 110,41; costo $ 3.504,10. El Programador Junior tiene costo $ 675,89 y neto $ 461,80.
4. **¿Es sostenible?:** con el contrato de $ 4.500, el costo del personal ($ 3.504,10, 77,9 %) más otros costos ($ 530) deja un margen de $ 465,90 (10,4 %). Desde el mes 13, los fondos de reserva (+$ 220,74) lo bajan a $ 245,16 (5,4 %). El punto de equilibrio es $ 4.034,10.
5. **Rol de octubre 2026:** generarlo (neto total $ 2.399,55; costo $ 3.504,10) y abrir el rol individual de **Sebastián Constante**. Revisar "¿Cómo se calculó?" y compararlo con la sección 6.2.
6. **Excel de la tabla** (*Exportar Excel* en el organigrama): cambiar un sueldo en Excel y mostrar cómo se recalcula todo.
7. **Sueldos de mercado en vivo:** editar a un director y subir su sueldo a 1.200 (p. ej.), luego recargar el organigrama: el margen de "¿Es sostenible?" se vuelve negativo.
8. **Reiniciar demo** (pie de página) para dejarlo listo para el siguiente grupo.

---

## 9. Estructura de archivos

``` text
roles_pago/
├── app.py            rutas Flask, esquema SQLite (versión 4), validaciones, guardado y organigrama
├── calculos.py       motor de cálculo puro, tabla sectorial y self-check
├── exportar.py       libro Excel (.xlsx) del rol y de la tabla de remuneraciones con openpyxl + self-check
├── templates/        plantillas Jinja: base, roles, empleados, empleado_form,
│                     rol_nuevo, rol_ver, rol_individual, organigrama
├── static/           style.css (sistema visual "libro contable") y favicon.svg
├── iniciar.bat / iniciar.sh   arranque con doble clic (crea .venv e instala dependencias)
├── requirements.txt  flask, openpyxl
├── roles.db          base SQLite local, se crea sola (no se sube a git)
└── roles_v<N>_respaldo.db     base de un esquema anterior, respaldada al cambiar de versión
```

---

## 10. Fuentes y verificación

Las reglas se contrastaron con prensa y calculadoras ecuatorianas: tabla de IR 2026, SBU, aportes IESS e IECE/SECAP, canasta y tabla de cargas, fondos mensualizados, décimo cuarto, horas extras y nocturnas.

**Pendiente de confirmar con fuente oficial:** la exención de IR de los fondos de reserva mensualizados (el código los trata como exentos) y el prorrateo del mes 13.

- Tabla IR 2026 (SRI, Res. NAC-DGERCGC25-00000043):
  - <https://www.eluniverso.com/noticias/economia/lo-que-debe-saber-sobre-el-impuesto-a-la-renta-de-2026-nota/>
  - <https://www.ecija.com/actualidad-insights/sri-publica-nuevas-tablas-para-liquidar-el-impuesto-a-la-renta-2026/>
  - <https://nmslaw.com.ec/blog/2026/01/05/tablas-impuesto-renta-2026-ecuador/>
- SBU 2026 de $ 482: <https://www.vistazo.com/2025-12-15-salario-basico-usd-482-2026-ecuador-incremento-dolares-IC10565269>
- Salarios mínimos sectoriales (comisión 12, rama 1, CIIU J62), R.O. 2.º Suplemento 708 (20-dic-2024), Anexo 1, págs. 64-65, y Acuerdo Ministerial MDT-2024-301. Para 2026 no se emitió tabla nueva: según el Ministerio del Trabajo rige la de 2025.
  - <https://www.trabajo.gob.ec/wp-content/uploads/2024/12/ACUERDO-MINISTERIAL-NRO.-MDT-2024-301-signed.pdf>
- Mercado de directores (referencia de 1.200 a 1.800 dólares): Paylab y Jobint, abril de 2026.
- Aportes IESS (9,45% / 11,15%) e IECE/SECAP 1%: <https://runahr.com/ec/recursos/salario/calculadora-de-salario/>
- Canasta $ 821,80 y tabla de cargas: <https://elmercurio.com.ec/?p=1239654>
- Fondos de reserva mensualizados por defecto: <https://primicias.ec/economia/fondos-reserva-iess-consejos-acumular-mensualizar-88720>
- Décimo cuarto (fechas de pago): <https://www.expreso.ec/actualidad/economia/decimo-cuarto-sueldo-en-ecuador-2026-cuanto-deben-pagarte-275386.html>
- Horas extras y nocturnas: <https://www.eldiario.ec/ecuador/jornada-laboral-en-ecuador-esto-debes-saber-sobre-el-pago-de-horas-extras-y-el-tiempo-maximo-de-trabajo-por-semana-11032026/>
- App de referencia funcional: <https://franzpc.com/apps/roles_pago_ecuador/>
