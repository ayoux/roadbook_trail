import streamlit as st
import pandas as pd
from engine.parser import GPXProcessor
from engine.calculator import RaceEngine
from engine.strategy import NutritionPlanner
from streamlit_folium import st_folium
from datetime import datetime, timedelta
import folium
import json

st.set_page_config(page_title="Trail Commander V2", layout="wide")

# --- INITIALISATION ÉTAT ---
if 'gpx_data' not in st.session_state:
    st.session_state.gpx_data = None
if 'params' not in st.session_state:
    st.session_state.params = {"v_base": 10.0, "fatigue": 2.0}

# --- SIDEBAR ---
import json

with st.sidebar:
    st.divider()
    st.subheader("💾 Sauvegarde")
    st.title("⚙️ Réglages")
    st.session_state.params['v_base'] = st.slider("Vitesse à plat (km/h)", 4.0, 18.0, st.session_state.params['v_base'])
    st.session_state.params['fatigue'] = st.slider("Fatigue (%/heure)", 0.0, 10.0, st.session_state.params['fatigue'])
    
     # Export
    if st.session_state.gpx_data is not None:
        json_data = edited_df.to_json(orient="records")
        st.download_button(
            label="Télécharger mon Roadbook (JSON)",
            data=json_data,
            file_name="mon_roadbook.json",
            mime="application/json"
        )
    
    # Import
    uploaded_json = st.file_uploader("Charger un Roadbook existant", type="json")
    if uploaded_json:
        user_rb = pd.read_json(uploaded_json)
        st.session_state.df_roadbook = user_rb
        st.rerun()
    
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

# --- CONFIGURATION STRATÉGIE ---
st.subheader("🍌 Stratégie & Roadbook Dynamique")

# On récupère les params de la sidebar
engine = RaceEngine(st.session_state.params['v_base'], st.session_state.params['fatigue'])
nutri = NutritionPlanner(carbs_per_hour=60) # On pourrait mettre ces params en sidebar aussi

# 1. Initialisation des points de passage (Waypoints)
# Idéalement, ces points viennent de ton parser.py (waypoints du GPX)
if 'df_roadbook' not in st.session_state:
    st.session_state.df_roadbook = pd.DataFrame([
        {"Point": "Départ", "KM": 0.0, "D+": 0, "Pause_min": 0, "Type": "Départ"},
        {"Point": "Ravito 1", "KM": 15.0, "D+": 600, "Pause_min": 10, "Type": "Ravito"},
        {"Point": "Sommet", "KM": 25.0, "D+": 1500, "Pause_min": 0, "Type": "Sommet"},
        {"Point": "Arrivée", "KM": 42.0, "D+": 1800, "Pause_min": 0, "Type": "Arrivée"},
    ])

# 2. L'Éditeur interactif
st.write("Modifier les points, distances ou temps de pause :")
edited_df = st.data_editor(
    st.session_state.df_roadbook, 
    num_rows="dynamic", 
    key="rb_editor"
)

# 3. MOTEUR DE RECALCUL DYNAMIQUE
def calculate_itinerary(df_waypoints, full_gpx_df):
    results = []
    # Heure de départ personnalisable
    start_time_input = st.sidebar.time_input("Heure de départ", value=datetime.strptime("08:00", "%H:%M").time())
    current_time = datetime.combine(datetime.today(), start_time_input)
    cumul_h = 0.0
    
    # On trie les waypoints par kilométrage pour éviter les erreurs
    df_waypoints = df_waypoints.sort_values("KM")

    for i in range(len(df_waypoints)):
        row = df_waypoints.iloc[i]
        
        if i == 0:
            arrival = current_time
            seg_time_h = 0
            dplus_seg = 0
        else:
            # 1. On récupère TOUS les points GPX entre le point précédent et celui-ci
            prev_km = df_waypoints.iloc[i-1]['KM']
            curr_km = row['KM']
            segment_points = processor.get_segment_points(full_gpx_df, prev_km, curr_km)
            
            # 2. On calcule le temps en sommant chaque micro-segment
            seg_time_h = 0
            if not segment_points.empty:
                # Calcul du D+ réel sur ce segment
                dplus_seg = max(0, segment_points['ele'].diff().sum())
                
                # Somme des temps (distance entre points * vitesse Tobler à la pente locale)
                # On utilise une boucle simplifiée pour la lisibilité
                for j in range(1, len(segment_points)):
                    p1 = segment_points.iloc[j-1]
                    p2 = segment_points.iloc[j]
                    dist_p1p2 = p2['cumul_dist'] - p1['cumul_dist']
                    pente_p1p2 = p2['pente']
                    
                    t_p1p2 = engine.estimate_segment_time(dist_p1p2, pente_p1p2, cumul_h)
                    seg_time_h += t_p1p2
            else:
                dplus_seg = 0
                seg_time_h = 0

            arrival = current_time + timedelta(hours=seg_time_h)
        
        nutrition = nutri.get_needs(seg_time_h)
        
        results.append({
            "Arrivée": arrival.strftime("%H:%M"),
            "D+ Seg.": int(dplus_seg),
            "Durée Seg.": f"{int(seg_time_h)}h{int((seg_time_h%1)*60):02d}",
            "Glucides": f"{nutrition['glucides_g']}g",
            "Eau": f"{nutrition['eau_ml']}ml"
        })
        
        # Mise à jour pour le point suivant (Arrivée + Pause)
        current_time = arrival + timedelta(minutes=int(row['Pause_min']))
        cumul_h += (seg_time_h + float(row['Pause_min'])/60)

    # On combine les données saisies avec les résultats calculés
    return pd.concat([df_waypoints.reset_index(drop=True), pd.DataFrame(results)], axis=1)

# Affichage du résultat recalculé
final_df = calculate_itinerary(edited_df, st.session_state.gpx_data)
st.table(final_df)

# 4. LE BOUTON CREW (MODE ASSISTANCE)
st.divider()
if st.checkbox("🚀 Activer le Mode Crew (Assistance mobile)"):
    st.info("Affichage optimisé pour le bord de route")
    next_point = final_df.iloc[1] # Exemple : le prochain point
    c1, c2, c3 = st.columns(3)
    c1.metric("Prochain Point", next_point['Point'])
    c2.metric("Heure d'arrivée", next_point['Arrivée'])
    c3.metric("À préparer", f"{next_point['Eau (ml)']}ml + {next_point['Glucides (g)']}g")
