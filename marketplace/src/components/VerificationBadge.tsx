'use client';

import { Shield, ShieldCheck, ShieldAlert, ShieldX, ShieldQuestion } from 'lucide-react';
import { cn, getVerificationColor, getVerificationBgColor, getScoreColor } from '@/lib/utils';
import type { VerificationStatus } from '@/types';

interface VerificationBadgeProps {
  status: VerificationStatus;
  score?: number;
  showScore?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  onClick?: () => void;
}

export function VerificationBadge({
  status,
  score,
  showScore = false,
  size = 'md',
  className,
  onClick,
}: VerificationBadgeProps) {
  const sizeClasses = {
    sm: 'text-xs px-1.5 py-0.5 gap-1',
    md: 'text-sm px-2 py-1 gap-1.5',
    lg: 'text-base px-3 py-1.5 gap-2',
  };

  const iconSizes = {
    sm: 12,
    md: 14,
    lg: 16,
  };

  const getIcon = () => {
    const iconSize = iconSizes[size];
    switch (status) {
      case 'passed':
        return <ShieldCheck size={iconSize} className="text-green-500" />;
      case 'warning':
        return <ShieldAlert size={iconSize} className="text-yellow-500" />;
      case 'failed':
        return <ShieldX size={iconSize} className="text-red-500" />;
      case 'skipped':
        return <ShieldQuestion size={iconSize} className="text-gray-500" />;
      default:
        return <Shield size={iconSize} className="text-gray-500" />;
    }
  };

  const getLabel = () => {
    switch (status) {
      case 'passed':
        return 'Verified';
      case 'warning':
        return 'Warnings';
      case 'failed':
        return 'Failed';
      case 'skipped':
        return 'Not Verified';
      default:
        return 'Unknown';
    }
  };

  return (
    <button
      onClick={onClick}
      className={cn(
        'inline-flex items-center rounded-full font-medium transition-all',
        getVerificationBgColor(status),
        getVerificationColor(status),
        sizeClasses[size],
        onClick && 'hover:opacity-80 cursor-pointer',
        !onClick && 'cursor-default',
        className
      )}
    >
      {getIcon()}
      <span>{getLabel()}</span>
      {showScore && score !== undefined && (
        <span className={cn('font-bold', getScoreColor(score))}>
          {score.toFixed(0)}%
        </span>
      )}
    </button>
  );
}

interface VerificationScoreProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

export function VerificationScore({
  score,
  size = 'md',
  showLabel = true,
  className,
}: VerificationScoreProps) {
  const sizeClasses = {
    sm: 'w-10 h-10 text-xs',
    md: 'w-14 h-14 text-sm',
    lg: 'w-20 h-20 text-lg',
  };

  const strokeWidth = size === 'sm' ? 4 : size === 'md' ? 3 : 2;
  const radius = size === 'sm' ? 16 : size === 'md' ? 22 : 32;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;

  return (
    <div className={cn('flex flex-col items-center gap-1', className)}>
      <div className={cn('relative', sizeClasses[size])}>
        <svg className="w-full h-full transform -rotate-90">
          {/* Background circle */}
          <circle
            cx="50%"
            cy="50%"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-gray-200 dark:text-gray-700"
          />
          {/* Progress circle */}
          <circle
            cx="50%"
            cy="50%"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference - progress}
            className={getScoreColor(score)}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={cn('font-bold', getScoreColor(score))}>
            {score.toFixed(0)}
          </span>
        </div>
      </div>
      {showLabel && (
        <span className="text-xs text-gray-500 dark:text-gray-400">
          Verification Score
        </span>
      )}
    </div>
  );
}
