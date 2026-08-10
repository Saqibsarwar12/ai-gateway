'use client';

import { Suspense, useEffect, useState, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Spinner } from '@/components/UI';

type Status = 'loading' | 'verifying' | 'success' | 'error';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api-proxy';

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get('token');
  const [status, setStatus] = useState<Status>('loading');
  const [message, setMessage] = useState('');

  const performAutoLogin = useCallback(async () => {
    sessionStorage.setItem('just_verified', 'true');
    router.push('/login?verified=1');
  }, [router]);

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('Missing verification token.');
      return;
    }

    setStatus('verifying');
    let cancelled = false;

    async function verify() {
      try {
        const apiBase = API_BASE;
        const res = await fetch(
          `${apiBase}/admin/auth/verify-email?token=${encodeURIComponent(token!)}`,
          { method: 'GET' }
        );
        const body = await res.json().catch(() => ({}));

        if (!res.ok) {
          throw new Error(body.detail || 'Verification failed');
        }

        if (!cancelled) {
          setStatus('success');
          setMessage(body.message || 'Email verified. Your account is now active.');

          if (body.email) {
            sessionStorage.setItem('verified_email', body.email);
          }

          setTimeout(() => {
            if (!cancelled) performAutoLogin();
          }, 2000);
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
  }, [token, performAutoLogin]);

  return (
    <div className="min-h-screen bg-[#0a0908] text-[#f5f1e8] flex items-center justify-center p-6">
      <div className="w-full max-w-md border border-[#1c1c1a] bg-[#13110f] p-8 rounded-sm">
        <div className="font-mono text-[10px] text-[#d4a574] tracking-[0.4em] uppercase">Email verification</div>

        {status === 'loading' && (
          <>
            <h1 className="mt-3 font-serif text-3xl italic text-[#8a8275]">Loading...</h1>
            <p className="mt-3 text-sm text-[#6b6358] leading-relaxed">Please wait.</p>
          </>
        )}

        {status === 'verifying' && (
          <>
            <h1 className="mt-3 font-serif text-3xl italic">Verifying...</h1>
            <p className="mt-3 text-sm text-[#8a8275] leading-relaxed">Checking your verification link. Do not close this page.</p>
            <div className="mt-4 flex items-center gap-2">
              <Spinner size={12} />
              <span className="text-xs font-mono text-[#6b6358]">Activating your account</span>
            </div>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="mt-2">
              <div className="text-[#74d4a5] text-4xl">✓</div>
            </div>
            <h1 className="mt-3 font-serif text-3xl italic">You're verified.</h1>
            <p className="mt-3 text-sm text-[#8a8275] leading-relaxed">{message}</p>
            <p className="mt-2 text-xs text-[#6b6358] leading-relaxed">Redirecting you to sign in...</p>
            <div className="mt-4 flex items-center gap-2">
              <Spinner size={12} />
              <span className="text-xs font-mono text-[#6b6358]">Redirecting...</span>
            </div>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="mt-2">
              <div className="text-red-400 text-4xl">✗</div>
            </div>
            <h1 className="mt-3 font-serif text-3xl italic">Link invalid or expired.</h1>
            <p className="mt-3 text-sm text-[#8a8275] leading-relaxed">{message}</p>
            <div className="mt-6 flex flex-col gap-3">
              <Link
                href="/signup"
                className="font-mono text-xs text-[#d4a574] uppercase tracking-wider hover:text-[#c89960]"
              >
                Register again →
              </Link>
              <Link
                href="/login"
                className="font-mono text-xs text-[#6b6358] uppercase tracking-wider hover:text-[#8a8275]"
              >
                Go to sign in →
              </Link>
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
