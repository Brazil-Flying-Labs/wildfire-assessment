function KebabMenu({ items, isOpen, onToggle, onClose, ariaLabel }) {
  return (
    <div className="kebab-menu">
      <button
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
      {isOpen && (
        <>
          <div className="kebab-backdrop" onClick={onClose}></div>
          <div className="kebab-dropdown">
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
