import streamlit as st
import json
import os
import extra_streamlit_components as stx
from datetime import datetime, timedelta
from scraper import scrape_nodata  # Importiert die Scraper-Logik

# --- KONFIGURATION & SETUP ---
st.set_page_config(
    page_title="Nodata Release Radar",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS (DARK MODE & CARD DESIGN) ---
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
    }
    div.stButton > button {
        width: 100%;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .stImage img {
        border-radius: 8px;
        transition: transform 0.3s ease;
    }
    .stImage img:hover {
        transform: scale(1.02);
    }
</style>
""", unsafe_allow_html=True)

# --- COOKIE MANAGER SETUP ---
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

# --- DATEN LADEN ---
@st.cache_data(ttl=3600)
def load_initial_data():
    """Lädt die JSON-Datei vom Server (GitHub Stand)"""
    if os.path.exists("releases.json"):
        with open("releases.json", "r") as f:
            return json.load(f)
    return []

# --- STATE INITIALISIERUNG ---

# 1. "Gesehen"-Status laden
if 'seen_releases' not in st.session_state:
    cookie_val = cookie_manager.get(cookie="nodata_seen_v1")
    if cookie_val:
        try:
            st.session_state.seen_releases = json.loads(cookie_val)
        except:
            st.session_state.seen_releases = []
    else:
        st.session_state.seen_releases = []

# 2. Release-Daten initialisieren
# Wir kopieren die Daten in den Session State, damit wir später neue (gescrapte) Daten anhängen können
if 'all_releases' not in st.session_state:
    initial_data = load_initial_data()
    st.session_state.all_releases = initial_data
    
    # Wir schätzen ab, bei welcher "Seite" wir uns befinden (ca. 10 Items pro Seite)
    # Das hilft dem Scraper zu wissen, wo er weitermachen soll
    st.session_state.current_scrape_page = max(1, len(initial_data) // 10)

# 3. Pagination Status
if 'page_size' not in st.session_state:
    st.session_state.page_size = 12

# --- HELPER FUNKTIONEN ---

def mark_as_seen(release_id):
    """Markiert ein Album als gesehen und speichert es im Cookie für 1 Jahr"""
    if release_id not in st.session_state.seen_releases:
        st.session_state.seen_releases.append(release_id)
        
        # FIX: Verwende ein datetime Objekt statt Timestamp
        expire_date = datetime.now() + timedelta(days=365)
        
        cookie_manager.set(
            "nodata_seen_v1", 
            json.dumps(st.session_state.seen_releases), 
            expires_at=expire_date
        )

# --- HEADER ---
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title("🎵 Nodata.tv Radar")
    st.caption("Serverless Music Discovery")
with col_h2:
    search = st.text_input("🔍 Filter...", "", placeholder="Artist oder Album")

# --- LOGIK: FILTERN ---
if search:
    # Bei Suche zeigen wir alles, was passt (aus den bereits geladenen Daten)
    filtered_data = [
        r for r in st.session_state.all_releases 
        if search.lower() in r['artist'].lower() or search.lower() in r['album'].lower()
    ]
    is_search_mode = True
else:
    # Normale Ansicht: Nur die ersten 'page_size' Elemente zeigen
    filtered_data = st.session_state.all_releases[:st.session_state.page_size]
    is_search_mode = False

# --- UI: GRID RENDERER ---
if not filtered_data:
    st.info("Keine Releases gefunden.")
else:
    cols_per_row = 4
    rows = [filtered_data[i:i + cols_per_row] for i in range(0, len(filtered_data), cols_per_row)]

    for row in rows:
        cols = st.columns(cols_per_row)
        for idx, release in enumerate(row):
            with cols[idx]:
                with st.container(border=True):
                    # Status Check
                    is_seen = release['id'] in st.session_state.seen_releases
                    
                    # Bild (ausgegraut wenn gesehen)
                    if release['image']:
                        opacity = 0.5 if is_seen else 1.0
                        st.markdown(f'<div style="opacity: {opacity}">', unsafe_allow_html=True)
                        st.image(release['image'], use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.image("https://placehold.co/400x400?text=No+Cover", use_container_width=True)

                    # Titel & Text
                    display_album = (release['album'][:30] + '..') if len(release['album']) > 30 else release['album']
                    
                    if is_seen:
                        st.markdown("✅ <small style='color:gray'>Gesehen</small>", unsafe_allow_html=True)
                    
                    st.subheader(release['artist'])
                    st.write(f"**{display_album}**")
                    st.caption(f"📅 {release['date_found']}")

                    # Links & Aktionen
                    with st.expander("🎧 Anhören / Links"):
                        l = release['links']
                        st.link_button("YouTube", l['youtube'], use_container_width=True)
                        st.link_button("SoundCloud", l['soundcloud'], use_container_width=True)
                        st.link_button("Bandcamp", l['bandcamp'], use_container_width=True)
                        st.link_button("Apple Music", l['apple'], use_container_width=True)
                        
                        if not is_seen:
                            if st.button("Als gesehen markieren", key=f"seen_{release['id']}"):
                                mark_as_seen(release['id'])
                                st.rerun()

# --- FOOTER / LOAD MORE LOGIC ---
if not is_search_mode:
    st.divider()
    col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
    with col_b2:
        # Checken: Haben wir lokal noch Daten, die wir nur noch nicht anzeigen?
        has_more_local_data = len(st.session_state.all_releases) > st.session_state.page_size
        
        if st.button("👇 Mehr Releases laden"):
            if has_more_local_data:
                # Fall A: Wir haben die Daten schon, zeigen nur mehr an
                st.session_state.page_size += 12
                st.rerun()
            else:
                # Fall B: Wir müssen neu scrapen
                with st.spinner("Lade ältere Releases direkt von Nodata.tv..."):
                    try:
                        # Nächste Seite berechnen
                        next_page = st.session_state.current_scrape_page + 1
                        
                        # Live Scraping starten (1 Seite)
                        new_items = scrape_nodata(pages=1, start_page=next_page)
                        
                        if new_items:
                            # Duplikate vermeiden
                            existing_ids = {item['id'] for item in st.session_state.all_releases}
                            added_count = 0
                            for item in new_items:
                                if item['id'] not in existing_ids:
                                    st.session_state.all_releases.append(item)
                                    added_count += 1
                            
                            # Status aktualisieren
                            st.session_state.current_scrape_page += 1
                            st.session_state.page_size += 12
                            
                            if added_count == 0:
                                st.warning("Es wurden Daten geladen, aber diese waren schon vorhanden.")
                            else:
                                st.success(f"{added_count} ältere Releases geladen!")
                                st.rerun()
                        else:
                            st.warning("Keine weiteren Releases auf Nodata.tv gefunden.")
                    except Exception as e:
                        st.error(f"Fehler beim Live-Scraping: {e}")
