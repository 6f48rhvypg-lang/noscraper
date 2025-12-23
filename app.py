import streamlit as st
import json
import os
import urllib.parse
import extra_streamlit_components as stx
from datetime import datetime, timedelta
# Wir importieren den Scraper, um bei Bedarf live nachzuladen
from scraper import scrape_nodata

# --- Page Config ---
st.set_page_config(
    page_title="Nodata Release Radar", 
    page_icon="🎵", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- Premium Mobile-First CSS ---
st.markdown("""
<style>
    /* ===== BASE LAYOUT ===== */
    .block-container {
        padding: 1rem 1rem 6rem 1rem;
        max-width: 1400px;
    }
    
    /* ===== RESPONSIVE GRID ===== */
    /* CSS Grid für Release Cards - Mobile First */
    .release-grid {
        display: grid;
        grid-template-columns: 1fr;  /* Mobile: 1 card per row */
        gap: 1rem;
        padding: 0.5rem 0;
    }
    
    @media (min-width: 640px) {
        .release-grid {
            grid-template-columns: repeat(2, 1fr);  /* Tablet: 2 cards */
        }
    }
    
    @media (min-width: 1024px) {
        .release-grid {
            grid-template-columns: repeat(3, 1fr);  /* Desktop: 3 cards */
        }
    }
    
    @media (min-width: 1280px) {
        .release-grid {
            grid-template-columns: repeat(4, 1fr);  /* Large Desktop: 4 cards */
        }
    }
    
    /* ===== RELEASE CARD ===== */
    .release-card {
        background: linear-gradient(145deg, rgba(30,30,35,0.9) 0%, rgba(20,20,25,0.95) 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        overflow: hidden;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
    }
    
    .release-card:hover {
        transform: translateY(-4px);
        border-color: rgba(255,255,255,0.15);
        box-shadow: 0 12px 40px rgba(0,0,0,0.4);
    }
    
    .release-card.seen {
        opacity: 0.4;
    }
    
    .release-card.seen:hover {
        opacity: 0.7;
    }
    
    /* ===== COVER IMAGE ===== */
    .card-cover {
        position: relative;
        aspect-ratio: 1;
        overflow: hidden;
    }
    
    .card-cover img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform 0.4s ease;
    }
    
    .release-card:hover .card-cover img {
        transform: scale(1.05);
    }
    
    /* Seen Badge Overlay */
    .seen-badge {
        position: absolute;
        top: 8px;
        right: 8px;
        background: rgba(0,0,0,0.75);
        backdrop-filter: blur(8px);
        color: #4ade80;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    
    /* ===== CARD CONTENT ===== */
    .card-content {
        padding: 12px 14px 14px;
    }
    
    .artist-name {
        font-size: 1rem;
        font-weight: 700;
        color: #fff;
        margin: 0 0 2px 0;
        line-height: 1.3;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    
    .album-name {
        font-size: 0.85rem;
        color: rgba(255,255,255,0.6);
        margin: 0 0 8px 0;
        line-height: 1.3;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    
    /* ===== GENRE PILLS ===== */
    .genre-pills {
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
        margin-bottom: 12px;
    }
    
    .genre-pill {
        background: rgba(255,255,255,0.08);
        color: rgba(255,255,255,0.7);
        padding: 3px 10px;
        border-radius: 100px;
        font-size: 0.65rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        border: 1px solid rgba(255,255,255,0.06);
        transition: all 0.2s ease;
    }
    
    .genre-pill:hover {
        background: rgba(255,255,255,0.12);
        color: rgba(255,255,255,0.9);
    }
    
    /* ===== ACTION BUTTONS ===== */
    .card-actions {
        display: flex;
        gap: 8px;
        align-items: center;
    }
    
    .action-btn {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 10px 12px;
        border-radius: 8px;
        font-size: 0.8rem;
        font-weight: 600;
        text-decoration: none;
        transition: all 0.2s ease;
        cursor: pointer;
        border: none;
    }
    
    .btn-play {
        background: linear-gradient(135deg, #ff4757 0%, #ff3344 100%);
        color: white;
    }
    
    .btn-play:hover {
        background: linear-gradient(135deg, #ff5a67 0%, #ff4455 100%);
        transform: scale(1.02);
    }
    
    .btn-links {
        background: rgba(255,255,255,0.08);
        color: rgba(255,255,255,0.85);
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .btn-links:hover {
        background: rgba(255,255,255,0.12);
        color: white;
    }
    
    /* Check/Uncheck Icon Button */
    .btn-check {
        width: 40px;
        height: 40px;
        min-width: 40px;
        flex: 0 0 40px;
        padding: 0;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.1);
        color: rgba(255,255,255,0.7);
        transition: all 0.2s ease;
    }
    
    .btn-check:hover {
        background: rgba(74, 222, 128, 0.15);
        border-color: rgba(74, 222, 128, 0.3);
        color: #4ade80;
    }
    
    .btn-check.checked {
        background: rgba(74, 222, 128, 0.15);
        border-color: rgba(74, 222, 128, 0.25);
        color: #4ade80;
    }
    
    .btn-check.checked:hover {
        background: rgba(239, 68, 68, 0.15);
        border-color: rgba(239, 68, 68, 0.3);
        color: #ef4444;
    }
    
    /* ===== LINKS DROPDOWN ===== */
    .links-menu {
        background: rgba(25,25,30,0.98);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 8px;
        min-width: 200px;
    }
    
    .link-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 12px;
        border-radius: 8px;
        color: rgba(255,255,255,0.85);
        text-decoration: none;
        font-size: 0.85rem;
        transition: all 0.15s ease;
    }
    
    .link-item:hover {
        background: rgba(255,255,255,0.08);
        color: white;
    }
    
    .link-item .icon {
        font-size: 1.1rem;
        width: 24px;
        text-align: center;
    }
    
    .link-divider {
        height: 1px;
        background: rgba(255,255,255,0.08);
        margin: 6px 0;
    }
    
    /* ===== HEADER ===== */
    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem 0 1.5rem;
        flex-wrap: wrap;
        gap: 1rem;
    }
    
    .app-title {
        font-size: 1.75rem;
        font-weight: 800;
        background: linear-gradient(135deg, #fff 0%, #aaa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
    }
    
    /* ===== STREAMLIT OVERRIDES ===== */
    /* Hide default streamlit elements we don't need */
    div[data-testid="stVerticalBlock"] > div:has(> .release-grid) {
        gap: 0 !important;
    }
    
    /* Better button styling */
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    /* Search input */
    div[data-testid="stTextInput"] input {
        border-radius: 10px;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Popover styling */
    div[data-testid="stPopover"] > div {
        background: rgba(20,20,25,0.98) !important;
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px !important;
    }
    
    /* Load more button */
    .load-more-btn {
        background: linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.04) 100%);
        border: 1px solid rgba(255,255,255,0.1);
        color: rgba(255,255,255,0.8);
        padding: 14px 28px;
        border-radius: 12px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .load-more-btn:hover {
        background: rgba(255,255,255,0.1);
        border-color: rgba(255,255,255,0.2);
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- Cookie Manager ---
# Note: CookieManager can't be cached due to internal widget usage
cookie_manager = stx.CookieManager(key="nodata_cookie_manager")

# --- Data Loading ---
@st.cache_data(ttl=3600)
def load_initial_data():
    if os.path.exists("releases.json"):
        with open("releases.json", "r") as f: return json.load(f)
    return []

# --- Cookie Constants ---
COOKIE_NAME = "nodata_seen_v1"
COOKIE_EXPIRY_DAYS = 365

# --- Session State Init (with cookie sync) ---
# Flag to track if we've attempted to load cookies
if 'cookie_loaded' not in st.session_state:
    st.session_state.cookie_loaded = False
    st.session_state.seen_releases = []

# Attempt to sync cookie value on each run until successful
# This handles the async nature of extra-streamlit-components
if not st.session_state.cookie_loaded:
    cookie_val = cookie_manager.get(cookie=COOKIE_NAME)
    if cookie_val is not None:
        try:
            st.session_state.seen_releases = json.loads(cookie_val)
        except (json.JSONDecodeError, TypeError):
            st.session_state.seen_releases = []
        st.session_state.cookie_loaded = True

if 'all_releases' not in st.session_state:
    initial_data = load_initial_data()
    st.session_state.all_releases = initial_data
    # Startpunkt für Live-Scraping: Berechnung basierend auf Items pro Seite (~7-10)
    st.session_state.current_scrape_page = max(1, len(initial_data) // 8)

if 'page_size' not in st.session_state: 
    st.session_state.page_size = 12

# --- Helper Functions ---
def _save_seen_cookie():
    """Speichert den aktuellen seen_releases State im Cookie."""
    expire_date = datetime.now() + timedelta(days=COOKIE_EXPIRY_DAYS)
    cookie_manager.set(COOKIE_NAME, json.dumps(st.session_state.seen_releases), expires_at=expire_date)

def mark_as_seen(release_id):
    """Markiert ein Release als gesehen und speichert im Cookie."""
    if release_id not in st.session_state.seen_releases:
        st.session_state.seen_releases.append(release_id)
        _save_seen_cookie()

def unmark_as_seen(release_id):
    """Entfernt die Gesehen-Markierung und aktualisiert das Cookie."""
    if release_id in st.session_state.seen_releases:
        st.session_state.seen_releases.remove(release_id)
        _save_seen_cookie()

def get_soundcloud_links(artist: str, album: str) -> dict:
    """
    Generiert SoundCloud Links die auf Mobile funktionieren.
    
    Returns:
        Dict mit 'web' (Browser-Link) und 'app' (Intent-URL für Android)
    """
    query = f"{artist} {album}".strip()
    encoded_query = urllib.parse.quote_plus(query)
    
    # Web-basierte Suche (funktioniert überall, öffnet App wenn installiert)
    web_url = f"https://soundcloud.com/search?q={encoded_query}"
    
    # Alternative: m.soundcloud.com für bessere Mobile-Erkennung
    mobile_url = f"https://m.soundcloud.com/search?q={encoded_query}"
    
    return {"web": web_url, "mobile": mobile_url}

def render_release_card(release: dict, is_seen: bool, card_idx: int) -> str:
    """
    Rendert eine Release Card als HTML.
    
    Args:
        release: Release dictionary
        is_seen: Ob das Release als gesehen markiert ist
        card_idx: Eindeutiger Index für Keys
        
    Returns:
        HTML string für die Card
    """
    artist = release.get('artist', 'Unknown')
    album = release.get('album', '')
    image = release.get('image', 'https://placehold.co/400x400/1a1a1f/333?text=No+Cover')
    genres = release.get('genres', [])[:4]  # Max 4 Genres
    youtube_link = release.get('links', {}).get('youtube', '#')
    
    # Card CSS Klasse
    card_class = "release-card seen" if is_seen else "release-card"
    
    # Seen Badge
    seen_badge = '<div class="seen-badge">✓ Gesehen</div>' if is_seen else ''
    
    # Genre Pills HTML
    genre_pills = ""
    if genres:
        pills = "".join([f'<span class="genre-pill">{g}</span>' for g in genres])
        genre_pills = f'<div class="genre-pills">{pills}</div>'
    
    # Build card HTML
    html = f'''
    <div class="{card_class}">
        <div class="card-cover">
            <img src="{image}" alt="{artist}" loading="lazy" onerror="this.src='https://placehold.co/400x400/1a1a1f/333?text=No+Cover'">
            {seen_badge}
        </div>
        <div class="card-content">
            <p class="artist-name">{artist}</p>
            <p class="album-name">{album or '—'}</p>
            {genre_pills}
        </div>
    </div>
    '''
    return html

# --- Header & Search ---
st.markdown("""
<div class="app-header">
    <h1 class="app-title">🎵 Nodata Radar</h1>
</div>
""", unsafe_allow_html=True)

# Search Input
search = st.text_input("🔍 Suche nach Artist oder Album...", "", label_visibility="collapsed", placeholder="🔍 Suche nach Artist oder Album...")

# Filtering
if search:
    search_lower = search.lower()
    filtered_data = [
        r for r in st.session_state.all_releases 
        if search_lower in r.get('artist', '').lower() 
        or search_lower in r.get('album', '').lower()
        or any(search_lower in g.lower() for g in r.get('genres', []))
    ]
    is_search_mode = True
else:
    filtered_data = st.session_state.all_releases[:st.session_state.page_size]
    is_search_mode = False

# Stats
total_count = len(st.session_state.all_releases)
seen_count = len(st.session_state.seen_releases)
st.caption(f"📀 {total_count} Releases • ✅ {seen_count} gesehen")

# --- Main Grid ---
if not filtered_data:
    st.info("🔍 Keine Releases gefunden. Versuche einen anderen Suchbegriff.")
else:
    # Responsive grid using CSS columns
    cols = st.columns(4)
    
    for idx, release in enumerate(filtered_data):
        col_index = idx % 4
        is_seen = release['id'] in st.session_state.seen_releases
        
        with cols[col_index]:
            # Card Container mit Opacity-Handling
            card_opacity = "0.4" if is_seen else "1"
            
            with st.container(border=True):
                # --- SEEN BADGE ---
                if is_seen:
                    st.markdown(
                        '<div style="background:rgba(74,222,128,0.15); color:#4ade80; padding:4px 10px; '
                        'border-radius:20px; font-size:0.7rem; font-weight:600; display:inline-block; '
                        'margin-bottom:8px;">✓ Gesehen</div>',
                        unsafe_allow_html=True
                    )
                
                # --- COVER IMAGE ---
                image_url = release.get('image') or 'https://placehold.co/400x400/1a1a1f/444?text=No+Cover'
                st.markdown(f'<div style="opacity:{card_opacity}; transition:opacity 0.3s;">', unsafe_allow_html=True)
                st.image(image_url, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # --- ARTIST & ALBUM ---
                artist = release.get('artist', 'Unknown')
                album = release.get('album', '')
                
                st.markdown(f"**{artist}**")
                if album:
                    st.markdown(f'<span style="color:rgba(255,255,255,0.6); font-size:0.9em;">{album}</span>', unsafe_allow_html=True)
                
                # --- GENRE PILLS ---
                genres = release.get('genres', [])[:4]
                if genres:
                    pills_html = "".join([
                        f'<span style="background:rgba(255,255,255,0.08); color:rgba(255,255,255,0.7); '
                        f'padding:3px 10px; border-radius:100px; font-size:0.65rem; font-weight:500; '
                        f'text-transform:uppercase; letter-spacing:0.04em; margin-right:5px; '
                        f'display:inline-block; margin-bottom:5px;">{g}</span>'
                        for g in genres
                    ])
                    st.markdown(f'<div style="margin-top:8px;">{pills_html}</div>', unsafe_allow_html=True)
                
                # --- ACTION BUTTONS ---
                col_play, col_links, col_check = st.columns([2, 2, 1])
                
                with col_play:
                    youtube_url = release.get('links', {}).get('youtube', '#')
                    st.link_button("▶️ Play", youtube_url, use_container_width=True)
                
                with col_links:
                    # Links Popover mit SoundCloud Fix
                    with st.popover("🔗", use_container_width=True):
                        st.markdown("**Suche auf:**")
                        
                        # Bandcamp
                        bandcamp_url = release.get('links', {}).get('bandcamp', '#')
                        st.markdown(f"🎸 [Bandcamp]({bandcamp_url})")
                        
                        # SoundCloud - Mobile-optimized links
                        sc_links = get_soundcloud_links(artist, album)
                        st.markdown(f"☁️ [SoundCloud]({sc_links['mobile']})")
                        
                        # Apple Music
                        apple_url = release.get('links', {}).get('apple', '#')
                        st.markdown(f"🍎 [Apple Music]({apple_url})")
                        
                        # Original Link
                        if release.get('detail_url'):
                            st.divider()
                            st.markdown(f"🌐 [Nodata Original]({release['detail_url']})")
                
                with col_check:
                    # Low-profile icon button für Mark as Seen
                    btn_icon = "✓" if is_seen else "○"
                    btn_type = "secondary" if is_seen else "primary"
                    btn_help = "Als ungesehen markieren" if is_seen else "Als gesehen markieren"
                    
                    if st.button(btn_icon, key=f"seen_{idx}_{release['id'][:20]}", type=btn_type, help=btn_help, use_container_width=True):
                        if is_seen:
                            unmark_as_seen(release['id'])
                        else:
                            mark_as_seen(release['id'])
                        st.rerun()

# --- Footer / Load More Logic ---
if not is_search_mode:
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Centered Load More Section
    _, col_center, _ = st.columns([1, 2, 1])
    
    with col_center:
        has_more_local = len(st.session_state.all_releases) > st.session_state.page_size
        remaining = len(st.session_state.all_releases) - st.session_state.page_size
        
        # Show count of remaining if any
        if has_more_local:
            btn_text = f"👇 Mehr laden ({remaining} weitere)"
        else:
            btn_text = "🔍 Im Archiv suchen..."
        
        if st.button(btn_text, use_container_width=True, type="secondary"):
            if has_more_local:
                st.session_state.page_size += 12
                st.rerun()
            else:
                # --- DEEP SEARCH LOOP ---
                max_attempts = 20
                with st.status("🔍 Durchsuche Nodata-Archiv...", expanded=True) as status:
                    found_count = 0
                    attempts = 0
                    p_bar = status.progress(0)
                    
                    while found_count < 8 and attempts < max_attempts:
                        attempts += 1
                        page_to_scrape = st.session_state.current_scrape_page + 1
                        
                        status.write(f"📄 Scanne Seite {page_to_scrape}...")
                        p_bar.progress(min(attempts * 5, 100))
                        
                        try:
                            # Live Scraping der nächsten Seite (mit Deep Scrape für Genres)
                            items = scrape_nodata(pages=1, start_page=page_to_scrape, deep_scrape=True)
                            
                            if not items: 
                                status.write("📭 Ende des Archivs erreicht.")
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
                            status.error(f"⚠️ Fehler: {e}")
                            break
                    
                    if found_count > 0:
                        st.session_state.page_size += found_count
                        status.update(label=f"🎉 {found_count} neue Releases geladen!", state="complete")
                        st.rerun()
                    else:
                        status.update(label="😔 Keine neuen Releases im Archiv gefunden.", state="error")
    
    # Footer Info
    st.markdown("""
    <div style="text-align:center; padding:2rem 0 1rem; color:rgba(255,255,255,0.3); font-size:0.75rem;">
        Powered by <a href="https://nodata.tv" style="color:rgba(255,255,255,0.5);">Nodata.tv</a> • 
        Built with Streamlit
    </div>
    """, unsafe_allow_html=True)
