import ee

# Visualization parameters
VIS_PARAMS = {
    "rgb": {"bands": ["B4", "B3", "B2"], "min": 0, "max": 0.3},
    "ndvi": {"min": -0.2, "max": 0.9, "palette": ["brown", "yellow", "green"]},
    "nbr": {"min": -0.3, "max": 0.56, "palette": ["brown", "yellow", "green"]},
    "delta_ndvi": {
        "min": 0,
        "max": 0.5,
        "palette": ["00FF00", "FFFF00", "FFA500", "FF0000", "8B4513"],
        "values": [0.0, 0.07, 0.20, 0.33, 0.45],
    },
    "delta_nbr": {
        "min": -0.3,
        "max": 0.5,
        "palette": ["00FF00", "FFFF00", "FFA500", "FF0000", "8B4513"],
        "values": [0.0, 0.1, 0.27, 0.44, 0.66],
    },
    "rbr": {"min": -0.5, "max": 0.6, "palette": ["black", "yellow", "red"]},
}

# Export settings
EXPORT_FOLDER = "GEE_exports"
EXPORT_SCALE = 30
EXPORT_CRS = "EPSG:4326"
EXPORT_MAX_PIXELS = 1e13

# Severity classification thresholds
SEVERITY_THRESHOLDS = [
    (0.1, "Unburned", 0),
    (0.27, "Low", 1),
    (0.44, "Moderate", 2),
    (0.66, "High", 3),
    (1.0, "Very High", 4),
]

# Authentication settings
SERVICE_ACCOUNT = "gee-service-account@well-stem.iam.gserviceaccount.com"
# CREDENTIALS_PATH = '/app/gee-service-account-credentials.json'  # Path inside Docker container
CREDENTIALS_PATH = r"C:\Users\Wellington\Documents\projeto\flying-labs\wildfire-assessment\well-stem-549be8c54c1c.json"
PROJECT_ID = "well-stem"
POLYGON_PATH = r"polygons"
