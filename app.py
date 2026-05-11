import streamlit as st
import pandas as pd
import numpy as np
import gpxpy
import plotly.express as px
import folium
from datetime import datetime, timedelta
from scipy.signal import savgol_filter
from streamlit_folium import st_folium

# --- 1. LOGIQUE MOTEUR (CLASSES) ---

class GPXProcessor:
    def __init__(self, file):
        self.gpx = gpxpy.parse(file)

    def extract_dataframe(self) -> pd.DataFrame:
        data = []
        for track in self.gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    data.append({"lat": point.latitude, "lon": point.longitude, "ele": point.elevation})
        df = pd.DataFrame(data)
        # Lissage de l'élévation
        if len(df) > 11:
            df['ele'] = savgol_filter(df['ele'], 11, 2)
        # Distance
        lat, lon = np.radians(df['lat']), np.radians(df['lon'])
        dlat, dlon = lat.diff(), lon.diff()
        a = np.sin(dlat/2)**2 + np.cos(lat.shift()) * np.cos(lat) * np.sin(dlon/2)**2
        df['dist_delta'] = 2 * 6371 * np.arcsin(np.sqrt(a)).fillna(0)
        df['cumul_dist'] = df['dist_delta'].cumsum()
        # Pente
        df['pente'] = np.gradient(df['ele'], df['dist_delta'] * 1000).clip(-50, 50)
        return df.fillna(0)

class RaceSimulator:
    def __init__(self, v_base, fatigue, night_factor=0.80):
        self.v_base = v_base
        self.fatigue = fatigue / 100
        self.night_factor = night_factor

    def tobler_speed(self, slope_pct):
        s = slope_pct / 100
        return self.v_base * (np.exp(-3.5 * abs(s + 0.05)) / 0.84)

    def compute_segment(self, dist, slope, cumul_h, hour):
        v = self.tobler_speed(slope)
        v *= (1 / (1 + self.fatigue * cumul_h)) # Fatigue
        if hour >= 21 or hour < 6: v *= self.night_factor # Nuit
        return dist / max(v, 1.0)

class StrategyManager:
    def __init__(self, carbs=60, water=500):
        self.carbs, self.water = carbs, water
    def needs(self, duration_h):
        return {"carbs": int(duration_h * self.carbs), "water": int(duration_h * self.water)}

# --- 2. CONFIGURATION STREAMLIT ---

st.set_page_config(page_title="Trail Commander Pro", layout="wide")

if 'gpx_df' not in st.session_state: st.session_state.gpx_df = None
if 'waypoints' not in st.session_state:
    st.session_state.waypoints = pd.DataFrame([
        {"Point": "Départ", "KM": 0.0, "Pause_min": 0, "Reel": ""},
        {"Point": "Arrivée", "KM": 10.0, "Pause_min": 0, "Reel": ""}
    ])

# --- 3. SIDEBAR ---

with st.sidebar:
    st.title("⚙️ Paramètres")
    uploaded = st.file_uploader("Fichier GPX", type="gpx")
    if uploaded:
        st.session_state.gpx_df = GPXProcessor(uploaded).extract_dataframe()
        # Ajuster l'arrivée au KM réel du GPX
        st.session_state.waypoints.iloc[-1, 1] = st.session_state.gpx_df['cumul_dist'].max()

    v_base = st.slider("Vitesse de base (km/h)", 4.0, 16.0, 9.0)
    fatigue = st.slider("Fatigue (% par heure)", 0.0, 10.0, 2.0)
    start_time = st.time_input("Heure de départ", value=datetime.strptime("08:00", "%H:%M").time())
    
    st.divider()
    st.subheader("Nutrition /h")
    c_h = st.number_input("Glucides (g)", 30, 100, 60)
    w_h = st.number_input("Eau (ml)", 200, 1000, 500)

# --- 4. CALCULS ---

if st.session_state.gpx_df is not None:
    df_gpx = st.session_state.gpx_df
    sim = RaceSimulator(v_base, fatigue)
    strat = StrategyManager(c_h, w_h)
    
    st.title("🏃 Trail Commander Pro")
    
    # Éditeur de waypoints
    st.subheader("📋 Roadbook & Assistance")
    edited_df = st.data_editor(st.session_state.waypoints, num_rows="dynamic", use_container_width=True)
    st.session_state.waypoints = edited_df # Sauvegarde auto dans la session

    # Moteur de recalcul
    results = []
    current_dt = datetime.combine(datetime.today(), start_time)
    cumul_h = 0.0

    for i, row in edited_df.iterrows():
        # Gestion du mode REEL (Recalcul adaptatif)
        if row['Reel'] and len(row['Reel']) >= 4:
            try:
                current_dt = datetime.combine(datetime.today(), datetime.strptime(row['Reel'], "%H:%M").time())
            except: pass
        
        if i == 0:
            seg_time, d_plus = 0, 0
        else:
            prev_km = edited_df.iloc[i-1]['KM']
            mask = (df_gpx['cumul_dist'] >= prev_km) & (df_gpx['cumul_dist'] <= row['KM'])
            seg_points = df_gpx[mask]
            
            seg_time = 0
            if len(seg_points) > 1:
                for j in range(1, len(seg_points)):
                    p1, p2 = seg_points.iloc[j-1], seg_points.iloc[j]
                    seg_time += sim.compute_segment(
                        p2['cumul_dist']-p1['cumul_dist'], 
                        p2['pente'], 
                        cumul_h, 
                        current_dt.hour
                    )
            d_plus = int(max(0, seg_points['ele'].diff().sum()))
            current_dt += timedelta(hours=seg_time)

        res_nutri = strat.needs(seg_time)
        results.append({
            "Passage": current_dt.strftime("%H:%M"),
            "D+ Seg": d_plus,
            "Glucides": f"{res_nutri['carbs']}g",
            "Eau": f"{res_nutri['water']}ml"
        })
        
        # Ajouter la pause pour le prochain segment
        pause = int(row['Pause_min'])
        current_dt += timedelta(minutes=pause)
        cumul_h += seg_time + (pause/60)

    # Affichage final
    final_view = pd.concat([edited_df.reset_index(drop=True), pd.DataFrame(results)], axis=1)
    st.table(final_view)

    # Visualisation
    col1, col2 = st.columns(2)
    with col1:
        m = folium.Map(location=[df_gpx.lat.mean(), df_gpx.lon.mean()], zoom_start=11)
        folium.PolyLine(df_gpx[['lat', 'lon']].values, color="red", weight=2).add_to(m)
        st_folium(m, width=None, height=400, key="map")
    with col2:
        fig = px.area(df_gpx, x="cumul_dist", y="ele", title="Profil Altimétrique")
        st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("👈 Veuillez charger un fichier GPX pour commencer.")
