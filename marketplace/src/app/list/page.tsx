'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  GitBranch,
  CheckCircle,
  Loader2,
  AlertCircle,
  ExternalLink,
  Copy,
  Check,
  Rocket,
  Shield,
  Coins,
  ArrowRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';

type Step = 'input' | 'analyzing' | 'config' | 'complete';

interface RepoInfo {
  name: string;
  owner: string;
  description: string;
  languages: string[];
  stars: number;
  forks: number;
  license: string | null;
}

export default function ListRepoPage() {
  const [repoUrl, setRepoUrl] = useState('');
  const [step, setStep] = useState<Step>('input');
  const [error, setError] = useState<string | null>(null);
  const [repoInfo, setRepoInfo] = useState<RepoInfo | null>(null);
  const [copied, setCopied] = useState(false);

  // Config form state
  const [config, setConfig] = useState({
    walletAddress: '',
    licenseModel: 'per-seat',
    basePrice: '0.05',
    royaltyRate: '5',
  });

  const handleAnalyze = async () => {
    setError(null);

    // Validate URL
    const githubRegex = /^https?:\/\/github\.com\/([^\/]+)\/([^\/]+)\/?$/;
    const match = repoUrl.match(githubRegex);

    if (!match) {
      setError('Please enter a valid GitHub repository URL (e.g., https://github.com/owner/repo)');
      return;
    }

    const [, owner, repo] = match;
    setStep('analyzing');

    try {
      // Fetch repo info from GitHub API
      const response = await fetch(`https://api.github.com/repos/${owner}/${repo}`);

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Repository not found. Make sure it exists and is public.');
        }
        throw new Error('Failed to fetch repository information');
      }

      const data = await response.json();

      // Fetch languages
      const langResponse = await fetch(`https://api.github.com/repos/${owner}/${repo}/languages`);
      const languages = langResponse.ok ? Object.keys(await langResponse.json()) : [];

      setRepoInfo({
        name: data.name,
        owner: data.owner.login,
        description: data.description || 'No description provided',
        languages,
        stars: data.stargazers_count,
        forks: data.forks_count,
        license: data.license?.spdx_id || null,
      });

      setStep('config');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze repository');
      setStep('input');
    }
  };

  const handleSubmit = async () => {
    if (!config.walletAddress || !config.walletAddress.startsWith('0x')) {
      setError('Please enter a valid Ethereum wallet address');
      return;
    }

    setStep('complete');
  };

  const handleCopyConfig = () => {
    const yamlConfig = `# .market.yaml - RRA Marketplace Configuration
version: "1.0"

metadata:
  name: "${repoInfo?.name}"
  description: "${repoInfo?.description}"
  author: "${repoInfo?.owner}"

story_protocol:
  chain_id: 1514
  # ip_asset_id and royalty_vault will be set after registration

tiers:
  personal:
    name: "Personal"
    price: "${config.basePrice}"
    currency: "WIP"
    terms:
      - "Non-commercial use only"
      - "Single developer"
    royalty_rate: 0

  commercial:
    name: "Commercial"
    price: "${(parseFloat(config.basePrice) * 2).toFixed(2)}"
    currency: "WIP"
    terms:
      - "Commercial use allowed"
      - "Team up to 10 developers"
    royalty_rate: ${config.royaltyRate}

  enterprise:
    name: "Enterprise"
    price: "${(parseFloat(config.basePrice) * 10).toFixed(2)}"
    currency: "WIP"
    terms:
      - "Unlimited commercial use"
      - "Unlimited developers"
      - "White-label rights"
    royalty_rate: ${Math.max(1, parseInt(config.royaltyRate) - 3)}

agent:
  negotiation_enabled: true
  max_discount: 10
  response_style: "professional"

developer_wallet: "${config.walletAddress}"
`;

    navigator.clipboard.writeText(yamlConfig);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-800">
      <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-900">
            <GitBranch className="h-8 w-8 text-indigo-600 dark:text-indigo-400" />
          </div>
          <h1 className="mt-6 text-3xl font-bold text-gray-900 dark:text-white">
            List Your Repository
          </h1>
          <p className="mt-2 text-lg text-gray-600 dark:text-gray-300">
            Turn your code into a licensable asset with AI-powered negotiation
          </p>
        </div>

        {/* Progress Steps */}
        <div className="mt-12 flex justify-center">
          <div className="flex items-center gap-4">
            {['Enter URL', 'Configure', 'Complete'].map((label, index) => {
              const stepIndex = ['input', 'analyzing', 'config', 'complete'].indexOf(step);
              const isActive = index <= (stepIndex === 1 ? 0 : stepIndex === 3 ? 2 : stepIndex);
              const isCurrent = (index === 0 && (step === 'input' || step === 'analyzing')) ||
                               (index === 1 && step === 'config') ||
                               (index === 2 && step === 'complete');

              return (
                <div key={label} className="flex items-center gap-4">
                  {index > 0 && (
                    <div className={cn(
                      'h-0.5 w-12',
                      isActive ? 'bg-indigo-600' : 'bg-gray-300 dark:bg-gray-600'
                    )} />
                  )}
                  <div className="flex flex-col items-center">
                    <div className={cn(
                      'flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium',
                      isCurrent
                        ? 'bg-indigo-600 text-white'
                        : isActive
                        ? 'bg-indigo-100 text-indigo-600 dark:bg-indigo-900 dark:text-indigo-400'
                        : 'bg-gray-200 text-gray-500 dark:bg-gray-700'
                    )}>
                      {isActive && index < stepIndex ? (
                        <CheckCircle className="h-5 w-5" />
                      ) : (
                        index + 1
                      )}
                    </div>
                    <span className={cn(
                      'mt-1 text-xs',
                      isCurrent ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-500'
                    )}>
                      {label}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="mt-12">
          {/* Step 1: Enter URL */}
          {(step === 'input' || step === 'analyzing') && (
            <div className="rounded-xl border border-gray-200 bg-white p-8 shadow-lg dark:border-gray-700 dark:bg-gray-800">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Enter your GitHub repository URL
              </h2>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                We&apos;ll analyze your repository and help you set up licensing.
              </p>

              <div className="mt-6">
                <input
                  type="url"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  placeholder="https://github.com/username/repository"
                  disabled={step === 'analyzing'}
                  className="w-full rounded-lg border border-gray-300 px-4 py-3 text-gray-900 placeholder-gray-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 disabled:bg-gray-100 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-500"
                />
              </div>

              {error && (
                <div className="mt-4 flex items-center gap-2 rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400">
                  <AlertCircle className="h-5 w-5 shrink-0" />
                  <span className="text-sm">{error}</span>
                </div>
              )}

              <button
                onClick={handleAnalyze}
                disabled={!repoUrl || step === 'analyzing'}
                className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-6 py-3 font-medium text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {step === 'analyzing' ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Analyzing Repository...
                  </>
                ) : (
                  <>
                    Analyze Repository
                    <ArrowRight className="h-5 w-5" />
                  </>
                )}
              </button>
            </div>
          )}

          {/* Step 2: Configure */}
          {step === 'config' && repoInfo && (
            <div className="space-y-6">
              {/* Repo Info Card */}
              <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-lg dark:border-gray-700 dark:bg-gray-800">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                      {repoInfo.name}
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      by {repoInfo.owner}
                    </p>
                  </div>
                  <a
                    href={repoUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-sm text-indigo-600 hover:underline dark:text-indigo-400"
                  >
                    View on GitHub
                    <ExternalLink className="h-4 w-4" />
                  </a>
                </div>
                <p className="mt-3 text-gray-600 dark:text-gray-300">{repoInfo.description}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {repoInfo.languages.map((lang) => (
                    <span
                      key={lang}
                      className="rounded-full bg-gray-100 px-3 py-1 text-sm text-gray-700 dark:bg-gray-700 dark:text-gray-300"
                    >
                      {lang}
                    </span>
                  ))}
                </div>
                <div className="mt-4 flex gap-6 text-sm text-gray-500 dark:text-gray-400">
                  <span>⭐ {repoInfo.stars} stars</span>
                  <span>🔀 {repoInfo.forks} forks</span>
                  {repoInfo.license && <span>📄 {repoInfo.license}</span>}
                </div>
              </div>

              {/* Config Form */}
              <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-lg dark:border-gray-700 dark:bg-gray-800">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Configure Licensing
                </h3>

                <div className="mt-6 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Wallet Address (for receiving payments)
                    </label>
                    <input
                      type="text"
                      value={config.walletAddress}
                      onChange={(e) => setConfig({ ...config, walletAddress: e.target.value })}
                      placeholder="0x..."
                      className="mt-1 w-full rounded-lg border border-gray-300 px-4 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Base Price (WIP)
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        value={config.basePrice}
                        onChange={(e) => setConfig({ ...config, basePrice: e.target.value })}
                        className="mt-1 w-full rounded-lg border border-gray-300 px-4 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Royalty Rate (%)
                      </label>
                      <input
                        type="number"
                        min="0"
                        max="100"
                        value={config.royaltyRate}
                        onChange={(e) => setConfig({ ...config, royaltyRate: e.target.value })}
                        className="mt-1 w-full rounded-lg border border-gray-300 px-4 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      License Model
                    </label>
                    <select
                      value={config.licenseModel}
                      onChange={(e) => setConfig({ ...config, licenseModel: e.target.value })}
                      className="mt-1 w-full rounded-lg border border-gray-300 px-4 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    >
                      <option value="per-seat">Per Seat (charge per developer)</option>
                      <option value="one-time">One-Time (single payment)</option>
                      <option value="subscription">Subscription (recurring)</option>
                    </select>
                  </div>
                </div>

                {error && (
                  <div className="mt-4 flex items-center gap-2 rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400">
                    <AlertCircle className="h-5 w-5 shrink-0" />
                    <span className="text-sm">{error}</span>
                  </div>
                )}

                <button
                  onClick={handleSubmit}
                  className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-6 py-3 font-medium text-white transition hover:bg-indigo-700"
                >
                  Generate Configuration
                  <ArrowRight className="h-5 w-5" />
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Complete */}
          {step === 'complete' && repoInfo && (
            <div className="space-y-6">
              <div className="rounded-xl border border-green-200 bg-green-50 p-6 dark:border-green-800 dark:bg-green-900/20">
                <div className="flex items-center gap-3">
                  <CheckCircle className="h-8 w-8 text-green-600 dark:text-green-400" />
                  <div>
                    <h3 className="text-lg font-semibold text-green-800 dark:text-green-200">
                      Configuration Generated!
                    </h3>
                    <p className="text-sm text-green-700 dark:text-green-300">
                      Follow these steps to complete your listing.
                    </p>
                  </div>
                </div>
              </div>

              {/* Instructions */}
              <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-lg dark:border-gray-700 dark:bg-gray-800">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Complete Your Listing
                </h3>

                <div className="mt-6 space-y-6">
                  {/* Step 1 */}
                  <div className="flex gap-4">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-600 dark:bg-indigo-900 dark:text-indigo-400">
                      1
                    </div>
                    <div className="flex-1">
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        Copy the configuration below
                      </h4>
                      <div className="mt-3 relative">
                        <pre className="overflow-x-auto rounded-lg bg-gray-900 p-4 text-sm text-gray-100">
                          <code>{`.market.yaml`}</code>
                        </pre>
                        <button
                          onClick={handleCopyConfig}
                          className="absolute right-2 top-2 flex items-center gap-1 rounded bg-gray-700 px-2 py-1 text-xs text-gray-300 hover:bg-gray-600"
                        >
                          {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                          {copied ? 'Copied!' : 'Copy Config'}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Step 2 */}
                  <div className="flex gap-4">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-600 dark:bg-indigo-900 dark:text-indigo-400">
                      2
                    </div>
                    <div>
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        Add to your repository
                      </h4>
                      <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                        Create a file named <code className="rounded bg-gray-100 px-1 dark:bg-gray-700">.market.yaml</code> in your repository root and paste the configuration.
                      </p>
                    </div>
                  </div>

                  {/* Step 3 */}
                  <div className="flex gap-4">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-600 dark:bg-indigo-900 dark:text-indigo-400">
                      3
                    </div>
                    <div>
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        Run ingestion
                      </h4>
                      <pre className="mt-2 overflow-x-auto rounded-lg bg-gray-900 p-4 text-sm text-gray-100">
                        <code>{`pip install rra-module\nrra ingest ${repoUrl}`}</code>
                      </pre>
                    </div>
                  </div>

                  {/* Step 4 */}
                  <div className="flex gap-4">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-600 dark:bg-indigo-900 dark:text-indigo-400">
                      4
                    </div>
                    <div>
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        Push and you&apos;re live!
                      </h4>
                      <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                        Commit and push your changes. Your AI agent will be ready to negotiate licenses!
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Benefits */}
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
                  <Rocket className="h-8 w-8 text-indigo-600 dark:text-indigo-400" />
                  <h4 className="mt-2 font-medium text-gray-900 dark:text-white">AI Negotiation</h4>
                  <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                    Your agent handles all licensing discussions
                  </p>
                </div>
                <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
                  <Shield className="h-8 w-8 text-green-600 dark:text-green-400" />
                  <h4 className="mt-2 font-medium text-gray-900 dark:text-white">On-Chain Rights</h4>
                  <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                    IP registered on Story Protocol
                  </p>
                </div>
                <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
                  <Coins className="h-8 w-8 text-amber-600 dark:text-amber-400" />
                  <h4 className="mt-2 font-medium text-gray-900 dark:text-white">Auto Royalties</h4>
                  <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                    Payments go directly to your wallet
                  </p>
                </div>
              </div>

              <div className="flex justify-center gap-4">
                <Link
                  href="/docs/quickstart"
                  className="rounded-lg border border-gray-300 px-6 py-3 font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
                >
                  Read Full Guide
                </Link>
                <Link
                  href="/search"
                  className="rounded-lg bg-indigo-600 px-6 py-3 font-medium text-white hover:bg-indigo-700"
                >
                  Browse Marketplace
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
