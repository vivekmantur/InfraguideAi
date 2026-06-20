import type { ReactNode } from "react";
import { FileText } from "lucide-react";

export function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
    </div>
  );
}

export function RequiredLabel({ children, htmlFor }: { children: ReactNode; htmlFor?: string }) {
  return (
    <span className="field-label" {...(htmlFor ? { id: `${htmlFor}Label` } : {})}>
      {children}
      <span className="required-star" aria-hidden="true">*</span>
    </span>
  );
}

export function FieldError({ message }: { message: string }) {
  return <span className="field-error">{message}</span>;
}

export function Select({
  label,
  value,
  values,
  placeholder,
  error,
  onChange,
}: {
  label: string;
  value: string;
  values: string[];
  placeholder: string;
  error?: string;
  onChange: (value: string) => void;
}) {
  return (
    <label>
      <RequiredLabel>{label}</RequiredLabel>
      <select className={`input ${error ? "input-error" : ""}`} value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="" disabled>
          {placeholder}
        </option>
        {values.map((item) => (
          <option key={item} value={item}>
            {item}
          </option>
        ))}
      </select>
      {error && <FieldError message={error} />}
    </label>
  );
}

export function Panel({ title, children, className = "", action }: { title: string; children: ReactNode; className?: string; action?: ReactNode }) {
  return (
    <section className={`report-card ${className}`}>
      <div className="report-card-header">
        <h3 className="report-card-title">
          <FileText size={18} className="report-card-icon" />
          {title}
        </h3>
        {action}
      </div>
      {children}
    </section>
  );
}

export function KeyValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="key-value-row">
      <span className="key-value-label">{label}</span>
      <span className="key-value-value">{value}</span>
    </div>
  );
}

export function List({ items = [], numbered = false }: { items?: string[]; numbered?: boolean }) {
  const ListTag = numbered ? "ol" : "ul";
  return (
    <ListTag className={`content-list ${numbered ? "content-list-numbered" : "content-list-bulleted"}`}>
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ListTag>
  );
}
