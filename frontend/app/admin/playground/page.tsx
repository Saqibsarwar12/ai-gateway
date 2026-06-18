'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { API_BASE_URL } from '@/lib/api';
import { Card, Loader, Select, Button, Badge, Textarea, Input } from '@/components/UI';

type Msg = { role: 'user' | 'assistant' | 'system'; content: string };
type OpenAIModel = { id: string; owned_by: string };

const SYSTEM_PRESETS = [
  { value: '', label: 'No system prompt' },
  { value: 'You are concise. Reply in 1-2 sentences.', label: 'Concise' },
  { value: 'You are an expert software engineer. Use code where appropriate.', label: 'Coder' },
  { value: 'You are a careful editor. Reply in well-structured prose.', label: 'Editor' },
  { value: 'You reply with dry British wit.', label: 'Sarcastic' },
];

export default function PlaygroundPage() {
  const { token, apiKey } = useAuth();
  const [models, setModels] = useState<OpenAIModel[]>([]);
  const [model, setModel] = useState('');
  const [system, setSystem] = useState('');
  const [temperature, setTemperature] = useState('0.7');
  const [maxTokens, setMaxTokens] = useState('1024');
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [usage, setUsage] = useState<{ input: number; output: number; ms: number } | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/v1/models`)
      .then((r) => r.json())
      .then((j) => {
        const list: OpenAIModel[] = j.data || [];
        setModels(list);
        if (list.length) setModel(list[0].id);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, loading]);

  async function send() {
    if (!input.trim() || !model || loading) return;
    const next: Msg[] = [...messages, { role: 'user', content: input }];
    setMessages(next);
    setInput('');
    setLoading(true);
    setError(null);
    setUsage(null);
    const t0 = Date.now();
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      else if (apiKey) headers['X-API-Key'] = apiKey;
      const sysMsgs: Msg[] = system ? [{ role: 'system', content: system }] : [];
      const r = await fetch(`${API_BASE_URL}/v1/chat/completions`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          model,
          messages: [...sysMsgs, ...next],
          temperature: parseFloat(temperature),
          max_tokens: parseInt(maxTokens),
        }),
      });
      if (!r.ok) {
        const t = await r.text();
        try {
          const j = JSON.parse(t);
          throw new Error(j.detail?.[0]?.msg || j.detail || j.error || t);
        } catch {
          throw new Error(t);
        }
      }
      const j = await r.json();
      const reply = j.choices?.[0]?.message?.content || '(empty response)';
      setMessages([...next, { role: 'assistant', content: reply }]);
      const ms = Date.now() - t0;
      setUsage({
        input: j.usage?.prompt_tokens ?? 0,
        output: j.usage?.completion_tokens ?? 0,
        ms,
      });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function clear() {
    setMessages([]);
    setError(null);
    setUsage(null);
  }

  const totalTokens = useMemo(
    () => messages.reduce((acc, m) => acc + m.content.length / 4, 0),
    [messages]
  );

  if (!token && !apiKey) return <Loader label="Authenticating" />;

  return (
    <div className="stack" style={{ minHeight: 'calc(100vh - 8rem)' }}>
      <header className="section-head">
        <div>
          <div className="section-eyebrow">Section 06 / Playground</div>
          <h1 className="section-title">Test any model</h1>
          <p className="section-sub mono">
            {models.length} models available · {messages.length} messages
          </p>
        </div>
        <Button variant="ghost" onClick={clear} disabled={messages.length === 0}>
          Clear
        </Button>
      </header>

      <Card>
        <div className="grid-3">
          <Select
            label="Model"
            value={model}
            onChange={setModel}
            options={models.length ? models.map((m) => ({ value: m.id, label: m.id })) : [{ value: '', label: 'No models — add a provider' }]}
          />
          <Select
            label="System prompt"
            value={system}
            onChange={setSystem}
            options={SYSTEM_PRESETS}
          />
          <div className="grid-2">
            <Input label="Temperature" type="number" step="0.1" min="0" max="2" value={temperature} onChange={setTemperature} />
            <Input label="Max tokens" type="number" value={maxTokens} onChange={setMaxTokens} />
          </div>
        </div>
      </Card>

      <Card style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, flexGrow: 1 }}>
        <div ref={scrollRef} className="scroll-y" style={{ flex: 1, minHeight: '20rem', maxHeight: '60vh' }}>
          {messages.length === 0 ? (
            <div className="empty-box">
              <p className="text-sm dim">No messages yet. Send something to start the conversation.</p>
            </div>
          ) : (
            <div className="stack" style={{ gap: '0.75rem' }}>
              {messages.map((m, i) => (
                <div key={i} className={m.role === 'user' ? 'msg msg-user' : 'msg msg-assistant'}>
                  <div className="row" style={{ gap: '0.5rem', marginBottom: '0.375rem' }}>
                    <Badge variant={m.role === 'user' ? 'default' : 'ok'}>{m.role}</Badge>
                  </div>
                  <div className="msg-text wrap">{m.content}</div>
                </div>
              ))}
              {loading && (
                <div className="msg msg-assistant">
                  <div className="row" style={{ gap: '0.5rem', marginBottom: '0.375rem' }}>
                    <Badge variant="ok">assistant</Badge>
                    <span className="dim text-xs">thinking…</span>
                  </div>
                  <div className="msg-text dim">…</div>
                </div>
              )}
            </div>
          )}
        </div>

        {error && (
          <div className="error-box mono text-sm wrap" style={{ marginTop: '0.75rem' }}>
            {error}
          </div>
        )}

        {usage && !error && (
          <div className="row" style={{ marginTop: '0.5rem', gap: '1rem' }}>
            <span className="text-xs dim mono">
              {usage.input} in / {usage.output} out
            </span>
            <span className="text-xs dim mono">{usage.ms} ms</span>
            <span className="text-xs dim mono">~{Math.round(totalTokens)} chars</span>
          </div>
        )}

        <div style={{ marginTop: '0.75rem' }}>
          <Textarea
            value={input}
            onChange={setInput}
            placeholder="Type a message… (Enter to send, Shift+Enter for newline)"
            rows={3}
            className=""
          />
          <div className="row" style={{ marginTop: '0.5rem', justifyContent: 'flex-end' }}>
            <Button
              variant="primary"
              onClick={send}
              disabled={loading || !input.trim() || !model}
            >
              {loading ? 'Sending…' : '→ Send'}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
