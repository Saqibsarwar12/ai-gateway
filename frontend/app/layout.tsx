import type { Metadata, Viewport } from 'next';
import './globals.css';
import { AuthProvider } from '@/lib/auth';
import { ClerkProvider } from '@clerk/nextjs';

export const metadata: Metadata = {
  title: 'AI Gateway — Every model. One endpoint.',
  description: 'Production AI routing platform — OpenAI-compatible gateway with multi-provider fallback.',
};

export const viewport: Viewport = {
  themeColor: '#0a0807',
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider
      publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY!}
      appearance={{
        variables: {
          colorBackground: '#0a0908',
          colorText: '#f5f1e8',
          colorPrimary: '#d4a574',
          colorInputBackground: '#14110f',
          colorInputText: '#f5f1e8',
          borderRadius: '2px',
          fontFamily: 'var(--font-mono, monospace)',
        },
        elements: {
          card: { background: '#14110f', border: '1px solid #2a2520', boxShadow: 'none' },
          headerTitle: { color: '#f5f1e8' },
          headerSubtitle: { color: '#8a8275' },
          formButtonPrimary: { background: '#d4a574', color: '#0a0908', borderRadius: '2px' },
          footerActionLink: { color: '#d4a574' },
        },
      }}
    >
      <html lang="en">
        <head>
          <link rel="preconnect" href="https://fonts.googleapis.com" />
          <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        </head>
        <body>
          <AuthProvider>{children}</AuthProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}
