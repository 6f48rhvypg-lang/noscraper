import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime
import time # Hinzugefügt, um Server beim Multi-Page Scraping nicht zu überlasten

# Datei zum Speichern der Daten
DATA_FILE = "releases.json"

def get_existing_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

def generate_search_links(artist, title):
    # URL-Encoding für die Suche
    query = requests.utils.quote(f"{artist} {title}")
    
    return {
        "youtube": f"https://www.youtube.com/results?search_query={query}",
        "bandcamp": f"https://bandcamp.com/search?q={query}",
        "soundcloud": f"https://soundcloud.com/search?q={query}",
        "apple": f"https://music.apple.com/de/search?term={query}"
    }

def _scrape_single_page(url):
    """Führt das eigentliche Scraping für eine einzelne URL durch."""
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status() # Löst HTTPError für schlechte Antworten aus
        soup = BeautifulSoup(response.content, 'html.parser')
        
        page_releases = []
        articles = soup.find_all('article', class_='project-box')
        
        for article in articles:
            h6_tag = article.find('h6')
            if not h6_tag:
                continue
            
            full_text = h6_tag.get_text(strip=True)
            
            # Artist und Album trennen
            if "/" in full_text:
                parts = full_text.split("/", 1)
                artist = parts[0].strip()
                raw_album = parts[1].strip()
                album = re.sub(r'\[.*?\]', '', raw_album).strip()
            else:
                artist = full_text
                album = ""

            # Bild finden
            img_tag = article.find('img')
            # Nodata.tv nutzt manchmal relative URLs. Sicherstellen, dass die URL vollständig ist, 
            # falls wir sie später brauchen, aber für den Streamlit-Einsatz reicht die relative
            img_url = img_tag['src'] if img_tag else None

            # Datum finden
            date_tag = article.find('em', class_='date')
            pub_date = date_tag.get_text(strip=True) if date_tag else datetime.now().strftime("%Y-%m-%d")

            links = generate_search_links(artist, album)

            release_data = {
                "id": full_text,
                "artist": artist,
                "album": album,
                "image": img_url,
                "date_found": pub_date,
                "links": links
            }
            page_releases.append(release_data)
            
        return page_releases

    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen der Seite {url}: {e}")
        return []
    except Exception as e:
        print(f"Allgemeiner Fehler beim Parsen der Seite {url}: {e}")
        return []


def scrape_nodata(pages=1, start_page=1):
    """
    Scrapt Seiten von Nodata.tv.
    :param pages: Wie viele Seiten wir abrufen wollen.
    :param start_page: Bei welcher Seite wir anfangen (z.B. Seite 4).
    """
    base_url = "https://nodata.tv/page/{}/"
    all_releases = []
    
    # Wir laufen von start_page bis (start_page + pages)
    for i in range(pages):
        current_page = start_page + i
        url = base_url.format(current_page) if current_page > 1 else "https://nodata.tv/"
        print(f"Live-Scraping Seite {current_page}: {url}")
        
        releases_on_page = _scrape_single_page(url)
        all_releases.extend(releases_on_page)
        
        if i < pages - 1:
            time.sleep(1) 
            
    return all_releases


def main(history_pages=1):
    """
    Führt das Hauptskript aus.
    :param history_pages: Anzahl der zu scrapenden Seiten (für Backfill)
    """
    existing_data = get_existing_data()
    existing_ids = {item['id'] for item in existing_data}
    
    scraped = scrape_nodata(pages=history_pages)
    added_count = 0
    
    # Releases werden eingefügt, aber nur wenn sie noch nicht existieren
    for release in reversed(scraped):
        if release['id'] not in existing_ids:
            existing_data.insert(0, release)
            existing_ids.add(release['id']) # ID zur Set hinzufügen, falls ein Release mehrfach in der Historie auftaucht
            added_count += 1
    
    # Speichern
    with open(DATA_FILE, "w") as f:
        json.dump(existing_data, f, indent=4)
    
    print(f"Fertig! {len(existing_data)} Gesamtreleases in der Datenbank. {added_count} neue Releases zur Datenbank hinzugefügt.")

if __name__ == "__main__":
    # Standardmäßig (für GitHub Actions) nur Seite 1 scrapen
    # Wenn Sie die Historie backfillen möchten, ändern Sie dies lokal: main(history_pages=10)
    main(history_pages=1)
