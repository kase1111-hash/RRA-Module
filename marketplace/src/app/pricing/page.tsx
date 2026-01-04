'use client';

import Link from 'next/link';
import { Check, Zap, Building2, Rocket } from 'lucide-react';

const tiers = [
  {
    name: 'Personal',
    price: '0.01',
    unit: 'WIP',
    description: 'For individual developers and small projects',
    icon: Zap,
    features: [
      'Single repository license',
      'Non-commercial use',
      'Community support',
      'Basic documentation access',
      'GitHub integration',
    ],
    cta: 'Get Started',
    highlighted: false,
  },
  {
    name: 'Professional',
    price: '0.1',
    unit: 'WIP',
    description: 'For teams and commercial applications',
    icon: Rocket,
    features: [
      'Up to 10 repository licenses',
      'Commercial use allowed',
      'Priority support',
      'Full API access',
      'Royalty sharing (5%)',
      'Derivative tracking',
    ],
    cta: 'Start Free Trial',
    highlighted: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    unit: '',
    description: 'For large organizations with custom needs',
    icon: Building2,
    features: [
      'Unlimited repositories',
      'White-label options',
      'Dedicated support',
      'Custom royalty terms',
      'On-chain governance',
      'SLA guarantees',
      'Custom integrations',
    ],
    cta: 'Contact Sales',
    highlighted: false,
  },
];

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-800">
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-5xl">
            Simple, Transparent Pricing
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-gray-600 dark:text-gray-300">
            License code directly from creators with on-chain royalty enforcement.
            Pay once, use forever with Story Protocol integration.
          </p>
        </div>

        {/* Pricing Cards */}
        <div className="mt-16 grid gap-8 lg:grid-cols-3">
          {tiers.map((tier) => (
            <div
              key={tier.name}
              className={`relative rounded-2xl p-8 ${
                tier.highlighted
                  ? 'bg-indigo-600 text-white shadow-xl ring-2 ring-indigo-600'
                  : 'bg-white text-gray-900 shadow-lg ring-1 ring-gray-200 dark:bg-gray-800 dark:text-white dark:ring-gray-700'
              }`}
            >
              {tier.highlighted && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 rounded-full bg-indigo-500 px-4 py-1 text-sm font-medium text-white">
                  Most Popular
                </div>
              )}

              <div className="flex items-center gap-3">
                <tier.icon className={`h-8 w-8 ${tier.highlighted ? 'text-indigo-200' : 'text-indigo-600'}`} />
                <h2 className="text-2xl font-bold">{tier.name}</h2>
              </div>

              <p className={`mt-2 text-sm ${tier.highlighted ? 'text-indigo-100' : 'text-gray-500 dark:text-gray-400'}`}>
                {tier.description}
              </p>

              <div className="mt-6">
                <span className="text-4xl font-bold">{tier.price}</span>
                {tier.unit && (
                  <span className={`ml-2 text-lg ${tier.highlighted ? 'text-indigo-200' : 'text-gray-500'}`}>
                    {tier.unit}
                  </span>
                )}
              </div>

              <ul className="mt-8 space-y-3">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-3">
                    <Check className={`h-5 w-5 flex-shrink-0 ${tier.highlighted ? 'text-indigo-200' : 'text-green-500'}`} />
                    <span className={`text-sm ${tier.highlighted ? 'text-indigo-50' : 'text-gray-600 dark:text-gray-300'}`}>
                      {feature}
                    </span>
                  </li>
                ))}
              </ul>

              <Link
                href="/search"
                className={`mt-8 block w-full rounded-lg py-3 text-center font-medium transition ${
                  tier.highlighted
                    ? 'bg-white text-indigo-600 hover:bg-indigo-50'
                    : 'bg-indigo-600 text-white hover:bg-indigo-700'
                }`}
              >
                {tier.cta}
              </Link>
            </div>
          ))}
        </div>

        {/* FAQ Section */}
        <div className="mt-20">
          <h2 className="text-center text-2xl font-bold text-gray-900 dark:text-white">
            Frequently Asked Questions
          </h2>
          <div className="mt-8 grid gap-6 md:grid-cols-2">
            <div className="rounded-lg bg-white p-6 shadow dark:bg-gray-800">
              <h3 className="font-semibold text-gray-900 dark:text-white">What is WIP?</h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                WIP (Wrapped IP) is the payment token used on Story Protocol. It&apos;s used for
                licensing transactions and royalty payments on the IP blockchain.
              </p>
            </div>
            <div className="rounded-lg bg-white p-6 shadow dark:bg-gray-800">
              <h3 className="font-semibold text-gray-900 dark:text-white">How do royalties work?</h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                Royalties are automatically enforced on-chain via Story Protocol. When derivative
                works generate revenue, creators receive their share automatically.
              </p>
            </div>
            <div className="rounded-lg bg-white p-6 shadow dark:bg-gray-800">
              <h3 className="font-semibold text-gray-900 dark:text-white">Can I upgrade my license?</h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                Yes! You can upgrade from Personal to Professional at any time. Just pay the
                difference and your license NFT will be updated on-chain.
              </p>
            </div>
            <div className="rounded-lg bg-white p-6 shadow dark:bg-gray-800">
              <h3 className="font-semibold text-gray-900 dark:text-white">What blockchain is used?</h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                RRA uses Story Protocol on the IP blockchain (Chain ID 1514). All licenses are
                minted as NFTs with on-chain royalty enforcement.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
