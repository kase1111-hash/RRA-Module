'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { SearchBar } from '@/components/SearchBar';
import { AgentCard } from '@/components/AgentCard';
import { Loader2 } from 'lucide-react';

// Mock data - in production would come from API based on search params
const allRepos = [
  {
    id: 'rra-module-abc123',
    url: 'https://github.com/kase1111-hash/RRA-Module',
    name: 'RRA-Module',
    owner: 'kase1111-hash',
    description: 'Revenant Repo Agent Module - Transform dormant GitHub repositories into autonomous, revenue-generating agents.',
    kb_path: 'agent_knowledge_bases/rra_module_kb.json',
    updated_at: '2025-12-19T12:00:00Z',
    languages: ['Python', 'Solidity', 'TypeScript'],
    files: 31,
    stars: 128,
    forks: 24,
  },
  {
    id: 'web3-utils-def456',
    url: 'https://github.com/example/web3-utils',
    name: 'web3-utils',
    owner: 'example',
    description: 'A comprehensive library of utility functions for Web3 development.',
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
    description: 'End-to-end machine learning pipeline framework with built-in feature engineering.',
    kb_path: 'agent_knowledge_bases/ml_pipeline_kb.json',
    updated_at: '2025-12-17T15:45:00Z',
    languages: ['Python', 'YAML'],
    files: 67,
    stars: 567,
    forks: 134,
  },
  {
    id: 'rust-crypto-jkl012',
    url: 'https://github.com/example/rust-crypto',
    name: 'rust-crypto',
    owner: 'example',
    description: 'High-performance cryptographic primitives implemented in Rust.',
    kb_path: 'agent_knowledge_bases/rust_crypto_kb.json',
    updated_at: '2025-12-16T11:20:00Z',
    languages: ['Rust'],
    files: 89,
    stars: 1024,
    forks: 256,
  },
  {
    id: 'react-components-mno345',
    url: 'https://github.com/example/react-components',
    name: 'react-components',
    owner: 'example',
    description: 'Production-ready React components with TypeScript support.',
    kb_path: 'agent_knowledge_bases/react_components_kb.json',
    updated_at: '2025-12-15T08:15:00Z',
    languages: ['TypeScript', 'CSS'],
    files: 156,
    stars: 892,
    forks: 178,
  },
  {
    id: 'go-microservices-pqr678',
    url: 'https://github.com/example/go-microservices',
    name: 'go-microservices',
    owner: 'example',
    description: 'Microservices framework for Go with service discovery and load balancing.',
    kb_path: 'agent_knowledge_bases/go_microservices_kb.json',
    updated_at: '2025-12-14T14:30:00Z',
    languages: ['Go', 'Protocol Buffers'],
    files: 78,
    stars: 456,
    forks: 92,
  },
];

const marketConfigs: Record<string, any> = {
  'rra-module-abc123': {
    license_identifier: 'FSL-1.1-ALv2',
    license_model: 'Per-seat',
    target_price: '0.05',
    floor_price: '0.02',
  },
  'web3-utils-def456': {
    license_identifier: 'MIT',
    license_model: 'One-time',
    target_price: '0.02',
    floor_price: '0.01',
  },
  'ml-pipeline-ghi789': {
    license_identifier: 'Apache-2.0',
    license_model: 'Subscription',
    target_price: '0.08',
    floor_price: '0.05',
  },
  'rust-crypto-jkl012': {
    license_identifier: 'MIT',
    license_model: 'One-time',
    target_price: '0.03',
    floor_price: '0.02',
  },
  'react-components-mno345': {
    license_identifier: 'MIT',
    license_model: 'Per-seat',
    target_price: '0.04',
    floor_price: '0.02',
  },
  'go-microservices-pqr678': {
    license_identifier: 'Apache-2.0',
    license_model: 'Enterprise',
    target_price: '0.1',
    floor_price: '0.06',
  },
};

// Mock verification data for repositories
const verificationData: Record<string, any> = {
  'rra-module-abc123': {
    repo_url: 'https://github.com/kase1111-hash/RRA-Module',
    overall_status: 'passed',
    score: 87.5,
    verified_at: '2025-12-19T12:00:00Z',
    checks: [
      { name: 'tests', status: 'passed', message: 'All 42 tests passed' },
      { name: 'security', status: 'warning', message: '2 low-severity issues' },
    ],
  },
  'web3-utils-def456': {
    repo_url: 'https://github.com/example/web3-utils',
    overall_status: 'passed',
    score: 92.0,
    verified_at: '2025-12-18T09:30:00Z',
    checks: [
      { name: 'tests', status: 'passed', message: 'All 78 tests passed' },
      { name: 'security', status: 'passed', message: 'No issues found' },
    ],
  },
  'ml-pipeline-ghi789': {
    repo_url: 'https://github.com/example/ml-pipeline',
    overall_status: 'warning',
    score: 75.0,
    verified_at: '2025-12-17T15:45:00Z',
    checks: [
      { name: 'tests', status: 'warning', message: '3 tests skipped' },
      { name: 'security', status: 'passed', message: 'No issues found' },
    ],
  },
  'rust-crypto-jkl012': {
    repo_url: 'https://github.com/example/rust-crypto',
    overall_status: 'passed',
    score: 98.5,
    verified_at: '2025-12-16T11:20:00Z',
    checks: [
      { name: 'tests', status: 'passed', message: 'All 156 tests passed' },
      { name: 'security', status: 'passed', message: 'No issues found' },
    ],
  },
  'react-components-mno345': {
    repo_url: 'https://github.com/example/react-components',
    overall_status: 'passed',
    score: 89.0,
    verified_at: '2025-12-15T08:15:00Z',
    checks: [
      { name: 'tests', status: 'passed', message: 'All 234 tests passed' },
      { name: 'security', status: 'warning', message: '1 low-severity issue' },
    ],
  },
  'go-microservices-pqr678': {
    repo_url: 'https://github.com/example/go-microservices',
    overall_status: 'failed',
    score: 45.0,
    verified_at: '2025-12-14T14:30:00Z',
    checks: [
      { name: 'tests', status: 'failed', message: '12 tests failing' },
      { name: 'security', status: 'warning', message: '5 medium-severity issues' },
    ],
  },
};

function SearchResults() {
  const searchParams = useSearchParams();
  const query = searchParams.get('q') || '';
  const language = searchParams.get('language') || '';
  const sortBy = searchParams.get('sort') || 'recent';

  // Filter repos based on search params
  let filteredRepos = [...allRepos];

  if (query) {
    const lowerQuery = query.toLowerCase();
    filteredRepos = filteredRepos.filter(
      (repo) =>
        repo.name.toLowerCase().includes(lowerQuery) ||
        repo.description.toLowerCase().includes(lowerQuery) ||
        repo.owner.toLowerCase().includes(lowerQuery) ||
        repo.languages.some((lang) => lang.toLowerCase().includes(lowerQuery))
    );
  }

  if (language) {
    filteredRepos = filteredRepos.filter((repo) =>
      repo.languages.some((lang) => lang.toLowerCase() === language.toLowerCase())
    );
  }

  // Sort repos
  if (sortBy === 'popular') {
    filteredRepos.sort((a, b) => (b.stars || 0) - (a.stars || 0));
  } else if (sortBy === 'price_low') {
    filteredRepos.sort((a, b) => {
      const priceA = parseFloat(marketConfigs[a.id]?.target_price || '0');
      const priceB = parseFloat(marketConfigs[b.id]?.target_price || '0');
      return priceA - priceB;
    });
  } else if (sortBy === 'price_high') {
    filteredRepos.sort((a, b) => {
      const priceA = parseFloat(marketConfigs[a.id]?.target_price || '0');
      const priceB = parseFloat(marketConfigs[b.id]?.target_price || '0');
      return priceB - priceA;
    });
  }

  return (
    <>
      {/* Results Header */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {filteredRepos.length} {filteredRepos.length === 1 ? 'result' : 'results'}
          {query && ` for "${query}"`}
        </p>
      </div>

      {/* Results Grid */}
      {filteredRepos.length > 0 ? (
        <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {filteredRepos.map((repo) => (
            <AgentCard
              key={repo.id}
              repository={repo}
              marketConfig={marketConfigs[repo.id]}
              verification={verificationData[repo.id]}
            />
          ))}
        </div>
      ) : (
        <div className="mt-12 text-center">
          <div className="mx-auto h-24 w-24 text-gray-300 dark:text-gray-600">
            <svg
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
          <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
            No repositories found
          </h3>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Try adjusting your search or filters to find what you're looking for.
          </p>
        </div>
      )}
    </>
  );
}

export default function SearchPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Search Header */}
      <div className="border-b border-gray-200 bg-white px-4 py-8 dark:border-gray-800 dark:bg-gray-800">
        <div className="mx-auto max-w-7xl">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Explore Repositories
          </h1>
          <p className="mt-1 text-gray-600 dark:text-gray-400">
            Find and license code from AI-powered agents
          </p>

          <div className="mt-6">
            <Suspense fallback={<div className="h-12 animate-pulse rounded-xl bg-gray-200 dark:bg-gray-700" />}>
              <SearchBarWithParams />
            </Suspense>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Suspense
          fallback={
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
            </div>
          }
        >
          <SearchResults />
        </Suspense>
      </div>
    </div>
  );
}

function SearchBarWithParams() {
  const searchParams = useSearchParams();
  const query = searchParams.get('q') || '';
  return <SearchBar initialQuery={query} />;
}
