import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge class names with Tailwind CSS support
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format price with currency symbol
 */
export function formatPrice(price: number | string, currency: string = 'ETH'): string {
  const numPrice = typeof price === 'string' ? parseFloat(price) : price;
  if (isNaN(numPrice)) return '0 ' + currency;

  if (numPrice >= 1000000) {
    return `${(numPrice / 1000000).toFixed(2)}M ${currency}`;
  } else if (numPrice >= 1000) {
    return `${(numPrice / 1000).toFixed(2)}K ${currency}`;
  } else if (numPrice < 0.001 && numPrice > 0) {
    return `${numPrice.toExponential(2)} ${currency}`;
  }
  return `${numPrice.toFixed(4)} ${currency}`;
}

/**
 * Get color for programming language badge
 */
export function getLanguageColor(language: string): string {
  const colors: Record<string, string> = {
    TypeScript: 'bg-blue-500',
    JavaScript: 'bg-yellow-500',
    Python: 'bg-green-500',
    Rust: 'bg-orange-500',
    Go: 'bg-cyan-500',
    Solidity: 'bg-purple-500',
    Java: 'bg-red-500',
    'C++': 'bg-pink-500',
    C: 'bg-gray-500',
    Ruby: 'bg-red-600',
    PHP: 'bg-indigo-500',
    Swift: 'bg-orange-400',
    Kotlin: 'bg-violet-500',
  };
  return colors[language] || 'bg-gray-400';
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(date: Date | string | number): string {
  const now = new Date();
  const past = new Date(date);
  const diffMs = now.getTime() - past.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);
  const diffWeek = Math.floor(diffDay / 7);
  const diffMonth = Math.floor(diffDay / 30);
  const diffYear = Math.floor(diffDay / 365);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin} minute${diffMin > 1 ? 's' : ''} ago`;
  if (diffHour < 24) return `${diffHour} hour${diffHour > 1 ? 's' : ''} ago`;
  if (diffDay < 7) return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;
  if (diffWeek < 4) return `${diffWeek} week${diffWeek > 1 ? 's' : ''} ago`;
  if (diffMonth < 12) return `${diffMonth} month${diffMonth > 1 ? 's' : ''} ago`;
  return `${diffYear} year${diffYear > 1 ? 's' : ''} ago`;
}

/**
 * Get verification status color
 */
export function getVerificationColor(status: string): string {
  const colors: Record<string, string> = {
    verified: 'text-green-500',
    pending: 'text-yellow-500',
    failed: 'text-red-500',
    partial: 'text-orange-500',
    unverified: 'text-gray-500',
  };
  return colors[status?.toLowerCase()] || 'text-gray-500';
}

/**
 * Get verification status background color
 */
export function getVerificationBgColor(status: string): string {
  const colors: Record<string, string> = {
    verified: 'bg-green-500/10',
    pending: 'bg-yellow-500/10',
    failed: 'bg-red-500/10',
    partial: 'bg-orange-500/10',
    unverified: 'bg-gray-500/10',
  };
  return colors[status?.toLowerCase()] || 'bg-gray-500/10';
}

/**
 * Get score color based on value (0-100)
 */
export function getScoreColor(score: number): string {
  if (score >= 80) return 'text-green-500';
  if (score >= 60) return 'text-yellow-500';
  if (score >= 40) return 'text-orange-500';
  return 'text-red-500';
}

/**
 * Copy text to clipboard
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    // Fallback for older browsers
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    document.body.appendChild(textArea);
    textArea.select();
    try {
      document.execCommand('copy');
      return true;
    } catch {
      return false;
    } finally {
      document.body.removeChild(textArea);
    }
  }
}

/**
 * Format blockchain address (truncate middle)
 */
export function formatAddress(address: string, chars: number = 4): string {
  if (!address) return '';
  if (address.length <= chars * 2 + 2) return address;
  return `${address.slice(0, chars + 2)}...${address.slice(-chars)}`;
}
