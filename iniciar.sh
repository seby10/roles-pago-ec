#!/usr/bin/env sh
# Abre la demo de Roles de Pago en macOS / Linux:  ./iniciar.sh
# La primera vez crea un entorno (.venv) e instala Flask; las siguientes arranca directo.
cd "$(dirname "$0")" || exit 1

PY=$(command -v python3 || command -v python) || { echo "Necesitas Python 3.9+: https://www.python.org/downloads/"; exit 1; }
"$PY" -c "import sys; sys.exit(sys.version_info < (3, 9))" || { echo "Necesitas Python 3.9 o superior."; exit 1; }

if [ ! -x .venv/bin/python ]; then
  echo "Preparando el entorno por primera vez..."
  # En Ubuntu/Debian puede faltar el módulo venv:  sudo apt install python3-venv
  "$PY" -m venv .venv || exit 1
fi
.venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt || exit 1

URL=http://127.0.0.1:5050
echo "Demo de Roles de Pago en $URL  (Ctrl+C para cerrar)"
( sleep 2; open "$URL" 2>/dev/null || xdg-open "$URL" 2>/dev/null ) &
exec .venv/bin/python app.py
