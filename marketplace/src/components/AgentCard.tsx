'use client';

import Link from 'next/link';
import { Star, GitFork, Code, ArrowRight, ShieldCheck, ShieldAlert, ShieldX } from 'lucide-react';
import { cn, formatPrice, getLanguageColor, formatRelativeTime } from '@/lib/utils';
import type { Repository, MarketConfig, VerificationResult } from '@/types';

interface AgentCardProps {
  repository: Repository;
  marketConfig?: MarketConfig;
  featured?: boolean;
  verification?: VerificationResult;
}

export function AgentCard({ repository, marketConfig, featured, verification }: AgentCardProps) {
  const primaryLanguage = repository.languages?.[0] || 'Unknown';

  const getVerificationIcon = () => {
    if (!verification) return null;
    switch (verification.overall_status) {
      case 'passed':
        return <ShieldCheck className="h-4 w-4 text-green-500" />;
      case 'warning':
        return <ShieldAlert className="h-4 w-4 text-yellow-500" />;
      case 'failed':
        return <ShieldX className="h-4 w-4 text-red-500" />;
      default:
        return null;
    }
  };

  const getVerificationLabel = () => {
    if (!verification) return null;
    return `${verification.score.toFixed(0)}%`;
  };

  return (
    <Link
      href={`/agent/${repository.id}`}
      className={cn(
        'group relative flex flex-col rounded-xl border bg-white p-6 transition-all hover:shadow-lg dark:bg-gray-800',
        featured
          ? 'border-primary-200 ring-2 ring-primary-100 dark:border-primary-800 dark:ring-primary-900'
          : 'border-gray-200 hover:border-gray-300 dark:border-gray-700 dark:hover:border-gray-600'
      )}
    >
      {/* Badges Row */}
      <div className="absolute -top-3 left-4 flex items-center gap-2">
        {/* Featured Badge */}
        {featured && (
          <span className="inline-flex items-center rounded-full bg-primary-600 px-3 py-0.5 text-xs font-medium text-white">
            Featured
          </span>
        )}
        {/* Verification Badge */}
        {verification && (
          <span className={cn(
            'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
            verification.overall_status === 'passed' && 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
            verification.overall_status === 'warning' && 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
            verification.overall_status === 'failed' && 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
          )}>
            {getVerificationIcon()}
            {getVerificationLabel()}
          </span>
        )}
      </div>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-3">
          {/* Avatar */}
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 text-lg font-bold text-gray-600 dark:bg-gray-700 dark:text-gray-300">
            {repository.owner?.[0]?.toUpperCase() || 'R'}
          </div>

          {/* Name and Owner */}
          <div>
            <h3 className="font-semibold text-gray-900 group-hover:text-primary-600 dark:text-white dark:group-hover:text-primary-400">
              {repository.name}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {repository.owner}
            </p>
          </div>
        </div>

        {/* Price */}
        {marketConfig?.target_price && (
          <div className="text-right">
            <p className="text-lg font-bold text-gray-900 dark:text-white">
              {formatPrice(marketConfig.target_price)}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {marketConfig.license_model || 'Per-seat'}
            </p>
          </div>
        )}
      </div>

      {/* Description */}
      <p className="mt-3 line-clamp-2 text-sm text-gray-600 dark:text-gray-300">
        {repository.description || 'No description provided.'}
      </p>

      {/* Stats */}
      <div className="mt-4 flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
        {/* Language */}
        <div className="flex items-center space-x-1">
          <span
            className="h-3 w-3 rounded-full"
            style={{ backgroundColor: getLanguageColor(primaryLanguage) }}
          />
          <span>{primaryLanguage}</span>
        </div>

        {/* Stars */}
        {repository.stars !== undefined && (
          <div className="flex items-center space-x-1">
            <Star className="h-4 w-4" />
            <span>{repository.stars}</span>
          </div>
        )}

        {/* Forks */}
        {repository.forks !== undefined && (
          <div className="flex items-center space-x-1">
            <GitFork className="h-4 w-4" />
            <span>{repository.forks}</span>
          </div>
        )}

        {/* Files */}
        <div className="flex items-center space-x-1">
          <Code className="h-4 w-4" />
          <span>{repository.files} files</span>
        </div>
      </div>

      {/* Languages Tags */}
      {repository.languages && repository.languages.length > 1 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {repository.languages.slice(0, 4).map((lang) => (
            <span
              key={lang}
              className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-300"
            >
              {lang}
            </span>
          ))}
          {repository.languages.length > 4 && (
            <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-300">
              +{repository.languages.length - 4}
            </span>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-4 dark:border-gray-700">
        <span className="text-xs text-gray-500 dark:text-gray-400">
          Updated {formatRelativeTime(repository.updated_at)}
        </span>

        <span className="flex items-center text-sm font-medium text-primary-600 group-hover:text-primary-700 dark:text-primary-400 dark:group-hover:text-primary-300">
          View Details
          <ArrowRight className="ml-1 h-4 w-4 transition-transform group-hover:translate-x-1" />
        </span>
      </div>
    </Link>
  );
}
