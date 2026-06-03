'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
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
import type { User } from '@/lib/api';

export default function UsersPage() {
  const { token, apiKey, user: me } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  else if (apiKey) headers['X-API-Key'] = apiKey;

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch('https://saki-gateway.indevs.in/admin/users', { headers });
      if (!r.ok) throw new Error(`${r.status}`);
      setUsers(await r.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, apiKey]);

  async function toggleActive(u: User) {
    await fetch(`https://saki-gateway.indevs.in/admin/users/${u.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...headers },
      body: JSON.stringify({ is_active: !u.is_active }),
    });
    load();
  }

  async function remove(u: User) {
    if (!confirm(`Delete user ${u.email}? This cannot be undone.`)) return;
    await fetch(`https://saki-gateway.indevs.in/admin/users/${u.id}`, {
      method: 'DELETE',
      headers,
    });
    load();
  }

  function copyKey(key: string, id: string) {
    navigator.clipboard.writeText(key);
    setCopiedKey(id);
    setTimeout(() => setCopiedKey(null), 1500);
  }

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
        {me?.role === 'admin' && (
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
                            {copiedKey === u.id ? '✓ copied' : 'Copy'}
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
                      {me?.role === 'admin' && u.id !== me.id && (
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
  const [credits, setCredits] = useState('100');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const r = await fetch('https://saki-gateway.indevs.in/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...headers },
        body: JSON.stringify({ name, email, password, role, credits: parseInt(credits) }),
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
          <Input label="Credits" type="number" value={credits} onChange={setCredits} />
        </div>
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
