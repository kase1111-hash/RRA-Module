'use client';

import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Check, Shield, Users, Building2, Sparkles, MessageCircle } from 'lucide-react';
import { useAccount } from 'wagmi';
import { ConnectButton } from '@rainbow-me/rainbowkit';

interface LicenseTier {
  id: string;
  name: string;
  price: string;
  priceUsd: string;
  description: string;
  features: string[];
  icon: React.ReactNode;
  popular?: boolean;
}

// Mock repository data
const mockRepos: Record<string, { name: string; owner: string; description: string }> = {
  'rra-module-abc123': {
    name: 'RRA-Module',
    owner: 'kase1111-hash',
    description: 'Revenant Repo Agent Module - Transform dormant GitHub repositories into autonomous, revenue-generating agents.',
  },
  'web3-utils-def456': {
    name: 'web3-utils',
    owner: 'example',
    description: 'A comprehensive library of utility functions for Web3 development.',
  },
  'ml-pipeline-ghi789': {
    name: 'ml-pipeline',
    owner: 'example',
    description: 'End-to-end machine learning pipeline framework with built-in feature engineering.',
  },
};

const licenseTiers: LicenseTier[] = [
  {
    id: 'individual',
    name: 'Individual',
    price: '0.02 ETH',
    priceUsd: '~$50',
    description: 'Perfect for solo developers and personal projects',
    features: [
      'Single developer license',
      'Full source code access',
      'Bug fix updates',
      'Community support',
      'Personal & commercial use',
    ],
    icon: <Shield className="h-6 w-6" />,
  },
  {
    id: 'team',
    name: 'Team',
    price: '0.05 ETH',
    priceUsd: '~$125',
    description: 'Ideal for small teams and startups',
    features: [
      'Up to 5 developer seats',
      'Full source code access',
      'Priority bug fixes',
      'Email support',
      'Commercial use',
      'Modification rights',
    ],
    icon: <Users className="h-6 w-6" />,
    popular: true,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: '0.15 ETH',
    priceUsd: '~$375',
    description: 'For large organizations with custom needs',
    features: [
      'Unlimited developer seats',
      'Full source code access',
      'Priority support (24h SLA)',
      'Custom modifications',
      'White-label rights',
      'Dedicated account manager',
      'Custom integrations',
    ],
    icon: <Building2 className="h-6 w-6" />,
  },
];

export default function LicenseTierPage() {
  const params = useParams();
  const router = useRouter();
  const { isConnected } = useAccount();

  const id = params.id as string;
  const tierParam = params.tier as string;

  const repo = mockRepos[id] || {
    name: 'Repository',
    owner: 'unknown',
    description: 'No description available',
  };

  const selectedTier = licenseTiers.find((t) => t.id === tierParam) || licenseTiers[1];

  const handlePurchase = () => {
    // In production, this would trigger the blockchain transaction
    alert(`Initiating purchase of ${selectedTier.name} license for ${selectedTier.price}`);
  };

  const handleNegotiate = () => {
    router.push(`/agent/${id}/chat`);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.back()}
              className="rounded-lg p-2 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <ArrowLeft className="h-5 w-5 text-gray-600 dark:text-gray-400" />
            </button>
            <div>
              <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
                {repo.name} - {selectedTier.name} License
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {repo.owner}
              </p>
            </div>
          </div>
          <ConnectButton />
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid gap-8 lg:grid-cols-3">
          {/* Main Content - Selected Tier Details */}
          <div className="lg:col-span-2">
            <div className="rounded-2xl bg-white p-8 shadow-sm dark:bg-gray-800">
              <div className="flex items-center gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-primary-100 text-primary-600 dark:bg-primary-900 dark:text-primary-400">
                  {selectedTier.icon}
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                    {selectedTier.name} License
                  </h2>
                  <p className="text-gray-600 dark:text-gray-400">
                    {selectedTier.description}
                  </p>
                </div>
                {selectedTier.popular && (
                  <span className="ml-auto flex items-center gap-1 rounded-full bg-amber-100 px-3 py-1 text-sm font-medium text-amber-700 dark:bg-amber-900 dark:text-amber-300">
                    <Sparkles className="h-4 w-4" />
                    Most Popular
                  </span>
                )}
              </div>

              <div className="mt-8">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  What's Included
                </h3>
                <ul className="mt-4 space-y-3">
                  {selectedTier.features.map((feature, index) => (
                    <li key={index} className="flex items-start gap-3">
                      <Check className="mt-0.5 h-5 w-5 flex-shrink-0 text-green-500" />
                      <span className="text-gray-700 dark:text-gray-300">{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="mt-8 border-t border-gray-200 pt-8 dark:border-gray-700">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Repository Details
                </h3>
                <p className="mt-2 text-gray-600 dark:text-gray-400">
                  {repo.description}
                </p>
                <Link
                  href={`/agent/${id}`}
                  className="mt-4 inline-block text-primary-600 hover:underline dark:text-primary-400"
                >
                  View full repository details
                </Link>
              </div>
            </div>

            {/* Other Tiers */}
            <div className="mt-8">
              <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
                Other License Options
              </h3>
              <div className="grid gap-4 sm:grid-cols-2">
                {licenseTiers
                  .filter((t) => t.id !== selectedTier.id)
                  .map((tier) => (
                    <Link
                      key={tier.id}
                      href={`/agent/${id}/license/${tier.id}`}
                      className="rounded-xl border border-gray-200 bg-white p-4 transition-all hover:border-primary-300 hover:shadow-md dark:border-gray-700 dark:bg-gray-800 dark:hover:border-primary-600"
                    >
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                          {tier.icon}
                        </div>
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white">
                            {tier.name}
                          </p>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            {tier.price}
                          </p>
                        </div>
                      </div>
                    </Link>
                  ))}
              </div>
            </div>
          </div>

          {/* Sidebar - Purchase Card */}
          <div className="lg:col-span-1">
            <div className="sticky top-8 rounded-2xl bg-white p-6 shadow-sm dark:bg-gray-800">
              <div className="text-center">
                <p className="text-sm text-gray-600 dark:text-gray-400">Price</p>
                <p className="mt-1 text-4xl font-bold text-gray-900 dark:text-white">
                  {selectedTier.price}
                </p>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-500">
                  {selectedTier.priceUsd}
                </p>
              </div>

              {isConnected ? (
                <>
                  <button
                    onClick={handlePurchase}
                    className="mt-6 w-full rounded-xl bg-primary-600 py-3 font-medium text-white transition-colors hover:bg-primary-700"
                  >
                    Purchase License
                  </button>
                  <button
                    onClick={handleNegotiate}
                    className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-gray-300 py-3 font-medium text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
                  >
                    <MessageCircle className="h-4 w-4" />
                    Negotiate Price
                  </button>
                </>
              ) : (
                <div className="mt-6">
                  <p className="mb-4 text-center text-sm text-gray-600 dark:text-gray-400">
                    Connect your wallet to purchase
                  </p>
                  <div className="flex justify-center">
                    <ConnectButton />
                  </div>
                </div>
              )}

              <div className="mt-6 border-t border-gray-200 pt-6 dark:border-gray-700">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                  Secure Purchase
                </h4>
                <ul className="mt-3 space-y-2 text-sm text-gray-600 dark:text-gray-400">
                  <li className="flex items-center gap-2">
                    <Check className="h-4 w-4 text-green-500" />
                    NFT license delivered instantly
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="h-4 w-4 text-green-500" />
                    On-chain verification
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="h-4 w-4 text-green-500" />
                    Transferable license
                  </li>
                </ul>
              </div>

              <div className="mt-6 text-center">
                <p className="text-xs text-gray-500 dark:text-gray-500">
                  By purchasing, you agree to the{' '}
                  <Link href="/terms" className="text-primary-600 hover:underline dark:text-primary-400">
                    Terms of Service
                  </Link>
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
