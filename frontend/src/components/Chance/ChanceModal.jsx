import React, { useEffect } from "react";
import "./ChanceModal.css";

export default function ChanceModal({ open, text, delta, onClose }) {
  useEffect(() => {
    if (!open) return;

    const onKeyDown = (e) => {
      if (e.key === "Escape") onClose?.();
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const sign = typeof delta === "number" ? (delta >= 0 ? "+" : "−") : null;
  const absDelta = typeof delta === "number" ? Math.abs(delta) : null;

  return (
    <div className="chance-backdrop" onClick={onClose}>
      <div className="chance-wrap">
        {/* glow слой */}
        <div className="chance-glow" />

        <div
          className="chance-card"
          role="dialog"
          aria-modal="true"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="chance-header">
            <div className="chance-title">
              <span className="chance-chip">★</span>
              <span>CHANCE</span>
            </div>

            <button className="chance-close" onClick={onClose} aria-label="Close">
              ✕
            </button>
          </div>

          <div className="chance-body">
            <div className="chance-shine" />

            <div className="chance-main">
              <div className="chance-text">{text}</div>

              {typeof delta === "number" && (
                <div className={`chance-delta ${delta >= 0 ? "pos" : "neg"}`}>
                  <span className="chance-delta-sign">{sign}</span>
                  <span className="chance-delta-num">{absDelta}</span>
                  <span className="chance-delta-unit">FC</span>
                </div>
              )}

              <div className="chance-hint">
                Закрой карточку, чтобы продолжить ход.
              </div>
            </div>
          </div>

          <div className="chance-footer">
            <button className="chance-btn" onClick={onClose}>
              CONTINUE
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
