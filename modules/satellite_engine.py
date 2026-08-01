

import requests
from datetime import datetime

def fetch_field_site_telemetry(lat: float, lon: float) -> dict:
    """Simulates real-time NASA/Sentinel satellite telemetry retrieval for biological sampling points."""
    # Calculates localized vegetation index proxy and satellite pass data
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    ndvi_value = round(0.45  ((lat  lon) % 0.35), 2)
    
    return {
        "coordinates": f"{lat:.4f}, {lon:.4f}",
        "timestamp": timestamp,
        "satellite_source": "Sentinel-2 / NASA MODIS",
        "ndvi_index": ndvi_value,
        "vegetation_health": "Dense / Optimal" if ndvi_value > 0.6 else "Moderate",
        "surface_temp_c": round(24.5  (lat % 5), 1),
        "moisture_index": "72%"
    }
