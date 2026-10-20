@echo off
rem Doble clic para abrir la demo de Roles de Pago en Windows.
rem La primera vez crea un entorno (.venv) e instala Flask; las siguientes arranca directo.
chcp 65001 >nul
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto :sinpython
%PY% -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>nul || goto :sinpython

if not exist ".venv\Scripts\python.exe" (
  echo Preparando el entorno por primera vez, espera un momento...
  %PY% -m venv .venv || goto :error
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt || goto :error

echo.
echo  Demo de Roles de Pago en http://127.0.0.1:5050
echo  Para cerrarla, cierra esta ventana o presiona Ctrl+C.
echo.
start "" cmd /c "timeout /t 2 >nul & start http://127.0.0.1:5050"
".venv\Scripts\python.exe" app.py
pause
exit /b 0

:sinpython
echo Necesitas Python 3.9 o superior: https://www.python.org/downloads/
echo Al instalarlo marca la casilla "Add python.exe to PATH" y vuelve a abrir este archivo.
pause
exit /b 1

:error
echo.
echo No se pudo preparar el entorno. Revisa tu conexion a internet (solo se necesita la primera vez).
pause
exit /b 1
