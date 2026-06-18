'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { useEffect, useState, ReactNode } from 'react';

const NAV: { href: string; label: string; glyph: string; adminOnly?: boolean }[] = [
  { href: '/admin', label: 'Overview', glyph: '◐' },
  { href: '/admin/keys', label: 'My API Keys', glyph: '❖' },
  { href: '/admin/providers', label: 'Providers', glyph: '◇', adminOnly: true },
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
      <style jsx>{`
        .shell-grid {
          display: grid;
          grid-template-columns: 280px 1fr;
          min-height: 100vh;
        }
        .shell-aside {
          position: sticky;
          top: 0;
          height: 100vh;
          border-right: 1px solid var(--line);
          background: var(--bg-1);
          display: flex;
          flex-direction: column;
        }
        .mobile-bar { display: none; }
        @media (max-width: 900px) {
          .shell-grid { grid-template-columns: 1fr; }
          .shell-aside {
            position: fixed;
            inset: 0;
            z-index: 50;
            width: 280px;
            transform: ${mobileNavOpen ? 'translateX(0)' : 'translateX(-100%)'};
            transition: transform 200ms ease;
          }
          .mobile-bar {
            display: flex;
            position: sticky;
            top: 0;
            z-index: 40;
            background: var(--bg-1);
            border-bottom: 1px solid var(--line);
            padding: 0.875rem 1rem;
            align-items: center;
            justify-content: space-between;
          }
          .mobile-backdrop {
            display: ${mobileNavOpen ? 'block' : 'none'};
            position: fixed; inset: 0; z-index: 49;
            background: rgba(0,0,0,0.5);
          }
        }
      `}</style>

      <div className="mobile-backdrop" onClick={() => setMobileNavOpen(false)} />

      <aside className="shell-aside">
        <div style={{ padding: '1.25rem 1.25rem 1rem', borderBottom: '1px solid var(--line)' }}>
          <Link href="/admin" className="row" style={{ gap: '0.5rem', alignItems: 'baseline' }}>
            <span className="mono" style={{ fontSize: '1.25rem', letterSpacing: '-0.02em' }}>ai</span>
            <span className="mono" style={{ fontSize: '1.25rem', letterSpacing: '-0.02em', color: 'var(--fg-0)' }}>gateway</span>
          </Link>
          <div className="text-xs mono" style={{ marginTop: '0.25rem', color: 'var(--fg-2)', letterSpacing: '0.18em', textTransform: 'uppercase' }}>
            v1.0.0 · obsidian
          </div>
        </div>

        <nav className="scroll-y" style={{ flex: 1, padding: '1rem 0.625rem', overflowY: 'auto' }}>
          <div className="text-xs mono" style={{ padding: '0 0.625rem 0.5rem', color: 'var(--fg-2)', letterSpacing: '0.18em', textTransform: 'uppercase' }}>
            Navigation
          </div>
          {visibleNav.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`nav-item ${active ? 'active' : ''}`}
              >
                <span className="nav-glyph">{item.glyph}</span>
                <span className="nav-label">{item.label}</span>
                {active && <span className="nav-dot" />}
              </Link>
            );
          })}
        </nav>

        <div style={{ padding: '0.875rem 1.25rem', borderTop: '1px solid var(--line)' }}>
          <div className="between" style={{ marginBottom: '0.5rem' }}>
            <span className="text-xs mono" style={{ color: 'var(--fg-2)', letterSpacing: '0.18em', textTransform: 'uppercase' }}>System</span>
            <span className="text-xs mono" style={{ color: 'var(--fg-1)' }}>{time}</span>
          </div>
          <div className="row" style={{ gap: '0.5rem', alignItems: 'center' }}>
            <span className="dot dot-ok" />
            <span className="text-xs mono" style={{ color: 'var(--fg-1)' }}>live · 1 node</span>
          </div>
          <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--line)' }}>
            <div className="text-xs mono wrap" style={{ color: 'var(--fg-1)' }}>{user?.email}</div>
            <div className="between" style={{ marginTop: '0.25rem' }}>
              <span className="text-xs mono" style={{ color: 'var(--fg-0)', letterSpacing: '0.14em', textTransform: 'uppercase' }}>{user?.role === 'admin' ? 'ADMIN' : 'USER CONSOLE'}</span>
              <button
                onClick={() => { logout(); router.push('/login'); }}
                className="text-xs mono hover-fg"
                style={{ color: 'var(--fg-2)', letterSpacing: '0.12em', textTransform: 'uppercase' }}
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
              style={{ width: 32, height: 32, border: '1px solid var(--line)', display: 'grid', placeItems: 'center' }}
            >≡</button>
            <span className="mono" style={{ fontSize: '1rem' }}>ai-gateway</span>
          </div>
          <span className="text-xs mono" style={{ color: 'var(--fg-2)' }}>{user?.role === 'admin' ? 'ADMIN' : 'USER CONSOLE'}</span>
        </div>
        <div style={{ flex: 1 }}>{children}</div>
      </main>
    </div>
  );
}
