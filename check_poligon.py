from shapely.geometry import Polygon
from shapely.validation import make_valid

BBOX_POLYGON = [
    [-47.825, -21.516], [-47.811, -21.519], [-47.804, -21.552],
    [-47.796, -21.559], [-47.791, -21.566], [-47.789, -21.573], [-47.784, -21.578],
    [-47.782, -21.577], [-47.767, -21.581], [-47.760, -21.592], [-47.757, -21.592],
    [-47.756, -21.601], [-47.730, -21.598], [-47.725, -21.595], [-47.725, -21.591],
    [-47.723, -21.588], [-47.718, -21.588], [-47.713, -21.591], [-47.710, -21.597],
    [-47.713, -21.600], [-47.714, -21.605], [-47.721, -21.609], [-47.726, -21.615],
    [-47.680, -21.631], [-47.680, -21.632], [-47.728, -21.676], [-47.730, -21.672],
    [-47.730, -21.675], [-47.732, -21.672], [-47.734, -21.662], [-47.737, -21.658],
    [-47.740, -21.648], [-47.736, -21.648], [-47.726, -21.618], [-47.729, -21.616],
    [-47.735, -21.619], [-47.740, -21.619], [-47.745, -21.623], [-47.758, -21.623],
    [-47.761, -21.624], [-47.769, -21.619], [-47.773, -21.618], [-47.776, -21.620],
    [-47.781, -21.626], [-47.785, -21.625], [-47.793, -21.627], [-47.802, -21.626],
    [-47.811, -21.630], [-47.813, -21.626], [-47.818, -21.624], [-47.816, -21.617],
    [-47.819, -21.615], [-47.822, -21.611], [-47.828, -21.612], [-47.831, -21.615],
    [-47.834, -21.611], [-47.831, -21.606], [-47.832, -21.600], [-47.835, -21.603],
    [-47.838, -21.599], [-47.844, -21.600], [-47.846, -21.596], [-47.841, -21.582],
    [-47.839, -21.577], [-47.836, -21.559], [-47.798, -21.559], [-47.804, -21.554],
    [-47.826, -21.545], [-47.838, -21.546], [-47.840, -21.536], [-47.838, -21.532],
    [-47.829, -21.520], [-47.827, -21.520], [-47.825, -21.516],
    [-47.825, -21.516]
]

polygon = Polygon(BBOX_POLYGON)
if not polygon.is_valid:
    print("Polígono inválido, tentando corrigir...")
    polygon = make_valid(polygon)
else:
    print("poligono valido.")

from pyproj import Transformer

# Criar o polígono
polygon = Polygon(BBOX_POLYGON)

# Transformar para um CRS projetado (ex.: UTM EPSG:32723)
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32723", always_xy=True)
coords_transformed = [transformer.transform(lon, lat) for lon, lat in BBOX_POLYGON]
polygon_utm = Polygon(coords_transformed)

# Calcular área
area_m2 = polygon_utm.area
print(f"Área do polígono: {area_m2:.2f} metros quadrados")

import matplotlib.pyplot as plt

x, y = polygon.exterior.xy
plt.plot(x, y, 'b-')
plt.fill(x, y, alpha=0.3)
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.title('Polígono')
plt.show()

if BBOX_POLYGON[0] != BBOX_POLYGON[-1]:
    print("erro")
