import Link from 'next/link';

export default function Home() {
  return (
    <main style={{ minHeight: '100vh', position: 'relative', zIndex: 1 }}>
      <nav style={{ borderBottom: '1px solid var(--line)', backdropFilter: 'blur(20px)' }}>
        <div className="container between" style={{ padding: '1rem 1.5rem' }}>
          <div className="row" style={{ gap: '0.75rem' }}>
            <div style={{
              width: 32, height: 32, background: 'var(--bg-3)', border: '1px solid var(--line)',
              display: 'grid', placeItems: 'center', color: 'var(--fg-0)', fontFamily: 'var(--font-mono)',
            }}>◇</div>
            <div>
              <div className="mono" style={{ fontSize: '0.875rem', letterSpacing: '-0.01em' }}>ai-gateway</div>
              <div className="text-xs mono" style={{ color: 'var(--fg-2)', letterSpacing: '0.14em', textTransform: 'uppercase' }}>v1.0 / obsidian</div>
            </div>
          </div>
          <div className="row" style={{ gap: '1.5rem' }}>
            <a href="https://saki-gateway.indevs.in/docs" target="_blank" rel="noreferrer" className="text-xs mono hover-fg" style={{ textTransform: 'uppercase', letterSpacing: '0.12em' }}>API</a>
            <Link href="/login" className="btn btn-primary text-xs" style={{ padding: '0.5rem 0.875rem' }}>→ Dashboard</Link>
          </div>
        </div>
      </nav>

      <section className="container" style={{ paddingTop: '5rem', paddingBottom: '6rem' }}>
        <div className="text-xs mono" style={{ color: 'var(--fg-1)', textTransform: 'uppercase', letterSpacing: '0.18em' }}>
          ◇ The OpenAI-compatible gateway
        </div>
        <h1 style={{
          marginTop: '1rem', fontFamily: 'var(--font-display)',
          fontSize: 'clamp(3rem, 9vw, 7rem)', lineHeight: 0.95, letterSpacing: '-0.03em',
          color: 'var(--fg-0)', maxWidth: '18ch', fontWeight: 600,
        }}>
          Every model.<br />
          <span style={{ fontStyle: 'italic', color: 'var(--fg-1)' }}>One endpoint.</span><br />
          Infinite fallbacks.
        </h1>
        <p style={{
          marginTop: '1.75rem', fontFamily: 'var(--font-display)', fontSize: 'clamp(1.125rem, 1.5vw, 1.375rem)',
          color: 'var(--fg-1)', maxWidth: '50ch', lineHeight: 1.5, fontStyle: 'italic',
        }}>
          A production-grade AI gateway that routes any provider, optimizes for cost and latency, and never goes down.
        </p>

        <div className="row wrap" style={{ marginTop: '2.5rem', gap: '0.75rem' }}>
          <Link href="/login" className="btn btn-primary">→ Open dashboard</Link>
          <a href="https://saki-gateway.indevs.in/docs" target="_blank" rel="noreferrer" className="btn btn-ghost">View API docs ↗</a>
        </div>

        <div style={{ marginTop: '4rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', border: '1px solid var(--line)' }}>
          {['OPENAI', 'ANTHROPIC', 'GOOGLE', 'DEEPSEEK', 'MISTRAL', 'GROQ', 'XAI'].map((p) => (
            <div key={p} style={{ padding: '1.5rem 1rem', textAlign: 'center', borderRight: '1px solid var(--line)' }}>
              <span className="text-xs mono" style={{ color: 'var(--fg-2)', letterSpacing: '0.18em' }}>{p}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="container" style={{ paddingTop: '4rem', paddingBottom: '6rem', borderTop: '1px solid var(--line)' }}>
        <div className="grid-3">
          {[
            { glyph: '◐', t: 'Provider routing', d: 'Connect OpenAI, Anthropic, Google, DeepSeek, and 20+ other providers. One endpoint, infinite choices.' },
            { glyph: '↯', t: 'Smart fallbacks', d: 'When a provider fails, we route around it. Automatic retries, cost-based, latency-based, or weighted.' },
            { glyph: '◎', t: 'Live analytics', d: 'See every request, token, and dollar in real-time. Drill down by user, provider, or model.' },
            { glyph: '◉', t: 'User & key management', d: 'Self-service account creation, scoped API keys, credit limits, role-based access.' },
            { glyph: '✦', t: 'Built-in playground', d: 'Test any model from your dashboard. Stream responses, tune temperature, swap providers.' },
            { glyph: '✧', t: 'OpenAI-compatible', d: 'Drop-in replacement for the OpenAI SDK. Migrate in one line of code.' },
          ].map((f) => (
            <div key={f.t} className="card" style={{ padding: '1.5rem' }}>
              <div className="mono" style={{ fontSize: '1.5rem', color: 'var(--fg-1)' }}>{f.glyph}</div>
              <h3 style={{ marginTop: '0.75rem', fontFamily: 'var(--font-display)', fontSize: '1.25rem', fontWeight: 500 }}>{f.t}</h3>
              <p className="text-sm wrap" style={{ marginTop: '0.5rem', color: 'var(--fg-1)', lineHeight: 1.55 }}>{f.d}</p>
            </div>
          ))}
        </div>
      </section>

      <footer style={{ borderTop: '1px solid var(--line)', padding: '1.5rem' }}>
        <div className="container between wrap" style={{ gap: '1rem' }}>
          <div className="text-xs mono" style={{ color: 'var(--fg-2)', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
            / ai-gateway · obsidian v1.0
          </div>
          <div className="text-xs mono" style={{ color: 'var(--fg-2)', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
            saki-gateway.indevs.in
          </div>
        </div>
      </footer>
    </main>
  );
}
