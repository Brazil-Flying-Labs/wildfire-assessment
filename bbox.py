import json
from shapely.geometry import Polygon, mapping
from shapely.ops import transform
from pyproj import Transformer

# --- Polígono original ---
POLYGON = [
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

# --- Margem em graus ---
MARGIN = 0.002  # ~200 metros

# Cria polígono e calcula bounding box
poly = Polygon(POLYGON)
minx, miny, maxx, maxy = poly.bounds

# Adiciona margem
minx -= MARGIN
miny -= MARGIN
maxx += MARGIN
maxy += MARGIN

# Coordenadas do bounding box expandido
bbox_coords = [
    [minx, miny],
    [minx, maxy],
    [maxx, maxy],
    [maxx, miny],
    [minx, miny]
]

bbox_poly = Polygon(bbox_coords)

# --- Gera GeoJSON em EPSG:4326 ---
geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Bounding Box com margem"},
            "geometry": mapping(bbox_poly)
        }
    ]
}

output_file = "bounding_box_margin.geojson"
with open(output_file, "w") as f:
    json.dump(geojson, f, indent=2)

print(f"[OK] GeoJSON salvo em: {output_file}")
print("Coordenadas do retângulo expandido (EPSG:4326):")
for i, (x, y) in enumerate(bbox_coords[:-1], start=1):
    print(f"P{i}: ({x:.6f}, {y:.6f})")

# --- Conversão para EPSG:32723 (UTM 23S) ---
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32723", always_xy=True)
bbox_utm_coords = [transformer.transform(x, y) for x, y in bbox_coords]
bbox_utm_poly = Polygon(bbox_utm_coords)

# --- Gera GeoJSON em EPSG:32723 ---
geojson_utm = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Bounding Box com margem (UTM)"},
            "geometry": mapping(bbox_utm_poly)
        }
    ]
}

output_file_utm = "bounding_box_margin_utm.geojson"
with open(output_file_utm, "w") as f:
    json.dump(geojson_utm, f, indent=2)

print(f"[OK] GeoJSON salvo em: {output_file_utm}")
print("Coordenadas do retângulo expandido (EPSG:32723):")
for i, (x, y) in enumerate(bbox_utm_coords[:-1], start=1):
    print(f"P{i}: ({x:.2f}, {y:.2f})")
