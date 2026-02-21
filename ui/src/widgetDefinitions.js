export const ALL_WIDGETS = [
  { id: "total_areas", titleKey: "dashboard.totalAreas", group: "stats" },
  { id: "total_analyses", titleKey: "dashboard.totalAnalyses", group: "stats" },
  { id: "total_analyzed_ha", titleKey: "dashboard.totalAnalyzedHa", group: "stats" },
  { id: "total_burned_ha", titleKey: "dashboard.totalBurnedHa", group: "stats" },
  { id: "analyses_this_month", titleKey: "dashboard.analysesThisMonth", group: "stats" },
  { id: "avg_severity", titleKey: "dashboard.avgBurnSeverity", group: "insights" },
  { id: "most_analyzed", titleKey: "dashboard.mostAnalyzedArea", group: "insights" },
  { id: "largest_fire", titleKey: "dashboard.largestFire", group: "insights" },
  { id: "recent_analyses", titleKey: "dashboard.recentAnalyses", group: "table" },
];

export const DEFAULT_WIDGET_IDS = ALL_WIDGETS.map((w) => w.id);

const widgetMap = Object.fromEntries(ALL_WIDGETS.map((w) => [w.id, w]));
export const getWidget = (id) => widgetMap[id];
