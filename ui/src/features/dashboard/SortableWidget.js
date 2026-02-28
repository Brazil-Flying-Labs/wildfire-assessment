import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

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
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="3"
      strokeLinecap="round"
    >
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function SortableWidget({
  id,
  colClassName,
  children,
  onRemove,
  t,
  isDesktop,
  jiggle,
  registerRef,
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const cls = [colClassName, "widget-wrapper"];
  if (isDragging) cls.push("is-dragging");
  if (jiggle && !isDragging) cls.push("is-jiggling");
  if (!isDesktop) cls.push("touch-draggable");

  // Combined ref handler
  const combinedRef = (node) => {
    setNodeRef(node);
    if (registerRef) registerRef(id, node);
  };

  return (
    <div
      ref={combinedRef}
      style={style}
      className={cls.join(" ")}
      {...(!isDesktop ? { ...attributes, ...listeners } : {})}
    >
      <div className="widget-controls">
        {isDesktop && (
          <button
            className="widget-control-btn drag-handle"
            aria-label={t("dashboard.dragWidget")}
            {...attributes}
            {...listeners}
          >
            <GripIcon />
          </button>
        )}
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

export default SortableWidget;
