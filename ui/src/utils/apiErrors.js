export function formatApiErrors(errorData, t) {
  let errorMessage = errorData.detail || errorData.error;

  if (!errorMessage && typeof errorData === "object") {
    const errorParts = [];
    for (const [field, errors] of Object.entries(errorData)) {
      const errorList = Array.isArray(errors) ? errors : [errors];
      const fieldLabel = field === "geojson" ? t("areas.geojsonFile") : field;
      errorParts.push(`${fieldLabel}: ${errorList.join(", ")}`);
    }
    errorMessage = errorParts.join("\n");
  }

  return errorMessage;
}
