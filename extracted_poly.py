import geojson

# BBOX_POLYGON = [
#     [-47.986093657999975, -21.742566157999966],
#     [-47.986093657999975, -21.32230777999997],
#     [-47.565835278999975, -21.32230777999997],
#     [-47.565835278999975, -21.742566157999966],
#     [-47.986093657999975, -21.742566157999966]
# ]

BBOX_POLYGON = [
    [-47.848, -21.677999999999997],
    [-47.848, -21.514],
    [-47.6762, -21.514],  # Aumentado mais 0.0009 graus (total de 200 metros)
    [-47.6762, -21.677999999999997],  # Aumentado mais 0.0009 graus
    [-47.848, -21.677999999999997]
]

bbox_geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [BBOX_POLYGON]},
            "properties": {}
        }
    ]
}

with open("extended_bbox_jatai_down.geojson", "w") as f:
    geojson.dump(bbox_geojson, f)

print("Novo bbox estendido para baixo salvo em 'extended_bbox_jatai_down.geojson'")