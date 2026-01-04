'use client';

import { useState, useEffect } from 'react';
import { Link2, Link2Off, Loader2, AlertCircle, ChevronDown, Activity, Database, FileText, Hash } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ChainConnectionStatus, ChainHealth, ChainStats } from '@/types';

interface ChainStatusProps {
  compact?: boolean;
  showDetails?: boolean;
}

export function ChainStatus({ compact = false, showDetails = false }: ChainStatusProps) {
  const [status, setStatus] = useState<ChainConnectionStatus>('connecting');
  const [health, setHealth] = useState<ChainHealth | null>(null);
  const [stats, setStats] = useState<ChainStats | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkConnection = async () => {
      try {
        setStatus('connecting');

        // Try to connect to NatLangChain API
        const response = await fetch('/api/chain/health', {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        });

        if (response.ok) {
          const data = await response.json();
          setHealth(data);
          setStatus('connected');
          setError(null);

          // Get stats if connected
          if (showDetails) {
            const statsResponse = await fetch('/api/chain/stats');
            if (statsResponse.ok) {
              setStats(await statsResponse.json());
            }
          }
        } else {
          setStatus('error');
          setError('Chain not available');
        }
      } catch (err) {
        setStatus('error');
        setError('Unable to connect to NatLangChain');
      }
    };

    checkConnection();

    // Poll every 30 seconds
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, [showDetails]);

  const getStatusIcon = () => {
    switch (status) {
      case 'connected':
        return <Link2 className="h-4 w-4 text-green-500" />;
      case 'connecting':
        return <Loader2 className="h-4 w-4 text-yellow-500 animate-spin" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Link2Off className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'connected':
        return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300';
      case 'connecting':
        return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300';
      case 'error':
        return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300';
      default:
        return 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'connected':
        return 'Chain Connected';
      case 'connecting':
        return 'Connecting...';
      case 'error':
        return 'Chain Error';
      default:
        return 'Disconnected';
    }
  };

  if (compact) {
    return (
      <div
        className={cn(
          'inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-xs font-medium cursor-pointer',
          getStatusColor()
        )}
        title={`NatLangChain: ${getStatusText()}`}
      >
        {getStatusIcon()}
        <span className="hidden sm:inline">{status === 'connected' ? 'Chain' : getStatusText()}</span>
        {status === 'connected' && health && (
          <span className="hidden lg:inline text-[10px] opacity-75">
            ({health.blocks} blocks)
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn(
          'flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors',
          status === 'connected'
            ? 'border-green-200 bg-green-50 hover:bg-green-100 dark:border-green-800 dark:bg-green-900/20 dark:hover:bg-green-900/30'
            : 'border-gray-200 bg-gray-50 hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700'
        )}
      >
        {getStatusIcon()}
        <div className="flex flex-col items-start">
          <span className="font-medium">{getStatusText()}</span>
          {status === 'connected' && health && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {health.service}
            </span>
          )}
        </div>
        <ChevronDown className={cn('h-4 w-4 transition-transform', expanded && 'rotate-180')} />
      </button>

      {/* Expanded Details Panel */}
      {expanded && (
        <div className="absolute right-0 top-full mt-2 w-72 rounded-lg border border-gray-200 bg-white p-4 shadow-lg dark:border-gray-700 dark:bg-gray-800 z-50">
          <div className="space-y-4">
            {/* Connection Status */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">Status</span>
              <span className={cn(
                'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium',
                getStatusColor()
              )}>
                {getStatusIcon()}
                {getStatusText()}
              </span>
            </div>

            {status === 'connected' && health && (
              <>
                {/* Chain Info */}
                <div className="border-t border-gray-100 pt-4 dark:border-gray-700">
                  <h4 className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400 mb-3">
                    Chain Info
                  </h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="flex items-center gap-2">
                      <Database className="h-4 w-4 text-primary-500" />
                      <div>
                        <p className="text-sm font-medium">{health.blocks}</p>
                        <p className="text-xs text-gray-500">Blocks</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-amber-500" />
                      <div>
                        <p className="text-sm font-medium">{health.pending_entries}</p>
                        <p className="text-xs text-gray-500">Pending</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Stats if available */}
                {stats && (
                  <div className="border-t border-gray-100 pt-4 dark:border-gray-700">
                    <h4 className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400 mb-3">
                      Statistics
                    </h4>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Total Entries</span>
                        <span className="text-sm font-medium">{stats.total_entries}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Authors</span>
                        <span className="text-sm font-medium">{stats.unique_authors}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Chain Valid</span>
                        <span className={cn(
                          'text-sm font-medium',
                          stats.chain_valid ? 'text-green-600' : 'text-red-600'
                        )}>
                          {stats.chain_valid ? 'Yes' : 'No'}
                        </span>
                      </div>
                      {stats.latest_block_hash && (
                        <div className="flex items-center gap-1 mt-2">
                          <Hash className="h-3 w-3 text-gray-400" />
                          <span className="text-xs text-gray-500 font-mono truncate">
                            {stats.latest_block_hash.slice(0, 16)}...
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* LLM Validation */}
                <div className="border-t border-gray-100 pt-4 dark:border-gray-700">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">LLM Validation</span>
                    <span className={cn(
                      'inline-flex items-center gap-1 text-xs font-medium',
                      health.llm_validation_available ? 'text-green-600' : 'text-gray-500'
                    )}>
                      <Activity className="h-3 w-3" />
                      {health.llm_validation_available ? 'Available' : 'Unavailable'}
                    </span>
                  </div>
                </div>
              </>
            )}

            {error && (
              <div className="text-sm text-red-600 dark:text-red-400">
                {error}
              </div>
            )}

            {/* Action Links */}
            <div className="border-t border-gray-100 pt-4 dark:border-gray-700">
              <a
                href="/chain"
                className="block w-full rounded-lg bg-primary-600 px-4 py-2 text-center text-sm font-medium text-white hover:bg-primary-700 transition-colors"
              >
                View Chain Explorer
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Simple indicator for header
export function ChainIndicator() {
  const [status, setStatus] = useState<'connecting' | 'connected' | 'demo' | 'error'>('connecting');

  useEffect(() => {
    const checkConnection = async () => {
      try {
        const response = await fetch('/api/chain/health');
        if (response.ok) {
          const data = await response.json();
          // Check if it's a mock/demo response
          setStatus(data.mock ? 'demo' : 'connected');
        } else {
          setStatus('error');
        }
      } catch {
        setStatus('error');
      }
    };

    checkConnection();
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div
      className={cn(
        'flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-colors',
        status === 'connected'
          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
          : status === 'demo'
          ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
          : status === 'connecting'
          ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
          : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
      )}
      title={`NatLangChain: ${status === 'demo' ? 'Demo Mode' : status}`}
    >
      {status === 'connected' ? (
        <Link2 className="h-3.5 w-3.5" />
      ) : status === 'demo' ? (
        <Link2 className="h-3.5 w-3.5" />
      ) : status === 'connecting' ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      ) : (
        <Link2Off className="h-3.5 w-3.5" />
      )}
      <span className="hidden sm:inline">
        {status === 'connected' ? 'Chain' : status === 'demo' ? 'Demo' : status === 'connecting' ? '...' : 'Offline'}
      </span>
    </div>
  );
}
