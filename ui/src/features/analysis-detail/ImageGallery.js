function ImageGallery({ imageEntries, t }) {
  return (
    <div className="card shadow-sm mb-4">
      <div className="card-header">
        <h3 className="h5 mb-0">{t("analysisDetail.images")}</h3>
      </div>
      <div className="card-body">
        {imageEntries.length > 0 ? (
          <div className="row g-3">
            {imageEntries.map(({ label, url }) => (
              <div className="col-md-6 col-lg-4" key={label}>
                <div className="text-center">
                  <div className="fw-semibold mb-2">{label}</div>
                  <a href={url} target="_blank" rel="noopener noreferrer">
                    <img
                      src={url}
                      alt={label}
                      className="img-fluid rounded border"
                      style={{ height: "300px", objectFit: "contain" }}
                    />
                  </a>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-muted mb-0">{t("analysisDetail.noImages")}</p>
        )}
      </div>
    </div>
  );
}

export default ImageGallery;
