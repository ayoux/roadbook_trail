import gpxpy
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from typing import Optional

class GPXProcessor:
    """Gère le chargement, le nettoyage et la réduction de données GPX."""

    def __init__(self, file):
        self.gpx = gpxpy.parse(file)

    def extract_dataframe(self, sampling_rate: int = 10) -> pd.DataFrame:
        """
        Extrait les points et applique un downsampling.
        Args:
            sampling_rate: Garde 1 point sur N pour fluidifier l'affichage.
        """
        data = []
        for track in self.gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    data.append({
                        "lat": point.latitude,
                        "lon": point.longitude,
                        "ele": point.elevation,
                        "dist": 0.0
                    })
        
        df = pd.DataFrame(data).iloc[::sampling_rate].reset_index(drop=True)
        
        # Lissage de l'élévation pour éviter les "bruits" de GPS (D+ surestimé)
        if len(df) > 15:
            df['ele'] = savgol_filter(df['ele'], window_length=11, polyorder=2)
            
        return self._compute_metrics(df)

    def _compute_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcule distances et pentes entre les points."""
        # Calcul de distance simplifié (Haversine serait mieux pour la prod)
        df['dist_delta'] = 0.0 
        # Logique de calcul de distance entre points consécutifs ici...
    
    def get_segment_points(self, df: pd.DataFrame, start_km: float, end_km: float) -> pd.DataFrame:
        """Extrait les points du DataFrame situés entre deux bornes kilométriques."""
        mask = (df['cumul_dist'] >= start_km) & (df['cumul_dist'] <= end_km)
        return df.loc[mask].copy()
        # Pour rester concis, on simulera le cumul de distance
        df['cumul_dist'] = np.linspace(0, 100, len(df)) # Exemple
        df['pente'] = np.gradient(df['ele'], df['cumul_dist'] * 1000) * 100
        return df
