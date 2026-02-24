import InfoTooltip from "../../components/InfoTooltip";

function StatCard({ icon, iconColor, value, label, tooltip }) {
  return (
    <div className="card h-100 shadow-sm stat-card">
      <div className="card-body text-center">
        <div className={`stat-icon mb-2 ${iconColor || ""}`}>{icon}</div>
        <h3 className="stat-value h2 mb-1">{value}</h3>
        <p className="stat-label text-muted mb-0 small">
          <span className="stat-label-text">{label}</span>
          <InfoTooltip text={tooltip} />
        </p>
      </div>
    </div>
  );
}

export default StatCard;
