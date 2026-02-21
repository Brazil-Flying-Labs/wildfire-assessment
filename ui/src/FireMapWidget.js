import { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
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

function burnedRadius(totalBurnedHa) {
  if (totalBurnedHa <= 0) return 6;
  if (totalBurnedHa < 50) return 8;
  if (totalBurnedHa < 200) return 10;
  if (totalBurnedHa < 1000) return 13;
  return 16;
}

function FitBounds({ areasGeo }) {
  const map = useMap();
  useEffect(() => {
    if (!areasGeo || areasGeo.length === 0) return;
    const bounds = L.latLngBounds(areasGeo.map((a) => [a.lat, a.lng]));
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 12 });
  }, [map, areasGeo]);
  return null;
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
          {areasGeo.map((area) => (
            <CircleMarker
              key={area.id}
              center={[area.lat, area.lng]}
              radius={burnedRadius(area.total_burned_ha)}
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
                  <>{t("dashboard.fireMapLastAnalysis")}: {area.last_analysis_date}</>
                )}
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
