from typing import Dict

class NutritionPlanner:
    """Calcule les besoins énergétiques et hydriques par segment."""

    def __init__(self, carbs_per_hour: int = 60, water_per_hour: int = 500, salt_per_hour: float = 0.5):
        self.carbs_per_hour = carbs_per_hour  # Cible standard : 60-90g/h
        self.water_per_hour = water_per_hour  # ml/h
        self.salt_per_hour = salt_per_hour    # g/h

    def get_needs(self, duration_hours: float) -> Dict[str, float]:
        """Retourne les besoins pour une durée donnée."""
        return {
            "glucides_g": round(duration_hours * self.carbs_per_hour),
            "eau_ml": round(duration_hours * self.water_per_hour),
            "sel_g": round(duration_hours * self.salt_per_hour, 1)
        }

    def get_logistics_advice(self, duration_hours: float) -> str:
        """Génère un conseil logistique pour l'assistance."""
        needs = self.get_needs(duration_hours)
        if duration_hours < 1:
            return "Simple hydratation."
        if duration_hours > 4:
            return f"Prévoir solide + {needs['eau_ml']}ml. Vérifier état mental."
        return f"Focus gels/boisson : {needs['glucides_g']}g de glucides."
