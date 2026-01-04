'use client';

import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  rounded?: 'default' | 'full';
  icon?: ReactNode;
  removable?: boolean;
  onRemove?: () => void;
  pulse?: boolean;
}

const variants = {
  default: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  primary: 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300',
  success: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  warning: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
  danger: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  info: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  outline: 'bg-transparent border border-gray-300 text-gray-700 dark:border-gray-600 dark:text-gray-300',
};

const sizes = {
  sm: 'px-1.5 py-0.5 text-xs',
  md: 'px-2.5 py-0.5 text-xs',
  lg: 'px-3 py-1 text-sm',
};

const iconSizes = {
  sm: 'h-3 w-3',
  md: 'h-3.5 w-3.5',
  lg: 'h-4 w-4',
};

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      className,
      variant = 'default',
      size = 'md',
      rounded = 'full',
      icon,
      removable = false,
      onRemove,
      pulse = false,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <span
        ref={ref}
        className={cn(
          'inline-flex items-center font-medium gap-1',
          variants[variant],
          sizes[size],
          rounded === 'full' ? 'rounded-full' : 'rounded-md',
          pulse && 'animate-pulse',
          className
        )}
        {...props}
      >
        {icon && <span className={iconSizes[size]}>{icon}</span>}
        {children}
        {removable && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onRemove?.();
            }}
            className={cn(
              'ml-0.5 hover:opacity-70 transition-opacity',
              iconSizes[size]
            )}
          >
            <X className="h-full w-full" />
          </button>
        )}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

// Dot badge for status indicators
export interface DotBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  status?: 'online' | 'offline' | 'busy' | 'away';
  pulse?: boolean;
}

const dotColors = {
  online: 'bg-green-500',
  offline: 'bg-gray-400',
  busy: 'bg-red-500',
  away: 'bg-yellow-500',
};

export function DotBadge({ className, status = 'online', pulse = false, children, ...props }: DotBadgeProps) {
  return (
    <span className={cn('inline-flex items-center gap-2', className)} {...props}>
      <span className="relative flex h-2.5 w-2.5">
        {pulse && (
          <span
            className={cn(
              'absolute inline-flex h-full w-full animate-ping rounded-full opacity-75',
              dotColors[status]
            )}
          />
        )}
        <span className={cn('relative inline-flex h-2.5 w-2.5 rounded-full', dotColors[status])} />
      </span>
      {children}
    </span>
  );
}
