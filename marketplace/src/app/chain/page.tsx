'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Database,
  FileText,
  Hash,
  Activity,
  RefreshCw,
  Loader2,
  CheckCircle,
  AlertCircle,
  Clock,
  User,
  Search,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ChainHealth, ChainStats, ChainEntry } from '@/types';

// Mock chain entries for display
const mockEntries: ChainEntry[] = [
  {
    id: 'entry-001',
    content: 'License inquiry started for RRA-Module repository',
    author: 'agent:rra-module',
    intent: 'inquiry_start',
    timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    type: 'inquiry',
    metadata: { repo: 'RRA-Module', phase: 'greeting' },
  },
  {
    id: 'entry-002',
    content: 'License tier requested: Per-seat license at 0.05 ETH',
    author: 'buyer:0x1234...5678',
    intent: 'tier_request',
    timestamp: new Date(Date.now() - 1000 * 60 * 10).toISOString(),
    type: 'inquiry',
    metadata: { repo: 'RRA-Module', price: '0.05' },
  },
  {
    id: 'entry-003',
    content: 'License purchase completed for web3-utils - MIT license',
    author: 'system',
    intent: 'transaction_complete',
    timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    type: 'transaction',
    metadata: { repo: 'web3-utils', license: 'MIT', price: '0.02' },
  },
  {
    id: 'entry-004',
    content: 'Repository verification passed with score 92.0',
    author: 'verifier:code-check',
    intent: 'verification_complete',
    timestamp: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
    type: 'verification',
    metadata: { repo: 'web3-utils', score: 92.0 },
  },
  {
    id: 'entry-005',
    content: 'New repository indexed: ml-pipeline',
    author: 'indexer:github',
    intent: 'repo_indexed',
    timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    type: 'system',
    metadata: { repo: 'ml-pipeline', files: 67 },
  },
];

const mockBlocks = [
  {
    hash: 'a1b2c3d4e5f6789012345678901234567890abcdef',
    index: 5,
    entries: 3,
    timestamp: new Date(Date.now() - 1000 * 60 * 2).toISOString(),
    previous_hash: '9876543210fedcba0987654321fedcba09876543',
  },
  {
    hash: '9876543210fedcba0987654321fedcba09876543',
    index: 4,
    entries: 2,
    timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
    previous_hash: 'fedcba9876543210fedcba9876543210fedcba98',
  },
  {
    hash: 'fedcba9876543210fedcba9876543210fedcba98',
    index: 3,
    entries: 4,
    timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    previous_hash: '1234567890abcdef1234567890abcdef12345678',
  },
];

export default function ChainExplorerPage() {
  const [health, setHealth] = useState<ChainHealth | null>(null);
  const [stats, setStats] = useState<ChainStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [expandedEntry, setExpandedEntry] = useState<string | null>(null);

  useEffect(() => {
    fetchChainData();
  }, []);

  const fetchChainData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthRes, statsRes] = await Promise.all([
        fetch('/api/chain/health'),
        fetch('/api/chain/stats'),
      ]);

      if (healthRes.ok) {
        setHealth(await healthRes.json());
      }
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch (err) {
      setError('Unable to connect to NatLangChain');
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
  };

  const getEntryIcon = (type?: string) => {
    switch (type) {
      case 'inquiry':
        return <Activity className="h-4 w-4 text-blue-500" />;
      case 'transaction':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'verification':
        return <FileText className="h-4 w-4 text-amber-500" />;
      default:
        return <Database className="h-4 w-4 text-gray-500" />;
    }
  };

  const filteredEntries = mockEntries.filter((entry) => {
    const matchesSearch =
      searchQuery === '' ||
      entry.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      entry.author.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = selectedType === 'all' || entry.type === selectedType;
    return matchesSearch && matchesType;
  });

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-4 py-6 dark:border-gray-800 dark:bg-gray-800">
        <div className="mx-auto max-w-7xl">
          <Link
            href="/"
            className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back to Marketplace
          </Link>
          <div className="mt-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-600 text-white">
                <Database className="h-5 w-5" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Chain Explorer
                </h1>
                <p className="text-gray-600 dark:text-gray-400">
                  Browse NatLangChain entries and transactions
                </p>
              </div>
            </div>
            <button
              onClick={fetchChainData}
              disabled={loading}
              className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
            >
              <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-4 py-8">
        {/* Status Cards */}
        <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900/30">
                {loading ? (
                  <Loader2 className="h-5 w-5 text-green-600 animate-spin" />
                ) : health ? (
                  <CheckCircle className="h-5 w-5 text-green-600" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-500" />
                )}
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Status</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  {loading ? 'Connecting...' : health ? 'Connected' : 'Offline'}
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-100 dark:bg-indigo-900/30">
                <Database className="h-5 w-5 text-indigo-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Blocks</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  {health?.blocks ?? stats?.total_blocks ?? 0}
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-100 dark:bg-amber-900/30">
                <FileText className="h-5 w-5 text-amber-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Entries</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  {stats?.total_entries ?? 0}
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/30">
                <Activity className="h-5 w-5 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">LLM Validation</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  {health?.llm_validation_available ? 'Active' : 'Inactive'}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          {/* Recent Entries */}
          <div className="lg:col-span-2">
            <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
              <div className="border-b border-gray-200 p-4 dark:border-gray-700">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Recent Entries
                  </h2>
                  <div className="flex gap-2">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                      <input
                        type="text"
                        placeholder="Search entries..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="rounded-lg border border-gray-300 bg-white py-2 pl-9 pr-4 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                      />
                    </div>
                    <select
                      value={selectedType}
                      onChange={(e) => setSelectedType(e.target.value)}
                      className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    >
                      <option value="all">All Types</option>
                      <option value="inquiry">Inquiries</option>
                      <option value="transaction">Transactions</option>
                      <option value="verification">Verifications</option>
                      <option value="system">System</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="divide-y divide-gray-100 dark:divide-gray-700">
                {filteredEntries.length === 0 ? (
                  <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                    No entries found matching your criteria
                  </div>
                ) : (
                  filteredEntries.map((entry) => (
                    <div
                      key={entry.id}
                      className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50"
                      onClick={() =>
                        setExpandedEntry(expandedEntry === entry.id ? null : entry.id)
                      }
                    >
                      <div className="flex items-start gap-3 p-4">
                        <div className="mt-1">{getEntryIcon(entry.type)}</div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm text-gray-900 dark:text-white">
                            {entry.content}
                          </p>
                          <div className="mt-1 flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                            <span className="flex items-center gap-1">
                              <User className="h-3 w-3" />
                              {entry.author}
                            </span>
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {formatTimestamp(entry.timestamp)}
                            </span>
                          </div>
                        </div>
                        {expandedEntry === entry.id ? (
                          <ChevronUp className="h-4 w-4 text-gray-400" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-gray-400" />
                        )}
                      </div>
                      {expandedEntry === entry.id && entry.metadata && (
                        <div className="border-t border-gray-100 bg-gray-50 px-4 py-3 dark:border-gray-600 dark:bg-gray-700/30">
                          <p className="mb-2 text-xs font-medium text-gray-500 dark:text-gray-400">
                            Metadata
                          </p>
                          <pre className="text-xs text-gray-600 dark:text-gray-300">
                            {JSON.stringify(entry.metadata, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Recent Blocks */}
          <div>
            <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
              <div className="border-b border-gray-200 p-4 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Recent Blocks
                </h2>
              </div>
              <div className="divide-y divide-gray-100 dark:divide-gray-700">
                {mockBlocks.map((block) => (
                  <div key={block.hash} className="p-4">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-2 text-sm font-medium text-gray-900 dark:text-white">
                        <Database className="h-4 w-4 text-indigo-500" />
                        Block #{block.index}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {formatTimestamp(block.timestamp)}
                      </span>
                    </div>
                    <div className="mt-2 flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                      <Hash className="h-3 w-3" />
                      <span className="font-mono">{block.hash.slice(0, 16)}...</span>
                    </div>
                    <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      {block.entries} entries
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Chain Validity */}
            {stats && (
              <div className="mt-4 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                  Chain Integrity
                </h3>
                <div className="mt-3 flex items-center gap-2">
                  {stats.chain_valid ? (
                    <>
                      <CheckCircle className="h-5 w-5 text-green-500" />
                      <span className="text-sm text-green-600 dark:text-green-400">
                        Chain is valid
                      </span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="h-5 w-5 text-red-500" />
                      <span className="text-sm text-red-600 dark:text-red-400">
                        Chain integrity issue
                      </span>
                    </>
                  )}
                </div>
                {stats.latest_block_hash && (
                  <div className="mt-3">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Latest Hash</p>
                    <p className="mt-1 font-mono text-xs text-gray-600 dark:text-gray-300 break-all">
                      {stats.latest_block_hash}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
