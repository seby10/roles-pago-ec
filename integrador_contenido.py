"""Síntesis de resultados ya entregados; los importes son transcripciones, no cálculos."""

# Carpetas aportadas por el grupo; se conservan sus permisos y alojamiento original.
RECURSOS = [
    dict(id="pitch", titulo="Elevator pitch y Canvas", modulos=["emprendimiento"],
         tipo="Video", contexto="Presentación del emprendimiento · material del grupo",
         descripcion="Carpeta del pitch y del modelo de negocio. Complementa la idea, la propuesta de valor y la comunicación del proyecto FERIAUTO.",
         url="https://drive.google.com/drive/folders/1S1RCbYb9AZY72_6UmDs2rxGvg-UPEIoo?usp=drive_link",
         nota="Actividad de presentación del proyecto desarrollada durante el semestre."),
    dict(id="casos-judiciales", titulo="Casos judiciales", modulos=["nomina", "liquidacion"],
         tipo="Video", contexto="Análisis de casos · material del curso",
         descripcion="Material audiovisual de los casos judiciales trabajados en el curso, relacionado con el análisis de conflictos y la argumentación en las relaciones laborales.",
         url="https://drive.google.com/drive/folders/1LFZ4ZDc7JSGp34sxZMzw_23p3q9AyFas?usp=drive_link",
         nota="Se consulta como evidencia de la actividad del curso, junto con sus trabajos escritos."),
    dict(id="despido-ideal", titulo="El despido ideal", modulos=["liquidacion"],
         tipo="Video", contexto="Reflexión sobre el trato humano · actividad del curso",
         descripcion="Actividad audiovisual sobre cómo comunicar una desvinculación con respeto y empatía. Complementa la discusión humana y organizacional del cierre de la relación laboral.",
         url="https://drive.google.com/drive/folders/17RSFaqTzWO9NHoiQlu3Uh48nbLa4KJ32?usp=drive_link",
         nota="Representa una propuesta de trato humano; no se presenta como el procedimiento legal de despido ni reemplaza los documentos laborales."),
]

MODULOS = [
    dict(id="emprendimiento", numero="01", titulo="Emprendimiento", icono="organigrama", tono="azulmarino",
         subtitulo="De una necesidad local a un plan empresarial",
         descripcion="Idea de negocio, Canvas, estrategia, mercado, operación y viabilidad de FERIAUTO.",
         fuente="PEA 1 · informe y plan de negocios", principal="pea1",
         introduccion="FERIAUTO propone una plataforma móvil para organizar la compraventa de vehículos usados en la feria de Ambato. El modelo plantea al GAD Municipalidad de Ambato como cliente institucional y a compradores y vendedores como usuarios del servicio.",
         resultados=[("Inversión inicial", "USD 5.150", "PEA 1 · pp. 3 y 14"),
                     ("Ingresos mensuales", "USD 3.000", "Escenario inicial del Taller 05"),
                     ("Costo mensual", "USD 2.458", "Incluye talento humano sin beneficios"),
                     ("Resultado mensual", "USD 542", "Margen reportado: 18,1 %")],
         secciones=[
             dict(titulo="La oportunidad y la propuesta", texto="El grupo identificó informalidad, información poco verificable y desconfianza en las transacciones de la feria. La propuesta es centralizar la oferta, verificar perfiles y datos vehiculares y facilitar el contacto previo al encuentro presencial.", fuente="pea1", pagina=7),
             dict(titulo="Cómo funciona el modelo de negocio", texto="El Canvas propone un modelo B2G financiado por el municipio, gratuito para la ciudadanía. El desarrollo, la implementación, el mantenimiento y el soporte sustentan la relación con el cliente institucional.", fuente="canvas", pagina=1,
                  items=[("Usuarios y cliente", "Compradores y comerciantes de la feria; el GAD como financiador."),
                         ("Propuesta de valor", "Información centralizada, perfiles verificados y mayor confianza."),
                         ("Canales", "Aplicación móvil, puntos de información y canales municipales."),
                         ("Relación con usuarios", "Autoservicio, soporte y alertas de seguridad."),
                         ("Ingresos", "Contrato o financiamiento institucional por el servicio."),
                         ("Recursos clave", "Equipo técnico, infraestructura en la nube y capital inicial."),
                         ("Actividades clave", "Desarrollo, validación, mantenimiento y soporte."),
                         ("Socios clave", "Instituciones de validación y asociaciones de comerciantes, propuestos en el plan."),
                         ("Costos", "Personal, infraestructura, difusión y mantenimiento.")]),
             dict(titulo="Estrategia, mercado y operación", texto="El perfil estratégico relaciona la capacidad técnica del grupo con la necesidad de reducir estafas. El estudio de mercado compara alternativas y la operación describe registro, validación, búsqueda, encuentro en la feria y calificación. Son propuestas del plan, no convenios ni integraciones oficiales implementadas.", fuente="pea1", pagina=8),
             dict(titulo="Resultados económicos del estudio inicial", texto="La matriz reporta costos fijos de USD 430, variables de USD 100 y talento humano de USD 1.928. Registra una recuperación simple de 9,5 meses. Estos resultados pertenecen al estudio inicial y se consultan tal como fueron entregados.", fuente="pea1", pagina=15),
         ],
         notas=["El propio plan (p. 16) reconoce que el Canvas B2G gratuito y la plantilla de USD 3 × 1.000 usuarios responden a supuestos distintos. La integración conserva ambos y no los presenta como una única operación real.",
                "Las cifras de nómina posteriores pertenecen al escenario PEA 3 de USD 4.500 mensuales e incorporan aportes y provisiones. No sustituyen los resultados del Taller 05.",
                "La ficha y las tablas del sondeo contienen cantidades de respuestas diferentes. Se conserva el estudio original; no se usa esa muestra para construir nuevos indicadores."],
         enlaces=[],
         acciones=[], conexion="El modelo de negocio da contexto a las obligaciones tributarias y a los costos de contratación que se estudian en los siguientes módulos."),
    dict(id="tributarias", numero="02", titulo="Obligaciones tributarias", icono="roles", tono="azul",
         subtitulo="Formalización y documentación del emprendimiento",
         descripcion="RUC simulado, comprobantes, declaración de IVA y registro de marca del caso consolidado.",
         fuente="PEA 2 · septiembre de 2026", principal="pea2",
         introduccion="La PEA 2 reúne el ejercicio tributario de FERIAUTO S.A.S. para septiembre de 2026. La ficha usa el RUC simulado 1850001234001 y el Régimen General. Los documentos son evidencias académicas; no acreditan inscripción, declaraciones ni pagos reales.",
         resultados=[("IVA generado", "USD 442,50", "Base gravada neta: USD 2.950"),
                     ("Crédito por compras", "USD 540,00", "PEA 2 · pp. 11 y 12"),
                     ("IVA por pagar", "USD 0,00", "Retenciones recibidas: USD 450,00"),
                     ("Crédito siguiente período", "USD 547,50", "Resultado reportado en el informe")],
         secciones=[
             dict(titulo="RUC y clasificación del caso", texto="El informe identifica una sociedad por acciones simplificada con actividad principal de programación informática (CIIU J62010101), domicilio simulado en Ambato y obligación de llevar contabilidad. La condición tributaria se presenta según el supuesto de la PEA 2.", fuente="pea2", pagina=6),
             dict(titulo="Comprobantes que respaldan las operaciones", texto="El consolidado organiza facturas, notas de crédito, compras y comprobantes de retención. Cada documento permite seguir el origen de los importes usados en la declaración del período.", fuente="pea2", pagina=8),
             dict(titulo="Resultados de la declaración del IVA", texto="El módulo transcribe los resultados del informe y permite abrir directamente el resumen y el formulario. Los importes corresponden únicamente a septiembre de 2026; no se suman a las prácticas de otras empresas ni se actualizan como obligaciones vigentes.", fuente="pea2", pagina=11),
             dict(titulo="Marca e identidad del emprendimiento", texto="El trabajo incluye búsqueda de antecedentes y simulación del registro de FERIAUTO en SENADI, junto con una actividad gamificada. Se conserva la clasificación usada en el ejercicio y sus respaldos, sin atribuirle la condición de un registro oficial concedido.", fuente="pea2", pagina=16),
         ],
         notas=["La Tarea 06 utiliza MACASOFT. Las Tareas 08 y 09 corresponden a INDUMETAL. Se conservan como prácticas complementarias y no como operaciones de FERIAUTO.",
                "La Tarea 07 es una práctica del facturador SRI, con emisor y adquirente del ejercicio de clase. El caso consolidado de FERIAUTO se consulta en la PEA 2.",
                "Las tasas, clasificaciones y resultados se muestran como antecedentes académicos del período trabajado, sin crear nuevos cálculos ni trámites."],
         enlaces=[("Juego del registro de marca", "https://feriauto-juego.vercel.app/", "Enlace de la actividad ya realizada, incluido en el trabajo de marca.")],
         acciones=[], conexion="Los comprobantes documentan la actividad económica. El siguiente módulo reúne el costo de contratar al equipo que presta el servicio."),
    dict(id="nomina", numero="03", titulo="Remuneraciones y nómina", icono="empleados", tono="arcilla",
         subtitulo="El equipo y el costo de prestar el servicio",
         descripcion="Organigrama, salarios, horas extras, beneficios sociales y roles de pago existentes.",
         fuente="PEA 3 · escenario laboral documentado", principal="pea3",
         introduccion="La PEA 3 desarrolla la estructura de FERIAUTO para un contrato municipal simulado de USD 4.500 al mes. La plataforma conserva las herramientas de empleados, organigrama, escalas, roles e históricos ya construidas durante el semestre.",
         resultados=[("Personal del informe", "5 trabajadores", "PEA 3 · pp. 13 y 14"),
                     ("Remuneraciones base", "USD 2.650,00", "Escenario documentado, no padrón actual"),
                     ("Costo de personal", "USD 3.490,85", "Aportes y provisiones del informe"),
                     ("Resultado mensual", "USD 479,15", "Contrato de USD 4.500; otros costos USD 530")],
         secciones=[
             dict(titulo="Del plan al equipo de trabajo", texto="El organigrama relaciona las funciones y la jerarquía con la tabla de remuneraciones. El informe explica la incorporación de un programador y el costo de mantener el servicio bajo el escenario laboral.", fuente="pea3", pagina=3),
             dict(titulo="Salarios, novedades y beneficios", texto="Las pantallas existentes permiten consultar sueldos, novedades por horas suplementarias y extraordinarias, descuentos y beneficios sociales. Los roles guardados y sus archivos Excel continúan disponibles desde el historial.", fuente="pea3", pagina=10),
             dict(titulo="Sostenibilidad documentada", texto="El informe reporta USD 530 de otros costos mensuales. Desde el mes 13, registra costo de personal de USD 3.711,60 y resultado de USD 258,40 por la incorporación de fondos de reserva. Se presentan los valores del trabajo original.", fuente="pea3", pagina=13),
         ],
         notas=["Las tarjetas resumen transcriben la PEA 3. El resumen operativo utiliza los datos actuales de la plataforma y puede variar si se editaron empleados o parámetros.",
                "La integración añade organización y consulta. Para la exposición se pueden abrir los roles ya guardados y los Excel existentes, sin generar un nuevo período."],
         enlaces=[], acciones=[("resumen", "Abrir resumen de nómina"), ("roles_lista", "Consultar roles guardados"),
                                ("organigrama", "Ver organigrama"), ("empleados_lista", "Consultar empleados"),
                                ("escalas", "Escalas salariales")],
         conexion="La nómina documenta la relación laboral durante su vigencia. El último módulo reúne su terminación y las evidencias de cierre."),
    dict(id="liquidacion", numero="04", titulo="Liquidación laboral", icono="roles", tono="rojo",
         subtitulo="Terminación y cierre con evidencias",
         descripcion="Formas de terminación, resultados ministeriales y expediente de paz y salvo ya desarrollado.",
         fuente="APE 4 · caso ficticio y resultados del 17 de noviembre de 2026", principal="paz-informe",
         introduccion="El módulo integra el caso ficticio de Mateo Demostración Rivera y el flujo de paz y salvo construido en la APE 4. Los derechos laborales provienen de las consultas ya realizadas a la calculadora del Ministerio del Trabajo y se conservan junto con sus documentos originales.",
         resultados=[("Acuerdo entre las partes", "USD 162,83", "Total aproximado del PDF ministerial"),
                     ("Comparación por despido", "USD 1.692,83", "Mismo supuesto, distinta causal"),
                     ("Áreas de revisión", "8 áreas", "Flujo de paz y salvo existente"),
                     ("Requisitos documentales", "21 requisitos", "19 previos a emisión y 2 de seguimiento")],
         secciones=[
             dict(titulo="Forma de terminación y supuesto trabajado", texto="El caso principal usa acuerdo entre las partes, ingreso el 1 de octubre de 2026, salida el 17 de noviembre de 2026, sueldo de USD 510 y décimos acumulados. El documento comparativo conserva el supuesto de despido intempestivo; son resultados distintos y no deben sumarse.", fuente="paz-resumen", pagina=1),
             dict(titulo="Rubros respaldados por el Ministerio", texto="La consulta existente reporta décimo tercero de USD 66,58, décimo cuarto de USD 62,93, vacaciones de USD 33,32 e indemnizaciones de USD 0,00 para el acuerdo. La aplicación conserva la evidencia y sus importes sin calcular nuevamente esos derechos.", fuente="ministerio", pagina=1),
             dict(titulo="Paz y salvo y trazabilidad del cierre", texto="El flujo relaciona áreas, requisitos y archivos con la revisión administrativa. Los documentos de muestra permiten consultar el certificado de paz y salvo, la liquidación administrativa y el resumen general para firma. No acreditan firmas, pagos ni trámites oficiales realizados.", fuente="paz-resumen", pagina=1),
         ],
         notas=["Los PDF de muestra corresponden al expediente académico ya preparado. Consultarlos no crea un empleado, no aprueba requisitos ni emite nuevos documentos.",
                "Los expedientes operativos mantienen su acceso de edición. La biblioteca reúne únicamente las muestras ficticias seleccionadas para la exposición."],
         enlaces=[], acciones=[("paz.lista", "Abrir expedientes de paz y salvo"), ("paz.caso", "Consultar guía del caso existente")],
         conexion="El expediente cierra el recorrido: idea y modelo de negocio, documentación tributaria, relación laboral y terminación respaldada por evidencias."),
]

# Identidad del emprendimiento. Transcripción de la PEA 1 (Anexo 1, secciones 1 y 4)
# y de la ficha tributaria de la PEA 2. No se redefine la marca aquí.
IDENTIDAD = dict(
    nombre="FERIAUTO",
    razon="FERIAUTO S.A.S.",
    lema="Compra y vende con respaldo",
    producto="Aplicación móvil de marketplace de vehículos usados para la feria de carros de Ambato.",
    ambito="Ciudad de Ambato, provincia de Tungurahua, Ecuador.",
    asignatura="Emprendimiento y Legislación Laboral · Carrera de Software, FISEI, UTA.",
    fuente="PEA 1 · Anexo 1, Plan de Negocios",
    origen_nombre="El nombre fusiona «feria» y «auto»: traslada el comercio tradicional de vehículos "
                  "a una experiencia digital y móvil, y destaca además la letra «A» de Ambato.",
    mision="Digitalizar y formalizar la compra y venta de vehículos usados en Ambato mediante una "
           "plataforma tecnológica intuitiva y segura para el usuario, brindando a comerciantes y "
           "ciudadanos un entorno de transacciones verificadas, seguras y transparentes.",
    vision="Ser, para el año 2031, el ecosistema digital líder a nivel nacional en la gestión y "
           "modernización de ferias vehiculares, reconocidos por transformar los mercados "
           "tradicionales en entornos comerciales transparentes, seguros y tecnológicamente avanzados.",
    marca=[
        ("Nombre", "FERIAUTO",
         "Marca corta y memorable que traslada el comercio físico de vehículos a una experiencia digital."),
        ("Forma o símbolo", "Letra «A», vehículo y circuitos",
         "Integra la «A» de Auto y de Ambato, un vehículo y circuitos tecnológicos dentro del formato "
         "de una aplicación móvil."),
        ("Color principal", "Azul oscuro",
         "Representa seguridad, confianza y profesionalismo, determinantes al comprar o vender un vehículo."),
        ("Color secundario", "Rojo / anaranjado",
         "Representa dinamismo, movimiento y acción; destaca la palabra AUTO dentro del logotipo."),
    ],
    paleta=[("Azul oscuro", "#13213d", "Principal"), ("Rojo", "#c8202a", "Secundario"),
            ("Blanco", "#ffffff", "Contraste")],
    equipo=["Jhanina Conterón Villamarín", "Daylé García Fernández",
            "Pablo Andrés Montero López", "Fabricio Sebastián Constante Naranjo"],
    problema=[
        ("Problema", "El proceso informal de compraventa en la feria de carros de Ambato dificulta "
                     "verificar la información de los vehículos y genera desconfianza entre las partes."),
        ("Cliente o usuario", "Comerciantes y vendedores de vehículos usados de la feria, y personas "
                              "interesadas en comprar. El cliente que financia la solución es el GAD "
                              "Municipalidad de Ambato."),
        ("Solución", "Plataforma digital que permite publicar y buscar vehículos usados, verificar la "
                     "información relevante y generar un reporte que facilite la evaluación previa a la compra."),
        ("Valor", "Mayor confianza y seguridad en el proceso, acceso a información verificable y una "
                  "gestión más ordenada de las oportunidades de venta."),
    ],
    foda=[
        ("Fortalezas", "internas", [
            "Propuesta de valor altamente diferenciada en el mercado.",
            "Equipo capaz de desarrollar una plataforma robusta y moderna.",
            "Modelo de negocio que elimina la barrera de costo para el usuario final."]),
        ("Oportunidades", "externas", [
            "Alto interés en modernizar el proceso de comercio automotriz.",
            "Necesidad ciudadana de reducir las estafas en la compraventa de autos.",
            "Creciente tendencia de las administraciones locales a modelos de «ciudades inteligentes»."]),
        ("Debilidades", "internas", [
            "Dependencia del financiamiento gubernamental mediante contratos.",
            "Falta de experiencia comercial en negociación y contratación con entidades municipales.",
            "Marca nueva en el mercado, sin reconocimiento previo entre los comerciantes de la feria."]),
        ("Amenazas", "externas", [
            "Resistencia al cambio de los comerciantes más apegados a los sistemas tradicionales.",
            "Burocracia y retrasos en el proceso de adopción del software.",
            "Inestabilidad o restricciones en el acceso a las bases de datos externas."]),
    ],
    ficha=[("Razón social del caso", "FERIAUTO S.A.S."), ("RUC simulado", "1850001234001"),
           ("Actividad económica", "Programación informática · CIIU J62010101"),
           ("Régimen", "Régimen General, obligada a llevar contabilidad"),
           ("Domicilio del ejercicio", "Ambato, Tungurahua")],
    nota="La ficha tributaria corresponde al supuesto académico de la PEA 2. El RUC es simulado y no "
         "acredita inscripción, declaraciones ni pagos reales.",
)
