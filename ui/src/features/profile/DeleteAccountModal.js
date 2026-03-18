import { useCallback, useState } from "react";
import { useLanguage } from "../../context/LanguageContext";

function DeleteAccountModal({ onConfirm, onClose }) {
  const { t } = useLanguage();
  const [inputValue, setInputValue] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState(null);

  const confirmWord = t("profile.deleteAccountConfirmWord");
  const isMatch = inputValue.trim().toLowerCase() === confirmWord.toLowerCase();

  const handleDelete = useCallback(async () => {
    if (!isMatch) return;
    setDeleting(true);
    setError(null);
    try {
      await onConfirm();
    } catch {
      setError(t("profile.deleteAccountError"));
      setDeleting(false);
    }
  }, [isMatch, onConfirm, t]);

  return (
    <>
      <div className="modal-backdrop show" />
      <div className="modal show d-block" tabIndex="-1" role="dialog">
        <div className="modal-dialog modal-dialog-centered" role="document">
          <div className="modal-content">
            <div className="modal-header border-danger">
              <h5 className="modal-title text-danger">
                {t("profile.deleteAccountTitle")}
              </h5>
              <button
                type="button"
                className="btn-close"
                onClick={onClose}
                disabled={deleting}
                aria-label={t("common.close")}
              />
            </div>
            <div className="modal-body">
              <p>{t("profile.deleteAccountWarning")}</p>
              {error && <div className="alert alert-danger">{error}</div>}
              <label className="form-label">
                {t("profile.deleteAccountConfirmLabel", {
                  word: confirmWord,
                })}
              </label>
              <input
                type="text"
                className="form-control"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                disabled={deleting}
                autoFocus
              />
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={onClose}
                disabled={deleting}
              >
                {t("profile.deleteAccountCancel")}
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={handleDelete}
                disabled={!isMatch || deleting}
              >
                {deleting
                  ? t("profile.deleteAccountDeleting")
                  : t("profile.deleteAccountButton")}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default DeleteAccountModal;
