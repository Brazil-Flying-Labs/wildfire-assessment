import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  rectSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useLanguage } from "./LanguageContext";
import { ALL_WIDGETS, DEFAULT_WIDGET_IDS, getWidget } from "./widgetDefinitions";
import useIsDesktop from "./useIsDesktop";

const STORAGE_KEY = "dashboard_widgets";

function readLayout() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const ids = JSON.parse(raw);
    if (!Array.isArray(ids)) return null;
    const validIds = new Set(ALL_WIDGETS.map((w) => w.id));
    const filtered = ids.filter((id) => validIds.has(id));
    return filtered.length > 0 ? filtered : null;
  } catch {
    return null;
  }
}

function saveLayout(ids) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
}

function InfoTooltip({ text }) {
  return (
    <span className="info-tooltip">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="16" x2="12" y2="12" />
        <line x1="12" y1="8" x2="12.01" y2="8" />
      </svg>
      <span className="info-tooltip-text">{text}</span>
    </span>
  );
}

/* Icons for drag handle and remove button */
function GripIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <circle cx="8" cy="4" r="2" />
      <circle cx="16" cy="4" r="2" />
      <circle cx="8" cy="12" r="2" />
      <circle cx="16" cy="12" r="2" />
      <circle cx="8" cy="20" r="2" />
      <circle cx="16" cy="20" r="2" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

/* Column class based on widget group */
function colClass(widgetId) {
  const w = getWidget(widgetId);
  if (!w) return "col-12";
  if (w.group === "stats") return "col-6 col-md";
  if (w.group === "insights") return "col-md-4";
  return "col-12";
}

/* SortableWidget wrapper — provides drag handle + remove button */
function SortableWidget({ id, children, onRemove, t }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`${colClass(id)} widget-wrapper${isDragging ? " is-dragging" : ""}`}
    >
      <div className="widget-controls">
        <button
          className="widget-control-btn drag-handle"
          aria-label={t("dashboard.dragWidget")}
          {...attributes}
          {...listeners}
        >
          <GripIcon />
        </button>
        <button
          className="widget-control-btn"
          aria-label={t("dashboard.removeWidget")}
          onClick={() => onRemove(id)}
        >
          <CloseIcon />
        </button>
      </div>
      {children}
    </div>
  );
}

function Dashboard({ authorizedFetch, baseUrl, onAnalysisClick, backendProfile, onWidgetsChange }) {
  const { t } = useLanguage();
  const isDesktop = useIsDesktop();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  const [visibleIds, setVisibleIds] = useState(() => readLayout() || DEFAULT_WIDGET_IDS);
  const [showAddModal, setShowAddModal] = useState(false);
  const backendSyncedRef = useRef(false);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

  const loadDashboard = useCallback(async () => {
    if (!baseUrl) return;

    setLoading(true);
    setError(null);

    try {
      const response = await authorizedFetch(`${baseUrl}/dashboard/`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      } else {
        throw new Error(t("dashboard.errorLoading"));
      }
    } catch (err) {
      console.error("Error loading dashboard:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [authorizedFetch, baseUrl, t]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const formatDate = useCallback((dateString) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return date.toLocaleDateString();
  }, []);

  const formatNumber = useCallback((num) => {
    if (num === null || num === undefined) return "-";
    return Number(num).toLocaleString(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    });
  }, []);

  /* Sync layout from backend on first load (backend wins) */
  useEffect(() => {
    if (backendSyncedRef.current) return;
    const backendWidgets = backendProfile?.dashboard_widgets;
    if (backendWidgets && Array.isArray(backendWidgets)) {
      backendSyncedRef.current = true;
      const validIds = new Set(ALL_WIDGETS.map((w) => w.id));
      const filtered = backendWidgets.filter((id) => validIds.has(id));
      if (filtered.length > 0) {
        setVisibleIds(filtered);
        saveLayout(filtered);
      }
    }
  }, [backendProfile?.dashboard_widgets]);

  /* Persist layout changes to localStorage + backend */
  const updateLayout = useCallback((newIds) => {
    setVisibleIds(newIds);
    saveLayout(newIds);
    onWidgetsChange?.(newIds);
  }, [onWidgetsChange]);

  const handleDragEnd = useCallback(
    (event) => {
      const { active, over } = event;
      if (over && active.id !== over.id) {
        const oldIndex = visibleIds.indexOf(active.id);
        const newIndex = visibleIds.indexOf(over.id);
        updateLayout(arrayMove(visibleIds, oldIndex, newIndex));
      }
    },
    [visibleIds, updateLayout]
  );

  const handleRemove = useCallback(
    (id) => {
      updateLayout(visibleIds.filter((wid) => wid !== id));
    },
    [visibleIds, updateLayout]
  );

  const handleAdd = useCallback(
    (id) => {
      const newIds = [...visibleIds, id];
      updateLayout(newIds);
      /* Auto-close modal when no more hidden widgets */
      const allIds = new Set(ALL_WIDGETS.map((w) => w.id));
      const newVisible = new Set(newIds);
      if ([...allIds].every((wid) => newVisible.has(wid))) {
        setShowAddModal(false);
      }
    },
    [visibleIds, updateLayout]
  );

  const hiddenWidgets = useMemo(
    () => ALL_WIDGETS.filter((w) => !visibleIds.includes(w.id)),
    [visibleIds]
  );

  /* Render functions for each widget */
  const widgetRenderers = useMemo(() => ({
    total_areas: () => (
      <div className="card h-100 shadow-sm stat-card">
        <div className="card-body text-center">
          <div className="stat-icon mb-2">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
              <line x1="8" y1="2" x2="8" y2="18" />
              <line x1="16" y1="6" x2="16" y2="22" />
            </svg>
          </div>
          <h3 className="stat-value h2 mb-1">{formatNumber(stats?.total_areas)}</h3>
          <p className="stat-label text-muted mb-0 small">
            {t("dashboard.totalAreas")}
            <InfoTooltip text={t("dashboard.tooltipTotalAreas")} />
          </p>
        </div>
      </div>
    ),
    total_analyses: () => (
      <div className="card h-100 shadow-sm stat-card">
        <div className="card-body text-center">
          <div className="stat-icon mb-2">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <h3 className="stat-value h2 mb-1">{formatNumber(stats?.total_analyses)}</h3>
          <p className="stat-label text-muted mb-0 small">
            {t("dashboard.totalAnalyses")}
            <InfoTooltip text={t("dashboard.tooltipTotalAnalyses")} />
          </p>
        </div>
      </div>
    ),
    total_analyzed_ha: () => (
      <div className="card h-100 shadow-sm stat-card">
        <div className="card-body text-center">
          <div className="stat-icon mb-2 text-primary">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
            </svg>
          </div>
          <h3 className="stat-value h2 mb-1">{formatNumber(stats?.total_analyzed_ha)}</h3>
          <p className="stat-label text-muted mb-0 small">
            {t("dashboard.totalAnalyzedHa")}
            <InfoTooltip text={t("dashboard.tooltipAnalyzedHa")} />
          </p>
        </div>
      </div>
    ),
    total_burned_ha: () => (
      <div className="card h-100 shadow-sm stat-card">
        <div className="card-body text-center">
          <div className="stat-icon mb-2 text-danger">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
            </svg>
          </div>
          <h3 className="stat-value h2 mb-1">{formatNumber(stats?.total_burned_ha)}</h3>
          <p className="stat-label text-muted mb-0 small">
            {t("dashboard.totalBurnedHa")}
            <InfoTooltip text={t("dashboard.tooltipBurnedHa")} />
          </p>
        </div>
      </div>
    ),
    analyses_this_month: () => (
      <div className="card h-100 shadow-sm stat-card">
        <div className="card-body text-center">
          <div className="stat-icon mb-2 text-success">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
          </div>
          <h3 className="stat-value h2 mb-1">{formatNumber(stats?.analyses_this_month)}</h3>
          <p className="stat-label text-muted mb-0 small">
            {t("dashboard.analysesThisMonth")}
            <InfoTooltip text={t("dashboard.tooltipThisMonth")} />
          </p>
        </div>
      </div>
    ),
    avg_severity: () => (
      <div className="card h-100 shadow-sm stat-card">
        <div className="card-body text-center">
          <div className="stat-icon mb-2 text-warning">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z" />
            </svg>
          </div>
          <h3 className="stat-value h2 mb-1">
            {stats?.average_burn_severity != null
              ? formatNumber(stats.average_burn_severity)
              : "-"}
          </h3>
          <p className="stat-label text-muted mb-0 small">
            {t("dashboard.avgBurnSeverity")}
            <InfoTooltip text={t("dashboard.tooltipAvgSeverity")} />
          </p>
        </div>
      </div>
    ),
    most_analyzed: () => (
      <div className="card h-100 shadow-sm stat-card">
        <div className="card-body text-center">
          <div className="stat-icon mb-2 text-info">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
              <circle cx="12" cy="10" r="3" />
            </svg>
          </div>
          <h3 className="stat-value h4 mb-1">
            {stats?.most_analyzed_area?.area_name || "-"}
          </h3>
          <p className="stat-label text-muted mb-0 small">
            {stats?.most_analyzed_area
              ? `${stats.most_analyzed_area.run_count} ${t("dashboard.runs")}`
              : t("dashboard.mostAnalyzedArea")}
            <InfoTooltip text={t("dashboard.tooltipMostAnalyzed")} />
          </p>
        </div>
      </div>
    ),
    largest_fire: () => (
      <div className="card h-100 shadow-sm stat-card">
        <div className="card-body text-center">
          <div className="stat-icon mb-2 text-danger">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
            </svg>
          </div>
          <h3 className="stat-value h4 mb-1">
            {stats?.largest_fire?.area_name || "-"}
          </h3>
          <p className="stat-label text-muted mb-0 small">
            {stats?.largest_fire
              ? `${formatNumber(stats.largest_fire.burned_ha)} ha`
              : t("dashboard.largestFire")}
            <InfoTooltip text={t("dashboard.tooltipLargestFire")} />
          </p>
        </div>
      </div>
    ),
    recent_analyses: () => (
      <div className="card shadow-sm">
        <div className="card-header">
          <h3 className="h5 mb-0">{t("dashboard.recentAnalyses")}</h3>
        </div>
        <div className="card-body p-0">
          {!stats?.recent_analyses?.length ? (
            <div className="p-4 text-center text-muted">
              {t("dashboard.noAnalyses")}
            </div>
          ) : (
            <>
              {/* Desktop table */}
              <div className="table-responsive d-none d-md-block">
                <table className="table table-hover mb-0">
                  <thead className="table-light">
                    <tr>
                      <th scope="col">{t("dashboard.area")}</th>
                      <th scope="col">{t("dashboard.country")}</th>
                      <th scope="col">{t("dashboard.dates")}</th>
                      <th scope="col">{t("dashboard.areaHa")}</th>
                      <th scope="col">{t("dashboard.burnedHa")}</th>
                      <th scope="col" className="d-none d-lg-table-cell">{t("dashboard.runDate")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.recent_analyses.map((analysis) => (
                      <tr
                        key={analysis.id}
                        onClick={() => onAnalysisClick?.(analysis.id)}
                        style={{ cursor: onAnalysisClick ? "pointer" : "default" }}
                        role={onAnalysisClick ? "button" : undefined}
                        tabIndex={onAnalysisClick ? 0 : undefined}
                        onKeyDown={(e) => {
                          if (onAnalysisClick && (e.key === "Enter" || e.key === " ")) {
                            e.preventDefault();
                            onAnalysisClick(analysis.id);
                          }
                        }}
                      >
                        <td>{analysis.area_name}</td>
                        <td>{analysis.country_name || "-"}</td>
                        <td>
                          <small>
                            {formatDate(analysis.pre_fire_date)} → {formatDate(analysis.post_fire_date)}
                          </small>
                        </td>
                        <td>
                          {formatNumber(analysis.severity_data?.["Total Area"]?.area_ha)} ha
                        </td>
                        <td>
                          {formatNumber(analysis.total_burned_ha)} ha
                        </td>
                        <td className="d-none d-lg-table-cell">
                          {formatDate(analysis.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile cards */}
              <div className="d-md-none mobile-card-list">
                {stats.recent_analyses.map((analysis) => (
                  <div
                    key={analysis.id}
                    className="mobile-card"
                    onClick={() => onAnalysisClick?.(analysis.id)}
                    style={{ cursor: onAnalysisClick ? "pointer" : "default" }}
                    role={onAnalysisClick ? "button" : undefined}
                    tabIndex={onAnalysisClick ? 0 : undefined}
                    onKeyDown={(e) => {
                      if (onAnalysisClick && (e.key === "Enter" || e.key === " ")) {
                        e.preventDefault();
                        onAnalysisClick(analysis.id);
                      }
                    }}
                  >
                    <div className="mobile-card-header">
                      <span className="mobile-card-title">{analysis.area_name}</span>
                      <span className="mobile-card-badge">{analysis.country_name || "-"}</span>
                    </div>
                    <div className="mobile-card-body">
                      <div className="mobile-card-row">
                        <span className="mobile-card-label">{t("dashboard.dates")}</span>
                        <span>{formatDate(analysis.pre_fire_date)} → {formatDate(analysis.post_fire_date)}</span>
                      </div>
                      <div className="mobile-card-row">
                        <span className="mobile-card-label">{t("dashboard.areaHa")}</span>
                        <span>{formatNumber(analysis.severity_data?.["Total Area"]?.area_ha)} ha</span>
                      </div>
                      <div className="mobile-card-row">
                        <span className="mobile-card-label">{t("dashboard.burnedHa")}</span>
                        <span>{formatNumber(analysis.total_burned_ha)} ha</span>
                      </div>
                      <div className="mobile-card-row">
                        <span className="mobile-card-label">{t("dashboard.runDate")}</span>
                        <span>{formatDate(analysis.created_at)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    ),
  }), [stats, t, formatNumber, formatDate, onAnalysisClick]);

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center p-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">{t("common.loading")}</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <div className="alert alert-danger" role="alert">
          {error}
          <button
            type="button"
            className="btn btn-outline-danger btn-sm ms-3"
            onClick={loadDashboard}
          >
            {t("common.tryAgain")}
          </button>
        </div>
      </div>
    );
  }

  /* Render widget by id — used for both desktop (sortable) and mobile (static) */
  const renderWidget = (id) => {
    const renderer = widgetRenderers[id];
    return renderer ? renderer() : null;
  };

  /* Mobile: all widgets, original order, no DnD */
  if (!isDesktop) {
    return (
      <div className="dashboard p-4">
        <h2 className="h4 mb-4">{t("dashboard.title")}</h2>
        <div className="row g-3">
          {DEFAULT_WIDGET_IDS.map((id) => (
            <div key={id} className={colClass(id)}>
              {renderWidget(id)}
            </div>
          ))}
        </div>
      </div>
    );
  }

  /* Desktop: sortable widgets with DnD */
  return (
    <div className="dashboard p-4">
      <h2 className="h4 mb-4">{t("dashboard.title")}</h2>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext items={visibleIds} strategy={rectSortingStrategy}>
          <div className="row g-3">
            {visibleIds.map((id) => (
              <SortableWidget key={id} id={id} onRemove={handleRemove} t={t}>
                {renderWidget(id)}
              </SortableWidget>
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {/* FAB — show only when widgets are hidden */}
      {hiddenWidgets.length > 0 && (
        <button
          type="button"
          className="dashboard-fab"
          onClick={() => setShowAddModal(true)}
          aria-label={t("dashboard.addWidget")}
          title={t("dashboard.addWidget")}
        >
          <PlusIcon />
          <span className="fab-badge">{hiddenWidgets.length}</span>
        </button>
      )}

      {/* Add Widget Modal */}
      {showAddModal && (
        <>
          <div
            className="modal-backdrop fade show"
            onClick={() => setShowAddModal(false)}
          ></div>
          <div className="modal fade show d-block" tabIndex="-1" role="dialog">
            <div className="modal-dialog modal-dialog-centered" role="document">
              <div className="modal-content">
                <div className="modal-header">
                  <h5 className="modal-title">{t("dashboard.addWidget")}</h5>
                  <button
                    type="button"
                    className="btn-close"
                    onClick={() => setShowAddModal(false)}
                    aria-label={t("common.close")}
                  ></button>
                </div>
                <div className="modal-body">
                  <p className="text-muted small mb-3">
                    {t("dashboard.addWidgetDesc")}
                  </p>
                  {hiddenWidgets.length === 0 ? (
                    <p className="text-center text-muted">
                      {t("dashboard.noData")}
                    </p>
                  ) : (
                    <div className="list-group">
                      {hiddenWidgets.map((w) => (
                        <div
                          key={w.id}
                          className="list-group-item d-flex justify-content-between align-items-center"
                        >
                          <span>{t(w.titleKey)}</span>
                          <button
                            type="button"
                            className="btn btn-sm btn-primary"
                            onClick={() => handleAdd(w.id)}
                          >
                            {t("dashboard.add")}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default Dashboard;
