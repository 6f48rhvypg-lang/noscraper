import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime
import time
import urllib.parse

DATA_FILE = "releases.json"

def get_existing_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

def generate_search_links(artist, title):
    # quote_plus wandelt Leerzeichen in + um, was Mobile Apps oft lieber mögen als %20
    query = urllib.parse.quote_plus(f"{artist} {title}")
    return {
        "youtube": f"https://www.youtube.com/results?search_query={query}",
        "bandcamp": f"https://bandcamp.com/search?q={query}",
        "soundcloud": f"https://soundcloud.com/search?q={query}",
        "apple": f"https://music.apple.com/de/search?term={query}"
    }

def _get_genres_from_detail_page(url):
    """Besucht die Detailseite, um Genres aus ul.meta zu holen"""
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if response.status_code != 200: return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        # Suche nach <ul class="meta"> -> Links mit rel="category tag"
        meta_section = soup.find('ul', class_='meta')
        if not meta_section: return []
        
        genre_tags = meta_section.find_all('a', rel='category tag')
        genres = [tag.get_text(strip=True) for tag in genre_tags]
        
        # Filtere generische Tags raus, falls gewünscht
        ignore = ['EP', 'Album', 'Single', 'Remix', 'Various Artists']
        return [g for g in genres if g not in ignore]
    except Exception as e:
        print(f"Warnung: Konnte Genres nicht laden für {url}: {e}")
        return []

def _scrape_single_page(url, fetch_genres=True):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        page_releases = []
        articles = soup.find_all('article', class_='project-box')
        
        for article in articles:
            h6_tag = article.find('h6')
            if not h6_tag: continue
            
            # Link zur Detailseite holen
            a_tag = h6_tag.find('a')
            detail_url = a_tag['href'] if a_tag else None
            
            full_text = h6_tag.get_text(strip=True)
            if "/" in full_text:
                parts = full_text.split("/", 1)
                artist = parts[0].strip()
                raw_album = parts[1].strip()
                album = re.sub(r'\[.*?\]', '', raw_album).strip()
            else:
                artist = full_text
                album = ""

            img_tag = article.find('img')
            img_url = img_tag['src'] if img_tag else None
            
            date_tag = article.find('em', class_='date')
            pub_date = date_tag.get_text(strip=True) if date_tag else datetime.now().strftime("%Y-%m-%d")

            links = generate_search_links(artist, album)

            # Genres holen (nur wenn wir aktiv scrapen, nicht beim schnellen Check)
            genres = []
            if fetch_genres and detail_url:
                # Kurze Pause um den Server nicht zu hämmern
                time.sleep(0.5) 
                genres = _get_genres_from_detail_page(detail_url)

            release_data = {
                "id": full_text,
                "artist": artist,
                "album": album,
                "image": img_url,
                "date_found": pub_date,
                "genres": genres, # Neu
                "detail_url": detail_url, # Neu: Link zur Nodata Seite
                "links": links
            }
            page_releases.append(release_data)
        return page_releases
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []

def scrape_nodata(pages=1, start_page=1):
    base_url = "https://nodata.tv/page/{}/"
    all_releases = []
    
    for i in range(pages):
        current_page = start_page + i
        url = base_url.format(current_page) if current_page > 1 else "https://nodata.tv/"
        print(f"Scraping Overview Page {current_page}...")
        
        releases_on_page = _scrape_single_page(url, fetch_genres=True)
        all_releases.extend(releases_on_page)
        
    return all_releases

def main(history_pages=1):
    existing_data = get_existing_data()
    existing_ids = {item['id'] for item in existing_data}
    
    print("Starte Scraping...")
    scraped = scrape_nodata(pages=history_pages)
    new_found_count = 0
    
    # Wir fügen nur hinzu, was wir noch nicht kennen
    # WICHTIG: reversed, damit die neuesten oben bleiben beim insert
    for release in reversed(scraped):
        if release['id'] not in existing_ids:
            existing_data.insert(0, release)
            existing_ids.add(release['id'])
            new_found_count += 1
    
    with open(DATA_FILE, "w") as f:
        json.dump(existing_data, f, indent=4)
    
    print(f"Fertig. {new_found_count} neue Releases gespeichert.")

if __name__ == "__main__":
    main(history_pages=1)
