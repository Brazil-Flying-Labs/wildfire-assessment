export function validatePolygonGeometry(geojson) {
  const allowed = ["Polygon", "MultiPolygon"];
  const type = geojson.type;
  if (type === "Feature") {
    const geomType = geojson.geometry?.type;
    if (!allowed.includes(geomType)) return false;
  } else if (type === "FeatureCollection") {
    for (const feat of geojson.features || []) {
      const geomType = feat.geometry?.type;
      if (!allowed.includes(geomType)) return false;
    }
  } else if (!allowed.includes(type)) {
    return false;
  }
  return true;
}
