import requests
from bs4 import BeautifulSoup
import jsona
import os
import re
from datetime import datetime

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

# Kleines Snippet für scraper.py Erweiterung
def scrape_nodata(pages=1):
    base_url = "https://nodata.tv/page/{}/"
    all_releases = []
    
    for page in range(1, pages + 1):
        url = base_url.format(page) if page > 1 else "https://nodata.tv/"
        # ... hier dein existierender Scraping Code ...
        # ... appende Ergebnisse an all_releases ...
    
    return all_releases
    
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.content, 'html.parser')
        
        new_releases = []
        
        # HIER IST DIE NEUE LOGIK BASIEREND AUF DEINEM QUELLTEXT:
        # Wir suchen nach <article class="project-box">
        articles = soup.find_all('article', class_='project-box')
        
        print(f"{len(articles)} Releases gefunden.")

        for article in articles:
            # 1. Titel finden (h6 -> a)
            h6_tag = article.find('h6')
            if not h6_tag:
                continue
            
            full_text = h6_tag.get_text(strip=True) # z.B. "Orca / Dancing With Dolphins Vol. 2 [2025]"
            
            # 2. Artist und Album trennen
            # Wir splitten am ersten "/"
            if "/" in full_text:
                parts = full_text.split("/", 1)
                artist = parts[0].strip()
                raw_album = parts[1].strip()
                
                # Entferne das Jahr in Klammern z.B. "[2025]", damit die Musiksuche besser klappt
                album = re.sub(r'\[.*?\]', '', raw_album).strip()
            else:
                artist = full_text
                album = ""

            # 3. Bild finden
            img_tag = article.find('img')
            img_url = img_tag['src'] if img_tag else None

            # 4. Datum finden (optional, steht im <em class="date">)
            date_tag = article.find('em', class_='date')
            pub_date = date_tag.get_text(strip=True) if date_tag else datetime.now().strftime("%Y-%m-%d")

            # Links generieren
            links = generate_search_links(artist, album)

            release_data = {
                "id": full_text, # Originaltitel als ID nutzen
                "artist": artist,
                "album": album,
                "image": img_url,
                "date_found": pub_date,
                "links": links
            }
            new_releases.append(release_data)
            
        return new_releases

    except Exception as e:
        print(f"Fehler beim Scrapen: {e}")
        return []

def main():
    existing_data = get_existing_data()
    existing_ids = {item['id'] for item in existing_data}
    
    scraped = scrape_nodata()
    added_count = 0
    
    # Umgekehrte Reihenfolge beim Einfügen, damit neueste oben bleiben
    for release in reversed(scraped):
        if release['id'] not in existing_ids:
            existing_data.insert(0, release)
            added_count += 1
    
    # Speichern
    with open(DATA_FILE, "w") as f:
        json.dump(existing_data, f, indent=4)
    
    print(f"Fertig! {added_count} neue Releases zur Datenbank hinzugefügt.")

if __name__ == "__main__":
    main()
