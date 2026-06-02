'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { Button, Input, Spinner } from '@/components/UI';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState('admin@example.com');
  const [password, setPassword] = useState('changeme');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0908] text-[#f5f1e8] flex">
      {/* Left: Brand panel */}
      <div className="hidden lg:flex w-1/2 relative overflow-hidden border-r border-[#1c1c1a]">
        {/* Gradient mesh background */}
        <div
          className="absolute inset-0 opacity-60"
          style={{
            backgroundImage:
              'radial-gradient(at 20% 30%, rgba(212, 165, 116, 0.15) 0px, transparent 50%), radial-gradient(at 80% 70%, rgba(184, 115, 51, 0.1) 0px, transparent 50%)',
          }}
        />
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
          }}
        />
        <div className="relative z-10 flex flex-col justify-between p-12 w-full">
          <div>
            <div className="font-mono text-[10px] text-[#6b6358] tracking-[0.4em] uppercase">
              ◇ Production Infrastructure
            </div>
            <div className="mt-2 font-serif italic text-2xl text-[#d4a574]">ai gateway / v1.0</div>
          </div>

          <div className="space-y-8">
            <div>
              <h1 className="font-serif text-7xl text-[#f5f1e8] leading-[0.95] tracking-tight">
                Every model.
                <br />
                <span className="italic text-[#d4a574]">One endpoint.</span>
              </h1>
              <p className="mt-6 text-lg text-[#8a8275] max-w-md leading-relaxed font-serif">
                Route 23 AI providers through a single, drop-in OpenAI-compatible interface. Built for production
                scale.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-6 max-w-md">
              <div>
                <div className="font-mono text-3xl text-[#f5f1e8]">∞</div>
                <div className="font-mono text-[10px] text-[#6b6358] tracking-[0.2em] uppercase mt-1">
                  Auto failover
                </div>
              </div>
              <div>
                <div className="font-mono text-3xl text-[#f5f1e8]">99.9%</div>
                <div className="font-mono text-[10px] text-[#6b6358] tracking-[0.2em] uppercase mt-1">
                  Uptime SLA
                </div>
              </div>
              <div>
                <div className="font-mono text-3xl text-[#f5f1e8]">~0</div>
                <div className="font-mono text-[10px] text-[#6b6358] tracking-[0.2em] uppercase mt-1">
                  Vendor lock-in
                </div>
              </div>
              <div>
                <div className="font-mono text-3xl text-[#f5f1e8]">1.4k</div>
                <div className="font-mono text-[10px] text-[#6b6358] tracking-[0.2em] uppercase mt-1">
                  Models live
                </div>
              </div>
            </div>
          </div>

          <div className="font-mono text-[10px] text-[#6b6358] tracking-[0.3em] uppercase">
            / Brooklyn, NY / since 2025
          </div>
        </div>
      </div>

      {/* Right: Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="mb-10">
            <div className="font-mono text-[10px] text-[#6b6358] tracking-[0.4em] uppercase">
              ◇ Sign in to your workspace
            </div>
            <h2 className="mt-2 font-serif text-3xl text-[#f5f1e8] italic">Welcome back.</h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e: any) => setEmail(e.target.value)}
              required
              autoComplete="email"
              placeholder="you@company.com"
            />
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e: any) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />

            {error && (
              <div className="bg-rose-500/10 border border-rose-500/30 rounded-sm px-3 py-2 text-xs text-rose-400 font-mono">
                ✕ {error}
              </div>
            )}

            <Button type="submit" disabled={loading} className="w-full !py-2.5 !text-xs">
              {loading ? (
                <span className="flex items-center gap-2">
                  <Spinner size={12} /> Authenticating...
                </span>
              ) : (
                '→ Enter dashboard'
              )}
            </Button>
          </form>

          <div className="mt-8 pt-6 border-t border-[#1c1c1a]">
            <div className="text-[10px] font-mono text-[#6b6358] tracking-wider uppercase mb-2">
              Demo credentials
            </div>
            <div className="font-mono text-xs text-[#8a8275] space-y-0.5">
              <div>admin@example.com / changeme</div>
            </div>
          </div>

          <div className="mt-6 text-center">
            <Link
              href="/"
              className="text-[10px] font-mono text-[#6b6358] tracking-wider uppercase hover:text-[#d4a574]"
            >
              ← Back to home
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
