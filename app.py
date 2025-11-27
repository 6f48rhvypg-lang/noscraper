import streamlit as st
import json
import os
import extra_streamlit_components as stx
from datetime import datetime, timedelta
# Wir importieren den Scraper, um bei Bedarf live nachzuladen
from scraper import scrape_nodata

# --- Page Config & CSS ---
st.set_page_config(
    page_title="Nodata Release Radar", 
    page_icon="🎵", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# CSS Hacks:
# 1. [data-testid="column"]: Macht die Spalten responsive (min. 200px breit, sonst Umbruch)
# 2. .stImage: Hover-Effekt für Cover
st.markdown("""
<style>
    .block-container {padding-top: 2rem; padding-bottom: 5rem;}
    
    [data-testid="column"] {
        min-width: 220px !important;
        flex: 1 1 220px !important; 
    }
    
    div.stButton > button {width: 100%; border-radius: 8px;}
    
    .stImage img {border-radius: 4px; transition: transform 0.3s ease;}
    .stImage img:hover {transform: scale(1.02);}
    
    /* Genre Tags Style */
    .genre-tag {
        background: rgba(255,255,255,0.1); 
        padding: 2px 8px; 
        border-radius: 10px; 
        font-size: 0.7em; 
        margin-right: 4px; 
        display: inline-block; 
        margin-bottom: 4px;
        color: #ddd;
    }
</style>
""", unsafe_allow_html=True)

# --- Cookie Manager ---
def get_manager(): return stx.CookieManager()
cookie_manager = get_manager()

# --- Data Loading ---
@st.cache_data(ttl=3600)
def load_initial_data():
    if os.path.exists("releases.json"):
        with open("releases.json", "r") as f: return json.load(f)
    return []

# --- Session State Init ---
if 'seen_releases' not in st.session_state:
    cookie_val = cookie_manager.get(cookie="nodata_seen_v1")
    st.session_state.seen_releases = json.loads(cookie_val) if cookie_val else []

if 'all_releases' not in st.session_state:
    initial_data = load_initial_data()
    st.session_state.all_releases = initial_data
    # Startpunkt für Live-Scraping, falls lokale Daten zu Ende sind
    st.session_state.current_scrape_page = max(1, len(initial_data) // 10)

if 'page_size' not in st.session_state: 
    st.session_state.page_size = 12

# --- Logic ---
def mark_as_seen(release_id):
    if release_id not in st.session_state.seen_releases:
        st.session_state.seen_releases.append(release_id)
        # Cookie update (1 Jahr gültig)
        expire_date = datetime.now() + timedelta(days=365)
        cookie_manager.set("nodata_seen_v1", json.dumps(st.session_state.seen_releases), expires_at=expire_date)

# --- Header & Search ---
col_h1, col_h2 = st.columns([3, 1])
with col_h1: st.title("🎵 Nodata.tv Radar")
with col_h2: search = st.text_input("🔍 Filter...", "")

# Filtering
if search:
    filtered_data = [r for r in st.session_state.all_releases if search.lower() in r['artist'].lower() or search.lower() in r['album'].lower()]
    is_search_mode = True
else:
    filtered_data = st.session_state.all_releases[:st.session_state.page_size]
    is_search_mode = False

# --- Main Grid ---
if not filtered_data:
    st.info("Keine Releases gefunden.")
else:
    # Responsive Grid Loop
    cols = st.columns(4) # Definiert 4 Spalten (die durch CSS auf Mobile umbrechen)
    
    for idx, release in enumerate(filtered_data):
        col_index = idx % 4
        
        with cols[col_index]:
            with st.container(border=True):
                is_seen = release['id'] in st.session_state.seen_releases
                opacity = 0.4 if is_seen else 1.0
                
                # 1. Status Badge
                if is_seen: 
                    st.caption("✅ Gesehen")
                
                # 2. Cover Image
                if release['image']:
                    st.markdown(f'<div style="opacity: {opacity}">', unsafe_allow_html=True)
                    st.image(release['image'], use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.image("https://placehold.co/400x400?text=No+Cover", use_container_width=True)
                
                # 3. Info Text
                st.markdown(f"**{release['artist']}**")
                st.markdown(f"<span style='color:#bbb; font-size:0.9em'>{release['album']}</span>", unsafe_allow_html=True)
                
                # 4. Genres (Neu)
                if release.get('genres'):
                    tags_html = "".join([f"<span class='genre-tag'>{g}</span>" for g in release['genres'][:4]])
                    st.markdown(f"<div style='margin-top:6px; line-height:1.2;'>{tags_html}</div>", unsafe_allow_html=True)
                
                st.markdown("---")
                
                # 5. Actions
                c_play, c_check = st.columns([1, 1])
                
                with c_play:
                    st.link_button("▶ Play", release['links']['youtube'], use_container_width=True)
                
                with c_check:
                    # Toggle Button
                    btn_label = "Undo" if is_seen else "Check"
                    # Key muss unique sein pro Button!
                    if st.button(btn_label, key=f"seen_btn_{release['id']}", type="secondary" if is_seen else "primary", use_container_width=True):
                        if is_seen:
                            st.session_state.seen_releases.remove(release['id'])
                            # Cookie update beim Entfernen (optional, hier einfachheitshalber Re-Save)
                            expire_date = datetime.now() + timedelta(days=365)
                            cookie_manager.set("nodata_seen_v1", json.dumps(st.session_state.seen_releases), expires_at=expire_date)
                        else:
                            mark_as_seen(release['id'])
                        st.rerun()
                
                # 6. More Links Popover
                with st.popover("Mehr Links", use_container_width=True):
                    st.markdown(f"**Suche auf:**")
                    st.markdown(f"• [Bandcamp]({release['links']['bandcamp']})")
                    st.markdown(f"• [Soundcloud]({release['links']['soundcloud']})")
                    st.markdown(f"• [Apple Music]({release['links']['apple']})")
                    if release.get('detail_url'):
                        st.divider()
                        st.markdown(f"🔗 [Original Post auf Nodata]({release.get('detail_url')})")

# --- Footer / Load More Logic ---
if not is_search_mode:
    st.divider()
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        has_more_local = len(st.session_state.all_releases) > st.session_state.page_size
        
        if st.button("👇 Mehr Releases laden", use_container_width=True):
            if has_more_local:
                st.session_state.page_size += 12
                st.rerun()
            else:
                # --- DEEP SEARCH LOOP ---
                max_attempts = 20
                with st.status("Durchsuche Nodata-Archiv...", expanded=True) as status:
                    found_count = 0
                    attempts = 0
                    p_bar = status.progress(0)
                    
                    while found_count < 8 and attempts < max_attempts:
                        attempts += 1
                        page_to_scrape = st.session_state.current_scrape_page + 1
                        
                        status.write(f"Scanne Seite {page_to_scrape}...")
                        p_bar.progress(min(attempts * 5, 100))
                        
                        try:
                            # Live Scraping der nächsten Seite
                            items = scrape_nodata(pages=1, start_page=page_to_scrape)
                            
                            if not items: 
                                status.write("Ende des Archivs erreicht.")
                                break
                            
                            # Filter: Nur IDs, die wir noch nicht im aktuellen State haben
                            current_ids = {x['id'] for x in st.session_state.all_releases}
                            new_items = [x for x in items if x['id'] not in current_ids]
                            
                            if new_items:
                                st.session_state.all_releases.extend(new_items)
                                found_count += len(new_items)
                                status.write(f"✅ {len(new_items)} neue Releases gefunden!")
                            
                            # Zähler hochsetzen für nächsten Loop
                            st.session_state.current_scrape_page += 1
                            
                        except Exception as e:
                            status.error(f"Fehler beim Scraping: {e}")
                            break
                    
                    if found_count > 0:
                        st.session_state.page_size += found_count
                        status.update(label=f"{found_count} geladen!", state="complete")
                        st.rerun()
                    else:
                        status.update(label="Keine neuen Releases im Archiv gefunden.", state="error")
