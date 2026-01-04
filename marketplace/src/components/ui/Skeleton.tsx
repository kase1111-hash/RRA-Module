'use client';

import { cn } from '@/lib/utils';

export interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded';
  width?: string | number;
  height?: string | number;
  animation?: 'pulse' | 'wave' | 'none';
}

export function Skeleton({
  className,
  variant = 'text',
  width,
  height,
  animation = 'pulse',
}: SkeletonProps) {
  const baseStyles = 'bg-gray-200 dark:bg-gray-700';

  const animations = {
    pulse: 'animate-pulse',
    wave: 'animate-shimmer bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 dark:from-gray-700 dark:via-gray-600 dark:to-gray-700 bg-[length:200%_100%]',
    none: '',
  };

  const variants = {
    text: 'rounded h-4',
    circular: 'rounded-full',
    rectangular: '',
    rounded: 'rounded-lg',
  };

  const style = {
    width: width ?? (variant === 'circular' ? height : '100%'),
    height: height ?? (variant === 'text' ? undefined : '100%'),
  };

  return (
    <div
      className={cn(baseStyles, animations[animation], variants[variant], className)}
      style={style}
    />
  );
}

// Pre-built skeleton components for common use cases
export function SkeletonCard() {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Skeleton variant="circular" width={40} height={40} />
          <div className="space-y-2">
            <Skeleton width={120} height={16} />
            <Skeleton width={80} height={12} />
          </div>
        </div>
        <div className="text-right space-y-1">
          <Skeleton width={60} height={20} />
          <Skeleton width={40} height={12} />
        </div>
      </div>
      <div className="mt-4 space-y-2">
        <Skeleton width="100%" height={14} />
        <Skeleton width="80%" height={14} />
      </div>
      <div className="mt-4 flex gap-4">
        <Skeleton width={60} height={16} />
        <Skeleton width={40} height={16} />
        <Skeleton width={50} height={16} />
      </div>
      <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700 flex justify-between">
        <Skeleton width={100} height={12} />
        <Skeleton width={80} height={16} />
      </div>
    </div>
  );
}

export function SkeletonTable({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex gap-4 pb-3 border-b border-gray-200 dark:border-gray-700">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} width={`${100 / columns}%`} height={16} />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex gap-4 py-2">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={colIndex} width={`${100 / columns}%`} height={14} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonChat({ messages = 3 }: { messages?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: messages }).map((_, i) => (
        <div
          key={i}
          className={cn('flex gap-3', i % 2 === 0 ? 'justify-start' : 'justify-end')}
        >
          {i % 2 === 0 && <Skeleton variant="circular" width={32} height={32} />}
          <div className={cn('space-y-2', i % 2 === 0 ? 'max-w-[70%]' : 'max-w-[60%]')}>
            <Skeleton
              variant="rounded"
              width={i % 2 === 0 ? 280 : 200}
              height={60}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export function SkeletonStats({ count = 4 }: { count?: number }) {
  return (
    <div className={cn('grid gap-4', `grid-cols-${Math.min(count, 4)}`)}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
        >
          <Skeleton width={80} height={12} className="mb-2" />
          <Skeleton width={100} height={28} className="mb-1" />
          <Skeleton width={60} height={10} />
        </div>
      ))}
    </div>
  );
}
