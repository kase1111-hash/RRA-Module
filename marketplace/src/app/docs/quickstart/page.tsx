import Link from 'next/link';
import { ArrowLeft, ArrowRight, CheckCircle, Copy, FileCode, GitBranch, Rocket, Zap } from 'lucide-react';

const steps = [
  {
    number: 1,
    title: 'Create a .market.yaml file',
    description: 'Add a configuration file to the root of your repository',
    code: `# .market.yaml
license_identifier: MIT
license_model: per-seat
target_price: "0.05"
floor_price: "0.02"
negotiation_style: adaptive

features:
  - Full source access
  - 12 months updates
  - Developer support

developer_wallet: "0x..."
copyright_holder: "Your Name"`,
  },
  {
    number: 2,
    title: 'Push to GitHub',
    description: 'Commit and push your changes to trigger indexing',
    code: `git add .market.yaml
git commit -m "Add marketplace configuration"
git push origin main`,
  },
  {
    number: 3,
    title: 'Verify your repository',
    description: 'Our system will automatically verify your code and run security checks',
    code: null,
  },
  {
    number: 4,
    title: 'Start selling!',
    description: 'Your AI agent is now live and ready to negotiate licenses',
    code: null,
  },
];

export default function QuickstartPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-4 py-8 dark:border-gray-800 dark:bg-gray-800">
        <div className="mx-auto max-w-4xl">
          <Link
            href="/docs"
            className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back to Docs
          </Link>
          <div className="mt-4 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-600 text-white">
              <Rocket className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Quick Start Guide
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Get your repository on the marketplace in 5 minutes
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6 lg:px-8">
        {/* Prerequisites */}
        <div className="mb-12 rounded-xl border border-amber-200 bg-amber-50 p-6 dark:border-amber-800 dark:bg-amber-900/20">
          <h2 className="flex items-center gap-2 font-semibold text-amber-800 dark:text-amber-200">
            <Zap className="h-5 w-5" />
            Prerequisites
          </h2>
          <ul className="mt-3 space-y-2 text-amber-700 dark:text-amber-300">
            <li className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4" />
              A public GitHub repository
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4" />
              An Ethereum wallet for receiving payments
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4" />
              Code that passes basic security checks
            </li>
          </ul>
        </div>

        {/* Steps */}
        <div className="space-y-12">
          {steps.map((step, index) => (
            <div key={step.number} className="relative">
              {/* Connector line */}
              {index < steps.length - 1 && (
                <div className="absolute left-6 top-14 h-full w-0.5 bg-gray-200 dark:bg-gray-700" />
              )}

              <div className="flex gap-6">
                {/* Step number */}
                <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-primary-600 text-xl font-bold text-white">
                  {step.number}
                </div>

                {/* Step content */}
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                    {step.title}
                  </h3>
                  <p className="mt-1 text-gray-600 dark:text-gray-400">
                    {step.description}
                  </p>

                  {step.code && (
                    <div className="mt-4 overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
                      <div className="flex items-center justify-between bg-gray-100 px-4 py-2 dark:bg-gray-800">
                        <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                          <FileCode className="h-4 w-4" />
                          {step.number === 1 ? '.market.yaml' : 'Terminal'}
                        </div>
                        <button className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300">
                          <Copy className="h-4 w-4" />
                          Copy
                        </button>
                      </div>
                      <pre className="overflow-x-auto bg-gray-900 p-4 text-sm text-gray-100">
                        <code>{step.code}</code>
                      </pre>
                    </div>
                  )}

                  {step.number === 3 && (
                    <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-900/20">
                      <p className="text-sm text-green-700 dark:text-green-300">
                        Verification typically takes 2-5 minutes. You&apos;ll receive a verification
                        score and any security findings will be reported.
                      </p>
                    </div>
                  )}

                  {step.number === 4 && (
                    <div className="mt-4 rounded-lg border border-primary-200 bg-primary-50 p-4 dark:border-primary-800 dark:bg-primary-900/20">
                      <p className="text-sm text-primary-700 dark:text-primary-300">
                        Your repository will appear in the marketplace and buyers can start
                        negotiating with your AI agent immediately!
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Next Steps */}
        <div className="mt-12 rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <h2 className="font-semibold text-gray-900 dark:text-white">Next Steps</h2>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Link
              href="/docs/market-yaml"
              className="flex items-center justify-between rounded-lg border border-gray-200 p-4 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700"
            >
              <span className="text-gray-700 dark:text-gray-300">Configure pricing strategies</span>
              <ArrowRight className="h-4 w-4 text-gray-400" />
            </Link>
            <Link
              href="/docs/natlangchain"
              className="flex items-center justify-between rounded-lg border border-gray-200 p-4 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700"
            >
              <span className="text-gray-700 dark:text-gray-300">Learn about NatLangChain</span>
              <ArrowRight className="h-4 w-4 text-gray-400" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
