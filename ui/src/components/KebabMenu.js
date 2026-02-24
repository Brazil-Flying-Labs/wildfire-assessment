import { useRef, useEffect, useState, useCallback } from "react";

function KebabMenu({ items, isOpen, onToggle, onClose, ariaLabel }) {
  const triggerRef = useRef(null);
  const [position, setPosition] = useState(null);

  const updatePosition = useCallback(() => {
    if (!triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const dropdownHeight = items.length * 40 + 8; // approximate height
    const spaceBelow = window.innerHeight - rect.bottom;
    const openUpward = spaceBelow < dropdownHeight;

    setPosition({
      top: openUpward ? rect.top - dropdownHeight : rect.bottom + 4,
      left: rect.right - 140, // align right edge with button
    });
  }, [items.length]);

  useEffect(() => {
    if (isOpen) updatePosition();
  }, [isOpen, updatePosition]);

  return (
    <div className="kebab-menu">
      <button
        ref={triggerRef}
        type="button"
        className="btn btn-link text-secondary p-1 kebab-trigger"
        onClick={onToggle}
        aria-label={ariaLabel}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
          <circle cx="12" cy="5" r="2" />
          <circle cx="12" cy="12" r="2" />
          <circle cx="12" cy="19" r="2" />
        </svg>
      </button>
      {isOpen && position && (
        <>
          <div className="kebab-backdrop" onClick={onClose}></div>
          <div
            className="kebab-dropdown"
            style={{ top: position.top, left: position.left }}
          >
            {items.map((item, i) => (
              <button
                key={i}
                type="button"
                className={`kebab-item ${item.className || ""}`}
                onClick={item.onClick}
              >
                {item.icon}
                {item.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default KebabMenu;
