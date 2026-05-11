import gpxpy
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from typing import Dict, Optional

class GPXProcessor:
    """Gère le parsing, le lissage et l'analyse spatiale des traces GPX."""

    def __init__(self, file):
        self.gpx = gpxpy.parse(file)

    def extract_full_dataframe(self, downsampling: int = 5) -> pd.DataFrame:
        """Extrait les points, calcule les distances cumulées et lisse l'élévation."""
        data = []
        for track in self.gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    data.append({
                        "lat": point.latitude,
                        "lon": point.longitude,
                        "ele": point.elevation
                    })
        
        df = pd.DataFrame(data).iloc[::downsampling].reset_index(drop=True)
        
        # Lissage de l'élévation (évite le bruit GPS qui gonfle le D+)
        if len(df) > 11:
            df['ele'] = savgol_filter(df['ele'], window_length=11, polyorder=2)

        # Calcul des distances
        df['dist_delta'] = self._haversine_distance(df)
        df['cumul_dist'] = df['dist_delta'].cumsum()
        
        # Calcul des pentes locales (%)
        df['pente'] = np.gradient(df['ele'], df['dist_delta'] * 1000).clip(-50, 50)
        df.fillna(0, inplace=True)
        return df

    @staticmethod
    def _haversine_distance(df: pd.DataFrame) -> pd.Series:
        """Calcule la distance en km entre points consécutifs."""
        lat = np.radians(df['lat'])
        lon = np.radians(df['lon'])
        dlat = lat.diff()
        dlon = lon.diff()
        a = np.sin(dlat/2)**2 + np.cos(lat.shift()) * np.cos(lat) * np.sin(dlon/2)**2
        return 2 * 6371 * np.arcsin(np.sqrt(a)).fillna(0)
