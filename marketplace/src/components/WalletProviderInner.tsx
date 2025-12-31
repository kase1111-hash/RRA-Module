'use client';

import { useState, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WagmiProvider } from 'wagmi';
import { mainnet, polygon, arbitrum, sepolia } from 'wagmi/chains';
import { RainbowKitProvider, getDefaultConfig } from '@rainbow-me/rainbowkit';
import '@rainbow-me/rainbowkit/styles.css';

/**
 * Configure wagmi with supported chains.
 *
 * Only imported when WalletProviderInner is loaded.
 */
const config = getDefaultConfig({
  appName: 'RRA Marketplace',
  projectId: process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID || 'demo',
  chains: [mainnet, polygon, arbitrum, sepolia],
  ssr: false, // Client-only
});

interface WalletProviderInnerProps {
  children: ReactNode;
}

/**
 * Inner wallet provider component.
 *
 * This is dynamically imported by WalletProvider to enable code splitting.
 * Contains the heavy Web3 dependencies (wagmi, viem, rainbowkit).
 */
export function WalletProviderInner({ children }: WalletProviderInnerProps) {
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
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <RainbowKitProvider>{children}</RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}
