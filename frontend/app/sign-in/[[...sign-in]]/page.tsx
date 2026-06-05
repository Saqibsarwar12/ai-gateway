import { SignIn } from '@/lib/clerk-shim';

export default function SignInPage() {
  return (
    <main className="min-h-screen bg-[#0a0908] flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="font-mono text-[10px] text-[#d4a574] tracking-[0.4em] uppercase mb-6 text-center">◇ ai-gateway</div>
        <SignIn
          routing="path"
          path="/sign-in"
          signUpUrl="/sign-up"
          fallbackRedirectUrl="/keys"
        />
      </div>
    </main>
  );
}
