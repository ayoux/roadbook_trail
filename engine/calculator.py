import numpy as np

class TrailEngine:
    def __init__(self, v_plat, coef_d_plus=10, coef_fatigue=0.0):
        self.v_plat = v_plat  # km/h
        self.coef_d_plus = coef_d_plus  # 100m D+ = X km effort
        self.coef_fatigue = coef_fatigue # % de ralentissement par heure

    def compute_segment_time(self, distance_km, d_plus_m, cumulative_hours=0):
        """
        Calcule le temps pour un segment en tenant compte du km-effort
        et de la fatigue accumulée.
        """
        # Formule de base : Km-effort
        km_effort = distance_km + (max(0, d_plus_m) / 100)
        
        # Temps théorique sans fatigue
        base_time = km_effort / self.v_plat
        
        # Application de la fatigue (linéaire pour la V1)
        # On ralentit de X% par heure déjà passée
        slowdown_factor = 1 + (self.coef_fatigue / 100 * cumulative_hours)
        
        return base_time * slowdown_factor
