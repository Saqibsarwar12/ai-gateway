'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

export default function HomePage() {
  const [sess, setSess] = useState<{ email: string; role: string } | null>(null);
  useEffect(() => {
    const u = localStorage.getItem('ai_gateway_user');
    if (u) {
      try { setSess(JSON.parse(u)); } catch {}
    }
  }, []);

  return (
    <main className="min-h-screen bg-[#0a0908] text-[#f5f1e8]">
      <nav className="border-b border-[#1c1c1a] backdrop-blur">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-sm bg-[#d4a574] flex items-center justify-center text-[#0a0908] font-serif italic text-lg">◇</div>
            <div>
              <div className="font-mono text-sm tracking-wider">ai-gateway</div>
              <div className="font-mono text-[10px] text-[#6b6358] tracking-[0.2em] uppercase">v1.0 / production</div>
            </div>
          </div>
          <div className="flex items-center gap-6">
            <a href="/docs" target="_blank" className="font-mono text-xs text-[#8a8275] hover:text-[#f5f1e8] tracking-wider uppercase">API</a>
            {sess ? (
              <Link href={sess.role === 'admin' ? '/admin' : '/keys'} className="font-mono text-xs px-4 py-1.5 bg-[#d4a574] text-[#0a0908] rounded-sm tracking-wider uppercase hover:bg-[#c89960]">
                → Continue
              </Link>
            ) : (
              <>
                <Link href="/register" className="font-mono text-xs text-[#8a8275] hover:text-[#f5f1e8] tracking-wider uppercase">Sign up</Link>
                <Link href="/login" className="font-mono text-xs px-4 py-1.5 bg-[#d4a574] text-[#0a0908] rounded-sm tracking-wider uppercase hover:bg-[#c89960]">→ Sign in</Link>
              </>
            )}
          </div>
        </div>
      </nav>

      <section className="max-w-7xl mx-auto px-6 pt-24 pb-32">
        <div className="font-mono text-[10px] text-[#d4a574] tracking-[0.4em] uppercase">◇ The OpenAI-compatible gateway</div>
        <h1 className="mt-4 font-serif text-7xl lg:text-9xl text-[#f5f1e8] leading-[0.95] tracking-tight max-w-5xl">
          Every model.<br />
          <span className="italic text-[#d4a574]">One endpoint.</span><br />
          Infinite fallbacks.
        </h1>
        <p className="mt-10 font-serif text-2xl text-[#8a8275] italic max-w-3xl leading-relaxed">
          A production-grade AI gateway that routes 23 providers, optimizes for cost &amp; latency, and never goes down.
        </p>

        <div className="mt-12 flex flex-wrap gap-4">
          <Link href={sess ? (sess.role === 'admin' ? '/admin' : '/keys') : '/register'} className="font-mono text-sm px-6 py-3 bg-[#d4a574] text-[#0a0908] rounded-sm tracking-wider uppercase hover:bg-[#c89960]">
            {sess ? '→ Open admin panel' : '→ Get your API key'}
          </Link>
          <a href="/docs" target="_blank" className="font-mono text-sm px-6 py-3 bg-[#1c1c1a] text-[#f5f1e8] border border-[#2a2820] rounded-sm tracking-wider uppercase hover:bg-[#26241f]">
            View API docs ↗
          </a>
        </div>
      </section>
    </main>
  );
}
