from __future__ import print_function
import datetime
import os.path
import pytz
import re
import json
import subprocess
import sys
import html
from urllib.parse import urlparse
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dateutil import parser

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
URL_REGEX = re.compile(r'https?://[^\s<>"\']+')

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
        print(f"Error comprobando proceso chromium: {e}")
        return False

def main():
    creds = None
    token_path = '/home/pi/Calendario/token.json'
    creds_path = '/home/pi/Calendario/credentials.json'

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            try:
                creds = flow.run_local_server(port=0)
            except Exception:
                print("No se pudo abrir el navegador automáticamente. Usando autenticación por consola...")
                creds = flow.run_console()
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    now_utc = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    now_str = now_utc.isoformat()
    events_result = service.events().list(
        calendarId='primary',
        timeMin=now_str,
        maxResults=10,
        singleEvents=True,
        orderBy='startTime').execute()

    events = events_result.get('items', [])
    if not events:
        print('No hay eventos próximos.')
        return

    next_event = None
    for event in events:
        if event['start'].get('dateTime'):
            next_event = event
            break

    if not next_event:
        print("No hay próximos eventos con fecha y hora específica.")
        return

    summary = next_event.get('summary', 'Sin título')
    local_tz = pytz.timezone('Europe/Madrid')
    start_dt = parser.isoparse(next_event['start']['dateTime']).astimezone(local_tz)
    end_dt = parser.isoparse(next_event['end']['dateTime']).astimezone(local_tz)

    print(f"Próxima reunión: {summary} de {start_dt} a {end_dt}")

    link = extract_links_from_event(next_event)
    if not link:
        print("No se encontraron enlaces.")
        return

    opened_file = '/home/pi/Calendario/.last_link_opened'
    if os.path.exists(opened_file):
        with open(opened_file, 'r') as f:
            last_link = f.read().strip()
        if last_link == link:
            print("La reunión ya fue abierta anteriormente.")
            return

    chromium_running = is_chromium_running()
    if chromium_running:
        print("Chromium está abierto con otro enlace, no se abrirá otro.")
        return


    seconds_to_start = (start_dt - now_utc).total_seconds()

    if (start_dt <= now_utc <= end_dt) or (0 <= seconds_to_start <= 60):
        print(link)
        try:
            subprocess.Popen([
                'chromium',
                '--start-fullscreen',
                '--user-data-dir=/home/pi/.config/chromium',
                '--force-renderer-accessibility',
                '--enable-remote-extensions',
                '--disable-features=WebRtcUseEchoCanceller3,WebRtcUseHardwareAcousticEchoCanceller,WebRtcUseExperimentalAgc',
                '--disable-gpu-compositing',
                '--disable-accelerated-video-decode',
                '--use-gl=egl',
                link
            ])
            with open(opened_file, 'w') as f:
                f.write(link)
        except FileNotFoundError:
            print("Chromium no está instalado o no se encuentra 'chromium-browser' en el PATH.")
            sys.exit(1)

if __name__ == '__main__':
    main()
