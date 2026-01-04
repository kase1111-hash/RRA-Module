'use client';

import { Suspense, useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { SearchBar } from '@/components/SearchBar';
import { AgentCard } from '@/components/AgentCard';
import { SkeletonCard } from '@/components/ui/Skeleton';
import { Badge } from '@/components/ui/Badge';
import { Loader2, X, Sparkles, TrendingUp, Clock, Search as SearchIcon } from 'lucide-react';

// Mock data - in production would come from API based on search params
const allRepos = [
  {
    id: 'rra-module-abc123',
    url: 'https://github.com/kase1111-hash/RRA-Module',
    name: 'RRA-Module',
    owner: 'kase1111-hash',
    description: 'Revenant Repo Agent Module - Transform dormant GitHub repositories into autonomous, revenue-generating agents.',
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

// Sort label mapping
const SORT_LABELS: Record<string, { label: string; icon: typeof Clock }> = {
  recent: { label: 'Most Recent', icon: Clock },
  popular: { label: 'Most Popular', icon: TrendingUp },
  price_low: { label: 'Price: Low to High', icon: TrendingUp },
  price_high: { label: 'Price: High to Low', icon: TrendingUp },
};

function SearchResults() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);

  const query = searchParams.get('q') || '';
  const language = searchParams.get('language') || '';
  const priceMin = searchParams.get('price_min') || '';
  const priceMax = searchParams.get('price_max') || '';
  const sortBy = searchParams.get('sort') || 'recent';

  // Simulate loading for demo
  useEffect(() => {
    setIsLoading(true);
    const timer = setTimeout(() => setIsLoading(false), 800);
    return () => clearTimeout(timer);
  }, [query, language, sortBy, priceMin, priceMax]);

  // Collect active filters
  const activeFilters: { key: string; label: string; value: string }[] = [];
  if (language) activeFilters.push({ key: 'language', label: 'Language', value: language });
  if (priceMin) activeFilters.push({ key: 'price_min', label: 'Min Price', value: `${priceMin} ETH` });
  if (priceMax) activeFilters.push({ key: 'price_max', label: 'Max Price', value: `${priceMax} ETH` });
  if (sortBy !== 'recent') activeFilters.push({ key: 'sort', label: 'Sort', value: SORT_LABELS[sortBy]?.label || sortBy });

  const removeFilter = (key: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete(key);
    router.push(`/search?${params.toString()}`);
  };

  const clearAllFilters = () => {
    const params = new URLSearchParams();
    if (query) params.set('q', query);
    router.push(`/search?${params.toString()}`);
  };

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

  if (priceMin) {
    const min = parseFloat(priceMin);
    filteredRepos = filteredRepos.filter((repo) => {
      const price = parseFloat(marketConfigs[repo.id]?.target_price || '0');
      return price >= min;
    });
  }

  if (priceMax) {
    const max = parseFloat(priceMax);
    filteredRepos = filteredRepos.filter((repo) => {
      const price = parseFloat(marketConfigs[repo.id]?.target_price || '0');
      return price <= max;
    });
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
      {/* Active Filters */}
      {activeFilters.length > 0 && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <span className="text-sm text-gray-500 dark:text-gray-400">Active filters:</span>
          {activeFilters.map((filter) => (
            <Badge
              key={filter.key}
              variant="primary"
              size="md"
              removable
              onRemove={() => removeFilter(filter.key)}
            >
              {filter.label}: {filter.value}
            </Badge>
          ))}
          <button
            onClick={clearAllFilters}
            className="ml-2 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 flex items-center gap-1"
          >
            <X className="h-3 w-3" />
            Clear all
          </button>
        </div>
      )}

      {/* Results Header */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {isLoading ? (
            <span className="animate-pulse">Searching...</span>
          ) : (
            <>
              {filteredRepos.length} {filteredRepos.length === 1 ? 'result' : 'results'}
              {query && <> for <span className="font-medium text-gray-900 dark:text-white">&quot;{query}&quot;</span></>}
            </>
          )}
        </p>
        {!isLoading && filteredRepos.length > 0 && (
          <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <span>Sorted by:</span>
            <span className="font-medium text-gray-700 dark:text-gray-300">
              {SORT_LABELS[sortBy]?.label || 'Most Recent'}
            </span>
          </div>
        )}
      </div>

      {/* Loading Skeleton */}
      {isLoading ? (
        <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : filteredRepos.length > 0 ? (
        /* Results Grid */
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
        /* Empty State */
        <div className="mt-12 text-center">
          <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800">
            <SearchIcon className="h-10 w-10 text-gray-400 dark:text-gray-500" />
          </div>
          <h3 className="mt-6 text-lg font-semibold text-gray-900 dark:text-white">
            No repositories found
          </h3>
          <p className="mt-2 text-gray-600 dark:text-gray-400 max-w-md mx-auto">
            We couldn&apos;t find any repositories matching your search.
            Try adjusting your filters or search terms.
          </p>
          {activeFilters.length > 0 && (
            <button
              onClick={clearAllFilters}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
            >
              <X className="h-4 w-4" />
              Clear all filters
            </button>
          )}

          {/* Suggestions */}
          <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Popular searches
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {['Python', 'TypeScript', 'Rust', 'Machine Learning', 'Web3'].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => router.push(`/search?q=${encodeURIComponent(suggestion)}`)}
                  className="inline-flex items-center gap-1 rounded-full border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-colors dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                >
                  <Sparkles className="h-3 w-3 text-amber-500" />
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
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
