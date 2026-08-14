'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { Button, Input, Spinner } from '@/components/UI';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ''}/admin/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ identifier, password }),
      });
      if (!res.ok) {
        const needsVerification = res.headers.get('X-Needs-Verification') === 'true';
        const body = await res.json().catch(() => ({}));
        if (needsVerification) {
          router.push(`/verify-email?email=${encodeURIComponent(identifier.trim())}`);
          return;
        }
        throw new Error(body.detail || 'Invalid credentials');
      }
      await login(identifier, password);
      router.push('/admin');
    } catch (err: any) {
      setError(err.message || 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)' }} className="login-grid">
      <style jsx>{`
        @media (max-width: 900px) {
          .login-grid { grid-template-columns: 1fr !important; }
          .login-side { display: none !important; }
        }
      `}</style>

      {/* Left brand panel */}
      <aside className="login-side" style={{
        position: 'relative', borderRight: '1px solid var(--line)', padding: '2.5rem',
        display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
        minHeight: '100vh', overflow: 'hidden',
      }}>
        <div>
          <div className="text-xs mono" style={{ color: 'var(--fg-2)', textTransform: 'uppercase', letterSpacing: '0.18em' }}>
            ◇ Production Infrastructure
          </div>
          <div style={{ marginTop: '0.5rem', fontFamily: 'var(--font-display)', fontStyle: 'italic', fontSize: '1.5rem' }}>
            ai gateway / v1.0
          </div>
        </div>

        <div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(2.5rem, 5vw, 4.25rem)', lineHeight: 1, letterSpacing: '-0.025em', fontWeight: 600, color: 'var(--fg-0)' }}>
            Every model.
            <br />
            <span style={{ color: 'var(--fg-1)', fontStyle: 'italic' }}>One endpoint.</span>
          </h1>
          <p style={{ marginTop: '1.25rem', fontSize: '1.0625rem', lineHeight: 1.6, color: 'var(--fg-1)', maxWidth: '34ch' }}>
            Route any AI provider through a single OpenAI-compatible interface. Built for production scale, with admin controls, routing rules, and full request logs.
          </p>

          <div style={{ marginTop: '2.5rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', maxWidth: '28rem' }}>
            <div>
              <div className="mono" style={{ fontSize: '1.75rem', color: 'var(--fg-0)' }}>∞</div>
              <div className="text-xs mono" style={{ color: 'var(--fg-2)', textTransform: 'uppercase', letterSpacing: '0.14em', marginTop: '0.25rem' }}>Auto failover</div>
            </div>
            <div>
              <div className="mono" style={{ fontSize: '1.75rem', color: 'var(--fg-0)' }}>99.9%</div>
              <div className="text-xs mono" style={{ color: 'var(--fg-2)', textTransform: 'uppercase', letterSpacing: '0.14em', marginTop: '0.25rem' }}>Uptime SLA</div>
            </div>
            <div>
              <div className="mono" style={{ fontSize: '1.75rem', color: 'var(--fg-0)' }}>~0</div>
              <div className="text-xs mono" style={{ color: 'var(--fg-2)', textTransform: 'uppercase', letterSpacing: '0.14em', marginTop: '0.25rem' }}>Vendor lock-in</div>
            </div>
            <div>
              <div className="mono" style={{ fontSize: '1.75rem', color: 'var(--fg-0)' }}>1.4k</div>
              <div className="text-xs mono" style={{ color: 'var(--fg-2)', textTransform: 'uppercase', letterSpacing: '0.14em', marginTop: '0.25rem' }}>Models live</div>
            </div>
          </div>
        </div>

        <div className="text-xs mono" style={{ color: 'var(--fg-2)', textTransform: 'uppercase', letterSpacing: '0.18em' }}>
          / Brooklyn, NY / since 2025
        </div>
      </aside>

      {/* Right form */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem 1.5rem' }}>
        <div style={{ width: '100%', maxWidth: '22rem' }}>
          <div style={{ marginBottom: '2.25rem' }}>
            <div className="text-xs mono" style={{ color: 'var(--fg-2)', textTransform: 'uppercase', letterSpacing: '0.18em' }}>
              ◇ Sign in
            </div>
            <h2 style={{ marginTop: '0.5rem', fontFamily: 'var(--font-display)', fontSize: '1.875rem', fontStyle: 'italic', fontWeight: 500 }}>
              Welcome back.
            </h2>
          </div>

          <form onSubmit={handleSubmit} className="stack" style={{ gap: '0.875rem' }}>
            <Input
              label="Email or username"
              type="text"
              value={identifier}
              onChange={setIdentifier}
              required
              autoComplete="email"
              placeholder="you@company.com or use"
            />
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={setPassword}
              required
              autoComplete="current-password"
            />

            {error && (
              <div className="card" style={{ borderColor: 'var(--line-strong)', padding: '0.625rem 0.75rem' }}>
                <div className="row" style={{ gap: '0.5rem' }}>
                  <span className="dot dot-err" style={{ marginTop: '0.375rem' }} />
                  <div className="text-sm wrap">{error}</div>
                </div>
              </div>
            )}

            <Button type="submit" disabled={loading} className="w-full" size="lg">
              {loading ? (
                <span className="row" style={{ gap: '0.5rem', justifyContent: 'center' }}>
                  <Spinner size={12} /> Signing in...
                </span>
              ) : '→ Sign in'}
            </Button>
          </form>

          <div style={{ marginTop: '1.75rem', paddingTop: '1.25rem', borderTop: '1px solid var(--line)' }}>
            <Link href="/" className="text-xs mono" style={{ color: 'var(--fg-2)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>
              ← Back to home
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
