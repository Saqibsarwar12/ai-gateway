// Clerk shim — re-exports from @clerk/nextjs when configured, otherwise no-op stubs.
// This lets the app boot on Render without Clerk env vars while still using real
// Clerk components in environments that configure them.

import React, { type ReactNode } from 'react';

export const CLERK_ENABLED = !!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

type AnyComponent = (props: any) => React.ReactElement | null;
type AnyHook = (...args: any[]) => any;

// No-op stubs (used when Clerk is disabled)
const Fragment = ({ children }: { children?: ReactNode }) =>
  React.createElement(React.Fragment, null, children);

const RenderChildren = ({ children }: { children?: ReactNode }) =>
  React.createElement(React.Fragment, null, children);

const Null = () => null;

const useUserStub = () => ({ isLoaded: true as const, isSignedIn: false, user: null });

// Real Clerk re-exports (used when Clerk is enabled). Lazily required so the
// disabled branch never touches the package.
let cached: any = null;
function getReal(): any {
  if (!cached) {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    cached = require('@clerk/nextjs');
  }
  return cached;
}

const wrap = (name: string): AnyComponent => (props) =>
  React.createElement(getReal()[name], props, props.children);

export const ClerkProvider: AnyComponent = CLERK_ENABLED ? wrap('ClerkProvider') : Fragment;
export const SignedIn: AnyComponent = CLERK_ENABLED ? wrap('SignedIn') : Null;
export const SignedOut: AnyComponent = CLERK_ENABLED ? wrap('SignedOut') : Fragment;
export const SignInButton: AnyComponent = CLERK_ENABLED ? wrap('SignInButton') : RenderChildren;
export const SignUpButton: AnyComponent = CLERK_ENABLED ? wrap('SignUpButton') : RenderChildren;
export const SignOutButton: AnyComponent = CLERK_ENABLED ? wrap('SignOutButton') : RenderChildren;
export const SignIn: AnyComponent = CLERK_ENABLED ? wrap('SignIn') : Null;
export const SignUp: AnyComponent = CLERK_ENABLED ? wrap('SignUp') : Null;

export const useUser: AnyHook = CLERK_ENABLED
  ? (...args: any[]) => getReal().useUser(...args)
  : useUserStub;
