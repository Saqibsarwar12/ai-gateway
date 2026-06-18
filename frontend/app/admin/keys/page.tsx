'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { apiListMyKeys, apiCreateMyKey, apiDeleteMyKey, API_BASE_URL } from '@/lib/api';
import { Card, Loader, ErrorState, Button, Input, Modal, Badge } from '@/components/UI';

type KeyData = {
  id: string;
  name: string;
  key_preview: string;
  is_active: boolean;
  created_at: string;
};

export default function KeysPage() {
  const { user } = useAuth();
  const [keys, setKeys] = useState<KeyData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [showNew, setShowNew] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [creating, setCreating] = useState(false);
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  const [copiedKeyId, setCopiedKeyId] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiListMyKeys();
      setKeys(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const res = await apiCreateMyKey({ name: newKeyName });
      setCreatedKey(res.key);
      setShowNew(false);
      setNewKeyName('');
      load();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Are you sure you want to delete this key? It will immediately stop working.')) return;
    try {
      await apiDeleteMyKey(id);
      load();
    } catch (err: any) {
      alert(err.message);
    }
  }

  function copyText(text: string, id: string) {
    navigator.clipboard.writeText(text);
    setCopiedKeyId(id);
    setTimeout(() => setCopiedKeyId(null), 1500);
  }

  if (loading && keys.length === 0) return <Loader label="Loading keys" />;
  if (error && keys.length === 0) return <ErrorState error={error} onRetry={load} />;

  return (
    <div className="stack" style={{ maxWidth: '900px' }}>
      <header className="section-head" style={{ marginBottom: '2rem' }}>
        <div>
          <div className="section-eyebrow">Section 04 / Access</div>
          <h1 className="section-title" style={{ fontSize: '2.5rem', marginTop: '0.25rem', marginBottom: '0.5rem' }}>API Keys</h1>
          <p className="text-sm muted wrap">
            Manage your API keys for authenticating with the gateway.
            You can create up to 5 keys. Keep them secret.
          </p>
        </div>
      </header>

      {/* Main Keys Display */}
      <div className="stack" style={{ gap: '1.5rem' }}>
        <div className="between" style={{ padding: '0 0.25rem' }}>
          <div className="text-xs mono dim tracking-widest uppercase">Your Keys ({keys.length}/5)</div>
          <Button variant="primary" onClick={() => setShowNew(true)} disabled={keys.length >= 5}>
            + Create new key
          </Button>
        </div>

        {keys.length === 0 ? (
          <Card>
            <div className="empty-box">No API keys generated yet. Create one to get started.</div>
          </Card>
        ) : (
          <div className="stack" style={{ gap: '1rem' }}>
            {keys.map((k) => (
              <div key={k.id} className="card" style={{ padding: '1.5rem', background: 'var(--bg-1)', border: '1px solid var(--line)' }}>
                <div className="between" style={{ marginBottom: '1rem' }}>
                  <div className="row" style={{ gap: '0.75rem' }}>
                    <div style={{ fontWeight: 600, fontSize: '1.125rem' }}>{k.name}</div>
                    {k.is_active ? <Badge variant="ok">Active</Badge> : <Badge variant="mute">Disabled</Badge>}
                  </div>
                  <div className="row" style={{ gap: '1rem' }}>
                    <div className="text-xs dim mono">Created {(k.created_at || '').slice(0, 10)}</div>
                    <button 
                      onClick={() => handleDelete(k.id)} 
                      className="text-xs hover-fg" 
                      style={{ color: 'var(--err)', textTransform: 'uppercase', letterSpacing: '0.05em', cursor: 'pointer', background: 'none', border: 'none' }}>
                      Delete
                    </button>
                  </div>
                </div>

                <div className="row" style={{ gap: '0.75rem', alignItems: 'stretch', flexWrap: 'wrap' }}>
                  <div className="mono text-sm" style={{ 
                    flex: 1, 
                    background: 'var(--bg-0)', 
                    border: '1px solid var(--line)', 
                    padding: '0.875rem 1rem', 
                    borderRadius: '6px',
                    color: 'var(--fg-1)',
                    display: 'flex',
                    alignItems: 'center',
                    letterSpacing: '0.05em'
                  }}>
                    {k.key_preview.replace('...', '••••••••••••••••••••••••')}
                  </div>
                  <button 
                    onClick={() => copyText(k.key_preview, k.id)}
                    className="btn btn-secondary mono text-xs uppercase"
                    style={{ padding: '0 1.25rem', letterSpacing: '0.05em' }}
                  >
                    {copiedKeyId === k.id ? 'Copied' : 'Copy'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ marginTop: '3rem' }}>
        <div className="text-xs mono dim tracking-widest uppercase mb-4" style={{ padding: '0 0.25rem' }}>Integration Details</div>
        <Card>
          <div className="stack" style={{ gap: '1.5rem' }}>
            <div>
              <div className="text-xs mono dim uppercase tracking-wider mb-2">Base URL</div>
              <div className="row" style={{ gap: '0.5rem', flexWrap: 'wrap' }}>
                <code className="mono text-sm flex-1 bg-[var(--bg-0)] border border-[var(--line)] px-4 py-3 rounded-md break-all">
                  {API_BASE_URL}/v1
                </code>
                <Button variant="secondary" onClick={() => copyText(`${API_BASE_URL}/v1`, 'url')}>
                  {copiedKeyId === 'url' ? 'Copied' : 'Copy'}
                </Button>
              </div>
            </div>
            
            <div className="divider" style={{ margin: 0 }} />

            <div>
              <div className="text-xs mono dim uppercase tracking-wider mb-2">cURL Example</div>
              <pre className="code wrap" style={{ padding: '1.25rem', fontSize: '0.8125rem' }}>{`curl -X POST ${API_BASE_URL}/v1/chat/completions \\
  -H "Authorization: Bearer <your-key>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "auto",
    "messages": [{"role": "user", "content": "hello"}]
  }'`}</pre>
            </div>
          </div>
        </Card>
      </div>

      {showNew && (
        <Modal open title="Create New API Key" onClose={() => setShowNew(false)}>
          <form onSubmit={handleCreate} className="stack">
            <p className="text-sm muted">Give your new key a descriptive name to help you track its usage.</p>
            <Input 
              label="Key Name" 
              value={newKeyName} 
              onChange={setNewKeyName} 
              placeholder="e.g. Production App, Local Testing..." 
              required 
            />
            {error && <div className="error-box mono text-sm wrap">{error}</div>}
            <div className="row" style={{ justifyContent: 'flex-end', marginTop: '0.5rem' }}>
              <Button variant="ghost" type="button" onClick={() => setShowNew(false)}>Cancel</Button>
              <Button variant="primary" type="submit" disabled={creating}>{creating ? 'Generating...' : 'Generate Key'}</Button>
            </div>
          </form>
        </Modal>
      )}

      {createdKey && (
        <Modal open title="Save Your API Key" onClose={() => setCreatedKey(null)}>
          <div className="stack" style={{ gap: '1.5rem' }}>
            <div style={{ background: 'rgba(212, 165, 116, 0.1)', border: '1px solid rgba(212, 165, 116, 0.3)', padding: '1rem', borderRadius: '6px' }}>
              <p className="text-sm" style={{ color: '#d4a574', margin: 0 }}>
                <strong>Important:</strong> Please copy this key now. For your security, it will not be shown again.
              </p>
            </div>
            
            <div className="row" style={{ gap: '0.75rem', alignItems: 'stretch', flexWrap: 'wrap' }}>
              <code className="mono text-sm flex-1 bg-[var(--bg-0)] border border-[var(--line)] px-4 py-3 rounded-md break-all" style={{ color: '#d4a574' }}>
                {createdKey}
              </code>
              <button 
                onClick={() => copyText(createdKey, 'new')}
                className="btn btn-primary mono text-xs uppercase"
                style={{ padding: '0 1.25rem', letterSpacing: '0.05em', background: '#d4a574', color: '#0a0908' }}
              >
                {copiedKeyId === 'new' ? 'Copied!' : 'Copy Key'}
              </button>
            </div>
            
            <div className="row" style={{ justifyContent: 'flex-end', borderTop: '1px solid var(--line)', paddingTop: '1rem', marginTop: '0.5rem' }}>
              <Button variant="secondary" onClick={() => setCreatedKey(null)}>I've saved it</Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
