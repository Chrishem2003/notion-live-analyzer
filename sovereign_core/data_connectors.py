
import numpy as np
import datetime

class LiveDataConnector:
    """Simulates high-throughput streaming feeds for central banks, WHO, and satellite telemetry."""
    @staticmethod
    def fetch_market_yields(country):
        base_yield = 12.5 if "Uganda" in country else 8.0
        return round(base_yield  np.random.normal(0, 0.3), 2)

    @staticmethod
    def fetch_icu_capacity(facility):
        return round(min(100.0, max(10.0, 72.4  np.random.normal(0, 2.5))), 1)

    @staticmethod
    def fetch_satellite_crop_index():
        return round(float(np.clip(0.68  np.random.normal(0, 0.05), 0.0, 1.0)), 3)





