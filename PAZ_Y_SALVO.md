# Paz y salvo laboral: uso, integración y fuentes

Revisión de fuentes: 17 de noviembre de 2026. Ámbito del proyecto: Ecuador; empresa de ejemplo FERIAUTO y régimen seleccionado en Parámetros.

El módulo genera una constancia interna de entregas y revisiones. El acta de finiquito y la liquidación laboral siguen su procedimiento legal propio. Tener un expediente en estado «firmado» significa que el operador archivó una copia y declaró haber verificado las firmas, no que una autoridad haya validado el cese ni que estén cumplidas todas las obligaciones laborales.

## Cómo utilizarlo

1. Iniciar con `iniciar.bat` o `iniciar.sh`; los lanzadores instalan las dependencias actualizadas. Abrir **Paz y salvo → Nuevo expediente**, o **Empleados → Paz y salvo**.
2. Seleccionar trabajador y fecha de salida. Indicar el motivo informado; esto no resuelve automáticamente la causal jurídica de terminación.
3. Confirmar cuatro responsables activos: jefatura, Tecnología y bienes, Finanzas y Talento humano. El sistema sugiere el jefe de `reporta_a` y las cabezas de Tecnología/Finanzas cuando encuentra una sola por departamento. Si se usa otro responsable de jefatura, justificar la designación. Cuando sale la máxima autoridad se debe designar a otra persona con facultades verificadas. El trabajador no puede revisar ni representar al empleador en su propio expediente.
4. Elegir quién firmará por el empleador. Verificar su representación o delegación y adjuntar respaldo cuando corresponda; seleccionar un cargo no demuestra sus facultades.
5. Adjuntar uno o más respaldos por área. Marcar **conforme** requiere archivo y confirmación de la revisión. **No aplica** exige justificación y confirmación. **Pendiente** y **observado** bloquean la emisión.
6. Reasignar en Empleados a los subordinados activos del trabajador que sale. La revisión de jefatura y la emisión comprueban esta condición.
7. Emitir el PDF. Desde ese momento se inmovilizan las revisiones y los respaldos. Descargarlo, recabar ambas firmas, completar lugar/fecha y entregar copias a las partes.
8. Revisar manualmente que ambas firmas y el contenido correspondan al PDF emitido; cargar la copia firmada en PDF y confirmar esa revisión. El archivo se conserva junto con el original emitido.

Si hay un error antes de archivar la copia firmada, anular indicando el motivo y crear otro expediente. Se conservan el historial y el PDF anterior como antecedentes. Comunicar a las partes la anulación de cualquier ejemplar que ya se hubiera distribuido. Un expediente firmado no se modifica ni anula desde este módulo.

## Qué revisar y respaldar

| Área | Revisión sugerida | Respaldos según el caso |
|---|---|---|
| Jefatura | Entrega de funciones, proyectos y documentación; continuidad de tareas; reasignación de subordinados | Acta de entrega, inventario de documentos, designación de responsable alternativo |
| Tecnología y bienes | Equipos, llaves, activos y cuentas; programar revocación de accesos en la fecha efectiva | Inventario y recepción firmados; confirmación de baja de accesos. No adjuntar contraseñas |
| Finanzas | Conciliar nómina, pagos, anticipos y préstamos; revisar justificación de cualquier descuento | Conciliación y comprobantes. Un rol generado no demuestra pago y su neto no equivale a la liquidación |
| Talento humano | Causal, fecha, beneficios pendientes, vacaciones, liquidación pormenorizada, finiquito y trámites aplicables | Aviso de salida IESS, acta SUT y comprobante de pago cuando proceda, constancias de entrega de documentos |

La revisión interna puede prepararse antes de la salida. Una baja de accesos o un trámite aún no efectuado debe quedar pendiente u observado; evitar afirmar su ejecución anticipadamente. El expediente no calcula indemnizaciones, no descuenta de nómina y no inactiva al empleado. La inactivación se hace en Empleados cuando corresponda a la fecha efectiva. El pago y los trámites legales se atienden independientemente de pendientes internos.

## Fuentes oficiales y consecuencias de diseño

| Fuente | Hallazgo | Decisión aplicada |
|---|---|---|
| [Constitución del Ecuador, art. 326.2 y 326.11](https://www.presidencia.gob.ec/wp-content/uploads/2024/07/CONSTITUCION_DE_LA_REPUBLICA_DEL_ECUADOR-2024-05-30.pdf) | Los derechos laborales son irrenunciables; la transacción laboral tiene condiciones y no puede implicar renuncia | El PDF delimita su alcance a entregas/revisiones, preserva derechos y no autoriza descuentos |
| [Código del Trabajo, art. 595, copia alojada por SERCOP](https://portal.compraspublicas.gob.ec/sercop/wp-content/uploads/2026/03/CT.pdf) | El documento de finiquito puede ser impugnado si la liquidación no fue practicada ante el inspector; debe ser pormenorizada | Se separa la constancia interna del finiquito y de la liquidación legal |
| [Acuerdo MDT-2025-053, arts. 2, 3 y 6](https://www.trabajo.gob.ec/wp-content/uploads/2025/06/ACUERDO-MINISTERIAL-MDT-2025-053.pdf) | Reforma el art. 19 del MDT-2023-140: acta firmada y comprobante de pago en PDF se cargan en el sistema ministerial; plazo máximo de registro de quince días desde la terminación. Incluye custodia a cargo del empleador y entrega de documentación al trabajador | Recordatorio SUT para CT; archivos conservados en el expediente y entrega de copia indicada en el PDF. El SHA-256 local no es el HASH emitido por el Ministerio |
| [IESS: avisos de entrada y salida](https://www.iess.gob.ec/web/empleador/avisos-de-entrada-y-salida) | El aviso de salida se comunica dentro del término de tres días posteriores al hecho, conforme al art. 73 de la Ley de Seguridad Social | Recordatorio separado del SUT; se evita calcular automáticamente ese término sin un calendario laboral aplicable |
| [Ley Orgánica de Protección de Datos Personales, art. 10](https://www.gob.ec/sites/default/files/regulations/2025-01/01%20Ley%20Org%C3%A1nica%20de%20Protecci%C3%B3n%20de%20Datos%20Personales.pdf) | Finalidad, minimización, conservación y seguridad de los datos | Expedientes privados en modo publicado, sin enlaces públicos a archivos ni caché; no incorporar documentos innecesarios |
| [OWASP: File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) | Validar autorización, tamaño, extensión y contenido; proteger almacenamiento y descargas; defensa en profundidad | CSRF en las acciones del módulo; PDF/PNG/JPG; validación por lector PDF/imagen; límites por archivo/expediente; archivos en SQLite fuera de `static`; descarga como adjunto |

El recordatorio de quince días se aplica al régimen CT y se calcula desde la fecha de salida informada, no desde la creación del expediente. No sustituye confirmar que esa fecha es efectiva ni revisar particularidades del caso. LOSEP, LOEP y LOES requieren examinar su normativa y procedimiento específico; el módulo no les impone automáticamente el plazo de CT. La revisión de fuentes no equivale a certificar cumplimiento de un caso laboral concreto.

## Integración técnica y conservación

- `paz_salvo.py` registra un Blueprint Flask. Las vistas reutilizan la barra lateral, estilos, filtros y empleados del sistema actual.
- Cuatro tablas: `paz_expedientes`, `paz_revisiones`, `paz_adjuntos` y `paz_eventos`. Adjuntos almacenados como BLOB: la copia de seguridad completa de SQLite incluye los archivos, sin rutas controladas por nombres aportados por el usuario.
- Esquema **7**: migración aditiva desde **6**. Antes de migrar crea `roles_v6_pre_paz_salvo_respaldo.db` mediante SQLite backup y conserva empleados, parámetros, escalas y roles. Las versiones anteriores a 6 conservan el comportamiento histórico de respaldo y recreación; para datos reales en esas versiones hace falta una migración específica.
- Datos del empleado, empresa y responsables copiados al crear el expediente; modificaciones posteriores no reescriben esa historia. Se conserva el PDF exacto emitido y su SHA-256, además del hash de cada respaldo.
- Máximo 10 MB por archivo y 50 archivos por expediente. PDF firmado exclusivamente PDF; los respaldos pueden ser PDF, PNG o JPEG. PDF cifrado, vacío, inválido, de más de 200 páginas o con ciertas acciones/adjuntos a nivel raíz se rechaza. Esta validación no es un antivirus ni garantiza ausencia de todo contenido activo.
- En publicación con `EDIT_PASSWORD`, todas las vistas, PDF y descargas del módulo exigen sesión de edición. Sin esa variable continúa el uso local académico. Los responsables no reciben cuentas, correos ni enlaces de aprobación: el operador registra sus revisiones y evidencias. La bitácora identifica el modo de operación, no inventa una identidad individual autenticada.
- Las transiciones de revisión, emisión, carga y anulación se serializan con transacciones SQLite. El índice de unicidad impide dos expedientes abiertos para el mismo empleado.
- Los roles recientes se consultan como referencia, sin copiarlos como saldos exigibles ni alterar los cálculos de nómina.
- No hay borrado de adjuntos desde el módulo. **Reiniciar demo sí borra la base completa, incluidos expedientes y archivos**, con advertencia explícita. Respaldar antes de usarlo. El respaldo previo a migración tampoco sustituye respaldos periódicos posteriores.

Para operar con datos laborales reales, el sistema académico necesita cuentas individuales y autorización por expediente/área, trazabilidad de identidad, respaldo y restauración probados, HTTPS, controles de acceso a la base, análisis de archivos y una política de conservación documentada que armonice la normativa laboral con protección de datos. El historial SQLite no es un registro inviolable frente a administradores con acceso al archivo. La validación de firmas manuscritas es manual. Estas capacidades no se presentan como implementadas en esta versión.

## Verificación

Instalar `requirements.txt` y ejecutar `python -m unittest test_paz_salvo -v`. Las pruebas usan bases temporales y no abren la base de trabajo. Cubren flujo PDF/archivo firmado, migración, copia histórica, subordinados, duplicados, justificaciones, restricciones de edición, formatos/tamaños, CSRF y acceso privado.

`ROLES_DB_PATH` permite indicar una base alternativa para pruebas o demostraciones sin alterar `roles.db`.
