'use client';

import { useEffect, useState, useRef } from 'react';
import { Card, ErrorState, Loader } from '@/components/UI';
import { api, type Provider } from '@/lib/api';

type Msg = { role: 'user' | 'assistant' | 'system'; content: string };

const SYSTEM_PROMPTS = [
  { label: 'None', value: '' },
  { label: 'Concise', value: 'You are concise. Reply in 1-2 sentences.' },
  { label: 'Coder', value: 'You are an expert software engineer. Reply with code where appropriate.' },
  { label: 'Editor', value: 'You are a careful editor. Reply in well-structured prose.' },
];

export default function PlaygroundPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [models, setModels] = useState<{ id: string; owned_by: string }[]>([]);
  const [model, setModel] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [system, setSystem] = useState('');
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    Promise.all([api.listProviders(), api.listOpenAIModels()])
      .then(([p, m]) => {
        setProviders(p);
        setModels(((m as any).data ?? m) as { id: string; owned_by: string }[]);
        const mm = ((m as any).data ?? m) as { id: string; owned_by: string }[]; if (mm.length) setModel(mm[0].id);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, loading]);

  const send = async () => {
    if (!input.trim() || !model || loading) return;
    const newMsgs: Msg[] = [...messages, { role: 'user', content: input }];
    setMessages(newMsgs);
    setInput('');
    setLoading(true);
    setError(null);
    try {
      const sysMsgs: Msg[] = system ? [{ role: 'system', content: system }] : [];
      const res = await api.chat({
        model,
        messages: [...sysMsgs, ...newMsgs],
        stream: false,
      });
      const reply = res.choices?.[0]?.message?.content || '(empty response)';
      setMessages([...newMsgs, { role: 'assistant', content: reply }]);
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  };

  return (
    <div className="space-y-6 h-[calc(100vh-140px)] flex flex-col">
      <header className="flex items-end justify-between">
        <div>
          <p className="font-mono text-[10px] tracking-[0.4em] text-[#6b6358] uppercase mb-2">Section 04 / Playground</p>
          <h1 className="font-serif text-5xl italic">Try a model</h1>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <label className="block">
          <span className="block font-mono text-[10px] uppercase tracking-widest text-[#6b6358] mb-1.5">Model</span>
          <select value={model} onChange={(e) => setModel(e.target.value)}
            className="w-full bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-mono text-[#f5f1e8] focus:border-[#d8a657] outline-none">
            {models.length === 0 && <option>No models available</option>}
            {models.map((m) => <option key={m.id} value={m.id}>{m.id}</option>)}
          </select>
        </label>
        <label className="block">
          <span className="block font-mono text-[10px] uppercase tracking-widest text-[#6b6358] mb-1.5">System prompt</span>
          <select value={system} onChange={(e) => setSystem(e.target.value)}
            className="w-full bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-mono text-[#f5f1e8] focus:border-[#d8a657] outline-none">
            {SYSTEM_PROMPTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </label>
        <label className="block">
          <span className="block font-mono text-[10px] uppercase tracking-widest text-[#6b6358] mb-1.5">API key (optional)</span>
          <input type="password" value={apiKey} onChange={(e: any) => setApiKey(e.target.value)} placeholder="sk-..."
            className="w-full bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-mono text-[#f5f1e8] focus:border-[#d8a657] outline-none" />
        </label>
      </div>

      <Card className="flex-1 flex flex-col">
        <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-4 pr-2">
          {messages.length === 0 && (
            <div className="h-full flex items-center justify-center py-12">
              <p className="font-serif italic text-2xl text-[#6b6358]">Ask anything to start…</p>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] p-4 border ${
                m.role === 'user'
                  ? 'border-[#d8a657] bg-[#1a1612] text-[#f5f1e8]'
                  : 'border-[#3a342c] bg-[#0a0908] text-[#d4cdbf]'
              }`}>
                <p className="font-mono text-[10px] uppercase tracking-widest text-[#6b6358] mb-2">
                  {m.role}
                </p>
                <p className="font-serif text-base whitespace-pre-wrap leading-relaxed">{m.content}</p>
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="border border-[#3a342c] bg-[#0a0908] px-4 py-3">
                <p className="font-mono text-[10px] uppercase tracking-widest text-[#6b6358]">assistant</p>
                <p className="font-serif italic text-[#6b6358] mt-1 animate-pulse">thinking…</p>
              </div>
            </div>
          )}
          {error && (
            <div className="border border-[#6b3a3a] bg-[#3a1a1a] p-4">
              <p className="font-mono text-[10px] uppercase tracking-widest text-[#e8c4c4] mb-1">Error</p>
              <p className="font-mono text-xs text-[#e8c4c4]">{error}</p>
            </div>
          )}
        </div>

        <div className="mt-4 pt-4 border-t border-[#2a2520] flex gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder="Type a message… (Enter to send, Shift+Enter for newline)"
            rows={2}
            className="flex-1 bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-serif text-[#f5f1e8] focus:border-[#d8a657] outline-none resize-none"
          />
          <button
            onClick={send}
            disabled={loading || !input.trim() || !model}
            className="font-mono text-xs uppercase tracking-widest px-6 bg-[#d8a657] text-[#0a0908] hover:bg-[#e8b867] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? '…' : 'Send'}
          </button>
        </div>
      </Card>
    </div>
  );
}
