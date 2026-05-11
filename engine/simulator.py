import numpy as np
from typing import Optional

class RaceSimulator:
    """Calcule les prévisions chronométriques basées sur la biomécanique de l'effort."""

    def __init__(self, v_base: float, fatigue_rate: float, night_factor: float = 0.85):
        self.v_base = v_base  # km/h sur plat
        self.fatigue_rate = fatigue_rate / 100
        self.night_factor = night_factor

    def get_tobler_speed(self, slope_pct: float) -> float:
        """
        Calcule la vitesse théorique selon la pente (Loi de Tobler modifiée).
        $V = V_{base} \cdot e^{-3.5 \cdot |s + 0.05|}$ normalisé.
        """
        s = slope_pct / 100
        # On normalise pour que la vitesse à 0% de pente soit proche de v_base
        adj = np.exp(-3.5 * abs(s + 0.05)) / 0.84 
        return self.v_base * adj

    def calculate_segment(self, dist_km: float, slope: float, cumul_h: float, is_night: bool) -> float:
        """Estime le temps d'un micro-segment avec fatigue et mode nuit."""
        v_theoretical = self.get_tobler_speed(slope)
        
        # Application de la fatigue (ralentissement progressif)
        fatigue_impact = 1 / (1 + self.fatigue_rate * cumul_h)
        
        v_final = v_theoretical * fatigue_impact
        if is_night:
            v_final *= self.night_factor
            
        return dist_km / max(v_final, 1.2) # Plancher à 1.2 km/h
