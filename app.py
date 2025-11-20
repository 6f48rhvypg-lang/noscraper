import streamlit as st
import json
import os

st.set_page_config(page_title="Nodata Release Radar", layout="wide")

st.title("🎵 Nodata.tv Release Radar")
st.write("Automatischer Feed neuer Releases mit direkten Links.")

# Daten laden
if os.path.exists("releases.json"):
    with open("releases.json", "r") as f:
        data = json.load(f)
else:
    data = []

if not data:
    st.info("Noch keine Daten vorhanden. Der Scraper läuft bald!")
else:
    # Suche/Filter
    search = st.text_input("Suche nach Artist oder Album...", "")
    
    # Grid Layout erstellen
    for release in data:
        if search.lower() in release['artist'].lower() or search.lower() in release['album'].lower():
            
            with st.container():
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if release['image']:
                        st.image(release['image'], width=200)
                    else:
                        st.text("Kein Bild")
                
                with col2:
                    st.subheader(f"{release['artist']} - {release['album']}")
                    st.caption(f"Gefunden am: {release['date_found']}")
                    
                    # Buttons für die Links
                    l = release['links']
                    c1, c2, c3, c4 = st.columns(4)
                    c1.link_button("📺 YouTube", l['youtube'])
                    c2.link_button("☁️ SoundCloud", l['soundcloud'])
                    c3.link_button("⛺ Bandcamp", l['bandcamp'])
                    c4.link_button("🍎 Apple Music", l['apple'])
            
            st.divider()
