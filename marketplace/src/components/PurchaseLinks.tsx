'use client';

import { useState } from 'react';
import {
  Link2,
  Copy,
  Check,
  ExternalLink,
  QrCode,
  Share2,
  Wallet,
  Shield,
  Tag,
  ChevronRight,
} from 'lucide-react';
import { cn, copyToClipboard, formatAddress, formatPrice } from '@/lib/utils';
import type { PurchaseLink, MarketplaceListing, NetworkType } from '@/types';

interface PurchaseLinkCardProps {
  link: PurchaseLink;
  className?: string;
}

export function PurchaseLinkCard({ link, className }: PurchaseLinkCardProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const success = await copyToClipboard(link.url);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const tierColors: Record<string, string> = {
    standard: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    premium: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    enterprise: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
    custom: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-300',
  };

  return (
    <div className={cn(
      'flex items-center justify-between p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors',
      className
    )}>
      <div className="flex items-center gap-4">
        <div className={cn('px-3 py-1 rounded-full text-sm font-medium', tierColors[link.tier] || tierColors.custom)}>
          {link.tier.charAt(0).toUpperCase() + link.tier.slice(1)}
        </div>
        <div>
          <div className="font-semibold text-gray-900 dark:text-white">
            {link.price_display}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 font-mono">
            {link.network}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={handleCopy}
          className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          title="Copy link"
        >
          {copied ? (
            <Check size={18} className="text-green-500" />
          ) : (
            <Copy size={18} className="text-gray-400" />
          )}
        </button>
        <a
          href={link.url}
          target="_blank"
          rel="noopener noreferrer"
          className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          title="Open link"
        >
          <ExternalLink size={18} className="text-gray-400" />
        </a>
      </div>
    </div>
  );
}

interface PurchaseLinksListProps {
  links: PurchaseLink[];
  className?: string;
}

export function PurchaseLinksList({ links, className }: PurchaseLinksListProps) {
  return (
    <div className={cn('space-y-3', className)}>
      <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
        <Link2 size={18} />
        Purchase Links
      </h3>
      <div className="space-y-2">
        {links.map((link) => (
          <PurchaseLinkCard key={`${link.tier}-${link.network}`} link={link} />
        ))}
      </div>
    </div>
  );
}

interface BlockchainInfoProps {
  ipAssetId: string;
  network: NetworkType;
  explorerUrl?: string;
  className?: string;
}

export function BlockchainInfo({ ipAssetId, network, explorerUrl, className }: BlockchainInfoProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const success = await copyToClipboard(ipAssetId);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const networkColors: Record<string, string> = {
    mainnet: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    testnet: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
    localhost: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-300',
  };

  return (
    <div className={cn('p-4 rounded-lg bg-gray-50 dark:bg-gray-800/50', className)}>
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-medium text-gray-900 dark:text-white flex items-center gap-2">
          <Shield size={16} />
          Story Protocol Registration
        </h4>
        <span className={cn('px-2 py-0.5 rounded text-xs font-medium', networkColors[network])}>
          {network}
        </span>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-500 dark:text-gray-400">IP Asset ID</span>
          <div className="flex items-center gap-2">
            <code className="text-xs font-mono text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
              {formatAddress(ipAssetId)}
            </code>
            <button
              onClick={handleCopy}
              className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
            >
              {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} className="text-gray-400" />}
            </button>
          </div>
        </div>

        {explorerUrl && (
          <a
            href={explorerUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            View on Story Protocol Explorer
            <ExternalLink size={14} />
          </a>
        )}
      </div>
    </div>
  );
}

interface PurchaseButtonProps {
  link: PurchaseLink;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'secondary' | 'outline';
  className?: string;
}

export function PurchaseButton({ link, size = 'md', variant = 'primary', className }: PurchaseButtonProps) {
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  const variantClasses = {
    primary: 'bg-indigo-600 text-white hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600',
    secondary: 'bg-gray-100 text-gray-900 hover:bg-gray-200 dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700',
    outline: 'border-2 border-indigo-600 text-indigo-600 hover:bg-indigo-50 dark:border-indigo-400 dark:text-indigo-400 dark:hover:bg-indigo-900/20',
  };

  return (
    <a
      href={link.url}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        'inline-flex items-center justify-center gap-2 font-semibold rounded-lg transition-colors',
        sizeClasses[size],
        variantClasses[variant],
        className
      )}
    >
      <Wallet size={size === 'sm' ? 14 : size === 'md' ? 16 : 18} />
      Purchase {link.tier.charAt(0).toUpperCase() + link.tier.slice(1)} - {link.price_display}
      <ChevronRight size={size === 'sm' ? 14 : size === 'md' ? 16 : 18} />
    </a>
  );
}

interface ShareLinksProps {
  repoName: string;
  purchaseUrl: string;
  ipAssetId: string;
  className?: string;
}

export function ShareLinks({ repoName, purchaseUrl, ipAssetId, className }: ShareLinksProps) {
  const [copiedLink, setCopiedLink] = useState(false);
  const [copiedBadge, setCopiedBadge] = useState(false);

  const badgeMarkdown = `[![Purchase License](https://img.shields.io/badge/RRA-Purchase_License-indigo)](${purchaseUrl})`;

  const handleCopyLink = async () => {
    const success = await copyToClipboard(purchaseUrl);
    if (success) {
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    }
  };

  const handleCopyBadge = async () => {
    const success = await copyToClipboard(badgeMarkdown);
    if (success) {
      setCopiedBadge(true);
      setTimeout(() => setCopiedBadge(false), 2000);
    }
  };

  return (
    <div className={cn('space-y-4', className)}>
      <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
        <Share2 size={18} />
        Share & Embed
      </h3>

      {/* Copy Link */}
      <div className="space-y-2">
        <label className="text-sm text-gray-600 dark:text-gray-400">Direct Link</label>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={purchaseUrl}
            readOnly
            className="flex-1 px-3 py-2 text-sm font-mono bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md"
          />
          <button
            onClick={handleCopyLink}
            className="px-3 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-md transition-colors"
          >
            {copiedLink ? <Check size={16} className="text-green-500" /> : <Copy size={16} />}
          </button>
        </div>
      </div>

      {/* Badge Markdown */}
      <div className="space-y-2">
        <label className="text-sm text-gray-600 dark:text-gray-400">README Badge (Markdown)</label>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={badgeMarkdown}
            readOnly
            className="flex-1 px-3 py-2 text-sm font-mono bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md"
          />
          <button
            onClick={handleCopyBadge}
            className="px-3 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-md transition-colors"
          >
            {copiedBadge ? <Check size={16} className="text-green-500" /> : <Copy size={16} />}
          </button>
        </div>
        {/* Preview */}
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span>Preview:</span>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="https://img.shields.io/badge/RRA-Purchase_License-indigo"
            alt="Purchase License Badge"
            className="h-5"
          />
        </div>
      </div>
    </div>
  );
}

interface MarketplaceCardProps {
  listing: MarketplaceListing;
  className?: string;
}

export function MarketplaceCard({ listing, className }: MarketplaceCardProps) {
  return (
    <div className={cn('rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden', className)}>
      {/* Header */}
      <div className="p-4 bg-gradient-to-r from-indigo-500 to-purple-600 text-white">
        <h3 className="font-bold text-lg">{listing.repo_name}</h3>
        <p className="text-sm text-white/80 mt-1">{listing.description}</p>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Category & Tags */}
        <div className="flex flex-wrap gap-2">
          <span className="px-2 py-1 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded text-sm font-medium">
            {listing.category}
          </span>
          {listing.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="px-2 py-1 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded text-sm"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* Verification Score */}
        <div className="flex items-center gap-2">
          <Shield size={16} className="text-green-500" />
          <span className="text-sm">
            Verification Score: <strong>{listing.verification_score.toFixed(0)}%</strong>
          </span>
        </div>

        {/* Purchase Links */}
        <div className="space-y-2">
          {listing.purchase_links.map((link) => (
            <a
              key={link.tier}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Tag size={16} className="text-gray-400" />
                <span className="font-medium capitalize">{link.tier}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-indigo-600 dark:text-indigo-400">
                  {link.price_display}
                </span>
                <ChevronRight size={16} className="text-gray-400" />
              </div>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
