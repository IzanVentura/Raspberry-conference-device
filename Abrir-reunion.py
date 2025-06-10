from __future__ import print_function
import os.path
import json
import html
import subprocess
from urllib.parse import urlparse
import pytz
import re
import time
import os
import pyautogui
from datetime import datetime, timedelta
from dateutil import parser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
URL_REGEX = re.compile(r'https?://[^\s<>"\']+')
HTML_OUTPUT_PATH = '/home/pi/RPI-Conference/eventos.html'
CRED_PATH = '/home/pi/RPI-Conference/credentials.json'
TOKEN_PATH = '/home/pi/RPI-Conference/token.json'
LOCAL_TZ = pytz.timezone('Europe/Madrid')

def extract_links_from_event(event):
    text_to_search = []

    for field in ['summary', 'description', 'location']:
        value = event.get(field)
        if value:
            text_to_search.append(value)

    if 'hangoutLink' in event:
        text_to_search.append(event['hangoutLink'])

    conference = event.get('conferenceData', {})
    entry_points = conference.get('entryPoints', [])
    for entry in entry_points:
        uri = entry.get('uri')
        if uri:
            text_to_search.append(uri)

    text_to_search.append(json.dumps(event))
    seen = set()

    for text in text_to_search:
        text = html.unescape(text)
        href_matches = re.findall(r'href=["\'](https?://[^"\'>\s]+)', text)
        raw_matches = URL_REGEX.findall(text)
        all_matches = href_matches + raw_matches

        for url in all_matches:
            url = url.strip().rstrip('.,);\'">')
            if "google.com/calendar" in url or "fonts.gstatic.com" in url:
                continue
            parsed = urlparse(url)
            simplified = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if simplified in seen:
                continue
            seen.add(simplified)
            return url

    return None


def is_chromium_running():
    try:
        result = subprocess.run(['pgrep', '-f', 'chromium'], stdout=subprocess.DEVNULL)
        return result.returncode == 0
    except Exception as e:
        print(f"Error checking chromium process: {e}")
        return False


def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CRED_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def generate_html(events):
    html_blocks = ""

    if not events:
        html_blocks = "<p class='no-eventos'>No hay eventos en los próximos 7 días.</p>"
    else:
        for i, event in enumerate(events):
            if not event['start'].get('dateTime'):
                continue
            summary = event.get('summary', 'Sin título')
            start_dt = parser.isoparse(event['start']['dateTime']).astimezone(LOCAL_TZ)
            end_dt = parser.isoparse(event['end']['dateTime']).astimezone(LOCAL_TZ)
            link = extract_links_from_event(event)
            if not link:
                continue
            html_blocks += f"""
            <div class="evento" tabindex="0" data-index="{i}">
              <a href="{link}" target="_blank">
                <h3>{html.escape(summary)}</h3>
                <p class="fecha">Inicio: {start_dt.strftime('%Y-%m-%d %H:%M')}<br>Fin: {end_dt.strftime('%Y-%m-%d %H:%M')}</p>
              </a>
            </div>
            """

        if not html_blocks:
            html_blocks = "<p class='no-eventos'>No hay eventos en los próximos 7 días.</p>"

    with open(HTML_OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="30">
  <title>Eventos</title>
  <link rel="stylesheet" type="text/css" href="estilos.css">
</head>
<body>
  <h1 id="Eventos">Lista de Eventos (próximos 7 días)</h1>
  <div class="container">
    {html_blocks}
  </div>
<script>
  document.addEventListener('DOMContentLoaded', () => {{
    const eventos = document.querySelectorAll('.evento');
    let index = 0;

    const savedIndex = localStorage.getItem('eventoActivoIndex');
    if (savedIndex !== null && eventos.length > savedIndex) {{
        index = parseInt(savedIndex, 10);
    }} else {{
        localStorage.removeItem('eventoActivoIndex');
    }}

    if (eventos.length > 0) {{
        eventos[index].classList.add('activo');
        eventos[index].focus();
    }}

    function updateActive(newIndex) {{
      if (eventos.length === 0) return;
      eventos[index].classList.remove('activo');
      index = (newIndex + eventos.length) % eventos.length;
      eventos[index].classList.add('activo');
      eventos[index].focus();
      eventos[index].scrollIntoView({{ behavior: 'smooth', block: 'center' }});
      localStorage.setItem('eventoActivoIndex', index);
    }}

    document.addEventListener('keydown', (e) => {{
      if (e.key === 'ArrowDown') {{
        updateActive(index + 3);
        e.preventDefault();
      }} else if (e.key === 'ArrowUp') {{
        updateActive(index - 3);
        e.preventDefault();
      }} else if (e.key === 'ArrowRight') {{
        updateActive(index + 1);
        e.preventDefault();
      }} else if (e.key === 'ArrowLeft') {{
        updateActive(index - 1);
        e.preventDefault();
      }} else if (e.key === 'Enter') {{
        const enlace = eventos[index].querySelector('a');
        if (enlace && enlace.href) {{
          window.open(enlace.href, '_blank');
        }}
        e.preventDefault();
      }}
    }});
  }});
</script>
</body>
</html>""")
    print(f"[INFO] HTML actualizado en: {HTML_OUTPUT_PATH}")
    return True


def launch_chromium():
    if not is_chromium_running():
        env = os.environ.copy()
        env['DISPLAY'] = ':0'
        env['XDG_RUNTIME_DIR'] = '/run/user/1000'
        env['DBUS_SESSION_BUS_ADDRESS'] = 'unix:path=/run/user/1000/bus'
        try:
            subprocess.Popen([
                'chromium',
                '--start-fullscreen',
                '--force-renderer-accessibility',
                '--enable-remote-extensions',
                '--disable-features=WebRtcUseEchoCanceller3,WebRtcUseHardwareAcousticEchoCanceller,WebRtcUseExperimentalAgc',
                '--disable-gpu-compositing',
                '--disable-accelerated-video-decode',
                '--hide-crash-restore-bubble',
                HTML_OUTPUT_PATH
            ], env=env)
            print("[INFO] Chromium lanzado.")
        except FileNotFoundError:
            print("Chromium no está instalado o no se encuentra en el PATH.")
        screen_width, screen_height = pyautogui.size()
        center_x = screen_width // 2
        center_y = screen_height // 2
        pyautogui.moveTo(center_x, center_y)
    else:
        print("[INFO] Chromium ya está en ejecución.")


def main_loop():
    service = get_calendar_service()
    while True:
        try:
            now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
            future_utc = now_utc + timedelta(days=7)

            events_result = service.events().list(
                calendarId='primary',
                timeMin=now_utc.isoformat(),
                timeMax=future_utc.isoformat(),
                maxResults=20,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            if not events:
                print('[INFO] No upcoming events in the next 7 days.')

            # Genera el HTML y lanza Chromium en todos los casos
            generate_html(events)
            launch_chromium()

        except Exception as e:
            print(f"[ERROR] {e}")

        time.sleep(30)


if __name__ == '__main__':
    main_loop()
