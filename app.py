import streamlit as st
import gpxpy
import pandas as pd
import plotly.express as px
from engine.calculator import TrailEngine

st.set_page_config(page_title="Trail Roadbook Creator", layout="wide")

st.title("🏃‍♂️ Trail Roadbook & Strategy")

# --- SIDEBAR : PARAMÈTRES ATHLÈTE ---
with st.sidebar:
    st.header("Configuration")
    v_plat = st.slider("Vitesse à plat (km/h)", 4.0, 16.0, 10.0)
    c_fatigue = st.slider("Coefficient de fatigue (%/h)", 0.0, 10.0, 2.0)
    dist_segment = st.number_input("Découpage segments (km)", 1, 20, 5)

# --- UPLOAD ---
uploaded_file = st.file_uploader("Importe ta trace GPX", type="gpx")

if uploaded_file:
    gpx = gpxpy.parse(uploaded_file)
    engine = TrailEngine(v_plat=v_plat, coef_fatigue=c_fatigue)
    
    # 1. Parsing simplifié
    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for p in segment.points:
                points.append({'lat': p.latitude, 'lon': p.longitude, 'ele': p.elevation})
    
    df = pd.DataFrame(points)
    
    # Calcul des deltas (distance et D+)
    df['dist_diff'] = 0.0
    df['ele_diff'] = 0.0
    # Note : Pour un vrai calcul précis, utiliser geopy pour la distance entre lat/lon
    # Ici on simplifie pour la structure
    
    # 2. Génération du Roadbook par segments
    st.subheader("📊 Profil Altimétrique")
    fig = px.area(df, y="ele", title="Élévation")
    st.plotly_chart(fig, use_container_width=True)

    # 3. Tableau de passage (Simulation de données)
    st.subheader("📋 Table de passage prévisionnelle")
    
    # Simulation de segments de 5km pour l'exemple
    data_roadbook = {
        "Segment": ["Départ", "Ravito 1", "Sommet 1", "Ravito 2", "Arrivée"],
        "KM Cumulé": [0, 12, 18, 30, 42],
        "D+ Cumulé": [0, 450, 1200, 1400, 1800],
    }
    rb_df = pd.DataFrame(data_roadbook)
    
    # Application du moteur de calcul
    times = []
    cumul_h = 0
    for i, row in rb_df.iterrows():
        if i == 0: 
            times.append("00:00")
            continue
        
        # Calcul de la tranche
        d_km = rb_df.iloc[i]['KM Cumulé'] - rb_df.iloc[i-1]['KM Cumulé']
        d_plus = rb_df.iloc[i]['D+ Cumulé'] - rb_df.iloc[i-1]['D+ Cumulé']
        
        t_segment = engine.compute_segment_time(d_km, d_plus, cumul_h)
        cumul_h += t_segment
        
        # Formatage HH:MM
        hours = int(cumul_h)
        minutes = int((cumul_h - hours) * 60)
        times.append(f"{hours:02d}:{minutes:02d}")
    
    rb_df['Heure de passage (estimée)'] = times
    st.table(rb_df)

else:
    st.info("En attente d'un fichier GPX pour générer le roadbook.")
