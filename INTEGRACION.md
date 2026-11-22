# Integración del proyecto FERIAUTO

## Qué se integró

- `/`: portada del proyecto y descargas para la entrega.
- `/modulos/emprendimiento`: PEA 1, idea, Canvas, estrategia, mercado, operación y estudio económico.
- `/modulos/tributarias`: PEA 2, RUC simulado, comprobantes, IVA y registro de marca.
- `/modulos/nomina`: PEA 3 y accesos a las herramientas existentes.
- `/modulos/liquidacion`: APE 4, resultados ministeriales y muestras ficticias del paz y salvo.
- `/biblioteca`: 33 documentos con búsqueda sin distinción de mayúsculas/tildes y filtros combinables.
- `/documentos/<id>`: páginas de consulta, procedencia y descarga literal del archivo.
- `/nomina/resumen`: resumen operativo anterior. Se conserva el endpoint `resumen`.

Se integran además tres carpetas audiovisuales compartidas por el grupo: elevator pitch/Canvas en Emprendimiento; casos judiciales en Nómina y Liquidación; y el despido ideal en Liquidación como reflexión sobre trato humano, sin atribuirle validez de procedimiento legal. También aparecen en la portada y en la biblioteca con búsqueda y filtro `Video`. Se enlazan las carpetas originales de Drive sin descargar su contenido ni cambiar sus permisos.

Los nuevos módulos consultan evidencias y transcriben resultados ya entregados. No generan casos, roles, expedientes ni importes nuevos. Las herramientas anteriores permanecen disponibles para continuar su uso habitual. El esquema de SQLite sigue en versión 8.

## Fuentes y coherencia

`evidencias_integrador/catalogo.json` registra título, módulo, contexto, archivo de origen, número de páginas, tamaño y SHA-256. Las copias se conservaron byte por byte. `evidencias_integrador/vistas` contiene imágenes de sus páginas para navegadores sin visor PDF; no reemplazan el original. Excel y Word se descargan en su formato original.

Se diferencian los ingresos del estudio inicial (USD 3.000, PEA 1) y los del escenario laboral (USD 4.500, PEA 3). Las prácticas de MACASOFT, INDUMETAL y del facturador SRI se identifican como complementarias. Las limitaciones del plan y la discrepancia del sondeo se explican sin corregir los trabajos originales. No se incorporó al resultado FERIAUTO el análisis de caja de otras empresas ni el ejemplo de liquidación con información personal real.

El catálogo incorpora contenido de clase de las cuatro unidades como referencia académica. Las reglas y valores históricos no se presentan como asesoramiento tributario o laboral actualizado.

## Entregables

En `entregables_integrador/`:

- `Informe_Integrador_FERIAUTO_Grupo1.pdf`: ocho páginas, incluida portada, adaptadas al archivo **FORMATO DE TRABAJO FINAL.docx** proporcionado el 21 de noviembre. Conserva encabezado, logotipos, campos y secciones 2.1 a 2.10, con la línea de investigación confirmada por el grupo.
- `Informe_Integrador_FERIAUTO_Grupo1.docx`: versión editable basada en una copia de la plantilla institucional, con su geometría y 21 partes originales preservadas.
- `Presentacion_Integrador_FERIAUTO_Grupo1.pptx`: diez láminas con texto, cinco tablas y diagrama editables, capturas reales, QR, enlaces y notas de exposición.
- `Presentacion_Integrador_FERIAUTO_Grupo1.pdf`: copia de consulta de las diez láminas, exportada con PowerPoint.
- `Guion_Exposicion_Grupo1.md`: reparto y recorrido sugeridos para ocho minutos y 35 segundos.

La revisión del 21 de noviembre está publicada en PythonAnywhere. Se sustituyeron los cinco entregables, con respaldo previo en `/home/seby10/respaldo_entregables_20261121_vgboaafl`. Se descargaron y comprobaron los cuatro enlaces públicos: sus tamaños y SHA-256 coinciden con las versiones finales locales. El DOCX editable también está conservado en la carpeta del servidor. La actualización no modificó el código ni las bases de datos.

Para mostrar el trabajo localmente, abre `iniciar.bat` y entra en `http://127.0.0.1:5050/`. El entorno local ya contiene las dependencias. Si el comando `python` del equipo apunta a la tienda de Windows, el iniciador utiliza primero el Python del entorno existente.

## Actualización de PythonAnywhere

Destino indicado por el grupo: `https://seby10.pythonanywhere.com/`.

La actualización final de los entregables está en `.test-output/formato-final/actualizacion-entregables.zip` (2.430.436 bytes; SHA-256 `1317d0bade963ca6ea003932b4e5d27aa20602181e9e03bada11961da19e3a9f`). Contiene exclusivamente los cinco archivos revisados, con rutas `entregables_integrador/`. Si se restaura el paquete inicial descrito debajo, aplicar después este ZIP para conservar el informe institucional de ocho páginas y las diez láminas finales. Para esta sustitución de documentos no hace falta recargar Flask.

El paquete `actualizacion-integrador-feriauto.zip` contiene el código de ejecución, plantillas, estilos, casos ficticios existentes, catálogo, documentos y los cuatro entregables. El paquete complementario `vistas-previas-integrador.zip` contiene las vistas de las páginas. **No incluyen bases de datos, archivos privados de expedientes, entornos virtuales ni credenciales.** Ambos se aplican sobre la carpeta existente de la app; no requieren volver a cargar casos ni ejecutar `preparar_evidencias.py` en el servidor.

1. Iniciar sesión en PythonAnywhere y confirmar la carpeta **Source code** en la pestaña **Web**.
2. Hacer una copia de seguridad de esa carpeta en el alojamiento antes de superponer el paquete.
3. Subir ambos ZIP a **Files** y extraerlos dentro de la carpeta de código confirmada (conservar `roles.db`, la configuración WSGI, el entorno y los archivos privados).
4. Pulsar **Reload** en **Web**.
5. Abrir la URL pública y comprobar portada, cuatro módulos, búsqueda, una página de PEA 2, descargas finales y acceso a nómina. Las consultas documentales son públicas; los expedientes operativos conservan sus restricciones anteriores.

Si el alojamiento usa el checkout `/home/seby10/roles-pago-ec`, la extracción desde una consola Bash es:

```bash
cd /home/seby10/roles-pago-ec
unzip -o /home/seby10/actualizacion-integrador-feriauto.zip
unzip -o /home/seby10/vistas-previas-integrador.zip
```

Confirmar las rutas en **Web/Files** antes de ejecutar. No se debe usar **Reiniciar demo** para aplicar esta actualización.

## Verificación

```bash
.venv/Scripts/python.exe -m unittest test_integrador test_paz_salvo test_expediente_completo
```

Las pruebas usan bases temporales: comprueban recorrido público, enlaces internos, fidelidad de originales, búsqueda/filtros, límites del visor, descargas y ausencia de modificaciones en datos laborales. Se conservan las 25 pruebas previas de paz y salvo.

La preparación de copias (`preparar_evidencias.py`) es una utilidad de empaquetado. El servidor solo necesita los archivos ya incluidos. No implementa una nueva automatización académica ni requiere los documentos externos a esta carpeta en tiempo de ejecución.
