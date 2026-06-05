'use client';
import { useUser, SignOutButton } from '@/lib/clerk-shim';
import { useAuth } from '@/lib/auth';
import Link from 'next/link';
import { useState, useEffect } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export default function KeysPage() {
  const { user: clerkUser, isLoaded: clerkLoaded } = useUser();
  const { user: adminUser, token: adminToken, logout: adminLogout } = useAuth();
  const [mounted, setMounted] = useState(false);
  const [copied, setCopied] = useState(false);
  const [gatewayUser, setGatewayUser] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { setMounted(true); }, []);

  // Provision Clerk user into gateway backend on first load
  useEffect(() => {
    if (!clerkLoaded || !clerkUser) return;
    // If already have admin session, use that
    if (adminUser && adminToken) {
      setGatewayUser(adminUser);
      return;
    }
    // Provision/fetch gateway user via Clerk
    provisionUser();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clerkLoaded, clerkUser, adminUser, adminToken]);

  async function provisionUser() {
    if (!clerkUser) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/clerk/provision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clerk_user_id: clerkUser.id,
          email: clerkUser.primaryEmailAddress?.emailAddress || '',
          name: clerkUser.fullName || clerkUser.username || '',
        }),
      });
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json();
      setGatewayUser(data.user);
    } catch (e: any) {
      setError('Could not load your API key. Please refresh.');
    } finally {
      setLoading(false);
    }
  }

  if (!mounted) {
    return (
      <main className="min-h-screen bg-[#0a0908] text-[#f5f1e8] grid place-items-center">
        <div className="font-mono text-[10px] text-[#6b6358] tracking-[0.3em] uppercase">Loading…</div>
      </main>
    );
  }

  // Not signed in via Clerk and no admin session
  if (!clerkUser && !adminUser) {
    return (
      <main className="min-h-screen bg-[#0a0908] text-[#f5f1e8] grid place-items-center p-8">
        <div className="text-center">
          <div className="font-mono text-[10px] text-[#6b6358] tracking-[0.4em] uppercase mb-3">◇ Sign in required</div>
          <p className="text-sm text-[#8a8275] mb-6">Sign in or create an account to get your API key.</p>
          <div className="flex justify-center gap-3">
            <Link href="/sign-in" className="font-mono text-xs px-4 py-2 bg-[#d4a574] text-[#0a0908] tracking-wider uppercase">→ Sign in</Link>
            <Link href="/sign-up" className="font-mono text-xs px-4 py-2 border border-[#3a342c] text-[#f5f1e8] tracking-wider uppercase">Create account</Link>
          </div>
        </div>
      </main>
    );
  }

  const displayUser = gatewayUser || adminUser;
  const apiKey = displayUser?.api_key || '(loading…)';
  const apiKeyShort = apiKey.length > 12 ? apiKey.slice(0, 12) + '…' : apiKey;
  const tier = displayUser?.tier || 'v1';

  return (
    <main className="min-h-screen bg-[#0a0908] text-[#f5f1e8]">
      <nav className="border-b border-[#1c1c1a]">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="font-mono text-sm tracking-wider">ai</span>
            <span className="font-mono text-sm tracking-wider text-[#d4a574]">gateway</span>
          </Link>
          <div className="flex items-center gap-4">
            {displayUser?.role === 'admin' && (
              <Link href="/admin" className="font-mono text-[10px] text-[#8a8275] hover:text-[#f5f1e8] tracking-wider uppercase">→ Admin</Link>
            )}
            <span className="font-mono text-[10px] text-[#6b6358]">
              {clerkUser?.primaryEmailAddress?.emailAddress || displayUser?.email}
            </span>
            {clerkUser ? (
              <SignOutButton redirectUrl="/">
                <button className="font-mono text-[10px] text-[#6b6358] hover:text-[#f5f1e8] tracking-wider uppercase">Logout</button>
              </SignOutButton>
            ) : (
              <button onClick={() => { adminLogout(); window.location.href = '/'; }} className="font-mono text-[10px] text-[#6b6358] hover:text-[#f5f1e8] tracking-wider uppercase">Logout</button>
            )}
          </div>
        </div>
      </nav>

      <section className="max-w-5xl mx-auto px-6 py-12">
        <div className="font-mono text-[10px] text-[#d4a574] tracking-[0.4em] uppercase mb-2">◇ Your API key</div>
        <h1 className="font-serif text-5xl italic mb-3">One key, every model.</h1>
        <p className="text-sm text-[#8a8275] max-w-2xl leading-relaxed mb-8">
          Use this key with any OpenAI-compatible client. Set <code className="font-mono text-[#d4a574]">base_url</code> to the gateway and your <code className="font-mono text-[#d4a574]">api_key</code> to the value below.
        </p>

        {error && (
          <div className="bg-[#1a0f0f] border border-[#4a2020] p-4 mb-6 font-mono text-xs text-[#e07070]">{error}</div>
        )}
        {loading && (
          <div className="font-mono text-[10px] text-[#6b6358] tracking-wider uppercase mb-6">Provisioning your account…</div>
        )}

        {/* Tier badge */}
        <div className="flex items-center gap-3 mb-6">
          <span className="font-mono text-[10px] text-[#6b6358] tracking-wider uppercase">Tier</span>
          <span className="font-mono text-xs px-2 py-0.5 bg-[#1c1c1a] border border-[#2a2520] text-[#d4a574] uppercase tracking-wider">{tier}</span>
          {tier === 'v1' && (
            <span className="font-mono text-[10px] text-[#6b6358]">Contact admin to upgrade to v2/v3 for more models &amp; higher limits</span>
          )}
        </div>

        <div className="bg-[#14110f] border border-[#2a2520] p-6 mb-6">
          <div className="font-mono text-[10px] text-[#6b6358] tracking-wider uppercase mb-3">Endpoint ({tier})</div>
          <code className="font-mono text-sm text-[#d4a574] break-all">{API_BASE}/{tier}</code>
          <div className="font-mono text-[10px] text-[#6b6358] tracking-wider uppercase mt-6 mb-3">API key</div>
          <div className="flex gap-2">
            <code className="font-mono text-sm text-[#f5f1e8] bg-[#0a0908] border border-[#2a2520] px-3 py-2 break-all flex-1">{apiKey}</code>
            <button
              onClick={() => { navigator.clipboard.writeText(apiKey); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
              className="font-mono text-[10px] px-3 py-2 bg-[#d4a574] text-[#0a0908] tracking-wider uppercase"
            >{copied ? 'Copied' : 'Copy'}</button>
          </div>
          <div className="font-mono text-[10px] text-[#6b6358] mt-4">Keep this secret. Don't share it.</div>
        </div>

        <div className="bg-[#14110f] border border-[#2a2520] p-6 mb-6">
          <div className="font-mono text-[10px] text-[#6b6358] tracking-wider uppercase mb-3">Try it (cURL)</div>
          <pre className="font-mono text-xs text-[#d4cdbf] overflow-x-auto whitespace-pre-wrap break-all">{`curl -X POST ${API_BASE}/${tier}/chat/completions \\
  -H "Authorization: Bearer ${apiKeyShort}" \\
  -H "Content-Type: application/json" \\
  -d '{"model":"auto","messages":[{"role":"user","content":"hello"}]}'`}</pre>
        </div>

        <div className="bg-[#14110f] border border-[#2a2520] p-6 mb-6">
          <div className="font-mono text-[10px] text-[#6b6358] tracking-wider uppercase mb-3">Try it (Python)</div>
          <pre className="font-mono text-xs text-[#d4cdbf] overflow-x-auto whitespace-pre-wrap break-all">{`from openai import OpenAI
client = OpenAI(
    base_url="${API_BASE}/${tier}",
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
            <div><div className="text-[10px] text-[#6b6358] uppercase tracking-wider">Name</div><div>{displayUser?.name || clerkUser?.fullName || '—'}</div></div>
            <div><div className="text-[10px] text-[#6b6358] uppercase tracking-wider">Email</div><div>{displayUser?.email || clerkUser?.primaryEmailAddress?.emailAddress}</div></div>
            <div><div className="text-[10px] text-[#6b6358] uppercase tracking-wider">Tier</div><div className="text-[#d4a574]">{tier}</div></div>
            <div><div className="text-[10px] text-[#6b6358] uppercase tracking-wider">Credits</div><div>{(displayUser?.credits ?? 0).toLocaleString()}</div></div>
          </div>
        </div>
      </section>
    </main>
  );
}
