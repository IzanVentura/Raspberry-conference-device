#!/bin/bash

echo "=== Instalando dependencias básicas ==="
sudo apt update
sudo apt install -y python3 python3-pip
sudo apt-get install -y cec-utils xdotool unclutter unclutter-xfixes

echo "=== Instalando librerías de Google API ==="
pip3 install --upgrade \
    google-api-python-client \
    google-auth-httplib2 \
    google-auth-oauthlib \
    pytz \
    python-dateutil \
    --break-system-packages

echo ""
echo "=== Creando estructura de archivos ==="
mkdir -p /home/pi/Calendario
echo "" > /home/pi/Calendario/.last_link_opened

echo "=== Añadiendo tarea a crontab para Abrir-reunion.py ==="
CRON_LINE="* * * * * export DISPLAY=:0 && export XAUTHORITY=/home/pi/.Xauthority && export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus && /usr/bin/python3 /home/pi/Calendario/Abrir-reunion.py > /dev/null 2>&1"

(crontab -l 2>/dev/null | grep -F "$CRON_LINE") >/dev/null
if [ $? -eq 0 ]; then
    echo "La tarea ya está en el crontab."
else
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
    echo "Tarea añadida correctamente al crontab."
fi

echo "=== Creando archivo .desktop para lanzar script CEC en inicio gráfico ==="
mkdir -p /home/pi/.config/autostart

cat > /home/pi/.config/autostart/cec-remote.desktop << EOF
[Desktop Entry]
Type=Application
Name=CEC Remote Script
Exec=/home/pi/Calendario/cec_control.sh
StartupNotify=false
Terminal=false
EOF

echo "Archivo cec-remote.desktop creado en /home/pi/.config/autostart/cec-remote.desktop"

echo "=== Creando servicio systemd para cec_control.sh ==="

SERVICE_PATH="/etc/systemd/system/cec_control.service"
sudo tee "$SERVICE_PATH" > /dev/null << EOF
[Unit]
Description=CEC Remote Control Service
After=graphical.target

[Service]
Type=simple
User=pi
Environment=DISPLAY=:0
ExecStart=/usr/bin/script -q -c /home/pi/Calendario/cec_control.sh /dev/null
Restart=always
RestartSec=3

[Install]
WantedBy=graphical.target
EOF

echo "Servicio creado: $SERVICE_PATH"

echo "Recargando systemd, habilitando y arrancando el servicio..."
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable cec_control.service
sudo systemctl restart cec_control.service

echo ""
echo "=== Todo listo ==="
echo "Asegúrate de tener el archivo 'credentials.json' y 'Abrir-reunion.py' en este mismo directorio."
echo ""

read -p "¿Quieres ejecutar ahora el script Abrir-reunion.py para autorizar la cuenta? (s/n): " respuesta

if [[ "$respuesta" =~ ^[Ss]$ ]]; then
    if [[ -f "Abrir-reunion.py" ]]; then
        echo "Ejecutando Abrir-reunion.py..."
        python3 Abrir-reunion.py
    else
        echo "No se encontró Abrir-reunion.py en este directorio."
    fi
else
    echo "Puedes ejecutar más tarde: python3 Abrir-reunion.py"
fi
