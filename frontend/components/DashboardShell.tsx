'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { useEffect, useState, ReactNode } from 'react';

const NAV: { href: string; label: string; glyph: string; adminOnly?: boolean }[] = [
  { href: '/admin', label: 'Overview', glyph: '◐' },
  { href: '/admin/keys', label: 'My API Keys', glyph: '❖' },
  { href: '/admin/gateway', label: 'Personal Gateway', glyph: '↗' },
  { href: '/admin/providers', label: 'Providers', glyph: '◇', adminOnly: true },
  { href: '/admin/nvidia-smart', label: 'NVIDIA Smart', glyph: 'N', adminOnly: true },
  { href: '/admin/routing', label: 'Routing', glyph: '↯', adminOnly: true },
  { href: '/admin/models', label: 'Models', glyph: '◎' },
  { href: '/admin/playground', label: 'Playground', glyph: '✦' },
  { href: '/admin/logs', label: 'Request Logs', glyph: '≡' },
  { href: '/admin/analytics', label: 'Analytics', glyph: '◓' },
  { href: '/admin/users', label: 'Users & Keys', glyph: '◉', adminOnly: true },
  { href: '/admin/settings', label: 'Settings', glyph: '✧' },
];

export default function DashboardShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const isAdmin = user?.role === 'admin';
  const visibleNav = NAV.filter((item) => !item.adminOnly || isAdmin);
  const [time, setTime] = useState<string>('');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    const tick = () => {
      const d = new Date();
      setTime(d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    };
    tick();
    const i = setInterval(tick, 1000);
    return () => clearInterval(i);
  }, []);

  useEffect(() => { setMobileNavOpen(false); }, [pathname]);

  function isActive(href: string) {
    if (href === '/admin') return pathname === '/admin';
    return pathname.startsWith(href);
  }

  return (
    <div className="shell-grid">
      <div className={`mobile-backdrop ${mobileNavOpen ? 'block' : 'hidden'}`} onClick={() => setMobileNavOpen(false)} />

      <aside className={`shell-aside ${mobileNavOpen ? 'mobile-open' : ''}`}>
        <div style={{ padding: '1.25rem 1.25rem 1rem', borderBottom: '1px solid var(--line)' }}>
          <Link href="/admin" className="row" style={{ gap: '0.5rem', alignItems: 'baseline' }}>
            <span className="mono" style={{ fontSize: '1.25rem', letterSpacing: '-0.02em', color: 'var(--fg-0)', fontWeight: 600 }}>ai</span>
            <span className="mono" style={{ fontSize: '1.25rem', letterSpacing: '-0.02em', color: 'var(--fg-1)' }}>gateway</span>
          </Link>
          <div className="text-xs mono" style={{ marginTop: '0.375rem', color: 'var(--fg-3)', letterSpacing: '0.15em', textTransform: 'uppercase' }}>
            v1.0.0 · obsidian
          </div>
        </div>

        <nav className="scroll-y" style={{ flex: 1, padding: '0.5rem 0.75rem', overflowY: 'auto' }}>
          <div className="text-xs mono" style={{ padding: '0 0.75rem 0.75rem', color: 'var(--fg-3)', letterSpacing: '0.15em', textTransform: 'uppercase' }}>
            Navigation
          </div>
          {visibleNav.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`nav-item ${active ? 'active' : ''}`}
                onClick={() => setMobileNavOpen(false)}
              >
                <span className="nav-glyph">{item.glyph}</span>
                <span className="nav-label">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div style={{ padding: '1.25rem', borderTop: '1px solid var(--line)' }}>
          <div className="between" style={{ marginBottom: '0.75rem' }}>
            <span className="text-xs mono" style={{ color: 'var(--fg-3)', letterSpacing: '0.15em', textTransform: 'uppercase' }}>System</span>
            <span className="text-xs mono" style={{ color: 'var(--fg-2)' }}>{time}</span>
          </div>
          <div className="row" style={{ gap: '0.5rem', alignItems: 'center' }}>
            <span className="dot dot-ok" style={{ boxShadow: '0 0 8px var(--fg-0)' }} />
            <span className="text-xs mono" style={{ color: 'var(--fg-1)' }}>live · 1 node</span>
          </div>
          <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--line)' }}>
            <div className="text-xs mono wrap" style={{ color: 'var(--fg-1)', marginBottom: '0.5rem' }}>{user?.email}</div>
            <div className="between">
              <span className="text-xs mono" style={{ color: 'var(--fg-0)', letterSpacing: '0.1em', textTransform: 'uppercase', background: 'var(--bg-3)', padding: '2px 6px', borderRadius: '4px' }}>
                {user?.role === 'admin' ? 'Admin' : 'User'}
              </span>
              <button
                onClick={() => { logout(); router.push('/login'); }}
                className="text-xs mono hover-fg"
                style={{ color: 'var(--fg-2)', letterSpacing: '0.1em', textTransform: 'uppercase', padding: '4px' }}
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </aside>

      <main style={{ minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <div className="mobile-bar">
          <div className="row" style={{ gap: '0.5rem', alignItems: 'center' }}>
            <button
              onClick={() => setMobileNavOpen(true)}
              aria-label="Open menu"
              style={{ width: 36, height: 36, borderRadius: '6px', border: '1px solid var(--line)', background: 'var(--bg-2)', display: 'grid', placeItems: 'center', color: 'var(--fg-0)' }}
            >≡</button>
            <span className="mono" style={{ fontSize: '1.125rem', fontWeight: 500, color: 'var(--fg-0)' }}>ai-gateway</span>
          </div>
          <span className="text-xs mono" style={{ color: 'var(--fg-2)' }}>{user?.role === 'admin' ? 'ADMIN' : 'USER'}</span>
        </div>
        <div className="main-content">{children}</div>
      </main>
    </div>
  );
}
