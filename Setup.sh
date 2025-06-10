#!/bin/bash

sudo apt update
sudo apt install -y python3 python3-pip
sudo apt-get install -y cec-utils xdotool unclutter unclutter-xfixes

pip3 install --upgrade \
    google-api-python-client \
    google-auth-httplib2 \
    google-auth-oauthlib \
    pytz \
    python-dateutil \
    pyautogui\
    --break-system-packages

mkdir -p /home/pi/RPI-Conference
echo "" > /home/pi/RPI-Conference/.last_link_opened
echo "" > /home/pi/RPI-Conference/eventos.html
cp ./Abrir-reunion.py /home/pi/RPI-Conference/Abrir-reunion.py
cp ./cec_control.sh /home/pi/RPI-Conference/cec_control.sh
cp ./estilos.css /home/pi/RPI-Conference/estilos.css
cp ./credentials.json /home/pi/RPI-Conference/credentials.json
chmod +x /home/pi/RPI-Conference/Abrir-reunion.py
chmod +x /home/pi/RPI-Conference/cec_control.sh


mkdir -p /home/pi/.config/autostart

cat > /home/pi/.config/autostart/cec-remote.desktop << EOF
[Desktop Entry]
Type=Application
Name=CEC Remote Script
Exec=/home/pi/RPI-Conference/cec_control.sh
StartupNotify=false
Terminal=false
EOF

servicePath="/etc/systemd/system/cec_control.service"
sudo tee "$servicePath" > /dev/null << EOF
[Unit]
Description=CEC Remote Control Service
After=graphical.target

[Service]
Type=simple
User=pi
Environment=DISPLAY=:0
ExecStart=/usr/bin/script -q -c /home/pi/RPI-Conference/cec_control.sh /dev/null
Restart=always
RestartSec=3

[Install]
WantedBy=graphical.target
EOF


reunionServicePath="/etc/systemd/system/abrir-reunion.service"
sudo tee "$reunionServicePath" > /dev/null << EOF
[Unit]
Description=Servicio para abrir reuniones automáticamente
After=graphical.target

[Service]
Type=simple
User=pi
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
ExecStart=/usr/bin/python3 /home/pi/RPI-Conference/Abrir-reunion.py
Restart=always
RestartSec=10

[Install]
WantedBy=graphical.target
EOF

sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable cec_control.service
sudo systemctl restart cec_control.service