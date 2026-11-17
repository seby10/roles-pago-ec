# Roles de Pago Ecuador 2026 (demo académica)

Módulo demostrativo para un taller de clase: calcula el rol de pagos mensual de una nómina ecuatoriana (ingresos, descuentos IESS e IR, neto a recibir y costo del empleador) y lo acompaña con un resumen de gestión, el organigrama, escalas salariales y parámetros editables. Soporta cuatro regímenes laborales (Código del Trabajo, LOSEP, LOEP y LOES). Está hecho con Flask, SQLite y CSS propio (sin Bootstrap ni npm).

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

El script crea un entorno virtual (`.venv`) con las dependencias del proyecto (Flask y openpyxl) para no tocar tu Python global, y abre **<http://127.0.0.1:5050>**. La primera vez tarda unos segundos porque descarga esas dependencias; después arranca directo. Se detiene con `Ctrl+C`.

Para traer cambios del repositorio: `git pull`.

Si prefieres hacerlo a mano:

```bash
pip install -r requirements.txt
python app.py          # http://127.0.0.1:5050
python calculos.py     # self-check del motor de cálculo contra casos resueltos a mano
python exportar.py     # self-check de los libros Excel (estructura y fórmulas)
```

Los dos self-checks terminan con un mensaje `OK` si todo coincide. `exportar.py` además recalcula el Excel con LibreOffice si lo tienes instalado; si no, omite ese paso y lo avisa.

Para volver a los datos de ejemplo usa **Reiniciar demo**, en el pie de la barra lateral. Borrar `roles.db` tiene el mismo efecto. Reiniciar borra roles, empleados y parámetros (incluido el logo y las escalas editadas).

**Si actualizas el código y cambia el esquema de la base**, al arrancar la app renombra tu base anterior como `roles_v<N>_respaldo.db` y crea una nueva con los datos de ejemplo. Los datos de la base vieja no se migran: quedan en el respaldo por si los necesitas (ver sección 4).

| Si pasa esto | Prueba |
| --- | --- |
| El script dice que falta Python | En Windows, Python debe estar en el PATH (es una casilla del instalador). |
| Linux no puede crear `.venv` | `sudo apt install python3-venv` |
| "Address already in use" | Otro programa usa el 5050: `PORT=5051 python app.py` (en Windows: `set PORT=5051 && python app.py`). |
| La tipografía se ve distinta | Las fuentes vienen de Google Fonts; sin internet se usan las del sistema y todo funciona igual. |
| Aparece un archivo `roles_v5_respaldo.db` (u otra versión) | Es la base anterior, respaldada al subir la versión del esquema. Puedes borrarlo si no lo necesitas; git lo ignora. |

> **¿Por qué no está en Vercel?** Vercel no guarda archivos entre peticiones: la base SQLite se perdería y además todos compartirían los mismos datos. Para un taller tiene más sentido que cada uno corra su copia. Si necesitas un enlace público para que otra persona lo revise, `PUBLICAR.md` explica cómo ponerlo en PythonAnywhere.

**Modo solo lectura.** Si defines la variable de entorno `EDIT_PASSWORD` (y, conviene, `SECRET_KEY`), la app queda en solo lectura: se puede navegar, descargar los Excel y usar la vista previa de novedades, pero guardar cambios exige ingresar la clave desde *Modo edición* (pie de la barra lateral, ruta `/login`). Sin esa variable, que es el uso local normal, todo es editable.

---

## 2. Navegación y flujo

### 2.1 Barra lateral

La app se organiza con una barra lateral a la izquierda. En escritorio se puede **contraer** con el botón del pie y el navegador recuerda tu elección (la guarda en `localStorage`, no en la base). En el teléfono (menos de 900 px) la barra es un **panel** que se abre con el botón de menú de la parte superior y se cierra con `Esc`, tocando fuera de él o con *Cerrar menú*. En el pie también ves el régimen vigente (con SBU y aportes IESS) como acceso directo a Parámetros, y los enlaces *Reiniciar demo* o *Modo edición*.

| Pestaña | Ruta | Para qué sirve |
| --- | --- | --- |
| Resumen | `/` | Página de inicio: cifras del mes, costo por departamento, próximas obligaciones, últimos roles, alertas y sostenibilidad del contrato (sección 2.2). |
| Empleados | `/empleados` | Alta, edición, activar/inactivar y eliminar (sección 2.3, paso 1). |
| Organigrama | `/organigrama` | Árbol de cargos, tabla de remuneraciones y "¿Es sostenible?" (sección 2.3, extra). |
| Roles de pago | `/roles` | Historial de roles generados y acceso a *Generar rol del mes* (sección 2.3, pasos 2 a 6). Antes esta lista estaba en `/`. |
| Escalas salariales | `/escalas` | La escala de cada régimen, editable (sección 5.9). |
| Parámetros | `/parametros` | Datos de la empresa, logo, régimen y valores de cálculo (sección 2.4). |

### 2.2 Resumen (`/`)

Es lo primero que se ve y se calcula con los empleados activos, sin novedades del mes (30 días, sin horas extra), con el mismo motor que el rol.

- **Cifras del mes:** trabajadores activos (con n.º de departamentos y cargos), remuneraciones, costo mensual de la empresa (con cuánto cuesta cada dólar de sueldo) y resultado frente al contrato con su porcentaje de margen.
- **Costo mensual por departamento:** barras por departamento, y debajo "¿De qué está hecho el costo?": sueldos, aportes patronales y provisiones (décimos, vacaciones y fondos).
- **Próximas obligaciones:** los seis vencimientos más cercanos entre planilla de aportes al IESS (día 15), retenciones en la fuente al SRI (formulario 103), pago del décimo tercero (24 de diciembre), pago del décimo cuarto, participación de utilidades (15 de abril, solo Código del Trabajo) y entrega del formulario 107 (31 de enero). El día de pago al SRI depende del **9.º dígito del RUC** y el mes del décimo cuarto depende de la **región** (ambos se editan en Parámetros). Las fechas están fijas en `obligaciones()` de `app.py` y no se corren por fines de semana o feriados: contrástalas con el calendario oficial antes de usarlas como recordatorio real.
- **Últimos roles:** columnas de neto y costo de los últimos seis roles; cada columna abre el rol.
- **Alertas:** trabajadores cuyo sueldo no cumple la escala de su régimen y trabajadores que **cumplen un año en los próximos 90 días** (desde el mes 13 empiezan los fondos de reserva y el costo sube). Si no hay nada, indica que todo está en regla.
- **¿Es sostenible?:** ingreso del contrato − costo de personal − otros costos = resultado mensual, con el punto de equilibrio y el efecto de los fondos de reserva desde el mes 13. El mismo panel aparece al final del organigrama.

### 2.3 Flujo del rol en 6 pasos

| # | Paso | Ruta | Qué ocurre |
| --- | ------ | ------ | ------------ |
| 1 | Empleados (CRUD) | `/empleados` | Alta, edición, activar/inactivar y eliminar. Cada empleado tiene departamento (los que definas en Parámetros), **reporta a** (jefe inmediato; vacío = máxima autoridad), función principal, tipo de contrato (la lista depende del régimen) y un **grado de la escala del régimen** (sección 5.9). En escalas de remuneración fija, al elegir el grado el sueldo se completa solo. También se configuran los beneficios (13.º y fondos mensualizados por defecto, 14.º acumulado por defecto), gastos personales anuales, cargas familiares (0 a 20) y la casilla de enfermedad catastrófica (sección 5.6). El formulario impide reportarse a sí mismo y formar ciclos. No se puede eliminar a un jefe que tiene subordinados: primero hay que cambiarles la línea de reporte. Un empleado que ya aparece en un rol generado no se elimina: se inactiva. La lista marca con "revisar escala" a quien no cumple la regla de la escala. |
| 2 | Nuevo rol | `/roles/nuevo` | Eliges año y mes. Por cada empleado activo hay una fila editable con días (30 por defecto), horas suplementarias, horas extraordinarias, comisiones, anticipos de sueldo y préstamo quirografario IESS. Si el rol del periodo ya existe, sus novedades se precargan. La columna **Neto estimado** se recalcula mientras escribes (`POST /roles/preview` usa el mismo `calculos.py`, sin guardar). `Enter` baja a la fila siguiente. |
| 3 | Generar | `POST /roles/generar` | Por cada empleado activo llama a `calculos.calcular_rol()`, una función pura que no toca la base de datos, con los parámetros vigentes del régimen. Valida días entre 1 y 30 y valores numéricos ≥ 0. |
| 4 | Guardar | (mismo POST) | Dentro de una transacción: borra el rol previo del mismo periodo (si existe), guarda la cabecera (con el régimen y los porcentajes usados) y luego los detalles. Regenerar reemplaza el rol. |
| 5 | Vista consolidada | `/roles/<id>` | Totales de ingresos, descuentos y neto por empleado. El costo empleador va en una tabla aparte (provisiones y aportes patronales) que no afecta el neto. Filas clicables; en celular se muestra como tarjetas. Se imprime en A4 horizontal. **Exportar Excel** (`/roles/<id>/excel`) descarga un `.xlsx` con 4 hojas: Rol de pagos, Costo empleador, Planilla IESS y Transferencias (archivo para el banco), con totales como fórmulas `SUM`. |
| 6 | Rol individual | `/roles/<id>/empleado/<det_id>` | Rol imprimible en A4 con logo, firmas y fechas de pago informativas; el costo del empleador se ve en pantalla pero no sale impreso (es información de la empresa, no del trabajador). Incluye la sección "¿Cómo se calculó este rol?" de 9 pasos. Botones ← / → (o flechas del teclado) para pasar al siguiente empleado. |
| extra | Organigrama y remuneraciones | `/organigrama` | Árbol de cargos con líneas de autoridad, generado desde "reporta a". Cada tarjeta muestra departamento, cargo, nombre, función, grado y sueldo, con una etiqueta "cumple" o "revisar escala". Debajo está la tabla de remuneraciones que pide la PEA 3 y el panel **"¿Es sostenible?"**. Como el organigrama y la tabla salen de los mismos datos, todo cargo del organigrama aparece en la tabla. |

Son dos libros Excel distintos. El del **rol** (`/roles/<id>/excel`, paso 5) tiene 4 hojas de nómina y banco, y sus encabezados usan los porcentajes con que se generó ese rol. El de la **tabla de remuneraciones** (`/organigrama/excel`, botón *Exportar Excel* del organigrama) tiene tres hojas: *Parámetros* (celdas amarillas editables y la tabla del IR como rango con nombre), *Tabla de remuneraciones* (número de trabajadores y remuneración como entradas; aportes, 13.º, 14.º, vacaciones, fondos y costo como fórmulas, más el bloque de sostenibilidad) y *Cálculo detallado* (el Gerente General paso a paso, con el IR por `VLOOKUP`). Al cambiar el sueldo o el n.º de trabajadores, todo se recalcula en Excel.

### 2.4 Parámetros (`/parametros`)

Todo lo que antes estaba fijo en el código ahora se edita aquí y se guarda en la base.

- **Logo:** PNG, JPG, WEBP o SVG de hasta 512 KB (mejor cuadrado). Aparece en la barra lateral, en la pestaña del navegador y en los roles individuales impresos. Por defecto se usa `static/logo.svg` (el de FeriAuto); *Volver al logo por defecto* lo restaura. El logo se guarda en la base (no como archivo) y se sirve desde `/logo`; un SVG subido se entrega con una política que le impide ejecutar scripts.
- **Empresa:** razón social, RUC (13 dígitos), actividad, región (Sierra, Amazonía, Costa o Galápagos), cliente principal, ingreso mensual del contrato, otros costos mensuales y la lista de departamentos (uno por línea). El RUC y la región alimentan las fechas de la agenda del Resumen y las fechas de pago del 14.º. El ingreso y los otros costos alimentan "¿Es sostenible?".
- **Régimen laboral:** Código del Trabajo, LOSEP, LOEP o LOES (sección 5.9 y 5.10 explican qué cambia en cada uno).
- **Valores de cálculo:** SBU, canasta familiar básica, aporte personal y patronal IESS, IECE, SECAP, fondos de reserva, días de vacaciones al año y factores de horas suplementarias y extraordinarias. Junto a cada campo aparece el **valor legal** vigente del régimen y una etiqueta "modificado" si lo cambiaste. *Restablecer valores legales* devuelve estos campos a los del régimen actual. Los límites que valida la app: SBU y canasta mayores que 0, porcentajes de 0 a 100, factores de al menos 1 y vacaciones entre 1 y 60 días.
- **Al cambiar de régimen** y guardar, se cargan los porcentajes legales de ese régimen y se usa su escala salarial. Los empleados cuyo grado no existe en la nueva escala aparecen con aviso y deben elegir uno (Empleados → Editar). El formulario también exige un tipo de contrato de la lista del nuevo régimen. Los sueldos no se modifican solos.
- **Los roles ya generados no cambian.** Cada rol guarda el régimen y los porcentajes con que se calculó, así que editar Parámetros después no altera ni sus pantallas ni su Excel.

Al pie de la página hay dos tablas de consulta: el impuesto a la renta 2026 (igual para todos los regímenes) y la rebaja por gastos personales con sus topes.

---

## 3. Stack y por qué

| Pieza | Por qué |
| ------- | --------- |
| **Flask** | Una sola dependencia de servidor. El código se lee casi como pseudocódigo. |
| **sqlite3** (librería estándar) | No necesita servidor de base de datos: todo está en un archivo, `roles.db`. |
| **Jinja + CSS propio** | Plantillas del lado del servidor y un solo archivo de estilos (`static/style.css`), sin build, sin npm y sin Bootstrap. |
| **openpyxl** | Genera los libros Excel con fórmulas reales. |

Se ejecuta con un solo comando: `python app.py`.

**Diseño "libro contable":** papel cálido, tres colores con significado fijo (verde = neto, arcilla = descuentos, índigo = costo empleador), totales con doble raya contable, celdas en cero como "—" y tablas sin "$" (los valores van en USD). Tipografía: Geist (cifras con dígitos tabulares) e Instrument Serif para títulos, cargadas desde Google Fonts; sin internet, caen a fuentes del sistema. Responsive hasta 375 px.

---

## 4. Esquema de la base de datos

| Tabla | Campos clave | Rol |
| ------- | -------------- | ----- |
| `empleados` | `cedula` (UNIQUE), `nombres`, `apellidos`, `cargo`, `sueldo`, `fecha_ingreso`, `tipo_contrato`, `activo`, `mensualiza_13` (1 por defecto), `mensualiza_14` (0 por defecto), `mensualiza_fondos` (1 por defecto), `gastos_personales`, `cargas`, `catastrofica` (0), `departamento`, `reporta_a` (FK a `empleados.id`; NULL = máxima autoridad), `funcion`, `estructura` (código del grado en la escala del régimen vigente; vacío si no aplica) | Maestro de empleados y organigrama. `reporta_a` define las líneas de autoridad. |
| `parametros` | `clave` (PK), `valor` (texto) | Datos de la empresa, régimen, valores de cálculo y logo (en base64, con su tipo MIME). |
| `escalas` | `regimen`, `codigo`, `denominacion`, `grupo`, `valor`; UNIQUE(`regimen`, `codigo`) | Una escala salarial por régimen, editable desde `/escalas`. |
| `roles_cabecera` | `anio`, `mes` (**UNIQUE**), `generado_en`, `n_empleados`, `total_ingresos`, `total_descuentos`, `total_neto`, `total_costo`, `total_iess`, `total_ir`, `regimen`, `params` (JSON con los porcentajes usados) | Un registro por periodo con los totales. `total_iess` = aporte personal + patronal + IECE/SECAP (lo que se transfiere al IESS). |
| `roles_detalle` | `rol_id` (FK, `ON DELETE CASCADE`), `empleado_id` (FK), **snapshot** de `nombre`, `cedula`, `cargo`, `sueldo`, `mensualiza_13`, `mensualiza_14`, `mensualiza_fondos`, `gastos_personales`, `cargas`, `catastrofica`; novedades (`dias`, `h50`, `h100`, `comisiones`, `anticipos`, `prestamos_iess`); resultados (`total_gravado`, `iess_personal`, `rebaja_gp`, `ir`, `neto`, `costo_total`, etc.) | Una fila por empleado y periodo. |

**Por qué `roles_detalle` guarda un snapshot:** al generar el rol copia nombre, cédula, cargo, sueldo y los beneficios elegidos. Si luego cambias el sueldo del empleado, los roles de meses pasados no cambian. Por la misma razón `roles_cabecera` guarda el régimen y los porcentajes (`params`): si luego cambias Parámetros, el histórico se sigue viendo con los valores con que se calculó.

**Por qué `UNIQUE(anio, mes)`:** solo puede existir un rol por periodo. Regenerar borra la cabecera anterior (el detalle cae en cascada) en lugar de duplicar datos.

**Versión del esquema:** `PRAGMA user_version` guarda `SCHEMA_VERSION` (hoy **7**). La versión 3 agregó organización; la 4 actualizó la semilla; la 5 agregó parámetros, escalas e históricos de cálculo; la 6 inicializó IECE en 0 %. La **7 agrega el expediente de paz y salvo mediante una migración aditiva desde la 6**, conservando empleados, parámetros y roles. Crea antes `roles_v6_pre_paz_salvo_respaldo.db`. Para versiones anteriores a 6 se conserva el comportamiento histórico: respaldo `roles_v<N>_respaldo.db` y recreación con semilla. Consulta [Paz y salvo: guía y fuentes](PAZ_Y_SALVO.md).

---

## 5. Lógica de cálculo

Fuente: `calculos.py`. Los cálculos usan `Decimal` y se redondean a centavos por línea (half-up). Los porcentajes que ves abajo son los **valores legales por defecto** del Código del Trabajo (régimen de la demo); en LOSEP, LOEP y LOES cambian los que se indican en 5.9 y 5.10, y todos se pueden ajustar en Parámetros. La fórmula es la misma para los cuatro regímenes.

### 5.1 Ingresos gravados (pagan IESS e IR)

``` text
valor hora       = sueldo / 240                      (40 h/semana × 4 semanas)
HE suplementarias = h50  × valor hora × factor suplementario   (CT ×1,5 · LOSEP/LOEP/LOES ×1,25)
HE extraordinarias = h100 × valor hora × factor extraordinario (CT ×2   · LOSEP/LOEP/LOES ×1,6)
sueldo ganado   = sueldo × días / 30
TOTAL GRAVADO    = sueldo ganado + HE suplementarias + HE extraordinarias + comisiones
```

Las suplementarias son las que siguen a la jornada; las extraordinarias son las de sábados, domingos, feriados y las de 24:00 a 06:00. El recargo nocturno del 25% no está incluido.

### 5.2 Descuentos

``` text
IESS personal     = gravado × aporte personal         (CT 9,45% · LOSEP/LOEP/LOES 11,45%)
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
vacaciones        = gravado × días de vacaciones / 360   (CT 15 días = 1/24 · LOSEP/LOEP/LOES 30 días = 1/12)
fondos de reserva = gravado × 8,33%                  (solo si cumple 365 días al cierre del mes)
aporte patronal   = gravado × aporte patronal        (CT 11,15% · LOSEP/LOEP/LOES 9,15%)
SECAP 0,5%        = gravado × 0,5%                   (solo CT; adicional al 11,15%. IECE en 0%)
COSTO EMPLEADOR   = gravado + provisiones (13°, 14°, vacaciones, fondos, patronal, SECAP)
```

En el Código del Trabajo el costo patronal de aportes suma 11,65% (11,15% + SECAP 0,5%). El IECE queda en 0% (ver 5.11); si el IESS lo vuelve a cobrar, se pone 0,5% en Parámetros y el total sube a 12,15%. En los regímenes públicos el IECE y el SECAP están en 0. Los fondos de reserva se provisionan siempre que el trabajador cumpla el año; si están mensualizados, además se pagan en el rol (sección 5.7).

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

Rebaja = 18% × menor(gastos personales anuales proyectados, tope). Tope = canastas × canasta familiar básica de enero 2026 ($ 821,80, editable en Parámetros). Las canastas dependen de las cargas familiares; 5 o más cargas usan 20 canastas. Si el trabajador, o una de sus cargas, tiene una **enfermedad catastrófica, rara o huérfana** (casilla en la ficha del empleado), el tope sube a 100 canastas sin importar el número de cargas.

| Cargas | Canastas | Tope ($) | Rebaja máxima ($) |
| -------: | ---------: | ---------: | ------------------: |
| 0 | 7 | 5.752,60 | 1.035,47 |
| 1 | 9 | 7.396,20 | 1.331,32 |
| 2 | 11 | 9.039,80 | 1.627,16 |
| 3 | 14 | 11.505,20 | 2.070,94 |
| 4 | 17 | 13.970,60 | 2.514,71 |
| 5 o más | 20 | 16.436,00 | 2.958,48 |
| Enfermedad catastrófica, rara o huérfana | 100 | 82.180,00 | 14.792,40 |

Los gastos personales y las cargas se capturan en la ficha del empleado; la proyección anual es la que entrega el trabajador al empleador.

Ejemplo teórico (no corresponde a un empleado de la semilla): gastos personales de $ 8.000 con 2 cargas. Tope = 11 × 821,80 = 9.039,80; rebaja = 18% × 8.000 = 1.440,00. Si el impuesto causado fuera $ 3.068,65, el IR anual sería 3.068,65 − 1.440,00 = 1.628,65 y el mensual 135,72. Si la rebaja superara el impuesto causado, el IR queda en 0.

### 5.7 Mensualización

Cada trabajador decide, y la ficha del empleado lo registra por separado para cada beneficio. Los valores por defecto de la app son:

| Beneficio | Por defecto | Si se acumula |
| --- | --- | --- |
| Décimo tercero | **mensualizado** (se paga 1/12 cada mes) | Se paga hasta el 24 de diciembre |
| Décimo cuarto | **acumulado** (SBU/12 se provisiona) | Se paga hasta el 15 de agosto (Sierra y Amazonía) o el 15 de marzo (Costa y Galápagos) |
| Fondos de reserva | **mensualizados** desde el mes 13 | El trabajador pide acumularlos en el IESS |

Lo mensualizado se paga en el rol como ingreso **no gravado**: no paga IESS ni IR, pero sube el neto. El costo del empleador no cambia, porque la provisión se calcula igual aunque el beneficio se pague hoy o más adelante.

### 5.8 Fechas de pago (informativas)

El rol individual muestra cuándo se paga cada beneficio acumulado: 13° hasta el 24 de diciembre; 14° hasta el 15 de agosto para Sierra/Amazonía o hasta el 15 de marzo para Costa/Galápagos. La fecha sale de la **región** configurada en Parámetros (la demo está en Sierra, por eso dice "paga 15 ago"; con "Costa" diría "paga 15 mar"). La región solo cambia fechas y la agenda del Resumen, no los montos.

### 5.9 Escalas salariales por régimen

Cada régimen trae una escala oficial cargada en la base. Se ven y se editan en **Escalas salariales** (`/escalas`): puedes cambiar denominaciones, grupos y valores, quitar niveles que no estén en uso, agregar un nivel nuevo (código, denominación, grupo y valor) y **Restaurar escala oficial** para volver a los valores de fábrica. La pantalla muestra además qué personal está asignado a cada nivel. Puedes mirar la escala de otro régimen sin cambiar el de la empresa; las ediciones de cada escala se conservan al cambiar de régimen.

Cada régimen aplica una **regla** distinta entre el sueldo y el valor del grado. Si no se cumple, el rol guarda un aviso (no bloquea la generación) y el empleado aparece con "revisar escala" en Empleados, Organigrama y Resumen.

| Régimen | Escala | Regla | Aviso si… |
| --- | --- | --- | --- |
| CT | Salarios mínimos sectoriales | **mínimo** | el sueldo es menor al del nivel (o al SBU). Un empleado sin nivel solo se compara con el SBU. |
| LOSEP | Escala nacional de remuneraciones (22 grados SPS1 a SP16 y niveles jerárquicos superiores NJS1 a NJS10) | **fija** | la remuneración es distinta a la del grado, o no tiene grado asignado. |
| LOEP | La misma escala nacional, usada como techo | **techo** | el sueldo supera el valor del grado, o no tiene grado asignado. |
| LOES | Escalafón del personal académico (CES) | **mínimo** | el sueldo es menor al mínimo de la categoría (o al SBU). |

En todos los regímenes se avisa también si el grado asignado ya no existe en la escala del régimen vigente. En las escalas de regla **fija**, al elegir el grado en el formulario del empleado el sueldo se completa solo.

#### Código del Trabajo (comisión sectorial 12, rama 1)

Fuente: R.O. 2.º Suplemento 708 (20-dic-2024), Anexo 1, págs. 64-65; comisión sectorial 12 "Tecnología: hardware y software", rama 1 "Informática y actividades conexas" (CIIU J62). Para 2026 el Ministerio del Trabajo no emitió una tabla nueva, así que sigue vigente la de 2025 (Acuerdo MDT-2024-301); solo los valores menores al SBU suben a $ 482. Un cargo no contemplado no puede ganar menos que el menor valor de su rama (art. 5 del acuerdo).

| Estructura | Cargo de referencia | Mínimo mensual ($) |
| --- | --- | ---: |
| A1 | Director / jefe de área | 507,37 |
| B1 | Supervisor de sistemas, desarrollo, tecnología y proyectos | 506,67 |
| B2 | Arquitecto de software / administrador de base de datos | 505,97 |
| B3 | Analista de I+D / controller de calidad de software | 505,27 |
| C1 | Analista de software, redes o sistemas / programador semi senior | 504,56 |
| C2 | Técnico en mantenimiento de computadoras y cableado estructurado | 502,68 |
| C3 | Programador junior de software | 500,80 |
| D1 | Técnico de help desk | 498,93 |
| D2 | Técnico de ensamblaje y mantenimiento de equipos | 497,05 |
| E2 | Asistente o auxiliar de sistemas (menor valor de la rama) | 493,29 |

Tres valores no vienen directamente de la tabla 2025 sino que se **derivaron** de la tabla 2023 con el incremento 2023-2025: B3, C2 y D2 (con una diferencia posible de ±$ 0,02). Si dispones del anexo oficial, corrígelos en Escalas salariales.

Los cuatro socios de la semilla están en A1 y el Programador Junior en C3 (mínimo $ 500,80; sueldo $ 510). Todos cobran sobre el mínimo de su estructura (sección 7).

#### LOSEP y LOEP

Escala nacional de remuneraciones mensuales unificadas del sector público (Acuerdo MDT-2024-039, 17-mar-2024), sin incremento en 2026. Tiene 32 niveles: los 22 grados desde SPS1 ($ 527) hasta SP16 ($ 4.500) y los niveles jerárquicos superiores NJS1 ($ 2.115) a NJS10 ($ 5.072). En LOSEP la remuneración es **exactamente** la del grado. En LOEP el directorio aprueba su propia escala; se carga la nacional como **techo** (los procesos gobernantes y adjetivos no la superan, art. 4 del acuerdo) y el sueldo puede ser menor. Si tu empresa pública tiene una escala propia, edítala en `/escalas`.

#### LOES (educación superior pública)

Mínimos referenciales del CES para personal académico titular a tiempo completo en universidades públicas (Reglamento de Carrera y Escalafón del Profesor, art. 69; RPC-SE-20-No.057-2021). Cada universidad fija la remuneración entre el mínimo y el máximo de la categoría; el máximo se muestra en la columna *Grupo*.

| Categoría | Mínimo ($) | Máximo ($) |
| --- | ---: | ---: |
| Auxiliar 1 | 1.676,00 | 2.552,68 |
| Auxiliar 2 | 1.855,00 | 2.750,67 |
| Agregado 1 | 2.034,00 | 3.193,90 |
| Agregado 2 | 2.392,00 | 3.441,62 |
| Agregado 3 | 2.574,00 | 3.708,55 |
| Principal 1 | 2.967,00 | 4.306,13 |
| Principal 2 | 3.367,00 | 4.640,11 |
| Principal 3 | 3.673,79 | 5.000,00 |

### 5.10 Regímenes laborales

Lo que cambia al elegir el régimen en Parámetros (todo es ajustable después, con el valor legal al lado):

| | Código del Trabajo | LOSEP | LOEP | LOES |
| --- | --- | --- | --- | --- |
| Sector | Privado | Servidores públicos | Empresas públicas | Educación superior pública |
| IESS personal / patronal | 9,45 % / 11,15 % | 11,45 % / 9,15 % | 11,45 % / 9,15 % | 11,45 % / 9,15 % |
| IECE / SECAP | 0 % + 0,5 % | no aplica | no aplica | no aplica |
| Vacaciones al año | 15 días (1/24) | 30 días (1/12) | 30 días | 30 días |
| Horas suplementarias / extraordinarias | ×1,5 / ×2 | ×1,25 / ×1,6 | ×1,25 / ×1,6 | ×1,25 / ×1,6 |
| Escala y regla | Mínimos sectoriales · mínimo | Escala nacional · fija | Escala nacional como techo · techo | Escalafón CES · mínimo |

Los aportes del sector público siguen la Resolución C.D. 501 del IESS (11,45 % personal y 9,15 % patronal); los GAD y las entidades descentralizadas aportan 11,15 % patronal, por lo que ese valor debe ajustarse a mano en Parámetros. Las horas extra siguen el Código del Trabajo (art. 55) en el sector privado y la LOSEP (art. 114) en el público; las vacaciones, el art. 69 del CT y el art. 29 de la LOSEP.

Cada régimen ofrece estos **tipos de contrato** en el formulario del empleado:

| Régimen | Tipos de contrato |
| --- | --- |
| CT | Indefinido, Plazo fijo, Eventual, Ocasional, Por obra o servicio, Jornada parcial |
| LOSEP | Nombramiento permanente, Nombramiento provisional, Libre nombramiento y remoción, Servicios ocasionales |
| LOEP | Libre designación y remoción, Nombramiento, Contrato ocasional, Obrero (Código del Trabajo) |
| LOES | Titular (nombramiento), No titular ocasional, Invitado, Honorario |

El tipo de contrato es solo informativo: no cambia ningún cálculo.

Comparación con el mismo caso (el de María en 6.1: sueldo $ 1.500, 10 horas suplementarias y $ 200 de comisión) en los dos regímenes, para ver el efecto de los porcentajes. En LOSEP la app avisa que su sueldo no es el del grado SP5 (que es $ 1.212), lo cual es esperable porque el caso no está pensado para ese régimen:

| Concepto | Código del Trabajo | LOSEP |
| --- | ---: | ---: |
| Horas suplementarias | 93,75 (×1,5) | 78,13 (×1,25) |
| Total gravado | 1.793,75 | 1.778,13 |
| IESS personal | 169,51 (9,45 %) | 203,60 (11,45 %) |
| IR mensual | 46,77 | 41,80 |
| Neto a recibir | 1.577,47 | 1.532,73 |
| Vacaciones | 74,74 (15 días) | 148,18 (30 días) |
| Aporte patronal | 200,00 (11,15 %) | 162,70 (9,15 %) |
| SECAP (IECE en 0) | 8,97 | 0,00 |
| Costo empleador | 2.416,53 | 2.425,48 |

### 5.11 Vigencia normativa (revisada a octubre de 2026)

| Elemento | Valor y fuente |
| --- | --- |
| SBU | $ 482 (Acuerdo MDT-2025-195) |
| Tabla de IR | Tabla 2026 de la sección 5.5 (Res. NAC-DGERCGC25-00000043) |
| Canasta familiar básica | $ 821,80 (enero 2026) y canastas por cargas 7 / 9 / 11 / 14 / 17 / 20 |
| Aportes IESS | Privados 9,45 % y 11,15 %; públicos 11,45 % y 9,15 % (Resolución C.D. 501) |
| IECE y SECAP | **IECE: 0 % por defecto.** El Instituto de Crédito Educativo dejó de funcionar en 2015 y en abril de 2025 el Ministerio del Trabajo informó que el 0,5 % se eliminó con la reforma al Código Monetario (luego dio señales contradictorias). Si el IESS lo vuelve a cobrar, basta con poner 0,5 % en Parámetros. **SECAP: 0,5 %**, sigue vigente como aporte patronal del sector privado; hay proyectos de reforma en la Asamblea. |
| Jornada distribuida | Hasta 10 horas diarias (Acuerdo MDT-2026-059); el recargo aplica solo sobre las 40 horas semanales. La app no distribuye la jornada: las horas con recargo las ingresas tú en las novedades del mes. |
| Salarios mínimos sectoriales | Tabla 2025 (MDT-2024-301), vigente en 2026 por no haberse emitido una nueva (sección 5.9) |

---

## 6. Ejemplos resueltos a mano

Los dos casos son de referencia. El primero (María) es un caso de prueba del self-check de `calculos.py`, no un empleado de la semilla. El segundo (Sebastián) es el Gerente General de FERIAUTO, con datos de la semilla. El self-check también prueba la rebaja con María (gastos $ 8.000 y 2 cargas), donde el impuesto queda en 0; una rebaja con impuesto positivo se ilustra en la sección 5.6.

### 6.1 María López (caso de prueba)

Datos: sueldo $ 1.500, 30 días, 10 h suplementarias, comisión $ 200, ingreso el 15/01/2024 (más de un año), sin gastos personales ni cargas. Código del Trabajo. Décimos y fondos acumulados (no mensualizados), a diferencia de los valores por defecto de la app. Periodo: octubre 2026.

``` text
Valor hora              1.500 / 240                     = 6,25
HE suplementarias       10 × 6,25 × 1,5                 = 93,75
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
| SECAP | 1.793,75 × 0,5% | $ 8,97 |
| **Total provisiones** | | **$ 622,78** |

Cadena completa:

``` text
Sueldo bruto (gravado)  $ 1.793,75
− Descuentos            $   216,28   (IESS 169,51 + IR 46,77)
= NETO A RECIBIR        $ 1.577,47
Costo empleador         $ 1.793,75 + provisiones 622,78 = $ 2.416,53
```

Como María acumula los fondos, no se pagan en el rol. Si los mensualizara, su neto sería $ 1.726,89 (suma los $ 149,42 como no gravados); IESS, IR y costo no cambian.

### 6.2 Sebastián Constante (Gerente General)

Datos: sueldo $ 550, 30 días, sin horas extra ni comisiones, sin gastos personales ni cargas. Ingreso el 01/09/2026, contrato indefinido, Código del Trabajo, estructura A1. Con los valores por defecto: **décimo tercero mensualizado**, décimo cuarto acumulado y fondos mensualizados (pero todavía no hay fondos que pagar porque no cumple 365 días). Periodo: octubre 2026.

``` text
TOTAL GRAVADO           550 × 30 / 30                   = 550,00
IESS personal           550 × 9,45%                     = 51,98
Base IR anual           (550 − 51,98) × 12              = 5.976,24
Impuesto causado        menor a 12.208: tramo 0%        = 0,00
IR mensual              0 / 12                          = 0,00
DESCUENTOS              51,98 + 0,00                    = 51,98
13° mensualizado (no gravado)  550 / 12                 = 45,83
TOTAL INGRESOS          550,00 + 45,83                  = 595,83
NETO A RECIBIR          595,83 − 51,98                  = 543,85
```

Provisiones:

| Concepto | Cálculo | Valor |
| ---------- | --------- | ------: |
| 13° (se paga en el rol) | 550 / 12 | $ 45,83 |
| 14° (se acumula) | 482 / 12 × 30/30 | $ 40,17 |
| Vacaciones | 550 / 24 | $ 22,92 |
| Fondos de reserva | 0: cumple 365 días en sep 2027 | $ 0,00 |
| Aporte patronal | 550 × 11,15% | $ 61,33 |
| SECAP | 550 × 0,5% | $ 2,75 |
| **Total provisiones** | | **$ 173,00** |

Cadena completa:

``` text
Sueldo bruto (gravado)  $ 550,00
+ 13° mensualizado      $  45,83   (no gravado)
− Descuentos            $  51,98   (IESS 51,98 + IR 0,00)
= NETO A RECIBIR        $ 543,85
Costo empleador         $ 550,00 + provisiones 173,00 = $ 723,00
```

Mensualizar el 13.º sube el neto pero no el costo: de los $ 173,00 de provisiones, $ 45,83 se pagan hoy en vez de acumularse. Si además mensualizara el 14.º, sumaría $ 40,17 más al neto.

### 6.3 Rol de octubre 2026 de los cinco trabajadores

Generado con los datos de la semilla, sin novedades (30 días, sin horas extra, comisiones, anticipos ni préstamos). Nadie paga IR porque la base anual de todos queda bajo los $ 12.208. Los cinco tienen el 13.º mensualizado; nadie recibe fondos todavía (el primero cumple un año en septiembre de 2027).

| Empleado | Sueldo | 13.º mensualizado | IESS 9,45 % | Neto | Costo empleador |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sebastián Constante | 550,00 | 45,83 | 51,98 | 543,85 | 723,00 |
| Pablo Montero | 530,00 | 44,17 | 50,09 | 524,08 | 698,17 |
| Daylé García | 530,00 | 44,17 | 50,09 | 524,08 | 698,17 |
| Jhanina Conterón | 530,00 | 44,17 | 50,09 | 524,08 | 698,17 |
| Andrés Villacís | 510,00 | 42,50 | 48,20 | 504,30 | 673,34 |
| **Total** | **2.650,00** | **220,84** | **250,45** | **2.620,39** | **3.490,85** |

El total de ingresos es $ 2.870,84 y la planilla IESS, $ 559,20 (aporte personal + patronal + SECAP). Antes de que el 13.º se mensualizara por defecto, el neto total era $ 2.399,55; la diferencia ($ 220,84) es exactamente ese décimo. El costo no cambió.

---

## 7. Decisiones y simplificaciones

| Decisión | Motivo |
| ---------- | -------- |
| El IR resta el IESS personal (base = (gravado − IESS) × 12) | Es lo que hace el SRI. |
| La rebaja por gastos personales resta del impuesto, no de la base, y no deja impuesto negativo | Así lo marca la norma: 18% del menor entre gastos y tope por cargas (o 100 canastas con enfermedad catastrófica). El sistema no valida el formulario de gastos personales. |
| Retención = proyección del mes × 12 / 12 | Simplificación. Un sistema real reliquida cada mes: (IR proyectado − retenido) / meses restantes. Aquí no se reliquida con lo ganado en meses previos. |
| 13° y vacaciones se calculan sobre el total gravado, no solo sobre el sueldo | El Código del Trabajo incluye horas extras y comisiones en la base. |
| 14° sobre el SBU proporcional a los días | El 14° se paga sobre el SBU, no sobre el sueldo. |
| Fondos completos si cumple 365 días al cierre del mes | La ley prorratea el mes 13. Aquí se simplifica a todo o nada. |
| 13° y fondos mensualizados por defecto; 14° acumulado por defecto | Fondos: por ley se pagan mensualizados salvo pedido de acumularlos en el IESS. Los décimos se pueden mensualizar a pedido del trabajador; en la demo el 13.º viene mensualizado y el 14.º no, y cada uno se cambia en la ficha del empleado. Lo mensualizado no paga IESS ni IR. Pendiente de confirmar la exención de IR (sección 10). |
| Los décimos, fondos y utilidades se calculan igual en los cuatro regímenes | El motor aplica la misma fórmula en el sector público. No modela particularidades del sector público (p. ej. cómo se pagan allí los décimos o los fondos). La agenda del Resumen solo muestra la participación de utilidades para el Código del Trabajo. |
| SECAP 0,5% se muestra aparte, adicional al 11,15%, solo en el Código del Trabajo; IECE en 0% | Es costo del empleador en el sector privado: el costo patronal total suma 11,65%. El IECE se dejó en 0% (sección 5.11), editable. En los regímenes públicos ambos están en 0. |
| Los valores de cálculo son editables con el valor legal al lado | Una resolución puede cambiar un porcentaje sin tocar el código. Los roles ya generados conservan los valores con que se calcularon. |
| La escala de cada régimen se carga en la base y se puede editar | Los valores oficiales se cargan al crear la base; cambiarlos en `/escalas` afecta los avisos, no los montos del rol. |
| Tres niveles de la escala CT (B3, C2, D2) están derivados | No se tuvo el anexo oficial de esas filas: se calcularon desde la tabla 2023 con el incremento 2023-2025 (±$ 0,02). |
| La región solo cambia fechas | El 14.º se paga igual en todas las regiones; solo cambia el plazo. |
| La agenda de obligaciones usa fechas fijas | No corre fechas por fines de semana ni feriados y no consulta ningún calendario oficial. Es una ayuda visual, no un recordatorio tributario. |
| Recargo nocturno del 25% no incluido; jornada distribuida no modelada | Fuera del alcance del taller. Las horas con recargo se ingresan a mano. |
| Decimal con redondeo half-up por línea | Evita errores de punto flotante y el redondeo bancario de `round()`. Los valores se guardan como float en SQLite al final. |
| Cédula: módulo 10, provincia 01-24 o 30, tercer dígito menor a 6 | Valida el formato. No consulta el Registro Civil. |
| Avisos: sueldo fuera de la regla de la escala (mínimo, fija o techo) o menor al SBU, más de 48 h suplementarias al mes, neto negativo | Son advertencias que se guardan en el rol. No bloquean la generación. |
| Sueldos de arranque sobre el mínimo de su estructura y con jerarquía (Gerente General > directores > programador junior) | El mercado paga unos 1.200–1.800 a directores (Paylab y Jobint, abr-2026), pero el contrato con el GAD ($ 4.500) no lo cubre. Subir a esos montos deja el resultado negativo (sección 8, paso 8). |
| El tipo de contrato es informativo | No cambia ningún cálculo; solo se valida que sea de la lista del régimen. |
| Fechas de pago solo informativas | No cambian ningún monto (sección 5.8). |
| Sin cuentas de usuario, sin PDF y sin cierre o aprobación de roles | Es una demo. Para imprimir se usa el navegador. La publicación opcional solo distingue "lectura" de "edición" con una clave compartida (sección 1). |

---

## 8. Guion sugerido para la demo (PEA 3, ~6 min)

1. **Resumen** (`/`): mostrar las cifras de FERIAUTO: 5 trabajadores, remuneraciones $ 2.650,00, costo mensual $ 3.490,85 y resultado frente al contrato $ 479,15. Señalar la agenda de obligaciones (el RUC de la demo termina su 9.º dígito en 3, por eso el SRI vence los días 14) y las alertas.
2. **Empleados:** 5 en total: los 4 socios de FERIAUTO y el Programador Junior Andrés Villacís (contratado, no socio; nombre ficticio), con su departamento y su jefe inmediato.
3. **Organigrama** (`/organigrama`): explicar las líneas de autoridad (desde "reporta a") y la función de cada cargo. Tiene 3 niveles: Gerente General, Director de Tecnología (Pablo Montero) y Programador Junior, que le reporta a él.
4. **Tabla de remuneraciones:** recorrer cada rubro (aportes, 13.º, 14.º, vacaciones, fondos y costo) y explicar por qué cada sueldo supera el mínimo de su estructura (A1: $ 507,37; C3 del programador: $ 500,80). Totales de los 5 trabajadores: remuneraciones $ 2.650,00; aporte personal $ 250,45; patronal $ 308,75; 13.º $ 220,84; 14.º $ 200,85; vacaciones $ 110,41; costo $ 3.490,85. El Programador Junior tiene costo $ 673,34 y neto $ 504,30. Cada cargo del organigrama muestra su nivel de la escala (código, denominación y valor) y si la cumple.
5. **¿Es sostenible?:** con el contrato de $ 4.500, el costo del personal ($ 3.490,85, 77,6 %) más otros costos ($ 530) deja un margen de $ 479,15 (10,6 %). Desde el mes 13, los fondos de reserva (+$ 220,75 al mes) lo bajan a $ 258,40 (5,7 %). El punto de equilibrio es $ 4.020,85.
6. **Rol de octubre 2026:** generarlo desde *Roles de pago* (neto total $ 2.620,39 porque el 13.º se paga mensualizado; costo $ 3.490,85) y abrir el rol individual de **Sebastián Constante** (neto $ 543,85). Revisar "¿Cómo se calculó?" y compararlo con la sección 6.2.
7. **Excel de la tabla** (*Exportar Excel* en el organigrama): cambiar un sueldo en Excel y mostrar cómo se recalcula todo.
8. **Sueldos de mercado en vivo:** editar a un director y subir su sueldo a 1.200 (p. ej.), luego recargar el Resumen o el organigrama: el margen de "¿Es sostenible?" se vuelve negativo.
9. **Parámetros y régimen (opcional):** mostrar los valores de cálculo con su valor legal al lado y, en *Escalas salariales*, cómo cambia la escala entre Código del Trabajo y LOSEP. Si cambias el régimen para probarlo, **Reiniciar demo** vuelve a FERIAUTO.
10. **Reiniciar demo** (pie de la barra lateral) para dejarlo listo para el siguiente grupo.

---

## 9. Estructura de archivos

``` text
roles_pago/
├── app.py            rutas Flask, esquema SQLite (versión 6), parámetros, escalas, resumen,
│                     validaciones, guardado y organigrama
├── calculos.py       motor de cálculo puro, regímenes (REGIMENES), escalas oficiales (ESCALAS_BASE) y self-check
├── exportar.py       libro Excel (.xlsx) del rol y de la tabla de remuneraciones con openpyxl + self-check
├── templates/        plantillas Jinja: base (barra lateral), resumen, empleados, empleado_form,
│                     organigrama, roles, rol_nuevo, rol_ver, rol_individual, escalas, parametros, login
├── static/           style.css (sistema visual "libro contable") y logo.svg (logo por defecto de FeriAuto)
├── iniciar.bat / iniciar.sh   arranque con doble clic (crea .venv e instala dependencias)
├── requirements.txt  flask, openpyxl
├── PUBLICAR.md       guía para publicar la demo en solo lectura (PythonAnywhere)
├── roles.db          base SQLite local, se crea sola (no se sube a git)
└── roles_v<N>_respaldo.db     base de un esquema anterior, respaldada al cambiar de versión
```

---

## 10. Fuentes y verificación

Las reglas se contrastaron con prensa y calculadoras ecuatorianas: tabla de IR 2026, SBU, aportes IESS e IECE/SECAP, canasta y tabla de cargas, fondos mensualizados, décimo cuarto, horas extras y nocturnas. La vigencia normativa se revisó por última vez en octubre de 2026 (sección 5.11).

**Pendiente de confirmar con fuente oficial:** la exención de IR de los décimos y fondos de reserva mensualizados (el código los trata como no gravados), el prorrateo del mes 13 y los valores derivados de los niveles B3, C2 y D2 de la escala del Código del Trabajo.

- Tabla IR 2026 (SRI, Res. NAC-DGERCGC25-00000043):
  - <https://www.eluniverso.com/noticias/economia/lo-que-debe-saber-sobre-el-impuesto-a-la-renta-de-2026-nota/>
  - <https://www.ecija.com/actualidad-insights/sri-publica-nuevas-tablas-para-liquidar-el-impuesto-a-la-renta-2026/>
  - <https://nmslaw.com.ec/blog/2026/01/05/tablas-impuesto-renta-2026-ecuador/>
- SBU 2026 de $ 482 (Acuerdo MDT-2025-195): <https://www.vistazo.com/2025-12-15-salario-basico-usd-482-2026-ecuador-incremento-dolares-IC10565269>
- Salarios mínimos sectoriales (comisión 12, rama 1, CIIU J62), R.O. 2.º Suplemento 708 (20-dic-2024), Anexo 1, págs. 64-65, y Acuerdo Ministerial MDT-2024-301. Para 2026 no se emitió tabla nueva: según el Ministerio del Trabajo rige la de 2025.
  - <https://www.trabajo.gob.ec/wp-content/uploads/2024/12/ACUERDO-MINISTERIAL-NRO.-MDT-2024-301-signed.pdf>
- Escala de remuneraciones del sector público: Acuerdo MDT-2024-039 (17-mar-2024). Escalafón académico: Reglamento de Carrera y Escalafón del Profesor e Investigador del CES, art. 69, y RPC-SE-20-No.057-2021.
- Jornada distribuida de hasta 10 horas diarias: Acuerdo MDT-2026-059.
- Mercado de directores (referencia de 1.200 a 1.800 dólares): Paylab y Jobint, abril de 2026.
- Aportes IESS (9,45% / 11,15%) y SECAP 0,5%: <https://runahr.com/ec/recursos/salario/calculadora-de-salario/>. Aportes del sector público: Resolución C.D. 501 del IESS (11,45% / 9,15%).
- Canasta $ 821,80 y tabla de cargas: <https://elmercurio.com.ec/?p=1239654>
- Fondos de reserva mensualizados por defecto: <https://primicias.ec/economia/fondos-reserva-iess-consejos-acumular-mensualizar-88720>
- Décimo cuarto (fechas de pago): <https://www.expreso.ec/actualidad/economia/decimo-cuarto-sueldo-en-ecuador-2026-cuanto-deben-pagarte-275386.html>
- Horas extras y nocturnas: <https://www.eldiario.ec/ecuador/jornada-laboral-en-ecuador-esto-debes-saber-sobre-el-pago-de-horas-extras-y-el-tiempo-maximo-de-trabajo-por-semana-11032026/>
- App de referencia funcional: <https://franzpc.com/apps/roles_pago_ecuador/>
