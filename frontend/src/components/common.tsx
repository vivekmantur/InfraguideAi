import type { ReactNode } from "react";
import { FileText } from "lucide-react";

export function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-24 rounded-md border border-ink/10 bg-cloud px-3 py-2">
      <div className="text-[0.68rem] font-semibold uppercase tracking-wide text-ink/55">{label}</div>
      <div className="mt-0.5 text-base font-bold text-ink">{value}</div>
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
    <section className={`rounded-lg border border-ink/10 p-4 ${className}`}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h3 className="flex items-center gap-2 text-lg font-semibold">
          <FileText size={18} className="text-signal" />
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
    <div className="mb-3 flex items-start justify-between gap-4 border-b border-ink/10 pb-2 last:mb-0 last:border-0 last:pb-0">
      <span className="text-sm font-semibold text-ink/60">{label}</span>
      <span className="max-w-[65%] text-right text-sm font-semibold">{value}</span>
    </div>
  );
}

export function List({ items = [], numbered = false }: { items?: string[]; numbered?: boolean }) {
  const ListTag = numbered ? "ol" : "ul";
  return (
    <ListTag className={`space-y-2 text-sm leading-6 text-ink/75 ${numbered ? "list-decimal pl-5" : "list-disc pl-5"}`}>
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ListTag>
  );
}
