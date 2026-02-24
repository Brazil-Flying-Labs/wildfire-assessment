export const SEVERITY_COLORS = {
  "Unburned": "#28a745",
  "Low Severity": "#ffc107",
  "Moderate Severity": "#fd7e14",
  "High Severity": "#dc3545",
  "Very High Severity": "#6f42c1",
};

export const SEVERITY_ORDER = [
  "Unburned",
  "Low Severity",
  "Moderate Severity",
  "High Severity",
  "Very High Severity",
  "Total Burned Area",
  "Total Area",
];

export function getSeverityTranslations(t) {
  return {
    "Unburned": t("severity.unburned"),
    "Low Severity": t("severity.low"),
    "Moderate Severity": t("severity.moderate"),
    "High Severity": t("severity.high"),
    "Very High Severity": t("severity.veryHigh"),
    "Total Burned Area": t("severity.totalBurned"),
    "Total Area": t("severity.totalArea"),
  };
}

export const SEVERITY_CHART_LABELS = {
  en: ["Unburned", "Low", "Moderate", "High", "Very High"],
  "pt-BR": ["Não queimado", "Baixa", "Moderada", "Alta", "Muito Alta"],
  fr: ["Non brûlé", "Faible", "Modéré", "Élevé", "Très élevé"],
};

export function burnedColor(totalBurnedHa) {
  if (totalBurnedHa <= 0) return "#22c55e";
  if (totalBurnedHa < 50) return "#facc15";
  if (totalBurnedHa < 200) return "#f97316";
  if (totalBurnedHa < 1000) return "#ef4444";
  return "#7f1d1d";
}

export function severityChartColor(value) {
  if (value < 1) return "#22c55e";
  if (value < 2) return "#facc15";
  if (value < 3) return "#f97316";
  if (value < 4) return "#ef4444";
  return "#7f1d1d";
}

export function parseSeverityData(mapData) {
  if (!mapData) return [];

  try {
    const parsed =
      typeof mapData === "string" ? JSON.parse(mapData) : mapData || {};
    const entries = Object.entries(parsed).map(([name, metrics]) => ({
      name,
      area: metrics?.area_ha ?? metrics?.area ?? null,
      percent: metrics?.ratio_percent ?? metrics?.percent ?? null,
    }));

    entries.sort((a, b) => {
      const orderA = SEVERITY_ORDER.indexOf(a.name);
      const orderB = SEVERITY_ORDER.indexOf(b.name);
      if (orderA === -1 && orderB === -1) {
        return a.name.localeCompare(b.name);
      }
      if (orderA === -1) return 1;
      if (orderB === -1) return -1;
      return orderA - orderB;
    });

    return entries;
  } catch (error) {
    console.error("Failed to parse severity data:", error);
    return [];
  }
}
