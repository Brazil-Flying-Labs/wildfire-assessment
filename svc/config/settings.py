import ee

# Coordinates for Jataí polygon
JATAI_COORDINATES = [
    [[-47.825, -21.516], [-47.811, -21.519], [-47.804, -21.552], [-47.796, -21.559],
     [-47.791, -21.566], [-47.789, -21.573], [-47.784, -21.578], [-47.782, -21.577],
     [-47.767, -21.581], [-47.76, -21.592], [-47.757, -21.592], [-47.756, -21.601],
     [-47.73, -21.598], [-47.725, -21.595], [-47.725, -21.591], [-47.723, -21.588],
     [-47.718, -21.588], [-47.713, -21.591], [-47.71, -21.597], [-47.713, -21.6],
     [-47.714, -21.605], [-47.721, -21.609], [-47.726, -21.615], [-47.68, -21.631],
     [-47.68, -21.632], [-47.728, -21.676], [-47.73, -21.672], [-47.73, -21.675],
     [-47.732, -21.672], [-47.734, -21.662], [-47.737, -21.658], [-47.74, -21.648],
     [-47.736, -21.648], [-47.726, -21.618], [-47.729, -21.616], [-47.735, -21.619],
     [-47.74, -21.619], [-47.745, -21.623], [-47.758, -21.623], [-47.761, -21.624],
     [-47.769, -21.619], [-47.773, -21.618], [-47.776, -21.62], [-47.781, -21.626],
     [-47.785, -21.625], [-47.793, -21.627], [-47.802, -21.626], [-47.811, -21.63],
     [-47.813, -21.626], [-47.818, -21.624], [-47.816, -21.617], [-47.819, -21.615],
     [-47.822, -21.611], [-47.828, -21.612], [-47.831, -21.615], [-47.834, -21.611],
     [-47.831, -21.606], [-47.832, -21.6], [-47.835, -21.603], [-47.838, -21.599],
     [-47.844, -21.6], [-47.846, -21.596], [-47.841, -21.582], [-47.839, -21.577],
     [-47.836, -21.559], [-47.798, -21.559], [-47.804, -21.554], [-47.826, -21.545],
     [-47.838, -21.546], [-47.84, -21.536], [-47.838, -21.532], [-47.829, -21.52],
     [-47.827, -21.52], [-47.825, -21.516]]
]

def get_polygon():
    """Create an ee.Geometry.Polygon from Jataí coordinates.

    Returns:
        ee.Geometry.Polygon, Polygon for the Jataí region.
    """
    return ee.Geometry.Polygon(JATAI_COORDINATES)

# Date ranges for pre- and post-fire analysis
PRE_FIRE_DATES = ('2024-06-01', '2024-10-01')
POST_FIRE_DATES = ('2024-10-17', '2024-12-31')

# Visualization parameters
VIS_PARAMS = {
    'rgb': {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 0.3},
    'ndvi': {'min': -0.2, 'max': 0.9, 'palette': ['brown', 'yellow', 'green']},
    'nbr': {'min': -0.3, 'max': 0.56, 'palette': ['brown', 'yellow', 'green']},
    'delta_ndvi': {
        'min': 0,
        'max': 0.5,
        'palette': ['00FF00', 'FFFF00', 'FFA500', 'FF0000', '8B4513'],
        'values': [0.0, 0.07, 0.20, 0.33, 0.45]
    },
    'delta_nbr': {
        'min': -0.3,
        'max': 0.5,
        'palette': ['00FF00', 'FFFF00', 'FFA500', 'FF0000', '8B4513'],
        'values': [0.0, 0.1, 0.27, 0.44, 0.66]
    },
    'rbr': {'min': -0.5, 'max': 0.6, 'palette': ['black', 'yellow', 'red']}
}

# Export settings
EXPORT_FOLDER = 'GEE_exports'
EXPORT_SCALE = 30
EXPORT_CRS = 'EPSG:4326'
EXPORT_MAX_PIXELS = 1e13

# Severity classification thresholds
SEVERITY_THRESHOLDS = [
    (0.1, 'Unburned', 0),
    (0.27, 'Low', 1),
    (0.44, 'Moderate', 2),
    (0.66, 'High', 3),
    (1.0, 'Very High', 4) 
]

# Authentication settings
SERVICE_ACCOUNT = 'gee-service-account@well-stem.iam.gserviceaccount.com'
# CREDENTIALS_PATH = '/app/gee-service-account-credentials.json'  # Path inside Docker container
CREDENTIALS_PATH = r"C:\Users\Wellington\Documents\projeto\flying-labs\wildfire-assessment\well-stem-549be8c54c1c.json"
PROJECT_ID = 'well-stem'
POLYGON_PATH = r'C:\Users\Wellington\Documents\projeto\flying-labs\wildfire-assessment\polygons'