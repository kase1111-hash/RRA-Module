import Link from 'next/link';
import { ArrowRight, Code, Cpu, Shield, Zap, Link2, FileText, Database, Activity } from 'lucide-react';
import { SearchBar } from '@/components/SearchBar';
import { AgentCard } from '@/components/AgentCard';
import { ChainStatus } from '@/components/ChainStatus';

// Mock data - in production, this would come from API
const featuredRepos = [
  {
    id: 'rra-module-abc123',
    url: 'https://github.com/kase1111-hash/RRA-Module',
    name: 'RRA-Module',
    owner: 'kase1111-hash',
    description: 'Revenant Repo Agent Module - Transform dormant GitHub repositories into autonomous, revenue-generating agents through AI-driven negotiation.',
    kb_path: 'agent_knowledge_bases/rra_module_kb.json',
    updated_at: '2025-01-04T12:00:00Z',
    languages: ['Python', 'TypeScript', 'JavaScript'],
    files: 45,
    stars: 3,
    forks: 1,
  },
  {
    id: 'web3-utils-def456',
    url: 'https://github.com/example/web3-utils',
    name: 'web3-utils',
    owner: 'example',
    description: 'A comprehensive library of utility functions for Web3 development, including address validation, unit conversion, and transaction helpers.',
    kb_path: 'agent_knowledge_bases/web3_utils_kb.json',
    updated_at: '2025-12-18T09:30:00Z',
    languages: ['TypeScript', 'JavaScript'],
    files: 45,
    stars: 342,
    forks: 89,
  },
  {
    id: 'ml-pipeline-ghi789',
    url: 'https://github.com/example/ml-pipeline',
    name: 'ml-pipeline',
    owner: 'example',
    description: 'End-to-end machine learning pipeline framework with built-in feature engineering, model training, and deployment capabilities.',
    kb_path: 'agent_knowledge_bases/ml_pipeline_kb.json',
    updated_at: '2025-12-17T15:45:00Z',
    languages: ['Python', 'YAML'],
    files: 67,
    stars: 567,
    forks: 134,
  },
];

const marketConfigs = {
  'rra-module-abc123': {
    license_identifier: 'FSL-1.1-ALv2',
    license_model: 'Per-seat',
    target_price: '0.05',
    floor_price: '0.02',
    negotiation_style: 'persuasive',
    features: ['Full source access', '12 months updates', 'Developer support'],
  },
  'web3-utils-def456': {
    license_identifier: 'MIT',
    license_model: 'One-time',
    target_price: '0.02',
    floor_price: '0.01',
    negotiation_style: 'concise',
    features: ['Full source access', 'Unlimited usage', 'No attribution required'],
  },
  'ml-pipeline-ghi789': {
    license_identifier: 'Apache-2.0',
    license_model: 'Subscription',
    target_price: '0.08',
    floor_price: '0.05',
    negotiation_style: 'adaptive',
    features: ['Enterprise support', 'Priority updates', 'Custom training'],
  },
};

// Mock verification data for featured repos
const verificationData = {
  'rra-module-abc123': {
    repo_url: 'https://github.com/kase1111-hash/RRA-Module',
    overall_status: 'passed' as const,
    score: 87.5,
    verified_at: '2025-01-04T12:00:00Z',
    checks: [
      { name: 'tests', status: 'passed' as const, message: 'All 29 tests passed' },
      { name: 'security', status: 'passed' as const, message: 'No issues found' },
    ],
  },
  'web3-utils-def456': {
    repo_url: 'https://github.com/example/web3-utils',
    overall_status: 'passed' as const,
    score: 92.0,
    verified_at: '2025-12-18T09:30:00Z',
    checks: [
      { name: 'tests', status: 'passed' as const, message: 'All 78 tests passed' },
      { name: 'security', status: 'passed' as const, message: 'No issues found' },
    ],
  },
  'ml-pipeline-ghi789': {
    repo_url: 'https://github.com/example/ml-pipeline',
    overall_status: 'warning' as const,
    score: 75.0,
    verified_at: '2025-12-17T15:45:00Z',
    checks: [
      { name: 'tests', status: 'warning' as const, message: '3 tests skipped' },
      { name: 'security', status: 'passed' as const, message: 'No issues found' },
    ],
  },
};

export default function HomePage() {
  return (
    <div className="flex flex-col">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-primary-50 to-white px-4 py-20 dark:from-gray-900 dark:to-gray-800">
        <div className="mx-auto max-w-7xl">
          <div className="text-center">
            <h1 className="text-4xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-5xl md:text-6xl">
              License Code with{' '}
              <span className="text-primary-600">AI Agents</span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg text-gray-600 dark:text-gray-300">
              Discover repositories, negotiate terms with AI-powered agents, and purchase
              blockchain-enforced licenses. The future of code monetization is here.
            </p>

            {/* Search */}
            <div className="mx-auto mt-10 max-w-2xl">
              <SearchBar showFilters={false} />
            </div>

            {/* Quick Links */}
            <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
              <Link
                href="/search"
                className="inline-flex items-center rounded-lg bg-primary-600 px-6 py-3 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
              >
                Explore Marketplace
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
              <Link
                href="/docs/quickstart"
                className="inline-flex items-center rounded-lg border border-gray-300 bg-white px-6 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 transition-colors"
              >
                List Your Repo
              </Link>
            </div>
          </div>
        </div>

        {/* Background decoration */}
        <div className="absolute -top-24 -right-24 h-96 w-96 rounded-full bg-primary-100 opacity-50 blur-3xl dark:bg-primary-900" />
        <div className="absolute -bottom-24 -left-24 h-96 w-96 rounded-full bg-primary-100 opacity-50 blur-3xl dark:bg-primary-900" />
      </section>

      {/* Features Section */}
      <section className="border-y border-gray-200 bg-gray-50 px-4 py-16 dark:border-gray-800 dark:bg-gray-900">
        <div className="mx-auto max-w-7xl">
          <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-4">
            <div className="flex flex-col items-center text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-100 dark:bg-primary-900">
                <Cpu className="h-6 w-6 text-primary-600 dark:text-primary-400" />
              </div>
              <h3 className="mt-4 font-semibold text-gray-900 dark:text-white">
                AI Negotiation
              </h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                Negotiate licensing terms naturally with AI-powered agents
              </p>
            </div>

            <div className="flex flex-col items-center text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-green-100 dark:bg-green-900">
                <Shield className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
              <h3 className="mt-4 font-semibold text-gray-900 dark:text-white">
                Blockchain Enforcement
              </h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                License terms enforced by smart contracts on Ethereum
              </p>
            </div>

            <div className="flex flex-col items-center text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-100 dark:bg-amber-900">
                <Code className="h-6 w-6 text-amber-600 dark:text-amber-400" />
              </div>
              <h3 className="mt-4 font-semibold text-gray-900 dark:text-white">
                Instant Access
              </h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                Get immediate access to licensed code upon purchase
              </p>
            </div>

            <div className="flex flex-col items-center text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-purple-100 dark:bg-purple-900">
                <Zap className="h-6 w-6 text-purple-600 dark:text-purple-400" />
              </div>
              <h3 className="mt-4 font-semibold text-gray-900 dark:text-white">
                Zero Friction
              </h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                No paperwork, no emails, no waiting - just click and buy
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* NatLangChain Integration Section */}
      <section className="px-4 py-16 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-gray-900 dark:to-indigo-900/20">
        <div className="mx-auto max-w-7xl">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 rounded-full bg-indigo-100 px-4 py-1.5 text-sm font-medium text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300 mb-4">
              <Link2 className="h-4 w-4" />
              NatLangChain Integration
            </div>
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
              Powered by Natural Language Blockchain
            </h2>
            <p className="mt-4 max-w-2xl mx-auto text-gray-600 dark:text-gray-400">
              Every negotiation, transaction, and license agreement is recorded on NatLangChain -
              a blockchain that speaks your language.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-100 dark:bg-indigo-900/50 mb-4">
                <FileText className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
              </div>
              <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
                Intent Logging
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Every negotiation step is logged as a verifiable intent on chain
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900/50 mb-4">
                <Database className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
              <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
                Transaction Records
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                License purchases recorded immutably with full terms
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-100 dark:bg-amber-900/50 mb-4">
                <Activity className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              </div>
              <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
                LLM Validation
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                AI-powered proof of understanding validates entries
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/50 mb-4">
                <Link2 className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              </div>
              <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
                Chain Connection
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Real-time sync with NatLangChain for transparency
              </p>
            </div>
          </div>

          {/* Chain Status Widget */}
          <div className="mt-10 flex justify-center">
            <ChainStatus showDetails={true} />
          </div>
        </div>
      </section>

      {/* Featured Repos */}
      <section className="px-4 py-16">
        <div className="mx-auto max-w-7xl">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                Featured Repositories
              </h2>
              <p className="mt-1 text-gray-600 dark:text-gray-400">
                Discover high-quality code ready for licensing
              </p>
            </div>
            <Link
              href="/search"
              className="hidden sm:flex items-center text-sm font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
            >
              View all
              <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </div>

          <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {featuredRepos.map((repo, index) => (
              <AgentCard
                key={repo.id}
                repository={repo}
                marketConfig={marketConfigs[repo.id as keyof typeof marketConfigs]}
                verification={verificationData[repo.id as keyof typeof verificationData]}
                featured={index === 0}
              />
            ))}
          </div>

          <div className="mt-8 text-center sm:hidden">
            <Link
              href="/search"
              className="inline-flex items-center text-sm font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
            >
              View all repositories
              <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-primary-600 px-4 py-16 dark:bg-primary-900">
        <div className="mx-auto max-w-7xl text-center">
          <h2 className="text-3xl font-bold text-white">
            Ready to Monetize Your Code?
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-primary-100">
            Add a .market.yaml file to your repository and start earning. Your AI agent
            handles all the negotiations while you focus on building.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/docs/quickstart"
              className="inline-flex items-center rounded-lg bg-white px-6 py-3 text-sm font-medium text-primary-600 hover:bg-primary-50 transition-colors"
            >
              Get Started
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <Link
              href="/docs"
              className="inline-flex items-center rounded-lg border border-primary-400 px-6 py-3 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
            >
              Read the Docs
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
