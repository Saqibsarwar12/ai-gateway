'use client';

import { FormEvent, Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Button, Input, Spinner } from '@/components/UI';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api-proxy';

type Status = 'form' | 'verifying' | 'success' | 'error';

function VerifyEmailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryEmail = searchParams.get('email') || '';
  const [email, setEmail] = useState(queryEmail);
  const [code, setCode] = useState('');
  const [status, setStatus] = useState<Status>('form');
  const [message, setMessage] = useState('');

  async function submit(e: FormEvent) {
    e.preventDefault();
    setMessage('');
    setStatus('verifying');
    try {
      const res = await fetch(`${API_BASE}/admin/auth/verify-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ email: email.trim(), code: code.trim() }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || 'Verification failed');
      localStorage.setItem('ai_gateway_token', body.access_token);
      localStorage.setItem('ai_gateway_user', JSON.stringify(body.user));
      setStatus('success');
      setMessage(body.message || 'Email verified. Your account is now active.');
      window.setTimeout(() => router.replace('/admin'), 1200);
    } catch (err: any) {
      setStatus('error');
      setMessage(err.message || 'Verification failed');
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0908] text-[#f5f1e8] flex items-center justify-center p-6">
      <div className="w-full max-w-md border border-[#1c1c1a] bg-[#13110f] p-8 rounded-sm">
        <div className="font-mono text-[10px] text-[#d4a574] tracking-[0.4em] uppercase">Email verification</div>
        {status === 'success' ? (
          <>
            <div className="mt-5 text-[#74d4a5] text-5xl">✓</div>
            <h1 className="mt-3 font-serif text-3xl italic">You're verified.</h1>
            <p className="mt-3 text-sm text-[#8a8275] leading-relaxed">{message}</p>
            <p className="mt-3 text-xs text-[#6b6358]">Signing you in and opening your dashboard…</p>
          </>
        ) : status === 'error' ? (
          <>
            <div className="mt-5 text-red-400 text-4xl">!</div>
            <h1 className="mt-3 font-serif text-3xl italic">Verification failed.</h1>
            <p className="mt-3 text-sm text-red-300 leading-relaxed">{message}</p>
            <Link href="/signup" className="mt-6 inline-block font-mono text-xs text-[#d4a574] uppercase tracking-wider">Register again →</Link>
          </>
        ) : (
          <>
            <h1 className="mt-3 font-serif text-3xl italic">Enter your code.</h1>
            <p className="mt-3 text-sm text-[#8a8275] leading-relaxed">We emailed a 6-digit code to <strong>{email}</strong> to activate your account. The code expires in 15 minutes.</p>
            <form onSubmit={submit} className="mt-6 flex flex-col gap-4">
              <Input label="Email" type="email" value={email} onChange={setEmail} required autoComplete="email" />
              <Input
                label="6-digit verification code"
                type="text"
                value={code}
                onChange={(value) => setCode(value.replace(/\D/g, '').slice(0, 6))}
                required
                minLength={6}
                maxLength={6}
                inputMode="numeric"
                autoComplete="one-time-code"
                placeholder="000000"
              />
              {message && <div className="text-sm border rounded px-3 py-2 text-[#d4a574] border-[#d4a574]/20 bg-[#d4a574]/10">{message}</div>}
              <Button type="submit" disabled={status === 'verifying' || code.length !== 6} className="w-full">
                {status === 'verifying' ? <><Spinner size={12} /> Verifying...</> : 'Verify email'}
              </Button>
            </form>
            <div className="mt-6 pt-4 border-t border-[#1c1c1a] flex justify-between">
              <Link href="/signup" className="font-mono text-xs text-[#8a8275] uppercase tracking-wider">Register again →</Link>
              <Link href="/login" className="font-mono text-xs text-[#8a8275] uppercase tracking-wider">Sign in →</Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}


export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-[#0a0908] text-[#f5f1e8] flex items-center justify-center p-6">
        <div className="w-full max-w-md border border-[#1c1c1a] bg-[#13110f] p-8 rounded-sm">
          <div className="font-mono text-[10px] text-[#d4a574] tracking-[0.4em] uppercase">Email verification</div>
          <h1 className="mt-3 font-serif text-3xl italic text-[#8a8275]">Loading...</h1>
          <div className="mt-4 flex items-center gap-2">
            <Spinner size={12} />
            <span className="text-xs font-mono text-[#6b6358]">Please wait</span>
          </div>
        </div>
      </div>
    }>
      <VerifyEmailContent />
    </Suspense>
  );
}
