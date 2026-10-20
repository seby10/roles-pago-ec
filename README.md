# Roles de Pago Ecuador 2026 (demo académica)

Módulo demostrativo para un taller de clase: calcula el rol de pagos mensual de una nómina ecuatoriana (ingresos, descuentos IESS e IR, neto a recibir y costo del empleador). Está hecho con Flask, SQLite y CSS propio (sin Bootstrap ni npm).

> **Aviso:** es una demo académica. No la uses en producción ni para pagar sueldos reales. El cálculo simplifica varios puntos legales (ver sección 7).

---

## 1. Cómo ejecutar

Solo necesitas **Python 3.9 o superior** ([python.org/downloads](https://www.python.org/downloads/); en Windows marca *"Add python.exe to PATH"* al instalar). Cada persona corre la app en su propia compu con su propia base de datos.

**Paso 1 — Descargar** (recomendado con git, así luego actualizas con un comando):

```bash
git clone https://github.com/seby10/roles-pago-ec.git
cd roles-pago-ec
```

El repositorio es privado: acepta primero la invitación que llega a tu correo de GitHub. La primera vez git te pedirá iniciar sesión (en Windows se abre el navegador; en macOS/Linux puedes usar `gh auth login`). Para traer cambios nuevos: `git pull` dentro de la carpeta.

¿Sin git? En la página del repo: botón verde **Code → Download ZIP** y descomprimir (para actualizar hay que volver a descargarlo).

**Paso 2 — Abrir.**

| Sistema | Qué hacer |
| --- | --- |
| Windows | Doble clic en **`iniciar.bat`** |
| macOS / Linux | En una terminal dentro de la carpeta: `sh iniciar.sh` |

La primera vez tarda ~30 s (crea un entorno `.venv` e instala Flask y openpyxl; necesita internet). Luego se abre solo el navegador en **http://127.0.0.1:5050**. Para cerrar, cierra la ventana de la terminal o presiona `Ctrl+C`.

**Manual (si prefieres):**

```bash
pip install -r requirements.txt
python app.py          # http://127.0.0.1:5050
python calculos.py     # self-check: imprime "OK: ..." si los casos resueltos a mano cuadran
```

**Reiniciar la demo:** enlace *Reiniciar demo* en el pie de página (vuelve a los 4 empleados de ejemplo y borra los roles). También puedes borrar `roles.db`; se recrea sola.

**Problemas comunes**

| Síntoma | Solución |
| --- | --- |
| "Necesitas Python 3.9 o superior" | Instala Python y, en Windows, reinstala marcando *Add python.exe to PATH*. |
| Linux: error al crear `.venv` | `sudo apt install python3-venv` y vuelve a ejecutar. |
| "Address already in use" | Otra app usa el puerto. Ejecuta con otro: `PORT=5051 python app.py` (Windows: `set PORT=5051 && python app.py`). |
| Se ve con otra tipografía | Sin internet no cargan las fuentes de Google; la app funciona igual con las del sistema. |

> ¿Por qué no está publicada en Vercel? Vercel ejecuta funciones sin disco persistente: la base SQLite se perdería entre peticiones y todos compartirían los mismos datos. Para un taller conviene que cada estudiante tenga su copia local.

---

## 2. Flujo en 6 pasos

| # | Paso | Ruta | Qué ocurre |
| --- | ------ | ------ | ------------ |
| 1 | Empleados (CRUD) | `/empleados` | Alta, edición, activar/inactivar y eliminar. Incluye mensualizar décimos y fondos, gastos personales anuales y cargas familiares (0 a 20). Un empleado que ya aparece en un rol generado no se elimina: se inactiva. |
| 2 | Nuevo rol | `/roles/nuevo` | Eliges año y mes. Por cada empleado activo hay una fila editable con días (30 por defecto), horas 50%, horas 100%, comisiones, anticipos de sueldo y préstamo quirografario IESS. Si el rol del periodo ya existe, sus novedades se precargan. La columna **Neto estimado** se recalcula mientras escribes (`POST /roles/preview` usa el mismo `calculos.py`, sin guardar). `Enter` baja a la fila siguiente. |
| 3 | Generar | `POST /roles/generar` | Por cada empleado activo llama a `calculos.calcular_rol()`, una función pura que no toca la base de datos. Valida días entre 1 y 30 y valores numéricos ≥ 0. |
| 4 | Guardar | (mismo POST) | Dentro de una transacción: borra el rol previo del mismo periodo (si existe), guarda la cabecera y luego los detalles. Regenerar reemplaza el rol. |
| 5 | Vista consolidada | `/roles/<id>` | Totales de ingresos, descuentos y neto por empleado. El costo empleador va en una tabla aparte (provisiones y aportes patronales) que no afecta el neto. Filas clicables; en celular se muestra como tarjetas. Se imprime en A4 horizontal. **Exportar Excel** (`/roles/<id>/excel`) descarga un `.xlsx` con 4 hojas: Rol de pagos, Costo empleador, Planilla IESS y Transferencias (archivo para el banco), con totales como fórmulas `SUM`. |
| 6 | Rol individual | `/roles/<id>/empleado/<det_id>` | Rol imprimible en A4 con firmas, fechas de pago informativas y la sección "¿Cómo se calculó este rol?" de 9 pasos. Botones ← / → (o flechas del teclado) para pasar al siguiente empleado. |

El listado de roles está en `/`.

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
| `empleados` | `cedula` (UNIQUE), `nombres`, `apellidos`, `cargo`, `sueldo`, `fecha_ingreso`, `tipo_contrato`, `activo`, `mensualiza_decimos` (0 por defecto), `mensualiza_fondos` (1 por defecto), `gastos_personales`, `cargas` | Maestro de empleados. |
| `roles_cabecera` | `anio`, `mes` (**UNIQUE**), `generado_en`, `n_empleados`, `total_ingresos`, `total_descuentos`, `total_neto`, `total_costo`, `total_iess`, `total_ir` | Un registro por periodo con los totales. `total_iess` = aporte personal + patronal + IECE/SECAP (lo que se transfiere al IESS). |
| `roles_detalle` | `rol_id` (FK, `ON DELETE CASCADE`), `empleado_id` (FK), **snapshot** de `nombre`, `cedula`, `cargo`, `sueldo`; novedades (`dias`, `h50`, `h100`, `comisiones`, `anticipos`, `prestamos_iess`); resultados (`total_gravado`, `iess_personal`, `rebaja_gp`, `ir`, `neto`, `costo_total`, etc.) | Una fila por empleado y periodo. |

**Por qué `roles_detalle` guarda un snapshot:** al generar el rol copia nombre, cédula, cargo y sueldo. Si luego cambias el sueldo del empleado, los roles de meses pasados no cambian.

**Por qué `UNIQUE(anio, mes)`:** solo puede existir un rol por periodo. Regenerar borra la cabecera anterior (el detalle cae en cascada) en lugar de duplicar datos.

**Versión del esquema:** `PRAGMA user_version` guarda `SCHEMA_VERSION` (hoy 2). Si al arrancar la base tiene otra versión, se renombra como `roles_v<N>_respaldo.db` y se crea una nueva con los empleados de ejemplo. Nada se borra en silencio.

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

### 5.7 Mensualización

Por ley, los **fondos de reserva** se pagan cada mes desde el mes 13, salvo que el trabajador pida acumularlos en el IESS; por eso *mensualiza fondos* viene marcado por defecto. Los **décimos** (13° y 14°) se acumulan, salvo que el trabajador pida mensualizarlos.

Lo mensualizado se paga en el rol como ingreso **no gravado**: no paga IESS ni IR, pero sube el neto. El costo del empleador no cambia, porque la provisión se calcula igual aunque el beneficio se pague hoy o en diciembre.

### 5.8 Fechas de pago (informativas)

El rol individual muestra cuándo se paga cada beneficio: 13° hasta el 24 de diciembre; 14° hasta el 15 de agosto para Sierra/Amazonía o hasta el 15 de marzo para Costa/Galápagos. La fecha sale de `EMPRESA["region"]` en `app.py` (la demo está en Sierra, por eso dice "paga 15 ago"; con "Costa" diría "paga 15 mar"). Es solo informativa: la región no altera ningún monto.

---

## 6. Ejemplos resueltos a mano

El primer caso es el del self-check de `calculos.py`. El segundo (Jorge) no está en el self-check; sus cifras salen de `calcular_rol()` con los mismos datos. El self-check también prueba la rebaja con María (gastos $ 8.000 y 2 cargas), donde el impuesto queda en 0.

### 6.1 María López

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

### 6.2 Jorge Castillo

Datos: gerente general, sueldo $ 3.200, 8 h al 100%, sin comisiones, gastos personales anuales proyectados de $ 8.000, 2 cargas familiares, ingreso el 01/06/2020, fondos mensualizados (por defecto). Periodo: octubre 2026.

``` text
Valor hora              3.200 / 240                     = 13,333…
HE 100%                 8 × 13,333… × 2                 = 213,33
TOTAL GRAVADO           3.200 + 213,33                  = 3.413,33
IESS personal           3.413,33 × 9,45%                = 322,56
Base IR anual           (3.413,33 − 322,56) × 12        = 37.089,24
Impuesto causado        2.678 + 20% × (37.089,24 − 35.136) = 3.068,65
Tope GP                 11 canastas × $ 821,80          = 9.039,80
Rebaja GP               18% × menor(8.000 ; 9.039,80)   = 1.440,00
IR anual                3.068,65 − 1.440,00             = 1.628,65
IR mensual              1.628,65 / 12                   = 135,72
```

Jorge tiene fondos mensualizados ($ 284,33 no gravados). Entran al neto, no a la base del IR:

``` text
Total ingresos          3.413,33 + 284,33 (fondos)      = 3.697,66
Descuentos              322,56 + 135,72                 = 458,28
NETO A RECIBIR                                          = 3.239,38
Costo empleador         3.413,33 + provisiones 1.165,88 = 4.579,21
```

Si sus gastos personales fueran 0, la rebaja sería 0 y el IR mensual subiría a $ 255,72.

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
| Avisos: sueldo menor al SBU, más de 48 h al 50% al mes, neto negativo | Son advertencias que se guardan en el rol. No bloquean la generación. |
| El tipo de contrato es informativo | No cambia ningún cálculo. |
| Fechas de pago solo informativas | No cambian ningún monto (sección 5.8). |
| Sin login, sin PDF y sin cierre o aprobación de roles | Es una demo de un solo usuario. Para imprimir se usa el navegador. |

---

## 8. Guion sugerido para la demo (~5 min)

1. Mostrar la pestaña **Empleados** con los 4 ejemplos, su antigüedad y su estado.
2. Crear un empleado nuevo y probar una cédula inválida: el formulario la rechaza.
3. En **Generar rol del mes** (octubre 2026), escribir 10 h al 50% y comisión $ 200 para **María López** mirando la columna *Neto estimado*: cambia al instante (con 20 h baja la proporción neta porque sube de tramo de IR). Luego **Calcular y generar rol**.
4. Abrir el rol consolidado y explicar la barra de neto, descuentos y aportes/provisiones.
5. Abrir el rol individual de María, recorrer "¿Cómo se calculó este rol?" y compararlo con la sección 6.1.
6. Editar a María, marcar **mensualizar décimo tercero y cuarto** y regenerar el rol. El neto sube de $ 1.577,47 a $ 1.767,12 (suma el 13° y el 14°), y el costo empleador se mantiene en $ 2.425,50.
7. **Jorge Castillo**: en el nuevo rol, poner 8 h al 100%. Con sus gastos personales de $ 8.000 y 2 cargas, la retención es $ 135,72. Editar sus gastos a 0 y regenerar: la retención sube a $ 255,72 (desaparece la rebaja de $ 1.440).
8. **Carlos Pérez** (sueldo $ 650, décimos y fondos mensualizados): en su rol individual, 13°, 14° y fondos aparecen como "pagado en rol". Su neto es $ 737,06 y su costo empleador $ 904,55. Mostrar que IESS e IR se calculan solo sobre $ 650.
9. **Exportar Excel** desde el consolidado: abrir la hoja *Planilla IESS* (lo que se paga al IESS) y *Transferencias* (lo que se paga al banco), y mostrar que los totales son fórmulas.
10. Usar **Reiniciar demo** (pie de página) para dejarlo listo para el siguiente grupo.

---

## 9. Estructura de archivos

``` text
roles_pago/
├── app.py            rutas Flask, esquema SQLite (versión 2), validaciones y guardado
├── calculos.py       motor de cálculo puro + self-check
├── exportar.py       libro Excel (.xlsx) del rol con openpyxl + self-check
├── templates/        plantillas Jinja: base, roles, empleados, empleado_form,
│                     rol_nuevo, rol_ver, rol_individual
├── static/           style.css (sistema visual "libro contable") y favicon.svg
├── iniciar.bat / iniciar.sh   arranque con doble clic (crea .venv e instala dependencias)
├── requirements.txt  flask, openpyxl
└── roles.db          base SQLite local, se crea sola (no se sube a git)
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
- Aportes IESS (9,45% / 11,15%) e IECE/SECAP 1%: <https://runahr.com/ec/recursos/salario/calculadora-de-salario/>
- Canasta $ 821,80 y tabla de cargas: <https://elmercurio.com.ec/?p=1239654>
- Fondos de reserva mensualizados por defecto: <https://primicias.ec/economia/fondos-reserva-iess-consejos-acumular-mensualizar-88720>
- Décimo cuarto (fechas de pago): <https://www.expreso.ec/actualidad/economia/decimo-cuarto-sueldo-en-ecuador-2026-cuanto-deben-pagarte-275386.html>
- Horas extras y nocturnas: <https://www.eldiario.ec/ecuador/jornada-laboral-en-ecuador-esto-debes-saber-sobre-el-pago-de-horas-extras-y-el-tiempo-maximo-de-trabajo-por-semana-11032026/>
- App de referencia funcional: <https://franzpc.com/apps/roles_pago_ecuador/>
