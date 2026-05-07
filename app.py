import streamlit as st
import pandas as pd
from engine.parser import GPXProcessor
from engine.calculator import RaceEngine
from streamlit_folium import st_folium
import folium

st.set_page_config(page_title="Trail Commander V2", layout="wide")

# --- INITIALISATION ÉTAT ---
if 'gpx_data' not in st.session_state:
    st.session_state.gpx_data = None
if 'params' not in st.session_state:
    st.session_state.params = {"v_base": 10.0, "fatigue": 2.0}

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Réglages")
    st.session_state.params['v_base'] = st.slider("Vitesse à plat (km/h)", 4.0, 18.0, st.session_state.params['v_base'])
    st.session_state.params['fatigue'] = st.slider("Fatigue (%/heure)", 0.0, 10.0, st.session_state.params['fatigue'])
    
    uploaded_file = st.file_uploader("Fichier GPX", type="gpx")
    if uploaded_file:
        processor = GPXProcessor(uploaded_file)
        st.session_state.gpx_data = processor.extract_dataframe()

# --- DASHBOARD PRINCIPAL ---
if st.session_state.gpx_data is not None:
    df = st.session_state.gpx_data
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🗺️ Tracé et Profil")
        # Carte simplifiée
        m = folium.Map(location=[df.lat.mean(), df.lon.mean()], zoom_start=12)
        folium.PolyLine(df[['lat', 'lon']].values, color="red", weight=2.5).add_to(m)
        st_folium(m, width=600, height=300)

    with col2:
        st.subheader("📊 Analyse des pentes")
        # Histogramme de pente (Analyse de terrain)
        import plotly.express as px
        fig = px.histogram(df, x="pente", nbins=20, title="Répartition des inclinaisons (%)")
        st.plotly_chart(fig, use_container_width=True)

    # --- ÉDITEUR DE ROADBOOK ---
    st.subheader("📋 Roadbook Interactif")
    # On crée des points de passage tous les 10km (Exemple)
    engine = RaceEngine(st.session_state.params['v_base'], st.session_state.params['fatigue'])
    
    # Construction du tableau de passage simplifié
    roadbook_data = pd.DataFrame({
        "Point": ["Départ", "Ravito 1", "Sommet", "Arrivée"],
        "KM": [0, 15, 25, 42],
        "Pause (min)": [0, 10, 0, 0]
    })
    
    # Utilisation du data_editor pour que les amis puissent modifier les pauses
    edited_rb = st.data_editor(roadbook_data, num_rows="dynamic")
    
    st.info("💡 Prochaine étape : Lier l'éditeur au RaceEngine pour le recalcul 'What-if' en temps réel.")

else:
    st.warning("Veuillez uploader un fichier GPX pour commencer l'analyse.")
