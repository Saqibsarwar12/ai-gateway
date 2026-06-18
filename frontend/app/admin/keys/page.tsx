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
    <div className="stack">
      <header className="section-head">
        <div>
          <div className="section-eyebrow">Section 04 / API Keys</div>
          <h1 className="section-title">My API Keys</h1>
          <p className="section-sub mono">
            {keys.length} / 5 keys used
          </p>
        </div>
        <Button variant="primary" onClick={() => setShowNew(true)} disabled={keys.length >= 5}>
          + Create key
        </Button>
      </header>

      <Card>
        {keys.length === 0 ? (
          <div className="empty-box">No API keys yet.</div>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Key</th>
                  <th>Created</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {keys.map((k) => (
                  <tr key={k.id}>
                    <td>
                      <div style={{ fontWeight: 500 }}>{k.name}</div>
                    </td>
                    <td>
                      <code className="mono text-xs dim bg-[#0a0908] border border-[#2a2520] px-2 py-1 rounded-sm">
                        {k.key_preview}
                      </code>
                    </td>
                    <td className="mono text-xs dim">
                      {(k.created_at || '').replace('T', ' ').slice(0, 16)}
                    </td>
                    <td>
                      {k.is_active ? <Badge variant="ok">active</Badge> : <Badge variant="mute">disabled</Badge>}
                    </td>
                    <td>
                      <div className="row" style={{ justifyContent: 'flex-end' }}>
                        <Button variant="danger" size="sm" onClick={() => handleDelete(k.id)}>
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {showNew && (
        <Modal open title="Create API Key" onClose={() => setShowNew(false)}>
          <form onSubmit={handleCreate} className="stack">
            <Input label="Key Name" value={newKeyName} onChange={setNewKeyName} placeholder="e.g. My App" required />
            {error && <div className="error-box mono text-sm wrap">{error}</div>}
            <div className="row" style={{ justifyContent: 'flex-end' }}>
              <Button variant="ghost" type="button" onClick={() => setShowNew(false)}>Cancel</Button>
              <Button variant="primary" type="submit" disabled={creating}>{creating ? 'Creating...' : 'Create'}</Button>
            </div>
          </form>
        </Modal>
      )}

      {createdKey && (
        <Modal open title="API Key Created" onClose={() => setCreatedKey(null)}>
          <div className="stack">
            <p className="text-sm muted">
              Please copy this key now. For your security, it will not be shown again.
            </p>
            <div className="row" style={{ gap: '0.5rem' }}>
              <code className="mono text-sm flex-1 bg-[#0a0908] border border-[#2a2520] px-3 py-2 rounded-sm break-all">
                {createdKey}
              </code>
              <Button variant="secondary" onClick={() => copyText(createdKey, 'new')}>
                {copiedKeyId === 'new' ? 'Copied!' : 'Copy'}
              </Button>
            </div>
            <div className="row" style={{ justifyContent: 'flex-end', marginTop: '1rem' }}>
              <Button variant="primary" onClick={() => setCreatedKey(null)}>Done</Button>
            </div>
          </div>
        </Modal>
      )}

      <Card title="Base URL" eyebrow="Integration">
        <p className="text-sm muted" style={{ marginBottom: '0.5rem' }}>Use this base URL with any OpenAI-compatible client:</p>
        <div className="row" style={{ gap: '0.5rem' }}>
          <code className="mono text-sm bg-[#0a0908] border border-[#2a2520] px-3 py-2 rounded-sm flex-1 break-all">
            {API_BASE_URL}/v1
          </code>
          <Button variant="secondary" size="sm" onClick={() => copyText(`${API_BASE_URL}/v1`, 'url')}>
            {copiedKeyId === 'url' ? 'Copied' : 'Copy'}
          </Button>
        </div>
      </Card>
    </div>
  );
}
