'use client';
// Shared UI primitives for AI Gateway dashboard.
// All colours come from the obsidian palette in globals.css. No gradients.

import React, { ReactNode } from 'react';

// ─── Card ────────────────────────────────────────────────────────────
export function Card({
  title,
  eyebrow,
  action,
  children,
  className = '',
  elevated = false,
  style,
}: {
  title?: string;
  eyebrow?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  elevated?: boolean;
  style?: React.CSSProperties;
}) {
  return (
    <div className={`${elevated ? 'card-elevated' : 'card'} ${className}`} style={style}>
      {(title || eyebrow || action) && (
        <div className="card-header">
          <div>
            {eyebrow && <div className="section-eyebrow">{eyebrow}</div>}
            {title && <h3 className="text-base font-semibold wrap" style={{ color: 'var(--fg-0)' }}>{title}</h3>}
          </div>
          {action}
        </div>
      )}
      <div>{children}</div>
    </div>
  );
}

// ─── Button ──────────────────────────────────────────────────────────
export function Button({
  children,
  onClick,
  type = 'button',
  variant = 'primary',
  size = 'md',
  disabled = false,
  className = '',
  title,
}: {
  children: ReactNode;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  className?: string;
  title?: string;
}) {
  const sz = size === 'sm' ? '0.4375rem 0.6875rem' : size === 'lg' ? '0.6875rem 1.125rem' : '0.5rem 0.875rem';
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`btn btn-${variant} ${className}`}
      style={{ padding: sz, fontSize: size === 'sm' ? '0.75rem' : size === 'lg' ? '0.9375rem' : '0.8125rem' }}
    >
      {children}
    </button>
  );
}

// ─── Input / Textarea / Select ──────────────────────────────────────
export function Input({
  label, value, onChange, type = 'text', placeholder, required, minLength, maxLength, hint, autoComplete, disabled, className = '', step, min, max,
}: {
  label?: string; value: string; onChange: (v: string) => void;
  type?: string; placeholder?: string; required?: boolean; hint?: ReactNode;
  autoComplete?: string; disabled?: boolean; className?: string; step?: string | number; min?: string | number; max?: string | number; minLength?: number; maxLength?: number;
}) {
  return (
    <div className={`field ${className}`}>
      {label && <label className="label">{label}{required && <span style={{ color: 'var(--err)' }}> *</span>}</label>}
      <input
        type={type} value={value} onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder} required={required} autoComplete={autoComplete} disabled={disabled}
        className="input"
        step={step} min={min} max={max} minLength={minLength} maxLength={maxLength}
      />
      {hint && <div className="text-xs muted" style={{ marginTop: '0.375rem' }}>{hint}</div>}
    </div>
  );
}

export function Textarea({
  label, value, onChange, placeholder, rows = 4, hint, className = '',
}: {
  label?: string; value: string; onChange: (v: string) => void;
  placeholder?: string; rows?: number; hint?: ReactNode; className?: string;
}) {
  return (
    <div className={`field ${className}`}>
      {label && <label className="label">{label}</label>}
      <textarea
        value={value} onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder} rows={rows}
        className="textarea"
      />
      {hint && <div className="text-xs muted" style={{ marginTop: '0.375rem' }}>{hint}</div>}
    </div>
  );
}

export function Select({
  label, value, onChange, options, className = '', disabled, hint,
}: {
  label?: string; value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[]; className?: string; disabled?: boolean; hint?: ReactNode;
}) {
  return (
    <div className={`field ${className}`}>
      {label && <label className="label">{label}</label>}
      <select value={value} onChange={(e) => onChange(e.target.value)} className="select" disabled={disabled}>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
      {hint && <div className="text-xs muted" style={{ marginTop: '0.375rem' }}>{hint}</div>}
    </div>
  );
}

export function Checkbox({
  label, checked, onChange,
}: { label: ReactNode; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="row" style={{ cursor: 'pointer' }}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="text-sm">{label}</span>
    </label>
  );
}

// ─── Badge ──────────────────────────────────────────────────────────
export function Badge({
  children, variant = 'default', className = '',
}: { children: ReactNode; variant?: 'default' | 'ok' | 'warn' | 'err' | 'info' | 'mute'; className?: string }) {
  const cls = variant === 'ok' ? 'badge-ok' : variant === 'warn' ? 'badge-warn' : variant === 'err' ? 'badge-err' : variant === 'info' ? 'badge-info' : variant === 'mute' ? 'badge-mute' : '';
  return <span className={`badge ${cls} ${className}`}>{children}</span>;
}

// ─── Stat ───────────────────────────────────────────────────────────
export function Stat({
  label, value, hint, accent = 'none',
}: { label: string; value: ReactNode; hint?: ReactNode; accent?: 'none' | 'ok' | 'warn' | 'err' }) {
  const dot = accent === 'ok' ? 'dot-ok' : accent === 'warn' ? 'dot-warn' : accent === 'err' ? 'dot-err' : 'dot-idle';
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value wrap">{value}</div>
      {hint && <div className="stat-hint">{hint}</div>}
      {accent !== 'none' && <div style={{ marginTop: '0.5rem' }}><span className={`dot ${dot}`} /></div>}
    </div>
  );
}

// ─── Spinner / Loader ───────────────────────────────────────────────
export function Spinner({ size = 16 }: { size?: number }) {
  return <span className="spinner" style={{ width: size, height: size }} />;
}
export function Loader({ label }: { label?: string }) {
  return (
    <div className="loader-block">
      <Spinner /> {label && <span>{label}</span>}
    </div>
  );
}

// ─── ErrorState ─────────────────────────────────────────────────────
export function ErrorState({ error, onRetry }: { error: string | Error; onRetry?: () => void }) {
  const msg = error instanceof Error ? error.message : error;
  return (
    <div className="card" style={{ borderColor: 'var(--line-strong)' }}>
      <div className="row" style={{ alignItems: 'flex-start' }}>
        <span className="dot dot-err" style={{ marginTop: '0.4375rem' }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="text-sm font-semibold mb-1">Error</div>
          <div className="text-sm muted wrap mono">{msg}</div>
          {onRetry && (
            <div style={{ marginTop: '0.75rem' }}>
              <Button onClick={onRetry} variant="secondary" size="sm">Try again</Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── EmptyState ─────────────────────────────────────────────────────
export function EmptyState({
  title, hint, action,
}: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="card" style={{ borderStyle: 'dashed', textAlign: 'center', padding: '2.5rem 1rem' }}>
      <div className="text-lg font-semibold mb-1">{title}</div>
      {hint && <div className="text-sm muted" style={{ marginBottom: action ? '1rem' : 0 }}>{hint}</div>}
      {action}
    </div>
  );
}

// ─── Modal ──────────────────────────────────────────────────────────
export function Modal({
  open, onClose, title, children, footer, width = 'md',
}: {
  open: boolean; onClose: () => void; title: string;
  children: ReactNode; footer?: ReactNode; width?: 'sm' | 'md' | 'lg';
}) {
  if (!open) return null;
  const cls = width === 'lg' ? 'modal modal-lg' : 'modal';
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className={cls} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="text-base font-semibold wrap">{title}</h3>
          <button onClick={onClose} aria-label="Close" className="btn btn-ghost" style={{ padding: '0.25rem 0.5rem' }}>×</button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  );
}

// ─── CopyableText ───────────────────────────────────────────────────
export function CopyableText({ value, label }: { value: string; label?: string }) {
  const [copied, setCopied] = React.useState(false);
  return (
    <div className="row" style={{ gap: '0.375rem' }}>
      <code className="mono text-xs" style={{
        background: 'var(--bg-0)', border: '1px solid var(--line)', padding: '0.1875rem 0.4375rem',
        borderRadius: 3, maxWidth: '100%', overflowWrap: 'anywhere', wordBreak: 'break-all',
      }}>{value}</code>
      <button
        className="btn btn-ghost"
        style={{ padding: '0.1875rem 0.4375rem', fontSize: '0.6875rem' }}
        onClick={() => {
          navigator.clipboard.writeText(value);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        }}
      >
        {copied ? 'Copied' : 'Copy'}
      </button>
      {label && <span className="text-xs dim">{label}</span>}
    </div>
  );
}

// ─── KeyValue ───────────────────────────────────────────────────────
export function KeyValue({ k, v, mono = true }: { k: string; v: ReactNode; mono?: boolean }) {
  return (
    <div className="between" style={{ padding: '0.4375rem 0', borderBottom: '1px solid var(--line)' }}>
      <span className="text-xs muted">{k}</span>
      <span className={`text-sm wrap ${mono ? 'mono' : ''}`} style={{ maxWidth: '60%', textAlign: 'right' }}>{v}</span>
    </div>
  );
}
