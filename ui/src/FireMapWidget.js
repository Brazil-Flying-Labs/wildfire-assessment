import { useCallback, useEffect, useMemo } from "react";
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useLanguage } from "./LanguageContext";

function burnedColor(totalBurnedHa) {
  if (totalBurnedHa <= 0) return "#22c55e";
  if (totalBurnedHa < 50) return "#facc15";
  if (totalBurnedHa < 200) return "#f97316";
  if (totalBurnedHa < 1000) return "#ef4444";
  return "#7f1d1d";
}

function FitBounds({ areasGeo }) {
  const map = useMap();
  useEffect(() => {
    if (!areasGeo || areasGeo.length === 0) return;

    // Find the area with the highest total burned hectares
    const mostBurned = areasGeo.reduce((max, a) =>
      (a.total_burned_ha || 0) > (max.total_burned_ha || 0) ? a : max
    , areasGeo[0]);

    // Fit map to that area's bounds
    if (mostBurned.geometry) {
      try {
        const layer = L.geoJSON(mostBurned.geometry);
        const bounds = layer.getBounds();
        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
          return;
        }
      } catch { /* fall through */ }
    }
    map.setView([mostBurned.lat, mostBurned.lng], 10);
  }, [map, areasGeo]);
  return null;
}

function AreaPolygon({ area, t }) {
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

  // Wrap geometry as a GeoJSON Feature for react-leaflet
  const featureData = useMemo(() => ({
    type: "Feature",
    geometry: area.geometry,
    properties: {},
  }), [area.geometry]);

  return (
    <GeoJSON
      key={`${area.id}-${color}`}
      data={featureData}
      style={style}
      onEachFeature={onEachFeature}
    />
  );
}

export default function FireMapWidget({ areasGeo }) {
  const { t } = useLanguage();

  const defaultCenter = useMemo(() => {
    if (!areasGeo || areasGeo.length === 0) return [-14.235, -51.925];
    return [areasGeo[0].lat, areasGeo[0].lng];
  }, [areasGeo]);

  if (!areasGeo || areasGeo.length === 0) {
    return (
      <div className="card h-100 shadow-sm">
        <div className="card-header">
          <h3 className="h5 mb-0">{t("dashboard.fireMap")}
            <span className="info-tooltip">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
              <span className="info-tooltip-text">{t("dashboard.tooltipFireMap")}</span>
            </span>
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
            <span className="info-tooltip">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
              <span className="info-tooltip-text">{t("dashboard.tooltipFireMap")}</span>
            </span>
          </h3>
      </div>
      <div className="card-body p-0" style={{ height: 400 }}>
        <MapContainer
          center={defaultCenter}
          zoom={4}
          style={{ height: "100%", width: "100%", borderRadius: "0 0 0.375rem 0.375rem" }}
          scrollWheelZoom={true}
        >
          <FitBounds areasGeo={areasGeo} />
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {areasGeo.map((area) =>
            area.geometry ? (
              <AreaPolygon key={area.id} area={area} t={t} />
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
        </MapContainer>
      </div>
    </div>
  );
}
