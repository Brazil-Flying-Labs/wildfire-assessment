import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { arrayMove } from "@dnd-kit/sortable";
import { ALL_WIDGETS, DEFAULT_WIDGET_IDS } from "./widgetDefinitions";
import { DASHBOARD_STORAGE_KEY } from "../../constants/config";

const STORAGE_KEY = DASHBOARD_STORAGE_KEY;

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

export default function useDashboardLayout(backendProfile, onWidgetsChange) {
  const [visibleIds, setVisibleIds] = useState(
    () => readLayout() || DEFAULT_WIDGET_IDS
  );
  const [showAddModal, setShowAddModal] = useState(false);
  const backendSyncedRef = useRef(false);

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

  const updateLayout = useCallback(
    (newIds) => {
      setVisibleIds(newIds);
      saveLayout(newIds);
      onWidgetsChange?.(newIds);
    },
    [onWidgetsChange]
  );

  const handleDragEnd = useCallback(
    (event) => {
      const { active, over } = event;
      if (over && active.id !== over.id) {
        const oldIndex = visibleIds.indexOf(active.id);
        const newIndex = visibleIds.indexOf(over.id);
        updateLayout(arrayMove(visibleIds, oldIndex, newIndex));
        return true;
      }
      return false;
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

  return {
    visibleIds,
    showAddModal,
    setShowAddModal,
    handleDragEnd,
    handleRemove,
    handleAdd,
    hiddenWidgets,
  };
}
