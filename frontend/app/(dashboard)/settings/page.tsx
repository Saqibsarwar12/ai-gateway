'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/auth';
import { useRouter } from 'next/navigation';

export default function SettingsPage() {
  const { user, logout, refresh } = useAuth();
  const router = useRouter();
  const [revealing, setRevealing] = useState(false);

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <div className="space-y-8">
      <header>
        <p className="font-mono text-[10px] tracking-[0.4em] text-[#6b6358] uppercase mb-2">Section 07 / Settings</p>
        <h1 className="font-serif text-5xl italic">Account</h1>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="border border-[#3a342c] p-6 space-y-4">
          <p className="font-mono text-[10px] uppercase tracking-widest text-[#6b6358]">Identity</p>
          <Row label="Name" value={user?.name || '—'} />
          <Row label="Email" value={user?.email || '—'} />
          <Row label="Role" value={<span className="text-[#d8a657]">{user?.role || 'user'}</span>} />
          <Row label="Credits" value={<span className="text-[#d8a657]">{(user?.credits || 0).toLocaleString()}</span>} />
        </div>

        <div className="border border-[#3a342c] p-6 space-y-4">
          <p className="font-mono text-[10px] uppercase tracking-widest text-[#6b6358]">API Key</p>
          <p className="font-serif text-sm text-[#8a8278]">Use this key to authenticate requests to <code className="text-[#d8a657]">/v1/*</code>.</p>
          <div className="bg-[#0a0908] border border-[#3a342c] p-3 font-mono text-xs text-[#f5f1e8] break-all">
            {revealing && user?.api_key ? user.api_key : '•'.repeat(40)}
          </div>
          <div className="flex gap-2">
            <button onClick={() => setRevealing(!revealing)}
              className="font-mono text-[10px] uppercase tracking-widest px-3 py-2 border border-[#3a342c] text-[#f5f1e8] hover:border-[#d8a657]">
              {revealing ? 'Hide' : 'Reveal'}
            </button>
            <button onClick={() => navigator.clipboard.writeText(user?.api_key || '')}
              className="font-mono text-[10px] uppercase tracking-widest px-3 py-2 border border-[#3a342c] text-[#f5f1e8] hover:border-[#d8a657]">
              Copy
            </button>
          </div>
        </div>

        <div className="border border-[#3a342c] p-6 space-y-4 lg:col-span-2">
          <p className="font-mono text-[10px] uppercase tracking-widest text-[#6b6358]">Example · OpenAI-compatible request</p>
          <pre className="bg-[#0a0908] border border-[#3a342c] p-4 text-xs text-[#d4cdbf] overflow-x-auto font-mono">
{`curl -X POST ${process.env.NEXT_PUBLIC_API_URL || 'https://ai-gateway-7dkh.onrender.com'}/v1/chat/completions \\
  -H "Authorization: Bearer ${user?.api_key || 'YOUR_API_KEY'}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'`}
          </pre>
        </div>

        <div className="lg:col-span-2 pt-4">
          <button onClick={handleLogout}
            className="font-mono text-xs uppercase tracking-widest px-6 py-3 border border-[#6b3a3a] text-[#e8c4c4] hover:bg-[#6b3a3a] hover:text-[#0a0908]">
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-[#2a2520]">
      <span className="font-mono text-xs text-[#6b6358] uppercase tracking-widest">{label}</span>
      <span className="font-mono text-sm text-[#f5f1e8]">{value}</span>
    </div>
  );
}
