import { useMemo } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";
import { useLanguage } from "./LanguageContext";

const SEVERITY_LABELS = {
  en: ["Unburned", "Low", "Moderate", "High", "Very High"],
  "pt-BR": ["Não queimado", "Baixa", "Moderada", "Alta", "Muito Alta"],
  fr: ["Non brûlé", "Faible", "Modéré", "Élevé", "Très élevé"],
};

function severityColor(value) {
  if (value < 1) return "#22c55e";
  if (value < 2) return "#facc15";
  if (value < 3) return "#f97316";
  if (value < 4) return "#ef4444";
  return "#7f1d1d";
}

function formatDate(dateStr) {
  const [year, month, day] = dateStr.split("-");
  return `${year}/${month}/${day}`;
}

function formatDateFull(dateStr) {
  const [year, month, day] = dateStr.split("-");
  return `${year}/${month}/${day}`;
}

export default function SeverityTrendWidget({ severityTrend }) {
  const { t, language } = useLanguage();

  const labels = SEVERITY_LABELS[language] || SEVERITY_LABELS.en;

  const chartData = useMemo(() => {
    if (!severityTrend || severityTrend.length === 0) return [];
    return severityTrend.map((item) => ({
      ...item,
      label: formatDate(item.date, language),
    }));
  }, [severityTrend, language]);

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload || !payload.length) return null;
    const data = payload[0].payload;
    const val = data.avg_severity;
    const severityIdx = Math.min(Math.floor(val), 4);
    return (
      <div
        className="p-2 rounded shadow-sm"
        style={{
          background: "var(--bg-card, #fff)",
          border: "1px solid var(--border-color, #e9ecef)",
          color: "var(--text-primary, #212529)",
        }}
      >
        <div className="fw-bold mb-1">{formatDateFull(data.date, language)}</div>
        <div>
          {t("dashboard.severityTrendAvg")}: <strong style={{ color: severityColor(val) }}>{val.toFixed(2)}</strong>
        </div>
        <div className="text-muted small">{labels[severityIdx]}</div>
      </div>
    );
  };

  if (!chartData || chartData.length === 0) {
    return (
      <div className="card h-100 shadow-sm">
        <div className="card-header">
          <h3 className="h5 mb-0">{t("dashboard.severityTrend")}
            <span className="info-tooltip">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
              <span className="info-tooltip-text">{t("dashboard.tooltipSeverityTrend")}</span>
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
        <h3 className="h5 mb-0">{t("dashboard.severityTrend")}
            <span className="info-tooltip">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
              <span className="info-tooltip-text">{t("dashboard.tooltipSeverityTrend")}</span>
            </span>
          </h3>
      </div>
      <div className="card-body" style={{ height: 300 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color, #e9ecef)" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 12, fill: "var(--text-secondary, #6c757d)" }}
            />
            <YAxis
              domain={[0, 4]}
              ticks={[0, 1, 2, 3, 4]}
              tickFormatter={(v) => labels[v] || v}
              tick={{ fontSize: 11, fill: "var(--text-secondary, #6c757d)" }}
              width={80}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={2} stroke="#f97316" strokeDasharray="5 5" strokeOpacity={0.5} />
            <Line
              type="monotone"
              dataKey="avg_severity"
              stroke="#ef4444"
              strokeWidth={2}
              dot={{ r: 4, fill: "#ef4444", stroke: "#fff", strokeWidth: 2 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
