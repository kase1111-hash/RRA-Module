'use client';

import dynamic from 'next/dynamic';
import { Suspense, type ReactNode } from 'react';

/**
 * Loading skeleton for wallet connection UI
 */
function WalletLoadingFallback() {
  return (
    <div className="animate-pulse">
      <div className="h-10 w-32 rounded-lg bg-gray-200" />
    </div>
  );
}

/**
 * Lazy-loaded wallet providers.
 *
 * This component dynamically imports the heavy Web3 libraries (wagmi, viem, rainbowkit)
 * only when needed, reducing initial bundle size for pages that don't require wallet
 * functionality.
 *
 * Usage:
 * - Wrap components that need wallet access with <WalletProvider>
 * - Use on specific pages rather than the root layout
 */
const WalletProviderInner = dynamic(
  () => import('./WalletProviderInner').then((mod) => mod.WalletProviderInner),
  {
    ssr: false, // Wallet functionality is client-only
    loading: () => <WalletLoadingFallback />,
  }
);

interface WalletProviderProps {
  children: ReactNode;
}

export function WalletProvider({ children }: WalletProviderProps) {
  return (
    <Suspense fallback={<WalletLoadingFallback />}>
      <WalletProviderInner>{children}</WalletProviderInner>
    </Suspense>
  );
}

/**
 * Lazy-loaded connect button.
 *
 * Use this instead of importing ConnectButton directly from rainbowkit
 * to enable code splitting.
 */
export const LazyConnectButton = dynamic(
  () => import('@rainbow-me/rainbowkit').then((mod) => mod.ConnectButton),
  {
    ssr: false,
    loading: () => <WalletLoadingFallback />,
  }
);
