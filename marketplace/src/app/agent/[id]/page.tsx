'use client';

import { useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  ExternalLink,
  GitFork,
  Star,
  Code,
  FileText,
  Shield,
  Clock,
  Users,
  CheckCircle,
  Link2,
  Wallet,
} from 'lucide-react';
import { NegotiationChat } from '@/components/NegotiationChat';
import { VerificationSection, VerificationSummary } from '@/components/VerificationSection';
import { PurchaseLinksList, BlockchainInfo, ShareLinks } from '@/components/PurchaseLinks';
import { cn, formatPrice, getLanguageColor } from '@/lib/utils';
import type { NegotiationMessage, NegotiationPhase, VerificationResult, PurchaseLink } from '@/types';

// Mock data - in production would come from API
const mockAgentData = {
  repository: {
    id: 'rra-module-abc123',
    url: 'https://github.com/kase1111-hash/RRA-Module',
    name: 'RRA-Module',
    owner: 'kase1111-hash',
    description:
      'Revenant Repo Agent Module - Transform dormant GitHub repositories into autonomous, revenue-generating agents through AI-driven negotiation and blockchain-enforced licensing.',
    kb_path: 'agent_knowledge_bases/rra_module_kb.json',
    updated_at: '2025-01-04T12:00:00Z',
    languages: ['Python', 'TypeScript', 'JavaScript'],
    files: 45,
    stars: 3,
    forks: 1,
  },
  market_config: {
    license_identifier: 'FSL-1.1-ALv2',
    license_model: 'Per-seat',
    target_price: '0.05',
    floor_price: '0.02',
    negotiation_style: 'persuasive',
    features: [
      'Full source code access',
      '12 months of updates',
      'Developer support',
      'Commercial usage rights',
    ],
    copyright_holder: 'Kase Branham',
    developer_wallet: '0x1234567890abcdef1234567890abcdef12345678',
  },
  statistics: {
    code_files: 45,
    languages: ['Python', 'TypeScript', 'JavaScript'],
    total_lines: 8500,
    test_coverage: 78,
  },
  reputation: {
    score: 0,
    total_sales: 0,
    total_revenue: '0 ETH',
  },
  license_tiers: [
    {
      id: 'standard',
      name: 'Standard',
      price: '0.05 ETH',
      features: ['1 seat', '12 months updates', 'Email support'],
    },
    {
      id: 'premium',
      name: 'Premium',
      price: '0.15 ETH',
      features: ['5 seats', 'Lifetime updates', 'Priority support', 'Private channel'],
    },
    {
      id: 'enterprise',
      name: 'Enterprise',
      price: '0.5 ETH',
      features: ['Unlimited seats', 'Custom terms', 'Dedicated support', 'SLA'],
    },
  ],
  verification: {
    repo_url: 'https://github.com/kase1111-hash/RRA-Module',
    overall_status: 'passed' as const,
    score: 87.5,
    verified_at: '2025-12-19T12:00:00Z',
    checks: [
      { name: 'tests', status: 'passed' as const, message: 'All 42 tests passed', details: { passed: 42, failed: 0, skipped: 0 } },
      { name: 'linting', status: 'passed' as const, message: 'No linting errors found', details: { errors: 0, warnings: 3 } },
      { name: 'security', status: 'warning' as const, message: '2 low-severity issues', details: { critical: 0, high: 0, medium: 0, low: 2 } },
      { name: 'build', status: 'passed' as const, message: 'Build successful', details: { duration_ms: 4250 } },
      { name: 'documentation', status: 'passed' as const, message: 'README and API docs present', details: { has_readme: true, has_api_docs: true } },
      { name: 'license', status: 'passed' as const, message: 'Valid FSL-1.1-ALv2 license', details: { license_type: 'FSL-1.1-ALv2' } },
    ],
  },
  purchase_links: [
    {
      url: '/agent/rra-module-abc123/license/standard',
      network: 'testnet' as const,
      tier: 'standard' as const,
      price_display: '0.05 ETH',
      ip_asset_id: '0xf08574c30337dde7C38869b8d399BA07ab23a07F',
    },
    {
      url: '/agent/rra-module-abc123/license/premium',
      network: 'testnet' as const,
      tier: 'premium' as const,
      price_display: '0.15 ETH',
      ip_asset_id: '0xf08574c30337dde7C38869b8d399BA07ab23a07F',
    },
    {
      url: '/agent/rra-module-abc123/license/enterprise',
      network: 'testnet' as const,
      tier: 'enterprise' as const,
      price_display: '0.5 ETH',
      ip_asset_id: '0xf08574c30337dde7C38869b8d399BA07ab23a07F',
    },
  ],
  blockchain_info: {
    ip_asset_id: '0xf08574c30337dde7C38869b8d399BA07ab23a07F',
    network: 'testnet' as const,
    explorer_url: 'https://aeneid.explorer.story.foundation/ipa/0xf08574c30337dde7C38869b8d399BA07ab23a07F',
  },
};

export default function AgentPage() {
  const params = useParams();
  const agentId = params.id as string;

  const [messages, setMessages] = useState<NegotiationMessage[]>([
    {
      id: '1',
      role: 'agent',
      content: `Hello! I'm the licensing agent for ${mockAgentData.repository.name}. This is a high-quality ${mockAgentData.statistics.languages[0]} repository with ${mockAgentData.statistics.code_files} files and ${mockAgentData.statistics.test_coverage}% test coverage.\n\nOur standard license is ${mockAgentData.market_config.target_price} ETH for a single seat with 12 months of updates.\n\nHow can I help you today? Are you interested in licensing this code for your project?`,
      timestamp: new Date().toISOString(),
    },
  ]);
  const [phase, setPhase] = useState<NegotiationPhase>('greeting');
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = useCallback(async (content: string) => {
    // Add user message
    const userMessage: NegotiationMessage = {
      id: String(Date.now()),
      role: 'buyer',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1500));

    // Generate mock response based on message content
    let agentResponse = '';
    let newPhase = phase;

    const lowerContent = content.toLowerCase();

    if (lowerContent.includes('price') || lowerContent.includes('cost') || lowerContent.includes('how much')) {
      agentResponse = `Great question! Our pricing is:\n\n• **Standard**: 0.05 ETH (1 seat, 12mo updates)\n• **Premium**: 0.15 ETH (5 seats, lifetime updates)\n• **Enterprise**: 0.5 ETH (unlimited, custom terms)\n\nAll licenses include full source code access and commercial usage rights. Would you like to discuss a specific tier?`;
      newPhase = 'proposal';
    } else if (lowerContent.includes('discount') || lowerContent.includes('lower') || lowerContent.includes('negotiate')) {
      agentResponse = `I appreciate you're looking for the best value. While our floor price is 0.02 ETH, I can offer you a 10% discount on the standard license - that's 0.045 ETH.\n\nThis is a limited offer considering our ${mockAgentData.statistics.test_coverage}% test coverage and the time this codebase would save you. What do you think?`;
      newPhase = 'negotiation';
    } else if (lowerContent.includes('deal') || lowerContent.includes('accept') || lowerContent.includes('ok') || lowerContent.includes('yes')) {
      agentResponse = `Excellent! I'm glad we could reach an agreement. Here's the final offer:\n\n**Standard License**\n• Price: 0.045 ETH\n• 1 seat license\n• 12 months of updates\n• Full commercial rights\n\nClick "Accept Offer & Purchase License" below to complete the transaction. Your license NFT will be minted immediately upon payment confirmation.`;
      newPhase = 'closing';
    } else if (lowerContent.includes('features') || lowerContent.includes('include') || lowerContent.includes('what do i get')) {
      agentResponse = `Here's what's included with every license:\n\n✅ Full source code access (${mockAgentData.statistics.code_files} files)\n✅ ${mockAgentData.statistics.test_coverage}% test coverage\n✅ Complete documentation\n✅ Commercial usage rights\n✅ Updates for your tier duration\n✅ Support via your tier level\n\nThe code is licensed under ${mockAgentData.market_config.license_identifier} and will convert to Apache-2.0 after 2 years. Any other questions?`;
      newPhase = 'discovery';
    } else {
      agentResponse = `Thanks for your interest! To better assist you, could you tell me more about your use case?\n\n• Are you building a commercial product?\n• How many developers will need access?\n• Do you need ongoing support?\n\nThis will help me recommend the best license tier for your needs.`;
      newPhase = 'discovery';
    }

    setPhase(newPhase);

    const responseMessage: NegotiationMessage = {
      id: String(Date.now() + 1),
      role: 'agent',
      content: agentResponse,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, responseMessage]);
    setIsLoading(false);
  }, [phase]);

  const handleAcceptOffer = useCallback(async () => {
    setIsLoading(true);
    await new Promise((resolve) => setTimeout(resolve, 1000));

    const confirmMessage: NegotiationMessage = {
      id: String(Date.now()),
      role: 'agent',
      content: `🎉 **Transaction Initiated!**\n\nPlease confirm the transaction in your wallet:\n• Amount: 0.045 ETH\n• Network: Ethereum Mainnet\n• Contract: RRALicense\n\nOnce confirmed, your license NFT will be minted and you'll receive instant access to the repository.\n\nThank you for choosing ${mockAgentData.repository.name}!`,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, confirmMessage]);
    setPhase('completed');
    setIsLoading(false);
  }, []);

  const { repository, market_config, statistics, reputation, license_tiers, verification, purchase_links, blockchain_info } = mockAgentData;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-800">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center space-x-4">
            <Link
              href="/search"
              className="flex h-10 w-10 items-center justify-center rounded-lg border border-gray-300 bg-white hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:hover:bg-gray-600"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>

            <div className="flex-1">
              <div className="flex items-center space-x-3">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  {repository.name}
                </h1>
                <a
                  href={repository.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                >
                  <ExternalLink className="h-5 w-5" />
                </a>
              </div>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                by {repository.owner}
              </p>
            </div>

            {/* Stats */}
            <div className="hidden md:flex items-center space-x-6 text-sm text-gray-600 dark:text-gray-300">
              <div className="flex items-center space-x-1">
                <Star className="h-4 w-4" />
                <span>{repository.stars}</span>
              </div>
              <div className="flex items-center space-x-1">
                <GitFork className="h-4 w-4" />
                <span>{repository.forks}</span>
              </div>
              <div className="flex items-center space-x-1">
                <Code className="h-4 w-4" />
                <span>{statistics.code_files} files</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          {/* Left Column - Info */}
          <div className="space-y-6 lg:col-span-1">
            {/* Description */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
              <h2 className="font-semibold text-gray-900 dark:text-white">About</h2>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                {repository.description}
              </p>

              {/* Languages */}
              <div className="mt-4 flex flex-wrap gap-2">
                {repository.languages.map((lang) => (
                  <span
                    key={lang}
                    className="inline-flex items-center space-x-1 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs dark:bg-gray-700"
                  >
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: getLanguageColor(lang) }}
                    />
                    <span className="text-gray-700 dark:text-gray-300">{lang}</span>
                  </span>
                ))}
              </div>
            </div>

            {/* License Info */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
              <h2 className="font-semibold text-gray-900 dark:text-white">License</h2>
              <div className="mt-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                    <FileText className="mr-2 h-4 w-4" />
                    Type
                  </span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {market_config.license_identifier}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                    <Shield className="mr-2 h-4 w-4" />
                    Model
                  </span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {market_config.license_model}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                    <Clock className="mr-2 h-4 w-4" />
                    Base Price
                  </span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {formatPrice(market_config.target_price)}
                  </span>
                </div>
              </div>
            </div>

            {/* Stats */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
              <h2 className="font-semibold text-gray-900 dark:text-white">Statistics</h2>
              <div className="mt-4 grid grid-cols-2 gap-4">
                <div className="text-center">
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {reputation.total_sales}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Licenses sold</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {reputation.score}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Rating</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {statistics.test_coverage}%
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Test coverage</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {statistics.total_lines.toLocaleString()}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Lines of code</p>
                </div>
              </div>
            </div>

            {/* Verification Status */}
            <VerificationSection verification={verification} />

            {/* Blockchain Info */}
            <BlockchainInfo
              ipAssetId={blockchain_info.ip_asset_id}
              network={blockchain_info.network}
              explorerUrl={blockchain_info.explorer_url}
            />

            {/* License Tiers with Purchase Buttons */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
              <h2 className="font-semibold text-gray-900 dark:text-white">License Tiers</h2>
              <div className="mt-4 space-y-4">
                {license_tiers.map((tier) => {
                  const purchaseLink = purchase_links.find((link) => link.tier === tier.id);
                  return (
                    <div
                      key={tier.id}
                      className="rounded-lg border border-gray-200 p-4 dark:border-gray-700"
                    >
                      <div className="flex items-center justify-between">
                        <h3 className="font-medium text-gray-900 dark:text-white">
                          {tier.name}
                        </h3>
                        <span className="text-lg font-bold text-primary-600 dark:text-primary-400">
                          {tier.price}
                        </span>
                      </div>
                      <ul className="mt-2 space-y-1">
                        {tier.features.map((feature) => (
                          <li
                            key={feature}
                            className="flex items-center text-xs text-gray-600 dark:text-gray-400"
                          >
                            <CheckCircle className="mr-1.5 h-3 w-3 text-green-500" />
                            {feature}
                          </li>
                        ))}
                      </ul>
                      {purchaseLink && (
                        <a
                          href={purchaseLink.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-3 flex w-full items-center justify-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-700"
                        >
                          <Wallet className="mr-2 h-4 w-4" />
                          Purchase License
                        </a>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Share Links */}
            <ShareLinks
              repoName={repository.name}
              purchaseUrl={purchase_links[0]?.url || ''}
              ipAssetId={blockchain_info.ip_asset_id}
            />
          </div>

          {/* Right Column - Chat */}
          <div className="lg:col-span-2">
            <div className="sticky top-24 h-[calc(100vh-12rem)]">
              <NegotiationChat
                messages={messages}
                phase={phase}
                isLoading={isLoading}
                onSendMessage={handleSendMessage}
                onAcceptOffer={handleAcceptOffer}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
