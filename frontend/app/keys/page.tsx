'use client';
import { useAuth } from '@/lib/auth';
import Link from 'next/link';
import { useState, useEffect } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export default function KeysPage() {
  const { user, token, logout } = useAuth();
  const [mounted, setMounted] = useState(false);
  const [copied, setCopied] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  if (!mounted) {
    return (
      <main className="min-h-screen bg-[#0a0908] text-[#f5f1e8] grid place-items-center">
        <div className="font-mono text-[10px] text-[#6b6358] tracking-[0.3em] uppercase">Loading…</div>
      </main>
    );
  }
  if (!user || !token) {
    return (
      <main className="min-h-screen bg-[#0a0908] text-[#f5f1e8] grid place-items-center p-8">
        <div className="text-center">
          <div className="font-mono text-[10px] text-[#6b6358] tracking-[0.4em] uppercase mb-3">◇ Sign in required</div>
          <p className="text-sm text-[#8a8275] mb-6">Sign in or create an account to get your API key.</p>
          <div className="row" style={{ justifyContent: 'center', gap: '0.5rem' }}>
            <Link href="/login" className="font-mono text-xs px-4 py-2 bg-[#d4a574] text-[#0a0908] tracking-wider uppercase">→ Sign in</Link>
            <Link href="/register" className="font-mono text-xs px-4 py-2 border border-[#3a342c] text-[#f5f1e8] tracking-wider uppercase">Create account</Link>
          </div>
        </div>
      </main>
    );
  }
  const apiKey = user.api_key || '(no key)';
  const apiKeyShort = apiKey.length > 12 ? apiKey.slice(0, 12) + '…' : apiKey;
  return (
    <main className="min-h-screen bg-[#0a0908] text-[#f5f1e8]">
      <nav className="border-b border-[#1c1c1a]">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="row" style={{ gap: '0.5rem' }}>
            <span className="font-mono text-sm tracking-wider">ai</span>
            <span className="font-mono text-sm tracking-wider text-[#d4a574]">gateway</span>
          </Link>
          <div className="row" style={{ gap: '0.75rem' }}>
            {user.role === 'admin' && <Link href="/dashboard" className="font-mono text-[10px] text-[#8a8275] hover:text-[#f5f1e8] tracking-wider uppercase">→ Admin</Link>}
            <span className="font-mono text-[10px] text-[#6b6358]">{user.email}</span>
            <button onClick={() => { logout(); window.location.href = '/'; }} className="font-mono text-[10px] text-[#6b6358] hover:text-[#f5f1e8] tracking-wider uppercase">Logout</button>
          </div>
        </div>
      </nav>
      <section className="max-w-5xl mx-auto px-6 py-12">
        <div className="font-mono text-[10px] text-[#d4a574] tracking-[0.4em] uppercase mb-2">◇ Your API key</div>
        <h1 className="font-serif text-5xl italic mb-3">One key, every model.</h1>
        <p className="text-sm text-[#8a8275] max-w-2xl leading-relaxed mb-8">
          Use this key with any OpenAI-compatible client. Set <code className="font-mono text-[#d4a574]">base_url</code> to the gateway and your <code className="font-mono text-[#d4a574]">api_key</code> to the value below. The gateway routes to the best available provider.
        </p>
        <div className="bg-[#14110f] border border-[#2a2520] p-6 mb-6">
          <div className="font-mono text-[10px] text-[#6b6358] tracking-wider uppercase mb-3">Endpoint</div>
          <code className="font-mono text-sm text-[#d4a574] break-all">{API_BASE}/v1</code>
          <div className="font-mono text-[10px] text-[#6b6358] tracking-wider uppercase mt-6 mb-3">API key</div>
          <div className="row" style={{ gap: '0.5rem' }}>
            <code className="font-mono text-sm text-[#f5f1e8] bg-[#0a0908] border border-[#2a2520] px-3 py-2 break-all flex-1">{apiKey}</code>
            <button onClick={() => { navigator.clipboard.writeText(apiKey); setCopied(true); setTimeout(() => setCopied(false), 1500); }} className="font-mono text-[10px] px-3 py-2 bg-[#d4a574] text-[#0a0908] tracking-wider uppercase">{copied ? 'Copied' : 'Copy'}</button>
          </div>
          <div className="font-mono text-[10px] text-[#6b6358] mt-4">Keep this secret. Don't share it. Rotate it from the Admin panel if leaked.</div>
        </div>
        <div className="bg-[#14110f] border border-[#2a2520] p-6 mb-6">
          <div className="font-mono text-[10px] text-[#6b6358] tracking-wider uppercase mb-3">Try it (cURL)</div>
          <pre className="font-mono text-xs text-[#d4cdbf] overflow-x-auto whitespace-pre-wrap break-all">{`curl -X POST ${API_BASE}/v1/chat/completions \\
  -H "Authorization: Bearer ${apiKeyShort}" \\
  -H "Content-Type: application/json" \\
  -d '{"model":"auto","messages":[{"role":"user","content":"hello"}]}'`}</pre>
        </div>
        <div className="bg-[#14110f] border border-[#2a2520] p-6 mb-6">
          <div className="font-mono text-[10px] text-[#6b6358] tracking-wider uppercase mb-3">Try it (Python)</div>
          <pre className="font-mono text-xs text-[#d4cdbf] overflow-x-auto whitespace-pre-wrap break-all">{`from openai import OpenAI
client = OpenAI(
    base_url="${API_BASE}/v1",
    api_key="${apiKeyShort}",
)
resp = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "hello"}],
)
print(resp.choices[0].message.content)`}</pre>
        </div>
        <div className="bg-[#14110f] border border-[#2a2520] p-6">
          <div className="font-mono text-[10px] text-[#6b6358] tracking-wider uppercase mb-3">Account</div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div><div className="text-[10px] text-[#6b6358] uppercase tracking-wider">Name</div><div>{user.name || '—'}</div></div>
            <div><div className="text-[10px] text-[#6b6358] uppercase tracking-wider">Email</div><div>{user.email}</div></div>
            <div><div className="text-[10px] text-[#6b6358] uppercase tracking-wider">Role</div><div>{user.role}</div></div>
            <div><div className="text-[10px] text-[#6b6358] uppercase tracking-wider">Credits</div><div>{(user.credits ?? 0).toLocaleString()}</div></div>
          </div>
        </div>
      </section>
    </main>
  );
}
