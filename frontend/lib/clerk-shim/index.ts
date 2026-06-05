// Clerk shim — re-exports from @clerk/nextjs if a publishable key is configured,
// otherwise exports no-op stubs. This lets the app boot on Render without Clerk
// environment variables set, while keeping the real Clerk components when they
// are configured (production / staging).

export const CLERK_ENABLED = !!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

type AnyComponent = (props: any) => any;
type AnyFn = (...args: any[]) => any;

const passthrough: AnyComponent = ({ children }) => children;
const noopButton: AnyComponent = ({ children, ...rest }: any) => {
  const { children: _c, mode: _m, ...safe } = rest;
  return <button {...safe}>{children}</button>;
};
const safeLink: AnyComponent = ({ children, ...rest }: any) => {
  const { mode: _m, ...safe } = rest;
  return <a {...safe}>{children}</a>;
};

const useUserStub = () => ({ isLoaded: true, isSignedIn: false, user: null });

const SignInStub: AnyComponent = (props) => safeLink(props);
const SignUpStub: AnyComponent = (props) => safeLink(props);
const SignOutStub: AnyComponent = (props) => passthrough(props);

export const ClerkProvider: AnyComponent = CLERK_ENABLED
  ? require('@clerk/nextjs').ClerkProvider
  : passthrough;

export const SignedIn: AnyComponent = CLERK_ENABLED
  ? require('@clerk/nextjs').SignedIn
  : () => null;

export const SignedOut: AnyComponent = CLERK_ENABLED
  ? require('@clerk/nextjs').SignedOut
  : ({ children }: any) => children ?? null;

export const SignInButton: AnyComponent = CLERK_ENABLED
  ? require('@clerk/nextjs').SignInButton
  : noopButton;

export const SignUpButton: AnyComponent = CLERK_ENABLED
  ? require('@clerk/nextjs').SignUpButton
  : noopButton;

export const SignOutButton: AnyComponent = CLERK_ENABLED
  ? require('@clerk/nextjs').SignOutButton
  : noopButton;

export const SignIn: AnyComponent = CLERK_ENABLED
  ? require('@clerk/nextjs').SignIn
  : () => null;

export const SignUp: AnyComponent = CLERK_ENABLED
  ? require('@clerk/nextjs').SignUp
  : () => null;

export const useUser = CLERK_ENABLED ? require('@clerk/nextjs').useUser : useUserStub;
