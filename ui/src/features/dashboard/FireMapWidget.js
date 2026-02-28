import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useLanguage } from "../../context/LanguageContext";
import InfoTooltip from "../../components/InfoTooltip";
import { burnedColor } from "../../constants/severity";

function FitBounds({ areasGeo, geometries }) {
  const map = useMap();
  useEffect(() => {
    if (!areasGeo || areasGeo.length === 0) return;
    // Guard against map container not being ready (e.g. after DnD remount)
    if (!map.getContainer() || !map.getPane("mapPane")) return;

    // Find the area with the highest total burned hectares
    const mostBurned = areasGeo.reduce((max, a) =>
      (a.total_burned_ha || 0) > (max.total_burned_ha || 0) ? a : max
    , areasGeo[0]);

    // Fit map to that area's bounds using lazy-loaded geometry
    const geometry = geometries[mostBurned.id];
    if (geometry) {
      try {
        const layer = L.geoJSON(geometry);
        const bounds = layer.getBounds();
        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
          return;
        }
      } catch { /* fall through */ }
    }
    map.setView([mostBurned.lat, mostBurned.lng], 10);
  }, [map, areasGeo, geometries]);
  return null;
}

function AreaPolygon({ area, geometry, t }) {
  const color = burnedColor(area.total_burned_ha);

  const style = useCallback(() => ({
    color,
    fillColor: color,
    fillOpacity: 0.35,
    weight: 2,
    opacity: 0.8,
  }), [color]);

  const onEachFeature = useCallback((_feature, layer) => {
    layer.bindPopup(
      `<strong>${area.name}</strong><br />` +
      `${t("dashboard.burnedHa")}: ${area.total_burned_ha.toLocaleString(undefined, { maximumFractionDigits: 1 })} ha<br />` +
      `${t("dashboard.fireMapRuns")}: ${area.run_count}<br />` +
      (area.last_analysis_date ? `${t("dashboard.fireMapLastAnalysis")}: ${area.last_analysis_date.replace(/-/g, "/")}` : "")
    );
  }, [area, t]);

  // Extract geometry from GeoJSON (Feature, FeatureCollection, or bare geometry)
  const extractedGeometry = useMemo(() => {
    if (!geometry) return null;
    const type = geometry.type;
    if (type === "FeatureCollection") {
      const features = geometry.features || [];
      return features[0]?.geometry || null;
    }
    if (type === "Feature") {
      return geometry.geometry;
    }
    if (type === "Polygon" || type === "MultiPolygon") {
      return geometry;
    }
    return null;
  }, [geometry]);

  // Wrap geometry as a GeoJSON Feature for react-leaflet
  const featureData = useMemo(() => ({
    type: "Feature",
    geometry: extractedGeometry,
    properties: {},
  }), [extractedGeometry]);

  if (!extractedGeometry) return null;

  return (
    <GeoJSON
      key={`${area.id}-${color}`}
      data={featureData}
      style={style}
      onEachFeature={onEachFeature}
    />
  );
}

export default function FireMapWidget({ areasGeo, authorizedFetch, baseUrl }) {
  const { t } = useLanguage();
  // Lazy-loaded geometries: { [areaId]: GeoJSON }
  const [geometries, setGeometries] = useState({});
  const loadingRef = useRef(new Set());

  // Delay MapContainer render so the parent DOM node is fully attached
  // before Leaflet tries to initialise panes (avoids "appendChild of
  // undefined" after DnD remount).
  const [mapReady, setMapReady] = useState(false);
  useEffect(() => {
    const id = setTimeout(() => setMapReady(true), 0);
    return () => { clearTimeout(id); setMapReady(false); };
  }, []);

  // Lazy-load geometries for all areas
  useEffect(() => {
    if (!areasGeo || !authorizedFetch || !baseUrl) return;

    const loadGeometries = async () => {
      for (const area of areasGeo) {
        if (geometries[area.id] || loadingRef.current.has(area.id)) continue;
        loadingRef.current.add(area.id);

        try {
          const response = await authorizedFetch(
            `${baseUrl}/area_of_interest/${area.id}/geojson/`
          );
          if (response.ok) {
            const geojson = await response.json();
            setGeometries(prev => ({ ...prev, [area.id]: geojson }));
          }
        } catch {
          // Silently ignore failures - will show CircleMarker fallback
        }
      }
    };

    loadGeometries();
  }, [areasGeo, authorizedFetch, baseUrl, geometries]);

  const defaultCenter = useMemo(() => {
    if (!areasGeo || areasGeo.length === 0) return [-14.235, -51.925];
    return [areasGeo[0].lat, areasGeo[0].lng];
  }, [areasGeo]);

  if (!areasGeo || areasGeo.length === 0) {
    return (
      <div className="card h-100 shadow-sm">
        <div className="card-header">
          <h3 className="h5 mb-0">{t("dashboard.fireMap")}
            <InfoTooltip text={t("dashboard.tooltipFireMap")} />
          </h3>
        </div>
        <div className="card-body d-flex align-items-center justify-content-center text-muted">
          {t("dashboard.noData")}
        </div>
      </div>
    );
  }

  return (
    <div className="card h-100 shadow-sm">
      <div className="card-header">
        <h3 className="h5 mb-0">{t("dashboard.fireMap")}
            <InfoTooltip text={t("dashboard.tooltipFireMap")} />
          </h3>
      </div>
      <div className="card-body p-0" style={{ height: 400, position: "relative" }}>
        {mapReady && <MapContainer
          center={defaultCenter}
          zoom={4}
          style={{ height: "100%", width: "100%", borderRadius: "0 0 0.375rem 0.375rem" }}
          scrollWheelZoom={true}
        >
          <FitBounds areasGeo={areasGeo} geometries={geometries} />
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {areasGeo.map((area) =>
            geometries[area.id] ? (
              <AreaPolygon key={area.id} area={area} geometry={geometries[area.id]} t={t} />
            ) : (
              <CircleMarker
                key={area.id}
                center={[area.lat, area.lng]}
                radius={8}
                pathOptions={{
                  color: burnedColor(area.total_burned_ha),
                  fillColor: burnedColor(area.total_burned_ha),
                  fillOpacity: 0.7,
                  weight: 2,
                }}
              >
                <Popup>
                  <strong>{area.name}</strong><br />
                  {t("dashboard.burnedHa")}: {area.total_burned_ha.toLocaleString(undefined, { maximumFractionDigits: 1 })} ha<br />
                  {t("dashboard.fireMapRuns")}: {area.run_count}<br />
                  {area.last_analysis_date && (
                    <>{t("dashboard.fireMapLastAnalysis")}: {area.last_analysis_date.replace(/-/g, "/")}</>
                  )}
                </Popup>
              </CircleMarker>
            )
          )}
        </MapContainer>}
        <div className="fire-map-legend">
          <div className="fire-map-legend__title">{t("dashboard.burnedHa")}</div>
          {[
            { color: "#22c55e", label: "0 ha" },
            { color: "#facc15", label: "< 50 ha" },
            { color: "#f97316", label: "< 200 ha" },
            { color: "#ef4444", label: "< 1,000 ha" },
            { color: "#7f1d1d", label: "\u2265 1,000 ha" },
          ].map(({ color, label }) => (
            <div key={label} className="fire-map-legend__item">
              <span className="fire-map-legend__swatch" style={{ background: color }} />
              <span>{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
