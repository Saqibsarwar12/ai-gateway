import { SignUp } from '@clerk/nextjs';

export default function SignUpPage() {
  return (
    <main className="min-h-screen bg-[#0a0908] flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="font-mono text-[10px] text-[#d4a574] tracking-[0.4em] uppercase mb-6 text-center">◇ ai-gateway</div>
        <SignUp
          routing="path"
          path="/sign-up"
          signInUrl="/sign-in"
          afterSignUpUrl="/keys"
        />
      </div>
    </main>
  );
}
