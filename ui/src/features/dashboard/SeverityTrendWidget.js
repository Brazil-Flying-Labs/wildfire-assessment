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
import { useLanguage } from "../../context/LanguageContext";
import InfoTooltip from "../../components/InfoTooltip";
import { SEVERITY_CHART_LABELS, severityChartColor } from "../../constants/severity";
import { formatDateFromIso } from "../../utils/formatting";

export default function SeverityTrendWidget({ severityTrend }) {
  const { t, language } = useLanguage();

  const labels = SEVERITY_CHART_LABELS[language] || SEVERITY_CHART_LABELS.en;

  const chartData = useMemo(() => {
    if (!severityTrend || severityTrend.length === 0) return [];
    /* Group per-run data points by local date */
    const daily = {};
    for (const item of severityTrend) {
      const d = new Date(item.created_at);
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, "0");
      const day = String(d.getDate()).padStart(2, "0");
      const key = `${y}-${m}-${day}`;
      if (!daily[key]) daily[key] = { sum: 0, count: 0 };
      daily[key].sum += item.avg_severity;
      daily[key].count += 1;
    }
    return Object.keys(daily)
      .sort()
      .map((key) => ({
        date: key,
        avg_severity: parseFloat((daily[key].sum / daily[key].count).toFixed(2)),
        label: formatDateFromIso(key),
      }));
  }, [severityTrend]);

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
        <div className="fw-bold mb-1">{formatDateFromIso(data.date, language)}</div>
        <div>
          {t("dashboard.severityTrendAvg")}: <strong style={{ color: severityChartColor(val) }}>{val.toFixed(2)}</strong>
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
            <InfoTooltip text={t("dashboard.tooltipSeverityTrend")} />
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
            <InfoTooltip text={t("dashboard.tooltipSeverityTrend")} />
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
