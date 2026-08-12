'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

export default function HomePage() {
  const [adminSess, setAdminSess] = useState<{ email: string; role: string } | null>(null);

  useEffect(() => {
    const u = localStorage.getItem('ai_gateway_user');
    if (u) {
      try { setAdminSess(JSON.parse(u)); } catch {}
    }
  }, []);

  return (
    <main className="min-h-screen bg-[#0a0908] text-[#f5f1e8]">
      <nav className="border-b border-[#1c1c1a] backdrop-blur sticky top-0 z-50 bg-[#0a0908]/90">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-sm bg-[#d4a574] flex items-center justify-center text-[#0a0908] font-serif italic text-lg">◇</div>
            <div>
              <div className="font-mono text-sm tracking-wider">ai-gateway</div>
              <div className="font-mono text-[10px] text-[#6b6358] tracking-[0.2em] uppercase">v1.0 / production</div>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <a href="/docs" target="_blank" className="font-mono text-xs text-[#8a8275] hover:text-[#f5f1e8] tracking-wider uppercase">API Docs</a>
            <a href="#endpoints" className="font-mono text-xs text-[#8a8275] hover:text-[#f5f1e8] tracking-wider uppercase">Endpoints</a>
            <Link href="/login" className="font-mono text-xs text-[#8a8275] hover:text-[#f5f1e8] tracking-wider uppercase">Sign in</Link>
            <Link href="/signup" className="font-mono text-xs text-[#8a8275] hover:text-[#f5f1e8] tracking-wider uppercase">Sign up</Link>
            {adminSess?.role === 'admin' && (
              <Link href="/admin" className="font-mono text-xs px-3 py-1.5 bg-[#d4a574] text-[#0a0908] rounded-sm tracking-wider uppercase hover:bg-[#c89960]">
                Admin →
              </Link>
            )}
          </div>
        </div>
      </nav>

      <section className="max-w-7xl mx-auto px-6 pt-24 pb-20">
        <div className="font-mono text-[10px] text-[#d4a574] tracking-[0.4em] uppercase">◇ The OpenAI-compatible gateway</div>
        <h1 className="mt-4 font-serif text-7xl lg:text-9xl text-[#f5f1e8] leading-[0.95] tracking-tight max-w-5xl">
          Every model.<br />
          <span className="italic text-[#d4a574]">One endpoint.</span><br />
          Infinite fallbacks.
        </h1>
        <p className="mt-10 font-serif text-2xl text-[#8a8275] italic max-w-3xl leading-relaxed">
          A production-grade AI gateway that routes across multiple providers, optimises for cost &amp; latency, and never goes down.
        </p>

        <div className="mt-12 flex flex-wrap gap-4">
          <Link
            href="/login"
            className="font-mono text-sm px-6 py-3 bg-[#d4a574] text-[#0a0908] rounded-sm tracking-wider uppercase hover:bg-[#c89960]"
          >
            → Open admin panel
          </Link>
          <a
            href="#quickstart"
            className="font-mono text-sm px-6 py-3 bg-[#1c1c1a] text-[#f5f1e8] border border-[#2a2820] rounded-sm tracking-wider uppercase hover:bg-[#26241f]"
          >
            View quick start ↓
          </a>
          <a
            href="/docs"
            target="_blank"
            className="font-mono text-sm px-6 py-3 bg-[#1c1c1a] text-[#f5f1e8] border border-[#2a2820] rounded-sm tracking-wider uppercase hover:bg-[#26241f]"
          >
            API docs ↗
          </a>
          <Link
            href="/signup"
            className="font-mono text-sm px-6 py-3 bg-[#d4a574] text-[#0a0908] rounded-sm tracking-wider uppercase hover:bg-[#c89960]"
          >
            Create free account
          </Link>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-6 pb-24">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-px border border-[#1c1c1a] bg-[#1c1c1a]">
          {[
            { icon: '∞', title: 'Auto failover', desc: 'If one provider fails, the next one picks up instantly. Zero downtime.' },
            { icon: '◇', title: 'OpenAI-compatible', desc: 'Drop-in replacement. Change base_url and api_key — nothing else.' },
            { icon: '◎', title: 'Multi-provider', desc: 'OpenAI, Anthropic, DeepSeek, Groq, Gemini, Ollama, and any custom endpoint.' },
            { icon: '≡', title: 'Full request logs', desc: 'Every request logged with tokens, latency, cost, and provider used.' },
            { icon: '◓', title: 'Cost analytics', desc: 'Track spend per model, per provider, per user — in real time.' },
            { icon: '✦', title: 'Tiered access', desc: 'v1 for all users. Upgrade to v2/v3 for more models and higher limits.' },
          ].map((f) => (
            <div key={f.title} className="bg-[#0a0908] p-8">
              <div className="font-mono text-3xl text-[#d4a574] mb-4">{f.icon}</div>
              <div className="font-mono text-xs tracking-[0.2em] uppercase text-[#6b6358] mb-2">{f.title}</div>
              <p className="text-sm text-[#8a8275] leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="endpoints" className="max-w-7xl mx-auto px-6 pb-24">
        <div className="font-mono text-[10px] text-[#d4a574] tracking-[0.4em] uppercase mb-6">◇ Three versions, one gateway</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { v: 'v1', tier: 'Standard', desc: 'Default tier — all users. Full OpenAI compatibility. Free-tier models included.', color: '#d4a574' },
            { v: 'v2', tier: 'Pro', desc: 'Higher rate limits, priority routing, access to premium models (GPT-4, Claude Sonnet, etc).', color: '#a374d4' },
            { v: 'v3', tier: 'Enterprise', desc: 'Dedicated capacity, custom providers, SLA-backed uptime, full audit logs.', color: '#74d4a5' },
          ].map((t) => (
            <div key={t.v} className="border border-[#2a2520] bg-[#14110f] p-6">
              <div className="flex items-baseline gap-3">
                <div className="font-serif text-5xl italic" style={{ color: t.color }}>/{t.v}</div>
                <div className="font-mono text-[10px] tracking-[0.2em] uppercase" style={{ color: t.color }}>{t.tier}</div>
              </div>
              <p className="mt-4 text-sm text-[#8a8275] leading-relaxed">{t.desc}</p>
              <div className="mt-6 font-mono text-[10px] text-[#6b6358] tracking-wider uppercase">base_url = https://saki-gateway.indevs.in/{t.v}</div>
            </div>
          ))}
        </div>
      </section>

      <section id="quickstart" className="max-w-7xl mx-auto px-6 pb-24">
        <div className="font-mono text-[10px] text-[#d4a574] tracking-[0.4em] uppercase mb-6">◇ Quick start</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-[#14110f] border border-[#2a2520] p-6">
            <div className="font-mono text-[10px] text-[#6b6358] tracking-wider uppercase mb-3">cURL</div>
            <pre className="font-mono text-xs text-[#d4cdbf] overflow-x-auto whitespace-pre-wrap break-all">{`curl -X POST https://saki-gateway.indevs.in/v1/chat/completions \\
  -H "Authorization: Bearer sk-your-key" \\
  -H "Content-Type: application/json" \\
  -d '{"model":"auto","messages":[{"role":"user","content":"hello"}]}'`}</pre>
          </div>
          <div className="bg-[#14110f] border border-[#2a2520] p-6">
            <div className="font-mono text-[10px] text-[#6b6358] tracking-wider uppercase mb-3">Python (openai SDK)</div>
            <pre className="font-mono text-xs text-[#d4cdbf] overflow-x-auto whitespace-pre-wrap break-all">{`from openai import OpenAI
client = OpenAI(
    base_url="https://saki-gateway.indevs.in/v1",
    api_key="sk-your-key",
)
resp = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "hello"}],
)
print(resp.choices[0].message.content)`}</pre>
          </div>
        </div>
      </section>

      <footer className="border-t border-[#1c1c1a] py-8">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
          <span className="font-mono text-[10px] text-[#6b6358] tracking-[0.2em] uppercase">ai-gateway / v1.0 / production</span>
          <div className="flex gap-6">
            <Link href="/login" className="font-mono text-[10px] text-[#6b6358] hover:text-[#f5f1e8] tracking-wider uppercase">Admin</Link>
            <Link href="/docs" className="font-mono text-[10px] text-[#6b6358] hover:text-[#f5f1e8] tracking-wider uppercase">Docs</Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
