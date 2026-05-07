import streamlit as st
import pandas as pd
from engine.parser import GPXProcessor
from engine.calculator import RaceEngine
from engine.strategy import NutritionPlanner
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
def calculate_itinerary(df):
    results = []
    current_time = datetime.combine(datetime.today(), datetime.min.time()) # T0 : 00:00
    cumul_h = 0.0
    
    for i, row in df.iterrows():
        if i == 0:
            arrival = current_time
            seg_time_h = 0
        else:
            # Calcul du segment précédent à celui-ci
            dist_seg = row['KM'] - df.iloc[i-1]['KM']
            # On simplifie la pente moyenne du segment pour la V2
            dplus_seg = row['D+'] - df.iloc[i-1]['D+']
            slope_avg = (dplus_seg / (dist_seg * 1000)) * 100 if dist_seg > 0 else 0
            
            # Appel au RaceEngine (Tobler + Fatigue)
            seg_time_h = engine.estimate_segment_time(dist_seg, slope_avg, cumul_h)
            arrival = current_time + timedelta(hours=seg_time_h)
        
        # Nutrition pour le segment à venir
        # (On regarde la durée du segment suivant si possible, ou du segment actuel)
        nutrition = nutri.get_needs(seg_time_h)
        
        results.append({
            "Arrivée": arrival.strftime("%H:%M"),
            "Durée Seg.": f"{int(seg_time_h)}h{int((seg_time_h%1)*60):02d}",
            "Glucides (g)": nutrition['glucides_g'],
            "Eau (ml)": nutrition['eau_ml']
        })
        
        # Update pour le prochain point : Arrivée + Pause
        current_time = arrival + timedelta(minutes=row['Pause_min'])
        cumul_h += (seg_time_h + row['Pause_min']/60)

    return pd.concat([df, pd.DataFrame(results)], axis=1)

# Affichage du résultat recalculé
final_df = calculate_itinerary(edited_df)
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
