import numpy as np

class RaceEngine:
    """Calculateur de performance basé sur la pente et la fatigue."""

    def __init__(self, v_base: float, fatigue_coef: float):
        self.v_base = v_base  # Vitesse à plat (km/h)
        self.fatigue_coef = fatigue_coef / 100

    def tobler_speed(self, slope_pct: float) -> float:
        """
        Règle de Tobler modifiée pour le trail.
        Retourne la vitesse ajustée selon la pente.
        """
        s = slope_pct / 100
        # V = 6 * exp(-3.5 * |s + 0.05|) -> Version marche
        # Adapté pour trail (v_base calée sur s=0)
        adj = np.exp(-3.5 * abs(s + 0.05))
        return self.v_base * (adj / 0.84) # Normalisation à plat

    def estimate_segment_time(self, dist_km: float, slope: float, elapsed_h: float) -> float:
        """Estime le temps avec impact de la fatigue cumulative."""
        v_instant = self.tobler_speed(slope)
        slowdown = 1 - (self.fatigue_coef * elapsed_h)
        return dist_km / (max(v_instant * slowdown, 1.5)) # Vitesse mini 1.5km/h
