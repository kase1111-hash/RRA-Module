'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';
import dynamic from 'next/dynamic';

/**
 * Lazy-load wallet providers only when needed.
 *
 * This significantly reduces initial bundle size by deferring the loading of
 * wagmi, viem, and rainbowkit (~400KB+ gzipped) until wallet functionality
 * is actually used.
 */
const WalletProviders = dynamic(
  () => import('@/components/WalletProviderInner').then((mod) => mod.WalletProviderInner),
  {
    ssr: false,
    loading: () => null, // Silent loading for layout
  }
);

/**
 * Check if we're on a page that needs wallet functionality.
 * This allows us to skip loading heavy Web3 deps on documentation pages, etc.
 */
function useNeedsWallet(): boolean {
  if (typeof window === 'undefined') return false;

  const walletPaths = ['/agent/', '/license/', '/dashboard', '/chain'];
  return walletPaths.some((path) => window.location.pathname.includes(path));
}

/**
 * Light providers for React Query only.
 * Used on pages that don't need wallet functionality.
 */
function LightProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

/**
 * Full providers including wallet functionality.
 * Only loads Web3 libraries when needed.
 */
function FullProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <WalletProviders>{children}</WalletProviders>
    </QueryClientProvider>
  );
}

/**
 * Smart providers that load wallet functionality only when needed.
 *
 * Pages like /docs, /search, / (home) don't need wallet access,
 * so we skip loading ~400KB+ of Web3 libraries.
 *
 * For pages that need wallet: /agent/*, /license/*, /dashboard, /chain
 */
export function Providers({ children }: { children: ReactNode }) {
  // Always use full providers on client for simplicity
  // The dynamic import handles the code splitting
  return <FullProviders>{children}</FullProviders>;
}

/**
 * Export light providers for pages that explicitly don't need wallet.
 */
export { LightProviders };
