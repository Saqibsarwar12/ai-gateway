'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import DashboardShell from '@/components/DashboardShell';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading, token } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login');
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
        <div className="text-xs mono" style={{ color: 'var(--fg-2)', letterSpacing: '0.18em', textTransform: 'uppercase' }}>
          Authenticating…
        </div>
      </div>
    );
  }

  if (!user || !token) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
        <div className="text-xs mono" style={{ color: 'var(--fg-2)', letterSpacing: '0.18em', textTransform: 'uppercase' }}>
          Redirecting…
        </div>
      </div>
    );
  }
  return <DashboardShell>{children}</DashboardShell>;
}
