import Link from 'next/link';
import { ChevronRight, GitBranch, Bot, FileCheck, Coins, ArrowRight } from 'lucide-react';

const steps = [
  {
    icon: GitBranch,
    title: '1. Register Your Repository',
    description: 'Initialize your repository with RRA to create a .market.yaml configuration file. This defines your licensing terms, pricing tiers, and royalty structure.',
    code: 'rra init .\nrra ingest',
  },
  {
    icon: Bot,
    title: '2. Deploy Your Agent',
    description: 'Your repository gets an AI negotiation agent that can discuss licensing terms, answer questions about your code, and handle purchase requests autonomously.',
    code: '# Agent deployed automatically\n# Available at /agent/your-repo-id',
  },
  {
    icon: FileCheck,
    title: '3. On-Chain IP Registration',
    description: 'Your code is registered as an IP Asset on Story Protocol. This creates an immutable record of ownership and enables programmable licensing.',
    code: '# IP Asset ID: 0xabcd...1234\n# Royalty Vault: 0x9876...5678',
  },
  {
    icon: Coins,
    title: '4. Earn Royalties',
    description: 'When users license your code, payment flows through Story Protocol. Royalties are automatically distributed to your wallet based on your terms.',
    code: '# Claim royalties anytime\nnode scripts/claim-royalties.js',
  },
];

export default function HowItWorksPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-gray-500">
          <Link href="/docs" className="hover:text-gray-700 dark:hover:text-gray-300">Docs</Link>
          <ChevronRight className="h-4 w-4" />
          <span className="text-gray-900 dark:text-white">How It Works</span>
        </nav>

        <h1 className="mt-6 text-4xl font-bold text-gray-900 dark:text-white">
          How RRA Works
        </h1>
        <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
          RRA (Revenant Repo Agent) transforms your code repository into a licensable IP asset
          with AI-powered negotiation and on-chain royalty enforcement.
        </p>

        {/* Steps */}
        <div className="mt-12 space-y-12">
          {steps.map((step, index) => (
            <div key={index} className="relative">
              {index < steps.length - 1 && (
                <div className="absolute left-6 top-16 h-full w-0.5 bg-gray-200 dark:bg-gray-700" />
              )}
              <div className="flex gap-6">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-900">
                  <step.icon className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
                </div>
                <div className="flex-1">
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                    {step.title}
                  </h2>
                  <p className="mt-2 text-gray-600 dark:text-gray-300">
                    {step.description}
                  </p>
                  <pre className="mt-4 overflow-x-auto rounded-lg bg-gray-900 p-4 text-sm text-gray-100">
                    <code>{step.code}</code>
                  </pre>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Architecture Diagram */}
        <div className="mt-16">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Architecture</h2>
          <div className="mt-6 rounded-xl border border-gray-200 bg-white p-8 dark:border-gray-700 dark:bg-gray-800">
            <div className="grid grid-cols-3 gap-4 text-center text-sm">
              <div className="rounded-lg bg-blue-100 p-4 dark:bg-blue-900/30">
                <div className="font-semibold text-blue-700 dark:text-blue-300">Your Repository</div>
                <div className="mt-1 text-blue-600 dark:text-blue-400">GitHub/GitLab</div>
              </div>
              <div className="rounded-lg bg-purple-100 p-4 dark:bg-purple-900/30">
                <div className="font-semibold text-purple-700 dark:text-purple-300">RRA Module</div>
                <div className="mt-1 text-purple-600 dark:text-purple-400">AI Agent + Config</div>
              </div>
              <div className="rounded-lg bg-green-100 p-4 dark:bg-green-900/30">
                <div className="font-semibold text-green-700 dark:text-green-300">Story Protocol</div>
                <div className="mt-1 text-green-600 dark:text-green-400">On-chain IP</div>
              </div>
            </div>
            <div className="mt-4 flex justify-center">
              <ArrowRight className="h-6 w-6 text-gray-400" />
            </div>
            <div className="mt-4 rounded-lg bg-indigo-100 p-4 text-center dark:bg-indigo-900/30">
              <div className="font-semibold text-indigo-700 dark:text-indigo-300">RRA Marketplace</div>
              <div className="mt-1 text-indigo-600 dark:text-indigo-400">Discovery + Licensing + Royalties</div>
            </div>
          </div>
        </div>

        {/* Next Steps */}
        <div className="mt-12 flex gap-4">
          <Link
            href="/docs/quickstart"
            className="rounded-lg bg-indigo-600 px-6 py-3 font-medium text-white hover:bg-indigo-700"
          >
            Get Started →
          </Link>
          <Link
            href="/docs/market-yaml"
            className="rounded-lg border border-gray-300 px-6 py-3 font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            Configuration Guide
          </Link>
        </div>
      </div>
    </div>
  );
}
