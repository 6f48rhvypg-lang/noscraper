import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime
import time
import urllib.parse
from typing import Optional

# --- Configuration ---
DATA_FILE = "releases.json"
REQUEST_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
REQUEST_TIMEOUT = 15
DEEP_SCRAPE_DELAY = 0.5  # Delay between detail page requests to avoid rate limiting

# Telegram Configuration (via Environment Variables for security)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
STREAMLIT_APP_URL = os.environ.get("STREAMLIT_APP_URL", "https://nodata-radar.streamlit.app")

# Genre categories to filter out (not actual music genres)
IGNORED_CATEGORIES = frozenset([
    'EP', 'Album', 'Single', 'Remix', 'Various Artists', 
    'Uncategorized', 'LP', 'Compilation', 'VA'
])


# =============================================================================
# TELEGRAM NOTIFICATIONS
# =============================================================================

def send_telegram_alert(new_releases: list, notify_enabled: bool = True) -> bool:
    """
    Sendet eine Telegram-Benachrichtigung über neue Releases.
    
    Args:
        new_releases: Liste der neu gefundenen Release-Dictionaries
        notify_enabled: Wenn False, wird keine Nachricht gesendet (für Tests)
        
    Returns:
        True wenn erfolgreich, False bei Fehler oder fehlenden Credentials
        
    Environment Variables Required:
        TELEGRAM_TOKEN: Bot Token von @BotFather
        TELEGRAM_CHAT_ID: Chat/Channel ID für Benachrichtigungen
    """
    if not notify_enabled:
        print("📵 Telegram-Benachrichtigung deaktiviert (notify_enabled=False)")
        return False
    
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram-Credentials fehlen (TELEGRAM_TOKEN / TELEGRAM_CHAT_ID)")
        print("   Setze diese als Environment Variables oder GitHub Secrets.")
        return False
    
    if not new_releases:
        print("📭 Keine neuen Releases - keine Benachrichtigung gesendet.")
        return False
    
    # --- Build HTML Message ---
    count = len(new_releases)
    
    # Header
    message_parts = [
        f"🎵 <b>Nodata Radar: {count} neue Release{'s' if count != 1 else ''}!</b>",
        ""
    ]
    
    # Release List (max 8 to avoid message length limits)
    for release in new_releases[:8]:
        artist = release.get('artist', 'Unknown')
        album = release.get('album', '')
        genres = release.get('genres', [])
        detail_url = release.get('detail_url', '')
        
        # Format: Artist - Album (Genre1, Genre2)
        line = f"• <b>{_escape_html(artist)}</b>"
        if album:
            line += f" — {_escape_html(album)}"
        
        # Add genres if available
        if genres:
            genre_str = ", ".join(genres[:3])
            line += f" <i>({genre_str})</i>"
        
        message_parts.append(line)
        
        # Add link to detail page
        if detail_url:
            message_parts.append(f"  └ <a href=\"{detail_url}\">🔗 Details</a>")
    
    # Show "and X more" if truncated
    if count > 8:
        message_parts.append(f"\n<i>...und {count - 8} weitere.</i>")
    
    # Footer with App Link
    message_parts.extend([
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🚀 <a href=\"{STREAMLIT_APP_URL}\">Öffne Nodata Radar App</a>"
    ])
    
    message = "\n".join(message_parts)
    
    # --- Send via Telegram Bot API ---
    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True  # Prevent link previews cluttering the message
    }
    
    try:
        print(f"📤 Sende Telegram-Benachrichtigung ({count} Releases)...")
        response = requests.post(api_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                print(f"✅ Telegram-Nachricht erfolgreich gesendet!")
                return True
            else:
                print(f"⚠️ Telegram API Fehler: {result.get('description', 'Unknown')}")
                return False
        else:
            print(f"⚠️ Telegram HTTP {response.status_code}: {response.text[:200]}")
            return False
            
    except requests.Timeout:
        print("⚠️ Telegram-Timeout - Nachricht nicht gesendet.")
        return False
    except requests.RequestException as e:
        print(f"⚠️ Telegram-Netzwerkfehler: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Unerwarteter Telegram-Fehler: {e}")
        return False


def _escape_html(text: str) -> str:
    """Escaped HTML-Sonderzeichen für Telegram HTML parse_mode."""
    if not text:
        return ""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def get_existing_data() -> list:
    """Lädt bestehende Release-Daten aus der JSON-Datei."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def generate_search_links(artist: str, title: str) -> dict:
    """Generiert Such-Links für verschiedene Musik-Plattformen."""
    query = urllib.parse.quote_plus(f"{artist} {title}")
    return {
        "youtube": f"https://www.youtube.com/results?search_query={query}",
        "bandcamp": f"https://bandcamp.com/search?q={query}",
        "soundcloud": f"https://soundcloud.com/search?q={query}",
        "apple": f"https://music.apple.com/de/search?term={query}"
    }


def _parse_date_from_text(text: str) -> str:
    """
    Extrahiert ein Datum aus einem String.
    Unterstützt Formate wie 'Nov 23, 2025' oder 'November 23, 2025'.
    
    Returns:
        ISO-formatiertes Datum (YYYY-MM-DD) oder heutiges Datum als Fallback.
    """
    # Regex für verschiedene Datumsformate
    patterns = [
        (r'([A-Za-z]{3,9} \d{1,2}, \d{4})', "%b %d, %Y"),      # Nov 23, 2025
        (r'(\d{1,2} [A-Za-z]{3,9} \d{4})', "%d %b %Y"),        # 23 Nov 2025
        (r'(\d{4}-\d{2}-\d{2})', "%Y-%m-%d"),                   # 2025-11-23
    ]
    
    for pattern, date_format in patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            try:
                dt = datetime.strptime(date_str, date_format)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
    
    return datetime.now().strftime("%Y-%m-%d")


def _parse_artist_album(full_text: str) -> tuple[str, str]:
    """
    Parst Artist und Album aus dem Titel-String.
    
    Handles various formats:
        - "Artist / Album [2025]"
        - "Artist / Album"
        - "Artist - Album [2025]"
        - "Artist – Album" (en-dash)
        - "Artist" (no album)
    
    Returns:
        Tuple von (artist, album)
    """
    if not full_text:
        return ("Unknown Artist", "")
    
    # Entferne Jahr-Tags wie [2025], [1992] etc.
    clean_text = re.sub(r'\s*\[\d{4}\]\s*$', '', full_text).strip()
    
    # Versuche verschiedene Trennzeichen (in Prioritätsreihenfolge)
    separators = [
        ' / ',      # Standard Nodata format
        ' – ',      # En-dash (Unicode)
        ' - ',      # Regular hyphen
        ' // ',     # Double slash
    ]
    
    for sep in separators:
        if sep in clean_text:
            parts = clean_text.split(sep, 1)
            artist = parts[0].strip()
            album = parts[1].strip() if len(parts) > 1 else ""
            
            # Nochmal Jahr-Tags aus Album entfernen (falls im mittleren Teil)
            album = re.sub(r'\s*\[.*?\]\s*', '', album).strip()
            
            if artist:  # Nur wenn Artist nicht leer
                return (artist, album)
    
    # Kein Trennzeichen gefunden -> Gesamter Text ist Artist
    return (clean_text, "")


def fetch_release_details(url: str) -> dict:
    """
    Besucht die Detail-Seite eines Releases und extrahiert zusätzliche Metadaten.
    
    Extrahiert:
        - genres: Liste der Genres aus der 'Posted in' Sektion
        - (erweiterbar für weitere Felder wie Label, Catalog#, etc.)
    
    Args:
        url: Die URL zur Nodata Detail-Seite
        
    Returns:
        Dict mit extrahierten Details, mindestens {'genres': [...]}
    """
    details = {
        'genres': [],
        'label': None,
        'catalog_number': None,
    }
    
    try:
        print(f"  → Fetching details: {url}")
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 200:
            print(f"    ⚠ HTTP {response.status_code} für {url}")
            return details
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # --- GENRES EXTRACTION ---
        # Suche nach <ul class="meta"> welches die "Posted in: Genre1, Genre2" Info enthält
        meta_section = soup.find('ul', class_='meta')
        
        if meta_section:
            # Methode 1: Suche nach Links mit rel="category tag" (WordPress Standard)
            genre_tags = meta_section.find_all('a', rel='category tag')
            
            if genre_tags:
                raw_genres = [tag.get_text(strip=True) for tag in genre_tags]
                # Filtere nicht-Genre Kategorien heraus
                details['genres'] = [g for g in raw_genres if g not in IGNORED_CATEGORIES]
            else:
                # Methode 2: Fallback - Suche nach "Posted in" Text und extrahiere Links
                for li in meta_section.find_all('li'):
                    li_text = li.get_text()
                    if 'Posted in' in li_text or 'Category' in li_text:
                        links = li.find_all('a')
                        raw_genres = [link.get_text(strip=True) for link in links]
                        details['genres'] = [g for g in raw_genres if g not in IGNORED_CATEGORIES]
                        break
        
        # --- OPTIONAL: Weitere Metadaten extrahieren ---
        # Label Info (falls vorhanden in der Detail-Seite)
        # Diese können später erweitert werden
        
        if details['genres']:
            print(f"    ✓ Found genres: {', '.join(details['genres'][:3])}{'...' if len(details['genres']) > 3 else ''}")
        
    except requests.Timeout:
        print(f"    ⚠ Timeout für {url}")
    except requests.RequestException as e:
        print(f"    ⚠ Request error für {url}: {e}")
    except Exception as e:
        print(f"    ⚠ Unerwarteter Fehler für {url}: {e}")
    
    return details

def _scrape_single_page(url: str, deep_scrape: bool = True) -> list:
    """
    Scraped eine einzelne Blog-Seite von Nodata.tv.
    
    Args:
        url: Die URL der Blog-Seite
        deep_scrape: Wenn True, werden Detail-Seiten für Genres besucht
        
    Returns:
        Liste von Release-Dictionaries
    """
    try:
        print(f"📄 Lade Seite: {url}")
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        page_releases = []
        
        # Im Blog View sind die Items in 'article.project-box'
        articles = soup.find_all('article', class_='project-box')
        
        if not articles:
            # Fallback: Versuche alternative Selektoren
            articles = soup.find_all('article', class_='post')
        
        print(f"   Gefunden: {len(articles)} Artikel")
        
        for idx, article in enumerate(articles):
            # --- TITEL & URL ---
            # Primärer Selektor für Blog View
            title_tag = article.select_one('.visual .hover3 .inside .area .object a.title')
            
            # Fallback Selektoren für verschiedene Themes/Layouts
            if not title_tag:
                title_tag = article.select_one('h2.entry-title a')
            if not title_tag:
                title_tag = article.select_one('a.title')
            if not title_tag:
                title_tag = article.find('a', class_='title')
            
            if not title_tag:
                print(f"   ⚠ Artikel {idx+1}: Kein Titel gefunden, überspringe...")
                continue
            
            full_text = title_tag.get_text(strip=True)
            detail_url = title_tag.get('href', '')
            
            if not full_text:
                continue
            
            # --- ARTIST / ALBUM PARSING ---
            artist, album = _parse_artist_album(full_text)
            
            # --- BILD ---
            img_tag = article.find('img')
            img_url = None
            if img_tag:
                # Prüfe verschiedene Bild-Attribute (src, data-src für lazy loading)
                img_url = img_tag.get('src') or img_tag.get('data-src') or img_tag.get('data-lazy-src')
            
            # --- DATUM ---
            meta_p = article.select_one('.visual .hover3 .inside .area .object p:last-of-type')
            if not meta_p:
                meta_p = article.select_one('time.entry-date')
            if not meta_p:
                meta_p = article.select_one('.entry-meta')
            
            pub_date = datetime.now().strftime("%Y-%m-%d")
            if meta_p:
                pub_date = _parse_date_from_text(meta_p.get_text())
            
            # --- SEARCH LINKS ---
            links = generate_search_links(artist, album)
            
            # --- DEEP SCRAPE: Genres von Detail-Seite ---
            genres = []
            if deep_scrape and detail_url:
                time.sleep(DEEP_SCRAPE_DELAY)  # Rate limiting
                details = fetch_release_details(detail_url)
                genres = details.get('genres', [])
            
            # --- RELEASE DATA ---
            release_data = {
                "id": full_text,  # Unique ID bleibt der volle Original-String
                "artist": artist,
                "album": album,
                "image": img_url,
                "date_found": pub_date,
                "genres": genres,
                "detail_url": detail_url,
                "links": links
            }
            page_releases.append(release_data)
            
            print(f"   ✓ {artist} - {album or '(Single)'}")
        
        return page_releases
        
    except requests.Timeout:
        print(f"⚠ Timeout beim Laden von {url}")
        return []
    except requests.RequestException as e:
        print(f"⚠ Netzwerkfehler für {url}: {e}")
        return []
    except Exception as e:
        print(f"⚠ Unerwarteter Fehler beim Scrapen von {url}: {e}")
        return []


def scrape_nodata(pages: int = 1, start_page: int = 1, deep_scrape: bool = True) -> list:
    """
    Hauptfunktion zum Scrapen von Nodata.tv Releases.
    
    Args:
        pages: Anzahl der zu scrapenden Seiten
        start_page: Startseite (1-basiert)
        deep_scrape: Wenn True, werden Detail-Seiten für Genres besucht.
                     Setzt DEEP_SCRAPE_DELAY (0.5s) zwischen Requests.
                     Wenn False, schnelleres Scraping ohne Genre-Info.
    
    Returns:
        Liste aller gefundenen Releases
        
    Example:
        # Schnelles Scraping ohne Genres
        releases = scrape_nodata(pages=5, deep_scrape=False)
        
        # Vollständiges Scraping mit Genres (langsamer)
        releases = scrape_nodata(pages=5, deep_scrape=True)
    """
    base_url = "https://nodata.tv/blog/page/{}/"
    all_releases = []
    
    mode = "Deep Scrape" if deep_scrape else "Fast Scrape"
    print(f"\n{'='*50}")
    print(f"🎵 Nodata.tv Scraper - {mode}")
    print(f"   Seiten: {start_page} bis {start_page + pages - 1}")
    if deep_scrape:
        print(f"   Detail-Delay: {DEEP_SCRAPE_DELAY}s pro Release")
    print(f"{'='*50}\n")
    
    for i in range(pages):
        current_page = start_page + i
        
        # Seite 1 hat keine /page/1/ URL
        if current_page == 1:
            url = "https://nodata.tv/blog"
        else:
            url = base_url.format(current_page)
        
        print(f"\n[Seite {current_page}/{start_page + pages - 1}]")
        
        releases_on_page = _scrape_single_page(url, deep_scrape=deep_scrape)
        
        if not releases_on_page:
            print(f"⚠ Keine Releases auf Seite {current_page}. Ende des Archivs?")
            break
        
        all_releases.extend(releases_on_page)
        
        # Kurze Pause zwischen Seiten
        if i < pages - 1:
            time.sleep(0.3)
    
    print(f"\n{'='*50}")
    print(f"✅ Scraping abgeschlossen: {len(all_releases)} Releases gefunden")
    print(f"{'='*50}\n")
    
    return all_releases

def main(history_pages: int = 1, deep_scrape: bool = True, notify: bool = True):
    """
    Hauptfunktion für GitHub Actions / CLI Nutzung.
    
    Args:
        history_pages: Anzahl der zu scrapenden Seiten
        deep_scrape: Wenn True, werden Genres von Detail-Seiten geholt
        notify: Wenn True, wird eine Telegram-Benachrichtigung bei neuen Releases gesendet
    """
    existing_data = get_existing_data()
    existing_ids = {item['id'] for item in existing_data}
    
    print(f"📦 Bestehende Releases: {len(existing_data)}")
    
    scraped = scrape_nodata(pages=history_pages, deep_scrape=deep_scrape)
    
    # Sammle neue Releases
    new_releases = []
    
    # Neue Items vorne einfügen (scraped ist Seite 1..N, also Neueste zuerst)
    # Wir iterieren REVERSE, damit die ältesten Neuen zuerst in die Liste kommen
    # und die allerneuesten ganz oben landen.
    for release in reversed(scraped):
        if release['id'] not in existing_ids:
            existing_data.insert(0, release)
            existing_ids.add(release['id'])
            new_releases.append(release)
            print(f"   🆕 Neu: {release['artist']} - {release['album']}")
    
    new_found_count = len(new_releases)
    
    # Speichere nur wenn es Änderungen gab
    if new_found_count > 0:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=4, ensure_ascii=False)
        print(f"\n💾 {new_found_count} neue Releases in {DATA_FILE} gespeichert.")
        
        # --- TELEGRAM NOTIFICATION ---
        # Nur wenn neue Releases gefunden UND notify aktiviert
        if notify:
            # Sortiere neue Releases (neueste zuerst für die Notification)
            send_telegram_alert(list(reversed(new_releases)), notify_enabled=True)
    else:
        print(f"\n✓ Keine neuen Releases gefunden. {DATA_FILE} unverändert.")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Nodata.tv Release Scraper mit Telegram Notifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  TELEGRAM_TOKEN      Bot Token von @BotFather
  TELEGRAM_CHAT_ID    Chat/Channel ID für Benachrichtigungen
  STREAMLIT_APP_URL   URL zur Streamlit App (optional)

Examples:
  python scraper.py                    # 1 Seite scrapen, mit Notification
  python scraper.py -p 5               # 5 Seiten scrapen
  python scraper.py -p 3 --fast        # Schnell ohne Genres
  python scraper.py --no-notify        # Ohne Telegram-Benachrichtigung
        """
    )
    parser.add_argument(
        "-p", "--pages", 
        type=int, 
        default=1, 
        help="Anzahl der zu scrapenden Seiten (default: 1)"
    )
    parser.add_argument(
        "--fast", 
        action="store_true", 
        help="Schnelles Scraping ohne Genre-Details"
    )
    parser.add_argument(
        "--no-notify", 
        action="store_true", 
        help="Keine Telegram-Benachrichtigung senden"
    )
    
    args = parser.parse_args()
    
    main(
        history_pages=args.pages, 
        deep_scrape=not args.fast,
        notify=not args.no_notify
    )
