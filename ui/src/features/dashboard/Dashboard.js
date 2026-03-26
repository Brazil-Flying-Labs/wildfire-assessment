import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  rectSortingStrategy,
} from "@dnd-kit/sortable";
import { useLanguage } from "../../context/LanguageContext";
import { getWidget } from "./widgetDefinitions";
import useIsDesktop from "../../hooks/useIsDesktop";
import { formatNumber } from "../../utils/formatting";
import LongPressSensor from "../../LongPressSensor";
import FireMapWidget from "./FireMapWidget";
import SeverityTrendWidget from "./SeverityTrendWidget";
import StatCard from "./StatCard";
import SortableWidget from "./SortableWidget";
import RecentAnalysesWidget from "./RecentAnalysesWidget";
import AddWidgetModal from "./AddWidgetModal";
import useDashboardLayout from "./useDashboardLayout";

/* Column class based on widget group */
function baseColClass(widgetId) {
  const w = getWidget(widgetId);
  if (!w) return "col-12";
  if (w.group === "stats") return "col-6 col-md";
  if (w.group === "insights") return "col-md-4";
  return "col-12";
}

function buildColClasses(ids) {
  return ids.map(baseColClass);
}

function PlusIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function Dashboard({ authorizedFetch, baseUrl, onAnalysisClick, backendProfile, onWidgetsChange, refreshKey }) {
  const { t } = useLanguage();
  const isDesktop = useIsDesktop();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  const [openMenuId, setOpenMenuId] = useState(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);
  const [deletingAnalysis, setDeletingAnalysis] = useState(false);
  const [isDraggingAny, setIsDraggingAny] = useState(false);
  const [activeId, setActiveId] = useState(null);
  const [activeRect, setActiveRect] = useState(null);
  const widgetRefs = useRef({});
  const [mapGeneration, setMapGeneration] = useState(0);
  const hasLoadedRef = useRef(false);

  // Paginated analyses state
  const [analysesList, setAnalysesList] = useState([]);
  const [analysesPage, setAnalysesPage] = useState(1);
  const [analysesCount, setAnalysesCount] = useState(0);
  const [analysesLoading, setAnalysesLoading] = useState(false);
  const analysesPageSize = 10;

  const {
    visibleIds,
    showAddModal,
    setShowAddModal,
    handleDragEnd,
    handleRemove,
    handleAdd,
    hiddenWidgets,
  } = useDashboardLayout(backendProfile, onWidgetsChange);

  const pointerSensor = useSensor(PointerSensor, { activationConstraint: { distance: 8 } });
  const longPressSensor = useSensor(LongPressSensor, { activationConstraint: { delay: 200, tolerance: 5 } });
  const sensors = useSensors(isDesktop ? pointerSensor : longPressSensor);

  const loadAnalyses = useCallback(async (page = 1) => {
    if (!baseUrl) return;
    setAnalysesLoading(true);
    try {
      const response = await authorizedFetch(
        `${baseUrl}/analysis_run/?page=${page}`
      );
      if (response.ok) {
        const data = await response.json();
        setAnalysesList(data.results || []);
        setAnalysesCount(data.count || 0);
        setAnalysesPage(page);
      }
    } catch (err) {
      console.error("Error loading analyses:", err);
    } finally {
      setAnalysesLoading(false);
    }
  }, [authorizedFetch, baseUrl]);

  const loadDashboard = useCallback(async () => {
    if (!baseUrl) return;

    if (hasLoadedRef.current) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const response = await authorizedFetch(`${baseUrl}/dashboard/`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
        hasLoadedRef.current = true;
      } else {
        throw new Error(t("dashboard.errorLoading"));
      }
    } catch (err) {
      console.error("Error loading dashboard:", err);
      setError(err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [authorizedFetch, baseUrl, t]);

  useEffect(() => {
    loadDashboard();
    loadAnalyses(1);
  }, [loadDashboard, loadAnalyses]);

  const prevRefreshKeyRef = useRef(refreshKey);
  useEffect(() => {
    if (prevRefreshKeyRef.current !== refreshKey) {
      prevRefreshKeyRef.current = refreshKey;
      loadDashboard();
      loadAnalyses(1);
    }
  }, [refreshKey, loadDashboard, loadAnalyses]);

  const handleDeleteAnalysis = useCallback(async (analysisId) => {
    setDeletingAnalysis(true);
    try {
      const response = await authorizedFetch(`${baseUrl}/analysis_run/${analysisId}/`, {
        method: "DELETE",
      });
      if (response.ok || response.status === 204) {
        setDeleteConfirmId(null);
        loadDashboard();
        loadAnalyses(analysesPage);
      } else {
        alert(t("dashboard.errorDeletingAnalysis"));
      }
    } catch {
      alert(t("dashboard.errorDeletingAnalysis"));
    } finally {
      setDeletingAnalysis(false);
    }
  }, [authorizedFetch, baseUrl, loadDashboard, loadAnalyses, analysesPage, t]);

  const toggleMenu = useCallback((id) => {
    setOpenMenuId((prev) => (prev === id ? null : id));
  }, []);

  const closeMenu = useCallback(() => {
    setOpenMenuId(null);
  }, []);

  const onDragEnd = useCallback(
    (event) => {
      setIsDraggingAny(false);
      if (handleDragEnd(event)) {
        setMapGeneration((g) => g + 1);
      }
    },
    [handleDragEnd]
  );

  /* Render functions for each widget */
  const widgetRenderers = useMemo(() => ({
    total_areas: () => (
      <StatCard
        icon={<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" /><line x1="8" y1="2" x2="8" y2="18" /><line x1="16" y1="6" x2="16" y2="22" /></svg>}
        value={formatNumber(stats?.total_areas)}
        label={t("dashboard.totalAreas")}
        tooltip={t("dashboard.tooltipTotalAreas")}
      />
    ),
    total_analyses: () => (
      <StatCard
        icon={<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" /></svg>}
        value={formatNumber(stats?.total_analyses)}
        label={t("dashboard.totalAnalyses")}
        tooltip={t("dashboard.tooltipTotalAnalyses")}
      />
    ),
    total_analyzed_ha: () => (
      <StatCard
        icon={<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" /></svg>}
        iconColor="text-primary"
        value={formatNumber(stats?.total_analyzed_ha)}
        label={t("dashboard.totalAnalyzedHa")}
        tooltip={t("dashboard.tooltipAnalyzedHa")}
      />
    ),
    total_burned_ha: () => (
      <StatCard
        icon={<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" /></svg>}
        iconColor="text-danger"
        value={formatNumber(stats?.total_burned_ha)}
        label={t("dashboard.totalBurnedHa")}
        tooltip={t("dashboard.tooltipBurnedHa")}
      />
    ),
    analyses_this_month: () => (
      <StatCard
        icon={<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /></svg>}
        iconColor="text-success"
        value={formatNumber(stats?.analyses_this_month)}
        label={t("dashboard.analysesThisMonth")}
        tooltip={t("dashboard.tooltipThisMonth")}
      />
    ),
    avg_severity: () => (
      <StatCard
        icon={<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z" /></svg>}
        iconColor="text-warning"
        value={stats?.average_burn_severity != null ? formatNumber(stats.average_burn_severity) : "-"}
        label={t("dashboard.avgBurnSeverity")}
        tooltip={t("dashboard.tooltipAvgSeverity")}
      />
    ),
    most_analyzed: () => (
      <StatCard
        icon={<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" /></svg>}
        iconColor="text-info"
        value={stats?.most_analyzed_area?.area_name || "-"}
        label={stats?.most_analyzed_area
          ? `${stats.most_analyzed_area.run_count} ${t("dashboard.runs")}`
          : t("dashboard.mostAnalyzedArea")}
        tooltip={t("dashboard.tooltipMostAnalyzed")}
      />
    ),
    largest_fire: () => (
      <StatCard
        icon={<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" /></svg>}
        iconColor="text-danger"
        value={stats?.largest_fire?.area_name || "-"}
        label={stats?.largest_fire
          ? `${formatNumber(stats.largest_fire.burned_ha)} ha`
          : t("dashboard.largestFire")}
        tooltip={t("dashboard.tooltipLargestFire")}
      />
    ),
    recent_analyses: () => (
      <RecentAnalysesWidget
        analyses={analysesList}
        t={t}
        onAnalysisClick={onAnalysisClick}
        deleteConfirmId={deleteConfirmId}
        setDeleteConfirmId={setDeleteConfirmId}
        deletingAnalysis={deletingAnalysis}
        handleDeleteAnalysis={handleDeleteAnalysis}
        openMenuId={openMenuId}
        toggleMenu={toggleMenu}
        closeMenu={closeMenu}
        currentPage={analysesPage}
        totalPages={Math.ceil(analysesCount / analysesPageSize)}
        onPageChange={loadAnalyses}
        analysesLoading={analysesLoading}
      />
    ),
    fire_map: () => (
      <FireMapWidget
        key={mapGeneration}
        areasGeo={stats?.areas_geo}
        authorizedFetch={authorizedFetch}
        baseUrl={baseUrl}
      />
    ),
    severity_trend: () => (
      <SeverityTrendWidget severityTrend={stats?.severity_trend} />
    ),
  }), [stats, t, onAnalysisClick, deleteConfirmId, deletingAnalysis, handleDeleteAnalysis, openMenuId, toggleMenu, closeMenu, mapGeneration, authorizedFetch, baseUrl, analysesList, analysesPage, analysesCount, analysesPageSize, loadAnalyses, analysesLoading]);

  if (loading) {
    const colClasses = buildColClasses(visibleIds);
    return (
      <div className="dashboard p-4">
        <div className="skeleton-text skeleton-title mb-4" />
        <div className="row g-3">
          {visibleIds.map((id, idx) => {
            const w = getWidget(id);
            const group = w?.group || "stats";
            return (
              <div key={id} className={colClasses[idx]}>
                {group === "stats" || group === "insights" ? (
                  <div className="card h-100 shadow-sm skeleton-card">
                    <div className="card-body text-center py-4">
                      <div className="skeleton-circle mx-auto mb-3" />
                      <div className="skeleton-text skeleton-value mx-auto mb-2" />
                      <div className="skeleton-text skeleton-label mx-auto" />
                    </div>
                    <div className="skeleton-spinner">
                      <div className="spinner-border spinner-border-sm text-primary" role="status" />
                    </div>
                  </div>
                ) : group === "table" ? (
                  <div className="card shadow-sm skeleton-card">
                    <div className="card-header">
                      <div className="skeleton-text skeleton-header-text" />
                    </div>
                    <div className="card-body p-0">
                      {[0, 1, 2, 3, 4].map((r) => (
                        <div key={r} className="skeleton-table-row" />
                      ))}
                    </div>
                    <div className="skeleton-spinner">
                      <div className="spinner-border text-primary" role="status" />
                    </div>
                  </div>
                ) : (
                  <div className="card shadow-sm skeleton-card">
                    <div className="card-header">
                      <div className="skeleton-text skeleton-header-text" />
                    </div>
                    <div className="card-body">
                      <div className="skeleton-block" />
                    </div>
                    <div className="skeleton-spinner">
                      <div className="spinner-border text-primary" role="status" />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
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

  const renderWidget = (id) => {
    const renderer = widgetRenderers[id];
    if (!renderer) return null;
    return (
      <div className="widget-refresh-wrapper">
        {renderer()}
        {refreshing && (
          <div className="widget-refresh-overlay">
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">{t("common.loading")}</span>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="dashboard p-4">
      <h2 className="h4 mb-4">{t("dashboard.title")}</h2>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={(event) => {
          setIsDraggingAny(true);
          const id = event.active.id;
          setActiveId(id);
          // Capture dimensions from the ref
          const el = widgetRefs.current[id];
          if (el) {
            const rect = el.getBoundingClientRect();
            setActiveRect({ width: rect.width, height: rect.height });
          }
        }}
        onDragEnd={(event) => {
          onDragEnd(event);
          setActiveId(null);
          setActiveRect(null);
        }}
        onDragCancel={() => {
          setIsDraggingAny(false);
          setActiveId(null);
          setActiveRect(null);
        }}
      >
        <SortableContext items={visibleIds} strategy={rectSortingStrategy}>
          <div className="row g-3">
            {(() => {
              const colClasses = buildColClasses(visibleIds);
              return visibleIds.map((id, idx) => (
                <SortableWidget key={id} id={id} colClassName={colClasses[idx]} onRemove={handleRemove} t={t} isDesktop={isDesktop} jiggle={isDraggingAny} registerRef={(wid, node) => { widgetRefs.current[wid] = node; }} draggedRect={activeId === id ? activeRect : null}>
                  {renderWidget(id)}
                </SortableWidget>
              ));
            })()}
          </div>
        </SortableContext>
        <DragOverlay>
          {activeId ? (
            <div
              className="widget-wrapper drag-overlay"
              style={activeRect ? { width: activeRect.width, height: activeRect.height } : undefined}
            >
              {renderWidget(activeId)}
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

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

      {showAddModal && (
        <AddWidgetModal
          hiddenWidgets={hiddenWidgets}
          onAdd={handleAdd}
          onClose={() => setShowAddModal(false)}
          t={t}
        />
      )}
    </div>
  );
}

export default Dashboard;
