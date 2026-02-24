export function downloadSeverityCsv(severityEntries) {
  if (!severityEntries.length) return;
  const header = "Severity,Area (ha),Percent\n";
  const rows = severityEntries
    .map(({ name, area, percent }) => {
      const areaVal = area !== null && area !== undefined ? area : "";
      const pctVal = percent !== null && percent !== undefined ? percent : "";
      return `"${name}",${areaVal},${pctVal}`;
    })
    .join("\n");
  const blob = new Blob([header + rows], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "severity_distribution.csv";
  link.click();
  URL.revokeObjectURL(url);
}
