import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import folium
from streamlit_folium import st_folium

from engine.parser import GPXProcessor
from engine.simulator import RaceSimulator
from engine.strategy import StrategyManager

st.set_page_config(page_title="Trail Commander V3", layout="wide")

# --- INITIALISATION ---
if 'scenarios' not in st.session_state:
    st.session_state.scenarios = {} # Format: {name: {df_waypoints, params}}
if 'current_gpx' not in st.session_state:
    st.session_state.current_gpx = None

# --- SIDEBAR & CONFIGURATION ---
with st.sidebar:
    st.header("🏁 Configuration Course")
    uploaded_file = st.file_uploader("Upload GPX", type="gpx")
    
    if uploaded_file:
        proc = GPXProcessor(uploaded_file)
        st.session_state.current_gpx = proc.extract_full_dataframe()
    
    v_base = st.slider("Vitesse de base (km/h)", 4.0, 16.0, 10.0)
    fatigue = st.slider("Fatigue (%/h)", 0.0, 10.0, 2.0)
    start_time = st.time_input("Heure de départ", value=datetime.strptime("08:00", "%H:%M").time())

# --- MAIN INTERFACE ---
if st.session_state.current_gpx is not None:
    df_gpx = st.session_state.current_gpx
    sim = RaceSimulator(v_base, fatigue)
    strat = StrategyManager()

    st.title("🏃 Trail Commander Pro")

    # 1. ÉDITEUR DE ROADBOOK
    st.subheader("📋 Plan de Course (Interactif)")
    if 'waypoint_data' not in st.session_state:
        st.session_state.waypoint_data = pd.DataFrame([
            {"Point": "Départ", "KM": 0.0, "Pause_min": 0, "Reel": ""},
            {"Point": "Arrivée", "KM": df_gpx['cumul_dist'].max(), "Pause_min": 0, "Reel": ""}
        ])

    edited_rb = st.data_editor(st.session_state.waypoint_data, num_rows="dynamic")

    # 2. LOGIQUE DE CALCUL (WHAT-IF & LIVE)
    def run_recalculation(waypoints, full_df):
        results = []
        t0 = datetime.combine(datetime.today(), start_time)
        cumul_h = 0.0
        
        for i, row in waypoints.iterrows():
            if i == 0:
                arrival = t0
                seg_time = 0
            else:
                # Si le crew a saisi une heure réelle, on l'utilise pour recaler la suite
                if row['Reel']:
                    try:
                        arrival = datetime.combine(datetime.today(), datetime.strptime(row['Reel'], "%H:%M").time())
                        cumul_h = (arrival - t0).total_seconds() / 3600
                    except:
                        st.error(f"Format heure réel invalide pour {row['Point']}")
                
                # Calcul basé sur le GPX entre les deux points
                prev_km = waypoints.iloc[i-1]['KM']
                curr_km = row['KM']
                seg_points = full_df[(full_df['cumul_dist'] >= prev_km) & (full_df['cumul_dist'] <= curr_km)]
                
                seg_time = 0
                for j in range(1, len(seg_points)):
                    p1, p2 = seg_points.iloc[j-1], seg_points.iloc[j]
                    # On check si c'est la nuit (simplifié : 21h-06h)
                    current_hour = (t0 + timedelta(hours=cumul_h)).hour
                    is_night = current_hour >= 21 or current_hour < 6
                    
                    seg_time += sim.calculate_segment(p2['cumul_dist']-p1['cumul_dist'], p2['pente'], cumul_h, is_night)
                
                arrival = t0 + timedelta(hours=cumul_h + seg_time)
            
            needs = strat.compute_needs(seg_time)
            results.append({
                "Prévu": arrival.strftime("%H:%M"),
                "D+": int(max(0, seg_points['ele'].diff().sum())) if i > 0 else 0,
                "Nutri (g)": needs['carbs'],
                "Eau (ml)": needs['water']
            })
            cumul_h += seg_time + (row['Pause_min'] / 60)
            
        return pd.concat([waypoints, pd.DataFrame(results)], axis=1)

    final_df = run_recalculation(edited_rb, df_gpx)
    st.dataframe(final_df, use_container_width=True)

    # 3. CARTOGRAPHIE & PROFIL
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🗺️ Carte")
        m = folium.Map(location=[df_gpx.lat.mean(), df_gpx.lon.mean()], zoom_start=11)
        folium.PolyLine(df_gpx[['lat', 'lon']].values, color="blue", weight=3).add_to(m)
        st_folium(m, width=None, height=400)
    
    with col2:
        st.subheader("📈 Profil")
        fig = px.area(df_gpx, x="cumul_dist", y="ele", title="Altitude (m)")
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("👋 Bienvenue ! Commencez par uploader un fichier GPX dans la barre latérale pour activer le Commander.")
