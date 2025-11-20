import streamlit as st
import json
import os
import extra_streamlit_components as stx
from datetime import datetime

# --- KONFIGURATION & SETUP ---
st.set_page_config(
    page_title="Nodata Release Radar",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS (DARK MODE & CARD DESIGN) ---
# Hier definieren wir das Aussehen der "Karten". 
# Streamlit erlaubt HTML/CSS Injection, was wir für Hover-Effekte und Grid-Styling nutzen.
st.markdown("""
<style>
    /* Entfernt den Standard-Padding oben, damit es app-artiger wirkt */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
    }
    
    /* Button Styling für "Load More" */
    div.stButton > button {
        width: 100%;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    /* Visueller Indikator für "Gesehen" (wird via Python Logik gesteuert, aber hier gestyled) */
    .seen-badge {
        color: #4CAF50;
        font-weight: bold;
        font-size: 0.8rem;
    }
    
    /* Anpassung der Bilder */
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
# Das ist notwendig, um den "Gesehen"-Status über Sessions hinweg zu speichern.
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

# --- DATEN LADEN ---
@st.cache_data(ttl=3600) # Cache die Daten für 1 Stunde
def load_data():
    if os.path.exists("releases.json"):
        with open("releases.json", "r") as f:
            return json.load(f)
    return []

data = load_data()

# --- SESSION STATE INITIALISIERUNG ---
if 'page_size' not in st.session_state:
    st.session_state.page_size = 12  # Start mit 12 Items (3x4 Grid)

if 'seen_releases' not in st.session_state:
    # Versuche Cookies zu lesen, sonst leere Liste
    cookie_val = cookie_manager.get(cookie="nodata_seen_v1")
    if cookie_val:
        st.session_state.seen_releases = json.loads(cookie_val)
    else:
        st.session_state.seen_releases = []

# Funktion zum Speichern des "Gesehen"-Status
def mark_as_seen(release_id):
    if release_id not in st.session_state.seen_releases:
        st.session_state.seen_releases.append(release_id)
        # Speichere im Cookie (Gültig für 30 Tage)
        cookie_manager.set("nodata_seen_v1", json.dumps(st.session_state.seen_releases), expires_at=datetime.now().timestamp() + 2592000)

# --- HEADER ---
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title("🎵 Nodata.tv Radar")
    st.caption("Serverless Music Discovery")
with col_h2:
    # Suche direkt oben rechts
    search = st.text_input("🔍 Filter...", "", placeholder="Artist oder Album")

# --- LOGIK: FILTERN & PAGINATION ---
if search:
    # Wenn gesucht wird, ignorieren wir Pagination und zeigen alle Matches
    filtered_data = [r for r in data if search.lower() in r['artist'].lower() or search.lower() in r['album'].lower()]
    is_search_mode = True
else:
    filtered_data = data[:st.session_state.page_size]
    is_search_mode = False

# --- UI: GRID GENERATOR ---
if not filtered_data:
    st.info("Keine Releases gefunden oder Daten werden noch geladen.")
else:
    # Wir erstellen ein Grid mit 4 Spalten (responsive)
    # Auf Mobile stapelt Streamlit diese automatisch untereinander.
    cols_per_row = 4
    rows = [filtered_data[i:i + cols_per_row] for i in range(0, len(filtered_data), cols_per_row)]

    for row in rows:
        cols = st.columns(cols_per_row)
        for idx, release in enumerate(row):
            with cols[idx]:
                # CONTAINER START (Visuelle Karte)
                with st.container(border=True):
                    # 1. Status Check (Gesehen?)
                    is_seen = release['id'] in st.session_state.seen_releases
                    
                    # 2. Bild
                    if release['image']:
                        # Wir machen das Bild etwas transparenter, wenn schon gesehen
                        opacity = 0.5 if is_seen else 1.0
                        st.markdown(f'<div style="opacity: {opacity}">', unsafe_allow_html=True)
                        st.image(release['image'], use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.image("https://placehold.co/400x400?text=No+Cover", use_container_width=True)

                    # 3. Titel & Artist
                    # Titel kürzen, falls zu lang für das Grid
                    display_album = (release['album'][:30] + '..') if len(release['album']) > 30 else release['album']
                    
                    if is_seen:
                        st.markdown(f"✅ <small style='color:gray'>Bereits gesehen</small>", unsafe_allow_html=True)
                    
                    st.subheader(release['artist'])
                    st.write(f"**{display_album}**")
                    st.caption(f"📅 {release['date_found']}")

                    # 4. Links & Interaktion
                    # Wir nutzen einen Expander für die Links, um die Karte sauber zu halten
                    with st.expander("🎧 Anhören / Links"):
                        l = release['links']
                        st.link_button("YouTube", l['youtube'], use_container_width=True)
                        st.link_button("SoundCloud", l['soundcloud'], use_container_width=True)
                        st.link_button("Bandcamp", l['bandcamp'], use_container_width=True)
                        st.link_button("Apple Music", l['apple'], use_container_width=True)
                        
                        # "Mark as seen" Button
                        # Da wir nicht wissen, welchen Link der User klickt, 
                        # geben wir einen expliziten Button zum "Abhaken".
                        if not is_seen:
                            if st.button("Als gesehen markieren", key=f"seen_{release['id']}"):
                                mark_as_seen(release['id'])
                                st.rerun()

# --- FOOTER / LOAD MORE ---
if not is_search_mode and len(data) > st.session_state.page_size:
    st.divider()
    col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
    with col_b2:
        if st.button("👇 Mehr Releases laden (+12)"):
            st.session_state.page_size += 12
            st.rerun()
