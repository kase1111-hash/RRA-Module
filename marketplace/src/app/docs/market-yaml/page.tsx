import Link from 'next/link';
import { ChevronRight } from 'lucide-react';

const exampleConfig = `# .market.yaml - RRA Configuration File
version: "1.0"

# Repository metadata
metadata:
  name: "My Awesome Library"
  description: "A powerful library for doing awesome things"
  author: "Your Name"
  website: "https://github.com/you/awesome-lib"

# Story Protocol integration
story_protocol:
  chain_id: 1514  # Story Protocol mainnet
  ip_asset_id: "0x..."  # Set after registration
  royalty_vault: "0x..."  # Auto-generated

# License tiers
tiers:
  personal:
    name: "Personal"
    price: "0.01"
    currency: "WIP"
    terms:
      - "Non-commercial use only"
      - "Single developer"
      - "No redistribution"
    royalty_rate: 0  # No royalties on derivatives

  commercial:
    name: "Commercial"
    price: "0.1"
    currency: "WIP"
    terms:
      - "Commercial use allowed"
      - "Team up to 10 developers"
      - "Internal use only"
    royalty_rate: 5  # 5% on derivative revenue

  enterprise:
    name: "Enterprise"
    price: "1.0"
    currency: "WIP"
    terms:
      - "Unlimited commercial use"
      - "Unlimited developers"
      - "Redistribution allowed"
      - "White-label rights"
    royalty_rate: 2  # 2% on derivative revenue

# Agent configuration
agent:
  negotiation_enabled: true
  max_discount: 10  # Max 10% discount
  auto_approve_threshold: "0.5"  # Auto-approve under 0.5 WIP
  response_style: "professional"

# Verification settings
verification:
  require_did: false
  require_kyc: false
  blocked_regions: []`;

export default function MarketYamlPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-gray-500">
          <Link href="/docs" className="hover:text-gray-700 dark:hover:text-gray-300">Docs</Link>
          <ChevronRight className="h-4 w-4" />
          <span className="text-gray-900 dark:text-white">market.yaml Reference</span>
        </nav>

        <h1 className="mt-6 text-4xl font-bold text-gray-900 dark:text-white">
          market.yaml Reference
        </h1>
        <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
          The <code className="rounded bg-gray-200 px-1 dark:bg-gray-700">.market.yaml</code> file
          configures how your repository appears and behaves on the RRA Marketplace.
        </p>

        {/* Full Example */}
        <div className="mt-8">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Complete Example</h2>
          <pre className="mt-4 overflow-x-auto rounded-lg bg-gray-900 p-4 text-sm text-gray-100">
            <code>{exampleConfig}</code>
          </pre>
        </div>

        {/* Field Reference */}
        <div className="mt-12 space-y-8">
          <section>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Field Reference</h2>

            <div className="mt-6 space-y-6">
              <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
                <h3 className="font-mono text-lg font-semibold text-indigo-600 dark:text-indigo-400">metadata</h3>
                <p className="mt-2 text-gray-600 dark:text-gray-300">Basic information about your repository.</p>
                <table className="mt-4 w-full text-sm">
                  <thead>
                    <tr className="border-b dark:border-gray-700">
                      <th className="py-2 text-left font-medium">Field</th>
                      <th className="py-2 text-left font-medium">Type</th>
                      <th className="py-2 text-left font-medium">Description</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-600 dark:text-gray-300">
                    <tr className="border-b dark:border-gray-700">
                      <td className="py-2 font-mono">name</td>
                      <td className="py-2">string</td>
                      <td className="py-2">Display name for your project</td>
                    </tr>
                    <tr className="border-b dark:border-gray-700">
                      <td className="py-2 font-mono">description</td>
                      <td className="py-2">string</td>
                      <td className="py-2">Short description (max 200 chars)</td>
                    </tr>
                    <tr className="border-b dark:border-gray-700">
                      <td className="py-2 font-mono">author</td>
                      <td className="py-2">string</td>
                      <td className="py-2">Author or organization name</td>
                    </tr>
                    <tr>
                      <td className="py-2 font-mono">website</td>
                      <td className="py-2">string</td>
                      <td className="py-2">Project website or repo URL</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
                <h3 className="font-mono text-lg font-semibold text-indigo-600 dark:text-indigo-400">story_protocol</h3>
                <p className="mt-2 text-gray-600 dark:text-gray-300">Story Protocol blockchain configuration.</p>
                <table className="mt-4 w-full text-sm">
                  <thead>
                    <tr className="border-b dark:border-gray-700">
                      <th className="py-2 text-left font-medium">Field</th>
                      <th className="py-2 text-left font-medium">Type</th>
                      <th className="py-2 text-left font-medium">Description</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-600 dark:text-gray-300">
                    <tr className="border-b dark:border-gray-700">
                      <td className="py-2 font-mono">chain_id</td>
                      <td className="py-2">number</td>
                      <td className="py-2">1514 for mainnet, 1315 for testnet</td>
                    </tr>
                    <tr className="border-b dark:border-gray-700">
                      <td className="py-2 font-mono">ip_asset_id</td>
                      <td className="py-2">address</td>
                      <td className="py-2">Your IP Asset address (auto-set)</td>
                    </tr>
                    <tr>
                      <td className="py-2 font-mono">royalty_vault</td>
                      <td className="py-2">address</td>
                      <td className="py-2">Royalty vault address (auto-set)</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
                <h3 className="font-mono text-lg font-semibold text-indigo-600 dark:text-indigo-400">tiers</h3>
                <p className="mt-2 text-gray-600 dark:text-gray-300">License tier definitions. Each tier has:</p>
                <table className="mt-4 w-full text-sm">
                  <thead>
                    <tr className="border-b dark:border-gray-700">
                      <th className="py-2 text-left font-medium">Field</th>
                      <th className="py-2 text-left font-medium">Type</th>
                      <th className="py-2 text-left font-medium">Description</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-600 dark:text-gray-300">
                    <tr className="border-b dark:border-gray-700">
                      <td className="py-2 font-mono">name</td>
                      <td className="py-2">string</td>
                      <td className="py-2">Display name for the tier</td>
                    </tr>
                    <tr className="border-b dark:border-gray-700">
                      <td className="py-2 font-mono">price</td>
                      <td className="py-2">string</td>
                      <td className="py-2">Price in specified currency</td>
                    </tr>
                    <tr className="border-b dark:border-gray-700">
                      <td className="py-2 font-mono">currency</td>
                      <td className="py-2">string</td>
                      <td className="py-2">WIP, USDC, or ETH</td>
                    </tr>
                    <tr className="border-b dark:border-gray-700">
                      <td className="py-2 font-mono">terms</td>
                      <td className="py-2">string[]</td>
                      <td className="py-2">License terms as bullet points</td>
                    </tr>
                    <tr>
                      <td className="py-2 font-mono">royalty_rate</td>
                      <td className="py-2">number</td>
                      <td className="py-2">Percentage of derivative revenue</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        </div>

        {/* Next Steps */}
        <div className="mt-12 flex gap-4">
          <Link
            href="/docs/quickstart"
            className="rounded-lg bg-indigo-600 px-6 py-3 font-medium text-white hover:bg-indigo-700"
          >
            ← Quick Start
          </Link>
          <Link
            href="/docs/api"
            className="rounded-lg border border-gray-300 px-6 py-3 font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            API Reference →
          </Link>
        </div>
      </div>
    </div>
  );
}
