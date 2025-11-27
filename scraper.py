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
    query = urllib.parse.quote_plus(f"{artist} {title}")
    return {
        "youtube": f"https://www.youtube.com/results?search_query={query}",
        "bandcamp": f"https://bandcamp.com/search?q={query}",
        "soundcloud": f"https://soundcloud.com/search?q={query}",
        "apple": f"https://music.apple.com/de/search?term={query}"
    }

def _parse_date_from_text(text):
    """
    Versucht ein Datum wie 'Nov 23, 2025' aus einem String zu extrahieren.
    """
    # Regex für "Nov 23, 2025" oder "November 23, 2025"
    match = re.search(r'([A-Za-z]+ \d{1,2}, \d{4})', text)
    if match:
        date_str = match.group(1)
        try:
            # Versuche Parsing (Unix/Mac unterstützt oft %B/%b korrekt, aber sicherheitshalber:)
            dt = datetime.strptime(date_str, "%b %d, %Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return datetime.now().strftime("%Y-%m-%d")

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
        
        ignore = ['EP', 'Album', 'Single', 'Remix', 'Various Artists', 'Uncategorized']
        return [g for g in genres if g not in ignore]
    except Exception as e:
        print(f"Warnung: Konnte Genres nicht laden für {url}: {e}")
        return []

def _scrape_single_page(url, fetch_genres=True):
    try:
        print(f"Lade URL: {url}")
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        page_releases = []
        # Im Blog View sind die Items auch in 'article.project-box'
        articles = soup.find_all('article', class_='project-box')
        
        for article in articles:
            # --- TITEL & URL ---
            # Im Blog View ist der Titel in: .visual .hover3 .inside .area .object a.title
            title_tag = article.select_one('.visual .hover3 .inside .area .object a.title')
            
            if not title_tag: 
                # Fallback: Manchmal ist Struktur anders, wir versuchen direktes Kind
                continue
                
            full_text = title_tag.get_text(strip=True)
            detail_url = title_tag['href']

            # Split Artist / Album
            if "/" in full_text:
                parts = full_text.split("/", 1)
                artist = parts[0].strip()
                raw_album = parts[1].strip()
                album = re.sub(r'\[.*?\]', '', raw_album).strip() # Entfernt [2025] im Titel
            else:
                artist = full_text
                album = ""

            # --- BILD ---
            img_tag = article.find('img')
            img_url = img_tag['src'] if img_tag else None
            
            # --- DATUM ---
            # Im Blog View steht das Datum in einem <p> Tag unter dem Titel, oft mit Kommentaren gemischt.
            # Bsp: <p>Nov 23, 2025 · <a href="...">5 comments</a></p>
            meta_p = article.select_one('.visual .hover3 .inside .area .object p:last-of-type')
            pub_date = datetime.now().strftime("%Y-%m-%d")
            
            if meta_p:
                pub_date = _parse_date_from_text(meta_p.get_text())

            links = generate_search_links(artist, album)

            # Genres holen
            genres = []
            if fetch_genres and detail_url:
                time.sleep(0.2) # Respektvoller Delay
                genres = _get_genres_from_detail_page(detail_url)

            release_data = {
                "id": full_text, # Unique ID bleibt der volle String
                "artist": artist,
                "album": album,
                "image": img_url,
                "date_found": pub_date,
                "genres": genres,
                "detail_url": detail_url,
                "links": links
            }
            page_releases.append(release_data)
        
        return page_releases
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []

def scrape_nodata(pages=1, start_page=1):
    # WICHTIG: Wir nutzen jetzt die /blog URL Struktur für Konsistenz
    base_url = "https://nodata.tv/blog/page/{}/"
    all_releases = []
    
    for i in range(pages):
        current_page = start_page + i
        if current_page == 1:
            url = "https://nodata.tv/blog" # Seite 1 ist /blog
        else:
            url = base_url.format(current_page)
            
        print(f"Scraping Page {current_page}...")
        
        releases_on_page = _scrape_single_page(url, fetch_genres=True)
        
        if not releases_on_page:
            print(f"Keine Releases auf Seite {current_page} gefunden. Abbruch.")
            break
            
        all_releases.extend(releases_on_page)
        
    return all_releases

def main(history_pages=1):
    existing_data = get_existing_data()
    existing_ids = {item['id'] for item in existing_data}
    
    print(f"Starte Scraping (History: {history_pages} Seiten)...")
    scraped = scrape_nodata(pages=history_pages)
    new_found_count = 0
    
    # Neue Items vorne einfügen (scraped ist Seite 1..N, also Neueste zuerst)
    # Wir iterieren durch `scraped` REVERSE, damit die ältesten Neuen zuerst in die Liste kommen
    # und die allerneuesten ganz oben landen.
    for release in reversed(scraped):
        if release['id'] not in existing_ids:
            existing_data.insert(0, release)
            existing_ids.add(release['id'])
            new_found_count += 1
    
    with open(DATA_FILE, "w") as f:
        json.dump(existing_data, f, indent=4)
    
    print(f"Fertig. {new_found_count} neue Releases gespeichert.")

if __name__ == "__main__":
    # Wenn man das Skript manuell ausführt, kann man hier die Seitenzahl erhöhen
    # um die History einmalig zu füllen.
    main(history_pages=1)
