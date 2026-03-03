import { useState, useRef, useEffect, useCallback } from "react";
import { DayPicker } from "react-day-picker";
import { format, parse } from "date-fns";
import { enUS, ptBR, fr } from "date-fns/locale";
import "react-day-picker/style.css";
import "./DateRangePicker.css";
import { useLanguage } from "../context/LanguageContext";

const LOCALE_MAP = { en: enUS, "pt-BR": ptBR, fr };

function toDate(isoStr) {
  if (!isoStr) return undefined;
  return parse(isoStr, "yyyy-MM-dd", new Date());
}

function toISO(date) {
  if (!date) return "";
  return format(date, "yyyy-MM-dd");
}

// step: "from" = picking pre-fire, "to" = picking post-fire
function DateRangePicker({ startDate, endDate, onRangeChange, label, startLabel, endLabel }) {
  const { language } = useLanguage();
  const locale = LOCALE_MAP[language] || enUS;
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState("from");
  const containerRef = useRef(null);

  const openPicker = useCallback((whichStep) => {
    setStep(whichStep);
    setOpen(true);
  }, []);

  const handleDayClick = useCallback(
    (day) => {
      const iso = toISO(day);
      if (step === "from") {
        // If picked from-date is after current end, clear end
        const clearEnd = endDate && iso > endDate;
        onRangeChange(iso, clearEnd ? "" : endDate);
        setStep("to");
      } else {
        // If picked to-date is before start, swap them
        if (startDate && iso < startDate) {
          onRangeChange(iso, startDate);
        } else {
          onRangeChange(startDate, iso);
        }
        setTimeout(() => setOpen(false), 150);
      }
    },
    [step, startDate, endDate, onRangeChange]
  );

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    const handleEscape = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  const formatDisplay = (isoStr, lbl) => {
    if (!isoStr) return lbl;
    const d = toDate(isoStr);
    return format(d, "dd MMM yyyy", { locale });
  };

  // Build the visual range highlight
  const fromDate = toDate(startDate);
  const toDateObj = toDate(endDate);
  const rangeSelected = fromDate && toDateObj ? { from: fromDate, to: toDateObj } : undefined;

  // Highlight the active step's date
  const activeDate = step === "from" ? fromDate : toDateObj;
  const defaultMonth = activeDate || fromDate || new Date();

  return (
    <div ref={containerRef} className="drp-container">
      {label ? <label className="form-label">{label}</label> : null}
      <div className="drp-trigger-row">
        <button
          type="button"
          className={`form-control drp-trigger-half text-start${open && step === "from" ? " drp-active" : ""}`}
          onClick={() => openPicker("from")}
        >
          <span className="drp-trigger-label">{startLabel}</span>
          <span className={startDate ? "drp-date-filled" : "drp-date-placeholder"}>
            {formatDisplay(startDate, "YYYY-MM-DD")}
          </span>
        </button>
        <span className="drp-arrow">→</span>
        <button
          type="button"
          className={`form-control drp-trigger-half text-start${open && step === "to" ? " drp-active" : ""}`}
          onClick={() => openPicker("to")}
        >
          <span className="drp-trigger-label">{endLabel}</span>
          <span className={endDate ? "drp-date-filled" : "drp-date-placeholder"}>
            {formatDisplay(endDate, "YYYY-MM-DD")}
          </span>
        </button>
      </div>
      {open ? (
        <div className={`drp-popover${step === "to" ? " drp-popover-end" : ""}`}>
          <div className="drp-step-indicator">
            <span className={step === "from" ? "drp-step-active" : "drp-step-dim"}>{startLabel}</span>
            <span className="drp-step-arrow">→</span>
            <span className={step === "to" ? "drp-step-active" : "drp-step-dim"}>{endLabel}</span>
          </div>
          <DayPicker
            mode="single"
            selected={activeDate}
            onSelect={handleDayClick}
            disabled={{ after: new Date() }}
            modifiers={rangeSelected ? { range_middle: { from: rangeSelected.from, to: rangeSelected.to } } : {}}
            modifiersClassNames={{ range_middle: "drp-in-range" }}
            numberOfMonths={1}
            defaultMonth={defaultMonth}
            locale={locale}
            showOutsideDays
          />
        </div>
      ) : null}
    </div>
  );
}

export default DateRangePicker;
