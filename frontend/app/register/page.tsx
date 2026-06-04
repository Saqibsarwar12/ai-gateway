'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { Button, Input } from '@/components/UI';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export default function RegisterPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const r = await fetch(`${API_BASE}/admin/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password }),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        throw new Error(j.detail || `${r.status}`);
      }
      // auto-login
      await login(email, password);
      router.push('/keys');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#0a0908] text-[#f5f1e8] grid lg:grid-cols-2">
      <div className="hidden lg:flex relative overflow-hidden border-r border-[#1c1c1a] p-12 flex-col justify-between">
        <div className="font-mono text-[10px] text-[#6b6358] tracking-[0.4em] uppercase">◇ Get an API key</div>
        <div>
          <h1 className="font-serif text-6xl leading-[0.95] tracking-tight">
            Sign up once.<br />
            <span className="italic text-[#d4a574]">Use every model.</span>
          </h1>
          <p className="mt-6 text-lg text-[#8a8275] max-w-md leading-relaxed font-serif">
            One OpenAI-compatible endpoint that routes to OpenAI, Anthropic, Google, DeepSeek, Mistral, Groq, xAI, and any custom URL. Fallback on failure. Track usage per request.
          </p>
        </div>
        <div className="font-mono text-[10px] text-[#6b6358] tracking-[0.3em] uppercase">/ Brooklyn, NY / since 2025</div>
      </div>
      <div className="flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="mb-10">
            <div className="font-mono text-[10px] text-[#6b6358] tracking-[0.4em] uppercase">◇ Create your account</div>
            <h2 className="mt-2 font-serif text-3xl text-[#f5f1e8] italic">Welcome.</h2>
          </div>
          <form onSubmit={submit} className="space-y-4">
            <Input label="Name" value={name} onChange={setName} required placeholder="Saqib Sarwar" autoComplete="name" />
            <Input label="Email" type="email" value={email} onChange={setEmail} required placeholder="you@company.com" autoComplete="email" />
            <Input label="Password" type="password" value={password} onChange={setPassword} required placeholder="8+ characters" autoComplete="new-password" hint="Min 8 chars." />
            {error && <div className="bg-rose-500/10 border border-rose-500/30 rounded-sm px-3 py-2 text-xs text-rose-400 font-mono">✕ {error}</div>}
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? 'Creating…' : '→ Create account & get key'}
            </Button>
          </form>
          <div className="mt-8 pt-6 border-t border-[#1c1c1a] text-center">
            <Link href="/login" className="text-[10px] font-mono text-[#6b6358] tracking-wider uppercase hover:text-[#d4a574]">Already have an account? → Sign in</Link>
          </div>
        </div>
      </div>
    </main>
  );
}
