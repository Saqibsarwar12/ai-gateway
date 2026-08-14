'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { API_BASE_URL } from '@/lib/api';
import {
  Card,
  Loader,
  ErrorState,
  Input,
  Select,
  Button,
  Modal,
  Badge,
} from '@/components/UI';
import type { User, UserResponse } from '@/lib/api';

type UserWithTier = User & { tier?: string };

export default function UsersPage() {
  const { token, apiKey, user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const router = useRouter();
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState('');
  const [editing, setEditing] = useState<UserResponse | null>(null);
  const [copiedKeyId, setCopiedKeyId] = useState<string | null>(null);
  const [showNew, setShowNew] = useState(false);

  useEffect(() => {
    if (!isAdmin) {
      router.replace('/admin');
      return;
    }
  }, [isAdmin, router]);

  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  else if (apiKey) headers['X-API-Key'] = apiKey;

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`${API_BASE_URL}/admin/users`, { headers });
      if (!r.ok) throw new Error(`${r.status}`);
      setUsers(await r.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    if (!isAdmin) return;
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, apiKey, isAdmin]);

  if (!isAdmin) {
    return <Loader label="Redirecting..." />;
  }

  async function toggleActive(u: UserWithTier) {
    await fetch(`${API_BASE_URL}/admin/users/${u.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...headers },
      body: JSON.stringify({ is_active: !u.is_active }),
    });
    load();
  }

  async function remove(u: UserWithTier) {
    if (!confirm(`Delete user ${u.email}? This cannot be undone.`)) return;
    if (u.role === 'admin') {
      setError('The admin account cannot be deleted.');
      return;
    }
    await fetch(`${API_BASE_URL}/admin/users/${u.id}`, { method: 'DELETE', headers });
    load();
  }

  async function updateTier(u: UserWithTier, tier: string) {
    await fetch(`${API_BASE_URL}/admin/users/${u.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...headers },
      body: JSON.stringify({ tier }),
    });
    setEditing(null);
    load();
  }

  function copyKey(key: string, id: string) {
    navigator.clipboard.writeText(key);
    setCopiedKeyId(id);
    setTimeout(() => setCopiedKeyId(null), 1500);
  }

  const tierVariant = (tier?: string) => {
    if (tier === 'v3') return 'ok';
    if (tier === 'v2') return 'default';
    return 'mute';
  };

  if (loading) return <Loader label="Loading users" />;
  if (error) return <ErrorState error={error} onRetry={load} />;

  return (
    <div className="stack">
      <header className="section-head">
        <div>
          <div className="section-eyebrow">Section 08 / Users &amp; API keys</div>
          <h1 className="section-title">Members</h1>
          <p className="section-sub mono">
            {users.length} users · {users.filter((u) => u.is_active).length} active · {users.filter((u) => u.role === 'admin').length} admin
          </p>
        </div>
        {user?.role === 'admin' && (
          <Button variant="primary" onClick={() => setShowNew(true)}>
            + Add user
          </Button>
        )}
      </header>

      <Card>
        {users.length === 0 ? (
          <div className="empty-box">No users yet.</div>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Role</th>
                  <th>Tier</th>
                  <th>Credits</th>
                  <th>API key</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <div style={{ fontWeight: 500 }}>{u.name || '—'}</div>
                      <div className="mono text-xs dim">{u.email}</div>
                    </td>
                    <td>
                      <Badge variant={u.role === 'admin' ? 'ok' : 'default'}>{u.role}</Badge>
                    </td>
                    <td>
                      <div className="row" style={{ gap: '0.375rem', alignItems: 'center' }}>
                        <Badge variant={tierVariant(u.tier)}>{u.tier || 'v1'}</Badge>
                        {user?.role === 'admin' && u.id !== user.id && (
                          <button
                            onClick={() => setEditing(u)}
                            className="text-xs dim hover-fg mono"
                            style={{ padding: '0.125rem 0.375rem', border: '1px solid var(--line)', borderRadius: 2 }}
                          >
                            ↑ upgrade
                          </button>
                        )}
                      </div>
                    </td>
                    <td className="mono text-sm">{(u.credits ?? 0).toLocaleString()}</td>
                    <td>
                      {u.api_key ? (
                        <div className="row">
                          <code className="mono text-xs dim" style={{ maxWidth: '12rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {u.api_key.slice(0, 6)}…{u.api_key.slice(-4)}
                          </code>
                          <button
                            onClick={() => copyKey(u.api_key!, u.id)}
                            className="btn-ghost"
                            style={{ padding: '0.125rem 0.5rem', fontSize: '0.6875rem', borderRadius: 4 }}
                          >
                            {copiedKeyId === u.id ? '✓ copied' : 'Copy'}
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs dim">—</span>
                      )}
                    </td>
                    <td>
                      {u.is_active ? <Badge variant="ok">active</Badge> : <Badge variant="mute">disabled</Badge>}
                    </td>
                    <td>
                      {user?.role === 'admin' && u.id !== user.id && (
                        <div className="row" style={{ justifyContent: 'flex-end' }}>
                          <Button variant="ghost" size="sm" onClick={() => toggleActive(u)}>
                            {u.is_active ? 'Disable' : 'Enable'}
                          </Button>
                          <Button variant="danger" size="sm" onClick={() => remove(u)}>
                            Delete
                          </Button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Tier upgrade modal */}
      {editing && (
        <TierModal
          user={editing}
          onClose={() => setEditing(null)}
          onSave={(tier) => updateTier(editing, tier)}
        />
      )}

      {showNew && (
        <NewUserForm
          headers={headers}
          onClose={() => setShowNew(false)}
          onCreated={() => {
            setShowNew(false);
            load();
          }}
        />
      )}
    </div>
  );
}

function TierModal({
  user,
  onClose,
  onSave,
}: {
  user: UserWithTier;
  onClose: () => void;
  onSave: (tier: string) => void;
}) {
  const [tier, setTier] = useState(user.tier || 'v1');
  return (
    <Modal open title={`Change tier · ${user.email}`} onClose={onClose}>
      <div className="stack">
        <p className="text-sm muted">
          Tier controls which API version the user can access and their rate limits.
        </p>
        <div className="grid-3" style={{ gap: '0.5rem' }}>
          {['v1', 'v2', 'v3'].map((t) => (
            <button
              key={t}
              onClick={() => setTier(t)}
              className={`card text-center mono text-sm ${tier === t ? 'active' : ''}`}
              style={{
                padding: '0.75rem',
                border: `1px solid ${tier === t ? 'var(--fg-0)' : 'var(--line)'}`,
                background: tier === t ? 'var(--bg-2)' : 'transparent',
                cursor: 'pointer',
              }}
            >
              <div style={{ fontSize: '1.25rem', marginBottom: '0.25rem' }}>{t}</div>
              <div className="text-xs dim">
                {t === 'v1' && '60 rpm · 100 credits'}
                {t === 'v2' && '200 rpm · 500 credits'}
                {t === 'v3' && '600 rpm · 2000 credits'}
              </div>
            </button>
          ))}
        </div>
        <div className="row" style={{ justifyContent: 'flex-end' }}>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={() => onSave(tier)}>Save tier</Button>
        </div>
      </div>
    </Modal>
  );
}

function NewUserForm({
  headers,
  onClose,
  onCreated,
}: {
  headers: Record<string, string>;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('user');
  const [tier, setTier] = useState('v1');
  const [credits, setCredits] = useState('100');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const r = await fetch(`${API_BASE_URL}/admin/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...headers },
        body: JSON.stringify({ name, email, password, role, tier, credits: parseInt(credits) }),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        throw new Error(j.detail || `${r.status}`);
      }
      onCreated();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open title="Add user" onClose={onClose}>
      <form onSubmit={submit} className="stack">
        <Input label="Name" value={name} onChange={setName} required />
        <Input label="Email" type="email" value={email} onChange={setEmail} required />
        <Input label="Password" type="password" value={password} onChange={setPassword} required minLength={6} />
        <div className="grid-2">
          <Select
            label="Role"
            value={role}
            onChange={setRole}
            options={[
              { value: 'user', label: 'User' },
              { value: 'admin', label: 'Admin' },
              { value: 'readonly', label: 'Read-only' },
            ]}
          />
          <Select
            label="Tier"
            value={tier}
            onChange={setTier}
            options={[
              { value: 'v1', label: 'v1 — 60 rpm' },
              { value: 'v2', label: 'v2 — 200 rpm' },
              { value: 'v3', label: 'v3 — 600 rpm' },
            ]}
          />
        </div>
        <Input label="Credits" type="number" value={credits} onChange={setCredits} />
        {error && <div className="error-box mono text-sm wrap">{error}</div>}
        <div className="row" style={{ justifyContent: 'flex-end' }}>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" type="submit" disabled={saving}>
            {saving ? 'Creating…' : 'Create user'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}