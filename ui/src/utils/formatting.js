export function formatDate(dateString) {
  if (!dateString) return "-";
  const date = new Date(dateString);
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}/${m}/${d}`;
}

export function formatDateFromIso(dateStr) {
  const [year, month, day] = dateStr.split("-");
  return `${year}/${month}/${day}`;
}

export function formatDateTime(dateString) {
  if (!dateString) return "-";
  const date = new Date(dateString);
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  const hh = String(date.getHours()).padStart(2, "0");
  const mm = String(date.getMinutes()).padStart(2, "0");
  return `${y}/${m}/${d} ${hh}:${mm}`;
}

export function formatNumber(num) {
  if (num === null || num === undefined) return "-";
  return Number(num).toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

export function formatLabel(key) {
  const withoutSuffix = key.replace(/_(jpg|tif)$/i, "");
  return withoutSuffix
    .split("_")
    .map((word) => {
      if (word.length <= 3) return word.toUpperCase();
      return word.charAt(0).toUpperCase() + word.slice(1);
    })
    .join(" ");
}

export function parseLocaleNumber(rawValue) {
  if (rawValue === null || rawValue === undefined) return Number.NaN;
  if (typeof rawValue === "number") return rawValue;
  if (typeof rawValue !== "string") return Number.NaN;

  const trimmed = rawValue.trim();
  if (!trimmed) return Number.NaN;

  const sanitized = trimmed
    .replace(/%$/g, "")
    .replace(/ha$/gi, "")
    .trim();

  if (!sanitized) return Number.NaN;

  let normalized = sanitized;

  if (sanitized.includes(",") && sanitized.includes(".")) {
    normalized = sanitized.replace(/\./g, "").replace(",", ".");
  } else if (sanitized.includes(",")) {
    normalized = sanitized.replace(",", ".");
  }

  const numeric = Number(normalized);

  if (Number.isNaN(numeric)) {
    return Number.NaN;
  }

  return numeric;
}

export function formatAreaValue(value) {
  if (value === null || value === undefined || value === "") return "";

  const numericValue = parseLocaleNumber(value);

  if (Number.isNaN(numericValue)) {
    return typeof value === "string" ? value : `${value}`;
  }

  const formatted = numericValue.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return `${formatted} ha`;
}

export function formatPercentValue(value) {
  if (value === null || value === undefined || value === "") return "";

  const numericValue = parseLocaleNumber(value);

  if (Number.isNaN(numericValue)) {
    return typeof value === "string" ? value : `${value}`;
  }

  const formatted = numericValue.toLocaleString("pt-BR", {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  });

  return `${formatted}%`;
}
