# Publicar la demo en PythonAnywhere

Para que la docente vea el sistema con los datos de FERIAUTO desde un enlace, sin instalar nada.

**Por qué PythonAnywhere:** corre Flask tal cual, el plan gratuito guarda la base SQLite entre visitas y da una URL pública (`usuario.pythonanywhere.com`). Vercel o el plan gratuito de Render no sirven: no conservan el archivo `roles.db`.

**Cómo queda:** en modo **solo lectura**. Cualquiera puede navegar, ver el organigrama, abrir roles, descargar los Excel y usar la vista previa de novedades, pero no guardar cambios. Para editar se entra con una clave (enlace *Modo edición* en el pie de página).

## Pasos (una sola vez, unos 15 minutos)

1. Crea una cuenta gratuita en <https://www.pythonanywhere.com> (*Beginner*). El nombre de usuario será parte de la URL.
2. **Consoles → Bash** y clona el repositorio. Como es privado, GitHub pide usuario y un *personal access token* (Settings → Developer settings → Fine-grained token con permiso de lectura sobre este repo):

   ```bash
   git clone https://github.com/seby10/roles-pago-ec.git
   cd roles-pago-ec
   pip install --user -r requirements.txt
   ```

3. **Web → Add a new web app → Manual configuration → Python 3.12** (o la más reciente).
4. En la misma página, **Source code**: `/home/USUARIO/roles-pago-ec`.
5. Abre el **WSGI configuration file** que enlaza la página, borra su contenido y pega esto (cambia `USUARIO` y las dos claves):

   ```python
   import os, sys
   os.environ["EDIT_PASSWORD"] = "una-clave-para-el-grupo"
   os.environ["SECRET_KEY"] = "pega-aqui-una-cadena-larga-y-aleatoria"
   sys.path.insert(0, "/home/USUARIO/roles-pago-ec")
   from app import app as application
   ```

   Para la cadena aleatoria: `python -c "import secrets; print(secrets.token_hex(32))"` en la consola.
6. **Reload** (botón verde) y abre `https://USUARIO.pythonanywhere.com`.
7. Entra en *Modo edición*, genera el rol de octubre 2026 para que la docente lo encuentre listo y sal del modo edición.

## Actualizar después de un cambio

Para esta versión de **Paz y salvo**, también hay que instalar las nuevas dependencias de PDF antes de recargar:

```bash
cd ~/roles-pago-ec
git pull --ff-only origin main
python3.12 -m pip install --user -r requirements.txt
```

Usa la misma versión de Python que indica tu aplicación en la pestaña **Web** (sustituye `python3.12` si es otra). Si la aplicación utiliza un entorno virtual, actívalo con `workon NOMBRE_DEL_ENTORNO` y ejecuta `python -m pip install -r requirements.txt` sin `--user`. El entorno virtual configurado en Web debe coincidir con el usado para instalar las dependencias. [Guía oficial de Flask en PythonAnywhere](https://help.pythonanywhere.com/pages/Flask/).

Después pulsa **Reload** en la pestaña Web. La base `roles.db` no está en git. Si estaba en esquema 6, la primera carga crea `roles_v6_pre_paz_salvo_respaldo.db` y agrega las tablas de paz y salvo conservando los datos existentes. Para esquemas anteriores revisa la sección de migración de [PAZ_Y_SALVO.md](PAZ_Y_SALVO.md) antes de actualizar.

Entra en **Modo edición → Paz y salvo → Nuevo expediente** para probarlo. Con `EDIT_PASSWORD` configurada, los expedientes y adjuntos no están disponibles en la navegación pública. Prueba con datos ficticios y evita **Reiniciar demo** si necesitas conservar datos o archivos.

## A tener en cuenta

- El plan gratuito pide entrar a la cuenta y pulsar *Run until 3 months from today* cada 3 meses; si no, la web se desactiva.
- Las fuentes tipográficas vienen de Google Fonts y la web publicada tiene internet, así que se ven igual que en local.
- No uses en `EDIT_PASSWORD` una contraseña personal: es una clave compartida del grupo.
