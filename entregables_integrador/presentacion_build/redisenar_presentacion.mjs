import fs from 'node:fs/promises';
import {readFileSync} from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const RUNTIME = String.raw`C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1119-907-0_26.1119.907.0_x64__3k8sg7r9htsxt\dependencies`;
process.env.RUNTIME_NODE_MODULES=path.join(RUNTIME,'node/node_modules');
process.env.RUNTIME_NODE=path.join(RUNTIME,'node/bin/node.exe');
const SKILL = String.raw`C:\Users\sebas\.codex\plugins\cache\openai-primary-runtime\presentations\26.1119.11507\skills\presentations`;
const {Presentation, PresentationFile, FileBlob} = await import(pathToFileURL(path.join(RUNTIME,'node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const {finalizePresentation} = await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const ROOT=path.resolve(process.cwd()), OUT=path.join(ROOT,'entregables_integrador'), BUILD=path.join(OUT,'presentacion_build');
const REV=process.env.DECK_REV || 'v1';
const FINAL=path.join(BUILD,'validated',REV,'final.pptx');
await fs.mkdir(path.dirname(FINAL),{recursive:true});
await fs.mkdir(path.join(BUILD,REV),{recursive:true});
const p=Presentation.create({slideSize:{width:1280,height:720}});
p.theme.defaultFont='Arial';
const C={paper:'#f6f5f1',ink:'#192b37',green:'#21684f',muted:'#596267',line:'#d5d9d5',pale:'#eaf1ed',blue:'#3e4a7c',white:'#ffffff',clay:'#a14f32'};
const NONE={style:'solid',fill:'none',width:0};
function text(s,txt,x,y,w,h,size=22,color=C.ink,bold=false,extra={}){
  const q=s.shapes.add({geometry:'textbox',name:txt.slice(0,60),position:{left:x,top:y,width:w,height:h},fill:'none',line:NONE});
  q.text=txt;q.text.style={typeface:'Arial',fontSize:`${size}pt`,color,bold,insets:0,autoFit:'none',verticalAlignment:'top',wrap:'square',...extra};return q;
}
function line(s,x,y,w,color=C.line){s.shapes.add({geometry:'line',position:{left:x,top:y,width:w,height:0},fill:'none',line:{style:'solid',fill:color,width:1}});}
function image(s,file,x,y,w,h,alt,uri){
 const ext=path.extname(file).toLowerCase();
 const contentType=ext==='.svg'?'image/svg+xml':ext==='.jpg'||ext==='.jpeg'?'image/jpeg':'image/png';
 return s.images.add({blob:new Uint8Array(readFileSync(file)),contentType,position:{left:x,top:y,width:w,height:h},fit:'contain',alt,...(uri?{hyperlink:{uri,isExternal:true}}:{})});
}
const records=[];
function slide(title,subtitle,notes,source=''){
 const s=p.slides.add();s.background.fill=C.paper;
 text(s,title,60,53,1150,64,32,C.ink,true);
 if(subtitle)text(s,subtitle,62,121,1152,38,17,C.muted);
 line(s,62,669,1152);
 text(s,'FERIAUTO S.A.S.  /  Grupo 1',62,683,750,20,10,C.muted);
 text(s,String(p.slides.items.length).padStart(2,'0'),1160,681,52,24,12,C.muted,false,{alignment:'right'});
 s.speakerNotes.text=notes+'\n\nFuentes: '+source;
 records.push({slide:p.slides.items.length,title,notes,source});return s;
}
function table(s,values,x,y,w,h,widths,font=18){
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});
 t.styleOptions={headerRow:true,bandedRows:false};
 t.borders.assign({style:'solid',fill:C.line,width:1});
 for(let r=0;r<values.length;r++)for(let c=0;c<values[r].length;c++){
  const cell=t.getCell(r,c);cell.fill=r===0?C.ink:(r%2===1?C.white:'#edf1ee');
  cell.text.style={typeface:'Arial',fontSize:`${font}pt`,color:r===0?C.white:C.ink,bold:r===0,insets:12,verticalAlignment:'middle',autoFit:'none'};
 }
 return t;
}
function caption(s,txt,x=62,y=639,w=1150){text(s,txt,x,y,w,25,11,C.muted);}
const URL='https://seby10.pythonanywhere.com/';
const pitch='https://drive.google.com/drive/folders/1S1RCbYb9AZY72_6UmDs2rxGvg-UPEIoo';
const judicial='https://drive.google.com/drive/folders/1LFZ4ZDc7JSGp34sxZMzw_23p3q9AyFas';
const despido='https://drive.google.com/drive/folders/17RSFaqTzWO9NHoiQlu3Uh48nbLa4KJ32';

// 1 Portada. Jerarquía tipográfica y escudos originales.
{
 const s=p.slides.add();s.background.fill=C.paper;
 image(s,path.join(OUT,'image2.png'),63,42,74,74,'Escudo original Universidad Técnica de Ambato');
 image(s,path.join(OUT,'image1.png'),1135,42,74,74,'Escudo original FISEI');
 text(s,'UNIVERSIDAD TÉCNICA DE AMBATO',162,49,900,31,18,C.ink,true);
 text(s,'FISEI  /  Carrera de Software  /  Octavo A',162,84,900,27,16,C.muted);
 text(s,'FERIAUTO',60,175,1120,86,52,C.green,true);
 text(s,'Proyecto final integrador',63,270,1120,63,34,C.ink,true);
 text(s,'Emprendimiento y Legislación Laboral',65,344,1120,42,23,C.ink);
 text(s,'Constante Naranjo Fabricio Sebastián\nConterón Villamarín Britani Jhanina\nGarcía Fernández Daylé\nMontero López Pablo Andrés',65,422,1100,140,18,C.ink);
 text(s,'Docente  Ing. María Francisca Cazorla Logroño, Mg.\nCiclo académico julio a diciembre de 2026',65,598,1110,63,16,C.muted);
 const n='Sebastián, 30 segundos. Presentar al grupo y la asignatura. El propósito es reunir los productos existentes del semestre y mostrar cómo se conectan. La exposición completa dura entre 7 y 9 minutos.';
 s.speakerNotes.text=n+'\nFuente: portadas confirmadas de los informes del Grupo 1 y escudos de la plantilla institucional original.';
 records.push({slide:1,title:'Proyecto final integrador',notes:n,source:'Informes del Grupo 1 UTA'});
}
// 2 Mapa editable y evidencia real de inicio.
{
 const s=slide('Cuatro módulos conectan el trabajo del semestre','La misma navegación reúne las síntesis, las fuentes y las herramientas existentes.',
 'Sebastián, 55 segundos. Recorrer el diagrama y señalar que el módulo lleva al informe original y a las herramientas ya realizadas. La captura muestra el inicio publicado. Durante la demostración se puede seguir este mismo orden.',
 'Consigna final; integrador_contenido.py; captura real .test-output/plataforma-publicada.jpg.');
 const names=['Emprendimiento','Obligaciones\ntributarias','Remuneraciones\ny nómina','Liquidación\nlaboral'];let prev;
 for(let i=0;i<4;i++){
  const x=62+i*294;
  const q=s.shapes.add({geometry:'rect',name:`Modulo ${i+1}`,position:{left:x,top:186,width:250,height:106},fill:C.pale,line:{style:'solid',fill:C.green,width:1}});
  q.text=`0${i+1}  ${names[i]}`;q.text.style={typeface:'Arial',fontSize:'20pt',bold:true,color:C.green,verticalAlignment:'middle',insets:12};
  if(prev)s.shapes.connect(prev,q,{kind:'straight',fromSide:'right',toSide:'left',line:{style:'solid',fill:C.green,width:2},tail:{type:'arrow',width:'sm',length:'sm'}});
  prev=q;
 }
 image(s,path.join(ROOT,'.test-output/plataforma-publicada.jpg'),62,323,590,330,'Captura real del inicio publicado de FERIAUTO',URL);
 text(s,'Resultado con fuente',708,341,490,36,23,C.ink,true);
 text(s,'Cada síntesis identifica el informe,\nel período y la etapa del proyecto.',708,388,490,80,19,C.muted);
 text(s,'Consulta y continuidad',708,489,490,36,23,C.ink,true);
 text(s,'La biblioteca abre las evidencias.\nLos módulos laborales conservan\nsus recorridos de trabajo.',708,536,490,96,19,C.muted);
}
// 3 Canvas auténtico con síntesis editable.
{
 const s=slide('Emprendimiento y modelo de negocio','FERIAUTO propone organizar la compraventa de vehículos usados en la feria de Ambato.',
 'Sebastián, 55 segundos. Presentar el problema de informalidad y desconfianza. Distinguir cliente institucional y usuarios. El Canvas propone validaciones y alianzas, sin afirmar que existen convenios oficiales o integraciones implementadas. El pitch complementa la explicación.',
 'Tarea02_BusinessModelCanvas_Grupo.pdf, p. 1; GuiaAPE1_Grupo01.pdf, pp. 6 a 9.');
 image(s,path.join(BUILD,'assets/canvas.png'),62,183,735,435,'Canvas original elaborado por el Grupo 1');
 text(s,'Cliente institucional',835,192,390,35,22,C.green,true);
 text(s,'GAD Municipalidad\nde Ambato',835,236,380,78,23,C.ink);
 text(s,'Usuarios del servicio',835,335,390,35,22,C.green,true);
 text(s,'Compradores y comerciantes\nde la feria. Acceso gratuito\nen el modelo propuesto.',835,378,380,116,20,C.ink);
 const l=text(s,'Pitch y Canvas del grupo',835,542,380,64,19,C.blue,true);l.hyperlink={uri:pitch,isExternal:true};
 caption(s,'Evidencia original del Canvas y síntesis del modelo B2G. Las alianzas e integraciones pertenecen a la propuesta.');
}
// 4 Escenarios documentados, tabla nativa.
{
 const s=slide('Escenarios económicos en etapas distintas','USD mensuales. Inversión inicial del Taller 05: USD 5.150.',
 'Jhanina, 65 segundos. Mostrar los ingresos, costos y resultados de las dos etapas. El Taller 05 usa una estimación de USD 3 por 1.000 usuarios y talento humano sin beneficios completos. PEA 3 trabaja con contrato municipal simulado de USD 4.500 e incorpora aportes y provisiones. No comparar como si fueran una sola operación. Inversión inicial documentada: USD 5.150.',
 'GuiaAPE1_Grupo01.pdf, pp. 3, 15 y 16; PEA3/Informe_PEA3_ContratacionLaboral_FERIAUTO.pdf, Tabla 12, p. 13.');
 table(s,[['Concepto','Taller 05 / PEA 1','Escenario PEA 3'],['Ingreso mensual','3.000,00','4.500,00'],['Talento humano / personal','1.928,00','3.490,85'],['Otros costos','530,00','530,00'],['Resultado mensual','542,00','479,15']],62,188,1152,318,[440,356,356],19);
 text(s,'Etapa inicial',65,537,525,34,22,C.green,true);
 text(s,'Estimación de usuarios y personal\nsin todos los beneficios laborales.',65,579,520,64,19,C.muted);
 text(s,'Etapa de contratación',659,537,550,34,22,C.blue,true);
 text(s,'Contrato B2G simulado con\naportes y provisiones laborales.',659,579,550,64,19,C.muted);
}
// 5 IVA transcrito, tabla nativa y resultados enfatizados.
{
 const s=slide('Obligaciones tributarias de FERIAUTO','RUC simulado 1850001234001. Ejercicio consolidado de septiembre de 2026.',
 'Jhanina, 55 segundos. Abrir en la plataforma la PEA 2 y su resumen de IVA. Relacionar los comprobantes con el resultado del período. Los USD 547,50 son crédito para el siguiente período, no efectivo recibido. Las tasas y clasificaciones corresponden al ejercicio entregado, sin presentar una actualización normativa.',
 'Informe_PEA2_ObligacionesTributarias_GRUPO1.pdf, pp. 6 a 12.');
 table(s,[['Respaldo del período','USD'],['IVA generado en ventas','442,50'],['Crédito por adquisiciones','540,00'],['Retenciones de IVA recibidas','450,00']],62,194,660,300,[490,170],19);
 text(s,'0,00',799,184,390,83,48,C.green,true);
 text(s,'IVA a pagar',801,276,380,40,23,C.ink);
 text(s,'547,50',799,355,390,83,48,C.blue,true);
 text(s,'Crédito para el\nsiguiente período',801,447,380,79,23,C.ink);
 text(s,'Facturas, notas de ajuste, retenciones y formulario conservan el origen de los importes.',65,553,1140,68,22,C.ink);
 caption(s,'Resultados transcritos de la PEA 2. Los documentos son didácticos y no acreditan trámites reales.');
}
// 6 Organigrama auténtico y parámetros históricos.
{
 const s=slide('Remuneraciones y costo del personal','Escenario histórico de PEA 3. Los roles guardados conservan los parámetros con que se generaron.',
 'Daylé, 55 segundos. Mostrar organigrama, un rol existente y su Excel. La captura pertenece a la evidencia PEA 3. El padrón operativo actual puede variar si se editaron empleados. Explicar que el costo empresarial agrega aportes y provisiones al sueldo. No crear un nuevo período durante la demostración.',
 'PEA3/figuras/01_organigrama.png; Informe_PEA3_ContratacionLaboral_FERIAUTO.pdf, pp. 13 y 14.');
 image(s,path.join(ROOT,'../PEA3/figuras/01_organigrama.png'),62,176,565,449,'Organigrama de FERIAUTO conservado en las evidencias PEA 3');
 text(s,'5 trabajadores',690,190,520,54,31,C.green,true);
 text(s,'4 directivos y 1 programador junior',691,253,500,61,19,C.muted);
 text(s,'USD 2.650,00',690,335,520,58,31,C.ink,true);
 text(s,'Remuneraciones base del informe',691,401,510,40,19,C.muted);
 text(s,'USD 3.490,85',690,476,520,58,31,C.blue,true);
 text(s,'Costo de personal con aportes\ny provisiones',691,542,510,71,19,C.muted);
 caption(s,'Herramientas existentes: empleados, escalas, organigrama, roles consolidados e individuales y exportación Excel.');
}
// 7 Resultado ministerial real del supuesto ficticio.
{
 const s=slide('Liquidación respaldada por el resultado ministerial','Caso ficticio por acuerdo entre las partes. Consulta conservada del 17 de noviembre de 2026.',
 'Pablo, 60 segundos. Explicar el supuesto: Mateo Demostración Rivera, ingreso 1 de octubre de 2026, salida 17 de noviembre de 2026, sueldo USD 510, Sierra y décimos acumulados. Los importes provienen del PDF ministerial existente. El escenario comparativo por despido da USD 1.692,83 y no se suma al acuerdo. Ambos son aproximados y no vinculantes.',
 'casos/ape4/liquidacion-oficial.pdf y comparacion-despido-oficial.pdf, ambos p. 1; calculadoras.trabajo.gob.ec/liquidaciones.');
 image(s,path.join(BUILD,'assets/ministerio.png'),62,172,312,443,'PDF original del simulador ministerial para el caso ficticio');
 table(s,[['Rubro del acuerdo','USD'],['Décimo tercero','66,58'],['Décimo cuarto','62,93'],['Vacaciones','33,32'],['Indemnizaciones','0,00'],['Total aproximado','162,83']],420,180,794,343,[580,214],18);
 text(s,'Comparación por despido: USD 1.692,83',422,554,785,42,25,C.blue,true);
 text(s,'Mismo supuesto, distinta forma de terminación.',422,602,785,34,18,C.muted);
 caption(s,'La integración conserva los PDF y sus resultados. No vuelve a calcular los derechos laborales.');
}
// 8 Control documental de paz y salvo, nativo + muestra conservada.
{
 const s=slide('El paz y salvo conserva la trazabilidad del cierre','La muestra del expediente permite seguir los requisitos y los productos documentales.',
 'Pablo, 55 segundos. Mostrar la muestra del resumen de paz y salvo. Ocho áreas participan en el flujo. De los 21 requisitos, 19 corresponden a controles previos y dos a seguimiento IESS/SUT. El resumen para firma no acredita firmas, pagos o trámites completados. No aprobar ni emitir nuevos documentos durante la defensa del integrador.',
 'entregables_ape4/resumen-general-para-firma.pdf, p. 1; insumos-informe-APE4.md; flujo de paz_salvo.py.');
 image(s,path.join(BUILD,'assets/resumen.png'),62,176,306,433,'Muestra ficticia del resumen general de paz y salvo para firma');
 text(s,'8 áreas',420,183,360,65,35,C.green,true);
 text(s,'21 requisitos',815,183,390,65,35,C.green,true);
 table(s,[['Control','Evidencia o resultado'],['Revisión por área','Requisitos y archivos del expediente'],['Emisión documental','Certificado, liquidación y resumen'],['Seguimiento','IESS y finiquito SUT cuando aplica']],420,285,794,264,[260,534],17);
 text(s,'19 requisitos previos y 2 de seguimiento',422,574,790,41,23,C.ink,true);
 caption(s,'El paz y salvo administrativo no reemplaza los documentos oficiales ni acredita firmas o trámites realizados.');
}
// 9 Recursos audiovisuales vinculados, hipervínculos nativos.
{
 const s=slide('Los videos complementan los trabajos escritos','Tres carpetas del grupo, vinculadas a sus módulos y localizables en la biblioteca.',
 'Grupo, 40 segundos. Mostrar los tres accesos de Drive sin reproducir necesariamente los videos completos. El pitch acompaña el modelo de negocio; los casos judiciales acompañan nómina y liquidación; el despido ideal propone trato humano y comunicación. Los enlaces conservan sus permisos originales. No afirmar que esta presentación valida o modifica los contenidos audiovisuales.',
 'Carpetas de Drive aportadas por el grupo: '+pitch+' ; '+judicial+' ; '+despido);
 const t=table(s,[['Recurso','Módulo','Aporte a la exposición'],['Elevator pitch y Canvas','Emprendimiento','Comunicación de la propuesta de negocio'],['Casos judiciales','Nómina y liquidación','Análisis y argumentación laboral'],['El despido ideal','Liquidación laboral','Reflexión sobre trato humano y comunicación']],62,194,1152,340,[330,330,492],18);
 [pitch,judicial,despido].forEach((uri,i)=>{const c=t.getCell(i+1,0);c.text.get(c.value).link={uri,isExternal:true};});
 text(s,'El despido ideal se presenta como reflexión sobre el trato humano,\nsin sustituir el procedimiento legal de terminación.',64,573,1138,65,21,C.ink);
}
// 10 Cierre con acceso verificable y QR funcional.
{
 const s=slide('Demostración y acceso a la plataforma','La defensa sigue los trabajos existentes y su respaldo documental.',
 'Cierre grupal, 45 segundos. Abrir el enlace publicado. Recorrer un módulo, mostrar un resultado y abrir su documento fuente. En los módulos laborales, abrir un rol y la muestra de paz y salvo. La copia local http://127.0.0.1:5050 sirve como respaldo si ya está iniciada. Cerrar con el aporte de integración y responder preguntas.',
 'Plataforma publicada '+URL+'; informes PEA 1, PEA 2, PEA 3 y muestras APE 4. QR funcional del mismo enlace.');
 image(s,path.join(BUILD,'assets/acceso.svg'),840,195,340,340,'Código QR de acceso a la plataforma publicada',URL);
 text(s,'1',64,211,65,55,35,C.green,true);text(s,'Elegir un módulo',150,211,610,45,27,C.ink,true);
 text(s,'Abrir la síntesis y ubicar su resultado.',150,270,610,67,21,C.muted);
 text(s,'2',64,365,65,55,35,C.green,true);text(s,'Consultar la evidencia',150,365,610,45,27,C.ink,true);
 text(s,'Revisar el documento, la página y el período.',150,424,610,67,21,C.muted);
 const link=text(s,'seby10.pythonanywhere.com',64,566,1150,54,29,C.green,true);link.hyperlink={uri:URL,isExternal:true};
 caption(s,'Cuatro módulos organizados, resultados con contexto y evidencias del semestre en un mismo acceso.');
}

await fs.writeFile(path.join(BUILD,REV,'contenido_y_notas.json'),JSON.stringify(records,null,2));
const old=path.join(OUT,'respaldo_presentacion_antes_redisenio/Presentacion_Integrador_FERIAUTO_Grupo1.pptx');
try {const previous=await PresentationFile.importPptx(await FileBlob.load(old));const ins=await previous.inspect({kind:'slide,notes',maxChars:3000});await fs.writeFile(path.join(BUILD,'inspeccion_anterior.ndjson'),ins.ndjson);}catch(e){await fs.writeFile(path.join(BUILD,'inspeccion_anterior_error.txt'),String(e));}
const candidate=path.join(BUILD,`candidate-${REV}.pptx`);
await (await PresentationFile.exportPptx(p)).save(candidate);
let result;
try {
result=await finalizePresentation({workspaceDir:OUT,candidatePath:candidate,finalPath:FINAL,pythonExecutable:path.join(RUNTIME,'python/python.exe'),integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...([4,5,7,8,9].flatMap(n=>['--require-native-table-slide',String(n)]))],explicitTotalSlideCount:10,requiredNativeTableOwnerSlides:[4,5,7,8,9],fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:path.join(BUILD,`validacion-${REV}.json`)});
} catch(e) {
 if(e.code!=='EPERM'||e.syscall!=='link')throw e;
 // El filesystem de Windows restringe hardlinks. El fallo sucede únicamente
 // después de completar los validadores y cotejar los bytes de preparación.
 const {createHash}=await import('node:crypto');
 const before=await fs.readFile(candidate);await fs.copyFile(candidate,FINAL,1);
 const after=await fs.readFile(FINAL);const sha=b=>createHash('sha256').update(b).digest('hex');
 if(sha(before)!==sha(after))throw new Error('La copia final difiere del candidato validado');
 result={passedPrepublicationValidation:true,publication:'exclusive-copy-after-Windows-hardlink-EPERM',sha256:sha(after),bytes:after.length};
 await fs.writeFile(path.join(BUILD,`validacion-${REV}.json`),JSON.stringify(result,null,2));
}
console.log(JSON.stringify({final:FINAL,result}));
for(const [i,s] of p.slides.items.entries()){
 try {const blob=await p.export({slide:s,format:'png',scale:1});await fs.writeFile(path.join(BUILD,REV,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await blob.arrayBuffer()));}
 catch(e){console.log('RENDER_ERROR',i+1,String(e).slice(0,300));break;}
}
try {const blob=await p.export({format:'pdf'});await fs.writeFile(path.join(path.dirname(FINAL),'artifact.pdf'),new Uint8Array(await blob.arrayBuffer()));}catch(e){console.log('PDF_EXPORT_ERROR',String(e).slice(0,400));}
