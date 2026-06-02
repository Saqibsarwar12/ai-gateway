// Reusable UI components for AI Gateway dashboard

import React from 'react';

// ─── Card ──────────────────────────────────────────────────────────────
export function Card({
  title,
  subtitle,
  action,
  children,
  className = '',
  accent = 'none',
}: {
  title?: string;
  subtitle?: string | React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  accent?: 'none' | 'acid' | 'rose' | 'cyan' | 'amber';
}) {
  const accentClass = {
    none: '',
    acid: 'border-l-2 border-l-[#c8ff3d]',
    rose: 'border-l-2 border-l-[#ff5d8f]',
    cyan: 'border-l-2 border-l-[#4dd0e1]',
    amber: 'border-l-2 border-l-[#ffb74d]',
  }[accent];

  return (
    <div className={`bg-[#0d0d0c] border border-white/5 rounded-sm ${accentClass} ${className}`}>
      {(title || action) && (
        <div className="flex items-start justify-between border-b border-white/5 px-5 py-3">
          <div>
            {title && <h3 className="text-[11px] font-mono uppercase tracking-[0.18em] text-white/40">{title}</h3>}
            {subtitle && <div className="mt-1 text-xs text-white/30">{subtitle}</div>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

// ─── Stat (alias) ──────────────────────────────────────────────────────
// Stat removed - use StatCard

// ─── StatCard with value ───────────────────────────────────────────────
export function StatCard({
  label,
  value,
  hint,
  trend,
  accent = 'none',
}: {
  label: string;
  value: string | number;
  hint?: string;
  trend?: { value: number; positive?: boolean };
  accent?: 'none' | 'acid' | 'rose' | 'cyan' | 'amber';
}) {
  return (
    <Card accent={accent} className="relative overflow-hidden">
      <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/30 mb-3">{label}</div>
      <div className="text-4xl font-serif text-white tracking-tight">{value}</div>
      {hint && <div className="mt-2 text-xs text-white/40 font-mono">{hint}</div>}
      {trend && (
        <div
          className={`mt-2 inline-flex items-center gap-1 text-xs font-mono ${
            trend.positive ? 'text-[#c8ff3d]' : 'text-[#ff5d8f]'
          }`}
        >
          <span>{trend.positive ? '↑' : '↓'}</span>
          <span>{Math.abs(trend.value).toFixed(1)}%</span>
        </div>
      )}
    </Card>
  );
}

// ─── Button ────────────────────────────────────────────────────────────
export function Button({
  children,
  onClick,
  type = 'button',
  variant = 'primary',
  size = 'md',
  disabled = false,
  className = '',
}: {
  children: React.ReactNode;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'acid';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  className?: string;
}) {
  const variants = {
    primary: 'bg-white text-black hover:bg-white/90',
    secondary: 'bg-white/5 text-white border border-white/10 hover:bg-white/10',
    ghost: 'text-white/60 hover:text-white hover:bg-white/5',
    danger: 'bg-[#ff5d8f]/10 text-[#ff5d8f] border border-[#ff5d8f]/30 hover:bg-[#ff5d8f]/20',
    acid: 'bg-[#c8ff3d] text-black hover:bg-[#c8ff3d]/90',
  };
  const sizes = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-5 py-2.5 text-sm',
  };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`font-mono uppercase tracking-wider transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {children}
    </button>
  );
}

// ─── Input ─────────────────────────────────────────────────────────────
export function Input({
  label,
  value,
  onChange,
  type = 'text',
  placeholder,
  required = false,
  hint,
  autoComplete,
  className = '',
}: {
  label?: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete?: string;
  type?: string;
  placeholder?: string;
  required?: boolean;
  hint?: string;
  className?: string;
}) {
  return (
    <div className={className}>
      {label && (
        <label className="block font-mono text-[10px] uppercase tracking-[0.2em] text-white/40 mb-2">
          {label} {required && <span className="text-[#ff5d8f]">*</span>}
        </label>
      )}
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        className="w-full bg-black/30 border border-white/10 px-3 py-2.5 text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-[#c8ff3d]/50 transition-colors font-mono"
        autoComplete={autoComplete}
      />
      {hint && <div className="mt-1.5 text-xs text-white/30">{hint}</div>}
    </div>
  );
}

// ─── Select ────────────────────────────────────────────────────────────
export function Select({
  label,
  value,
  onChange,
  options,
  className = '',
}: {
  label?: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  className?: string;
}) {
  return (
    <div className={className}>
      {label && (
        <label className="block font-mono text-[10px] uppercase tracking-[0.2em] text-white/40 mb-2">
          {label}
        </label>
      )}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-black/30 border border-white/10 px-3 py-2.5 text-sm text-white focus:outline-none focus:border-[#c8ff3d]/50 transition-colors font-mono"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value} className="bg-[#0d0d0c]">
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

// ─── Badge ─────────────────────────────────────────────────────────────
export function Badge({
  children,
  variant = 'default',
  className = '',
}: {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'acid';
  className?: string;
}) {
  const v = {
    default: 'bg-white/5 text-white/60 border-white/10',
    success: 'bg-[#c8ff3d]/10 text-[#c8ff3d] border-[#c8ff3d]/30',
    warning: 'bg-[#ffb74d]/10 text-[#ffb74d] border-[#ffb74d]/30',
    danger: 'bg-[#ff5d8f]/10 text-[#ff5d8f] border-[#ff5d8f]/30',
    info: 'bg-[#4dd0e1]/10 text-[#4dd0e1] border-[#4dd0e1]/30',
    acid: 'bg-[#c8ff3d] text-black border-[#c8ff3d]',
  }[variant];
  return (
    <span className={`inline-flex items-center px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider border ${v} ${className}`}>
      {children}
    </span>
  );
}

// ─── Spinner / Loader ──────────────────────────────────────────────────
export function Spinner({ size = 16 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className="animate-spin"
      style={{ color: '#c8ff3d' }}
    >
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity="0.2" strokeWidth="3" />
      <path
        d="M12 2a10 10 0 0 1 10 10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function Loader({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-white/50 font-mono text-xs">
      <Spinner />
      {label && <span className="uppercase tracking-wider">{label}</span>}
    </div>
  );
}

// ─── ErrorState ────────────────────────────────────────────────────────
export function ErrorState({ error, onRetry }: { error: string | Error; onRetry?: () => void }) {
  const msg = error instanceof Error ? error.message : error;
  return (
    <div className="border border-[#ff5d8f]/30 bg-[#ff5d8f]/5 p-5">
      <div className="flex items-start gap-3">
        <div className="w-2 h-2 bg-[#ff5d8f] rounded-full mt-1.5 flex-shrink-0" />
        <div className="flex-1">
          <div className="font-mono text-xs uppercase tracking-wider text-[#ff5d8f] mb-1">
            Something broke
          </div>
          <div className="text-sm text-white/70 font-mono">{msg}</div>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-3 text-xs font-mono uppercase tracking-wider text-white/60 hover:text-white"
            >
              ↻ Try again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── EmptyState ────────────────────────────────────────────────────────
export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="border border-dashed border-white/10 p-8 text-center">
      <div className="font-serif text-2xl text-white/50 mb-2">{title}</div>
      {hint && <div className="text-sm text-white/30 mb-4 font-mono">{hint}</div>}
      {action}
    </div>
  );
}

// ─── Modal ─────────────────────────────────────────────────────────────
export function Modal({
  open,
  onClose,
  title,
  children,
  width = 'md',
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  width?: 'sm' | 'md' | 'lg' | 'xl';
}) {
  if (!open) return null;
  const widths = {
    sm: 'max-w-md',
    md: 'max-w-xl',
    lg: 'max-w-3xl',
    xl: 'max-w-5xl',
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className={`w-full ${widths[width]} bg-[#0d0d0c] border border-white/10 max-h-[90vh] overflow-y-auto`}>
        <div className="flex items-center justify-between border-b border-white/5 px-5 py-3">
          <h2 className="font-mono text-xs uppercase tracking-[0.2em] text-white/60">{title}</h2>
          <button
            onClick={onClose}
            className="text-white/40 hover:text-white text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
