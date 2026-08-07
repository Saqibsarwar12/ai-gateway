'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button, Input, Spinner } from '@/components/UI';

export default function SignupPage() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError('Passwords do not match');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || '/api-proxy'}/admin/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Registration failed');
      }
      setSubmittedEmail(email);
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  }

  if (submittedEmail) {
    return (
      <div className="min-h-screen bg-[#0a0908] text-[#f5f1e8] flex items-center justify-center p-6">
        <div className="w-full max-w-md border border-[#1c1c1a] bg-[#13110f] p-8 rounded-sm">
          <div className="font-mono text-[10px] text-[#d4a574] tracking-[0.4em] uppercase">Check your inbox</div>
          <h1 className="mt-3 font-serif text-3xl italic">Verify your email.</h1>
          <p className="mt-3 text-sm text-[#8a8275] leading-relaxed">We sent a verification link to {submittedEmail}. Your account stays inactive until you open it.</p>
          <Link href="/login" className="mt-6 inline-block font-mono text-xs text-[#d4a574] uppercase tracking-wider">Return to sign in →</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0908] text-[#f5f1e8] flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="border border-[#1c1c1a] bg-[#13110f] p-8 rounded-sm">
          <div className="font-mono text-[10px] text-[#d4a574] tracking-[0.4em] uppercase mb-2">Create account</div>
          <h1 className="font-serif text-3xl italic mb-6">Get started.</h1>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input label="Username" type="text" value={name} onChange={setName} required placeholder="johndoe" />
            <Input label="Email" type="email" value={email} onChange={setEmail} required placeholder="you@company.com" />
            <Input label="Password" type="password" value={password} onChange={setPassword} required placeholder="Min 8 characters" />
            <Input label="Confirm password" type="password" value={confirm} onChange={setConfirm} required />
            {error && (
              <div className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded px-3 py-2">{error}</div>
            )}
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? <><Spinner size={12} /> Creating...</> : 'Create account'}
            </Button>
          </form>
          <div className="mt-6 pt-4 border-t border-[#1c1c1a] text-center">
            <Link href="/login" className="font-mono text-xs text-[#8a8275] hover:text-[#f5f1e8] tracking-wider uppercase">
              Already have an account? Sign in →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
