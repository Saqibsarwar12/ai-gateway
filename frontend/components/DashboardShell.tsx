'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { useState, useEffect, ReactNode } from "react";

const NAV = [
  { href: '/dashboard', label: 'Overview', glyph: '◐' },
  { href: '/dashboard/providers', label: 'Providers', glyph: '◇' },
  { href: '/dashboard/routing', label: 'Routing', glyph: '↯' },
  { href: '/dashboard/models', label: 'Models', glyph: '◎' },
  { href: '/dashboard/playground', label: 'Playground', glyph: '✦' },
  { href: '/dashboard/logs', label: 'Request Logs', glyph: '≡' },
  { href: '/dashboard/analytics', label: 'Analytics', glyph: '◓' },
  { href: '/dashboard/users', label: 'Users & Keys', glyph: '◉' },
  { href: '/dashboard/settings', label: 'Settings', glyph: '✧' },
];

export default function DashboardShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, apiKey, logout } = useAuth();
  const [time, setTime] = useState<string>('');

  useEffect(() => {
    const tick = () => {
      const d = new Date();
      setTime(
        d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) +
          ' UTC' + (d.getTimezoneOffset() > 0 ? '-' : '+') + Math.abs(d.getTimezoneOffset() / 60)
      );
    };
    tick();
    const i = setInterval(tick, 1000);
    return () => clearInterval(i);
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0908] text-[#f5f1e8] flex">
      {/* Sidebar */}
      <aside className="w-72 border-r border-[#1c1c1a] flex flex-col bg-[#0a0908] sticky top-0 h-screen">
        <div className="px-6 pt-7 pb-5 border-b border-[#1c1c1a]">
          <Link href="/dashboard" className="block group">
            <div className="flex items-baseline gap-2">
              <span className="font-serif text-3xl text-[#f5f1e8] italic tracking-tight">ai</span>
              <span className="font-mono text-3xl text-[#d4a574] tracking-tighter">gateway</span>
            </div>
            <div className="mt-1 font-mono text-[10px] text-[#6b6358] tracking-[0.2em] uppercase">
              v1.0.0 / production
            </div>
          </Link>
        </div>

        <nav className="flex-1 px-3 py-5 space-y-0.5 overflow-y-auto">
          <div className="px-3 mb-2 font-mono text-[9px] text-[#6b6358] tracking-[0.3em] uppercase">Navigation</div>
          {NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`group flex items-center gap-3 px-3 py-2.5 rounded-sm transition-all ${
                  active
                    ? 'bg-[#1a1815] text-[#f5f1e8]'
                    : 'text-[#8a8275] hover:bg-[#141210] hover:text-[#f5f1e8]'
                }`}
              >
                <span
                  className={`font-mono text-base w-5 text-center ${
                    active ? 'text-[#d4a574]' : 'text-[#6b6358] group-hover:text-[#d4a574]'
                  }`}
                >
                  {item.glyph}
                </span>
                <span className="text-sm font-medium">{item.label}</span>
                {active && <span className="ml-auto h-1 w-1 rounded-full bg-[#d4a574]" />}
              </Link>
            );
          })}
        </nav>

        {/* System Status */}
        <div className="px-6 py-4 border-t border-[#1c1c1a] space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[9px] text-[#6b6358] tracking-[0.3em] uppercase">System</span>
            <span className="font-mono text-[10px] text-[#f5f1e8]">{time}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
            </span>
            <span className="font-mono text-[11px] text-[#8a8275]">live · 5 nodes</span>
          </div>
          <div className="pt-2 border-t border-[#1c1c1a]">
            <div className="text-[10px] font-mono text-[#6b6358] truncate">{user?.email}</div>
            <div className="flex items-center justify-between mt-1">
              <span className="text-[10px] font-mono text-[#d4a574] uppercase tracking-wider">{user?.role}</span>
              <button
                onClick={() => {
                  logout();
                  router.push('/login');
                }}
                className="text-[10px] font-mono text-[#6b6358] hover:text-[#f5f1e8] tracking-wider uppercase"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 min-w-0">{children}</main>
    </div>
  );
}
