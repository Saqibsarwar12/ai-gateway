'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';

type Status = 'loading' | 'success' | 'error';

export default function VerifyEmailPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get('token');
  const [status, setStatus] = useState<Status>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('Missing verification token.');
      return;
    }

    let cancelled = false;
    async function verify() {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || '/api-proxy'}/admin/auth/verify-email?token=${encodeURIComponent(token)}`,
        );
        const body = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(body.detail || 'Verification failed');
        }
        if (!cancelled) {
          setStatus('success');
          setMessage(body.message || 'Email verified. Your account is now active.');
        }
      } catch (err: any) {
        if (!cancelled) {
          setStatus('error');
          setMessage(err.message || 'Invalid or expired verification link.');
        }
      }
    }

    verify();
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <div className="min-h-screen bg-[#0a0908] text-[#f5f1e8] flex items-center justify-center p-6">
      <div className="w-full max-w-md border border-[#1c1c1a] bg-[#13110f] p-8 rounded-sm">
        <div className="font-mono text-[10px] text-[#d4a574] tracking-[0.4em] uppercase">Email verification</div>
        <h1 className="mt-3 font-serif text-3xl italic">
          {status === 'loading' && 'Verifying...'}
          {status === 'success' && "You're in."}
          {status === 'error' && 'Link expired or invalid.'}
        </h1>
        <p className="mt-3 text-sm text-[#8a8275] leading-relaxed">{message}</p>
        {status === 'success' && (
          <button
            onClick={() => router.push('/login')}
            className="mt-6 inline-block font-mono text-xs text-[#d4a574] uppercase tracking-wider"
          >
            Continue to sign in →
          </button>
        )}
        {status === 'error' && (
          <Link href="/signup" className="mt-6 inline-block font-mono text-xs text-[#d4a574] uppercase tracking-wider">
            Register again →
          </Link>
        )}
      </div>
    </div>
  );
}
