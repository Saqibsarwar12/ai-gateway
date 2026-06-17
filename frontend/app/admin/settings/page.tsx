'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/auth';
import { API_BASE_URL } from '@/lib/api';
import { Card, Button, Input, Modal, Badge } from '@/components/UI';

export default function SettingsPage() {
  const { user, token, logout } = useAuth();
  const [showPwd, setShowPwd] = useState(false);
  const [oldPwd, setOldPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [confirm, setConfirm] = useState('');
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null);

  const API_BASE = process.env.NEXT_PUBLIC_PUBLIC_URL || 'https://saki-gateway.vercel.app';

  async function changePwd(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    if (newPwd !== confirm) return setMsg({ kind: 'err', text: 'New passwords do not match' });
    if (newPwd.length < 8) return setMsg({ kind: 'err', text: 'New password must be at least 8 characters' });
    setSaving(true);
    try {
      // Self-service: call register-style update on /admin/users/<me> with password
      const r = await fetch(`${API_BASE}/admin/users/${user?.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ password: newPwd }),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        throw new Error(j.detail || `${r.status}`);
      }
      setMsg({ kind: 'ok', text: 'Password changed. Please log in again.' });
      setTimeout(() => {
        logout();
        window.location.href = '/login';
      }, 1500);
    } catch (e: any) {
      setMsg({ kind: 'err', text: e.message });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="stack">
      <header className="section-head">
        <div>
          <div className="section-eyebrow">Section 09 / Settings</div>
          <h1 className="section-title">Account &amp; workspace</h1>
        </div>
      </header>

      <Card title="Profile" eyebrow="your account">
        <div className="grid-2">
          <div>
            <div className="text-xs dim mono">Name</div>
            <div className="text-sm" style={{ marginTop: '0.25rem' }}>{user?.name || '—'}</div>
          </div>
          <div>
            <div className="text-xs dim mono">Email</div>
            <div className="text-sm mono" style={{ marginTop: '0.25rem' }}>{user?.email}</div>
          </div>
          <div>
            <div className="text-xs dim mono">Role</div>
            <div style={{ marginTop: '0.25rem' }}>
              <Badge variant={user?.role === 'admin' ? 'ok' : 'default'}>{user?.role}</Badge>
            </div>
          </div>
          <div>
            <div className="text-xs dim mono">Credits</div>
            <div className="text-sm mono" style={{ marginTop: '0.25rem' }}>
              {(user?.credits ?? 0).toLocaleString()}
            </div>
          </div>
        </div>
      </Card>

      <Card title="Security" eyebrow="password" action={<Button onClick={() => setShowPwd(true)}>Change password</Button>}>
        <p className="text-sm muted">
          Change the password used to sign in to this admin panel. After changing, you will be signed out and asked to log in again.
        </p>
      </Card>

      <Card title="API base URL" eyebrow="endpoints">
        <p className="text-sm muted" style={{ marginBottom: '0.5rem' }}>
          Use this base URL when integrating from your own applications:
        </p>
        <pre className="code wrap">{API_BASE}/v1</pre>
        <p className="text-sm muted" style={{ marginTop: '0.5rem' }}>
          Example OpenAI-compatible request:
        </p>
        <pre className="code wrap">{`curl ${API_BASE}/v1/chat/completions \\
  -H "Authorization: Bearer <your-api-key>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "<model-id>",
    "messages": [{"role": "user", "content": "Hello"}]
  }'`}</pre>
      </Card>

      <Card title="Session" eyebrow="sign out">
        <p className="text-sm muted" style={{ marginBottom: '0.75rem' }}>
          Sign out from this device. Your API keys and providers remain intact.
        </p>
        <Button variant="danger" onClick={logout}>
          Sign out
        </Button>
      </Card>

      {showPwd && (
        <Modal open title="Change password" onClose={() => setShowPwd(false)}>
          <form onSubmit={changePwd} className="stack">
            <Input label="Current password" type="password" value={oldPwd} onChange={setOldPwd} required autoComplete="current-password" />
            <Input label="New password" type="password" value={newPwd} onChange={setNewPwd} required autoComplete="new-password" hint="At least 8 characters" />
            <Input label="Confirm new password" type="password" value={confirm} onChange={setConfirm} required autoComplete="new-password" />
            {msg && (
              <div className={msg.kind === 'ok' ? 'badge badge-ok' : 'error-box mono text-sm wrap'}>{msg.text}</div>
            )}
            <div className="row" style={{ justifyContent: 'flex-end' }}>
              <Button variant="ghost" onClick={() => setShowPwd(false)}>Cancel</Button>
              <Button variant="primary" type="submit" disabled={saving}>
                {saving ? 'Saving…' : 'Update password'}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
