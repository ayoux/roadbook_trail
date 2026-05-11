class StrategyManager:
    """Gère les besoins en ressources selon l'intensité et la durée."""

    def __init__(self, carbs_h: int = 60, water_h: int = 500):
        self.carbs_h = carbs_h
        self.water_h = water_h

    def compute_needs(self, duration_h: float):
        return {
            "carbs": round(duration_h * self.carbs_h),
            "water": round(duration_h * self.water_h)
        }
