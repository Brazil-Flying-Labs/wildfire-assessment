import json
import matplotlib.pyplot as plt
from shapely.geometry import shape
from shapely.ops import transform
import pyproj

# --- Função para ler GeoJSON ---
def load_geojson(path):
    with open(path, "r") as f:
        data = json.load(f)
    geoms = [shape(feat["geometry"]) for feat in data["features"]]
    crs = data.get("crs", {}).get("properties", {}).get("name", None)
    return geoms, crs

# --- Função para reprojetar geometria ---
def reproject_geometry(geom, src_crs, dst_crs):
    project = pyproj.Transformer.from_crs(src_crs, dst_crs, always_xy=True).transform
    return transform(project, geom)

# --- Arquivos ---
file_utm = "jatai-utm32723.geojson"
file_wgs = "jatai-EPSG-4326.geojson"

# --- Ler GeoJSONs ---
geoms_utm, crs_utm = load_geojson(file_utm)
geoms_wgs, crs_wgs = load_geojson(file_wgs)

# --- Reprojetar geoms WGS84 para UTM (EPSG:32723) ---
geoms_wgs_reproj = [reproject_geometry(g, "EPSG:4326", "EPSG:32723") for g in geoms_wgs]

# --- Plotar ---
fig, ax = plt.subplots(figsize=(8, 8))

# GeoJSON UTM (original)
for i, geom in enumerate(geoms_utm):
    if geom.geom_type == "LineString":
        x, y = geom.xy
        ax.plot(x, y, color="blue", label="GeoJSON UTM (32723)" if i == 0 else "")
    elif geom.geom_type == "MultiLineString":
        for j, line in enumerate(geom.geoms):
            x, y = line.xy
            ax.plot(x, y, color="blue", label="GeoJSON UTM (32723)" if i == 0 and j == 0 else "")

# GeoJSON reprojetado (de 4326 para 32723)
for i, geom in enumerate(geoms_wgs_reproj):
    if geom.geom_type == "LineString":
        x, y = geom.xy
        ax.plot(x, y, color="red", linestyle="--", label="GeoJSON reprojetado (4326→32723)" if i == 0 else "")
    elif geom.geom_type == "MultiLineString":
        for j, line in enumerate(geom.geoms):
            x, y = line.xy
            ax.plot(x, y, color="red", linestyle="--", label="GeoJSON reprojetado (4326→32723)" if i == 0 and j == 0 else "")

ax.set_title("Comparação: UTM (EPSG:32723) vs reprojetado de EPSG:4326")
ax.set_xlabel("Easting (m)")
ax.set_ylabel("Northing (m)")
ax.axis("equal")
ax.legend()
plt.show()
