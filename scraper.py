import requests
from bs4 import BeautifulSoup
import json
import os
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
        # Apple Music Search Link (kostet nichts, führt direkt zur Suche)
        "apple": f"https://music.apple.com/de/search?term={query}"
    }

def scrape_nodata():
    url = "https://nodata.tv/" # Ggf. spezifische Kategorie-URL nutzen
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.content, 'html.parser')
        
        new_releases = []
        
        # ACHTUNG: Du musst die CSS-Selektoren anpassen, wenn du den Quelltext prüfst.
        # Dies ist ein generisches Beispiel basierend auf typischen WordPress-Strukturen.
        articles = soup.find_all('article') 
        
        for article in articles:
            # Beispielhafte Extraktion - muss an die echte HTML-Struktur angepasst werden
            title_element = article.find('h2') # Oft sind Titel in H2
            if not title_element: continue
            
            full_title = title_element.get_text(strip=True)
            
            # Versuche Artist und Titel zu trennen (oft durch "–" oder "-" getrennt)
            if "–" in full_title:
                parts = full_title.split("–")
                artist = parts[0].strip()
                album = parts[1].strip()
            elif "-" in full_title:
                parts = full_title.split("-")
                artist = parts[0].strip()
                album = parts[1].strip()
            else:
                artist = full_title
                album = "Unknown"

            # Bild finden
            img = article.find('img')
            img_url = img['src'] if img else None

            # Links generieren
            links = generate_search_links(artist, album)

            release_data = {
                "id": full_title, # Eindeutige ID
                "artist": artist,
                "album": album,
                "image": img_url,
                "date_found": datetime.now().strftime("%Y-%m-%d"),
                "links": links
            }
            new_releases.append(release_data)
            
        return new_releases
    except Exception as e:
        print(f"Fehler beim Scrapen: {e}")
        return []

def main():
    existing_data = get_existing_data()
    # Nur die IDs (Titel) laden, um Duplikate zu vermeiden
    existing_ids = {item['id'] for item in existing_data}
    
    scraped = scrape_nodata()
    added_count = 0
    
    for release in scraped:
        if release['id'] not in existing_ids:
            existing_data.insert(0, release) # Neue Releases nach oben
            added_count += 1
    
    # Speichern
    with open(DATA_FILE, "w") as f:
        json.dump(existing_data, f, indent=4)
    
    print(f"Fertig! {added_count} neue Releases gefunden.")

if __name__ == "__main__":
    main()
