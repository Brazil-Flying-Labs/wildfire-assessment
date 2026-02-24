function DeleteConfirmation({
  onConfirm,
  onCancel,
  confirming,
  confirmLabel,
  cancelLabel,
  className = "",
}) {
  return (
    <div className={`d-flex gap-1 ${className}`}>
      <button
        type="button"
        className="btn btn-danger btn-sm"
        onClick={onConfirm}
        disabled={confirming}
      >
        {confirming ? (
          <span
            className="spinner-border spinner-border-sm"
            role="status"
            aria-hidden="true"
          ></span>
        ) : (
          confirmLabel
        )}
      </button>
      <button
        type="button"
        className="btn btn-outline-secondary btn-sm"
        onClick={onCancel}
        disabled={confirming}
      >
        {cancelLabel}
      </button>
    </div>
  );
}

export default DeleteConfirmation;
