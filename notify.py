import json
import requests
import os
from datetime import datetime

# GitHub Secrets werden hier eingelesen
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram Credentials fehlen.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload)

def check_and_notify():
    if not os.path.exists("releases.json"): return

    with open("releases.json", "r") as f:
        data = json.load(f)

    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Finde Releases, die heute (vom Datum her) gefunden wurden
    # Da der Scraper das Feld 'date_found' setzt
    new_releases = [r for r in data if r.get('date_found') == today_str]

    if new_releases:
        msg = f"<b>🎵 Nodata Radar: {len(new_releases)} neue Releases!</b>\n\n"
        for r in new_releases[:5]: # Max 5 anzeigen, sonst wird Nachricht zu lang
            genre_txt = f" ({', '.join(r['genres'][:2])})" if r.get('genres') else ""
            msg += f"• <b>{r['artist']}</b> - {r['album']}{genre_txt}\n"
            msg += f"  <a href='{r['links']['youtube']}'>▶ YouTube</a> | <a href='{r.get('detail_url', 'https://nodata.tv')}'>Info</a>\n\n"
        
        if len(new_releases) > 5:
            msg += f"<i>...und {len(new_releases)-5} weitere.</i>"
            
        print("Sende Telegram Benachrichtigung...")
        send_telegram_message(msg)
    else:
        print("Keine neuen Releases heute.")

if __name__ == "__main__":
    check_and_notify()
